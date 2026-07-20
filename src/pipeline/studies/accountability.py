"""Study: who is accountable for merged AI code? (v2_results §11–§11c)

Two designs, both hydrating mergedBy + comment authors via pull_prs.batch_pull
(census cells before 2026-07-08 lack those fields):

1. self-merge lane (§11b): per period, sample merged human-authored PRs
   UNCONDITIONED on review status; split by mergedBy==author; report AI-code
   rate, human-review rate (reviewer!=author), AI-review rate per lane.
2. accountability cohorts (§11): within merged-without-human-review cohorts,
   measure self-merge share, other-human comment engagement, and one-person
   accountability (self-merged AND no other-human comment).

Usage:
  python -m pipeline.studies.accountability --per-period 250 --seed 13
"""
from __future__ import annotations

import argparse
import random

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import MARKERS, classify_pr
from pipeline.pull_prs import batch_pull
from pipeline.scan_orgs import QUARTER_RANGES

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]


def sample_merged_human(per_period: int, seed: int) -> dict[str, list[tuple[str, dict]]]:
    random.seed(seed)
    grouped = group_by_period(load_cells(), QUARTER_RANGES)
    pools: dict[str, list[tuple[str, dict]]] = {p: [] for p in PERIODS}
    for (repo, per), prs in grouped.items():
        if per not in pools:
            continue
        for p in prs:
            if (p.get("author") or {}).get("__typename") != "Bot" and p.get("mergedAt"):
                pools[per].append((repo, p))
    return {per: random.sample(pool, min(per_period, len(pool)))
            for per, pool in pools.items()}


def other_human_commented(pr: dict) -> bool:
    author = (pr.get("author") or {}).get("login")
    return any((c.get("author") or {}).get("__typename") == "User"
               and (c.get("author") or {}).get("login") != author
               for c in (pr.get("comments") or {}).get("nodes") or [])


def run(per_period: int, seed: int) -> None:
    samples = sample_merged_human(per_period, seed)
    refs = [(repo, pr["number"]) for prs in samples.values() for repo, pr in prs]
    hydrated = batch_pull(refs)
    print(f"hydrated {len(hydrated)}/{len(refs)} PRs\n")
    print(f"{'period':9}{'lane':13}{'n':>5}{'share':>7}{'AIcode%':>9}"
          f"{'humRev%':>9}{'AIrev%':>8}{'1person%':>10}")
    for per, prs in samples.items():
        rows = []
        for repo, pr in prs:
            full = hydrated.get((repo, pr["number"]))
            if not full:
                continue
            c = classify_pr(full, MARKERS)
            if c.self_merged is None:
                continue
            rows.append((c, other_human_commented(full)))
        if not rows:
            continue
        for label, flag in (("SELF-merged", True), ("other-merged", False)):
            lane = [(c, eng) for c, eng in rows if c.self_merged == flag]
            if len(lane) < 10:
                continue
            n = len(lane)
            one = sum(1 for c, eng in lane
                      if flag and not c.human_reviewed and not eng)
            print(f"{per:9}{label:13}{n:>5}{100*n/len(rows):>6.0f}%"
                  f"{100*sum(bool(c.marker_tools) for c, _ in lane)/n:>8.1f}%"
                  f"{100*sum(c.human_reviewed for c, _ in lane)/n:>8.1f}%"
                  f"{100*sum(c.ai_reviewed for c, _ in lane)/n:>7.1f}%"
                  f"{100*one/n:>9.1f}%")
        ai_self = [(c, eng) for c, eng in rows if c.self_merged and c.marker_tools]
        if len(ai_self) >= 10:
            n = len(ai_self)
            print(f"{'':9}{'self+AIcode':13}{n:>5}{'':7}{'':9}"
                  f"{100*sum(c.human_reviewed for c, _ in ai_self)/n:>8.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-period", type=int, default=250)
    ap.add_argument("--seed", type=int, default=13)
    a = ap.parse_args()
    run(a.per_period, a.seed)


if __name__ == "__main__":
    main()
