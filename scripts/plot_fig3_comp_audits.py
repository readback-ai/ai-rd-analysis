"""Figure 3 companion (comp audits): who still gets human review, and how
much attention per line — AI-involved vs non-AI vs fleet-operator PRs.

Left: % of mature merged PRs with a human (reviewer != author) review.
Right: human comments per kLOC on mature merged human-reviewed PRs.
Slices: AI-involved and non-AI PRs (fleet-operator authors excluded) plus
fleet-operator PRs as their own series. AI series absent at the Q1-2024
baseline by construction; Q2 partial (w8 windows open at the AS_OF).

Output: artifacts/figure_3_comp_audits.png
Usage:  PYTHONPATH=src python scripts/plot_fig3_comp_audits.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import (PAIR_BLUE, PAIR_ORANGE, broken_pair, cell,
                               plt, quarter_series, save, shade_q2_partial)
from pipeline.studies.attention import attention_by_ai
from pipeline.studies.productivity import PERIODS, review_mix

SLICES = [("ai", PAIR_BLUE[0], "AI-involved PRs"),
          ("nonai", PAIR_BLUE[1], "non-AI PRs"),
          ("fleet", PAIR_ORANGE[0], "fleet-operator PRs")]


def main() -> None:
    mix = review_mix(by="ai", fleet_slice=True)
    att = attention_by_ai(fleet_slice=True)
    fig = plt.figure(figsize=(11, 4.4))
    fig.suptitle("Figure 3 companion: human review coverage and attention "
                 "per line, by PR type", fontsize=12, y=-0.08)
    subfigs = fig.subfigures(1, 2, wspace=0.05)

    # figstyle.cell suppresses the ai slice at the Q1-2024 baseline (zero
    # denominator) even if a stray detector FP creates a tiny cell
    axl, axr = broken_pair(subfigs.flat[0],
                           "% of merged PRs human-reviewed")
    for sl, color, label in SLICES:
        y = [cell(mix, p, sl, "humanRev_pr", scale=100) for p in PERIODS]
        quarter_series(axl, axr, y, color, label)
    shade_q2_partial(axr)
    axl.set_ylim(0, 100)
    axl.set_ylabel("% of merged PRs human-reviewed")
    axr.legend(fontsize=8, loc="lower left")

    axl, axr = broken_pair(subfigs.flat[1], "human comments per kLOC")
    for sl, color, label in SLICES:
        y = [cell(att, p, sl, "comments_per_kloc") for p in PERIODS]
        quarter_series(axl, axr, y, color, label)
    shade_q2_partial(axr)
    axl.set_ylim(bottom=0)
    axl.set_ylabel("human comments per kLOC")
    axr.legend(fontsize=8, loc="upper right")

    save(fig, "artifacts/figure_3_comp_audits.png")


if __name__ == "__main__":
    main()
