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

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.productivity import (adoption_monthly,  # noqa: E402
                                           month_w8_mature)

BREAK_KW = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=9,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)
BASELINE = ["2024-01", "2024-02", "2024-03"]
WINDOW = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
          "2026-04", "2026-05", "2026-06"]
ALL = [
    ("submitted", "tab:blue", "-", "submitted total"),
    ("sub_nonai", "tab:blue", "--", "submitted non-AI"),
    ("sub_ai", "tab:blue", ":", "submitted AI-involved"),
    ("merged", "tab:green", "-", "merged total (w8)"),
    ("mrg_nonai", "tab:green", "--", "merged non-AI"),
    ("mrg_ai", "tab:green", ":", "merged AI-involved"),
]
TOTALS = [ALL[0], ALL[3]]


def broken_pair(subfig, title):
    axl, axr = subfig.subplots(
        1, 2, sharey=True,
        gridspec_kw={"width_ratios": [1, 3], "wspace": 0.08})
    axl.set_xlim(-0.5, len(BASELINE) - 0.5)
    axl.set_xticks([1], ["Q1-24"])
    axr.set_xlim(-0.5, len(WINDOW) - 0.5)
    ticks = [0, 3, 6, 8]
    axr.set_xticks(ticks, [WINDOW[i][2:7] for i in ticks], fontsize=8)
    axl.spines.right.set_visible(False)
    axr.spines.left.set_visible(False)
    axr.tick_params(left=False)
    for ax, x in ((axl, 1), (axr, 0)):
        ax.plot([x], [0], transform=ax.transAxes, **BREAK_KW)
        ax.plot([x], [1], transform=ax.transAxes, **BREAK_KW)
    axl.set_title(title, fontsize=10, loc="left")
    return axl, axr


def main() -> None:
    rows = adoption_monthly()
    fig = plt.figure(figsize=(11, 4.6))
    fig.suptitle("Figure 5: fleet operators vs non-adopters — LOC per "
                 "contributor per month", fontsize=12, y=1.04)
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    prov = [i for i, m in enumerate(WINDOW) if not month_w8_mature(m)]
    for sf, coh, title, series in (
            (subfigs.flat[0], "fleet", "fleet operators (all six metrics)",
             ALL),
            (subfigs.flat[1], "never",
             "non-adopters (totals; AI ≡ 0 by construction)", TOTALS)):
        axl, axr = broken_pair(sf, title)
        for key, color, ls, label in series:
            axl.plot(range(len(BASELINE)),
                     [rows.get((m, coh), {}).get(key) for m in BASELINE],
                     marker="o", ms=2.5, ls=ls, color=color)
            axr.plot(range(len(WINDOW)),
                     [rows.get((m, coh), {}).get(key) for m in WINDOW],
                     marker="o", ms=2.5, ls=ls, color=color, label=label)
        if prov:
            axr.axvspan(prov[0] - 0.5, prov[-1] + 0.5, color="0.85",
                        alpha=0.5, zorder=0,
                        label="w8 windows open (merged provisional)")
        axl.set_ylim(bottom=0)
        axl.set_ylabel("kLOC / contributor / month")
        axr.legend(fontsize=7,
                   loc="upper left" if coh == "fleet" else "lower right")
    fig.savefig("artifacts/fig5_fleet_vs_nonadopters.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig5_fleet_vs_nonadopters.png")


if __name__ == "__main__":
    main()
