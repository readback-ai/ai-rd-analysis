"""Figure 2a: the Figure 2 event panels on MEDIANS instead of means.

Same balanced cohorts, offsets and six series as
`plot_fig2_comp_audits.py`, but each point is the median cohort member
rather than the mean. Per-author volume is heavy-tailed (METHODS
§1d.4b), so the mean follows whoever the tail happens to be while the
median follows membership — the same reason Figures 3a, 5a and A1a
exist. Read the pair together: mean >> median marks a cohort-month
carried by a few accounts.

CAVEAT — medians are per series and DO NOT DECOMPOSE. The AI and non-AI
lines will not sum to their total, because a different member sits at
the middle of each. The panel label carries this warning (figures bake
in no captions; 547596e), and any paper text reproducing the panel must
repeat it.

Data:   artifacts/data/figure_2a_comp_audits_median.csv
Output: artifacts/figure_2a_comp_audits_median.png
Usage:  PYTHONPATH=src python scripts/plot_fig2_comp_audits_median.py
"""
import functools
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
from pipeline.figdata import Table, figure_main
from pipeline.studies.productivity import event_by_adoption_month

import plot_fig2_comp_audits as mean_fig

NAME = "figure_2a_comp_audits_median"
YLABEL = "median kLOC / contributor / month"
LEGEND_TITLE = "median:"


def collect() -> Table:
    return mean_fig.table(event_by_adoption_month(stat="median"),
                          NAME)


if __name__ == "__main__":
    figure_main(collect,
                functools.partial(mean_fig.render, ylabel=YLABEL,
                                  legend_title=LEGEND_TITLE),
                f"artifacts/{NAME}.png")
