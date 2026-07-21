"""Figure A1: LOC per contributor per month, submitted and merged, by
adoption cohort.

2x3 small multiples (fleet / early / middle / late / non-adopters), each
panel a broken x-axis (Q1-2024 months | Oct-2025..Jun-2026) with two
series from pipeline.studies.productivity.adoption_monthly(): mean
SUBMITTED kLOC per month-active cohort member (no censoring) and mean
MERGED (w8) kLOC. Merged values for months past the w8-mature cap are
drawn dotted (provisional; they finalize with the AS_OF re-pulls).

Output: artifacts/fig_a1_adoption_cohorts.png
Usage:  PYTHONPATH=src python scripts/plot_adoption_cohorts.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline import detect  # noqa: E402
from pipeline.studies.productivity import (ADOPTION_COHORTS,  # noqa: E402
                                           adoption_monthly)

BREAK_KW = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=9,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)
BASELINE = ["2024-01", "2024-02", "2024-03"]
WINDOW = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
          "2026-04", "2026-05", "2026-06"]


def month_mature(mon: str) -> bool:
    """Every PR of month `mon` reached w8 by the AS_OF."""
    from calendar import monthrange
    from datetime import datetime, timedelta
    as_of = datetime.fromisoformat(detect.AS_OF.replace("Z", "+00:00"))
    y, m = int(mon[:4]), int(mon[5:7])
    end = datetime(y, m, monthrange(y, m)[1], 23, 59, tzinfo=as_of.tzinfo)
    return end + timedelta(days=56) <= as_of


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


# six series per panel: color = outcome (blue submitted, green merged),
# linestyle = AI split (solid total, dashed non-AI, dotted AI-involved);
# months with open w8 windows are shaded (merged provisional there)
SERIES = [
    ("submitted", "tab:blue", "-", "submitted total"),
    ("sub_nonai", "tab:blue", "--", "submitted non-AI"),
    ("sub_ai", "tab:blue", ":", "submitted AI-involved"),
    ("merged", "tab:green", "-", "merged total (w8)"),
    ("mrg_nonai", "tab:green", "--", "merged non-AI"),
    ("mrg_ai", "tab:green", ":", "merged AI-involved"),
]


def series(axl, axr, rows, coh, key, color, ls, label):
    def vals(months):
        return [rows.get((m, coh), {}).get(key) for m in months]
    axl.plot(range(len(BASELINE)), vals(BASELINE), marker="o", ms=2.5,
             ls=ls, color=color)
    axr.plot(range(len(WINDOW)), vals(WINDOW), marker="o", ms=2.5,
             ls=ls, color=color, label=label)


def main() -> None:
    rows = adoption_monthly()
    fig = plt.figure(figsize=(13, 7))
    fig.suptitle("Figure A1: LOC per contributor per month, submitted and "
                 "merged, by adoption cohort", fontsize=12, y=1.02)
    subfigs = fig.subfigures(2, 3, hspace=0.08, wspace=0.05)
    prov = [i for i, m in enumerate(WINDOW) if not month_mature(m)]
    for sf, (coh, desc) in zip(subfigs.flat, ADOPTION_COHORTS):
        axl, axr = broken_pair(sf, desc.split(":")[0])
        for key, color, ls, label in SERIES:
            series(axl, axr, rows, coh, key, color, ls, label)
        if prov:
            axr.axvspan(prov[0] - 0.5, prov[-1] + 0.5, color="0.85",
                        alpha=0.5, zorder=0,
                        label="w8 windows open (merged provisional)")
        axl.set_ylim(bottom=0)
        axl.set_ylabel("kLOC / contributor / month")
    # legend lives in the unused sixth panel slot
    handles, labels = axr.get_legend_handles_labels()
    ax6 = list(subfigs.flat)[5].subplots()
    ax6.axis("off")
    ax6.legend(handles, labels, loc="center", fontsize=10, frameon=False)
    fig.savefig("artifacts/fig_a1_adoption_cohorts.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig_a1_adoption_cohorts.png")


if __name__ == "__main__":
    main()
