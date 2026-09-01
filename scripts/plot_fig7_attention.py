"""Figure 7: human attention proxies — AI-involved vs non-AI PRs.

Two broken-axis panels over mature merged human-reviewed PRs (pooled):
comments/kLOC (bot-clean human inline comments) and first-review latency
hours/kLOC (creation -> first human review, per kLOC). Dark = AI-involved
PRs, light = non-AI; the AI series is absent at the Q1-2024 baseline by
construction. Q2 is partial (w8 windows open at the AS_OF).

Data:   artifacts/data/attention_by_ai.csv
Output: artifacts/attention_by_ai.png
        (+ the *_monthly twin via plot_all --monthly)
Usage:  PYTHONPATH=src python scripts/plot_fig7_attention.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.analyze import month_window
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (BASELINE, PAIR_BLUE, broken_pair, cell,
                               month_series, plt, quarter_series,
                               shade_provisional, shade_q2_partial,
                               window_of)
from pipeline.studies.attention import PERIODS, attention_by_ai

SLICES = [("ai", PAIR_BLUE[0], "AI-involved PRs"),
          ("nonai", PAIR_BLUE[1], "non-AI PRs")]

PANELS = [("comments_per_kloc", "human comments per kLOC"),
          ("first_rev_h_per_kloc", "hours to first human review per kLOC")]


def collect() -> Table:
    rows = attention_by_ai()
    t = Table("attention_by_ai")
    for key, title in PANELS:
        for sl, _color, label in SLICES:
            t.add_series(key, sl, [cell(rows, p, sl, key) for p in PERIODS],
                         x_labels=PERIODS, panel_label=title,
                         series_label=label)
    return t


def render(t: Table):
    fig = plt.figure(figsize=(11, 4.4))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, (key, _title) in zip(subfigs.flat, PANELS):
        title = t.label_of(key)
        axl, axr = broken_pair(sf, title)
        for sl, color, label in SLICES:
            quarter_series(axl, axr, t.values(key, sl), color, label)
        shade_q2_partial(axr)
        axl.set_ylim(bottom=0)
        axl.set_ylabel(title)
        axr.legend(fontsize=8, loc="lower left")
    return fig


def collect_monthly(window: list[str] | None = None) -> Table:
    """Monthly twin (plot_all --monthly): month-keyed attention over the
    baseline + window months, provisional months in and shaded — unlike
    the Figure 3 companion, which EXCLUDES immature months (its per-kLOC
    rates on immature merged sets are undefined under its methodology).
    fleet_slice stays False: this is Figure 7's population."""
    window = window or month_window()
    months = BASELINE + window
    rows = attention_by_ai(granularity="month", window=window)
    t = Table("attention_by_ai_monthly")
    for key, title in PANELS:
        for sl, _color, label in SLICES:
            t.add_series(key, sl, [cell(rows, m, sl, key) for m in months],
                         x_labels=months, panel_label=title,
                         series_label=label)
    return t


def render_monthly(t: Table):
    window = window_of(t)
    fig = plt.figure(figsize=(11, 4.4))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, (key, _title) in zip(subfigs.flat, PANELS):
        title = t.label_of(key)
        axl, axr = broken_pair(sf, title, span="month", window=window)
        for sl, color, label in SLICES:
            vals = t.values(key, sl)
            month_series(axl, axr, vals[:len(BASELINE)],
                         vals[len(BASELINE):], color, label=label)
        shade_provisional(axr, window)
        axl.set_ylim(bottom=0)
        axl.set_ylabel(title)
        axr.legend(fontsize=8, loc="lower left")
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/attention_by_ai.png")
