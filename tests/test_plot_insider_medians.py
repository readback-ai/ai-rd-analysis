"""scripts/plot_insider_medians.py render layout."""
import sys

sys.path.insert(0, "scripts")
import plot_insider_medians as pim  # noqa: E402

from pipeline.figdata import Table  # noqa: E402
from pipeline.figstyle import plt  # noqa: E402
from pipeline.frame import PERIODS  # noqa: E402
from pipeline.studies.productivity import (INSIDER_METRICS,  # noqa: E402
                                           INSIDER_POPULATIONS,
                                           INSIDER_SLICES)


def _table() -> Table:
    t = Table(pim.NAME)
    for metric, mlabel in INSIDER_METRICS:
        for pop, plabel in INSIDER_POPULATIONS:
            panel = f"{metric}|{pop}"
            for sl, slabel in INSIDER_SLICES:
                for i, q in enumerate(PERIODS):
                    t.add(panel, sl, i, 2.0 + i, lo=1.5 + i, hi=2.5 + i,
                          panel_label=f"{mlabel} — {plabel}",
                          series_label=slabel, x_label=q)
                    t.add(panel, f"n_{sl}", i, 100,
                          panel_label=f"{mlabel} — {plabel}",
                          series_label=f"n, {slabel}", x_label=q)
    return t


def test_growth_annotates_only_the_all_series():
    """The growth variant labels each all-insiders multiple (like Figure
    2's x-baseline annotations) and leaves the AI/non-AI curves
    unlabelled: one annotation per quarter per panel, no more."""
    fig = pim.render_growth(_table())
    texts = [txt.get_text() for ax in fig.get_axes() for txt in ax.texts]
    panels = len(INSIDER_METRICS) * len(INSIDER_POPULATIONS)
    assert len(texts) == panels * len(PERIODS)
    assert all(t.endswith("x") for t in texts)
    ylabels = {ax.get_ylabel() for ax in fig.get_axes() if ax.get_ylabel()}
    assert all(y.startswith("× own Q1-2024 median") for y in ylabels)
    plt.close(fig)


def test_column_titles_are_short_and_only_on_the_top_row():
    """Panel titles overlap across columns: the full metric-and-population
    description was set as a single-line title on every panel, so
    adjacent columns' titles ran into each other in both rows. Columns
    carry a short wrapped population title on the top row only; the
    metric lives in the row's y-label."""
    fig = pim.render(_table())
    titles = [ax.get_title(loc="left") for ax in fig.get_axes()
              if ax.get_title(loc="left")]
    assert len(titles) == len(INSIDER_POPULATIONS)          # top row only
    for title in titles:
        lines = title.split("\n")
        assert len(lines) <= 2 and all(len(ln) <= 34 for ln in lines), title
    ylabels = {ax.get_ylabel() for ax in fig.get_axes() if ax.get_ylabel()}
    assert ylabels == {m for _k, m in INSIDER_METRICS}
    plt.close(fig)
