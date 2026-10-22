"""Core invariants: cell storage round-trips, response validation, AI markers."""
import json

import pytest

from pipeline import ghx
from pipeline.ghx import (cell_path, cell_valid, decode_cell_stem, read_cell)


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    ghx._budget.update({"remaining": None, "used_since": 0})   # isolate budget cache
    return tmp_path


# --------------------------------------------------------------- storage

def test_cell_path_roundtrips_repo_slash(tmp_store):
    p = cell_path("census", "fw-ai/flashinfer", "2026-01-01..2026-03-31")
    assert p.name == "fw-ai~flashinfer@2026-01-01..2026-03-31.json"
    assert str(tmp_store) in str(p)
    # '~' encoding must be reversible and unambiguous vs org names
    repo_part, _, rng = p.stem.partition("@")
    assert repo_part.replace("~", "/") == "fw-ai/flashinfer"
    assert rng == "2026-01-01..2026-03-31"


def test_cell_valid_rejects_rate_limit_error_objects(tmp_store):
    """The bug that corrupted 267 census cells: an error OBJECT written where
    an ARRAY was expected must not count as a completed cell."""
    p = cell_path("census", "o/r", "w")
    p.write_text(json.dumps({"errors": [{"type": "RATE_LIMIT"}]}))
    assert not cell_valid(p, list)
    p.write_text("[]")
    assert cell_valid(p, list)


@pytest.mark.parametrize("content", ["", "[", "null", "12"])
def test_cell_valid_rejects_garbage(tmp_store, content):
    p = cell_path("census", "o/r", "w")
    p.write_text(content)
    assert not cell_valid(p, list)


def test_cell_valid_missing_file(tmp_store):
    assert not cell_valid(cell_path("census", "o/r", "nope"), list)


def test_read_cell_parses_once_and_decode_roundtrips(tmp_store):
    p = cell_path("census", "fw-ai/flashinfer", "2026-01-01..2026-03-31")
    p.write_text('[{"number": 5}]')
    assert read_cell(p, list) == [{"number": 5}]
    assert read_cell(p, dict) is None
    assert decode_cell_stem(p.stem) == ["fw-ai/flashinfer", "2026-01-01..2026-03-31"]


def test_budget_wait_caches_rate_limit_polls(monkeypatch):
    """Review finding: a full rate_limit REST call ran before EVERY query."""
    polls = []
    monkeypatch.setattr(ghx, "_gh", lambda *a, **k: polls.append(1) or "4000\t9999999999")
    for _ in range(10):
        ghx.graphql_budget_wait(min_remaining=200)
    assert len(polls) == 1                # 9 subsequent calls served from cache


# --------------------------------------------------------------- gh wrappers

def test_rest_count_retries_then_gives_up_as_none(monkeypatch):
    calls = []
    monkeypatch.setattr(ghx, "_gh", lambda *a, **k: calls.append(1) or None)
    monkeypatch.setattr(ghx.time, "sleep", lambda s: None)
    assert ghx.rest_count("org:x y", retries=3) is None
    assert len(calls) == 3


def test_rest_count_parses_count(monkeypatch):
    monkeypatch.setattr(ghx, "_gh", lambda *a, **k: "42\n")
    assert ghx.rest_count("q") == 42


def test_graphql_nodes_never_returns_wrong_shape(monkeypatch):
    """A rate-limit error body (dict) must never be returned where a list is
    expected — the caller would write it as a cell."""
    monkeypatch.setattr(ghx, "graphql_budget_wait", lambda **k: None)
    monkeypatch.setattr(ghx.time, "sleep", lambda s: None)
    monkeypatch.setattr(ghx, "_gh",
                        lambda *a, **k: '{"errors":[{"type":"RATE_LIMIT"}]}')
    assert ghx.graphql_nodes("q", {}, ".data", expect=list, retries=2) is None


def test_graphql_nodes_returns_valid_list(monkeypatch):
    monkeypatch.setattr(ghx, "graphql_budget_wait", lambda **k: None)
    monkeypatch.setattr(ghx, "_gh", lambda *a, **k: '[{"number": 1}]')
    assert ghx.graphql_nodes("q", {}, ".data", expect=list) == [{"number": 1}]


def test_graphql_tolerates_node_level_errors_with_complete_data(monkeypatch):
    """PRs referencing deleted (ghost) accounts make gh exit nonzero while
    stdout still holds complete extracted data; shape validation accepts it.
    Twelve repo-periods failed deterministically on this."""

    def fake_run(cmd, **kw):
        class R:
            returncode = 1
            # gh does NOT apply --jq on nonzero exit: raw envelope on stdout
            stdout = ('{"data": {"search": {"nodes": [{"number": 1}], '
                      '"pageInfo": {"hasNextPage": false}}}, '
                      '"errors": [{"type": "NOT_FOUND"}]}')
            stderr = "gh: Not Found\n"
        return R()
    monkeypatch.setattr(ghx.subprocess, "run", fake_run)
    monkeypatch.setattr(ghx, "graphql_budget_wait", lambda **k: None)
    out = ghx.graphql_nodes("q", {}, ".data.search", expect=dict)
    assert out == {"nodes": [{"number": 1}], "pageInfo": {"hasNextPage": False}}


def test_graphql_nodes_logs_discarded_errors(monkeypatch, capsys):
    """Issue #3, final item: graphql_nodes tolerates a partial response
    but must not consume it SILENTLY — the errors array is printed so a
    pipeline-wide partial-response event is visible in every caller's
    log, not only the review-action batch path."""
    monkeypatch.setattr(ghx, "graphql_budget_wait", lambda **k: None)
    monkeypatch.setattr(
        ghx, "_gh",
        lambda *a, **k: '{"data": {"search": {"nodes": []}}, '
                        '"errors": [{"type": "RATE_LIMITED", '
                        '"path": ["search"]}]}')
    out = ghx.graphql_nodes("q", {}, ".data.search.nodes", expect=list)
    assert out == []
    log = capsys.readouterr().out
    assert "GRAPHQL ERRORS" in log
    assert "RATE_LIMITED" in log


def test_all_commits_rejects_page_without_pageinfo(monkeypatch):
    """PR #14 review, P1: a partial envelope (node served, totalCount
    claimed, pageInfo missing) must not return as a complete commit
    list — the record would checkpoint commits_complete: true and never
    be revisited. Pagination terminates only on hasNextPage is False,
    the rule _conn_commits, census._paginate, and enum_org follow."""
    from pipeline.studies import review_action as ra
    monkeypatch.setattr(ra, "graphql_nodes",
                        lambda *a, **k: {"nodes": [{"commit": {}}],
                                         "totalCount": 2})
    assert ra._all_commits("o/r", 1) is None


def test_rest_count_still_rejects_nonzero_exit(monkeypatch):
    """allow_partial is GraphQL-only; REST counts must not trust error runs."""
    def fake_run(cmd, **kw):
        class R:
            returncode = 1
            stdout = "12345"
            stderr = "boom"
        return R()
    monkeypatch.setattr(ghx.subprocess, "run", fake_run)
    monkeypatch.setattr(ghx.time, "sleep", lambda s: None)
    assert ghx.rest_count("q", retries=2) is None
