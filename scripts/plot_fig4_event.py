"""Figure 4: productivity metrics around the first month of AI adoption.

One BALANCED event panel pooling every non-fleet adopter whose full
[-2..+2] window fits the data (first AI use 2025-12..2026-04): six
series — submitted/merged (blue/green) x total/non-AI/AI-involved
(solid/dashed/dotted) — as raw mean kLOC per author per month. Offsets
containing w8-open calendar months are shaded with the affected share
annotated (merged provisional there; finalizes with the AS_OF re-pulls).

Output: artifacts/fig4_event_balanced.png
Usage:  PYTHONPATH=src python scripts/plot_fig4_event.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.productivity import event_balanced  # noqa: E402

SERIES = [
    ("submitted", "tab:blue", "-", "submitted total"),
    ("sub_nonai", "tab:blue", "--", "submitted non-AI"),
    ("sub_ai", "tab:blue", ":", "submitted AI-involved"),
    ("merged", "tab:green", "-", "merged total (w8)"),
    ("mrg_nonai", "tab:green", "--", "merged non-AI"),
    ("mrg_ai", "tab:green", ":", "merged AI-involved"),
]


def main() -> None:
    rows = event_balanced()
    offs = sorted(rows)
    fig, (ax, axleg) = plt.subplots(1, 2, figsize=(9, 4.4),
                                    gridspec_kw={"width_ratios": [2.2, 1]})
    n = rows[0]["n"]
    fig.suptitle("Figure 4: LOC per contributor around first AI adoption\n"
                 f"(balanced panel: first AI use 2025-12..2026-04, n={n})",
                 fontsize=12)
    for key, color, ls, label in SERIES:
        ax.plot(offs, [rows[e][key] for e in offs], marker="o", ms=3.5,
                ls=ls, color=color, label=label)
    shaded = False
    for e in offs:
        sh = rows[e]["immature_share"]
        if sh > 0:
            ax.axvspan(e - 0.5, e + 0.5, color="0.85", alpha=0.5, zorder=0,
                       label=None if shaded else
                       "offset contains w8-open months\n(merged provisional)")
            ax.annotate(f"{sh:.0%}", (e, 0), xycoords=("data",
                        "axes fraction"), xytext=(0, 2),
                        textcoords="offset points", ha="center",
                        fontsize=7, color="0.4")
            shaded = True
    ax.set_xticks(offs, [f"t{e:+d}" if e else "t0" for e in offs])
    ax.set_xlabel("months from first observed AI use")
    ax.set_ylabel("kLOC / contributor / month")
    ax.set_ylim(bottom=0)
    handles, labels = ax.get_legend_handles_labels()
    axleg.axis("off")
    axleg.legend(handles, labels, loc="center", fontsize=9, frameon=False)
    fig.tight_layout()
    fig.savefig("artifacts/fig4_event_balanced.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig4_event_balanced.png")


if __name__ == "__main__":
    main()
