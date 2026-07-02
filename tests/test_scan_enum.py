"""Checkpoint semantics for the scan and enum stages: failed pulls must never
be recorded as zeros (absence of evidence != evidence of absence)."""
import json

import pytest

from pipeline import enum_repos, scan_orgs
from pipeline.ghx import MARKERS_V1, cell_path


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
    assert scan_orgs.scan_org("acme", "Q1-2026", MARKERS_V1) == {"claude": 7, "cursor": 7}
    assert scan_orgs.scan_org("acme", "Q1-2026", MARKERS_V1) == {"claude": 7, "cursor": 7}
    assert len(calls) == len(MARKERS_V1)          # second call fully cached
    # bare-term + date qualifier, never author-email:
    assert calls[0] == "org:acme noreply@anthropic.com author-date:2026-01-01..2026-03-31"
    assert "author-email" not in calls[0]


def test_scan_org_failure_not_recorded_as_zero(monkeypatch):
    monkeypatch.setattr(scan_orgs, "rest_count", lambda q, **k: None)
    assert scan_orgs.scan_org("acme", None, MARKERS_V1) is None
    assert not cell_path("scan_orgs", "acme", "all-time").exists()


def test_enum_org_tallies_by_repo(monkeypatch):
    monkeypatch.setattr(enum_repos, "_paginate_repos",
                        lambda q, **k: ["acme/big", "acme/big", "acme/small"])
    res = enum_repos.enum_org("acme", "2025-07-01..2026-06-30", MARKERS_V1)
    assert res["acme/big"] == {"claude": 2, "cursor": 2}
    assert res["acme/small"] == {"claude": 1, "cursor": 1}
    # checkpoint round-trips through JSON
    p = cell_path("enum_repos", "acme", "2025-07-01..2026-06-30")
    assert json.loads(p.read_text()) == res


def test_enum_org_failure_writes_nothing(monkeypatch):
    monkeypatch.setattr(enum_repos, "_paginate_repos", lambda q, **k: None)
    assert enum_repos.enum_org("acme", "w", MARKERS_V1) is None
    assert not cell_path("enum_repos", "acme", "w").exists()
