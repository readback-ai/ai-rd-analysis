"""Figure 6: human review of merged PRs and LOC — core vs external, with
the bot-review substitution.

Two panels (share of merged PRs; share of merged LOC), each with six
series: {human-reviewed, bot-only-reviewed, self-merged-unreviewed} x
{core contributors (solid), external contributors (dashed)}. Merged
outcomes are mature-gated (Q2-2026 reflects PRs whose w8 window closed;
finalizes with AS_OF re-pulls). Broken x-axis: Q1-2024 | Q4-2025..Q2-2026.

Output: artifacts/fig6_review_mix.png
Usage:  PYTHONPATH=src python scripts/plot_fig6_review.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.productivity import PERIODS, review_mix  # noqa: E402

BREAK_KW = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=9,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)
CLASSES = [("humanRev", "tab:blue", "human-reviewed"),
           ("botOnly", "tab:orange", "bot-only reviewed"),
           ("selfUnrev", "tab:red", "self-merged unreviewed")]
SLICES = [("ins", "-", "core"), ("ext", "--", "external")]


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
    rows = review_mix()
    fig = plt.figure(figsize=(11, 4.6))
    fig.suptitle("Figure 6: review of merged PRs and merged LOC — core vs "
                 "external contributors", fontsize=12, y=1.06)
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, unit, title in ((subfigs.flat[0], "pr",
                             "share of merged PRs"),
                            (subfigs.flat[1], "loc",
                             "share of merged LOC")):
        axl, axr = broken_pair(sf, title)
        for ch, color, clabel in CLASSES:
            for sl, ls, slabel in SLICES:
                y = [100 * rows.get((p, sl), {}).get(f"{ch}_{unit}", 0)
                     for p in PERIODS]
                axl.plot([0], y[:1], marker="o", ms=3, ls=ls, color=color)
                axr.plot([0, 1, 2], y[1:], marker="o", ms=3, ls=ls,
                         color=color, label=f"{clabel} ({slabel})")
        axl.set_ylim(0, 100)
        axl.set_ylabel("% of merged " + ("PRs" if unit == "pr" else "LOC"))
    handles, labels = axr.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.08))
    fig.savefig("artifacts/fig6_review_mix.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig6_review_mix.png")


if __name__ == "__main__":
    main()
