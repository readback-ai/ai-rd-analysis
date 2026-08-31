"""Figure 5a: the Figure 5 panels on MEDIANS instead of means.

Same two panels (fleet operators with all six metrics, non-adopters with
totals) as `plot_fig5_fleet.py`, but each point is the median cohort
member. The fleet mean tripled over 2026-03..06 while its median held
near 60 kLOC: the rise is one operator scaling up, not the cohort moving.

CAVEAT — medians are per series and DO NOT DECOMPOSE: the AI and non-AI
lines will not sum to their total, because a different member sits at the
middle of each.

Data:   artifacts/data/fig5a_fleet_vs_nonadopters_median.csv
Output: artifacts/fig5a_fleet_vs_nonadopters_median.png
Usage:  PYTHONPATH=src python scripts/plot_fig5_fleet_median.py
"""
import functools
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
from pipeline.figdata import Table, figure_main
from pipeline.studies.productivity import adoption_monthly

import plot_fig5_fleet as mean_fig

NAME = "fig5a_fleet_vs_nonadopters_median"
YLABEL = "median kLOC / contributor / month"
LEGEND_TITLE = "median:"


def collect(window: list[str] | None = None) -> Table:
    return mean_fig.table(adoption_monthly(stat="median", window=window),
                          NAME, window=window)


if __name__ == "__main__":
    figure_main(collect,
                functools.partial(mean_fig.render, ylabel=YLABEL,
                                  legend_title=LEGEND_TITLE),
                f"artifacts/{NAME}.png")
