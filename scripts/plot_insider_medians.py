"""Figure 3b: the MEDIAN insider author's kLOC per quarter — person-level.

One number per person (kLOC pooled across every repo they author in),
then the median across people: no repo weighting, no two-stage
aggregation, so "median" means the middle insider. Three populations
(columns), all excluding fleet operators:

  any        — period-active insiders (>=1 PR in the quarter)
  productive — insiders with >=10 submitted PRs in the quarter
  panel      — insiders active in all four study quarters (same people
               throughout; survivor-selected)

Rows: submitted kLOC (no censoring) and merged kLOC (w8 rule). Series:
all insiders, ever-AI, never-AI (any AI-involved PR in the window). Bands
are seeded percentile bootstraps of the median over persons; n per
quarter is in the CSV (n_<slice> series) and the legend quotes the
Q1-2024 -> Q2-2026 membership. Broken x-axis: Q1-2024 | Q4-2025..Q2-2026.

Growth variant (insider_medians_growth): the same grid with every series
divided by its own Q1-2024 median, so each population and slice starts
at 1.0 and the panels compare growth rather than levels; the
all-insiders multiples are annotated, the AI/non-AI curves are not.

Data:    artifacts/data/insider_medians.csv,
         artifacts/data/insider_medians_growth.csv
Outputs: artifacts/insider_medians.png, artifacts/insider_medians_growth.png
Usage:   PYTHONPATH=src python scripts/plot_insider_medians.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import PAIR_BLUE, PAIR_ORANGE, broken_pair, plt
from pipeline.frame import PERIODS
from pipeline.studies.productivity import (INSIDER_METRICS,
                                           INSIDER_POPULATIONS,
                                           INSIDER_SLICES, insider_growth,
                                           insider_medians)

NAME = "insider_medians"
COLORS = {"all": "0.25", "ever_ai": PAIR_ORANGE[0], "never_ai": PAIR_BLUE[0]}
# column titles: short and wrapped so adjacent panels never collide; the
# full population definition stays in the CSV's panel_label
COLUMN_TITLES = {
    "any": "period-active insiders\n(≥1 PR in the quarter)",
    "productive": "productive insiders\n(≥10 submitted PRs in the quarter)",
    "panel": "balanced panel\n(≥1 PR in all four quarters)",
}


def collect() -> Table:
    rows = insider_medians()
    t = Table(NAME)
    for metric, mlabel in INSIDER_METRICS:
        for pop, plabel in INSIDER_POPULATIONS:
            panel = f"{metric}|{pop}"
            for sl, slabel in INSIDER_SLICES:
                cells = [rows[(pop, sl, metric, q)] for q in PERIODS]
                for i, (q, c) in enumerate(zip(PERIODS, cells)):
                    t.add(panel, sl, i, c["median"], lo=c["lo"], hi=c["hi"],
                          panel_label=f"{mlabel} — {plabel}",
                          series_label=slabel, x_label=q)
                    t.add(panel, f"n_{sl}", i, c["n"],
                          panel_label=f"{mlabel} — {plabel}",
                          series_label=f"n, {slabel}", x_label=q)
    return t


def _series(axl, axr, pts, label, color):
    """Baseline point with its CI as an errorbar on the left panel; the
    window as a line with its CI band on the right."""
    m = [p["value"] for p in pts]
    lo = [p["lo"] for p in pts]
    hi = [p["hi"] for p in pts]
    axl.errorbar([0], m[:1], yerr=[[m[0] - lo[0]], [hi[0] - m[0]]],
                 marker="o", ms=4, capsize=3, color=color)
    x = [0, 1, 2]
    axr.plot(x, m[1:], marker="o", ms=3, label=label, color=color)
    axr.fill_between(x, lo[1:], hi[1:], alpha=0.15, color=color)


def render(t: Table):
    fig = plt.figure(figsize=(13, 8))
    subfigs = fig.subfigures(len(INSIDER_METRICS), len(INSIDER_POPULATIONS),
                             hspace=0.1, wspace=0.05)
    for r, (metric, mlabel) in enumerate(INSIDER_METRICS):
        for c, (pop, _plabel) in enumerate(INSIDER_POPULATIONS):
            panel = f"{metric}|{pop}"
            # column title on the top row only; the row's y-label names
            # the metric, so lower panels need no title
            title = COLUMN_TITLES[pop] if r == 0 else ""
            axl, axr = broken_pair(subfigs[r][c], title)
            for sl, slabel in INSIDER_SLICES:
                pts = t.points(panel, sl)
                n = [int(p["value"]) for p in t.points(panel, f"n_{sl}")]
                _series(axl, axr, pts, f"{slabel} (n {n[0]}→{n[-1]})",
                        COLORS[sl])
            axl.set_ylim(bottom=0)
            if c == 0:
                axl.set_ylabel(mlabel)
            axr.legend(fontsize=7, loc="upper left")
    return fig


GROWTH_NAME = "insider_medians_growth"


def collect_growth() -> Table:
    """Growth variant: every series divided by its own Q1-2024 median, so
    each population and slice starts at 1.0 and the panels compare growth
    rather than levels (insider_growth)."""
    rows = insider_growth()
    t = Table(GROWTH_NAME)
    for metric, mlabel in INSIDER_METRICS:
        for pop, plabel in INSIDER_POPULATIONS:
            panel = f"{metric}|{pop}"
            for sl, slabel in INSIDER_SLICES:
                for i, q in enumerate(PERIODS):
                    c = rows[(pop, sl, metric, q)]
                    t.add(panel, sl, i, c["mult"], lo=c["lo"], hi=c["hi"],
                          panel_label=f"{mlabel} — {plabel}",
                          series_label=slabel, x_label=q)
                    t.add(panel, f"n_{sl}", i, c["n"],
                          panel_label=f"{mlabel} — {plabel}",
                          series_label=f"n, {slabel}", x_label=q)
    return t


def render_growth(t: Table):
    """Same grid as render(); y is the multiple of each series' own
    Q1-2024 median. Only the all-insiders series is annotated with its
    multiples (the AI/non-AI curves stay unlabelled), like Figure 2."""
    fig = plt.figure(figsize=(13, 8))
    subfigs = fig.subfigures(len(INSIDER_METRICS), len(INSIDER_POPULATIONS),
                             hspace=0.1, wspace=0.05)
    for r, (metric, mlabel) in enumerate(INSIDER_METRICS):
        for c, (pop, _plabel) in enumerate(INSIDER_POPULATIONS):
            panel = f"{metric}|{pop}"
            title = COLUMN_TITLES[pop] if r == 0 else ""
            axl, axr = broken_pair(subfigs[r][c], title)
            for sl, slabel in INSIDER_SLICES:
                pts = t.points(panel, sl)
                n = [int(p["value"]) for p in t.points(panel, f"n_{sl}")]
                _series(axl, axr, pts, f"{slabel} (n {n[0]}→{n[-1]})",
                        COLORS[sl])
            for i, p in enumerate(t.points(panel, "all")):
                ax, x = (axl, 0) if i == 0 else (axr, i - 1)
                ax.annotate(f"{p['value']:.2f}x", (x, p["value"]),
                            textcoords="offset points", xytext=(6, 6),
                            fontsize=8, color=COLORS["all"])
            axr.axhline(1.0, color="0.7", lw=0.8, zorder=0)
            axl.set_ylim(bottom=0)
            if c == 0:
                axl.set_ylabel(f"× own Q1-2024 median — {mlabel}")
            axr.legend(fontsize=7, loc="upper left")
    return fig


if __name__ == "__main__":
    figure_main(collect, render, f"artifacts/{NAME}.png")
    figure_main(collect_growth, render_growth, f"artifacts/{GROWTH_NAME}.png")
