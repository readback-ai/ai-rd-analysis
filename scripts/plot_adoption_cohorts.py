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
from pipeline.analyze import month_window
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (BASELINE, LOC_SERIES, broken_pair,
                               month_series, plt, shade_provisional)
from pipeline.studies.productivity import (ADOPTION_COHORTS,
                                           adoption_monthly)

STYLE = {key: (color, ls, label) for key, color, ls, label in LOC_SERIES}


def table(rows: dict, name: str, label_suffix: str = "",
          window: list[str] | None = None) -> Table:
    """The cohort x series table, over whichever per-member statistic
    `rows` carries — shared with the median variant (fig_a1a).

    `label_suffix` names the statistic in the panel label, which is where
    a caption's factual content lives once figures stopped baking in
    captions (they are supplied in the paper text). `window` follows the
    censused registry (analyze.month_window / plot_all --through)."""
    months = BASELINE + (window or month_window())
    t = Table(name)
    for coh, desc in ADOPTION_COHORTS:
        for key, _color, _ls, label in LOC_SERIES:
            t.add_series(coh, key,
                         [rows.get((m, coh), {}).get(key) for m in months],
                         x_labels=months,
                         panel_label=desc.split(":")[0] + label_suffix,
                         series_label=label)
    return t


def collect(window: list[str] | None = None) -> Table:
    window = window or month_window()
    return table(adoption_monthly(window=window),
                 "fig_a1_adoption_cohorts", window=window)


def render(t: Table, ylabel: str = "kLOC / contributor / month"):
    # window from the table itself, so --from-table replays a committed
    # CSV faithfully regardless of the registry at render time
    window = [r["x_label"] for r in t.points(t.panels()[0], "submitted")
              if r["x_label"] not in BASELINE]
    fig = plt.figure(figsize=(13, 7))
    subfigs = fig.subfigures(2, 3, hspace=0.08, wspace=0.05)
    for sf, coh in zip(subfigs.flat, t.panels()):
        axl, axr = broken_pair(sf, t.label_of(coh), span="month",
                               window=window)
        for key in t.series_in(coh):
            color, ls, label = STYLE[key]
            vals = t.values(coh, key)
            month_series(axl, axr, vals[:len(BASELINE)],
                         vals[len(BASELINE):], color, ls=ls, label=label)
        shade_provisional(axr, window)
        axl.set_ylim(bottom=0)
        axl.set_ylabel(ylabel)
    # legend lives in the unused sixth panel slot
    handles, labels = axr.get_legend_handles_labels()
    ax6 = list(subfigs.flat)[5].subplots()
    ax6.axis("off")
    ax6.legend(handles, labels, loc="center", fontsize=10, frameon=False)
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/fig_a1_adoption_cohorts.png")
