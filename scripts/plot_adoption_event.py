"""Figure A2: the Figure A1 metrics in event time, net of non-adopters.

BALANCED PANEL: only authors observed at every offset t-2..t+2 (constant
composition; late adopters drop out by construction since their t+2 lies
beyond the window; fleet operators are excluded from this per-contributor
figure — their 10-100x scale belongs to Figure 4's own panel). One panel
per cohort (early / middle): mean
kLOC per contributor per month around each author's first observed AI
month, with the contemporaneous NON-ADOPTER mean subtracted from every
observation (difference-in-differences: calendar drift cancels; the y=0
line IS the non-adopter counterfactual). Same encoding as Figure 4:
blue = submitted, green = merged (w8), solid/dashed/dotted =
total/non-AI/AI-involved.

Data:   artifacts/data/fig_a2_adoption_event.csv
Output: artifacts/fig_a2_adoption_event.png
Usage:  PYTHONPATH=src python scripts/plot_adoption_event.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import LOC_SERIES, plt, shade_span
from pipeline.studies.productivity import adoption_event

PANELS = [("early", "early adopters"), ("medium", "middle adopters")]
OFFSETS = list(range(-2, 3))
# offsets whose observations partly land in w8-open calendar months:
# merged is deflated there, so the renderer shades them and prints the
# affected share
IMMATURE = "immature_share"


def collect() -> Table:
    rows = adoption_event()
    t = Table("fig_a2_adoption_event")
    for coh, title in PANELS:
        n = rows.get((coh, 0), {}).get("n", 0)   # constant (balanced)
        label = f"{title} (n={n})"
        for key, _color, _ls, series_label in LOC_SERIES:
            for e in OFFSETS:
                t.add(coh, key, e, rows.get((coh, e), {}).get(key),
                      panel_label=label, series_label=series_label,
                      x_label=f"t{e:+d}" if e else "t0")
        for e in OFFSETS:
            t.add(coh, IMMATURE, e,
                  rows.get((coh, e), {}).get(IMMATURE, 0),
                  panel_label=label,
                  series_label="share of offset in w8-open months",
                  x_label=f"t{e:+d}" if e else "t0")
    return t


def render(t: Table):
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    for ax, coh in zip(axes.flat, t.panels()):
        for key, color, ls, label in LOC_SERIES:
            pts = t.points(coh, key)
            ax.plot([p["x"] for p in pts], [p["value"] for p in pts],
                    marker="o", ms=3, ls=ls, color=color, label=label)
        shaded = False
        for p in t.points(coh, IMMATURE):
            if p["value"]:
                shade_span(ax, p["x"] - 0.5, p["x"] + 0.5,
                           label=None if shaded else
                           "offset contains w8-open months\n"
                           "(merged provisional)")
                ax.annotate(f"{p['value']:.0%}", (p["x"], 0),
                            xycoords=("data", "axes fraction"),
                            xytext=(0, 2), textcoords="offset points",
                            ha="center", fontsize=7, color="0.4")
                shaded = True
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(t.label_of(coh), fontsize=10, loc="left")
        pts = t.points(coh, LOC_SERIES[0][0])
        ax.set_xticks([p["x"] for p in pts], [p["x_label"] for p in pts])
        ax.set_xlabel("months from first observed AI use")
        ax.set_ylabel("kLOC/month, net of non-adopters")
    handles, labels = axes.flat[1].get_legend_handles_labels()
    ax3 = axes.flat[2]
    ax3.axis("off")
    ax3.legend(handles, labels, loc="center", fontsize=9, frameon=False)
    fig.tight_layout()
    return fig


if __name__ == "__main__":
    figure_main(collect, render, "artifacts/fig_a2_adoption_event.png")
