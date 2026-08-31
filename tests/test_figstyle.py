"""Figure toolkit (pipeline.figstyle) — the house style that was copied
across the 11 plot scripts (architecture review 2026-07-22, candidate 2:
`broken_pair` character-identical in 7 files, the provisional band's
axvspan(1.6, 2.4) in 11 places, the zero-denominator suppression rule
diverged between copies, plot_fig6_review{,_ai}.py twin files).

Every constant asserted here is the LEGACY value lifted verbatim from the
scripts, so the migration is provably style-preserving.
"""
import pathlib

import matplotlib

from pipeline import figstyle
from pipeline.figstyle import (BASELINE, LOC_SERIES, WINDOW, broken_axes,
                               broken_pair, cell, month_series,
                               paired_series6, quarter_series, save,
                               shade_q2_partial, shade_span)


def _labels(ax):
    return [t.get_text() for t in ax.get_xticklabels()]


def test_backend_is_agg():
    """Importing the toolkit selects Agg, replacing the per-script
    matplotlib.use("Agg") boilerplate."""
    assert matplotlib.get_backend().lower() == "agg"


def test_broken_pair_quarter_geometry():
    """Legacy broken_pair verbatim (plot_fig6_review.py and 5 siblings):
    left panel Q1-24 at x=0, right panel Q4-25..Q2-26 at 0..2, joined
    spines hidden, break marks drawn, left-aligned title."""
    fig = figstyle.plt.figure()
    sf = fig.subfigures(1, 1)
    axl, axr = broken_pair(sf, "share of merged PRs")
    assert axl.get_xlim() == (-0.5, 0.5)
    assert list(axl.get_xticks()) == [0] and _labels(axl) == ["Q1-24"]
    assert axr.get_xlim() == (-0.4, 2.4)
    assert list(axr.get_xticks()) == [0, 1, 2]
    assert _labels(axr) == ["Q4-25", "Q1-26", "Q2-26"]
    assert not axl.spines.right.get_visible()
    assert not axr.spines.left.get_visible()
    assert axl.get_title(loc="left") == "share of merged PRs"
    # two break marks per panel
    assert len(axl.lines) == 2 and len(axr.lines) == 2
    figstyle.plt.close(fig)


def test_broken_pair_month_geometry():
    """Legacy month variant verbatim (plot_fig5_fleet.py /
    plot_adoption_cohorts.py): Q1-2024 months on the left, the
    Oct-2025..Jun-2026 window on the right, ticks at [0, 3, 6, 8]."""
    fig = figstyle.plt.figure()
    sf = fig.subfigures(1, 1)
    axl, axr = broken_pair(sf, "fleet operators", span="month")
    assert axl.get_xlim() == (-0.5, len(BASELINE) - 0.5)
    assert list(axl.get_xticks()) == [1] and _labels(axl) == ["Q1-24"]
    assert axr.get_xlim() == (-0.5, len(WINDOW) - 0.5)
    assert list(axr.get_xticks()) == [0, 3, 6, 8]
    assert _labels(axr) == [WINDOW[i][2:7] for i in (0, 3, 6, 8)]
    figstyle.plt.close(fig)


def test_broken_pair_month_custom_window():
    """Monthly figures restricted to w8-final months pass their own
    window: the right panel's domain and tick set follow it (ticks at
    months [0, 3, 6, last])."""
    fig = figstyle.plt.figure()
    sf = fig.subfigures(1, 1)
    window = WINDOW[:8]                       # through 2026-05
    axl, axr = broken_pair(sf, "t", span="month", window=window)
    assert axl.get_xlim() == (-0.5, len(BASELINE) - 0.5)
    assert axr.get_xlim() == (-0.5, len(window) - 0.5)
    assert list(axr.get_xticks()) == [0, 3, 6, 7]
    assert _labels(axr) == [window[i][2:7] for i in (0, 3, 6, 7)]
    figstyle.plt.close(fig)


def test_broken_pair_month_marks_every_month():
    """Figure 3 companion: month_marks=True labels EVERY plotted month
    on both panels (replacing the sparse tick set and the Q1-24 baseline
    label); the default keeps the legacy sparse-ticks-only axes."""
    fig = figstyle.plt.figure()
    sf = fig.subfigures(1, 2)
    window = WINDOW[:8]
    axl, axr = broken_pair(sf.flat[0], "t", span="month", window=window,
                           month_marks=True)
    assert list(axl.get_xticks()) == list(range(len(BASELINE)))
    assert _labels(axl) == [m[2:7] for m in BASELINE]
    assert list(axr.get_xticks()) == list(range(len(window)))
    assert _labels(axr) == [m[2:7] for m in window]
    dl, dr = broken_pair(sf.flat[1], "t", span="month")
    assert list(dl.get_xticks()) == [1] and _labels(dl) == ["Q1-24"]
    assert list(dr.get_xticks()) == [0, 3, 6, 8]
    figstyle.plt.close(fig)


def test_broken_pair_month_short_window_ticks():
    """broken_pair month ticks crash on windows shorter than 7 months:
    the sparse tick set [0, 3, 6, last] indexes past the end of a short
    window (reachable via fig3-comp's maturity filter and month_window
    truncation). Short windows keep the in-range sparse ticks plus the
    last month."""
    fig = figstyle.plt.figure()
    sf = fig.subfigures(1, 1)
    axl, axr = broken_pair(sf, "t", span="month", window=WINDOW[:5])
    assert list(axr.get_xticks()) == [0, 3, 4]
    assert _labels(axr) == [WINDOW[0][2:7], WINDOW[3][2:7], WINDOW[4][2:7]]
    figstyle.plt.close(fig)


def test_broken_axes_paper_variant():
    """Legacy plot_paper_tables.broken_axes: its own figure, full-length
    quarter labels, ylabel on the left panel."""
    fig, axl, axr = broken_axes("share (%)")
    assert axl.get_xlim() == (-0.5, 0.5) and _labels(axl) == ["Q1-2024"]
    assert axr.get_xlim() == (-0.4, 2.4)
    assert _labels(axr) == ["Q4-2025", "Q1-2026", "Q2-2026"]
    assert axl.get_ylabel() == "share (%)"
    assert fig.get_size_inches().tolist() == [8, 4.5]
    figstyle.plt.close(fig)


def test_figures_carry_no_caption():
    """Captions belong in the paper text, not baked into the image: no
    figure sets a suptitle, so the rendered canvas is the plot alone."""
    fig, _axl, _axr = broken_axes("share (%)")
    assert fig._suptitle is None
    figstyle.plt.close(fig)


def test_no_plot_script_sets_a_caption():
    """The convention holds across every figure, not just the shared
    helper — a caption baked into one script would print twice once the
    paper supplies its own."""
    scripts = pathlib.Path(__file__).resolve().parents[1] / "scripts"
    offenders = [p.name for p in sorted(scripts.glob("plot_*.py"))
                 if "suptitle" in p.read_text()]
    assert offenders == []


def test_q2_band_disappears_once_the_quarter_finalizes(monkeypatch):
    """Codex review P1: the Q2 band was unconditional, so every quarter
    figure would keep shading and labelling Q2 'provisional' after the
    finalization re-pull. Derive it from the data stamp instead."""
    from pipeline import detect
    fig, ax = figstyle.plt.subplots()
    monkeypatch.setattr(detect, "AS_OF", "2026-08-25T00:00:00Z")
    assert shade_q2_partial(ax) is not None      # windows still open
    monkeypatch.setattr(detect, "AS_OF", "2026-08-26T00:00:00Z")
    assert shade_q2_partial(ax) is None          # finalized: no band
    figstyle.plt.close(fig)


def test_shade_q2_partial_params(monkeypatch):
    """The magic band verbatim: axvspan(1.6, 2.4, color="0.85", alpha=0.5,
    zorder=0) — previously copied into 11 call sites."""
    from pipeline import detect
    monkeypatch.setattr(detect, "AS_OF", "2026-08-01T00:00:00Z")
    fig, ax = figstyle.plt.subplots()
    span = shade_q2_partial(ax)
    assert (span.get_x(), span.get_x() + span.get_width()) == (1.6, 2.4)
    assert span.get_alpha() == 0.5 and span.get_zorder() == 0
    assert span.get_label() == "Q2 partial (w8 windows open)"
    generic = shade_span(ax, -0.5, 0.5, "w8 window open")
    assert (generic.get_x(),
            generic.get_x() + generic.get_width()) == (-0.5, 0.5)
    assert generic.get_alpha() == 0.5 and generic.get_zorder() == 0
    figstyle.plt.close(fig)


def test_shade_provisional_bands_the_open_month_suffix(monkeypatch):
    """The monthly analogue of shade_q2_partial: one span over the
    trailing window months whose w8 windows are still open, gone once
    every month matures (same auto-finalization rule)."""
    from pipeline import detect
    fig, ax = figstyle.plt.subplots()
    # 2026-05 matures at 2026-07-26; 2026-06 at 2026-08-26
    monkeypatch.setattr(detect, "AS_OF", "2026-08-01T00:00:00Z")
    span = figstyle.shade_provisional(ax, WINDOW)
    assert (span.get_x(), span.get_x() + span.get_width()) == (7.5, 8.5)
    assert span.get_label() == "w8 windows open (merged provisional)"
    monkeypatch.setattr(detect, "AS_OF", "2026-08-26T00:00:00Z")
    assert figstyle.shade_provisional(ax, WINDOW) is None
    figstyle.plt.close(fig)


def test_broken_axes_month_geometry():
    """Month-domain twin of broken_axes (monthly paper figures 2/3):
    every baseline and window month labeled, width scaling with the
    window."""
    window = WINDOW + ["2026-07"]
    fig, axl, axr = figstyle.broken_axes_month("share (%)", window)
    assert axl.get_xlim() == (-0.5, len(BASELINE) - 0.5)
    assert _labels(axl) == [m[2:7] for m in BASELINE]
    assert axr.get_xlim() == (-0.5, len(window) - 0.5)
    assert _labels(axr) == [m[2:7] for m in window]
    assert axl.get_ylabel() == "share (%)"
    assert not axl.spines.right.get_visible()
    assert not axr.spines.left.get_visible()
    assert fig.get_size_inches()[0] == max(8.0, 0.75 * len(window) + 3)
    assert fig._suptitle is None
    figstyle.plt.close(fig)


def test_quarter_series_split():
    """The y[:1] / y[1:] split-plot idiom: baseline point on the left
    panel (ms 4, unlabeled), window series on the right (ms 3, labeled)."""
    fig = figstyle.plt.figure()
    sf = fig.subfigures(1, 1)
    axl, axr = broken_pair(sf, "t")
    n_l, n_r = len(axl.lines), len(axr.lines)
    quarter_series(axl, axr, [10, 20, None, 40], "#1f77b4", "human-reviewed")
    (left,), (right,) = axl.lines[n_l:], axr.lines[n_r:]
    assert list(left.get_xdata()) == [0] and list(left.get_ydata()) == [10]
    assert list(right.get_xdata()) == [0, 1, 2]
    assert right.get_label() == "human-reviewed"
    assert left.get_markersize() == 4 and right.get_markersize() == 3
    figstyle.plt.close(fig)


def test_month_series_split():
    """The monthly split-plot idiom shared by plot_fig5_fleet and
    plot_adoption_cohorts: ms 2.5, baseline unlabeled, window labeled."""
    fig = figstyle.plt.figure()
    sf = fig.subfigures(1, 1)
    axl, axr = broken_pair(sf, "t", span="month")
    n_l, n_r = len(axl.lines), len(axr.lines)
    month_series(axl, axr, [1, 2, 3], [None] * len(WINDOW), "tab:blue",
                 ls="--", label="submitted non-AI")
    (left,), (right,) = axl.lines[n_l:], axr.lines[n_r:]
    assert list(left.get_xdata()) == [0, 1, 2]
    assert list(right.get_xdata()) == list(range(len(WINDOW)))
    assert right.get_label() == "submitted non-AI"
    assert left.get_markersize() == 2.5 == right.get_markersize()
    assert right.get_linestyle() == "--"
    figstyle.plt.close(fig)


def test_month_series_follows_value_length():
    """month_series plots however many window values it is given, so a
    shortened (w8-final-only) window needs no special casing."""
    fig = figstyle.plt.figure()
    sf = fig.subfigures(1, 1)
    window = WINDOW[:8]
    axl, axr = broken_pair(sf, "t", span="month", window=window)
    n_r = len(axr.lines)
    month_series(axl, axr, [1, 2, 3], [None] * len(window), "tab:blue")
    (right,) = axr.lines[n_r:]
    assert list(right.get_xdata()) == list(range(len(window)))
    figstyle.plt.close(fig)


def test_cell_suppresses_ai_slice_at_baseline():
    """Architecture review 2026-07-22 candidate 2: the zero-denominator
    suppression rule DIVERGED between copies — plot_fig3_comp_audits.py
    suppresses the ai slice at Q1-2024 'even if a stray detector FP
    creates a tiny cell', while the fig6 twins and fig7 only checked cell
    presence and would have plotted the stray. The unified rule: an
    AI-conditioned rate is undefined at the baseline, absent cells are
    undefined, and both read as None (never a plotted zero)."""
    rows = {("Q1-2024", "ai"): {"humanRev_pr": 0.5},    # stray detector FP
            ("Q2-2026", "ai"): {"humanRev_pr": 0.6},
            ("Q1-2024", "ins"): {"humanRev_pr": 0.7}}
    assert cell(rows, "Q1-2024", "ai", "humanRev_pr") is None
    assert cell(rows, "Q2-2026", "ai", "humanRev_pr") == 0.6
    assert cell(rows, "Q1-2024", "ins", "humanRev_pr") == 0.7   # role slices exempt
    assert cell(rows, "Q4-2025", "ai", "humanRev_pr") is None   # absent cell
    assert cell(rows, "Q2-2026", "ai", "humanRev_pr", scale=100) == 60.0
    assert cell(rows, "Q1-2024", "ai", "humanRev_pr", scale=100) is None


def test_cell_suppresses_ai_slice_at_monthly_baseline():
    """Monthly variant of the baseline rule: an AI-conditioned rate is
    undefined in every Q1-2024 baseline MONTH too — a stray detector FP
    cell there must read None while other slices pass through."""
    rows = {("2024-02", "ai"): {"humanRev_pr": 0.5},     # stray detector FP
            ("2024-02", "nonai"): {"humanRev_pr": 0.7},
            ("2026-04", "ai"): {"humanRev_pr": 0.6}}
    assert cell(rows, "2024-02", "ai", "humanRev_pr") is None
    assert cell(rows, "2024-02", "nonai", "humanRev_pr") == 0.7
    assert cell(rows, "2026-04", "ai", "humanRev_pr") == 0.6


def test_paired_series6_matches_legacy_tuples():
    """SERIES6 was copied between the fig6 twins with only keys/labels
    edited; the builder must reproduce both legacy lists exactly."""
    assert paired_series6(("ins", "core"), ("ext", "external")) == [
        ("humanRev", "ins", "#1f77b4", "human-reviewed (core)"),
        ("humanRev", "ext", "#8ec1e8", "human-reviewed (external)"),
        ("botOnly", "ins", "#d95f02", "bot-only reviewed (core)"),
        ("botOnly", "ext", "#fdbf6f", "bot-only reviewed (external)"),
        ("selfUnrev", "ins", "#c11b1b", "self-merged unreviewed (core)"),
        ("selfUnrev", "ext", "#f79c9c", "self-merged unreviewed (external)"),
    ]
    assert paired_series6(("ai", "AI-involved"), ("nonai", "non-AI")) == [
        ("humanRev", "ai", "#1f77b4", "human-reviewed (AI-involved)"),
        ("humanRev", "nonai", "#8ec1e8", "human-reviewed (non-AI)"),
        ("botOnly", "ai", "#d95f02", "bot-only reviewed (AI-involved)"),
        ("botOnly", "nonai", "#fdbf6f", "bot-only reviewed (non-AI)"),
        ("selfUnrev", "ai", "#c11b1b", "self-merged unreviewed (AI-involved)"),
        ("selfUnrev", "nonai", "#f79c9c", "self-merged unreviewed (non-AI)"),
    ]


def test_loc_series_and_month_lists_are_the_legacy_values():
    """The six submitted/merged x total/non-AI/AI tuples and the
    BASELINE/WINDOW month lists, previously duplicated across
    plot_fig2_comp_audits / plot_fig5_fleet / plot_adoption_{cohorts,event}."""
    assert LOC_SERIES == [
        ("submitted", "tab:blue", "-", "submitted total"),
        ("sub_nonai", "tab:blue", "--", "submitted non-AI"),
        ("sub_ai", "tab:blue", ":", "submitted AI-involved"),
        ("merged", "tab:green", "-", "merged total (w8)"),
        ("mrg_nonai", "tab:green", "--", "merged non-AI"),
        ("mrg_ai", "tab:green", ":", "merged AI-involved"),
    ]
    assert BASELINE == ["2024-01", "2024-02", "2024-03"]
    assert WINDOW == ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02",
                      "2026-03", "2026-04", "2026-05", "2026-06"]


def test_save_writes_png_and_prints(tmp_path, capsys):
    fig, ax = figstyle.plt.subplots()
    ax.plot([0, 1], [0, 1])
    out = tmp_path / "fig_test.png"
    save(fig, str(out))
    assert out.exists() and out.stat().st_size > 0
    assert capsys.readouterr().out == f"wrote {out}\n"
    figstyle.plt.close(fig)
