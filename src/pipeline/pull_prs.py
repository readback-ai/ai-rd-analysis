"""Targeted PR pulls beyond the census: batch hydration + branch-PR sampling.

Two collection helpers that later analyses (accountability §11, integration
§12) need and the census cells cannot provide:

- batch_pull(refs, fields): hydrate specific PRs by (repo, number) via aliased
  GraphQL (10 PRs per call) — used for fields the census never fetched
  (mergedBy, comment authors, per-commit committedDate).
- sample_branch_prs(prefix, ...): org-stratified sample of branch-prefix PRs
  (detection layer C): one 50-PR page per (org, quarter) with a nonzero
  branch_scan count, checkpointed one JSON cell per org-quarter. Estimators
  weight each org's sampled PRs by its population count (pop_count in the
  cell), so unequal org sizes don't bias pooled metrics. Known limitation:
  pages are created-desc — a mild within-quarter recency bias, documented in
  v2_results §12 caveats.

Both are checkpointed and resume-safe like every other stage.
"""
from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

from pipeline.ghx import graphql_nodes
from pipeline.scan_orgs import QUARTER_RANGES

# Superset of census PR fields + the fields only targeted pulls have.
PR_FIELDS = """
number headRefName createdAt mergedAt closedAt authorAssociation
additions deletions changedFiles
repository{ nameWithOwner }
author{login __typename} mergedBy{login __typename}
commits(first:12){ nodes{ commit{ message committedDate
  authors(first:6){ nodes{ email } }
  committer{ email user{ login } } } } }
reviews(first:15){ nodes{ author{login __typename} submittedAt state
                          comments{totalCount} } }
comments(first:40){ nodes{ author{login __typename} } }
"""

SEARCH_QUERY = ("query($q:String!){ search(query:$q, type:ISSUE, first:50){"
                " nodes{ ... on PullRequest{ %s } } } }" % PR_FIELDS)


def batch_pull(refs: list[tuple[str, int]], pace: float = 0.8,
               batch: int = 10) -> dict[tuple[str, int], dict]:
    """Hydrate PRs by (repo, number). Missing/failed PRs are absent from the
    result (never faked); callers decide how to handle gaps."""
    out: dict[tuple[str, int], dict] = {}
    for i in range(0, len(refs), batch):
        chunk = refs[i:i + batch]
        parts = []
        for j, (repo, num) in enumerate(chunk):
            owner, name = repo.split("/", 1)
            parts.append(f'a{j}: repository(owner:"{owner}", name:"{name}")'
                         f'{{ pullRequest(number:{num}){{ {PR_FIELDS} }} }}')
        data = graphql_nodes("query{ " + " ".join(parts) + " }", {},
                             ".data", expect=dict)
        for j, ref in enumerate(chunk):
            node = (data or {}).get(f"a{j}") or {}
            pr = node.get("pullRequest") if isinstance(node, dict) else None
            if pr:
                out[ref] = pr
        time.sleep(pace)
    return out


def _repo_chunks(repos: list[str], budget: int = 180) -> list[list[str]]:
    """Split a repo list so each 'repo:a repo:b ...' clause fits GitHub's
    256-char search-query limit alongside the fixed qualifiers."""
    chunks: list[list[str]] = []
    cur: list[str] = []
    used = 0
    for r in repos:
        cost = len("repo:") + len(r) + 1
        if cur and used + cost > budget:
            chunks.append(cur)
            cur, used = [], 0
        cur.append(r)
        used += cost
    if cur:
        chunks.append(cur)
    return chunks


def sample_branch_prs(prefix: str, scan_path: Path, out_dir: Path,
                      periods: list[str], pace: float = 1.5,
                      in_scope: dict[str, set[str]] | None = None) -> None:
    """One 50-PR page per org-quarter with branch_scan count > 0.
    in_scope maps repo-scoped orgs to their in-scope repos (R5). Their
    universe is queried per repo chunk BEFORE the 50-newest cap — an
    org-wide page could exhaust its 50 slots on out-of-scope PRs and
    checkpoint an empty cell against a positive scoped pop_count. Scoped
    cells carry universe='scoped'; an existing cell without it was drawn
    org-wide (biased selection, org-wide weight) and is re-drawn."""
    from pipeline.branch_scan import load
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = load(scan_path)
    todo = sorted(((org, per, n) for (org, per, pfx), n in counts.items()
                   if pfx == prefix and per in periods and n > 0),
                  key=lambda t: -t[2])
    for org, per, n in todo:
        cell = out_dir / f"{org}__{per}.json"
        keep = in_scope.get(org) if in_scope else None
        if cell.exists():
            if keep is None:
                continue
            if json.loads(cell.read_text()).get("universe") == "scoped":
                continue
        rng = QUARTER_RANGES[per]
        if keep is not None:
            nodes = []
            for chunk in _repo_chunks(sorted(keep)):
                repos_q = " ".join(f"repo:{r}" for r in chunk)
                got = graphql_nodes(
                    SEARCH_QUERY,
                    {"q": f"{repos_q} is:pr head:{prefix} created:{rng} "
                          f"sort:created-desc"},
                    ".data.search.nodes", expect=list)
                if got is None:
                    nodes = None
                    break
                nodes.extend(got)
                time.sleep(pace)
            if nodes is not None:
                nodes = [p for p in nodes
                         if ((p.get("repository") or {})
                             .get("nameWithOwner") in keep)]
                nodes.sort(key=lambda p: p.get("createdAt") or "",
                           reverse=True)
                nodes = nodes[:50]
        else:
            nodes = graphql_nodes(
                SEARCH_QUERY,
                {"q": f"org:{org} is:pr head:{prefix} created:{rng} "
                      f"sort:created-desc"},
                ".data.search.nodes", expect=list)
        if nodes is None:
            print(f"FAIL {org} {per}", flush=True)
            continue
        payload = {"org": org, "period": per, "pop_count": n, "prs": nodes}
        if keep is not None:
            payload["universe"] = "scoped"
        cell.write_text(json.dumps(payload))
        print(f"ok {org} {per}: {len(nodes)}/{n}", flush=True)
        time.sleep(pace)


def load_branch_samples(out_dir: Path) -> list[dict]:
    """All sample cells for one prefix: [{org, period, pop_count, prs}]."""
    cells = []
    for f in sorted(out_dir.glob("*.json")):
        try:
            cells.append(json.loads(f.read_text()))
        except json.JSONDecodeError:
            continue
    return cells


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--prefix", required=True, help="e.g. codex/")
    ap.add_argument("--scan", default="data/derived/branch_scan.tsv")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--periods", nargs="+",
                    default=["Q4-2025", "Q1-2026", "Q2-2026"])
    a = ap.parse_args()
    from pipeline.org_set import scoped_repos
    sample_branch_prs(a.prefix, Path(a.scan), Path(a.out_dir), a.periods,
                      in_scope={o: set(rs)
                                for o, rs in scoped_repos().items()})


if __name__ == "__main__":
    main()
