"""Shared GitHub-API + storage core for the AI-dev-practices pipeline.

Hard-won rules baked in (see artifacts/agent_detection_cues.md, RESUME.md):
- Commit search MUST use bare-term queries for co-author trailers (the
  `author-email:` qualifier matches only the primary author and returns 0 for
  co-authored commits org-scoped). Qualifier terms are still right for tools
  that ARE the primary author/committer (Codex cloud) — so each tool carries
  its own list of full search terms, not one positional convention.
- GraphQL responses are only written if they validate as the expected shape;
  GitHub serves `{"errors":[{"type":"RATE_LIMIT"...}]}` bodies that a naive
  "non-empty" check treats as data (this corrupted 267 census cells once).
- When the GraphQL point budget is low, sleep until the advertised reset —
  short fixed retries just burn attempts against an hourly window.
- Cell files are named from explicit keys (never `tr '/' '__'`), and the key
  must include EVERY parameter that determines the cell's content (marker set,
  date range) — under-keyed caches silently served stale results once.
- Raw pulls go to a durable store OUTSIDE the worktree (session scratchpads
  get cleared): $AIRD_DATA_DIR, default ~/devel/ai-rd-analysis-data.
"""
from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path

# ---------------------------------------------------------------- storage

def data_dir() -> Path:
    d = Path(os.environ.get("AIRD_DATA_DIR", "~/devel/ai-rd-analysis-data")).expanduser()
    d.mkdir(parents=True, exist_ok=True)
    return d


def raw_dir(stage: str) -> Path:
    d = data_dir() / "raw" / stage
    d.mkdir(parents=True, exist_ok=True)
    return d


def cell_path(stage: str, *key: str) -> Path:
    """Deterministic cell file for a work unit. Key parts are joined with '@',
    '/' in a part becomes '~' (round-trippable; never collides with org names).
    Include every parameter that determines the content in the key."""
    safe = "@".join(part.replace("/", "~") for part in key)
    return raw_dir(stage) / f"{safe}.json"


def decode_cell_stem(stem: str) -> list[str]:
    """Inverse of cell_path's naming: file stem -> key parts."""
    return [part.replace("~", "/") for part in stem.split("@")]


def read_cell(path: Path, expect: type = list):
    """Parse a cell once; return the value only if it is the expected JSON
    type, else None. The single definition of 'valid cell' for all stages."""
    try:
        if not path.is_file() or path.stat().st_size < 2:
            return None
        val = json.loads(path.read_text())
    except (json.JSONDecodeError, OSError):
        return None
    return val if isinstance(val, expect) else None


def cell_valid(path: Path, expect: type = list) -> bool:
    return read_cell(path, expect) is not None


# ---------------------------------------------------------------- gh wrappers

def _gh(args: list[str], timeout: int = 90,
        allow_partial: bool = False) -> str | None:
    """allow_partial: GraphQL responses may carry node-level errors (deleted
    "ghost" accounts referenced by a PR) alongside COMPLETE data; gh exits
    nonzero on any errors array, but the jq-extracted data on stdout is
    usable. Callers that validate response shape may accept it — dropping
    whole repo-periods over one ghost user is the worse failure."""
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout)
        if r.returncode == 0:
            return r.stdout
        if allow_partial and r.stdout and r.stdout.strip():
            return r.stdout
        return None
    except subprocess.TimeoutExpired:
        return None


def rest_count(query: str, endpoint: str = "search/commits",
               retries: int = 4, backoff: float = 25.0) -> int | None:
    """total_count for a search query. None = gave up (do NOT record as 0
    unless the caller decides absence-of-evidence is acceptable)."""
    for _ in range(retries):
        out = _gh(["api", "-X", "GET", endpoint, "-f", f"q={query}",
                   "--jq", ".total_count"])
        if out is not None and out.strip().isdigit():
            return int(out.strip())
        time.sleep(backoff)
    return None


# GraphQL budget state: poll rate_limit only when the cached headroom could
# plausibly be exhausted, not before every query (each poll is a REST call).
_budget = {"remaining": None, "used_since": 0}


def graphql_budget_wait(min_remaining: int = 200) -> None:
    _budget["used_since"] += 1
    rem = _budget["remaining"]
    if rem is not None and rem - _budget["used_since"] > min_remaining:
        return
    out = _gh(["api", "rate_limit", "--jq",
               "[.resources.graphql.remaining, .resources.graphql.reset] | @tsv"])
    if not out:
        return
    try:
        remaining, reset = (int(x) for x in out.split())
    except ValueError:
        return
    _budget["remaining"], _budget["used_since"] = remaining, 0
    if remaining < min_remaining:
        wait = max(0, reset - int(time.time()) + 5)
        if 0 < wait < 4000:
            time.sleep(wait)
        _budget["remaining"] = None      # force re-poll after the reset


def graphql_nodes(query: str, variables: dict[str, object],
                  jq: str, expect: type = list,
                  retries: int = 5) -> object | None:
    """Run a GraphQL query, return the jq-extracted value only if it parses
    as `expect`. Handles rate limits by sleeping to reset. None = failed."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += (["-F", f"{k}={v}"] if isinstance(v, int) else ["-f", f"{k}={v}"])
    args += ["--jq", jq]
    for _ in range(retries):
        graphql_budget_wait()
        out = _gh(args, allow_partial=True)   # shape check below guards garbage
        if out:
            try:
                val = json.loads(out)
                if isinstance(val, expect):
                    return val
            except json.JSONDecodeError:
                pass
        time.sleep(5)
    return None


# AI-detection identities/logic live in pipeline.detect (single home).
