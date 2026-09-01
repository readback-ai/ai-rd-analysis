"""Figure 3a: Figure 3 on the MEDIAN core author instead of the mean.

Same two series, quarters, CIs and baseline multiples as
`plot_paper_tables.py`'s Figure 3, but stage 1 — the statistic over a
repo's core authors — is the median. The contributor-weighted stage
across repos is unchanged.

METHODS §1d.4b quotes per-contributor LEVELS from the median: output is
heavy-tailed, so the mean tracks whoever the tail happens to be. The
growth MULTIPLE is robust to the choice (×2.95 mean vs ×2.92 median) but
the levels are not (19.0 vs 10.0 kLOC/author in Q2-2026), which is why
this figure exists rather than a footnote.

Data:   artifacts/data/core_loc_median.csv
Output: artifacts/core_loc_median.png
Usage:  PYTHONPATH=src python scripts/plot_core_loc_median.py
"""
import sys

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
from pipeline.figdata import Table, figure_main
from pipeline.studies.paper_tables import core_rows

import plot_paper_tables as mean_fig

NAME = "core_loc_median"


def collect() -> Table:
    return mean_fig.core_table(core_rows(stat="median"), NAME)


def collect_monthly(window: list[str] | None = None) -> Table:
    """Monthly twin (plot_all --monthly); rendered by
    mean_fig.render_core_monthly, like the mean variant."""
    from pipeline.analyze import month_window
    window = window or month_window()
    return mean_fig.core_table(
        core_rows(stat="median", granularity="month", window=window),
        f"{NAME}_monthly", unit="month")


if __name__ == "__main__":
    figure_main(collect, mean_fig.render_core, f"artifacts/{NAME}.png")
