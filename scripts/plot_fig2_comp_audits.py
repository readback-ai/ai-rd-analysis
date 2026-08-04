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

Output: artifacts/figure_2_comp_audits.png
Usage:  PYTHONPATH=src python scripts/plot_fig2_comp_audits.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import LOC_SERIES, plt, save
from pipeline.studies.productivity import event_by_adoption_month


def main() -> None:
    cohorts = sorted(event_by_adoption_month().items())
    rows = (len(cohorts) + 1) // 2
    fig, axes = plt.subplots(rows, 2, figsize=(9, 3.75 * rows),
                             squeeze=False)
    fig.suptitle("Figure 2: LOC per contributor around first AI adoption, "
                 "by adoption month (balanced cohorts, finalized months "
                 "only)", fontsize=12, y=-0.03)
    for ax, (t0_mon, c) in zip(axes.flat, cohorts):
        offs = sorted(c["offsets"])
        for key, color, ls, label in LOC_SERIES:
            ax.plot(offs, [c["offsets"][e][key] for e in offs],
                    marker="o", ms=3, ls=ls, color=color, label=label)
        ax.set_title(f"first AI use {t0_mon} (n={c['n']})",
                     fontsize=10, loc="left")
        ax.set_xticks(offs, [f"t{e:+d}" if e else "t0" for e in offs])
        ax.set_xlabel("months from first observed AI use")
        ax.set_ylabel("kLOC / contributor / month")
        ax.set_ylim(bottom=0)
    for ax in list(axes.flat)[len(cohorts):]:
        ax.axis("off")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.tight_layout()
    # legend to the right of the top-right panel, outside the grid
    fig.legend(handles, labels, loc="upper left",
               bbox_to_anchor=(1.0, 0.97), fontsize=10, frameon=False)
    save(fig, "artifacts/figure_2_comp_audits.png")


if __name__ == "__main__":
    main()
