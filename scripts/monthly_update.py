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
- --REVISE-ONLY runs the revision window without collecting the target
  month, for a finalization that has to land mid-month: N-2's w8 windows
  close 8 weeks after its month end, which falls partway through month N.
  The target month stays uncollected and unregistered, and keeps its own
  wipe-log cycle for the later full update.

Usage:
  PYTHONPATH=src python scripts/monthly_update.py 2026-07
  (collects 2026-07 fresh, re-collects 2026-06 and 2026-05, prints tables)
  PYTHONPATH=src python scripts/monthly_update.py 2026-08 --revise-only
  (re-collects 2026-06 and 2026-07 only — finalizes June, skips August)
"""
import argparse
import json
import subprocess
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, "src")
from pipeline import detect  # noqa: E402
from pipeline.analyze import INCREMENTAL_REGISTRY  # noqa: E402
from pipeline.ghx import raw_dir  # noqa: E402
from pipeline.org_set import DRV  # noqa: E402
from pipeline.scan_orgs import QUARTER_RANGES, month_range, resolve_period  # noqa: E402

_STAMP = "%Y-%m-%dT%H:%M:%SZ"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def previous_month(tok: str) -> str:
    y, m = int(tok[:4]), int(tok[5:7])
    return f"{y - 1}-12" if m == 1 else f"{y}-{m - 1:02d}"


def finalization_stamp(tok: str) -> str:
    """Earliest AS_OF at which every PR created in `tok` has reached the
    w8 horizon: the month's LAST creation instant plus W8_DAYS. A stamp
    even a day short leaves the month's final day immature."""
    last = datetime.strptime(f"{month_range(tok).split('..')[1]}T23:59:59Z",
                             _STAMP)
    return (last + timedelta(days=detect.W8_DAYS)).strftime(_STAMP)


def check_finalizable(tok: str, now: datetime | None = None) -> None:
    """Refuse to revise `tok` as N-2 unless the data stamp both covers it
    and is honest about this run.

    Too EARLY a stamp publishes `tok` as final with its last days' PRs
    carrying no fate, and N-2 is never re-collected again, so the
    undercount is permanent. A stamp AHEAD of the run marks PRs mature
    whose events the census has not observed yet, so an unobserved merge
    reads as never-merged."""
    stamp = datetime.strptime(detect.AS_OF, _STAMP).replace(tzinfo=timezone.utc)
    need = finalization_stamp(tok)
    if stamp < datetime.strptime(need, _STAMP).replace(tzinfo=timezone.utc):
        raise SystemExit(
            f"refusing to finalize {tok}: detect.AS_OF is {detect.AS_OF}, "
            f"but its w8 windows close at {need}. Run on/after that "
            f"instant and bump AS_OF to the run's start date (METHODS "
            f"§1c step 2).")
    now = now or _utcnow()
    if stamp > now:
        raise SystemExit(
            f"refusing to finalize {tok}: detect.AS_OF ({detect.AS_OF}) is "
            f"ahead of this run ({now.strftime(_STAMP)}). The stamp records "
            f"when the census was pulled — wait until it passes.")


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


def cycle_key(new: str, revise_only: bool) -> str:
    """Wipe-log key for a run. A revise-only run gets its own key so it
    does not consume the target month's cycle: the later full update
    must still wipe and re-collect its revision window."""
    return f"{new}:revise-only" if revise_only else new


def ensure_wiped(cycle: str, revise: list[str]) -> None:
    """Wipe the revision months exactly ONCE per cycle. The wipe log
    lives beside the store it clears (raw/monthly_wipes.json), so
    rerunning the update after a mid-census failure resumes the
    checkpointed collection instead of discarding it. A different cycle
    wipes its own revision window. To force a re-wipe of the same cycle
    deliberately, delete the log entry."""
    from pipeline.ghx import data_dir
    log = data_dir() / "raw" / "monthly_wipes.json"
    done = json.loads(log.read_text()) if log.is_file() else {}
    if done.get(cycle) == revise:
        print(f"revision months already wiped this cycle ({cycle}); "
              f"resuming collection", flush=True)
        return
    for tok in revise:
        print(f"revising provisional month {tok}: "
              f"wiped {wipe_month(tok)} cells", flush=True)
    done[cycle] = revise
    log.parent.mkdir(parents=True, exist_ok=True)
    log.write_text(json.dumps(done))


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


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("month", help="target month, YYYY-MM")
    ap.add_argument("--revise-only", action="store_true",
                    help="re-collect the revision window only; leave the "
                         "target month uncollected and unregistered")
    a = ap.parse_args(argv)
    new = a.month
    month_range(new)                       # validates the token
    revise = months_to_revise(new)
    check_finalizable(revise[0])           # before anything is wiped
    collect = list(revise) if a.revise_only else [*revise, new]
    repos = DRV / "population_repos.txt"
    coll = collectable(repos)
    ensure_wiped(cycle_key(new, a.revise_only), revise)
    run("pipeline.precount", "--repos", str(coll), "--periods", *collect)
    run("pipeline.census", "--repos", str(coll), "--periods", *collect)
    # register the months PERSISTENTLY: later analyses (and later monthly
    # updates) must keep every incremental month, not just this invocation's
    reg = set()
    if INCREMENTAL_REGISTRY.is_file():
        reg = {ln.strip() for ln in
               INCREMENTAL_REGISTRY.read_text().splitlines() if ln.strip()}
    for tok in collect:
        start = resolve_period(tok).split("..")[0]
        inside_frozen = any(qr.split("..")[0] <= start <= qr.split("..")[1]
                            for qr in QUARTER_RANGES.values())
        if not inside_frozen:
            reg.add(tok)
    INCREMENTAL_REGISTRY.parent.mkdir(parents=True, exist_ok=True)
    INCREMENTAL_REGISTRY.write_text("\n".join(sorted(reg)) + "\n")
    print(f"incremental-month registry: {sorted(reg)}")
    newest = collect[-1]
    note = (f"{revise[0]} is now FINAL; newest month {newest} is PROVISIONAL"
            if a.revise_only else f"newest month {newest} is PROVISIONAL")
    print(f"\n=== monthly trend ({note}) ===")
    run("pipeline.analyze", "--granularity", "month",
        "--contributors", str(DRV / "repo_contributors_window.csv"),
        "--repos", str(repos), "--bootstrap", "1000")


if __name__ == "__main__":
    main()
