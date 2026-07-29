"""Direct (non-search) census route for UNSEARCHABLE repos.

GitHub's search index refuses some public repos outright — `repo:X` search
answers HTTP 422 "the listed users and repositories cannot be searched"
— while the same repos serve their PRs happily through the object APIs.
Every search-based route (precount, census cells, branch counts) is blind
to them, so they can never be collected and their real PRs would either
fail the run forever or be waived as "inaccessible", which biases the
population against exactly these repos (new, small, AI-tooling-heavy).

This module collects such a repo through `repository.pullRequests`, which
does not touch the search index, and writes normal census cells so the
frame cannot tell the difference.

Completeness rule: no precount exists for an unsearchable repo, so the
connection's own `totalCount` is the denominator — the full history must
arrive, verified page by page, or NOTHING is written. Quarters with no
PRs get a cell that is a VERIFIED empty (stronger evidence than a search
zero, which cannot distinguish empty from browned-out).

Usage:
  python -m pipeline.census_direct --repos <file>   # collect all listed
  python -m pipeline.census_direct --probe <file>   # only report which
                                                    # repos are unsearchable
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from pipeline.census import PAGE_SIZE, STAGE
from pipeline.ghx import cell_path, graphql_nodes, read_cell, search_error
from pipeline.scan_orgs import QUARTER_RANGES, resolve_period

MAX_PRS = 2_000        # the fallback is for SMALL unsearchable repos; a
                       # huge history must fail loudly, not page for hours
UNSEARCHABLE = "cannot be searched"

# Same per-PR field set as census.PR_QUERY — a direct cell must be
# indistinguishable to the frame from a search-collected one.
PR_FIELDS = """
number createdAt mergedAt closedAt authorAssociation
additions deletions changedFiles headRefName
author{login __typename} mergedBy{login __typename}
commits(first:12){ nodes{ commit{ message
  authors(first:6){ nodes{ email } }
  committer{ email user{ login } } } } }
reviews(first:15){ nodes{ author{login __typename} submittedAt state
                          comments{totalCount} } }
"""

PRS_QUERY = """
query($owner:String!, $name:String!, $cur:String){
  repository(owner:$owner, name:$name){
    pullRequests(first:%d, after:$cur, orderBy:{field:CREATED_AT,
                                                direction:ASC}){
      totalCount
      pageInfo{ hasNextPage endCursor }
      nodes{ %s } } } }
""" % (PAGE_SIZE, PR_FIELDS)


def repo_unsearchable(repo: str) -> bool:
    """True only for the DEFINITIVE 422 answer. Any other failure (502,
    rate limit, timeout) is transient and must not be mistaken for a
    permanent property of the repo."""
    err = search_error(f"repo:{repo} is:pr")
    return bool(err) and UNSEARCHABLE in err


def pull_repo_prs(repo: str) -> list[dict] | None:
    """The repo's FULL PR history via the object API. None = incomplete
    (partial page, totalCount disagreement, oversized history, or a
    failed request) — callers must write nothing."""
    owner, name = repo.split("/", 1)
    nodes: list[dict] = []
    cur = None
    total = None
    # BOUNDED: enough pages for MAX_PRS and no more. An unbounded loop
    # never terminates when the API keeps answering hasNextPage:true with
    # a repeating cursor.
    for _ in range(-(-MAX_PRS // PAGE_SIZE) + 1):
        variables = {"owner": owner, "name": name,
                     **({"cur": cur} if cur else {})}
        conn = graphql_nodes(PRS_QUERY, variables,
                            ".data.repository.pullRequests", expect=dict)
        if conn is None:
            return None
        total = conn.get("totalCount")
        if not isinstance(total, int) or total > MAX_PRS:
            return None
        nodes.extend(conn.get("nodes") or [])
        pi = conn.get("pageInfo") or {}
        if pi.get("hasNextPage") is False:
            break
        if pi.get("hasNextPage") is not True:
            return None            # partial response: never "last page"
        cur = pi.get("endCursor")
        if not cur:
            return None            # would loop on the first page
        time.sleep(1)
    else:
        return None                # page budget exhausted: incomplete
    if len(nodes) != total:
        return None                # the API's own count is the denominator
    return nodes


def census_repo_direct(repo: str) -> dict[str, int] | None:
    """Collect the repo and write one cell per study quarter (keyed by the
    full quarter range, so coverage sees gap-free coverage). Returns
    {period: pr_count} written, or None when the history was incomplete.
    Existing valid cells are left alone."""
    periods = [p for p in QUARTER_RANGES if p != "Q3-2025"]
    prs = pull_repo_prs(repo)
    if prs is None:
        return None
    buckets: dict[str, list[dict]] = {p: [] for p in periods}
    for pr in prs:
        created = (pr.get("createdAt") or "")[:10]
        for per in periods:
            a, b = resolve_period(per).split("..")
            if a <= created <= b:
                buckets[per].append(pr)
                break
    out: dict[str, int] = {}
    for per, cell_prs in buckets.items():
        p = cell_path(STAGE, repo, resolve_period(per))
        if read_cell(p, list) is None:
            tmp = p.with_suffix(".tmp")
            tmp.write_text(json.dumps(cell_prs))
            tmp.replace(p)
        out[per] = len(cell_prs)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", help="file of owner/repo lines to collect")
    ap.add_argument("--probe", help="file of owner/repo lines to classify")
    a = ap.parse_args()
    path = Path(a.repos or a.probe)
    repos = [ln.strip() for ln in path.read_text().splitlines()
             if ln.strip()]
    unsearchable = []
    for repo in repos:
        if repo_unsearchable(repo):
            unsearchable.append(repo)
            print(f"UNSEARCHABLE {repo}", flush=True)
    print(f"{len(unsearchable)}/{len(repos)} unsearchable", flush=True)
    if a.probe:
        return
    failed = []
    for repo in unsearchable:
        written = census_repo_direct(repo)
        if written is None:
            failed.append(repo)
            print(f"FAIL {repo} (incomplete history; nothing written)",
                  flush=True)
        else:
            print(f"ok   {repo}: {written}", flush=True)
    if failed:
        raise SystemExit(f"{len(failed)} repos incomplete: {failed[:5]}")


if __name__ == "__main__":
    main()
