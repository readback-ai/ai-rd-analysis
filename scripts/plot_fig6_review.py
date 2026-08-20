"""Figure 6: human review of merged PRs and LOC, with the bot-review
substitution — BOTH variants (formerly the plot_fig6_review{,_ai}.py
twin files; merged per the 2026-07-22 architecture review, candidate 2).

Two panels (share of merged PRs; share of merged LOC), each with six
series: {human-reviewed, bot-only-reviewed, self-merged-unreviewed} x a
dark/light slice pair — core vs external contributors, and AI-involved
vs non-AI PRs. The AI slice is absent at the Q1-2024 baseline by
construction (no detectable channel existed). Merged outcomes are
mature-gated (Q2-2026 reflects PRs whose w8 window closed; finalizes
with AS_OF re-pulls). Broken x-axis: Q1-2024 | Q4-2025..Q2-2026.

Data:    artifacts/data/fig6_review_mix.csv,
         artifacts/data/fig6_review_mix_by_ai.csv
Outputs: artifacts/fig6_review_mix.png, artifacts/fig6_review_mix_by_ai.png
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
     "Figure 6: review of merged PRs and merged LOC — core vs external "
     "(fleet authors excluded)",
     "artifacts/fig6_review_mix.png"),
    ("ai", ("ai", "AI-involved"), ("nonai", "non-AI"),
     "Figure 6 (alt): review of merged PRs and merged LOC — AI vs "
     "non-AI PRs (fleet authors excluded)",
     "artifacts/fig6_review_mix_by_ai.png"),
]

UNITS = [("pr", "share of merged PRs", "% of merged PRs"),
         ("loc", "share of merged LOC", "% of merged LOC")]


def collect(name, by, dark, light) -> Table:
    rows = review_mix(by)
    t = Table(name)
    for unit, title, _ylabel in UNITS:
        for ch, sl, _color, label in paired_series6(dark, light):
            t.add_series(unit, f"{ch}_{sl}",
                         [cell(rows, p, sl, f"{ch}_{unit}", scale=100)
                          for p in PERIODS],
                         x_labels=PERIODS, panel_label=title,
                         series_label=label)
    return t


def render(t: Table, dark, light, suptitle):
    fig = plt.figure(figsize=(11, 4.6))
    fig.suptitle(suptitle, fontsize=12, y=-0.16)   # below the bottom legend
    subfigs = fig.subfigures(1, 2, wspace=0.05)
    for sf, (unit, _title, ylabel) in zip(subfigs.flat, UNITS):
        axl, axr = broken_pair(sf, t.label_of(unit))
        for ch, sl, color, label in paired_series6(dark, light):
            quarter_series(axl, axr, t.values(unit, f"{ch}_{sl}"),
                           color, label)
        # Q2-2026 is PARTIAL: only PRs whose w8 window closed by the
        # AS_OF are classified (early-quarter weighted until the re-pull)
        shade_q2_partial(axr)
        axl.set_ylim(0, 100)
        axl.set_ylabel(ylabel)
    handles, labels = axr.get_legend_handles_labels()
    fig.legend(handles, labels, loc="lower center", ncol=4, fontsize=8,
               frameon=False, bbox_to_anchor=(0.5, -0.08))
    return fig


def main() -> None:
    for by, dark, light, suptitle, out in VARIANTS:
        name = out.split("/")[-1].removesuffix(".png")
        figure_main(lambda n=name, b=by, d=dark, li=light:
                    collect(n, b, d, li),
                    lambda t, d=dark, li=light, s=suptitle:
                    render(t, d, li, s), out)


if __name__ == "__main__":
    main()
