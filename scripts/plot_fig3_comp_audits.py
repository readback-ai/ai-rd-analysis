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

Data:   artifacts/data/figure_3_comp_audits.csv
Output: artifacts/figure_3_comp_audits.png
Usage:  PYTHONPATH=src python scripts/plot_fig3_comp_audits.py
        PYTHONPATH=src python scripts/plot_fig3_comp_audits.py \
            --from-table --format png,svg
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (BASELINE, PAIR_BLUE, PAIR_ORANGE, WINDOW,
                               broken_pair, cell, month_series, plt)
from pipeline.studies.attention import attention_by_ai
from pipeline.studies.productivity import month_w8_mature, review_mix

SLICES = [("ai", PAIR_BLUE[0], "AI-involved PRs"),
          ("nonai", PAIR_BLUE[1], "non-AI PRs"),
          ("fleet", PAIR_ORANGE[0], "fleet-operator PRs")]

PANELS = [("humanrev", "% of merged PRs human-reviewed", "humanRev_pr", 100),
          ("comments", "human comments per kLOC", "comments_per_kloc", 1)]


def collect() -> Table:
    window = [m for m in WINDOW if month_w8_mature(m)]
    rows_of = {"humanrev": review_mix(by="ai", fleet_slice=True,
                                      granularity="month"),
               "comments": attention_by_ai(fleet_slice=True,
                                           granularity="month")}
    months = BASELINE + window
    t = Table("figure_3_comp_audits")
    for panel, title, key, scale in PANELS:
        for sl, _color, label in SLICES:
            t.add_series(panel, sl,
                         [cell(rows_of[panel], m, sl, key, scale=scale)
                          for m in months],
                         x_labels=months, panel_label=title,
                         series_label=label)
    return t


def render(t: Table):
    window = [r["x_label"] for r in t.points("humanrev", "nonai")
              if r["x_label"] not in BASELINE]
    fig = plt.figure(figsize=(11, 4.4))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, (panel, _title, _key, _scale) in zip(subfigs.flat, PANELS):
        axl, axr = broken_pair(sf, t.label_of(panel), span="month",
                               window=window, month_marks=True)
        for sl, color, label in SLICES:
            vals = t.values(panel, sl)
            month_series(axl, axr, vals[:len(BASELINE)],
                         vals[len(BASELINE):], color, label=label)
        axl.set_ylabel(t.label_of(panel))
        if panel == "humanrev":
            axl.set_ylim(0, 100)
            axr.legend(fontsize=8, loc="lower left")
        else:
            axl.set_ylim(bottom=0)
            axr.legend(fontsize=8, loc="upper right")
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/figure_3_comp_audits.png")
