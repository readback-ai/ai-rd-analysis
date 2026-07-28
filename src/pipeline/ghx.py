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


def _walk(val: object, jq: str) -> object:
    """Resolve a simple dotted jq path ('.data.search') against a parsed
    response. Needed because gh does NOT apply --jq when it exits nonzero
    (node-level errors): stdout is then the raw {data, errors} envelope."""
    for part in jq.lstrip(".").split("."):
        if not part:
            continue
        if not isinstance(val, dict):
            return None
        val = val.get(part)
    return val


def _log_graphql_errors(errors: object) -> None:
    """A partial response is tolerated but never consumed silently: print
    the error types and first paths so a pipeline-wide partial-response
    event is visible in every caller's log. Null aliases inside an
    errored response are not facts (see graphql_envelope)."""
    if not isinstance(errors, list) or not errors:
        return
    errs = [e for e in errors if isinstance(e, dict)]
    types = sorted({e.get("type") or "UNKNOWN" for e in errs})
    print(f"GRAPHQL ERRORS: {len(errors)} {types}; paths="
          f"{[e.get('path') for e in errs][:4]}", flush=True)


def graphql_nodes(query: str, variables: dict[str, object],
                  jq: str, expect: type = list,
                  retries: int = 5) -> object | None:
    """Run a GraphQL query, return the jq-extracted value only if it parses
    as `expect`. Handles rate limits by sleeping to reset, and tolerates
    node-level errors (ghost accounts) by extracting from the raw envelope
    when gh skipped jq. None = failed."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in variables.items():
        args += (["-F", f"{k}={v}"] if isinstance(v, int) else ["-f", f"{k}={v}"])
    args += ["--jq", jq]
    for _ in range(retries):
        graphql_budget_wait()
        out = _gh(args, allow_partial=True)
        if out:
            try:
                val = json.loads(out)
            except json.JSONDecodeError:
                val = None
            if isinstance(val, dict) and "data" in val and "errors" in val:
                _log_graphql_errors(val.get("errors"))
                val = _walk(val, jq)      # raw envelope: jq was not applied
            if isinstance(val, expect):
                return val
        time.sleep(5)
    return None


def graphql_envelope(query: str, variables: dict[str, object] | None = None,
                     retries: int = 3) -> dict | None:
    """The FULL response envelope — {"data": ..., "errors": [...]} — for the
    rare caller that must tell a DEFINITIVE null apart from a transient
    partial failure.

    graphql_nodes above tolerates `errors` (one ghost account must not
    drop a whole repo-period; it logs them, then returns `data` alone),
    which makes its result unable to distinguish "this PR is gone" from
    "this batch timed out or hit the secondary rate limit" — GitHub
    answers both with null aliases in `data`. Callers deciding whether an
    absence is PERMANENT must use this and inspect `errors` themselves:
    a null alias is definitive only when its error is NOT_FOUND.
    None = no parseable response at all."""
    args = ["api", "graphql", "-f", f"query={query}"]
    for k, v in (variables or {}).items():
        args += (["-F", f"{k}={v}"] if isinstance(v, int)
                 else ["-f", f"{k}={v}"])
    for _ in range(retries):
        graphql_budget_wait()
        out = _gh(args, allow_partial=True)
        if out and out.strip():
            try:
                env = json.loads(out)
            except json.JSONDecodeError:
                env = None
            if isinstance(env, dict):
                return env
        time.sleep(5)
    return None


# AI-detection identities/logic live in pipeline.detect (single home).
