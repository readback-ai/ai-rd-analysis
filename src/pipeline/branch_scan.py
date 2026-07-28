"""Stage 3c — branch-prefix PR counts (detection layer C denominator-free).

For every (org, quarter, prefix) in the population, counts PRs whose head
branch matches an agent naming convention (detect.BRANCH_PREFIXES) via one
REST search per cell: `org:X is:pr head:<prefix> created:<range>`.

Why counts-first: search is capped at 1000 nodes per query, so
population-level rates come from counts (this stage) divided by precount
denominators, while PR-level metrics come from the org-stratified sample
(pull_prs.sample_branch_prs). (Historical origin: the census once lacked
headRefName; today per-PR layer C runs on the census directly and this
stage remains as admission evidence.) Q1-2024 is scanned too: agent branch prefixes
did not exist then, so a zero there is the built-in false-positive check
(measured: exactly 0 across all 210 orgs — v2_results §12).

Checkpointing: TSV append, one row per completed cell; reruns skip done cells.
A failed count is SKIPPED, never written as 0 (absence-of-evidence rule).

Usage:
  python -m pipeline.branch_scan --out data/derived/branch_scan.tsv
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from pipeline.detect import BRANCH_PREFIXES
from pipeline.ghx import graphql_nodes, rest_count
from pipeline.scan_orgs import QUARTER_RANGES

BATCH = 25   # aliased search sub-queries per GraphQL call


def _scoped_cell_count(repos: list[str], prefix: str,
                       rng: str) -> int | None:
    """Sum of per-repo branch-prefix counts for one (org, period, prefix)
    cell, batched via aliased GraphQL search (BATCH repos per call — a
    per-repo REST loop costs ~30x the wall clock on large conglomerates).
    None if ANY repo's count is missing: a partial sum understates
    silently."""
    total = 0
    for i in range(0, len(repos), BATCH):
        chunk = repos[i:i + BATCH]
        parts = [f'a{j}: search(query:"repo:{r} is:pr head:{prefix} '
                 f'created:{rng}", type:ISSUE){{ issueCount }}'
                 for j, r in enumerate(chunk)]
        data = graphql_nodes("query{ " + " ".join(parts) + " }", {},
                             ".data", expect=dict)
        if data is None:
            return None
        for j in range(len(chunk)):
            node = data.get(f"a{j}")
            if not (isinstance(node, dict)
                    and isinstance(node.get("issueCount"), int)):
                return None
            total += node["issueCount"]
    return total


def scan(orgs: list[str], out_path: Path, periods: dict[str, str],
         prefixes: dict[str, str], pace: float = 2.2,
         scoped: dict[str, list[str]] | None = None) -> None:
    """scoped maps repo-scoped orgs to their in-scope repos: their cells
    are counted per repo and summed — an org-wide query would count
    prefix PRs in out-of-scope repos into R4 admission evidence (R5).
    A cell with any failed per-repo count is skipped, never written
    partial (a partial sum understates silently)."""
    scoped = scoped or {}
    done: set[tuple[str, str, str]] = set()
    if out_path.exists():
        for ln in out_path.read_text().splitlines():
            f = ln.split("\t")
            if len(f) >= 3:
                done.add((f[0], f[1], f[2]))
    with out_path.open("a") as out:
        for org in orgs:
            for per, rng in periods.items():
                for prefix in prefixes.values():
                    if (org, per, prefix) in done:
                        continue
                    if org in scoped:
                        n = _scoped_cell_count(scoped[org], prefix, rng)
                        time.sleep(pace)
                    else:
                        n = rest_count(
                            f"org:{org} is:pr head:{prefix} created:{rng}",
                            endpoint="search/issues")
                        time.sleep(pace)
                    if n is None:
                        print(f"FAIL {org} {per} {prefix}", flush=True)
                        continue
                    out.write(f"{org}\t{per}\t{prefix}\t{n}\n")
                    out.flush()


def load(out_path: Path) -> dict[tuple[str, str, str], int]:
    """(org, period, prefix) -> PR count."""
    counts: dict[tuple[str, str, str], int] = {}
    for ln in out_path.read_text().splitlines():
        f = ln.split("\t")
        if len(f) == 4 and f[3].isdigit():
            counts[(f[0], f[1], f[2])] = int(f[3])
    return counts


def main() -> None:
    from pipeline.org_set import population, scoped_repos
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="data/derived/branch_scan.tsv")
    ap.add_argument("--periods", nargs="+", default=list(QUARTER_RANGES),
                    choices=list(QUARTER_RANGES))
    a = ap.parse_args()
    scan(population(), Path(a.out),
         {p: QUARTER_RANGES[p] for p in a.periods}, BRANCH_PREFIXES,
         scoped=scoped_repos())
    print("branch scan complete")


if __name__ == "__main__":
    main()
