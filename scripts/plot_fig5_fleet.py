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
from pipeline.analyze import month_window
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (BASELINE, LOC_SERIES, broken_pair,
                               month_series, plt, shade_provisional,
                               window_of)
from pipeline.studies.productivity import adoption_monthly

TOTALS = [LOC_SERIES[0], LOC_SERIES[3]]
STYLE = {key: (color, ls, label) for key, color, ls, label in LOC_SERIES}

PANELS = [("fleet", "fleet operators (all six metrics)", LOC_SERIES),
          ("never", "non-adopters (totals; AI ≡ 0 by construction)",
           TOTALS)]


def table(rows: dict, name: str, label_suffix: str = "",
          window: list[str] | None = None) -> Table:
    """The two-panel table over whichever per-member statistic `rows`
    carries — shared with the median variant (fig5a). `label_suffix`
    names the statistic in the panel label; `window` follows the
    censused registry (analyze.month_window / plot_all --through)."""
    months = BASELINE + (window or month_window())
    t = Table(name)
    for coh, title, series in PANELS:
        for key, _color, _ls, label in series:
            t.add_series(coh, key,
                         [rows.get((m, coh), {}).get(key) for m in months],
                         x_labels=months, panel_label=title + label_suffix,
                         series_label=label)
    return t


def collect(window: list[str] | None = None) -> Table:
    window = window or month_window()
    return table(adoption_monthly(window=window),
                 "fig5_fleet_vs_nonadopters", window=window)


def render(t: Table, ylabel: str = "kLOC / contributor / month",
           legend_title: str | None = None):
    window = window_of(t)
    fig = plt.figure(figsize=(11, 4.6))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
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
        axr.legend(fontsize=7, title=legend_title,
                   loc="upper left" if coh == "fleet" else "lower right")
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/fig5_fleet_vs_nonadopters.png")
