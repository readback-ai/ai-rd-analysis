"""Figure 5: fleet operators vs non-adopters, total productivity over the
whole period.

Two calendar-time panels (broken x-axis: Q1-2024 months | Oct-2025..
Jun-2026): fleet operators with all six metrics (submitted/merged x
total/non-AI/AI-involved), non-adopters with totals only (their AI
series are identically zero by construction). Mean kLOC per month-active
cohort member; w8-open months shaded (merged provisional).

Output: artifacts/fig5_fleet_vs_nonadopters.png
Usage:  PYTHONPATH=src python scripts/plot_fig5_fleet.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import (BASELINE, LOC_SERIES, WINDOW, broken_pair,
                               month_series, plt, save, shade_span)
from pipeline.studies.productivity import (adoption_monthly,
                                           month_w8_mature)

TOTALS = [LOC_SERIES[0], LOC_SERIES[3]]


def main() -> None:
    rows = adoption_monthly()
    fig = plt.figure(figsize=(11, 4.6))
    fig.suptitle("Figure 5: fleet operators vs non-adopters — LOC per "
                 "contributor per month", fontsize=12, y=-0.08)
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    prov = [i for i, m in enumerate(WINDOW) if not month_w8_mature(m)]
    for sf, coh, title, series in (
            (subfigs.flat[0], "fleet", "fleet operators (all six metrics)",
             LOC_SERIES),
            (subfigs.flat[1], "never",
             "non-adopters (totals; AI ≡ 0 by construction)", TOTALS)):
        axl, axr = broken_pair(sf, title, span="month")
        for key, color, ls, label in series:
            month_series(axl, axr,
                         [rows.get((m, coh), {}).get(key) for m in BASELINE],
                         [rows.get((m, coh), {}).get(key) for m in WINDOW],
                         color, ls=ls, label=label)
        if prov:
            shade_span(axr, prov[0] - 0.5, prov[-1] + 0.5,
                       label="w8 windows open (merged provisional)")
        axl.set_ylim(bottom=0)
        axl.set_ylabel("kLOC / contributor / month")
        axr.legend(fontsize=7,
                   loc="upper left" if coh == "fleet" else "lower right")
    save(fig, "artifacts/fig5_fleet_vs_nonadopters.png")


if __name__ == "__main__":
    main()
