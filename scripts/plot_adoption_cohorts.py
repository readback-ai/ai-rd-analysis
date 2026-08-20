"""Figure A1: LOC per contributor per month, submitted and merged, by
adoption cohort.

2x3 small multiples (fleet / early / middle / late / non-adopters), each
panel a broken x-axis (Q1-2024 months | Oct-2025..Jun-2026) with the six
figstyle.LOC_SERIES from pipeline.studies.productivity.adoption_monthly():
mean SUBMITTED kLOC per month-active cohort member (no censoring) and mean
MERGED (w8) kLOC. Months with open w8 windows are shaded (merged
provisional there; they finalize with the AS_OF re-pulls).

Data:   artifacts/data/fig_a1_adoption_cohorts.csv
Output: artifacts/fig_a1_adoption_cohorts.png
Usage:  PYTHONPATH=src python scripts/plot_adoption_cohorts.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (BASELINE, LOC_SERIES, WINDOW, broken_pair,
                               month_series, plt, shade_span)
from pipeline.studies.productivity import (ADOPTION_COHORTS,
                                           adoption_monthly,
                                           month_w8_mature)

STYLE = {key: (color, ls, label) for key, color, ls, label in LOC_SERIES}


def collect() -> Table:
    rows = adoption_monthly()
    months = BASELINE + WINDOW
    t = Table("fig_a1_adoption_cohorts")
    for coh, desc in ADOPTION_COHORTS:
        for key, _color, _ls, label in LOC_SERIES:
            t.add_series(coh, key,
                         [rows.get((m, coh), {}).get(key) for m in months],
                         x_labels=months, panel_label=desc.split(":")[0],
                         series_label=label)
    return t


def render(t: Table):
    fig = plt.figure(figsize=(13, 7))
    fig.suptitle("Figure A1: LOC per contributor per month, submitted and "
                 "merged, by adoption cohort", fontsize=12, y=-0.04)
    subfigs = fig.subfigures(2, 3, hspace=0.08, wspace=0.05)
    prov = [i for i, m in enumerate(WINDOW) if not month_w8_mature(m)]
    for sf, coh in zip(subfigs.flat, t.panels()):
        axl, axr = broken_pair(sf, t.label_of(coh), span="month")
        for key in t.series_in(coh):
            color, ls, label = STYLE[key]
            vals = t.values(coh, key)
            month_series(axl, axr, vals[:len(BASELINE)],
                         vals[len(BASELINE):], color, ls=ls, label=label)
        if prov:
            shade_span(axr, prov[0] - 0.5, prov[-1] + 0.5,
                       label="w8 windows open (merged provisional)")
        axl.set_ylim(bottom=0)
        axl.set_ylabel("kLOC / contributor / month")
    # legend lives in the unused sixth panel slot
    handles, labels = axr.get_legend_handles_labels()
    ax6 = list(subfigs.flat)[5].subplots()
    ax6.axis("off")
    ax6.legend(handles, labels, loc="center", fontsize=10, frameon=False)
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/fig_a1_adoption_cohorts.png")
