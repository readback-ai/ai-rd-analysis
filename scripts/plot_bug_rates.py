"""Bug-labeled issues per risk window on the balanced panel — pooled and
median repo, both exposure denominators.

Two broken-axis panels (Q1-2024 | Q4-2025..Q2-2026): issues per
PR-risk-window and per kLOC-risk-window, from
pipeline.studies.churn.exposure_cuts — the same cuts the appendix table
prints. Every merged PR opens a 28-day window at its merge day; a
quarter's rate is the issues filed on its days over the exposure carried
on those days. Balanced panel = repos rated in every quarter, so the
trend cannot be composition; the panel size is in each title. Dark =
pooled (sum over sum), light dashed = median repo — read them together,
since pooled rates can be dominated by single large repos.

Data:   artifacts/data/bug_rates.csv
Output: artifacts/bug_rates.png
Usage:  PYTHONPATH=src python scripts/plot_bug_rates.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import PAIR_BLUE, broken_pair, plt, quarter_series
from pipeline.studies import churn

NAME = "bug_rates"
PANELS = [("per_pr", "bug-labeled issues per PR-risk-window",
           "pooled_per_pr", "median_per_pr"),
          ("per_kloc", "bug-labeled issues per kLOC-risk-window",
           "pooled_per_kloc", "median_per_kloc")]
SERIES = [("pooled", PAIR_BLUE[0], "-", "pooled (sum / sum)"),
          ("median", PAIR_BLUE[1], "--", "median repo")]


def collect() -> Table:
    rows, (periods, meta) = churn.exposure_rows("quarter")
    rows = [r for r in rows if r["repo"] in meta["label_users"]]
    cuts = churn.exposure_cuts(rows, periods, meta)
    n = cuts[(periods[0], "balanced")]["repos"]   # constant by construction
    t = Table(NAME)
    for panel, title, pooled_key, median_key in PANELS:
        label = f"{title} — balanced panel, n={n}"
        for (series, _c, _ls, series_label), key in zip(
                SERIES, (pooled_key, median_key)):
            t.add_series(panel, series,
                         [cuts[(p, "balanced")][key] for p in periods],
                         x_labels=periods, panel_label=label,
                         series_label=series_label)
    return t


def render(t: Table):
    fig = plt.figure(figsize=(11, 4.4))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, (panel, title, _pk, _mk) in zip(subfigs.flat, PANELS):
        axl, axr = broken_pair(sf, t.label_of(panel))
        for series, color, ls, label in SERIES:
            quarter_series(axl, axr, t.values(panel, series), color, label,
                           ls=ls)
        axl.set_ylim(bottom=0)
        axl.set_ylabel(title)
        axr.legend(fontsize=8, loc="upper right")
    return fig


if __name__ == "__main__":
    figure_main(collect, render, f"artifacts/{NAME}.png")
