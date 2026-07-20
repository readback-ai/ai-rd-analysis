"""Incremental monthly update — the trend-tracking runbook, executable.

Adds one month of data and refreshes the monthly trend tables. Semantics
(docs/METHODS.md §0 addendum):

- PROVISIONAL MONTHS: under the w8 rule a month's fate metrics stay open
  until ~8 weeks after month end, so each update RE-COLLECTS the previous
  TWO months (wipes their census cells first) before collecting the new
  one: N-1 for creation recency, N-2 for w8 finalization. A month's fates
  are final after it has been revised as N-2 (two updates after first
  collection); until then read it as provisional.
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
from pipeline.analyze import INCREMENTAL_REGISTRY  # noqa: E402
from pipeline.ghx import raw_dir  # noqa: E402
from pipeline.org_set import DRV  # noqa: E402
from pipeline.scan_orgs import QUARTER_RANGES, month_range, resolve_period  # noqa: E402


def previous_month(tok: str) -> str:
    y, m = int(tok[:4]), int(tok[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def months_to_revise(new: str) -> list[str]:
    """The two trailing months to wipe+re-collect when adding `new`:
    N-1 (creation recency — PRs still being opened/indexed) and N-2
    (w8 finalization — its last 8-week windows closed during month N-1/N,
    so this re-collection makes its fate metrics final). Revising only
    N-1 never finalizes anything under the w8 rule."""
    prev = previous_month(new)
    return [previous_month(prev), prev]


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
    revise = months_to_revise(new)
    repos = DRV / "population_repos.txt"
    coll = collectable(repos)
    for tok in revise:
        print(f"revising provisional month {tok}: wiped {wipe_month(tok)} cells")
    run("pipeline.precount", "--repos", str(coll), "--periods", *revise, new)
    run("pipeline.census", "--repos", str(coll), "--periods", *revise, new)
    # register the months PERSISTENTLY: later analyses (and later monthly
    # updates) must keep every incremental month, not just this invocation's
    reg = set()
    if INCREMENTAL_REGISTRY.is_file():
        reg = {ln.strip() for ln in
               INCREMENTAL_REGISTRY.read_text().splitlines() if ln.strip()}
    for tok in (*revise, new):
        start = resolve_period(tok).split("..")[0]
        inside_frozen = any(qr.split("..")[0] <= start <= qr.split("..")[1]
                            for qr in QUARTER_RANGES.values())
        if not inside_frozen:
            reg.add(tok)
    INCREMENTAL_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    INCREMENTAL_REGISTRY.write_text("\n".join(sorted(reg)) + "\n")
    print(f"incremental-month registry: {sorted(reg)}")
    print(f"\n=== monthly trend (newest month {new} is PROVISIONAL) ===")
    run("pipeline.analyze", "--granularity", "month",
        "--contributors", str(DRV / "repo_contributors_window.csv"),
        "--repos", str(repos), "--bootstrap", "1000")
