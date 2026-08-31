"""Figure A4: how ACTIVE each group is — why the AI split needs the panel.

Detection needs a marker inside a PR, so a contributor's chance of ever
being detected scales with how many PRs they submit. That makes the
ever-AI / never-AI split only as meaningful as the activity behind it.

Two rows, one per population:
  PERIOD-ACTIVE INSIDERS — insiders with >=1 PR in the displayed period
                           (each column its own population). The never-AI
                           row's ~1.67 PRs/month describes THAT subset;
                           over the fixed set of never-AI insiders the
                           median is only ~6 window PRs (~8 among the
                           window-active), so detection opportunity for
                           the group as a whole is modest.
  BALANCED 9-MONTH PANEL — never-AI sits near 7 PRs/month, i.e. ~63 PRs
                           across the window without a marker, which is
                           evidence of non-use.

Columns are the three periods. Q1-2024 predates the tools entirely, so the
gap there is pure selection: what future adopters looked like two years
before adopting.

Data:   artifacts/data/figure_a4_activity_deciles.csv
Output: artifacts/figure_a4_activity_deciles.png
Usage:  PYTHONPATH=src python scripts/plot_activity_deciles.py
        PYTHONPATH=src python scripts/plot_activity_deciles.py --kloc
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import PAIR_BLUE, PAIR_ORANGE, plt
from pipeline.studies.productivity import ACTIVITY_PERIODS, activity_deciles

DECILES = list(range(10, 100, 10))
POPS = [("all", "period-active insiders", False),
        ("panel", "balanced 9-month panel", True)]
GROUPS = [("ever_ai", "ever used AI (detected)", PAIR_ORANGE[0]),
          ("never_ai", "never used AI (detected)", PAIR_BLUE[0])]
NAME = "figure_a4_activity_deciles"
KLOC_NAME = f"{NAME}_kloc"
UNITS = {"prs": "PRs / month", "kloc": "submitted kLOC / month"}


def table(metric: str, name: str = NAME) -> Table:
    t = Table(name)
    for pop, pop_label, balanced in POPS:
        rows = activity_deciles(balanced=balanced)
        for period, _desc in ACTIVITY_PERIODS:
            for group, glabel, _c in GROUPS:
                n = int(rows[(period, group, metric, "n")][0])
                t.add_series(f"{pop}|{period}", group,
                             rows[(period, group, metric, "deciles")],
                             x_labels=[f"p{d}" for d in DECILES],
                             panel_label=f"{pop_label} — {period}",
                             series_label=f"{glabel} (n={n})")
    return t


def collect() -> Table:
    return table("prs")


def collect_kloc() -> Table:
    return table("kloc", KLOC_NAME)      # own table: never clobber the
                                         # canonical PR-count CSV


def render(t: Table, unit: str = UNITS["prs"]):
    panels = t.panels()
    fig, axes = plt.subplots(len(POPS), len(ACTIVITY_PERIODS),
                             figsize=(4.0 * len(ACTIVITY_PERIODS), 7),
                             squeeze=False, sharey="row")
    for r, (pop, _pl, _b) in enumerate(POPS):
        for c, (period, _d) in enumerate(ACTIVITY_PERIODS):
            ax = axes[r][c]
            panel = f"{pop}|{period}"
            if panel not in panels:
                continue
            for group, _gl, color in GROUPS:
                pts = t.points(panel, group)
                ax.plot([p["x"] for p in pts], [p["value"] for p in pts],
                        marker="o", ms=4, color=color,
                        label=pts[0]["series_label"])
            ax.set_yscale("log")
            ax.set_xticks(range(len(DECILES)), [f"p{d}" for d in DECILES],
                          fontsize=7)
            ax.set_title(t.label_of(panel), fontsize=9, loc="left")
            ax.grid(axis="y", color="0.92", lw=0.6, zorder=0)
            if c == 0:
                ax.set_ylabel(f"{unit} (LOG scale)")
            ax.legend(fontsize=7, loc="upper left")
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    as_kloc = "--kloc" in sys.argv
    argv = [a for a in sys.argv[1:] if a != "--kloc"]
    figure_main(collect_kloc if as_kloc else collect,
                (lambda t: render(t, UNITS["kloc"])) if as_kloc else render,
                f"artifacts/{KLOC_NAME if as_kloc else NAME}.png", argv=argv)
