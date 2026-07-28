"""Stage 3a — batch PR-denominator precount via aliased GraphQL search.

The census needs total-PR counts per (repo, period) to decide full-census vs
sub-windowing. Fetching each via REST `search/issues` costs one 30/min-budget
call per cell (~4.5h for 8k cells) and was the census bottleneck. GraphQL
allows ~20 aliased `search(...){issueCount}` sub-queries per call on the
5000-point/hr budget, collapsing 8k counts into ~400 calls (~15 min).

Counts are written one cell per (repo, period) under raw/precount/, which
census.census_repo_period consults before falling back to REST.

Usage:
  python -m pipeline.precount --repos census_repos.txt \
      --periods Q1-2024 Q4-2025 Q1-2026 Q2-2026
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from pipeline.ghx import cell_path, graphql_nodes, read_cell, rest_count
from pipeline.scan_orgs import QUARTER_RANGES, resolve_period

BATCH = 20
BROWNOUT_WAIT = 60   # seconds; brownouts are minutes-scale (the census
                     # self-heal waits the same horizon)


def precount_path(repo: str, period: str) -> Path:
    return cell_path("precount", repo, period)


def get_precount(repo: str, period: str) -> int | None:
    """Census-side lookup: cached denominator or None."""
    val = read_cell(precount_path(repo, period), dict)
    return val.get("total") if val else None


def write_precount(repo: str, period: str, total: int) -> None:
    precount_path(repo, period).write_text(json.dumps({"total": total}))


def ensure_precount(repo: str, period: str) -> int | None:
    """Cached denominator, querying REST search and cache-writing on miss —
    the ONE home for precount read/query/write (census delegates here).
    None only when the query itself fails (never recorded, per durability
    rules)."""
    total = get_precount(repo, period)
    if total is not None:
        return total
    rng = resolve_period(period)
    total = rest_count(f"repo:{repo} is:pr created:{rng}",
                       endpoint="search/issues")
    time.sleep(2)
    if total is not None:
        write_precount(repo, period, total)
    return total


def confirm_zero_precount(repo: str, period: str) -> int | None:
    """A zero denominator is unverifiable from one sample: a browned-out
    search returns 200 with issueCount 0, indistinguishable from a truly
    empty repo-period. So a 0 only counts once independently re-observed:
    re-query fresh; a confirmed 0 is cache-marked so later runs trust it,
    a nonzero recount replaces the cached value, and a failed recount
    returns None (never recorded).

    Independence is temporal: a zero observed within the last
    BROWNOUT_WAIT seconds (cell mtime) could sit in the same brownout as
    its confirmation, so the recount first waits out the remainder of
    that horizon; an older cached zero is already independent and is
    re-queried immediately. (The sleeps after each rest_count are
    rate-limit pacing, not independence.)"""
    p = precount_path(repo, period)
    val = read_cell(p, dict)
    if val and val.get("confirmed"):
        return 0
    try:
        age = time.time() - p.stat().st_mtime
    except OSError:
        age = 0.0
    if age < BROWNOUT_WAIT:
        time.sleep(BROWNOUT_WAIT - age)
    rng = resolve_period(period)
    fresh = rest_count(f"repo:{repo} is:pr created:{rng}",
                       endpoint="search/issues")
    time.sleep(2)
    if fresh is None:
        return None
    if fresh == 0:
        precount_path(repo, period).write_text(
            json.dumps({"total": 0, "confirmed": True}))
    else:
        write_precount(repo, period, fresh)
    return fresh


def batch_counts(pairs: list[tuple[str, str]]) -> int:
    """Fetch denominators for up to BATCH (repo, period) pairs in one call.
    Returns how many were written."""
    todo = [(r, p) for r, p in pairs if get_precount(r, p) is None]
    if not todo:
        return 0
    parts = []
    for i, (repo, per) in enumerate(todo):
        q = f"repo:{repo} is:pr created:{resolve_period(per)}"
        parts.append(f'a{i}: search(query:"{q}", type:ISSUE){{ issueCount }}')
    query = "query{ " + " ".join(parts) + " }"
    data = graphql_nodes(query, {}, ".data", expect=dict)
    if data is None:
        return 0
    written = 0
    for i, (repo, per) in enumerate(todo):
        node = data.get(f"a{i}")
        if isinstance(node, dict) and isinstance(node.get("issueCount"), int):
            write_precount(repo, per, node["issueCount"])
            written += 1
    return written


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", required=True)
    ap.add_argument("--periods", nargs="+", default=list(QUARTER_RANGES),
                    help="quarters and/or YYYY-MM months")
    a = ap.parse_args()
    repos = []
    for line in Path(a.repos).read_text().splitlines():
        f = line.split("\t")[0].strip()
        if f and "/" in f and f != "repo":
            repos.append(f)
    pairs = [(r, p) for r in repos for p in a.periods]
    total_written = 0
    for i in range(0, len(pairs), BATCH):
        n = batch_counts(pairs[i:i + BATCH])
        total_written += n
        if n:
            time.sleep(1)
        if (i // BATCH) % 25 == 0:
            print(f"precount progress: {i + BATCH}/{len(pairs)} pairs", flush=True)
    print(f"DONE precount: {total_written} denominators written "
          f"({len(pairs)} pairs total)", flush=True)


if __name__ == "__main__":
    main()
