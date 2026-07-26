"""House style for the paper figures — the single home for conventions
that were previously copied across the 11 scripts/plot_*.py files
(architecture review 2026-07-22, candidate 2).

Vocabulary (CONTEXT.md): the study window is the broken x-axis — the
Q1-2024 detector-validity baseline sits ~7 quarters before the continuous
Q4-2025..Q2-2026 window, so every time-series figure is a left/right
panel pair joined by axis-break marks. Q2-2026 outcome metrics are
w8-provisional at the current AS_OF, marked by the standard shaded band.

Importing this module selects the Agg backend; scripts use its `plt`.
"""
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

# monthly-figure x domains (fig5, A1): the Q1-2024 baseline months and the
# continuous Oct-2025..Jun-2026 window
BASELINE = ["2024-01", "2024-02", "2024-03"]
WINDOW = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
          "2026-04", "2026-05", "2026-06"]

# dark/light hue pairs for two-slice contrasts (dark = the highlighted
# slice: core / AI-involved / fleet)
PAIR_BLUE = ("#1f77b4", "#8ec1e8")
PAIR_ORANGE = ("#d95f02", "#fdbf6f")
PAIR_RED = ("#c11b1b", "#f79c9c")

# the six per-contributor LOC series shared by figures 2-comp/5/A1/A2:
# color = outcome (blue submitted, green merged), linestyle = AI split
# (solid total, dashed non-AI, dotted AI-involved)
LOC_SERIES = [
    ("submitted", "tab:blue", "-", "submitted total"),
    ("sub_nonai", "tab:blue", "--", "submitted non-AI"),
    ("sub_ai", "tab:blue", ":", "submitted AI-involved"),
    ("merged", "tab:green", "-", "merged total (w8)"),
    ("mrg_nonai", "tab:green", "--", "merged non-AI"),
    ("mrg_ai", "tab:green", ":", "merged AI-involved"),
]

_CHANNELS6 = [("humanRev", "human-reviewed", PAIR_BLUE),
              ("botOnly", "bot-only reviewed", PAIR_ORANGE),
              ("selfUnrev", "self-merged unreviewed", PAIR_RED)]


def paired_series6(dark, light):
    """The fig6 six-series list: {humanRev, botOnly, selfUnrev} x
    {dark, light} as (channel, slice_key, color, label) tuples. `dark` /
    `light` are (slice_key, slice_label) pairs — six SOLID lines in
    paired hues because a dashed-vs-solid split is invisible on the
    isolated Q1-2024 points."""
    return [(ch, key, color, f"{chlab} ({lab})")
            for ch, chlab, pair in _CHANNELS6
            for key, lab, color in ((dark[0], dark[1], pair[0]),
                                    (light[0], light[1], pair[1]))]


def break_kw(markersize=9):
    """Axis-break tick marks (the diagonal cut glyphs)."""
    return dict(marker=[(-1, -0.5), (1, 0.5)], markersize=markersize,
                linestyle="none", color="k", mec="k", mew=1, clip_on=False)


def _break_marks(axl, axr, markersize=9):
    kw = break_kw(markersize)
    for ax, x in ((axl, 1), (axr, 0)):
        ax.plot([x], [0], transform=ax.transAxes, **kw)
        ax.plot([x], [1], transform=ax.transAxes, **kw)


def broken_pair(subfig, title, span="quarter"):
    """Left/right broken-axis panel pair inside a subfigure, shared y.

    span="quarter": Q1-24 at x=0 on the left; Q4-25..Q2-26 at x=0..2 on
    the right (fig6/7/8 and the fig3 companion).
    span="month": BASELINE months on the left, WINDOW months on the right
    with ticks at months [0, 3, 6, 8] (fig5, A1)."""
    axl, axr = subfig.subplots(
        1, 2, sharey=True,
        gridspec_kw={"width_ratios": [1, 3], "wspace": 0.08})
    if span == "quarter":
        axl.set_xlim(-0.5, 0.5)
        axl.set_xticks([0], ["Q1-24"])
        axr.set_xlim(-0.4, 2.4)
        axr.set_xticks([0, 1, 2], ["Q4-25", "Q1-26", "Q2-26"])
    elif span == "month":
        axl.set_xlim(-0.5, len(BASELINE) - 0.5)
        axl.set_xticks([1], ["Q1-24"])
        axr.set_xlim(-0.5, len(WINDOW) - 0.5)
        ticks = [0, 3, 6, 8]
        axr.set_xticks(ticks, [WINDOW[i][2:7] for i in ticks], fontsize=8)
    else:
        raise ValueError(f"unknown span {span!r}")
    axl.spines.right.set_visible(False)
    axr.spines.left.set_visible(False)
    axr.tick_params(left=False)
    _break_marks(axl, axr)
    axl.set_title(title, fontsize=10, loc="left")
    return axl, axr


def broken_axes(ylabel: str, title: str):
    """Whole-figure broken-axis variant (paper figures 2/3): full-length
    quarter labels, caption below the figure."""
    fig, (axl, axr) = plt.subplots(
        1, 2, sharey=True, figsize=(8, 4.5),
        gridspec_kw={"width_ratios": [1, 4], "wspace": 0.06})
    axl.set_xlim(-0.5, 0.5)
    axl.set_xticks([0], ["Q1-2024"])
    axr.set_xlim(-0.4, 2.4)
    axr.set_xticks([0, 1, 2], ["Q4-2025", "Q1-2026", "Q2-2026"])
    axl.spines.right.set_visible(False)
    axr.spines.left.set_visible(False)
    axr.tick_params(left=False)
    _break_marks(axl, axr, markersize=12)
    axl.set_ylabel(ylabel)
    fig.suptitle(title, y=-0.06)   # caption below the figure
    return fig, axl, axr


def quarter_series(axl, axr, y, color, label=None, ms=(4, 3), **kw):
    """Plot a 4-period series across a quarter broken_pair: the Q1-2024
    point on the left panel (unlabeled), Q4-25..Q2-26 on the right."""
    axl.plot([0], y[:1], marker="o", ms=ms[0], color=color, **kw)
    axr.plot([0, 1, 2], y[1:], marker="o", ms=ms[1], color=color,
             label=label, **kw)


def month_series(axl, axr, vals_baseline, vals_window, color, ls="-",
                 label=None):
    """Plot a monthly series across a month broken_pair: BASELINE values
    on the left panel (unlabeled), WINDOW values on the right."""
    axl.plot(range(len(BASELINE)), vals_baseline, marker="o", ms=2.5,
             ls=ls, color=color)
    axr.plot(range(len(WINDOW)), vals_window, marker="o", ms=2.5,
             ls=ls, color=color, label=label)


def shade_span(ax, lo, hi, label=None):
    """The provisional-data band: w8 windows still open at the AS_OF, so
    merged outcomes there are floors until the re-pull."""
    return ax.axvspan(lo, hi, color="0.85", alpha=0.5, zorder=0,
                      label=label)


def shade_q2_partial(axr, label="Q2 partial (w8 windows open)"):
    """Q2-2026 band on a quarter broken_pair right panel — the former
    magic axvspan(1.6, 2.4) copied into 11 call sites."""
    return shade_span(axr, 1.6, 2.4, label)


def cell(rows, per, sl, key, scale=1):
    """Zero-denominator suppression, unified (candidate-2 divergence): an
    absent (period, slice) cell is undefined — never a plotted zero — and
    an AI-conditioned rate is undefined at the Q1-2024 baseline even if a
    stray detector false positive creates a tiny cell (the guard
    plot_fig3_comp_audits.py had and the fig6 twins lacked)."""
    if sl == "ai" and per == "Q1-2024":
        return None
    v = rows.get((per, sl), {}).get(key)
    return None if v is None else scale * v


def save(fig, path):
    """House export: 200 dpi, tight bbox, provenance line on stdout."""
    fig.savefig(path, dpi=200, bbox_inches="tight")
    print(f"wrote {path}")
