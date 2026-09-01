"""Figure A3: the productivity DISTRIBUTION before and after, by AI use.

Balanced panel — contributors with >=1 PR in every window month, so a
shift in these curves is the same people changing, not the population
changing. One panel per group (all non-fleet / ever used AI / never used
AI / fleet operators); x is the decile of the group's own distribution,
y is kLOC on a log scale, with the pre and post curves overlaid.

The question the figure answers: is growth BROAD (the whole curve lifts)
or CONCENTRATED (only the upper deciles move)? A group whose lower
deciles lift as much as its upper ones grew across its membership.

"never used AI" means never DETECTABLY — detection is a floor, so that
group contains undetected use, which biases against finding a gap
between the groups.

Two variants:
  productivity_deciles_monthly          endpoints 2025-10 vs 2026-06
  productivity_deciles_quarterly   Oct-Dec vs Apr-Jun means

Read the QUARTERLY one for trend: single months are dominated by
volatility (the monthly endpoint ratio spans p10 0.08x to p90 19.9x), and
averaging three months at each end collapses most of that.

Data:   artifacts/data/productivity_deciles_monthly.csv
Output: artifacts/productivity_deciles_monthly.png
Usage:  PYTHONPATH=src python scripts/plot_productivity_deciles.py
        PYTHONPATH=src python scripts/plot_productivity_deciles.py --quarterly
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import PAIR_BLUE, PAIR_ORANGE, plt
from pipeline.studies.productivity import DECILE_GROUPS, productivity_deciles

DECILES = list(range(10, 100, 10))
NAME = "productivity_deciles_monthly"
QUARTERLY_NAME = "productivity_deciles_quarterly"


def table(rows: dict, name: str, pre_label: str, post_label: str) -> Table:
    t = Table(name)
    label_of = dict(DECILE_GROUPS)
    for group, desc in DECILE_GROUPS:
        n = int(rows[(group, "submitted", "n")][0])
        for metric in ("submitted", "merged"):
            # pre == 0 members carry no change ratio (codex review P1):
            # the ratio series is a smaller sample than the membership
            n_ratio = int(rows[(group, metric, "n_ratio")][0])
            for series in ("pre", "post", "ratio"):
                label = {"pre": f"{metric} {pre_label}",
                         "post": f"{metric} {post_label}",
                         "ratio": f"{metric} change (n={n_ratio})"}[series]
                t.add_series(f"{group}|{metric}", f"{metric}_{series}",
                             rows[(group, metric, series)],
                             x_labels=[f"p{d}" for d in DECILES],
                             panel_label=f"{label_of[group]} (n={n})",
                             series_label=label)
    return t


def collect() -> Table:
    return table(productivity_deciles(basis="month"), NAME,
                 "2025-10", "2026-06")


def collect_quarterly() -> Table:
    return table(productivity_deciles(basis="quarter"), QUARTERLY_NAME,
                 "Oct-Dec 2025", "Apr-Jun 2026")


GROUP_STYLE = {"all": ("0.45", "-"), "ever_ai": (PAIR_ORANGE[0], "-"),
               "never_ai": (PAIR_BLUE[0], "-"), "fleet": ("tab:green", "--")}
# ratio -> "% change" ticks. Denser through 0..+100%, where the group
# medians sit, and coarse in the tails where only the extremes live.
TICKS = [0.25, 0.5, 0.75, 1, 1.25, 1.5, 1.75, 2, 3, 5, 10, 20]
TICK_LABELS = ["-75%", "-50%", "-25%", "0%", "+25%", "+50%", "+75%",
               "+100%", "+200%", "+400%", "+900%", "+1900%"]


def render(t: Table):
    """Deciles of the PER-CONTRIBUTOR change, all groups on shared axes.

    Each contributor's own post/pre ratio is computed first, then the
    deciles of those ratios — never a ratio of deciles, which would
    describe different people at each end. The y axis is the ratio on a
    log scale, tick-labelled as percentage change; the line at 0% is no
    change, so the decile at which a group's curve crosses it is the
    share of that group who produced less than before."""
    fig, axes = plt.subplots(1, 2, figsize=(12, 5), squeeze=False,
                             sharey=True)
    for col, metric in enumerate(("submitted", "merged")):
        ax = axes[0][col]
        for group, desc in DECILE_GROUPS:
            panel = f"{group}|{metric}"
            pts = t.points(panel, f"{metric}_ratio")
            if not pts:
                continue
            color, ls = GROUP_STYLE[group]
            # p50 goes in the legend: four annotations at one x collide
            mid = pts[len(pts) // 2]
            # panel label carries the full membership n; the series label
            # carries the ratio sample (pre == 0 members drop out)
            ratio_n = pts[0]["series_label"].split("(n=")[1].rstrip(")")
            group_name = t.label_of(panel).split(" (n=")[0]
            ax.plot([p["x"] for p in pts], [p["value"] for p in pts],
                    marker="o", ms=4, ls=ls, color=color,
                    label=f"{group_name} (n={ratio_n})  —  p50 "
                          f"{100 * (mid['value'] - 1):+.0f}%")
            ax.plot([mid["x"]], [mid["value"]], marker="o", ms=9,
                    mfc="none", mec=color, mew=1.6, zorder=5)
        ax.axhline(1.0, color="0.3", lw=0.8, zorder=0)
        ax.set_yscale("log")
        ax.set_yticks(TICKS, TICK_LABELS, fontsize=8)
        ax.grid(axis="y", color="0.9", lw=0.6, zorder=0)
        ax.set_xticks(range(len(DECILES)), [f"p{d}" for d in DECILES],
                      fontsize=8)
        ax.set_xlabel("decile of the change distribution")
        ax.set_title(f"{metric} kLOC per contributor", fontsize=10,
                     loc="left")
        if col == 0:
            ax.set_ylabel("change vs the earlier period (LOG scale)")
        ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    quarterly = "--quarterly" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--quarterly"]
    figure_main(collect_quarterly if quarterly else collect, render,
                f"artifacts/{QUARTERLY_NAME if quarterly else NAME}.png",
                argv=argv)
