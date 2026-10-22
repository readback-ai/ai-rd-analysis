"""Batch denominator precount: aliasing, caching, partial-response safety."""

import pytest

from pipeline import precount
from pipeline.precount import batch_counts, get_precount


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    return tmp_path


def test_batch_writes_cells_and_caches(monkeypatch):
    captured = {}
    def fake_gql(query, variables, jq, expect):
        captured["q"] = query
        return {"a0": {"issueCount": 12}, "a1": {"issueCount": 0}}
    monkeypatch.setattr(precount, "graphql_nodes", fake_gql)
    n = batch_counts([("o/a", "Q1-2026"), ("o/b", "Q1-2024")])
    assert n == 2
    assert 'repo:o/a is:pr created:2026-01-01..2026-03-31' in captured["q"]
    assert get_precount("o/a", "Q1-2026") == 12
    assert get_precount("o/b", "Q1-2024") == 0
    # second call: fully cached, no query issued
    monkeypatch.setattr(precount, "graphql_nodes",
                        lambda *a, **k: (_ for _ in ()).throw(AssertionError))
    assert batch_counts([("o/a", "Q1-2026"), ("o/b", "Q1-2024")]) == 0


def test_batch_partial_response_writes_only_valid(monkeypatch):
    monkeypatch.setattr(precount, "graphql_nodes",
                        lambda *a, **k: {"a0": {"issueCount": 5}, "a1": None})
    n = batch_counts([("o/a", "Q2-2026"), ("o/b", "Q2-2026")])
    assert n == 1
    assert get_precount("o/a", "Q2-2026") == 5
    assert get_precount("o/b", "Q2-2026") is None    # retried next run


def test_batch_failure_writes_nothing(monkeypatch):
    monkeypatch.setattr(precount, "graphql_nodes", lambda *a, **k: None)
    assert batch_counts([("o/a", "Q1-2026")]) == 0
    assert get_precount("o/a", "Q1-2026") is None
