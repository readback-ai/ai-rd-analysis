"""Checkpoint semantics for the scan and enum stages: failed pulls must never
be recorded as zeros, cache keys must include every content-determining
parameter, and BOTH branches of the keep rule must work."""
import json

import pytest

from pipeline import enum_repos, scan_orgs
from pipeline.detect import MARKERS_V1, MARKERS_V2
from pipeline.ghx import cell_path

N_TERMS_V1 = sum(len(s.search_terms) for s in MARKERS_V1.values())


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(scan_orgs.time, "sleep", lambda s: None)
    monkeypatch.setattr(enum_repos.time, "sleep", lambda s: None)
    return tmp_path


def test_scan_org_checkpoints_and_skips(monkeypatch):
    calls = []
    monkeypatch.setattr(scan_orgs, "rest_count",
                        lambda q, **k: calls.append(q) or 7)
    res = scan_orgs.scan_org("acme", "Q1-2026", MARKERS_V1, "v1")
    assert res["claude"]["count"] == 7 and res["cursor"]["count"] == 7
    assert scan_orgs.scan_org("acme", "Q1-2026", MARKERS_V1, "v1") == res
    assert len(calls) == N_TERMS_V1              # second call fully cached
    # bare-term + date qualifier, never author-email:
    assert calls[0] == "org:acme noreply@anthropic.com author-date:2026-01-01..2026-03-31"
    assert "author-email" not in calls[0]
    # ALL terms searched (footer too), count = max over terms
    assert any("Generated with [Claude Code]" in c for c in calls)


def test_scan_count_is_max_over_terms_not_sum(monkeypatch):
    seq = iter([10, 8, 3])                        # claude email, claude footer, cursor
    monkeypatch.setattr(scan_orgs, "rest_count", lambda q, **k: next(seq))
    res = scan_orgs.scan_org("acme", None, MARKERS_V1, "v1")
    assert res["claude"]["count"] == 10           # max(10, 8), NOT 18
    assert res["claude"]["terms"] == [10, 8]


def test_scan_cache_key_includes_range_and_markers(monkeypatch):
    """Review finding: under-keyed caches served stale results. A different
    marker set (or quarter definition) must MISS the cache, not hit it."""
    monkeypatch.setattr(scan_orgs, "rest_count", lambda q, **k: 1)
    scan_orgs.scan_org("acme", "Q1-2026", MARKERS_V1, "v1")
    assert cell_path("scan_orgs", "acme", "2026-01-01..2026-03-31", "v1").exists()
    calls = []
    monkeypatch.setattr(scan_orgs, "rest_count", lambda q, **k: calls.append(q) or 2)
    res = scan_orgs.scan_org("acme", "Q1-2026", MARKERS_V2, "v2")
    assert calls, "v2 run must not be served from the v1 cell"
    assert "codex" in res and "aider" in res


def test_scan_org_failure_not_recorded_as_zero(monkeypatch):
    monkeypatch.setattr(scan_orgs, "rest_count", lambda q, **k: None)
    assert scan_orgs.scan_org("acme", None, MARKERS_V1, "v1") is None
    assert not cell_path("scan_orgs", "acme", "all-time", "v1").exists()


def test_enum_org_tallies_max_over_terms(monkeypatch):
    """claude has 2 search terms; a repo hit by both must count once (max),
    not twice (sum)."""
    monkeypatch.setattr(enum_repos, "_paginate_repos",
                        lambda q, **k: ["acme/big", "acme/big", "acme/small"])
    res = enum_repos.enum_org("acme", "2025-07-01..2026-06-30", MARKERS_V1, "v1")
    assert res["acme/big"] == {"claude": 2, "cursor": 2}     # max, not 4
    assert res["acme/small"] == {"claude": 1, "cursor": 1}
    p = cell_path("enum_repos", "acme", "2025-07-01..2026-06-30", "v1")
    assert json.loads(p.read_text()) == res


def test_enum_org_failure_writes_nothing(monkeypatch):
    monkeypatch.setattr(enum_repos, "_paginate_repos", lambda q, **k: None)
    assert enum_repos.enum_org("acme", "w", MARKERS_V1, "v1") is None
    assert not cell_path("enum_repos", "acme", "w", "v1").exists()


def test_enum_warns_on_search_cap(monkeypatch, capsys):
    """Review finding: 1000-cap saturation was silent."""
    monkeypatch.setattr(enum_repos, "_paginate_repos",
                        lambda q, **k: ["acme/huge"] * 1000)
    monkeypatch.setattr(enum_repos, "rest_count", lambda q, **k: 4321)
    enum_repos.enum_org("acme", "w", MARKERS_V1, "v1")
    assert "search cap hit" in capsys.readouterr().err


# ------------------------------------------------------------- keep rule

def test_keep_rule_absolute_branch(monkeypatch):
    assert enum_repos.keep_reason("o/r", 5, "w", 5) == "abs"


def test_keep_rule_rate_branch(monkeypatch):
    """Review finding: the >=0.1%-of-PRs OR-branch was documented but never
    implemented. 3 AI commits / 200 PRs = 1.5% -> keep."""
    monkeypatch.setattr(enum_repos, "rest_count", lambda q, **k: 200)
    assert enum_repos.keep_reason("o/r", 3, "w", 5) == "rate"


def test_keep_rule_rejects_below_both(monkeypatch):
    monkeypatch.setattr(enum_repos, "rest_count", lambda q, **k: 10000)
    assert enum_repos.keep_reason("o/r", 3, "w", 5) is None      # 0.03% < 0.1%
    assert enum_repos.keep_reason("o/r", 0, "w", 5) is None      # no evidence
