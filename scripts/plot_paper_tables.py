"""Render paper figures 2 & 3 as line graphs with a broken x-axis.

Q1-2024 (the detector-validity baseline) sits ~7 quarters before the
continuous Q4-2025..Q2-2026 window, so each figure uses two panels sharing
the y-axis — a narrow left panel for Q1-2024 and a right panel for the
window — joined with standard axis-break marks. Shaded bands are the
bootstrap 95% CIs from pipeline.studies.paper_tables (CW, seeded).

Outputs: artifacts/fig2_ai_usage.png, artifacts/fig3_core_loc.png

Usage:  PYTHONPATH=src python scripts/plot_paper_tables.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.paper_tables import core_rows, usage_rows  # noqa: E402

BREAK_KW = dict(marker=[(-1, -0.5), (1, 0.5)], markersize=12,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)


def broken_axes(ylabel: str, title: str):
    """Left panel = Q1-2024 only, right = Q4-2025..Q2-2026, shared y."""
    fig, (axl, axr) = plt.subplots(
        1, 2, sharey=True, figsize=(8, 4.5),
        gridspec_kw={"width_ratios": [1, 4], "wspace": 0.06})
    axl.set_xlim(-0.5, 0.5)
    axl.set_xticks([0], ["Q1-2024"])
    axr.set_xlim(-0.4, 2.4)
    axr.set_xticks([0, 1, 2], ["Q4-2025", "Q1-2026", "Q2-2026"])
    axl.spines.right.set_visible(False)
    axr.spines.left.set_visible(False)
    axr.tick_params(left=False)
    axl.plot([1], [0], transform=axl.transAxes, **BREAK_KW)
    axl.plot([1], [1], transform=axl.transAxes, **BREAK_KW)
    axr.plot([0], [0], transform=axr.transAxes, **BREAK_KW)
    axr.plot([0], [1], transform=axr.transAxes, **BREAK_KW)
    axl.set_ylabel(ylabel)
    fig.suptitle(title)
    return fig, axl, axr


def series(axl, axr, ests, label, color):
    """ests: 4 (mean, lo, hi) tuples ordered Q1-2024, Q4-2025..Q2-2026."""
    m = [e[0] for e in ests]
    lo = [e[1] for e in ests]
    hi = [e[2] for e in ests]
    axl.errorbar([0], m[:1], yerr=[[m[0] - lo[0]], [hi[0] - m[0]]],
                 marker="o", capsize=3, color=color)
    x = [0, 1, 2]
    axr.plot(x, m[1:], marker="o", label=label, color=color)
    axr.fill_between(x, lo[1:], hi[1:], alpha=0.15, color=color)


def fig2(rows):
    fig, axl, axr = broken_axes(
        "share with traceable AI usage (%)",
        "Figure 2: Traceable AI usage over time (CW, 95% CI; floors)")
    pct = [("sub_pr", "AI% of submitted PRs", "tab:blue"),
           ("mrg_pr", "AI% of merged PRs", "tab:orange"),
           ("sub_loc", "AI-PR share of submitted LOC", "tab:green"),
           ("mrg_loc", "AI-PR share of merged LOC", "tab:red")]
    for key, label, color in pct:
        ests = [tuple(v * 100 for v in r[key]) for r in rows]
        series(axl, axr, ests, label, color)
    axl.set_ylim(bottom=0)
    axr.legend(fontsize=8, loc="upper left")
    fig.savefig("artifacts/fig2_ai_usage.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig2_ai_usage.png")


def fig3(rows):
    fig, axl, axr = broken_axes(
        "kLOC per core contributor / quarter",
        "Figure 3: Submitted and merged LOC per core contributor "
        "(CW, 95% CI)")
    series(axl, axr, [r["sub_kloc"] for r in rows],
           "submitted kLOC / core author", "tab:blue")
    series(axl, axr, [r["kloc"] for r in rows],
           "merged kLOC / core author (w8)", "tab:green")
    for i, r in enumerate(rows):
        ax, x = (axl, 0) if i == 0 else (axr, i - 1)
        ax.annotate(f"{r['sub_mult']:.2f}x", (x, r["sub_kloc"][0]),
                    textcoords="offset points", xytext=(6, 8), fontsize=8,
                    color="tab:blue")
        ax.annotate(f"{r['mult']:.2f}x", (x, r["kloc"][0]),
                    textcoords="offset points", xytext=(6, -14), fontsize=8,
                    color="tab:green")
    # Q2-2026 merged is w8-provisional (May/June windows open at AS_OF)
    axr.axvspan(1.6, 2.4, color="0.85", alpha=0.5, zorder=0,
                label="Q2 merged provisional (w8 windows open)")
    axr.legend(fontsize=8, loc="upper left")
    axl.set_ylim(bottom=0)
    fig.savefig("artifacts/fig3_core_loc.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig3_core_loc.png")


if __name__ == "__main__":
    fig2(usage_rows())
    fig3(core_rows())
