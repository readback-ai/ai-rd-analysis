"""Figure 8: do human review requests still produce edits? — by PR type.

Two broken-axis panels from the identified CLEAN lanes (no AI-reviewer
activity; manifest-bound PPS sample, Horvitz-Thompson weighted):
(a) share of PRs with an explicit human ask whose author subsequently
edited; (b) share of post-ask LOC in those PRs' commits. Dark =
AI-involved PRs, light = non-AI. Points with sample n < 20 are omitted;
the AI lane starts in Q1-2026 (too few asked AI PRs earlier). Q2 partial
(w8 windows open at the AS_OF).

Output: artifacts/fig8_responsiveness_by_ai.png
Usage:  PYTHONPATH=src python scripts/plot_fig8_responsiveness.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.review_action import PERIODS, lane_rows  # noqa: E402

BREAK_KW = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=9,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)
SLICES = [("CLEAN+AI", "#1f77b4", "AI-involved PRs"),
          ("CLEAN+nonAI", "#8ec1e8", "non-AI PRs")]


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
    _, lanes, _ = lane_rows()   # fleet-excluded domain

    def val(per, lane, kind):
        a = lanes.get((per, lane))
        if not a or a["n"] < 20:
            return None
        if kind == "responded":
            return 100 * a["wacted"] / a["wn"]
        return 100 * a["post"] / a["total"]

    fig = plt.figure(figsize=(11, 4.4))
    fig.suptitle("Figure 8: responsiveness to human review requests — "
                 "AI vs non-AI PRs (CLEAN lane, HT; fleet authors excluded)",
                 fontsize=12, y=-0.08)
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, kind, title in (
            (subfigs.flat[0], "responded", "% of asked PRs with author "
             "edits after the ask"),
            (subfigs.flat[1], "locshare", "% of LOC edited after the ask")):
        axl, axr = broken_pair(sf, title)
        for lane, color, label in SLICES:
            y = [val(p, lane, kind) for p in PERIODS]
            axl.plot([0], y[:1], marker="o", ms=4, color=color)
            axr.plot([0, 1, 2], y[1:], marker="o", ms=3, color=color,
                     label=label)
        axr.axvspan(1.6, 2.4, color="0.85", alpha=0.5, zorder=0,
                    label="Q2 partial (w8 windows open)")
        axl.set_ylim(0, 100)
        axl.set_ylabel(title)
        axr.legend(fontsize=8, loc="lower left")
    fig.savefig("artifacts/fig8_responsiveness_by_ai.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig8_responsiveness_by_ai.png")


if __name__ == "__main__":
    main()
