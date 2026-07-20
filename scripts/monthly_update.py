"""Incremental monthly update — the trend-tracking runbook, executable.

Adds one month of data and refreshes the monthly trend tables. Semantics
(docs/METHODS.md §0 addendum):

- PROVISIONAL MONTH: reviews and merges lag PR creation, so the most recent
  month is always preliminary. Each update therefore RE-COLLECTS the previous
  month (wipes its census-v2 cells first) before collecting the new one, and
  the newest month should be read as provisional until the next update.
- The population and classification metadata stay FROZEN between deliberate
  revisions — a monthly update adds activity data only, so trend movements
  are practice changes, not population artifacts.

Usage:
  PYTHONPATH=src python scripts/monthly_update.py 2026-07
  (collects 2026-07 fresh, re-collects 2026-06, prints monthly tables)
"""
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, "src")
from pipeline.ghx import raw_dir  # noqa: E402
from pipeline.org_set import DRV  # noqa: E402
from pipeline.scan_orgs import month_range, resolve_period  # noqa: E402


def previous_month(tok: str) -> str:
    y, m = int(tok[:4]), int(tok[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def wipe_month(tok: str) -> int:
    """Invalidate a month's census cells so it re-collects fresh (the
    provisional-month revision)."""
    rng = resolve_period(tok)
    start, end = rng.split("..")
    wiped = 0
    for f in raw_dir("census-v2").glob("*.json"):
        try:
            cell_start = f.stem.split("@")[1].split("..")[0]
        except IndexError:
            continue
        if start <= cell_start <= end:
            f.unlink()
            wiped += 1
    # month precounts too — totals move as PRs are deleted/created
    for f in raw_dir("precount").glob(f"*@{tok}.json"):
        f.unlink()
        wiped += 1
    return wiped


def run(mod: str, *args: str) -> None:
    r = subprocess.run([sys.executable, "-m", mod, *args])
    if r.returncode != 0:
        raise SystemExit(f"{mod} failed")


def collectable(repos: Path) -> Path:
    """Population minus documented-inaccessible repos — same waiver as
    regenerate stage C; retrying all 71 dead repos would trip the
    fail-hard census (external review P1)."""
    skip_p = DRV / "inaccessible_repos.txt"
    skip = set(skip_p.read_text().split()) if skip_p.exists() else set()
    todo = [r for r in repos.read_text().split() if r not in skip]
    out = DRV / "population_repos_collectable.txt"
    out.write_text("\n".join(todo) + "\n")
    print(f"collecting {len(todo)} repos ({len(skip)} documented "
          f"inaccessible, waived)", flush=True)
    return out


if __name__ == "__main__":
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    new = sys.argv[1]
    month_range(new)                       # validates the token
    prev = previous_month(new)
    repos = DRV / "population_repos.txt"
    coll = collectable(repos)
    print(f"revising provisional month {prev}: wiped {wipe_month(prev)} cells")
    run("pipeline.precount", "--repos", str(coll), "--periods", prev, new)
    run("pipeline.census", "--repos", str(coll), "--periods", prev, new)
    print(f"\n=== monthly trend (newest month {new} is PROVISIONAL) ===")
    run("pipeline.analyze", "--granularity", "month", "--markers", "v2",
        "--contributors", str(DRV / "repo_contributors_window.csv"),
        "--repos", str(repos), "--bootstrap", "1000",
        "--periods", prev, new)
