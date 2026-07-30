"""Stage 3 — PR census for the analysis repo set.

Pulls PR nodes (commits + reviews + authorAssociation + size) per repo x period.
Sampling: if a repo-period holds <= PAGE_SIZE PRs it is fully censused in one
search call; otherwise the period is split into --subwindows uniform date
sub-windows of up to PAGE_SIZE each (uniform-over-time, avoids window-tail
bias). Collected-vs-total is checked and any undercount is WARNed — silent
truncation is how a census quietly becomes a biased sample.

Every cell is checkpointed and only counted done if it parses as a JSON
array (rate-limit error objects are never written — see ghx); writes are
atomic. Cached cells cost no network calls and no sleeps, so resume runs are
fast. Known cache-poisoning mode: during degraded search moments GitHub can
return HTTP 200 with EMPTY result sets, which are valid JSON and get cached;
the per-repo-period completeness gate catches this as a deterministic
deficit — the remedy is wiping that period's cells so they re-pull.

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

from pipeline.ghx import cell_path, graphql_nodes, read_cell
from pipeline.precount import confirm_zero_precount, ensure_precount
from pipeline.scan_orgs import QUARTER_RANGES, resolve_period

PAGE_SIZE = 50   # PRs per GraphQL call; _paginate cursors to the API's
                 # 1,000-node cap per search window
# Cell-store stage name. The "-v2" suffix is historical: it encodes the
# query version, because a cell's CONTENT depends on the query that pulled
# it; this is the single store now (analyze.load_cells reads only census-v2).
STAGE = "census-v2"

PR_QUERY = """
query($q:String!, $cur:String){ search(query:$q, type:ISSUE, first:%d, after:$cur){
  pageInfo{ hasNextPage endCursor }
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


def _paginate(q: str, page_size: int) -> list | None:
    """Cursor-paginate one window up to the search API's 1,000-node cap."""
    query = PR_QUERY if page_size == PAGE_SIZE else \
        PR_QUERY.replace(f"first:{PAGE_SIZE}", f"first:{page_size}")
    nodes: list = []
    cur = None
    for _ in range(-(-1000 // page_size)):
        variables = {"q": q, **({"cur": cur} if cur else {})}
        page = graphql_nodes(query, variables, ".data.search", expect=dict)
        if page is None:
            return None
        nodes.extend(n for n in page.get("nodes") or [])
        pi = page.get("pageInfo") or {}
        # Terminate ONLY on an explicit false: a missing/null pageInfo is what
        # a partial or errored response looks like, and reading it as "no more
        # pages" returned a TRUNCATED window that pull_cell then cached as a
        # finished cell (issue #3 item 3, same rule as _conn_commits).
        if pi.get("hasNextPage") is False:
            return nodes
        if pi.get("hasNextPage") is not True:
            return None                  # partial response: fail, don't cache
        cur = pi.get("endCursor")
        time.sleep(1)
    return nodes


def pull_cell(repo: str, rng: str) -> tuple[list | None, bool]:
    """-> (nodes, was_cached). Cached hits cost no network and need no pacing.
    Paginates within the window via search cursors. Windows whose 50-PR pages
    make GraphQL time out server-side (HTTP 502 — pathological payloads such
    as giant commit messages) are retried with 5-PR pages: slower, but it is
    the difference between pytorch/pytorch Q4-2025 completing and failing."""
    p = cell_path(STAGE, repo, rng)
    cached = read_cell(p, list)
    if cached is not None:
        return cached, True
    q = f"repo:{repo} is:pr created:{rng} sort:created-desc"
    nodes = _paginate(q, PAGE_SIZE)
    if nodes is None:
        print(f"RETRY {repo} {rng}: small pages (502 dodge)",
              file=sys.stderr, flush=True)
        nodes = _paginate(q, 5)
    if nodes is None:
        return None, False
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(nodes))       # json.dumps output is valid JSON;
    tmp.replace(p)                          # atomic rename => complete-or-absent
    return nodes, False


def _direct_or_none(repo: str, period: str) -> int | None:
    """Last resort on ANY definitive search-route failure: a repo the
    search index refuses (HTTP 422) is invisible to every search-based
    route, whatever the precount cache happens to hold — a cached
    positive keeps failing the pull, and a cached zero can never be
    confirmed, since the confirming recount uses the same refused search.
    Collect it through the object API instead. Only the DEFINITIVE
    refusal qualifies: a transient failure still fails the period rather
    than silently switching collection routes."""
    from pipeline import census_direct
    if not census_direct.repo_unsearchable(repo):
        return None
    written = census_direct.census_repo_direct(repo)
    return None if written is None else written.get(period)


def census_repo_period(repo: str, period: str, k: int) -> int | None:
    """k is a FLOOR on sub-windows; the actual count adapts to the repo's
    PR volume (ceil(total/45) with 10% headroom, capped at one window per
    day) so a quarter is never silently capped at k*PAGE_SIZE PRs. If the
    adaptive windows still saturate (sub-day burstiness), the repo-period
    FAILS — an incomplete census must be visible, not a warning
    (external review finding 4)."""
    rng = resolve_period(period)
    total = ensure_precount(repo, period)   # cached, or queried+cache-written
    if total is None:
        return _direct_or_none(repo, period)
    if total == 0:
        # 0 passes both completeness gates trivially, so it may not stand
        # on a single observation — a browned-out search looks identical.
        total = confirm_zero_precount(repo, period)
        if total is None:
            return _direct_or_none(repo, period)
    # fully-cached fast path — only when the cache satisfies the same
    # drift allowance as fresh pulls; a brownout-poisoned empty cached as
    # valid must fall through to the self-heal path (external review P1)
    cached = read_cell(cell_path(STAGE, repo, rng), list)
    if cached is not None \
            and (len(cached) >= total * 0.98 or total - len(cached) <= 3):
        return len(cached)
    k = max(k, -(-total * 11 // (10 * (PAGE_SIZE - 5))))   # ceil w/ headroom
    ranges = [rng] if total <= PAGE_SIZE else subwindows(rng, k)
    for attempt in (0, 1):
        n = 0
        failed = False
        for r in ranges:
            nodes, was_cached = pull_cell(repo, r)
            if nodes is None:
                failed = True
                break
            n += len(nodes)
            if not was_cached:
                time.sleep(1)
        if not failed and (n >= total * 0.98 or total - n <= 3):
            # percentage AND absolute allowance: PRs deleted after the
            # precount snapshot make small deficits permanent drift
            return n
        if attempt == 0:
            # SELF-HEAL: cached cells can be silently incomplete (search
            # brownouts return 200 with empty results, which cache as valid
            # empties). Invalidate this period's cells and re-pull once
            # before declaring failure.
            print(f"HEAL {repo} {period}: collected {n}/{total}; "
                  f"invalidating {len(ranges)} cells and re-pulling",
                  file=sys.stderr, flush=True)
            for r in {*ranges, rng}:      # incl. stale full-range cell
                p = cell_path(STAGE, repo, r)
                if p.exists():
                    p.unlink()
            time.sleep(60)   # brownouts are minutes-scale; an immediate
                             # re-pull would likely hit the same one
    reason = "window pull failed" if failed else "count deficit"
    print(f"FAIL {repo} {period}: collected {n}/{total} PRs with "
          f"{len(ranges)} sub-windows after a fresh re-pull ({reason})",
          file=sys.stderr, flush=True)
    return _direct_or_none(repo, period)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", required=True,
                    help="TSV from enum_repos (col 1 = repo) or plain repo list")
    ap.add_argument("--periods", nargs="+", default=list(QUARTER_RANGES),
                    help="quarter keys (Q2-2026) and/or months (2026-07)")
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
    if failed:
        sys.exit(1)          # incomplete collection must not look successful


if __name__ == "__main__":
    main()
