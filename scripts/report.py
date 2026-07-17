"""Generate the full study report at quarter or month granularity.

Same six sections either way (docs/METRICS.md §5): contributor-weighted
metrics, exact layered decomposition, slice involvement, slice self-merge,
balanced panel, two-sided bound. Quarterly is the canonical headline path
(invoked by scripts/regenerate.py stage F, which also gates on coverage and
writes the census manifest); monthly is the trend view (2-PR/month floor,
newest month PROVISIONAL if produced mid-update — see METHODS §1c).

Usage:
  PYTHONPATH=src python scripts/report.py --granularity month
  PYTHONPATH=src python scripts/report.py                     # quarterly
"""
import argparse
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")
from pipeline.org_set import DRV  # noqa: E402

CAPTION = (
    "> Q1-2024 columns are a detector-validity check and review-practice "
    "baseline,\n> NOT an AI-usage estimate: the detectable channels "
    "(trailers, agent accounts,\n> branch conventions) did not exist yet, "
    "while autocomplete-era assistance was\n> already widespread and is "
    "invisible to every layer. All rates are floors\n> (one quantified "
    "exception: the two-sided bound section).\n\n")


def sections(granularity: str, repos: Path) -> list[tuple[str, list[str]]]:
    g = ["--granularity", granularity]
    return [
        ("Contributor-weighted metrics",
         ["pipeline.analyze", *g, "--markers", "v2", "--contributors",
          str(DRV / "repo_contributors_window.csv"),
          "--repos", str(repos), "--bootstrap", "2000"]),
        ("Figure 2: Traceable AI usage over time (CW, 95% CI)",
         ["pipeline.studies.paper_tables", "--table", "usage"]),
        ("Figure 3: Merged LOC per core contributor over time (CW, 95% CI)",
         ["pipeline.studies.paper_tables", "--table", "core"]),
        ("Layered decomposition (pooled)", ["pipeline.integrate", *g]),
        ("Slices: involvement",
         ["pipeline.studies.slices", *g, "--table", "involvement"]),
        ("Slices: self-merge",
         ["pipeline.studies.slices", *g, "--table", "selfmerge"]),
        ("Balanced-panel sensitivity",
         ["pipeline.studies.slices", *g, "--table", "panel"]),
        ("Reviewer profile of merged PRs (unmerged = implicitly rejected)",
         ["pipeline.studies.slices", *g, "--table", "reviewers"]),
        ("Two-sided bound (weak-prefix indeterminates)",
         ["pipeline.studies.slices", *g, "--table", "bounds"]),
        ("Productivity decomposition (authors vs output/author)",
         ["pipeline.studies.productivity", "--cut", "decomposition"]),
        ("Persistent-author productivity (same person, same repo)",
         ["pipeline.studies.productivity", "--cut", "persistent"]),
        ("Core-contributor merged LOC (CW)",
         ["pipeline.studies.productivity", "--cut", "core"]),
        ("Core-contributor merged LOC split by AI involvement (CW, 95% CI)",
         ["pipeline.studies.productivity", "--cut", "aisplit"]),
        ("Merged LOC by approval channel",
         ["pipeline.studies.productivity", "--cut", "channels"]),
        ("Attention per line (comments/kLOC primary, bot-clean)",
         ["pipeline.studies.attention"]),
        ("PR fates at matched horizons (w8 primary, w26 sensitivity)",
         ["pipeline.studies.fates"]),
        ("Responsiveness to human asks (clean lane identified)",
         ["pipeline.studies.review_action"]),
        ("Adoption event-study (merged kLOC w8 + submitted kLOC "
         "in event time)",
         ["pipeline.studies.event_study"]),
    ]


def generate(granularity: str, out: Path,
             repos: Path | None = None) -> None:
    repos = repos or DRV / "population_repos.txt"
    with out.open("w") as fh:
        fh.write(f"# GENERATED {granularity}ly report — scripts/report.py\n\n")
        fh.write(CAPTION)
        for title, args in sections(granularity, repos):
            r = subprocess.run([sys.executable, "-m", *args],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit(f"{args[0]} failed:\n{r.stderr[-800:]}")
            fh.write(f"## {title}\n```\n{r.stdout}\n```\n\n")
            print(f"section done: {title}", flush=True)
    print(f"wrote {out}", flush=True)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--granularity", choices=["quarter", "month"],
                    default="quarter")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    default_out = ("artifacts/report_generated.md" if a.granularity == "quarter"
                   else "artifacts/report_monthly.md")
    generate(a.granularity, Path(a.out or default_out))
