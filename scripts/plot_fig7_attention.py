"""Figure 7: human attention proxies — AI-involved vs non-AI PRs.

Two broken-axis panels over mature merged human-reviewed PRs (pooled):
comments/kLOC (bot-clean human inline comments) and first-review latency
hours/kLOC (creation -> first human review, per kLOC). Dark = AI-involved
PRs, light = non-AI; the AI series is absent at the Q1-2024 baseline by
construction. Q2 is partial (w8 windows open at the AS_OF).

Output: artifacts/fig7_attention_by_ai.png
Usage:  PYTHONPATH=src python scripts/plot_fig7_attention.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import (PAIR_BLUE, broken_pair, cell, plt,
                               quarter_series, save, shade_q2_partial)
from pipeline.studies.attention import PERIODS, attention_by_ai

SLICES = [("ai", PAIR_BLUE[0], "AI-involved PRs"),
          ("nonai", PAIR_BLUE[1], "non-AI PRs")]


def main() -> None:
    rows = attention_by_ai()
    fig = plt.figure(figsize=(11, 4.4))
    fig.suptitle("Figure 7: human attention per line — AI vs non-AI "
                 "merged PRs (fleet authors excluded)", fontsize=12,
                 y=-0.08)
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, key, title in (
            (subfigs.flat[0], "comments_per_kloc",
             "human comments per kLOC"),
            (subfigs.flat[1], "first_rev_h_per_kloc",
             "hours to first human review per kLOC")):
        axl, axr = broken_pair(sf, title)
        for sl, color, label in SLICES:
            y = [cell(rows, p, sl, key) for p in PERIODS]
            quarter_series(axl, axr, y, color, label)
        shade_q2_partial(axr)
        axl.set_ylim(bottom=0)
        axl.set_ylabel(title)
        axr.legend(fontsize=8, loc="lower left")
    save(fig, "artifacts/fig7_attention_by_ai.png")


if __name__ == "__main__":
    main()
