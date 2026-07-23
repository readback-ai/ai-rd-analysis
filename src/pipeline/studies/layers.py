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

from pipeline.analyze import extended_quarters
from pipeline.frame import PERIODS, study_frame


def layered_table(granularity: str = "quarter") -> None:
    agg: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for f in study_frame("all", periods=None, ranges=extended_quarters(),
                         granularity=granularity):
        d = agg[f.period]
        d["n"] += 1
        if f.cls.agent_author:
            d["b"] += 1
        elif f.cls.marker_tools:
            d["a"] += 1
        elif f.cls.branch_tool:
            d["c"] += 1
    if not agg:
        raise SystemExit("no census cells for the population in "
                         "$AIRD_DATA_DIR — refusing to print an empty "
                         "decomposition")
    periods = PERIODS if granularity == "quarter" else sorted(agg)
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
