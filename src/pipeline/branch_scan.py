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


def verify_zeros(out_path: Path, periods: dict[str, str],
                 scoped: dict[str, list[str]],
                 pace: float = 1.0) -> None:
    """Second, temporally-independent observation of every scoped ZERO
    cell: a search brownout can return a structurally valid zero, so a
    zero only stands once re-observed (the precount confirm-zero rule).
    Rows whose recount is nonzero are corrected in place; recount
    failures leave the row untouched and are reported for the next
    run."""
    rows = []
    checked = corrected = failed = 0
    for ln in out_path.read_text().splitlines():
        f = ln.split("\t")
        if len(f) == 4 and f[0] in scoped and f[1] in periods \
                and f[3] == "0":
            checked += 1
            n = _scoped_cell_count(scoped[f[0]], f[2], periods[f[1]])
            time.sleep(pace)
            if n is None:
                failed += 1
                print(f"VERIFY FAIL {f[0]} {f[1]} {f[2]}", flush=True)
            elif n != 0:
                corrected += 1
                print(f"ZERO CORRECTED {f[0]} {f[1]} {f[2]}: 0 -> {n}",
                      flush=True)
                f[3] = str(n)
        rows.append("\t".join(f))
    tmp = out_path.with_suffix(".tmp")
    tmp.write_text("\n".join(rows) + "\n")
    tmp.replace(out_path)
    print(f"verify-zeros: {checked} checked, {corrected} corrected, "
          f"{failed} failed", flush=True)


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
    ap.add_argument("--verify-zeros", action="store_true")
    a = ap.parse_args()
    periods = {p: QUARTER_RANGES[p] for p in a.periods}
    if a.verify_zeros:
        verify_zeros(Path(a.out), periods, scoped_repos())
        return
    scan(population(), Path(a.out), periods, BRANCH_PREFIXES,
         scoped=scoped_repos())
    print("branch scan complete")


if __name__ == "__main__":
    main()
