"""Figure 4: merged LOC per core author by fixed adoption cohort.

2x3 small multiples (early / medium / late / never / fleet), each panel a
broken x-axis (Q1-2024 | Q4-2025..Q2-2026) with three series: kLOC in
AI-tracked PRs, in non-AI PRs, and their sum (total), author-level pooled
means over quarter-active cohort members from
pipeline.studies.productivity.adoption_rows(). Shaded band = bootstrap
95% CI on the total mean; the black line is the cell MEDIAN — means are
whale-sensitive (agent-fleet accounts; audit in the module docstring).

Output: artifacts/fig4_adoption_cohorts.png

Usage:  PYTHONPATH=src python scripts/plot_adoption_cohorts.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.productivity import (ADOPTION_COHORTS, PERIODS,  # noqa: E402
                                           adoption_rows)

BREAK_KW = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=9,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)


def broken_pair(subfig, title):
    axl, axr = subfig.subplots(
        1, 2, sharey=True,
        gridspec_kw={"width_ratios": [1, 4], "wspace": 0.08})
    axl.set_xlim(-0.5, 0.5)
    axl.set_xticks([0], ["Q1-24"])
    axr.set_xlim(-0.4, 2.4)
    axr.set_xticks([0, 1, 2], ["Q4-25", "Q1-26", "Q2-26"])
    axl.spines.right.set_visible(False)
    axr.spines.left.set_visible(False)
    axr.tick_params(left=False)
    for ax, x in ((axl, 1), (axr, 0)):
        ax.plot([x], [0], transform=ax.transAxes, **BREAK_KW)
        ax.plot([x], [1], transform=ax.transAxes, **BREAK_KW)
    axl.set_title(title, fontsize=10, loc="left")
    return axl, axr


def draw(axl, axr, vals, style, label, color, band=None):
    """vals: 4 numbers (or None) ordered Q1-2024, Q4-2025..Q2-2026."""
    if vals[0] is not None:
        axl.plot([0], vals[:1], marker="o", ms=4, ls=style, color=color)
    x = [i for i, v in enumerate(vals[1:]) if v is not None]
    y = [v for v in vals[1:] if v is not None]
    axr.plot(x, y, marker="o", ms=4, ls=style, label=label, color=color)
    if band:
        lo = [band[0][i + 1] for i in x]
        hi = [band[1][i + 1] for i in x]
        axr.fill_between(x, lo, hi, alpha=0.12, color=color)


def main() -> None:
    rows = adoption_rows()
    fig = plt.figure(figsize=(13, 7))
    fig.suptitle("Figure 4: Merged LOC per core contributor by adoption "
                 "cohort (pooled author means, w8)", fontsize=12, y=1.04)
    subfigs = fig.subfigures(2, 3, hspace=0.08, wspace=0.05)
    for sf, (coh, desc) in zip(subfigs.flat, ADOPTION_COHORTS):
        axl, axr = broken_pair(sf, f"{coh} ({desc})")

        def col(key):
            return [rows[(p, coh)][key] if rows[(p, coh)] else None
                    for p in PERIODS]

        band = (col("lo"), col("hi"))
        draw(axl, axr, col("nonai"), "--", "non-AI PRs", "tab:gray")
        draw(axl, axr, col("ai"), ":", "AI-tracked PRs", "tab:red")
        draw(axl, axr, col("total"), "-", "total (mean)", "tab:blue", band)
        draw(axl, axr, col("median"), "-", "total (median)", "black")
        axl.set_ylim(bottom=0)
        axl.set_ylabel("merged kLOC / author")
        axr.legend(fontsize=7, loc="upper left")
    fig.savefig("artifacts/fig4_adoption_cohorts.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig4_adoption_cohorts.png")


if __name__ == "__main__":
    main()
