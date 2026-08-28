"""Figure 5: fleet operators vs non-adopters, total productivity over the
whole period.

Two calendar-time panels (broken x-axis: Q1-2024 months | Oct-2025..
Jun-2026): fleet operators with all six metrics (submitted/merged x
total/non-AI/AI-involved), non-adopters with totals only (their AI
series are identically zero by construction). Mean kLOC per month-active
cohort member; w8-open months shaded (merged provisional).

Data:   artifacts/data/fig5_fleet_vs_nonadopters.csv
Output: artifacts/fig5_fleet_vs_nonadopters.png
Usage:  PYTHONPATH=src python scripts/plot_fig5_fleet.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (BASELINE, LOC_SERIES, WINDOW, broken_pair,
                               month_series, plt, shade_span)
from pipeline.studies.productivity import adoption_monthly, month_w8_mature

TOTALS = [LOC_SERIES[0], LOC_SERIES[3]]
STYLE = {key: (color, ls, label) for key, color, ls, label in LOC_SERIES}

PANELS = [("fleet", "fleet operators (all six metrics)", LOC_SERIES),
          ("never", "non-adopters (totals; AI ≡ 0 by construction)",
           TOTALS)]


def table(rows: dict, name: str) -> Table:
    """The two-panel table over whichever per-member statistic `rows`
    carries — shared with the median variant (fig5a)."""
    months = BASELINE + WINDOW
    t = Table(name)
    for coh, title, series in PANELS:
        for key, _color, _ls, label in series:
            t.add_series(coh, key,
                         [rows.get((m, coh), {}).get(key) for m in months],
                         x_labels=months, panel_label=title,
                         series_label=label)
    return t


def collect() -> Table:
    return table(adoption_monthly(), "fig5_fleet_vs_nonadopters")


def render(t: Table, ylabel: str = "kLOC / contributor / month"):
    fig = plt.figure(figsize=(11, 4.6))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
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
        axl.set_ylabel(ylabel)
        axr.legend(fontsize=7,
                   loc="upper left" if coh == "fleet" else "lower right")
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/fig5_fleet_vs_nonadopters.png")
