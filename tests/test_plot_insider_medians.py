"""scripts/plot_insider_medians.py — per-population figures and layout."""
import math
import sys

sys.path.insert(0, "scripts")
import plot_insider_medians as pim  # noqa: E402

from pipeline.figdata import Table  # noqa: E402
from pipeline.figstyle import plt  # noqa: E402
from pipeline.frame import PERIODS  # noqa: E402
from pipeline.studies.productivity import (INSIDER_METRICS,  # noqa: E402
                                           INSIDER_POPULATIONS,
                                           INSIDER_SLICES)


def _rows(value_key):
    rows = {}
    for pop, _pl in INSIDER_POPULATIONS:
        for sl, _sl in INSIDER_SLICES:
            for metric, _ml in INSIDER_METRICS:
                for i, q in enumerate(PERIODS):
                    rows[(pop, sl, metric, q)] = {
                        "n": 100 + i, value_key: 2.0 + i,
                        "lo": 1.5 + i, "hi": 2.5 + i}
    return rows


def _table(pop, growth=False) -> Table:
    return pim._table(pop, _rows("mult" if growth else "median"),
                      pim.stem(pop, growth), "mult" if growth else "median")


def test_six_figures_with_distinct_stems_one_per_population():
    figs = pim.figures()
    stems = [out for out, _c, _r in figs]
    assert len(stems) == 2 * len(INSIDER_POPULATIONS) == len(set(stems))
    assert "artifacts/insider_medians_productive.png" in stems
    assert "artifacts/insider_medians_growth_productive.png" in stems
    assert "artifacts/insider_medians_active.png" in stems       # pop 'any'


def test_table_carries_full_population_label_and_n_series():
    t = _table("productive")
    assert t.panels() == [m for m, _l in INSIDER_METRICS]
    assert "productive panel" in t.label_of("submitted")
    assert set(t.series_in("merged")) == {sl for sl, _l in INSIDER_SLICES} | {
        f"n_{sl}" for sl, _l in INSIDER_SLICES}


def test_panel_titles_name_metric_then_population_on_two_lines():
    """Each figure is one population: the two panel titles carry the
    metric on line one and the short population line on line two, short
    enough that adjacent panels never collide."""
    fig = pim.render(_table("productive"), "productive")
    titles = [ax.get_title(loc="left") for ax in fig.get_axes()
              if ax.get_title(loc="left")]
    assert len(titles) == len(INSIDER_METRICS)
    for title in titles:
        lines = title.split("\n")
        assert len(lines) == 2 and all(len(ln) <= 60 for ln in lines), title
    assert titles[0].endswith(pim.POP_TITLES["productive"])
    assert not any(ax.texts for ax in fig.get_axes())        # no annotations
    plt.close(fig)


def test_growth_annotates_only_the_all_series():
    """The growth twin labels each all-insiders multiple (like Figure 2's
    x-baseline annotations) and leaves the AI/non-AI curves unlabelled:
    one annotation per quarter per panel, no more."""
    fig = pim.render_growth(_table("panel", growth=True), "panel")
    texts = [txt.get_text() for ax in fig.get_axes() for txt in ax.texts]
    assert len(texts) == len(INSIDER_METRICS) * len(PERIODS)
    assert all(t.endswith("x") for t in texts)
    ylabels = {ax.get_ylabel() for ax in fig.get_axes() if ax.get_ylabel()}
    assert ylabels == {"× own Q1-2024 median"}
    plt.close(fig)


def test_rows_are_computed_once_per_process(monkeypatch):
    """Six collects in one plot_all run share a single study pass."""
    calls = []
    monkeypatch.setattr(pim, "_ROWS", {})
    monkeypatch.setattr(pim, "_insider_cells",
                        lambda: calls.append("cells") or {})
    monkeypatch.setattr(pim, "insider_medians",
                        lambda cells=None: _rows("median"))
    monkeypatch.setattr(pim, "insider_growth",
                        lambda cells=None: _rows("mult"))
    for pop, _l in INSIDER_POPULATIONS:
        pim.collect(pop)
        pim.collect_growth(pop)
    assert calls == ["cells"]
    assert not math.isnan(pim._ROWS["medians"][("any", "all", "submitted",
                                                 "Q1-2024")]["median"])
