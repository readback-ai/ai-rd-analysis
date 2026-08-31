"""Figure A1a: the Figure A1 panels on MEDIANS instead of means.

Same cohorts, months and six LOC series as `plot_adoption_cohorts.py`,
but each point is the median cohort member rather than the mean. Cohort
output is heavy-tailed — a single fleet operator supplied 54.7% of the
cohort's merged LOC in 2026-06 while the median stayed flat — so the mean
describes the tail and the median describes membership. Read the pair
together: mean >> median is the signature of a cohort carried by a few
accounts.

CAVEAT — medians are per series and DO NOT DECOMPOSE. The AI and non-AI
lines will not sum to their total, because a different member sits at the
middle of each. Compare each series against its own mean counterpart; do
not read a median panel as a breakdown.

Data:   artifacts/data/fig_a1a_adoption_cohorts_median.csv
Output: artifacts/fig_a1a_adoption_cohorts_median.png
Usage:  PYTHONPATH=src python scripts/plot_adoption_cohorts_median.py
"""
import functools
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
from pipeline.figdata import Table, figure_main
from pipeline.studies.productivity import adoption_monthly

import plot_adoption_cohorts as mean_fig

NAME = "fig_a1a_adoption_cohorts_median"
YLABEL = "median kLOC / contributor / month"
LEGEND_TITLE = "median:"


def collect() -> Table:
    return mean_fig.table(adoption_monthly(stat="median"), NAME)


if __name__ == "__main__":
    figure_main(collect,
                functools.partial(mean_fig.render, ylabel=YLABEL,
                                  legend_title=LEGEND_TITLE),
                f"artifacts/{NAME}.png")
