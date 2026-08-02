"""Figure 2: productivity metrics around the first month of AI adoption,
one panel per ADOPTION MONTH.

Balanced cohorts, one per adoption month whose full [-2..+2] window has
passed w8 finalization at the AS_OF (at AS_OF 2026-08-01: first AI use
2025-12 .. 2026-03), non-fleet adopters, six series per panel:
submitted/merged (blue/green) x total/non-AI/AI-involved
(solid/dashed/dotted), raw mean kLOC per author per month. Every offset
is a finalized calendar month, so the merged series are final and no
provisional shading is needed; each x tick names its offset AND its
calendar month.

Output: artifacts/figure_2_comp_audits.png
Usage:  PYTHONPATH=src python scripts/plot_fig2_comp_audits.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figstyle import LOC_SERIES, plt, save
from pipeline.studies.productivity import event_by_adoption_month


def main() -> None:
    cohorts = sorted(event_by_adoption_month().items())
    fig, axes = plt.subplots(2, 3, figsize=(13, 7.5))
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
        ax.set_xticks(offs,
                      [(f"t{e:+d}" if e else "t0")
                       + f"\n{c['offsets'][e]['month'][2:]}" for e in offs],
                      fontsize=8)
        ax.set_xlabel("months from first observed AI use")
        ax.set_ylabel("kLOC / contributor / month")
        ax.set_ylim(bottom=0)
    handles, labels = axes.flat[0].get_legend_handles_labels()
    spare = list(axes.flat)[len(cohorts):]
    for ax in spare:
        ax.axis("off")
    spare[0].legend(handles, labels, loc="center", fontsize=10,
                    frameon=False)
    fig.tight_layout()
    save(fig, "artifacts/figure_2_comp_audits.png")


if __name__ == "__main__":
    main()
