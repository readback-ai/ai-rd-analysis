"""Window math (the banker's-rounding bug) and census checkpointing."""
import json
from datetime import date, timedelta

import pytest

from pipeline import census, ghx
from pipeline.census import census_repo_period, pull_cell, subwindows
from pipeline.scan_orgs import QUARTER_RANGES


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(census.time, "sleep", lambda s: None)
    return tmp_path


def _days_covered(windows):
    days = []
    for w in windows:
        a, b = (date.fromisoformat(x) for x in w.split(".."))
        assert a <= b, f"inverted range {w}"
        d = a
        while d <= b:
            days.append(d)
            d += timedelta(days=1)
    return days


@pytest.mark.parametrize("rng,k", [
    ("2026-01-01..2026-03-31", 10),   # standard quarter
    ("2026-04-01..2026-06-30", 10),   # Q2
    ("2024-01-01..2024-03-31", 10),   # leap-year quarter
    ("2026-01-01..2026-01-05", 10),   # k > days (the bug case)
    ("2026-01-01..2026-01-01", 10),   # single day
    ("2026-01-01..2026-12-31", 7),    # uneven split
])
def test_subwindows_cover_exactly_once(rng, k):
    s, e = (date.fromisoformat(x) for x in rng.split(".."))
    expected = [s + timedelta(days=i) for i in range((e - s).days + 1)]
    covered = _days_covered(subwindows(rng, k))
    assert covered == expected            # complete, ordered, no gap/overlap
    assert len(subwindows(rng, k)) <= k


def test_quarter_ranges_use_full_quarters():
    assert QUARTER_RANGES["Q2-2026"].endswith("2026-06-30")   # review gap P2.9


def test_pull_cell_checkpoints_and_skips_refetch(monkeypatch):
    calls = []
    monkeypatch.setattr(census, "graphql_nodes",
                        lambda *a, **k: calls.append(1) or [{"number": 1}])
    assert pull_cell("o/r", "2026-01-01..2026-01-31") == [{"number": 1}]
    assert pull_cell("o/r", "2026-01-01..2026-01-31") == [{"number": 1}]
    assert len(calls) == 1                # second call served from cell


def test_pull_cell_repulls_corrupt_cell(monkeypatch):
    p = ghx.cell_path("census", "o/r", "2026-01-01..2026-01-31")
    p.write_text(json.dumps({"errors": [{"type": "RATE_LIMIT"}]}))
    monkeypatch.setattr(census, "graphql_nodes", lambda *a, **k: [{"number": 2}])
    assert pull_cell("o/r", "2026-01-01..2026-01-31") == [{"number": 2}]
    assert json.loads(p.read_text()) == [{"number": 2}]


def test_pull_cell_failure_writes_nothing(monkeypatch):
    monkeypatch.setattr(census, "graphql_nodes", lambda *a, **k: None)
    assert pull_cell("o/r", "2026-02-01..2026-02-28") is None
    assert not ghx.cell_path("census", "o/r", "2026-02-01..2026-02-28").exists()


def test_census_small_repo_single_cell(monkeypatch):
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 30)
    pulled = []
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, rng: pulled.append(rng) or [{}] * 30)
    n = census_repo_period("o/r", "Q1-2026", cell_cap=50, k=10)
    assert n == 30 and pulled == [QUARTER_RANGES["Q1-2026"]]


def test_census_big_repo_subwindowed(monkeypatch):
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 500)
    pulled = []
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, rng: pulled.append(rng) or [{}] * 50)
    n = census_repo_period("o/r", "Q1-2026", cell_cap=50, k=10)
    assert n == 500 and len(pulled) == 10


def test_census_denominator_failure_propagates(monkeypatch):
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: None)
    assert census_repo_period("o/r", "Q1-2026", 50, 10) is None
