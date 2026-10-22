"""Figure 3b: the MEDIAN insider author's kLOC per quarter — person-level,
one figure per population.

One number per person (kLOC pooled across every repo they author in),
then the median across people: no repo weighting, no two-stage
aggregation, so "median" means the middle insider. Each figure is one
population (fleet operators excluded from all), two panels (submitted
kLOC, no censoring | merged kLOC, w8 rule), three series (all insiders,
ever-AI, never-AI — any AI-involved PR in the window):

  productive — insider_medians_productive: panel members with >=5
               submitted PRs in every study quarter and a mean of >=10
               per quarter over all four (membership decided once, the
               baseline weighted like any other quarter, so nobody near
               the floor pops in and out and window ramp-ups are not
               selected for) — the headline population
  active     — insider_medians_active: period-active insiders (>=1 PR in
               the quarter; the only population whose membership changes)
  panel      — insider_medians_panel: insiders active in all four study
               quarters (same people throughout; survivor-selected)

Bands are seeded percentile bootstraps of the median over persons; n per
quarter is in the CSV (n_<slice> series) and the legend quotes the
Q1-2024 -> Q2-2026 membership. Broken x-axis: Q1-2024 | Q4-2025..Q2-2026.

Growth twins (insider_medians_growth_<population>): every series divided
by its own Q1-2024 median, so each slice starts at 1.0 and the panels
compare growth rather than levels; the all-insiders multiples are
annotated, the AI/non-AI curves are not.

Data:    artifacts/data/insider_medians_{productive,active,panel}.csv
         artifacts/data/insider_medians_growth_{productive,active,panel}.csv
Outputs: the matching PNGs under artifacts/
Usage:   PYTHONPATH=src python scripts/plot_insider_medians.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import PAIR_BLUE, PAIR_ORANGE, broken_pair, plt
from pipeline.frame import PERIODS
from pipeline.studies.productivity import (INSIDER_METRICS,
                                           INSIDER_POPULATIONS,
                                           INSIDER_SLICES, _insider_cells,
                                           insider_growth, insider_medians)

COLORS = {"all": "0.25", "ever_ai": PAIR_ORANGE[0], "never_ai": PAIR_BLUE[0]}
# output stem per population key
STEMS = {"any": "active", "productive": "productive", "panel": "panel"}
# short population line for the panel titles; the full definition stays
# in the CSV's panel_label
POP_TITLES = {
    "any": "period-active insiders (≥1 PR in the quarter)",
    "productive": "productive panel (≥5 PRs every quarter, mean ≥10)",
    "panel": "balanced panel (≥1 PR in all four quarters)",
}
_ROWS: dict = {}


def stem(pop: str, growth: bool = False) -> str:
    return f"insider_medians{'_growth' if growth else ''}_{STEMS[pop]}"


def _rows(growth: bool) -> dict:
    """The study's cells, computed once per process and shared by the six
    figures (plot_all renders them in one run)."""
    if "cells" not in _ROWS:
        _ROWS["cells"] = _insider_cells()
    key = "growth" if growth else "medians"
    if key not in _ROWS:
        fn = insider_growth if growth else insider_medians
        _ROWS[key] = fn(cells=_ROWS["cells"])
    return _ROWS[key]


def _table(pop: str, rows: dict, name: str, value_key: str) -> Table:
    plabel = dict(INSIDER_POPULATIONS)[pop]
    t = Table(name)
    for metric, mlabel in INSIDER_METRICS:
        for sl, slabel in INSIDER_SLICES:
            for i, q in enumerate(PERIODS):
                c = rows[(pop, sl, metric, q)]
                t.add(metric, sl, i, c[value_key], lo=c["lo"], hi=c["hi"],
                      panel_label=f"{mlabel} — {plabel}",
                      series_label=slabel, x_label=q)
                t.add(metric, f"n_{sl}", i, c["n"],
                      panel_label=f"{mlabel} — {plabel}",
                      series_label=f"n, {slabel}", x_label=q)
    return t


def collect(pop: str) -> Table:
    return _table(pop, _rows(growth=False), stem(pop), "median")


def collect_growth(pop: str) -> Table:
    return _table(pop, _rows(growth=True), stem(pop, growth=True), "mult")


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


def _panels(t: Table, pop: str, ylabel: str, annotate_all: bool):
    """Two broken-pair panels (submitted | merged) for one population.
    Titles: the metric on line one, the population on line two."""
    fig = plt.figure(figsize=(11, 4.8))
    subfigs = fig.subfigures(1, len(INSIDER_METRICS), wspace=0.05)
    for sf, (metric, mlabel) in zip(subfigs.flat, INSIDER_METRICS):
        axl, axr = broken_pair(sf, f"{mlabel}\n{POP_TITLES[pop]}")
        for sl, slabel in INSIDER_SLICES:
            pts = t.points(metric, sl)
            n = [int(p["value"]) for p in t.points(metric, f"n_{sl}")]
            _series(axl, axr, pts, f"{slabel} (n {n[0]}→{n[-1]})",
                    COLORS[sl])
        if annotate_all:
            for i, p in enumerate(t.points(metric, "all")):
                ax, x = (axl, 0) if i == 0 else (axr, i - 1)
                ax.annotate(f"{p['value']:.2f}x", (x, p["value"]),
                            textcoords="offset points", xytext=(6, 6),
                            fontsize=8, color=COLORS["all"])
            axr.axhline(1.0, color="0.7", lw=0.8, zorder=0)
        axl.set_ylim(bottom=0)
        axl.set_ylabel(ylabel)
        axr.legend(fontsize=7, loc="upper left")
    return fig


def render(t: Table, pop: str):
    return _panels(t, pop, "median kLOC / insider / quarter",
                   annotate_all=False)


def render_growth(t: Table, pop: str):
    """Only the all-insiders series is annotated with its multiples (the
    AI/non-AI curves stay unlabelled), like Figure 2."""
    return _panels(t, pop, "× own Q1-2024 median", annotate_all=True)


def figures() -> list[tuple]:
    """(output path, collect, render) for the six figures, in plot_all's
    shape."""
    import functools
    out = []
    for pop, _label in INSIDER_POPULATIONS:
        out.append((f"artifacts/{stem(pop)}.png",
                    functools.partial(collect, pop),
                    functools.partial(render, pop=pop)))
        out.append((f"artifacts/{stem(pop, growth=True)}.png",
                    functools.partial(collect_growth, pop),
                    functools.partial(render_growth, pop=pop)))
    return out


if __name__ == "__main__":
    for out, coll, rend in figures():
        figure_main(coll, rend, out)
