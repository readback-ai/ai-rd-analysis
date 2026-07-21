"""Figure 4a: the Figure 4 metrics in event time, net of non-adopters.

One panel per adopting cohort (fleet / early / middle / late): mean kLOC
per contributor per month at offsets t-2..t+2 around each author's first
observed AI month, with the contemporaneous NON-ADOPTER mean subtracted
from every observation (difference-in-differences: calendar drift
cancels; the y=0 line IS the non-adopter counterfactual). Same encoding
as Figure 4: blue = submitted, green = merged (w8), solid/dashed/dotted =
total/non-AI/AI-involved.

Output: artifacts/fig4a_adoption_event.png
Usage:  PYTHONPATH=src python scripts/plot_adoption_event.py
"""
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

sys.path.insert(0, "src")
from pipeline.studies.productivity import adoption_event  # noqa: E402

PANELS = [("fleet", "fleet operators"), ("early", "early adopters"),
          ("medium", "middle adopters"), ("late", "late adopters")]
SERIES = [
    ("submitted", "tab:blue", "-", "submitted total"),
    ("sub_nonai", "tab:blue", "--", "submitted non-AI"),
    ("sub_ai", "tab:blue", ":", "submitted AI-involved"),
    ("merged", "tab:green", "-", "merged total (w8)"),
    ("mrg_nonai", "tab:green", "--", "merged non-AI"),
    ("mrg_ai", "tab:green", ":", "merged AI-involved"),
]


def main() -> None:
    rows = adoption_event()
    offs = list(range(-2, 3))
    fig, axes = plt.subplots(2, 2, figsize=(10, 7))
    fig.suptitle("Figure 4a: LOC per contributor around first AI adoption "
                 "(event time), net of the non-adopter mean", fontsize=12)
    for ax, (coh, title) in zip(axes.flat, PANELS):
        for key, color, ls, label in SERIES:
            y = [rows.get((coh, e), {}).get(key) for e in offs]
            ax.plot(offs, y, marker="o", ms=3, ls=ls, color=color,
                    label=label)
        ns = [rows.get((coh, e), {}).get("n", 0) for e in offs]
        ax.axhline(0, color="k", lw=0.8)
        ax.set_title(f"{title} (n={min(n for n in ns if n)}–{max(ns)})",
                     fontsize=10, loc="left")
        ax.set_xticks(offs, [f"t{e:+d}" if e else "t0" for e in offs])
        ax.set_xlabel("months from first observed AI use")
        ax.set_ylabel("kLOC/month, net of non-adopters")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=3, fontsize=9,
               frameon=False, bbox_to_anchor=(0.5, -0.04))
    fig.tight_layout()
    fig.savefig("artifacts/fig4a_adoption_event.png", dpi=200,
                bbox_inches="tight")
    print("wrote artifacts/fig4a_adoption_event.png")


if __name__ == "__main__":
    main()
