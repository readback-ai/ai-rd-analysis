"""Figure data tables (pipeline.figdata) — the CSV that stands between the
study pass and the rendered image.

The contract the figures depend on: a table round-trips exactly (a
re-render must reproduce the plotted numbers bit for bit), missing points
stay missing rather than becoming zeros, and --from-table renders without
running a study function.
"""
import matplotlib.pyplot as plt
import pytest

from pipeline import figdata
from pipeline.figdata import COLUMNS, Table, figure_main, read, write
from pipeline.figstyle import save


def _table():
    t = Table("demo")
    t.add_series("left", "ai", [None, 1 / 3, 2.5], x_labels=["a", "b", "c"],
                 panel_label="left panel", series_label="AI-involved PRs")
    t.add_series("right", "nonai", [77.23684210526316, None, 0.0],
                 x_labels=["a", "b", "c"], panel_label="right panel",
                 series_label="non-AI PRs")
    return t


def test_round_trip_is_exact(tmp_path):
    """Values must survive the CSV round-trip bit for bit — a re-render
    from the table is only trustworthy if it plots identical floats."""
    t = _table()
    path = tmp_path / "demo.csv"
    write(t, path)
    back = read("demo", path)
    assert back.values("left", "ai") == [None, 1 / 3, 2.5]
    assert back.values("right", "nonai") == [77.23684210526316, None, 0.0]


def test_missing_points_stay_none(tmp_path):
    """A suppressed cell (zero denominator, AI slice at the 2024 baseline)
    must read back as None, never as a plotted 0.0."""
    path = tmp_path / "demo.csv"
    write(_table(), path)
    assert read("demo", path).values("left", "ai")[0] is None


def test_labels_and_order_survive(tmp_path):
    path = tmp_path / "demo.csv"
    write(_table(), path)
    back = read("demo", path)
    assert back.panels() == ["left", "right"]
    assert back.series_in("left") == ["ai"]
    assert back.label_of("right") == "right panel"
    assert [p["x_label"] for p in back.points("left", "ai")] == ["a", "b", "c"]
    assert back.points("left", "ai")[0]["series_label"] == "AI-involved PRs"


def test_header_is_the_documented_schema(tmp_path):
    path = tmp_path / "demo.csv"
    write(_table(), path)
    assert path.read_text().splitlines()[0] == ",".join(COLUMNS)
    assert COLUMNS[:4] == ["panel", "panel_label", "series", "series_label"]


def test_error_band_columns(tmp_path):
    """Figures with bootstrap CIs (paper figures 2/3) carry lo/hi with the
    point, so the band re-renders from the table alone."""
    t = Table("band")
    t.add("p", "s", 0, 10.0, lo=9.5, hi=10.5)
    path = tmp_path / "band.csv"
    write(t, path)
    lo, hi = read("band", path).band("p", "s")
    assert (lo, hi) == ([9.5], [10.5])


def test_save_writes_every_format_from_one_figure(tmp_path):
    """One render, many formats: the PNG and the SVG of a figure cannot
    disagree because they come from the same figure object."""
    fig = plt.figure()
    fig.add_subplot().plot([0, 1], [1, 2])
    out = tmp_path / "fig.png"
    save(fig, out, formats=("png", "svg"))
    assert out.exists() and out.with_suffix(".svg").exists()


def test_from_table_skips_collection(tmp_path, monkeypatch, capsys):
    """--from-table must render off the committed CSV: the expensive
    study pass is never entered."""
    monkeypatch.setattr(figdata, "DATA_DIR", tmp_path)
    write(_table(), tmp_path / "fig.csv")

    def collect():
        raise AssertionError("study pass ran under --from-table")

    def render(t):
        fig = plt.figure()
        fig.add_subplot().plot([p["x"] for p in t.points("right", "nonai")],
                              [0, 0, 0])
        return fig

    figure_main(collect, render, str(tmp_path / "fig.png"),
                argv=["--from-table"])
    assert (tmp_path / "fig.png").exists()


def test_collection_writes_the_table(tmp_path, monkeypatch):
    """The default path writes the table next to rendering it, so every
    published image has its numbers on disk."""
    monkeypatch.setattr(figdata, "DATA_DIR", tmp_path)

    def render(t):
        return plt.figure()

    figure_main(_table, render, str(tmp_path / "demo.png"), argv=[])
    assert (tmp_path / "demo.csv").exists()
    assert read("demo", tmp_path / "demo.csv").values("left", "ai")[2] == 2.5


def test_add_series_rejects_short_label_list():
    """Mismatched x labels are a collect-time bug; fail loudly instead of
    mislabelling an axis."""
    t = Table("demo")
    with pytest.raises(IndexError):
        t.add_series("p", "s", [1.0, 2.0], x_labels=["only-one"])
