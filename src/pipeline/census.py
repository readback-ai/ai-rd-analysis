"""Stage 3 — PR census for the analysis repo set.

Pulls PR nodes (commits + reviews + authorAssociation + size) per repo x period.
Sampling: if a repo-period holds <= --cell-cap PRs it is fully censused in one
search call; otherwise the period is split into --subwindows uniform date
sub-windows of --cell-cap each (uniform-over-time, avoids window-tail bias).

Every cell is checkpointed to raw/census/ and only counted done if it parses
as a JSON array (rate-limit error objects are never written — see ghx).

Usage:
  python -m pipeline.census --repos repos.tsv \
      --periods Q1-2024 Q4-2025 Q1-2026 Q2-2026
"""
from __future__ import annotations

import argparse
import json
import time
from datetime import date, timedelta
from pathlib import Path

from pipeline.ghx import cell_path, cell_valid, graphql_nodes, rest_count
from pipeline.scan_orgs import QUARTER_RANGES

PR_QUERY = """
query($q:String!){ search(query:$q, type:ISSUE, first:50){
  nodes{ ... on PullRequest{ number createdAt mergedAt closedAt authorAssociation
    additions deletions changedFiles
    author{login __typename}
    commits(first:12){ nodes{ commit{ message authors(first:6){ nodes{ email } } } } }
    reviews(first:15){ nodes{ author{login __typename} submittedAt state
                              comments{totalCount} } } } } } }
"""


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


def pull_cell(repo: str, rng: str) -> list | None:
    p = cell_path("census", repo, rng)
    if cell_valid(p, list):
        return json.loads(p.read_text())
    nodes = graphql_nodes(PR_QUERY, {"q": f"repo:{repo} is:pr created:{rng} sort:created-desc"},
                          ".data.search.nodes", expect=list)
    if nodes is None:
        return None
    p.write_text(json.dumps(nodes))
    return nodes


def census_repo_period(repo: str, period: str, cell_cap: int, k: int) -> int | None:
    rng = QUARTER_RANGES[period]
    total = rest_count(f"repo:{repo} is:pr created:{rng}", endpoint="search/issues")
    time.sleep(2)
    if total is None:
        return None
    ranges = [rng] if total <= cell_cap else subwindows(rng, k)
    n = 0
    for r in ranges:
        nodes = pull_cell(repo, r)
        if nodes is None:
            return None
        n += len(nodes)
        time.sleep(1)
    return n


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", required=True,
                    help="TSV from enum_repos (col 1 = repo) or plain repo list")
    ap.add_argument("--periods", nargs="+", default=list(QUARTER_RANGES),
                    choices=list(QUARTER_RANGES))
    ap.add_argument("--cell-cap", type=int, default=50)
    ap.add_argument("--subwindows", type=int, default=10)
    a = ap.parse_args()
    repos = []
    for line in Path(a.repos).read_text().splitlines():
        f = line.split("\t")[0].strip()
        if f and "/" in f and f != "repo" and not f.endswith("/*"):
            repos.append(f)
    done = failed = 0
    for repo in repos:
        for per in a.periods:
            n = census_repo_period(repo, per, a.cell_cap, a.subwindows)
            if n is None:
                failed += 1
                print(f"FAIL {repo} {per}", flush=True)
            else:
                done += 1
                print(f"ok   {repo} {per}: {n} PRs", flush=True)
    print(f"census complete: {done} cells ok, {failed} failed (re-run to retry fails)")


if __name__ == "__main__":
    main()
