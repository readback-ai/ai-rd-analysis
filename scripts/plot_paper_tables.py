"""Render paper figures 2 & 3 as line graphs with a broken x-axis.

Q1-2024 (the detector-validity baseline) sits ~7 quarters before the
continuous Q4-2025..Q2-2026 window, so each figure uses two panels sharing
the y-axis — a narrow left panel for Q1-2024 and a right panel for the
window — joined with standard axis-break marks. Shaded bands are the
bootstrap 95% CIs from pipeline.studies.paper_tables (CW, seeded).

Data:    artifacts/data/ai_usage.csv, artifacts/data/core_loc.csv
Outputs: artifacts/ai_usage.png, artifacts/core_loc.png
         (+ *_monthly twins via plot_all --monthly)

Usage:  PYTHONPATH=src python scripts/plot_paper_tables.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.analyze import month_window
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (BASELINE, broken_axes, broken_axes_month,
                               shade_provisional, shade_q2_partial,
                               window_of)
from pipeline.studies.paper_tables import core_rows, usage_rows

USAGE = [("sub_pr", "AI% of submitted PRs", "tab:blue"),
         ("mrg_pr", "AI% of merged PRs", "tab:orange"),
         ("sub_loc", "AI-PR share of submitted LOC", "tab:green"),
         ("mrg_loc", "AI-PR share of merged LOC", "tab:red")]

CORE = [("sub_kloc", "sub_mult", "submitted kLOC / insider contributor",
         "tab:blue", (6, 8)),
        ("kloc", "mult", "merged kLOC / insider contributor (w8)",
         "tab:green", (6, -14))]


def series(axl, axr, pts, label, color):
    """pts: 4 (mean, lo, hi) point dicts ordered Q1-2024, Q4-2025..Q2-2026."""
    m = [p["value"] for p in pts]
    lo = [p["lo"] for p in pts]
    hi = [p["hi"] for p in pts]
    axl.errorbar([0], m[:1], yerr=[[m[0] - lo[0]], [hi[0] - m[0]]],
                 marker="o", capsize=3, color=color)
    x = [0, 1, 2]
    axr.plot(x, m[1:], marker="o", label=label, color=color)
    axr.fill_between(x, lo[1:], hi[1:], alpha=0.15, color=color)


def usage_table(rows: list, name: str) -> Table:
    """Figure 2's table over whichever period grain `rows` carries —
    shared with the monthly variant."""
    t = Table(name)
    for key, label, _color in USAGE:
        for i, r in enumerate(rows):
            mean, lo, hi = (v * 100 for v in r[key])
            t.add("usage", key, i, mean, lo=lo, hi=hi,
                  panel_label="share with traceable AI usage (%)",
                  series_label=label, x_label=r["period"])
    return t


def collect_usage() -> Table:
    return usage_table(usage_rows(), "ai_usage")


def render_usage(t: Table):
    fig, axl, axr = broken_axes(t.label_of("usage"))
    for key, label, color in USAGE:
        series(axl, axr, t.points("usage", key), label, color)
    axl.set_ylim(bottom=0)
    axr.legend(fontsize=8, loc="upper left")
    return fig


def core_table(rows: list, name: str, unit: str = "quarter") -> Table:
    """Figure 3's table over whichever per-author statistic `rows` carries
    — shared with the median variant and the monthly twins.
    Monthly rows carry no baseline multiples (paper_tables.core_rows),
    so their mult series are simply not emitted."""
    t = Table(name)
    panel_label = f"kLOC per insider contributor / {unit}"
    for key, mult_key, label, _color, _offset in CORE:
        for i, r in enumerate(rows):
            mean, lo, hi = r[key]
            t.add("core_loc", key, i, mean, lo=lo, hi=hi,
                  panel_label=panel_label,
                  series_label=label, x_label=r["period"])
            if mult_key in r:
                t.add("core_loc", mult_key, i, r[mult_key],
                      panel_label=panel_label,
                      series_label=f"{label} (x baseline)",
                      x_label=r["period"])
    return t


def collect_core() -> Table:
    return core_table(core_rows(), "core_loc")


def render_core(t: Table):
    fig, axl, axr = broken_axes(t.label_of("core_loc"))
    for key, _mult_key, label, color, _offset in CORE:
        series(axl, axr, t.points("core_loc", key), label, color)
    for i in range(len(t.points("core_loc", CORE[0][0]))):
        ax, x = (axl, 0) if i == 0 else (axr, i - 1)
        for key, mult_key, _label, color, offset in CORE:
            mult = t.points("core_loc", mult_key)[i]["value"]
            ax.annotate(f"{mult:.2f}x",
                        (x, t.points("core_loc", key)[i]["value"]),
                        textcoords="offset points", xytext=offset,
                        fontsize=8, color=color)
    # Q2-2026 merged is w8-provisional (May/June windows open at AS_OF)
    shade_q2_partial(axr, label="Q2 merged provisional (w8 windows open)")
    axr.legend(fontsize=8, loc="upper left")
    axl.set_ylim(bottom=0)
    return fig


def series_month(axl, axr, pts, label, color):
    """Month-domain sibling of series(): baseline months as errorbars on
    the left, the window as a line with its CI band on the right. Months
    below the repo floor carry NaN estimates and plot as gaps."""
    m = [p["value"] for p in pts]
    lo = [p["lo"] for p in pts]
    hi = [p["hi"] for p in pts]
    nb = len(BASELINE)
    axl.errorbar(range(nb), m[:nb],
                 yerr=[[v - low for v, low in zip(m[:nb], lo[:nb])],
                       [h - v for v, h in zip(m[:nb], hi[:nb])]],
                 marker="o", ms=3, capsize=2, color=color)
    x = range(len(m) - nb)
    axr.plot(x, m[nb:], marker="o", ms=3, label=label, color=color)
    axr.fill_between(x, lo[nb:], hi[nb:], alpha=0.15, color=color)


def collect_usage_monthly(window: list[str] | None = None) -> Table:
    """Monthly twin of Figure 2 (plot_all --monthly): month-keyed rows,
    2-PR/month repo floor, provisional months in and shaded at render."""
    window = window or month_window()
    return usage_table(usage_rows(granularity="month", window=window),
                       "ai_usage_monthly")


def render_usage_monthly(t: Table):
    fig, axl, axr = broken_axes_month(t.label_of("usage"), window_of(t))
    for key, label, color in USAGE:
        series_month(axl, axr, t.points("usage", key), label, color)
    shade_provisional(axr, window_of(t))
    axl.set_ylim(bottom=0)
    axr.legend(fontsize=8, loc="upper left")
    return fig


def collect_core_monthly(window: list[str] | None = None) -> Table:
    """Monthly twin of Figure 3 (plot_all --monthly): no baseline
    multiples (core_rows omits them per month), provisional months in
    and shaded at render."""
    window = window or month_window()
    return core_table(core_rows(granularity="month", window=window),
                      "core_loc_monthly", unit="month")


def render_core_monthly(t: Table):
    window = window_of(t)
    fig, axl, axr = broken_axes_month(t.label_of("core_loc"), window)
    for key, _mult_key, label, color, _offset in CORE:
        series_month(axl, axr, t.points("core_loc", key), label, color)
    shade_provisional(axr, window,
                      label="w8 windows open (merged provisional)")
    axr.legend(fontsize=8, loc="upper left")
    axl.set_ylim(bottom=0)
    return fig


if __name__ == "__main__":
    figure_main(collect_usage, render_usage, "artifacts/ai_usage.png")
    figure_main(collect_core, render_core, "artifacts/core_loc.png")
