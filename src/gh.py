"""Thin, throttled wrapper over `gh api` for Phase 0 sampling (read-only).

Uses the gh CLI so it inherits keyring auth (no PAT env var). Honors the Search
API's 30 req/min limit with a conservative interval and backs off on secondary
rate limits. Not the production Stage 0 client -- just enough for Phase 0.
"""
from __future__ import annotations
import json
import subprocess
import sys
import time
import urllib.parse

_SEARCH_MIN_INTERVAL = 2.2          # ~27 req/min, under the 30/min search cap
_last_call = [0.0]


class ResultsExhausted(Exception):
    """Search returned 422 -- past the 1000-result ceiling for this query."""


def _throttle() -> None:
    wait = _SEARCH_MIN_INTERVAL - (time.monotonic() - _last_call[0])
    if wait > 0:
        time.sleep(wait)
    _last_call[0] = time.monotonic()


def gh_api(path: str, throttle: bool = True, retries: int = 4) -> dict:
    if throttle:
        _throttle()
    for attempt in range(retries):
        proc = subprocess.run(["gh", "api", path], capture_output=True, text=True)
        if proc.returncode == 0:
            return json.loads(proc.stdout)
        err = (proc.stderr or "").strip()
        low = err.lower()
        if "http 422" in low:
            raise ResultsExhausted(err)
        if "rate limit" in low or "secondary" in low or "http 403" in low:
            backoff = 30 * (attempt + 1)
            print(f"    rate-limited, sleeping {backoff}s ({err[:100]})", file=sys.stderr)
            time.sleep(backoff)
            continue
        raise RuntimeError(f"gh api {path} failed: {err[:300]}")
    raise RuntimeError(f"gh api {path}: exhausted {retries} retries")


def search(kind: str, q: str, per_page: int = 100, max_pages: int = 10,
           sort: str | None = None, order: str = "desc"):
    """Paginate a Search endpoint (kind: 'issues' or 'commits') up to the 1000 cap.

    Yields item dicts. Stops at max_pages, the 1000-result ceiling, or 422.
    """
    base = f"search/{kind}?q={urllib.parse.quote(q)}&per_page={per_page}"
    if sort:
        base += f"&sort={sort}&order={order}"
    for page in range(1, max_pages + 1):
        try:
            data = gh_api(f"{base}&page={page}")
        except ResultsExhausted:
            return
        items = data.get("items", [])
        for it in items:
            yield it
        if len(items) < per_page:
            return
