"""Study: exact per-PR decomposition of AI involvement across the three
detection layers, pooled over the population manifest.

Layers are made DISJOINT by precedence B > A > C (agent authorship is the
strongest single signal; a marker on an agent-authored PR attributes to B):

  B  agent-authored       detect.pr_agent_author
  A' marker, not B        detect.pr_ai_tools
  C' branch, not A/B      detect.pr_branch_tool
  union = ai_involved     (the primary metric)

All three layers are observed per-PR inside the census (headRefName +
commits + author in every cell), so the decomposition is exact on one
population — no cross-source denominators or sampled overlap corrections.
(The sampled-blending machinery this replaced lived in pipeline.integrate,
removed 2026-07-20.)

Usage:  python -m pipeline.studies.layers [--granularity month]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from pathlib import Path

from pipeline.analyze import extended_quarters, group_by_period, load_cells
from pipeline.detect import MARKERS, classify_pr

DRV = Path("data/derived")
PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]


def layered_table(granularity: str = "quarter") -> None:
    keep = set((DRV / "population_repos.txt").read_text().split())
    grouped = group_by_period(load_cells(), extended_quarters(), granularity)
    if not grouped:
        raise SystemExit("no census cells in $AIRD_DATA_DIR — refusing to "
                         "print an empty decomposition")
    agg: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (repo, per), prs in grouped.items():
        if repo not in keep:
            continue
        d = agg[per]
        for p in prs:
            d["n"] += 1
            c = classify_pr(p, MARKERS)
            if c.agent_author:
                d["b"] += 1
            elif c.marker_tools:
                d["a"] += 1
            elif c.branch_tool:
                d["c"] += 1
    periods = PERIODS if granularity == "quarter" else \
        sorted({p for (_, p) in grouped})
    print(f"{'period':9}{'PRs':>8}{'A marker%':>10}{'B agent%':>9}"
          f"{'C branch%':>10}{'union%':>8}")
    for per in periods:
        d = agg.get(per)
        if not d or not d["n"]:
            continue
        n = d["n"]
        print(f"{per:9}{n:>8}{100*d['a']/n:>9.2f}%{100*d['b']/n:>8.2f}%"
              f"{100*d['c']/n:>9.2f}%{100*(d['a']+d['b']+d['c'])/n:>7.2f}%")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--granularity", choices=["quarter", "month"],
                    default="quarter")
    layered_table(ap.parse_args().granularity)
