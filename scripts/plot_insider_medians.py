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

Data:   artifacts/data/insider_medians.csv
Output: artifacts/insider_medians.png
Usage:  PYTHONPATH=src python scripts/plot_insider_medians.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import PAIR_BLUE, PAIR_ORANGE, broken_pair, plt
from pipeline.frame import PERIODS
from pipeline.studies.productivity import (INSIDER_METRICS,
                                           INSIDER_POPULATIONS,
                                           INSIDER_SLICES, insider_medians)

NAME = "insider_medians"
COLORS = {"all": "0.25", "ever_ai": PAIR_ORANGE[0], "never_ai": PAIR_BLUE[0]}


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
    fig = plt.figure(figsize=(13, 7.5))
    subfigs = fig.subfigures(len(INSIDER_METRICS), len(INSIDER_POPULATIONS),
                             hspace=0.08, wspace=0.05)
    for r, (metric, mlabel) in enumerate(INSIDER_METRICS):
        for c, (pop, _plabel) in enumerate(INSIDER_POPULATIONS):
            panel = f"{metric}|{pop}"
            axl, axr = broken_pair(subfigs[r][c], t.label_of(panel))
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


if __name__ == "__main__":
    figure_main(collect, render, f"artifacts/{NAME}.png")
