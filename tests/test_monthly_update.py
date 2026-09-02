"""Monthly-update wipe semantics: the provisional-month wipe happens
exactly once per target-month cycle, so a rerun after a mid-census
failure resumes collection instead of discarding a night's work."""
import json
import sys
from datetime import datetime, timezone

import pytest

sys.path.insert(0, "scripts")
import monthly_update  # noqa: E402

from pipeline import detect, ghx  # noqa: E402

# The data stamp advances at every re-pull (METHODS §1c), so tests that
# turn on maturity pin their own rather than riding the constant. This
# one clears June-2026's last creation instant by an hour.
AS_OF_JUNE_FINAL = "2026-08-26T00:00:00Z"


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def stub_run(tmp_path, monkeypatch):
    """Isolate `main` from the real store: record the stage invocations
    instead of shelling out, and point the derived inputs at tmp."""
    drv = tmp_path / "derived"
    drv.mkdir()
    (drv / "population_repos.txt").write_text("o/r\n")
    monkeypatch.setattr(monthly_update, "DRV", drv)
    monkeypatch.setattr(monthly_update, "INCREMENTAL_REGISTRY",
                        drv / "incremental_months.txt")
    monkeypatch.setattr(detect, "AS_OF", AS_OF_JUNE_FINAL)
    monkeypatch.setattr(monthly_update, "_utcnow",
                        lambda: datetime(2026, 8, 26, tzinfo=timezone.utc))
    calls = []
    monkeypatch.setattr(monthly_update, "run",
                        lambda mod, *args: calls.append((mod, args)))
    return calls


def _periods(calls, mod):
    args = next(a for m, a in calls if m == mod)
    return list(args[args.index("--periods") + 1:])


def _cell(repo, rng, prs):
    p = ghx.cell_path("census-v2", repo, rng)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(prs))
    return p


def test_wipe_happens_once_per_cycle_so_reruns_resume():
    """2026-08-02 monthly-update abort: rerunning after a mid-census
    failure re-wiped the revision months, discarding ~5,900 freshly
    collected cells. The wipe must be recorded per target month and
    skipped on rerun, preserving cells collected since."""
    may = "2026-05-01..2026-05-31"
    stale = _cell("o/r", may, [{"number": 1}])
    monthly_update.ensure_wiped("2026-07", ["2026-05", "2026-06"])
    assert not stale.exists()                    # first run wipes
    fresh = _cell("o/r", may, [{"number": 1}, {"number": 2}])
    monthly_update.ensure_wiped("2026-07", ["2026-05", "2026-06"])
    assert fresh.exists()                        # rerun preserves
    assert json.loads(fresh.read_text()) == [{"number": 1},
                                             {"number": 2}]


def test_a_new_target_month_wipes_its_own_revision_window():
    jun = "2026-06-01..2026-06-30"
    cell = _cell("o/r", jun, [{"number": 3}])
    monthly_update.ensure_wiped("2026-07", ["2026-05", "2026-06"])
    assert not cell.exists()
    cell = _cell("o/r", jun, [{"number": 4}])
    # the NEXT cycle revises 2026-06/2026-07 — June wipes again
    monthly_update.ensure_wiped("2026-08", ["2026-06", "2026-07"])
    assert not cell.exists()


def test_revise_only_skips_the_target_months_own_collection(stub_run):
    """A w8 finalization run can fall mid-month, when the target month
    is still partial. --revise-only re-collects the revision window
    (N-2 finalizing, N-1 for creation recency) and leaves the target
    month uncollected."""
    monthly_update.main(["2026-08", "--revise-only"])
    assert _periods(stub_run, "pipeline.precount") == ["2026-06", "2026-07"]
    assert _periods(stub_run, "pipeline.census") == ["2026-06", "2026-07"]


def test_revise_only_does_not_register_an_uncollected_month(stub_run):
    """The registry drives which months `analyze` reads, so a month
    skipped by --revise-only must stay out of it."""
    monthly_update.main(["2026-08", "--revise-only"])
    reg = monthly_update.INCREMENTAL_REGISTRY.read_text().split()
    assert "2026-08" not in reg
    assert "2026-07" in reg                      # N-1, outside frozen Q2


def test_revise_only_wipe_log_does_not_shadow_the_full_update(stub_run):
    """The wipe log is keyed per cycle and suppresses a repeat wipe. A
    revise-only run must not consume the target month's key, or the
    later full update would skip re-collecting its revision window."""
    monthly_update.main(["2026-08", "--revise-only"])
    jun = _cell("o/r", "2026-06-01..2026-06-30", [{"number": 5}])
    monthly_update.ensure_wiped("2026-08", ["2026-06", "2026-07"])
    assert not jun.exists()


def test_full_update_keeps_the_month_its_revise_only_cycle_finalized(
        stub_run):
    """The 2026-08 full update re-wiped and re-collected June-2026 even
    though the 2026-08 revise-only cycle had already finalized it — that
    run is gated on June's w8 windows being closed, so its cells are
    final, and a second wipe can only lose PRs deleted since while
    re-spending a month of census. N-1 must still be wiped (creation
    recency), and the finalized month stays in the collection list so a
    partial revise-only census completes through the checkpoint."""
    monthly_update.main(["2026-08", "--revise-only"])
    jun = _cell("o/r", "2026-06-01..2026-06-30", [{"number": 6}])
    jul = _cell("o/r", "2026-07-01..2026-07-31", [{"number": 7}])
    monthly_update.main(["2026-08"])
    assert jun.exists()                   # finalized N-2 stays frozen
    assert not jul.exists()               # N-1 revision still wipes
    census = [a for m, a in stub_run if m == "pipeline.census"][-1]
    assert list(census[census.index("--periods") + 1:]) == \
        ["2026-06", "2026-07", "2026-08"]


def test_full_update_still_collects_the_target_month(stub_run):
    monthly_update.main(["2026-08"])
    assert _periods(stub_run, "pipeline.census") == ["2026-06", "2026-07",
                                                     "2026-08"]
    reg = monthly_update.INCREMENTAL_REGISTRY.read_text().split()
    assert "2026-08" in reg


def test_windows_closed_tracks_the_last_creation_instant():
    """A month is finalizable only once its LAST creation instant clears
    w8: June-2026 needs a stamp of 2026-08-26, not 2026-08-25 (which
    leaves PRs created on June 30 immature)."""
    assert monthly_update.finalization_stamp("2026-06") == \
        "2026-08-25T23:59:59Z"


def test_finalizing_before_the_windows_close_is_refused(stub_run,
                                                        monkeypatch):
    """A run one day early marks N-2 final while its last day's PRs are
    still immature, and N-2 is never re-collected afterwards — so the
    undercount is permanent. Refuse BEFORE wiping anything."""
    monkeypatch.setattr(detect, "AS_OF", "2026-08-25T00:00:00Z")
    jun = _cell("o/r", "2026-06-01..2026-06-30", [{"number": 1}])
    with pytest.raises(SystemExit) as e:
        monthly_update.main(["2026-08", "--revise-only"])
    assert "2026-08-25T23:59:59Z" in str(e.value)   # the stamp it needs
    assert jun.exists()                             # nothing was wiped
    assert stub_run == []                           # no stage ran


def test_finalization_proceeds_once_the_windows_close(stub_run,
                                                      monkeypatch):
    monkeypatch.setattr(detect, "AS_OF", "2026-08-26T00:00:00Z")
    monthly_update.main(["2026-08", "--revise-only"])
    assert _periods(stub_run, "pipeline.census") == ["2026-06", "2026-07"]


def test_a_stamp_ahead_of_the_run_is_refused(monkeypatch):
    """AS_OF is the data-collection stamp, so it must never lead the run:
    a forward-dated stamp would mark PRs mature whose events the census
    has not observed yet, reading unobserved merges as never-merged."""
    monkeypatch.setattr(detect, "AS_OF", AS_OF_JUNE_FINAL)
    early = datetime(2026, 8, 25, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(SystemExit) as e:
        monthly_update.check_finalizable("2026-06", now=early)
    assert "ahead of" in str(e.value)


def test_a_stamp_at_the_run_instant_is_accepted(monkeypatch):
    monkeypatch.setattr(detect, "AS_OF", AS_OF_JUNE_FINAL)
    at_instant = datetime(2026, 8, 26, 0, 0, tzinfo=timezone.utc)
    monthly_update.check_finalizable("2026-06", now=at_instant)
