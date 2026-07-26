"""Figure 2: productivity metrics around the first month of AI adoption,
one panel per ADOPTION MONTH.

Five balanced cohorts (first AI use 2025-12 .. 2026-04 — the months
whose full [-2..+2] window fits the data), non-fleet adopters, six
series per panel: submitted/merged (blue/green) x total/non-AI/
AI-involved (solid/dashed/dotted), raw mean kLOC per author per month.
Within a cohort each offset is one calendar month, so w8-open offsets
are shaded exactly (merged provisional there; finalizes with the AS_OF
re-pulls).

Output: artifacts/figure_2_comp_audits.png
Usage:  PYTHONPATH=src python scripts/plot_fig2_comp_audits.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import LOC_SERIES, plt, save, shade_span
from pipeline.studies.productivity import event_by_adoption_month


def main() -> None:
    cohorts = event_by_adoption_month()
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
    fig.suptitle("Figure 2: LOC per contributor around first AI adoption, "
                 "by adoption month (balanced cohorts)", fontsize=12,
                 y=-0.03)
    for ax, (t0_mon, c) in zip(axes.flat, sorted(cohorts.items())):
        offs = sorted(c["offsets"])
        for key, color, ls, label in LOC_SERIES:
            ax.plot(offs, [c["offsets"][e][key] for e in offs],
                    marker="o", ms=3, ls=ls, color=color, label=label)
        shaded = False
        for e in offs:
            if not c["offsets"][e]["mature"]:
                shade_span(ax, e - 0.5, e + 0.5, label=None if shaded else
                           "w8 window open (merged provisional)")
                shaded = True
        ax.set_title(f"first AI use {t0_mon} (n={c['n']})",
                     fontsize=10, loc="left")
        ax.set_xticks(offs, [f"t{e:+d}" if e else "t0" for e in offs])
        ax.set_xlabel("months from first observed AI use")
        ax.set_ylabel("kLOC / contributor / month")
        ax.set_ylim(bottom=0)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    ax6 = axes.flat[5]
    ax6.axis("off")
    ax6.legend(handles, labels, loc="center", fontsize=10, frameon=False)
    fig.tight_layout()
    save(fig, "artifacts/figure_2_comp_audits.png")


if __name__ == "__main__":
    main()
