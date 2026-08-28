"""Generate every figure's data table and image in ONE process.

Each plot script can run on its own, but each run re-reads the census
store. This driver collects all tables in a single pass — the store is
read once and shared by every study function — then renders each figure
from its own table.

  PYTHONPATH=src python scripts/plot_all.py                 # tables + PNGs
  PYTHONPATH=src python scripts/plot_all.py --format png,svg
  PYTHONPATH=src python scripts/plot_all.py --from-tables   # render only,
                                                            # no census read

Usage: PYTHONPATH=src python scripts/plot_all.py [--from-tables]
                                                 [--format png,svg]
"""
import argparse
import functools
import sys
from pathlib import Path

sys.path.insert(0, "src")
sys.path.insert(0, "scripts")
from pipeline import figdata, frame                          # noqa: E402
from pipeline.figstyle import save                           # noqa: E402

import plot_adoption_cohorts as a1                           # noqa: E402
import plot_adoption_cohorts_median as a1a                    # noqa: E402
import plot_adoption_event as a2                             # noqa: E402
import plot_fig2_comp_audits as comp2                        # noqa: E402
import plot_fig3_comp_audits as comp3                        # noqa: E402
import plot_fig5_fleet as f5                                 # noqa: E402
import plot_fig5_fleet_median as f5a                          # noqa: E402
import plot_fig6_review as f6                                # noqa: E402
import plot_fig7_attention as f7                             # noqa: E402
import plot_fig8_responsiveness as f8                        # noqa: E402
import plot_paper_tables as paper                            # noqa: E402

ROLE, AI = f6.VARIANTS[0], f6.VARIANTS[1]

# (output path, collect, render) for every figure in the paper
FIGURES = [
    ("artifacts/fig2_ai_usage.png", paper.collect_usage, paper.render_usage),
    ("artifacts/fig3_core_loc.png", paper.collect_core, paper.render_core),
    ("artifacts/fig5_fleet_vs_nonadopters.png", f5.collect, f5.render),
    ("artifacts/fig6_review_mix.png",
     lambda: f6.collect("fig6_review_mix", ROLE[0], ROLE[1], ROLE[2]),
     lambda t: f6.render(t, ROLE[1], ROLE[2])),
    ("artifacts/fig6_review_mix_by_ai.png",
     lambda: f6.collect("fig6_review_mix_by_ai", AI[0], AI[1], AI[2]),
     lambda t: f6.render(t, AI[1], AI[2])),
    ("artifacts/fig7_attention_by_ai.png", f7.collect, f7.render),
    ("artifacts/fig8_responsiveness_by_ai.png", f8.collect, f8.render),
    ("artifacts/fig_a1_adoption_cohorts.png", a1.collect, a1.render),
    ("artifacts/fig_a2_adoption_event.png", a2.collect, a2.render),
    # median twins: same panels, typical member instead of cohort mean
    (f"artifacts/{f5a.NAME}.png", f5a.collect,
     functools.partial(f5.render, ylabel=f5a.YLABEL)),
    (f"artifacts/{a1a.NAME}.png", a1a.collect,
     functools.partial(a1.render, ylabel=a1a.YLABEL)),
    ("artifacts/figure_2_comp_audits.png", comp2.collect, comp2.render),
    ("artifacts/figure_3_comp_audits.png", comp3.collect, comp3.render),
]


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--from-tables", action="store_true",
                    help="render from artifacts/data/*.csv without "
                         "reading the census store")
    ap.add_argument("--format", default="png",
                    help="comma-separated image formats (png,svg)")
    a = ap.parse_args(argv)
    formats = a.format.split(",")

    if not a.from_tables:
        # one census read for the whole run: every study function reaches
        # the store through this loader
        frame.load_cells = functools.cache(frame.load_cells)

    failed = []
    for out, collect, render in FIGURES:
        name = Path(out).stem
        try:
            table = figdata.read(name) if a.from_tables else collect()
            if not a.from_tables:
                figdata.write(table)
            save(render(table), out, formats=formats)
        # SystemExit too, not just Exception: a study bails that way when
        # its inputs are stale (review_action on an out-of-date selection
        # manifest), and one such figure must not discard the shared
        # census pass the rest of the run depends on. KeyboardInterrupt
        # stays uncaught so an operator can still stop the run.
        except (Exception, SystemExit) as exc:
            failed.append((name, exc))
            print(f"FAILED {name}: {exc}", flush=True)
    if failed:
        raise SystemExit(f"{len(failed)} figure(s) failed: "
                         f"{[n for n, _ in failed]}")


if __name__ == "__main__":
    main()
