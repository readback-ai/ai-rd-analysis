"""Figure 2: productivity metrics around the first month of AI adoption,
one panel per ADOPTION MONTH.

Balanced cohorts, one per adoption month whose full [-2..+2] window has
passed w8 finalization at the AS_OF (at AS_OF 2026-08-01: first AI use
2025-12 .. 2026-03), non-fleet adopters, six series per panel:
submitted/merged (blue/green) x total/non-AI/AI-involved
(solid/dashed/dotted), raw mean kLOC per author per month, in a
two-column panel grid with the legend to the right of the top-right
panel. Every offset is a finalized calendar month, so the merged series
are final and no provisional shading is needed.

Data:   artifacts/data/figure_2_comp_audits.csv
Output: artifacts/figure_2_comp_audits.png
Usage:  PYTHONPATH=src python scripts/plot_fig2_comp_audits.py
        PYTHONPATH=src python scripts/plot_fig2_comp_audits.py \
            --from-table --format png,svg
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import LOC_SERIES, plt
from pipeline.studies.productivity import event_by_adoption_month


def collect() -> Table:
    t = Table("figure_2_comp_audits")
    for t0_mon, c in sorted(event_by_adoption_month().items()):
        label = f"first AI use {t0_mon} (n={c['n']})"
        offs = sorted(c["offsets"])
        for key, _color, _ls, series_label in LOC_SERIES:
            for e in offs:
                t.add(t0_mon, key, e, c["offsets"][e][key],
                      panel_label=label, series_label=series_label,
                      x_label=f"t{e:+d}" if e else "t0")
    return t


def render(t: Table):
    panels = t.panels()
    rows = (len(panels) + 1) // 2
    fig, axes = plt.subplots(rows, 2, figsize=(9, 3.75 * rows),
                             squeeze=False)
    for ax, panel in zip(axes.flat, panels):
        for key, color, ls, label in LOC_SERIES:
            pts = t.points(panel, key)
            ax.plot([p["x"] for p in pts], [p["value"] for p in pts],
                    marker="o", ms=3, ls=ls, color=color, label=label)
        pts = t.points(panel, LOC_SERIES[0][0])
        ax.set_title(t.label_of(panel), fontsize=10, loc="left")
        ax.set_xticks([p["x"] for p in pts], [p["x_label"] for p in pts])
        ax.set_xlabel("months from first observed AI use")
        ax.set_ylabel("kLOC / contributor / month")
        ax.set_ylim(bottom=0)
    for ax in list(axes.flat)[len(panels):]:
        ax.axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.tight_layout()
    # legend to the right of the top-right panel, outside the grid
    fig.legend(handles, labels, loc="upper left",
               bbox_to_anchor=(1.0, 0.97), fontsize=10, frameon=False)
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/figure_2_comp_audits.png")
