"""Figure 6: human review of merged PRs and LOC, with the bot-review
substitution — BOTH variants (formerly the plot_fig6_review{,_ai}.py
twin files; merged per the 2026-07-22 architecture review, candidate 2).

Two panels (share of merged PRs; share of merged LOC), each with the
{human-reviewed, bot-only-reviewed, self-merged-unreviewed} channels x a
dark/light slice pair — core vs external contributors, and AI-involved
vs non-AI PRs. The AI variant adds FLEET-operator PRs as a third slice
(dashed, in each channel's dark hue; the ai/nonai slices exclude fleet
authors). The AI slice is absent at the Q1-2024 baseline by construction
(no detectable channel existed). Merged outcomes are mature-gated.
Broken x-axis: Q1-2024 | Q4-2025..Q2-2026.

Data:    artifacts/data/review_mix.csv,
         artifacts/data/review_mix_by_ai.csv
Outputs: artifacts/review_mix.png, artifacts/review_mix_by_ai.png
Usage:   PYTHONPATH=src python scripts/plot_fig6_review.py
"""
import sys

sys.path.insert(0, "src")
from pipeline.figdata import Table, figure_main
from pipeline.figstyle import (broken_pair, cell, paired_series6, plt,
                               quarter_series, shade_q2_partial)
from pipeline.studies.productivity import PERIODS, review_mix

VARIANTS = [
    ("role", ("ins", "core"), ("ext", "external"),
     "artifacts/review_mix.png", False),
    ("ai", ("ai", "AI-involved"), ("nonai", "non-AI"),
     "artifacts/review_mix_by_ai.png", True),
]

UNITS = [("pr", "share of merged PRs", "% of merged PRs"),
         ("loc", "share of merged LOC", "% of merged LOC")]


def series_for(dark, light, fleet):
    """paired_series6 plus, for the AI variant, a dashed fleet series per
    channel in that channel's dark hue: at Q1-2024 the ai slice is absent,
    so the shared hue is unambiguous on the left panel, and dash-vs-solid
    separates them on the right."""
    out = [(ch, sl, color, "-", label)
           for ch, sl, color, label in paired_series6(dark, light)]
    if fleet:
        seen = {}
        for ch, sl, color, _ls, _label in out:
            seen.setdefault(ch, color)          # the dark hue comes first
        out += [(ch, "fleet", color, "--",
                 f"{label.split(' (')[0]} (fleet)")
                for (ch, _sl, color, _ls, label) in out[::2]]
    return out


def collect(name, by, dark, light, fleet=False) -> Table:
    rows = review_mix(by, fleet_slice=True) if fleet else review_mix(by)
    t = Table(name)
    for unit, title, _ylabel in UNITS:
        for ch, sl, _color, _ls, label in series_for(dark, light, fleet):
            t.add_series(unit, f"{ch}_{sl}",
                         [cell(rows, p, sl, f"{ch}_{unit}", scale=100)
                          for p in PERIODS],
                         x_labels=PERIODS, panel_label=title,
                         series_label=label)
    return t


def render(t: Table, dark, light, fleet=False):
    fig = plt.figure(figsize=(11, 4.6))
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, (unit, _title, ylabel) in zip(subfigs.flat, UNITS):
        axl, axr = broken_pair(sf, t.label_of(unit))
        for ch, sl, color, ls, label in series_for(dark, light, fleet):
            quarter_series(axl, axr, t.values(unit, f"{ch}_{sl}"),
                           color, label, ls=ls)
        # Q2-2026 is PARTIAL: only PRs whose w8 window closed by the
        # AS_OF are classified (early-quarter weighted until the re-pull)
        shade_q2_partial(axr)
        axl.set_ylim(0, 100)
        axl.set_ylabel(ylabel)
    handles, labels = axr.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center",
               ncol=3 if fleet else 4, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.1))
    return fig


def main() -> None:
    for by, dark, light, out, fleet in VARIANTS:
        name = out.split("/")[-1].removesuffix(".png")
        figure_main(lambda n=name, b=by, d=dark, li=light, fl=fleet:
                    collect(n, b, d, li, fl),
                    lambda t, d=dark, li=light, fl=fleet:
                    render(t, d, li, fl), out)


if __name__ == "__main__":
    main()
