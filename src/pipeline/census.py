"""Stage 3 — PR census for the analysis repo set.

Pulls PR nodes (commits + reviews + authorAssociation + size) per repo x period.
Sampling: if a repo-period holds <= PAGE_SIZE PRs it is fully censused in one
search call; otherwise the period is split into --subwindows uniform date
sub-windows of up to PAGE_SIZE each (uniform-over-time, avoids window-tail
bias). Collected-vs-total is checked and any undercount is WARNed — silent
truncation is how a census quietly becomes a biased sample.

Every cell is checkpointed to raw/census/ and only counted done if it parses
as a JSON array (rate-limit error objects are never written — see ghx).
Cached cells cost no network calls and no sleeps, so resume runs are fast.

Usage:
  python -m pipeline.census --repos repos.tsv \
      --periods Q1-2024 Q4-2025 Q1-2026 Q2-2026
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import date, timedelta
from pathlib import Path

from pipeline.ghx import cell_path, graphql_nodes, read_cell, rest_count
from pipeline.precount import get_precount
from pipeline.scan_orgs import QUARTER_RANGES

PAGE_SIZE = 50   # per-call PR fetch; the census cap per cell (single page, no pagination)
# Cell-store stage name. Versioned because the PR_QUERY changed (headRefName +
# mergedBy added): a cell's content depends on the query, so the cache key
# must too (ghx lesson). Cells pulled with the old query live in "census";
# analyze merges both stores, preferring census-v2.
STAGE = "census-v2"

# headRefName (detection layer C) and mergedBy (self-merge/accountability)
# were added 2026-07-08; cells pulled earlier lack them and downstream code
# must treat the fields as optional (detect.classify_pr does).
PR_QUERY = """
query($q:String!){ search(query:$q, type:ISSUE, first:%d){
  nodes{ ... on PullRequest{ number createdAt mergedAt closedAt authorAssociation
    additions deletions changedFiles headRefName
    author{login __typename} mergedBy{login __typename}
    commits(first:12){ nodes{ commit{ message
      authors(first:6){ nodes{ email } }
      committer{ email user{ login } } } } }
    reviews(first:15){ nodes{ author{login __typename} submittedAt state
                              comments{totalCount} } } } } } }
""" % PAGE_SIZE


def subwindows(rng: str, k: int) -> list[str]:
    """Split an inclusive date range into <=k contiguous sub-ranges that cover
    it exactly once (no gaps, no overlap, no inverted ranges). Integer
    boundaries — float `round()` (banker's rounding) produced inverted and
    duplicated windows on ranges shorter than k days."""
    s, e = (date.fromisoformat(x) for x in rng.split(".."))
    days = (e - s).days + 1
    k = max(1, min(k, days))
    bounds = [s + timedelta(days=(i * days) // k) for i in range(k)]
    bounds.append(e + timedelta(days=1))
    out = []
    for a, nxt in zip(bounds, bounds[1:]):
        b = nxt - timedelta(days=1)
        if a <= b:
            out.append(f"{a}..{b}")
    return out


def pull_cell(repo: str, rng: str) -> tuple[list | None, bool]:
    """-> (nodes, was_cached). Cached hits cost no network and need no pacing."""
    p = cell_path(STAGE, repo, rng)
    cached = read_cell(p, list)
    if cached is not None:
        return cached, True
    nodes = graphql_nodes(PR_QUERY, {"q": f"repo:{repo} is:pr created:{rng} sort:created-desc"},
                          ".data.search.nodes", expect=list)
    if nodes is None:
        return None, False
    p.write_text(json.dumps(nodes))
    return nodes, False


def census_repo_period(repo: str, period: str, k: int) -> int | None:
    rng = QUARTER_RANGES[period]
    # fully-cached fast path: a valid full-range cell needs no denominator call
    cached = read_cell(cell_path(STAGE, repo, rng), list)
    if cached is not None:
        return len(cached)
    total = get_precount(repo, period)          # batch-precounted (GraphQL)
    if total is None:                            # fall back to REST search
        total = rest_count(f"repo:{repo} is:pr created:{rng}", endpoint="search/issues")
        time.sleep(2)
    if total is None:
        return None
    ranges = [rng] if total <= PAGE_SIZE else subwindows(rng, k)
    n = 0
    for r in ranges:
        nodes, was_cached = pull_cell(repo, r)
        if nodes is None:
            return None
        n += len(nodes)
        if not was_cached:
            time.sleep(1)
    if n < total:
        print(f"WARN {repo} {period}: collected {n}/{total} PRs "
              f"(sub-window saturation) — raise --subwindows to recover",
              file=sys.stderr, flush=True)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", required=True,
                    help="TSV from enum_repos (col 1 = repo) or plain repo list")
    ap.add_argument("--periods", nargs="+", default=list(QUARTER_RANGES),
                    choices=list(QUARTER_RANGES))
    ap.add_argument("--subwindows", type=int, default=10)
    a = ap.parse_args()
    repos = []
    for line in Path(a.repos).read_text().splitlines():
        f = line.split("\t")[0].strip()
        if f and "/" in f and f != "repo":
            repos.append(f)
    done = failed = 0
    for repo in repos:
        for per in a.periods:
            n = census_repo_period(repo, per, a.subwindows)
            if n is None:
                failed += 1
                print(f"FAIL {repo} {per}", flush=True)
            else:
                done += 1
                print(f"ok   {repo} {per}: {n} PRs", flush=True)
    print(f"census complete: {done} cells ok, {failed} failed (re-run to retry fails)")


if __name__ == "__main__":
    main()
