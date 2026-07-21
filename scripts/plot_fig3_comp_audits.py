"""Figure 3 companion (comp audits): who still gets human review, and how
much attention per line — AI-involved vs non-AI vs fleet-operator PRs.

Left: % of mature merged PRs with a human (reviewer != author) review.
Right: human comments per kLOC on mature merged human-reviewed PRs.
Slices: AI-involved and non-AI PRs (fleet-operator authors excluded) plus
fleet-operator PRs as their own series. AI series absent at the Q1-2024
baseline by construction; Q2 partial (w8 windows open at the AS_OF).

Output: artifacts/figure_3_comp_audits.png
Usage:  PYTHONPATH=src python scripts/plot_fig3_comp_audits.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.attention import attention_by_ai  # noqa: E402
from pipeline.studies.productivity import PERIODS, review_mix  # noqa: E402

BREAK_KW = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=9,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)
SLICES = [("ai", "#1f77b4", "AI-involved PRs"),
          ("nonai", "#8ec1e8", "non-AI PRs"),
          ("fleet", "#d95f02", "fleet-operator PRs")]


def broken_pair(subfig, title):
    axl, axr = subfig.subplots(
        1, 2, sharey=True,
        gridspec_kw={"width_ratios": [1, 3], "wspace": 0.08})
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


def main() -> None:
    mix = review_mix(by="ai", fleet_slice=True)
    att = attention_by_ai(fleet_slice=True)
    fig = plt.figure(figsize=(11, 4.4))
    fig.suptitle("Figure 3 companion: human review coverage and attention "
                 "per line, by PR type", fontsize=12, y=-0.08)
    subfigs = fig.subfigures(1, 2, wspace=0.05)

    axl, axr = broken_pair(subfigs.flat[0],
                           "% of merged PRs human-reviewed")
    for sl, color, label in SLICES:
        # AI-conditioned rates are undefined at the Q1-2024 baseline
        # (zero denominator) — suppress even if a stray detector FP
        # creates a tiny cell
        y = [100 * mix[(p, sl)]["humanRev_pr"]
             if (p, sl) in mix and not (sl == "ai" and p == "Q1-2024")
             else None for p in PERIODS]
        axl.plot([0], y[:1], marker="o", ms=4, color=color)
        axr.plot([0, 1, 2], y[1:], marker="o", ms=3, color=color,
                 label=label)
    axr.axvspan(1.6, 2.4, color="0.85", alpha=0.5, zorder=0,
                label="Q2 partial (w8 windows open)")
    axl.set_ylim(0, 100)
    axl.set_ylabel("% of merged PRs human-reviewed")
    axr.legend(fontsize=8, loc="lower left")

    axl, axr = broken_pair(subfigs.flat[1], "human comments per kLOC")
    for sl, color, label in SLICES:
        y = [att[(p, sl)]["comments_per_kloc"]
             if (p, sl) in att and not (sl == "ai" and p == "Q1-2024")
             else None for p in PERIODS]
        axl.plot([0], y[:1], marker="o", ms=4, color=color)
        axr.plot([0, 1, 2], y[1:], marker="o", ms=3, color=color,
                 label=label)
    axr.axvspan(1.6, 2.4, color="0.85", alpha=0.5, zorder=0,
                label="Q2 partial (w8 windows open)")
    axl.set_ylim(bottom=0)
    axl.set_ylabel("human comments per kLOC")
    axr.legend(fontsize=8, loc="upper right")

    fig.savefig("artifacts/figure_3_comp_audits.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/figure_3_comp_audits.png")


if __name__ == "__main__":
    main()
