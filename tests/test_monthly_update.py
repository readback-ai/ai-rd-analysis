"""Monthly-update wipe semantics: the provisional-month wipe happens
exactly once per target-month cycle, so a rerun after a mid-census
failure resumes collection instead of discarding a night's work."""
import json
import sys

import pytest

sys.path.insert(0, "scripts")
import monthly_update  # noqa: E402

from pipeline import ghx  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    return tmp_path


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
