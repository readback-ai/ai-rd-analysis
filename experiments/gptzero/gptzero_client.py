"""GPTZero API client: reservation-ledger budget guard, versioned
response cache, transient-failure backoff.

Words are money, and an HTTP attempt can be billed server-side even
when its response is lost (connection drop after processing, crash
before the cache write). So the ceiling is enforced against words
RESERVED — one durable ledger row appended BEFORE every attempt — not
against observed successes. Cache hits reserve nothing.

The detector version is pinned for a whole design (PINNED_VERSION,
set from the smoke run before the full corpus): requests carry it,
the response cache is namespaced by it, and analyze refuses pooled
statistics over mixed versions.

The API key comes from GPTZERO_API_KEY (or the gitignored
local/api_key) and is never logged or written.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

from diffs import count_words

API_URL = "https://api.gptzero.me/v2/predict/text"
BUDGET_WORDS = 50_000
PINNED_VERSION: str | None = "2026-07-04-base"   # from the 2026-07-29
                                                 # smoke run's responses
TRANSIENT_HTTP = (429, 500, 502, 503, 504)


def ledger(reservations_path: Path) -> int:
    """Words reserved so far — every attempt row counts, settled or
    not."""
    if not reservations_path.is_file():
        return 0
    return sum(json.loads(ln)["words"]
               for ln in reservations_path.read_text().splitlines()
               if ln.strip())


def _reserve(path: Path, doc_sha: str, words: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        f.write(json.dumps({"doc_sha": doc_sha, "words": words}) + "\n")
        f.flush()
        os.fsync(f.fileno())


def _api_key() -> str:
    """GPTZERO_API_KEY from the environment, the experiment's .env file
    (KEY=VALUE lines), or the gitignored local/api_key. The key is read
    at call time and never logged or written."""
    key = os.environ.get("GPTZERO_API_KEY")
    here = Path(__file__).resolve().parent
    if not key:
        env = here / ".env"
        if env.is_file():
            names = {"GPTZERO_API_KEY", "GPTZERO_KEY", "API_KEY",
                     "X_API_KEY"}
            lines = [ln.strip() for ln in env.read_text().splitlines()
                     if ln.strip() and not ln.strip().startswith("#")]
            for ln in lines:
                k, sep, v = ln.partition("=")
                k = k.strip()
                if k.startswith("export "):
                    k = k[len("export "):].strip()
                if sep and k in names and v.strip():
                    key = v.strip().strip("'\"")
                    break
            if not key and len(lines) == 1 and "=" not in lines[0]:
                key = lines[0]          # bare token, no NAME= wrapper
    if not key:
        p = here / "local" / "api_key"
        if p.is_file():
            key = p.read_text().strip()
    if not key:
        raise SystemExit("no GPTZero key: set GPTZERO_API_KEY, put it "
                         "in experiments/gptzero/.env, or write "
                         "experiments/gptzero/local/api_key")
    return key


def _post_once(text: str) -> dict:
    """One POST via curl: GPTZero's edge blocks urllib's client
    signature (Cloudflare 1010) but accepts standard API clients. The
    key travels in a 0600 header file, never in argv. Raises
    urllib.error types so score()'s transient/permanent classification
    is transport-agnostic."""
    body: dict = {"document": text, "multilingual": False}
    if PINNED_VERSION:
        body["version"] = PINNED_VERSION
    hdr = Path(__file__).resolve().parent / "local" / "curl_headers"
    hdr.parent.mkdir(parents=True, exist_ok=True)
    hdr.touch()
    hdr.chmod(0o600)
    hdr.write_text(f"x-api-key: {_api_key()}\n")
    out = subprocess.run(
        ["curl", "-sS", "-m", "120", "-X", "POST", API_URL,
         "-H", "Content-Type: application/json",
         "-H", "Accept: application/json",
         "-H", f"@{hdr}",
         "--data", "@-",
         "-w", "\n%{http_code}"],
        input=json.dumps(body), capture_output=True, text=True)
    if out.returncode != 0:
        raise urllib.error.URLError(out.stderr.strip()[:200])
    payload, _, code_s = out.stdout.rpartition("\n")
    code = int(code_s) if code_s.isdigit() else 0
    if code >= 400 or not payload:
        raise urllib.error.HTTPError(API_URL, code or 599,
                                     payload[:200], None, None)
    return json.loads(payload)


def _cache_path(cache_dir: Path, doc_sha: str) -> Path:
    return cache_dir / (PINNED_VERSION or "unpinned") / f"{doc_sha}.json"


def score(doc_sha: str, text: str, cache_dir: Path,
          reservations_path: Path, transport=_post_once,
          retries: int = 3) -> tuple[dict, int]:
    """(raw response, billed words); 0 billed on a cache hit. Each HTTP
    attempt first checks the ceiling against the reservation ledger and
    appends its own reservation, so neither retries nor crashes can
    spend past BUDGET_WORDS unnoticed. Transient failures (429/5xx/
    network) back off and retry; anything else raises immediately;
    exhausted retries raise RuntimeError so the caller defers the
    document."""
    cached = _cache_path(cache_dir, doc_sha)
    if cached.is_file():
        return json.loads(cached.read_text()), 0
    words = count_words(text)
    last: Exception | None = None
    for attempt in range(retries):
        spent = ledger(reservations_path)
        if spent + words > BUDGET_WORDS:
            raise SystemExit(
                f"budget ceiling: {spent} reserved + {words} for this "
                f"document > {BUDGET_WORDS}")
        _reserve(reservations_path, doc_sha, words)
        try:
            resp = transport(text)
        except urllib.error.HTTPError as e:
            if e.code not in TRANSIENT_HTTP:
                raise
            last = e
        except (urllib.error.URLError, TimeoutError,
                json.JSONDecodeError) as e:
            last = e
        else:
            if PINNED_VERSION is not None:
                got = resp.get("version") or (
                    (resp.get("documents") or [{}])[0].get("version"))
                if got != PINNED_VERSION:
                    # NOT cached (it would poison the pinned namespace
                    # for every later run) and the whole run aborts —
                    # a wrong pin must not bill the remaining corpus.
                    # The reservation above stands: the attempt may
                    # have been billed.
                    raise SystemExit(
                        f"version mismatch: response reports {got!r}, "
                        f"pin is {PINNED_VERSION!r} — nothing cached; "
                        f"fix the pin before re-running")
            cached.parent.mkdir(parents=True, exist_ok=True)
            tmp = cached.with_suffix(".tmp")
            tmp.write_text(json.dumps(resp))
            tmp.replace(cached)
            return resp, words
        time.sleep(5 * 3 ** attempt)
    raise RuntimeError(f"GPTZero request failed after {retries} "
                       f"attempts: {last}")


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
