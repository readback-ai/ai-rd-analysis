"""Figure A1: LOC per contributor per month, submitted and merged, by
adoption cohort.

2x3 small multiples (fleet / early / middle / late / non-adopters), each
panel a broken x-axis (Q1-2024 months | Oct-2025..Jun-2026) with the six
figstyle.LOC_SERIES from pipeline.studies.productivity.adoption_monthly():
mean SUBMITTED kLOC per month-active cohort member (no censoring) and mean
MERGED (w8) kLOC. Months with open w8 windows are shaded (merged
provisional there; they finalize with the AS_OF re-pulls).

Output: artifacts/fig_a1_adoption_cohorts.png
Usage:  PYTHONPATH=src python scripts/plot_adoption_cohorts.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import (BASELINE, LOC_SERIES, WINDOW, broken_pair,
                               month_series, plt, save, shade_span)
from pipeline.studies.productivity import (ADOPTION_COHORTS,
                                           adoption_monthly,
                                           month_w8_mature)


def main() -> None:
    rows = adoption_monthly()
    fig = plt.figure(figsize=(13, 7))
    fig.suptitle("Figure A1: LOC per contributor per month, submitted and "
                 "merged, by adoption cohort", fontsize=12, y=-0.04)
    subfigs = fig.subfigures(2, 3, hspace=0.08, wspace=0.05)
    prov = [i for i, m in enumerate(WINDOW) if not month_w8_mature(m)]
    for sf, (coh, desc) in zip(subfigs.flat, ADOPTION_COHORTS):
        axl, axr = broken_pair(sf, desc.split(":")[0], span="month")
        for key, color, ls, label in LOC_SERIES:
            month_series(axl, axr,
                         [rows.get((m, coh), {}).get(key) for m in BASELINE],
                         [rows.get((m, coh), {}).get(key) for m in WINDOW],
                         color, ls=ls, label=label)
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
    save(fig, "artifacts/fig_a1_adoption_cohorts.png")


if __name__ == "__main__":
    main()
