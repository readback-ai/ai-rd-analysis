"""Shared GitHub-API + storage core for the AI-dev-practices pipeline.

Hard-won rules baked in (see artifacts/agent_detection_cues.md, RESUME.md):
- Commit search MUST use bare-term queries (the `author-email:` qualifier matches
  only the primary author and returns 0 for co-authored commits org-scoped).
- GraphQL responses are only written if they validate as the expected shape;
  GitHub serves `{"errors":[{"type":"RATE_LIMIT"...}]}` bodies that a naive
  "non-empty" check treats as data (this corrupted 267 census cells once).
- When the GraphQL point budget is low, sleep until the advertised reset —
  short fixed retries just burn attempts against an hourly window.
- Cell files are named from explicit keys (never `tr '/' '__'`, which maps
  char-for-char and broke safe-name round-tripping once).
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
    '/' in a part becomes '~' (round-trippable; never collides with org names)."""
    safe = "@".join(part.replace("/", "~") for part in key)
    return raw_dir(stage) / f"{safe}.json"


def cell_valid(path: Path, expect: type = list) -> bool:
    """A cell counts as done only if it parses as the expected JSON type."""
    if not path.is_file() or path.stat().st_size < 2:
        return False
    try:
        return isinstance(json.loads(path.read_text()), expect)
    except (json.JSONDecodeError, OSError):
        return False


# ---------------------------------------------------------------- gh wrappers

def _gh(args: list[str], timeout: int = 90) -> str | None:
    try:
        r = subprocess.run(["gh"] + args, capture_output=True, text=True, timeout=timeout)
        return r.stdout if r.returncode == 0 else None
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


def graphql_budget_wait(min_remaining: int = 200) -> None:
    """Sleep until the GraphQL point budget resets if we're nearly out."""
    out = _gh(["api", "rate_limit", "--jq",
               "[.resources.graphql.remaining, .resources.graphql.reset] | @tsv"])
    if not out:
        return
    try:
        remaining, reset = (int(x) for x in out.split())
    except ValueError:
        return
    if remaining < min_remaining:
        wait = max(0, reset - int(time.time()) + 5)
        if 0 < wait < 4000:
            time.sleep(wait)


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
        out = _gh(args)
        if out:
            try:
                val = json.loads(out)
                if isinstance(val, expect):
                    return val
            except json.JSONDecodeError:
                pass
        time.sleep(5)
    return None


# ---------------------------------------------------------------- AI markers

# v1 marker set: what every published Phase-0 number used (comparability).
MARKERS_V1 = {
    "claude": ("noreply@anthropic.com", "Generated with [Claude Code]"),
    "cursor": ("cursoragent@cursor.com",),
}
# v2 adds the R4 extensions (quantify the delta before switching headlines).
MARKERS_V2 = MARKERS_V1 | {
    "aider": ("Co-authored-by: aider",),
    "codex": ("chatgpt-codex-connector", "codex@openai.com"),
}
# PR authors that are coding agents (bot-authored PRs carry no trailer).
AGENT_PR_AUTHORS = {
    "copilot-swe-agent", "devin-ai-integration", "cursor", "google-labs-jules",
    "codegen-sh", "amazon-q-developer", "factory-droid", "claude",
}


def pr_ai_tools(pr: dict, markers: dict[str, tuple[str, ...]] = MARKERS_V1,
                include_bot_authors: bool = False) -> set[str]:
    """Which AI tools left evidence in this PR (search-API PullRequest node
    with commits{nodes{commit{message authors{nodes{email}}}}})."""
    found: set[str] = set()
    for c in (pr.get("commits") or {}).get("nodes") or []:
        commit = c.get("commit") or {}
        hay = commit.get("message") or ""
        for a in (commit.get("authors") or {}).get("nodes") or []:
            hay += "\n" + ((a or {}).get("email") or "")
        for tool, needles in markers.items():
            if any(n in hay for n in needles):
                found.add(tool)
    if include_bot_authors:
        login = ((pr.get("author") or {}).get("login") or "").removesuffix("[bot]")
        if login in AGENT_PR_AUTHORS:
            found.add(f"agent:{login}")
    return found
