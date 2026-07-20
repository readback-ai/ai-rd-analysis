"""Window math (the banker's-rounding bug), census checkpointing, and the
undercount/caching behavior from the 2026-07-03 review fixes."""
import json
from datetime import date, timedelta

import pytest

from pipeline import census, ghx
from pipeline.census import PAGE_SIZE, census_repo_period, pull_cell, subwindows
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


def test_page_size_is_interpolated_into_query():
    """Review finding: the fetch size was hardcoded separately from the cap."""
    assert f"first:{PAGE_SIZE}" in census.PR_QUERY
    assert "committer{" in census.PR_QUERY.replace(" ", "")   # codex-cloud field


def test_pull_cell_checkpoints_and_skips_refetch(monkeypatch):
    calls = []
    monkeypatch.setattr(census, "graphql_nodes",
                        lambda *a, **k: calls.append(1) or
                        {"nodes": [{"number": 1}], "pageInfo": {"hasNextPage": False}})
    assert pull_cell("o/r", "2026-01-01..2026-01-31") == ([{"number": 1}], False)
    assert pull_cell("o/r", "2026-01-01..2026-01-31") == ([{"number": 1}], True)
    assert len(calls) == 1                # second call served from cell


def test_pull_cell_repulls_corrupt_cell(monkeypatch):
    p = ghx.cell_path(census.STAGE, "o/r", "2026-01-01..2026-01-31")
    p.write_text(json.dumps({"errors": [{"type": "RATE_LIMIT"}]}))
    monkeypatch.setattr(census, "graphql_nodes",
                        lambda *a, **k: {"nodes": [{"number": 2}],
                                         "pageInfo": {"hasNextPage": False}})
    nodes, cached = pull_cell("o/r", "2026-01-01..2026-01-31")
    assert nodes == [{"number": 2}] and not cached
    assert json.loads(p.read_text()) == [{"number": 2}]


def test_pull_cell_paginates_within_window(monkeypatch):
    pages = [{"nodes": [{"number": i}], "pageInfo": {"hasNextPage": i < 2,
                                                     "endCursor": f"c{i}"}}
             for i in (1, 2)]
    monkeypatch.setattr(census.time, "sleep", lambda s: None)
    monkeypatch.setattr(census, "graphql_nodes", lambda *a, **k: pages.pop(0))
    nodes, cached = pull_cell("o/r", "2026-03-01..2026-03-01")
    assert [n["number"] for n in nodes] == [1, 2] and not cached


def test_pull_cell_failure_writes_nothing(monkeypatch):
    monkeypatch.setattr(census, "graphql_nodes", lambda *a, **k: None)
    assert pull_cell("o/r", "2026-02-01..2026-02-28") == (None, False)
    assert not ghx.cell_path(census.STAGE, "o/r", "2026-02-01..2026-02-28").exists()


def test_census_small_repo_single_cell(monkeypatch):
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 30)
    pulled = []
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, rng: (pulled.append(rng) or [{}] * 30, False))
    n = census_repo_period("o/r", "Q1-2026", k=10)
    assert n == 30 and pulled == [QUARTER_RANGES["Q1-2026"]]


def test_census_big_repo_subwindowed(monkeypatch):
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 500)
    pulled = []
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, rng: (pulled.append(rng) or [{}] * 42, False))
    n = census_repo_period("o/r", "Q1-2026", k=10)
    # adaptive: 500 PRs need ceil(500*1.1/45)=13 windows, not the k=10 floor
    assert len(pulled) == 13 and n == 13 * 42


def test_census_cached_full_cell_skips_denominator_call(monkeypatch):
    """Resume runs must not pay a search call per cached repo-period — but
    ONLY when the cached PRECOUNT corroborates the cell (external review
    P1: an unchecked fast path let brownout-poisoned empties through)."""
    rng = QUARTER_RANGES["Q1-2026"]
    ghx.cell_path(census.STAGE, "o/r", rng).write_text(json.dumps([{"number": 1}] * 3))
    ghx.cell_path("precount", "o/r", "Q1-2026").write_text(json.dumps({"total": 3}))
    def boom(*a, **k):
        raise AssertionError("rest_count must not be called on cached cells")
    monkeypatch.setattr(census, "rest_count", boom)
    assert census_repo_period("o/r", "Q1-2026", k=10) == 3


def test_census_poisoned_empty_cache_self_heals(monkeypatch):
    """External review P1: a cached-but-empty full-range cell contradicting
    the precount must fall through to the heal/re-pull path, not return 0."""
    rng = QUARTER_RANGES["Q1-2026"]
    ghx.cell_path(census.STAGE, "o/r", rng).write_text(json.dumps([]))
    ghx.cell_path("precount", "o/r", "Q1-2026").write_text(json.dumps({"total": 30}))
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 30)
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, r: ([{"number": i} for i in range(30)], False))
    assert census_repo_period("o/r", "Q1-2026", k=10) == 30


def test_census_heal_backs_off_before_repull(monkeypatch):
    """Repro RED first: an immediate heal re-pull likely hits the SAME
    search brownout; the heal branch must back off (sleep >=30s) before
    re-pulling."""
    ghx.cell_path("precount", "o/r", "Q1-2026").write_text(json.dumps({"total": 30}))
    sleeps = []
    monkeypatch.setattr(census.time, "sleep", lambda s: sleeps.append(s))
    calls = iter([[], [{"number": i} for i in range(30)]])   # brownout, then ok
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, r: (next(calls), False))
    assert census_repo_period("o/r", "Q1-2026", k=10) == 30
    assert any(s >= 30 for s in sleeps), sleeps


def test_census_fails_hard_on_saturation(monkeypatch, capsys):
    """External review finding 4: saturation must FAIL, not warn-succeed.
    Even adaptive windows can saturate on sub-day PR bursts."""
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 6000)
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, rng: ([{}] * PAGE_SIZE, False))
    # windows are capped at one per day (90), so 6000 PRs cannot fit
    n = census_repo_period("o/r", "Q1-2026", k=10)
    assert n is None
    assert "FAIL" in capsys.readouterr().err


def test_census_adaptive_windows_scale_with_volume(monkeypatch):
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 3000)
    pulled = []
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, rng: (pulled.append(rng) or [{}] * 40, False))
    census_repo_period("o/r", "Q1-2026", k=10)
    assert len(pulled) >= 70          # ceil(3300/45)=74 windows, not 10


def test_census_denominator_failure_propagates(monkeypatch):
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: None)
    assert census_repo_period("o/r", "Q1-2026", 10) is None


def test_census_uses_precount_cache_over_rest(monkeypatch):
    """Denominators come from the batch precount when available — no REST
    search call, no pacing sleep."""
    import json as _json
    from pipeline.precount import precount_path
    precount_path("o/r", "Q1-2026").write_text(_json.dumps({"total": 30}))
    def boom(*a, **k):
        raise AssertionError("REST denominator must not be called when precounted")
    monkeypatch.setattr(census, "rest_count", boom)
    monkeypatch.setattr(census, "pull_cell", lambda repo, rng: ([{}] * 30, False))
    assert census_repo_period("o/r", "Q1-2026", k=10) == 30


def test_deficit_triggers_self_heal_repull(monkeypatch, capsys):
    """Silently-incomplete cached cells (brownout empties) must be
    invalidated and re-pulled once before failing."""
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 100)
    calls = {"n": 0}
    def pull(repo, rng):
        calls["n"] += 1
        # first sweep: cached shorts; second sweep: complete
        first_sweep = calls["n"] <= 3
        return ([{}] * (10 if first_sweep else 34), first_sweep)
    monkeypatch.setattr(census, "pull_cell", pull)
    n = census_repo_period("o/r", "Q1-2026", k=3)
    assert n == 102 and "HEAL" in capsys.readouterr().err


def test_small_absolute_deficit_tolerated_as_precount_drift(monkeypatch):
    """PRs deleted after the precount snapshot leave permanent 1-3 PR gaps;
    those must not fail a 54-PR quarter forever."""
    monkeypatch.setattr(census, "rest_count", lambda *a, **k: 54)
    monkeypatch.setattr(census, "pull_cell",
                        lambda repo, rng: ([{}] * 26, False) if "01-01" in rng
                        else ([{}] * 26, False))
    n = census_repo_period("o/r", "Q1-2026", k=2)
    assert n == 52          # 52/54: within max(2%, 3) allowance -> success


def test_pull_cell_falls_back_to_small_pages_on_502(monkeypatch):
    """Persistent 502s on 50-PR pages (pathological payloads) must retry the
    window with small pages instead of failing the repo-period."""
    calls = []
    def fake_nodes(query, variables, jq, expect):
        calls.append("small" if "first:5" in query else "big")
        if "first:5" in query:
            return {"nodes": [{"number": 9}], "pageInfo": {"hasNextPage": False}}
        return None                      # big pages always 502
    monkeypatch.setattr(census, "graphql_nodes", fake_nodes)
    monkeypatch.setattr(census.time, "sleep", lambda s: None)
    nodes, cached = pull_cell("o/r", "2025-12-21..2025-12-21")
    assert nodes == [{"number": 9}] and "small" in calls
