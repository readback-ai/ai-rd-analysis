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


def sample_branch_prs(prefix: str, scan_path: Path, out_dir: Path,
                      periods: list[str], pace: float = 1.5) -> None:
    """One 50-PR page per org-quarter with branch_scan count > 0."""
    from pipeline.branch_scan import load
    out_dir.mkdir(parents=True, exist_ok=True)
    counts = load(scan_path)
    todo = sorted(((org, per, n) for (org, per, pfx), n in counts.items()
                   if pfx == prefix and per in periods and n > 0),
                  key=lambda t: -t[2])
    for org, per, n in todo:
        cell = out_dir / f"{org}__{per}.json"
        if cell.exists():
            continue
        rng = QUARTER_RANGES[per]
        nodes = graphql_nodes(
            SEARCH_QUERY,
            {"q": f"org:{org} is:pr head:{prefix} created:{rng} sort:created-desc"},
            ".data.search.nodes", expect=list)
        if nodes is None:
            print(f"FAIL {org} {per}", flush=True)
            continue
        cell.write_text(json.dumps(
            {"org": org, "period": per, "pop_count": n, "prs": nodes}))
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
    ap.add_argument("--scan", default="data/resume_state/v2/branch_scan.tsv")
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--periods", nargs="+",
                    default=["Q4-2025", "Q1-2026", "Q2-2026"])
    a = ap.parse_args()
    sample_branch_prs(a.prefix, Path(a.scan), Path(a.out_dir), a.periods)


if __name__ == "__main__":
    main()
