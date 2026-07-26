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

Output: artifacts/fig_a2_adoption_event.png
Usage:  PYTHONPATH=src python scripts/plot_adoption_event.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import LOC_SERIES, plt, save, shade_span
from pipeline.studies.productivity import adoption_event

PANELS = [("early", "early adopters"), ("medium", "middle adopters")]


def main() -> None:
    rows = adoption_event()
    offs = list(range(-2, 3))
    fig, axes = plt.subplots(1, 3, figsize=(12, 4.2))
    fig.suptitle("Figure A2: LOC per contributor around first AI adoption "
                 "(balanced panel, event time), net of the non-adopter "
                 "mean", fontsize=12, y=-0.05)
    for ax, (coh, title) in zip(axes.flat, PANELS):
        for key, color, ls, label in LOC_SERIES:
            y = [rows.get((coh, e), {}).get(key) for e in offs]
            ax.plot(offs, y, marker="o", ms=3, ls=ls, color=color,
                    label=label)
        n = rows.get((coh, 0), {}).get("n", 0)   # constant (balanced)
        # offsets whose observations partly land in w8-open calendar
        # months: merged deflated there — shade, with the affected share
        shaded = False
        for e in offs:
            sh = rows.get((coh, e), {}).get("immature_share", 0)
            if sh > 0:
                shade_span(ax, e - 0.5, e + 0.5, label=None if shaded else
                           "offset contains w8-open months\n"
                           "(merged provisional)")
                ax.annotate(f"{sh:.0%}", (e, 0), xycoords=("data",
                            "axes fraction"), xytext=(0, 2),
                            textcoords="offset points", ha="center",
                            fontsize=7, color="0.4")
                shaded = True
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(f"{title} (n={n})", fontsize=10, loc="left")
        ax.set_xticks(offs, [f"t{e:+d}" if e else "t0" for e in offs])
        ax.set_xlabel("months from first observed AI use")
        ax.set_ylabel("kLOC/month, net of non-adopters")
    handles, labels = axes.flat[1].get_legend_handles_labels()
    ax3 = axes.flat[2]
    ax3.axis("off")
    ax3.legend(handles, labels, loc="center", fontsize=9, frameon=False)
    fig.tight_layout()
    save(fig, "artifacts/fig_a2_adoption_event.png")


if __name__ == "__main__":
    main()
