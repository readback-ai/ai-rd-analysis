"""Figure 7: human attention proxies — AI-involved vs non-AI PRs.

Two broken-axis panels over mature merged human-reviewed PRs (pooled):
comments/kLOC (bot-clean human inline comments) and first-review latency
hours/kLOC (creation -> first human review, per kLOC). Dark = AI-involved
PRs, light = non-AI; the AI series is absent at the Q1-2024 baseline by
construction. Q2 is partial (w8 windows open at the AS_OF).

Output: artifacts/fig7_attention_by_ai.png
Usage:  PYTHONPATH=src python scripts/plot_fig7_attention.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.attention import PERIODS, attention_by_ai  # noqa: E402

BREAK_KW = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=9,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)
SLICES = [("ai", "#1f77b4", "AI-involved PRs"),
          ("nonai", "#8ec1e8", "non-AI PRs")]


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
    rows = attention_by_ai()
    fig = plt.figure(figsize=(11, 4.4))
    fig.suptitle("Figure 7: human attention per line — AI vs non-AI "
                 "merged PRs (fleet authors excluded)", fontsize=12,
                 y=1.06)
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, key, title in (
            (subfigs.flat[0], "comments_per_kloc",
             "human comments per kLOC"),
            (subfigs.flat[1], "first_rev_h_per_kloc",
             "hours to first human review per kLOC")):
        axl, axr = broken_pair(sf, title)
        for sl, color, label in SLICES:
            y = [rows.get((p, sl), {}).get(key) for p in PERIODS]
            axl.plot([0], y[:1], marker="o", ms=4, color=color)
            axr.plot([0, 1, 2], y[1:], marker="o", ms=3, color=color,
                     label=label)
        axr.axvspan(1.6, 2.4, color="0.85", alpha=0.5, zorder=0,
                    label="Q2 partial (w8 windows open)")
        axl.set_ylim(bottom=0)
        axl.set_ylabel(title)
        axr.legend(fontsize=8, loc="upper right")
    fig.savefig("artifacts/fig7_attention_by_ai.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig7_attention_by_ai.png")


if __name__ == "__main__":
    main()
