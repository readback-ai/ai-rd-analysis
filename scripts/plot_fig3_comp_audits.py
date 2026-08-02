"""Figure 3 companion (comp audits): who still gets human review, and how
much attention per line — AI-involved vs non-AI vs fleet-operator PRs.

Left: % of mature merged PRs with a human (reviewer != author) review.
Right: human comments per kLOC on mature merged human-reviewed PRs.
MONTHLY rates over the Q1-2024 baseline months and the window months
that have passed w8 finalization at the AS_OF (through 2026-05 at AS_OF
2026-08-01; still-open months are excluded rather than shaded, so
nothing plotted is provisional). Slices: AI-involved and non-AI PRs
(fleet-operator authors excluded) plus fleet-operator PRs as their own
series. AI series absent at the Q1-2024 baseline by construction.

Output: artifacts/figure_3_comp_audits.png
Usage:  PYTHONPATH=src python scripts/plot_fig3_comp_audits.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import (BASELINE, PAIR_BLUE, PAIR_ORANGE, WINDOW,
                               broken_pair, cell, month_series, plt, save)
from pipeline.studies.attention import attention_by_ai
from pipeline.studies.productivity import month_w8_mature, review_mix

SLICES = [("ai", PAIR_BLUE[0], "AI-involved PRs"),
          ("nonai", PAIR_BLUE[1], "non-AI PRs"),
          ("fleet", PAIR_ORANGE[0], "fleet-operator PRs")]


def panel(subfig, title, rows, key, window, scale=1):
    axl, axr = broken_pair(subfig, title, span="month", window=window,
                           month_marks=True)
    for sl, color, label in SLICES:
        month_series(axl, axr,
                     [cell(rows, m, sl, key, scale=scale) for m in BASELINE],
                     [cell(rows, m, sl, key, scale=scale) for m in window],
                     color, label=label)
    return axl, axr


def main() -> None:
    window = [m for m in WINDOW if month_w8_mature(m)]
    mix = review_mix(by="ai", fleet_slice=True, granularity="month")
    att = attention_by_ai(fleet_slice=True, granularity="month")
    fig = plt.figure(figsize=(11, 4.4))
    fig.suptitle("Figure 3 companion: human review coverage and attention "
                 "per line, by PR type (monthly, finalized months only)",
                 fontsize=12, y=-0.08)
    subfigs = fig.subfigures(1, 2, wspace=0.05)

    axl, axr = panel(subfigs.flat[0], "% of merged PRs human-reviewed",
                     mix, "humanRev_pr", window, scale=100)
    axl.set_ylim(0, 100)
    axl.set_ylabel("% of merged PRs human-reviewed")
    axr.legend(fontsize=8, loc="lower left")

    axl, axr = panel(subfigs.flat[1], "human comments per kLOC",
                     att, "comments_per_kloc", window)
    axl.set_ylim(bottom=0)
    axl.set_ylabel("human comments per kLOC")
    axr.legend(fontsize=8, loc="upper right")

    save(fig, "artifacts/figure_3_comp_audits.png")


if __name__ == "__main__":
    main()
