"""Fleet operators vs non-adopters, total productivity over the period.

Two QUARTERLY calendar-time panels (broken x-axis: Q1-2024 | Q4-2025..
Q2-2026): fleet operators with all six metrics (submitted/merged x
total/non-AI/AI-involved), non-adopters with totals only (their AI
series are identically zero by construction). kLOC per quarter-active
cohort member per quarter — quarters, not months: the monthly points
were dominated by month-to-month noise (`adoption_quarterly`).

Data:   artifacts/data/fleet_vs_nonadopters.csv
Output: artifacts/fleet_vs_nonadopters.png
Usage:  PYTHONPATH=src python scripts/plot_fig5_fleet.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (LOC_SERIES, broken_pair, plt, quarter_series,
                               shade_q2_partial)
from pipeline.studies.productivity import adoption_quarterly

QUARTERS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
TOTALS = [LOC_SERIES[0], LOC_SERIES[3]]
STYLE = {key: (color, ls, label) for key, color, ls, label in LOC_SERIES}

PANELS = [("fleet", "fleet operators (all six metrics)", LOC_SERIES),
          ("never", "non-adopters (totals; AI ≡ 0 by construction)",
           TOTALS)]

NAME = "fleet_vs_nonadopters"


def table(rows: dict, name: str, label_suffix: str = "") -> Table:
    """The two-panel table over whichever per-member statistic `rows`
    carries — shared with the median variant. `label_suffix` names the
    statistic in the panel label."""
    t = Table(name)
    for coh, title, series in PANELS:
        for key, _color, _ls, label in series:
            t.add_series(coh, key,
                         [rows.get((q, coh), {}).get(key) for q in QUARTERS],
                         x_labels=QUARTERS, panel_label=title + label_suffix,
                         series_label=label)
    return t


def collect() -> Table:
    return table(adoption_quarterly(), NAME)


def render(t: Table, ylabel: str = "kLOC / contributor / quarter",
           legend_title: str | None = None):
    fig = plt.figure(figsize=(11, 4.6))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, coh in zip(subfigs.flat, t.panels()):
        axl, axr = broken_pair(sf, t.label_of(coh), span="quarter")
        for key in t.series_in(coh):
            color, ls, label = STYLE[key]
            vals = [p["value"] for p in t.points(coh, key)]
            quarter_series(axl, axr, vals, color, ls=ls, label=label)
        shade_q2_partial(axr)            # no-op once Q2 is finalized
        axl.set_ylim(bottom=0)
        axl.set_ylabel(ylabel)
        axr.legend(fontsize=7, title=legend_title,
                   loc="upper left" if coh == "fleet" else "lower right")
    return fig


if __name__ == "__main__":
    figure_main(collect, render, f"artifacts/{NAME}.png")
