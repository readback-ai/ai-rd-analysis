"""GPTZero API client: response cache + hard word-budget guard.

Words are money: a document is billed once, so the response cache
(keyed by document sha256) short-circuits both the POST and the ledger,
and the ceiling is checked BEFORE any HTTP. The ledger is recomputed
from the results file on every run — a crashed run resumes without
double-spending. The API key comes from GPTZERO_API_KEY and is never
logged or written anywhere.
"""
from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

from diffs import count_words

API_URL = "https://api.gptzero.me/v2/predict/text"
BUDGET_WORDS = 50_000


def ledger(results_path: Path) -> int:
    """Words billed so far = sum over recorded results, never a running
    variable."""
    if not results_path.is_file():
        return 0
    return sum(json.loads(ln)["billed_words"]
               for ln in results_path.read_text().splitlines()
               if ln.strip())


def _api_key() -> str:
    """GPTZERO_API_KEY env var, else the gitignored local/api_key file.
    The key is read at call time and never logged or written."""
    key = os.environ.get("GPTZERO_API_KEY")
    if not key:
        p = Path(__file__).resolve().parent / "local" / "api_key"
        if p.is_file():
            key = p.read_text().strip()
    if not key:
        raise SystemExit("no GPTZero key: set GPTZERO_API_KEY or write "
                         "experiments/gptzero/local/api_key")
    return key


def _post(text: str, retries: int = 3) -> dict:
    """POST with backoff on transient failures (429/5xx/network). A
    non-transient HTTP error (bad key, bad request) raises immediately;
    exhausted retries raise RuntimeError so the caller can defer the
    document instead of crashing the run."""
    last: Exception | None = None
    for attempt in range(retries):
        req = urllib.request.Request(
            API_URL,
            data=json.dumps({"document": text,
                             "multilingual": False}).encode(),
            headers={"Content-Type": "application/json",
                     "Accept": "application/json",
                     "x-api-key": _api_key()})
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                return json.loads(r.read())
        except urllib.error.HTTPError as e:
            if e.code not in (429, 500, 502, 503, 504):
                raise
            last = e
        except (urllib.error.URLError, TimeoutError,
                json.JSONDecodeError) as e:
            last = e
        time.sleep(5 * 3 ** attempt)
    raise RuntimeError(f"GPTZero request failed after {retries} tries: "
                       f"{last}")


def score(doc_sha: str, text: str, spent: int, cache_dir: Path,
          transport=_post) -> tuple[dict, int]:
    """(raw response, billed words). billed = 0 on a cache hit."""
    cached = cache_dir / f"{doc_sha}.json"
    if cached.is_file():
        return json.loads(cached.read_text()), 0
    words = count_words(text)
    if spent + words > BUDGET_WORDS:
        raise SystemExit(
            f"budget ceiling: {spent} spent + {words} for this document "
            f"> {BUDGET_WORDS}")
    resp = transport(text)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = cached.with_suffix(".tmp")
    tmp.write_text(json.dumps(resp))
    tmp.replace(cached)
    return resp, words


def doc_fields(resp: dict) -> dict:
    """Document-level fields pinned into the results row; missing keys
    become None so schema drift surfaces in analysis, not as a crash."""
    d = (resp.get("documents") or [{}])[0]
    return {"predicted_class": d.get("predicted_class"),
            "class_probabilities": d.get("class_probabilities"),
            "completely_generated_prob":
                d.get("completely_generated_prob"),
            "confidence_category": d.get("confidence_category"),
            "model_version": resp.get("version") or d.get("version")}
