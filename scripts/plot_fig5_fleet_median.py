"""The fleet_vs_nonadopters panels on MEDIANS instead of means.

Same two QUARTERLY panels (fleet operators with all six metrics,
non-adopters with totals) as `plot_fig5_fleet.py`, but each point is the
median cohort member. Fleet mean and median diverge sharply — a single
operator supplied over half the cohort's merged LOC by 2026-06 — so the
mean tracks that operator while the median tracks membership.

CAVEAT — medians are per series and DO NOT DECOMPOSE: the AI and non-AI
lines will not sum to their total, because a different member sits at the
middle of each.

Data:   artifacts/data/fleet_vs_nonadopters_median.csv
Output: artifacts/fleet_vs_nonadopters_median.png
Usage:  PYTHONPATH=src python scripts/plot_fig5_fleet_median.py
"""
import functools
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
from pipeline.figdata import Table, figure_main
from pipeline.studies.productivity import adoption_quarterly

import plot_fig5_fleet as mean_fig

NAME = "fleet_vs_nonadopters_median"
YLABEL = "median kLOC / contributor / quarter"
LEGEND_TITLE = "median:"


def collect() -> Table:
    return mean_fig.table(adoption_quarterly(stat="median"), NAME)


if __name__ == "__main__":
    figure_main(collect,
                functools.partial(mean_fig.render, ylabel=YLABEL,
                                  legend_title=LEGEND_TITLE),
                f"artifacts/{NAME}.png")
