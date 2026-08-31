"""Figure A5: per-person productivity change among ACTIVE INSIDERS.

The strongest population in the productivity series: insider authors with
>= 10 submitted PRs in BOTH endpoint quarters, fleet excluded. The floor makes
"never used AI" a behavioural claim — dozens of PRs in which a marker
could have appeared, none did — where low-activity authors' non-detection
is mostly lack of opportunity.

Grid: rows = baseline quarter (Q4-2025, then Q1-2024 for the long arc);
columns = submitted kLOC/quarter, merged kLOC/quarter, PRs/quarter. Each
panel plots deciles of the PER-PERSON post/pre ratio for ever-AI vs
never-AI, on a log axis tick-labelled as % change; each curve's p50 is
ringed and quoted in the legend. The 0% line divides growers from
shrinkers: where a curve crosses it is the share of that group that
produced less than before.

The submitted-PRs/quarter column is the one that dodges the "AI writes verbose
code" objection: never-AI throughput is ~flat while detected adopters
ship ~24% more PRs.

Data:   artifacts/data/figure_a5_active_insider_deciles.csv
Output: artifacts/figure_a5_active_insider_deciles.png
Usage:  PYTHONPATH=src python scripts/plot_active_insider_deciles.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import PAIR_BLUE, PAIR_ORANGE, plt
from pipeline.studies.productivity import ACTIVE_FLOOR, active_insider_deciles

DECILES = list(range(10, 100, 10))
BASES = [("Q4-2025", "Q4-2025 → Q2-2026"),
         ("Q1-2024", "Q1-2024 → Q2-2026")]
METRICS = [("submitted", "submitted kLOC / quarter"),
           ("merged", "merged kLOC / quarter"),
           ("prs", "submitted PRs / quarter")]
GROUPS = [("ever_ai", "ever used AI (detected)", PAIR_ORANGE[0]),
          ("never_ai", "never used AI (detected)", PAIR_BLUE[0])]
NAME = "figure_a5_active_insider_deciles"
TICKS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 3, 5, 10, 20]
TICK_LABELS = ["-75%", "-50%", "-25%", "0%", "+25%", "+50%", "+75%",
               "+100%", "+200%", "+400%", "+900%", "+1900%"]


def collect() -> Table:
    t = Table(NAME)
    for pre, base_label in BASES:
        rows = active_insider_deciles(pre=pre)
        for metric, mlabel in METRICS:
            for group, glabel, _c in GROUPS:
                n = int(rows[(group, metric, "n")][0])
                t.add_series(f"{pre}|{metric}", group,
                             rows[(group, metric, "ratio")],
                             x_labels=[f"p{d}" for d in DECILES],
                             panel_label=f"{mlabel} — {base_label}",
                             series_label=f"{glabel} (n={n})")
    return t


def render(t: Table):
    fig, axes = plt.subplots(len(BASES), len(METRICS),
                             figsize=(4.2 * len(METRICS), 8),
                             squeeze=False, sharey=True)
    for r, (pre, _bl) in enumerate(BASES):
        for c, (metric, _ml) in enumerate(METRICS):
            ax = axes[r][c]
            panel = f"{pre}|{metric}"
            for group, _gl, color in GROUPS:
                pts = t.points(panel, group)
                if not pts:
                    continue
                mid = pts[len(pts) // 2]
                ax.plot([p["x"] for p in pts], [p["value"] for p in pts],
                        marker="o", ms=4, color=color,
                        label=f"{pts[0]['series_label']}  —  p50 "
                              f"{100 * (mid['value'] - 1):+.0f}%")
                ax.plot([mid["x"]], [mid["value"]], marker="o", ms=9,
                        mfc="none", mec=color, mew=1.6, zorder=5)
            ax.axhline(1.0, color="0.3", lw=0.8, zorder=0)
            ax.set_yscale("log")
            ax.set_yticks(TICKS, TICK_LABELS, fontsize=8)
            ax.grid(axis="y", color="0.92", lw=0.6, zorder=0)
            ax.set_xticks(range(len(DECILES)), [f"p{d}" for d in DECILES],
                          fontsize=7)
            ax.set_title(t.label_of(panel), fontsize=9, loc="left")
            if c == 0:
                ax.set_ylabel(f"per-person change (LOG scale)\n"
                              f">={ACTIVE_FLOOR} submitted PRs in both quarters")
            ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    figure_main(collect, render, f"artifacts/{NAME}.png")
