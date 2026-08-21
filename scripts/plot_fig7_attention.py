"""Figure 7: human attention proxies — AI-involved vs non-AI PRs.

Two broken-axis panels over mature merged human-reviewed PRs (pooled):
comments/kLOC (bot-clean human inline comments) and first-review latency
hours/kLOC (creation -> first human review, per kLOC). Dark = AI-involved
PRs, light = non-AI; the AI series is absent at the Q1-2024 baseline by
construction. Q2 is partial (w8 windows open at the AS_OF).

Data:   artifacts/data/fig7_attention_by_ai.csv
Output: artifacts/fig7_attention_by_ai.png
Usage:  PYTHONPATH=src python scripts/plot_fig7_attention.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (PAIR_BLUE, broken_pair, cell, plt,
                               quarter_series, shade_q2_partial)
from pipeline.studies.attention import PERIODS, attention_by_ai

SLICES = [("ai", PAIR_BLUE[0], "AI-involved PRs"),
          ("nonai", PAIR_BLUE[1], "non-AI PRs")]

PANELS = [("comments_per_kloc", "human comments per kLOC"),
          ("first_rev_h_per_kloc", "hours to first human review per kLOC")]


def collect() -> Table:
    rows = attention_by_ai()
    t = Table("fig7_attention_by_ai")
    for key, title in PANELS:
        for sl, _color, label in SLICES:
            t.add_series(key, sl, [cell(rows, p, sl, key) for p in PERIODS],
                         x_labels=PERIODS, panel_label=title,
                         series_label=label)
    return t


def render(t: Table):
    fig = plt.figure(figsize=(11, 4.4))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, (key, _title) in zip(subfigs.flat, PANELS):
        title = t.label_of(key)
        axl, axr = broken_pair(sf, title)
        for sl, color, label in SLICES:
            quarter_series(axl, axr, t.values(key, sl), color, label)
        shade_q2_partial(axr)
        axl.set_ylim(bottom=0)
        axl.set_ylabel(title)
        axr.legend(fontsize=8, loc="lower left")
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/fig7_attention_by_ai.png")
