"""Figure 8: do human review requests still produce edits? — by PR type.

Two broken-axis panels from the identified CLEAN lanes (no AI-reviewer
activity), each estimated on the manifest-bound sample whose design fits
its estimand (issue #2): (a) share of PRs with an explicit human ask whose
author subsequently edited — the UNWEIGHTED share of the equal-probability
sample (uniform inclusion cancels in the ratio); (b) share of post-ask LOC
in those PRs' commits — Horvitz-Thompson weighted over the PPS-by-LOC
sample. Dark = AI-involved PRs, light = non-AI. Each panel omits points
below n < 20 in ITS OWN sample (2026-07-25 review: the draws are
independent, so the AI lane can begin in a different quarter per panel).
Q2 partial (w8 windows open at the AS_OF).

Output: artifacts/fig8_responsiveness_by_ai.png
Usage:  PYTHONPATH=src python scripts/plot_fig8_responsiveness.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import (PAIR_BLUE, broken_pair, plt, quarter_series,
                               save, shade_q2_partial)
from pipeline.studies.review_action import PERIODS, lane_rows

SLICES = [("CLEAN+AI", PAIR_BLUE[0], "AI-involved PRs"),
          ("CLEAN+nonAI", PAIR_BLUE[1], "non-AI PRs")]


def val(lanes, per, lane, kind):
    """Each panel gates on ITS OWN design's sample count (2026-07-25
    review): responded% comes from the EQ draw (n), the LOC share from the
    PPS draw (n_loc). The draws are independent, so a lane can support one
    panel and not the other — gating both on n both crashed on empty PPS
    cells (0.0/0.0 on the defaultdict) and dropped supported LOC points."""
    a = lanes.get((per, lane))
    if not a:
        return None
    if kind == "responded":
        return 100 * a["wacted"] / a["wn"] if a["n"] >= 20 else None
    return (100 * a["post"] / a["total"]
            if a.get("n_loc", 0) >= 20 and a["total"] else None)


def main() -> None:
    _, lanes, _ = lane_rows()   # fleet-excluded domain

    fig = plt.figure(figsize=(11, 4.4))
    fig.suptitle("Figure 8: responsiveness to human review requests — AI vs "
                 "non-AI PRs (CLEAN lane; (a) equal-probability sample, "
                 "unweighted / (b) PPS-by-LOC, HT; fleet authors excluded)",
                 fontsize=11, y=-0.08)
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, kind, title in (
            (subfigs.flat[0], "responded", "% of asked PRs with author "
             "edits after the ask"),
            (subfigs.flat[1], "locshare", "% of LOC edited after the ask")):
        axl, axr = broken_pair(sf, title)
        for lane, color, label in SLICES:
            y = [val(lanes, p, lane, kind) for p in PERIODS]
            quarter_series(axl, axr, y, color, label)
        shade_q2_partial(axr)
        axl.set_ylim(0, 100)
        axl.set_ylabel(title)
        axr.legend(fontsize=8, loc="lower left")
    save(fig, "artifacts/fig8_responsiveness_by_ai.png")


if __name__ == "__main__":
    main()
