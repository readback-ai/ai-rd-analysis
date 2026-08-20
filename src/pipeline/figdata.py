"""Figure data tables — the render source of truth for every paper figure.

A figure is produced in two stages. `collect()` runs the study functions
(the expensive census pass) and returns a Table; `render(table)` builds
the matplotlib figure from that Table alone, touching no census data. The
Table is written to artifacts/data/<figure>.csv, so re-rendering — a
different image format, a tweaked axis, a chart rebuilt in a spreadsheet —
reads the committed table instead of recomputing the study.

The table is tidy/long: one row per plotted point, carrying the panel and
series it belongs to along with their display labels. That one shape
covers every figure in the paper (single-panel, small multiples, broken
axis, event time, error bars) and pivots cleanly in a spreadsheet.

Values serialize at full float precision, so a table round-trip is exact
and a re-render is byte-identical to the original.
"""
import argparse
import csv
from pathlib import Path

DATA_DIR = Path("artifacts/data")

COLUMNS = ["panel", "panel_label", "series", "series_label",
           "x", "x_label", "value", "lo", "hi"]


def _num(text: str):
    return None if text == "" else float(text)


def _text(value) -> str:
    """Full-precision float text: repr round-trips exactly in Python 3,
    so reading a table back reproduces the plotted numbers bit for bit."""
    return "" if value is None else repr(value)


class Table:
    """The plotted points of one figure, in plot order.

    Points are addressed by (panel, series); `x` is the numeric position
    the renderer plots at and `x_label` is what the axis shows. `lo`/`hi`
    carry an error-bar or confidence band where a figure has one.
    """

    def __init__(self, name: str, rows: list | None = None):
        self.name = name
        self.rows = list(rows or [])

    def add(self, panel: str, series: str, x: float, value,
            *, panel_label: str = "", series_label: str = "",
            x_label: str = "", lo=None, hi=None) -> None:
        self.rows.append({"panel": panel, "panel_label": panel_label,
                          "series": series, "series_label": series_label,
                          "x": float(x), "x_label": x_label,
                          "value": value, "lo": lo, "hi": hi})

    def add_series(self, panel: str, series: str, values,
                   *, x_labels=None, x0: float = 0, **kw) -> None:
        """Add a whole series at consecutive x positions from `x0` — the
        common case, since the figures plot against positional indices."""
        for i, value in enumerate(values):
            self.add(panel, series, x0 + i, value,
                     x_label="" if x_labels is None else x_labels[i], **kw)

    def panels(self) -> list[str]:
        """Panel keys in first-appearance order."""
        return list(dict.fromkeys(r["panel"] for r in self.rows))

    def series_in(self, panel: str) -> list[str]:
        """Series keys of one panel, in first-appearance order."""
        return list(dict.fromkeys(r["series"] for r in self.rows
                                  if r["panel"] == panel))

    def label_of(self, panel: str) -> str:
        for r in self.rows:
            if r["panel"] == panel and r["panel_label"]:
                return r["panel_label"]
        return ""

    def points(self, panel: str, series: str) -> list[dict]:
        return [r for r in self.rows
                if r["panel"] == panel and r["series"] == series]

    def values(self, panel: str, series: str) -> list:
        return [r["value"] for r in self.points(panel, series)]

    def band(self, panel: str, series: str) -> tuple[list, list]:
        pts = self.points(panel, series)
        return [p["lo"] for p in pts], [p["hi"] for p in pts]


def path_for(name: str) -> Path:
    return DATA_DIR / f"{name}.csv"


def write(table: Table, path: Path | None = None) -> Path:
    """Write the table as CSV, creating artifacts/data/ on demand."""
    path = path or path_for(table.name)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(COLUMNS)
        for r in table.rows:
            w.writerow([r["panel"], r["panel_label"], r["series"],
                        r["series_label"], _text(r["x"]), r["x_label"],
                        _text(r["value"]), _text(r["lo"]), _text(r["hi"])])
    print(f"wrote {path}")
    return path


def read(name: str, path: Path | None = None) -> Table:
    path = path or path_for(name)
    table = Table(name)
    with path.open(newline="") as fh:
        for r in csv.DictReader(fh):
            table.rows.append({"panel": r["panel"],
                               "panel_label": r["panel_label"],
                               "series": r["series"],
                               "series_label": r["series_label"],
                               "x": float(r["x"]), "x_label": r["x_label"],
                               "value": _num(r["value"]),
                               "lo": _num(r["lo"]), "hi": _num(r["hi"])})
    return table


def figure_main(collect, render, out: str, argv=None) -> None:
    """CLI shared by the plot scripts: collect the table, write it, then
    render every requested image format from the one figure object.

    --from-table renders from the committed CSV without running any study
    function, so a format or styling change never re-reads the census.
    """
    name = Path(out).stem
    ap = argparse.ArgumentParser(description=f"render {name}")
    ap.add_argument("--from-table", action="store_true",
                    help="render from artifacts/data/<figure>.csv, "
                         "skipping the study pass")
    ap.add_argument("--format", default="png",
                    help="comma-separated image formats (png,svg)")
    a = ap.parse_args(argv)

    from pipeline.figstyle import save
    table = read(name) if a.from_table else collect()
    if not a.from_table:
        write(table)
    save(render(table), out, formats=a.format.split(","))
