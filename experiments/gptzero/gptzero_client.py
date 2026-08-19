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
FILES_URL = "https://api.gptzero.me/v2/predict/files"
BATCH_FILES = 50          # API limit per request (support, 2026-07-29)
BATCH_WORDS = 20_000      # server-side processing budget per request:
                          # bigger uploads time out inside the API
                          # (200 + {"error": ..., "status": 408})
BUDGET_WORDS = 520_000
PINNED_VERSION: str | None = "2026-07-04-base"   # from the 2026-07-29
                                                 # smoke run's responses
TRANSIENT_HTTP = (408, 429, 500, 502, 503, 504)


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
          reservations_path: Path, transport=None,
          retries: int = 3) -> tuple[dict, int]:
    """(raw response, billed words); 0 billed on a cache hit. Each HTTP
    attempt first checks the ceiling against the reservation ledger and
    appends its own reservation, so neither retries nor crashes can
    spend past BUDGET_WORDS unnoticed. Transient failures (429/5xx/
    network) back off and retry; anything else raises immediately;
    exhausted retries raise RuntimeError so the caller defers the
    document."""
    if transport is None:
        transport = _post_once      # resolved at call time so a patched
                                    # module attribute always wins
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


def _post_files_once(paths: list[Path]) -> dict:
    """One multipart POST to the batch files endpoint via curl (the
    support-recommended path for many documents — one request instead of
    a burst). No Content-Type header: curl sets the multipart boundary.
    The key travels in the 0600 header file, never in argv."""
    hdr = Path(__file__).resolve().parent / "local" / "curl_headers"
    hdr.parent.mkdir(parents=True, exist_ok=True)
    hdr.touch()
    hdr.chmod(0o600)
    hdr.write_text(f"x-api-key: {_api_key()}\n")
    cmd = ["curl", "-sS", "-m", "300", "-X", "POST", FILES_URL,
           "-H", "Accept: application/json", "-H", f"@{hdr}"]
    for p in paths:
        cmd += ["-F", f"files=@{p};type=text/plain"]
    if PINNED_VERSION:
        cmd += ["-F", f"version={PINNED_VERSION}"]
    cmd += ["-w", "\n%{http_code}"]
    out = subprocess.run(cmd, capture_output=True, text=True)
    if out.returncode != 0:
        raise urllib.error.URLError(out.stderr.strip()[:200])
    payload, _, code_s = out.stdout.rpartition("\n")
    code = int(code_s) if code_s.isdigit() else 0
    if code >= 400 or not payload:
        raise urllib.error.HTTPError(FILES_URL, code or 599,
                                     payload[:200], None, None)
    return json.loads(payload)


def _dump_mismatch(dir_: Path, resp: dict) -> Path:
    """A refused batch response is evidence: keep the full payload so
    the abort can be diagnosed without re-billing an attempt."""
    dir_.mkdir(parents=True, exist_ok=True)
    p = dir_ / f"batch_mismatch_{time.time_ns()}.json"
    p.write_text(json.dumps(resp))
    return p


def score_batch(items: list[tuple[str, Path]], cache_dir: Path,
                reservations_path: Path,
                transport=None,
                retries: int = 3) -> list[tuple[dict, int]]:
    """Score up to BATCH_FILES documents in ONE request. items are
    (doc_sha, text_path) with filenames '{sha}.txt', so results map back
    by filename (falling back to upload order when the response carries
    none). Cache hits are excluded from the upload and billed 0; every
    HTTP attempt first checks the ceiling and reserves the batch's words
    (an attempt can be billed even when its response is lost). Transient
    failures (408/429/5xx/network) back off and retry; anything else
    raises immediately; exhausted retries raise RuntimeError so the
    caller defers the batch. The whole batch aborts UNCACHED on a
    version or shape mismatch — a misattributed batch would poison
    every document in it. Returns (per-doc response in the single-doc
    cache format, billed words) in items order."""
    if transport is None:
        transport = _post_files_once
    results: dict[str, tuple[dict, int]] = {}
    misses: list[tuple[str, Path, int]] = []
    for sha, path in items:
        cached = _cache_path(cache_dir, sha)
        if cached.is_file():
            results[sha] = (json.loads(cached.read_text()), 0)
        else:
            misses.append((sha, path, count_words(path.read_text())))
    if misses:
        total = sum(w for _s, _p, w in misses)
        resp = None
        last: Exception | None = None
        for attempt in range(retries):
            spent = ledger(reservations_path)
            if spent + total > BUDGET_WORDS:
                raise SystemExit(
                    f"budget ceiling: {spent} reserved + {total} for "
                    f"this batch > {BUDGET_WORDS}")
            for sha, _p, w in misses:
                _reserve(reservations_path, sha, w)
            try:
                got = transport([p for _s, p, _w in misses])
            except urllib.error.HTTPError as e:
                if e.code not in TRANSIENT_HTTP:
                    raise
                last = e
            except (urllib.error.URLError, TimeoutError,
                    json.JSONDecodeError) as e:
                last = e
            else:
                # The endpoint can wrap failures in an HTTP 200 whose
                # body is {"error": ..., "status": ...} with no
                # documents — classify by the embedded status exactly
                # like a real HTTP error.
                if "documents" not in got and (
                        got.get("error") or got.get("status")):
                    status = got.get("status")
                    if status not in TRANSIENT_HTTP:
                        dump = _dump_mismatch(reservations_path.parent,
                                              got)
                        raise SystemExit(
                            f"batch error response (status {status!r}): "
                            f"{got.get('error')!r} — nothing cached; "
                            f"dumped to {dump}")
                    last = RuntimeError(
                        f"error envelope status {status}: "
                        f"{got.get('error')!r}")
                else:
                    resp = got
                    break
            time.sleep(5 * 3 ** attempt)
        if resp is None:
            raise RuntimeError(f"GPTZero batch failed after {retries} "
                               f"attempts: {last}")
        version = resp.get("version")
        docs = resp.get("documents") or []
        if PINNED_VERSION is not None and version != PINNED_VERSION:
            dump = _dump_mismatch(reservations_path.parent, resp)
            raise SystemExit(
                f"version mismatch: batch reports {version!r}, pin is "
                f"{PINNED_VERSION!r} — nothing cached; response keys "
                f"{sorted(resp)} dumped to {dump}")
        if len(docs) != len(misses):
            dump = _dump_mismatch(reservations_path.parent, resp)
            raise SystemExit(
                f"batch shape mismatch: {len(misses)} files uploaded, "
                f"{len(docs)} documents returned — nothing cached; "
                f"response dumped to {dump}")
        # Filename mapping is all-or-nothing: a complete, unique set
        # exactly matching the upload (any order), or no filenames at
        # all (upload order). A partial/duplicate/unknown mapping could
        # assign one response to two files and poison the SHA-keyed
        # cache, so it aborts with nothing written.
        names = [d.get("filename") for d in docs
                 if isinstance(d, dict) and d.get("filename")]
        by_name: dict[str, dict] = {}
        if names:
            expected = {f"{sha}.txt" for sha, _p, _w in misses}
            if (len(names) != len(docs)
                    or len(set(names)) != len(names)
                    or set(names) != expected):
                dump = _dump_mismatch(reservations_path.parent, resp)
                raise SystemExit(
                    f"batch filename mapping mismatch: {len(names)} "
                    f"named of {len(docs)} documents, "
                    f"{len(set(names) - expected)} unknown — nothing "
                    f"cached; response dumped to {dump}")
            by_name = {d["filename"]: d for d in docs}
        for i, (sha, path, w) in enumerate(misses):
            d = by_name.get(f"{sha}.txt") if by_name else docs[i]
            single = {"version": version, "documents": [d]}
            cached = _cache_path(cache_dir, sha)
            cached.parent.mkdir(parents=True, exist_ok=True)
            tmp = cached.with_suffix(".tmp")
            tmp.write_text(json.dumps(single))
            tmp.replace(cached)
            results[sha] = (single, w)
    return [results[sha] for sha, _p in items]


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
