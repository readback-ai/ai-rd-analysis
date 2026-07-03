"""Core invariants: cell storage round-trips, response validation, AI markers."""
import json

import pytest

from pipeline import ghx
from pipeline.ghx import (MARKERS_V1, MARKERS_V2, cell_path, cell_valid,
                          decode_cell_stem, pr_ai_tools, read_cell)


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


# --------------------------------------------------------------- AI markers

def _pr(messages=(), emails=(), author=None):
    return {
        "author": {"login": author, "__typename": "Bot"} if author else None,
        "commits": {"nodes": [
            {"commit": {"message": m,
                        "authors": {"nodes": [{"email": e} for e in emails]}}}
            for m in messages or [""]
        ]},
    }


def test_detects_claude_coauthor_email():
    pr = _pr(messages=["fix bug"], emails=["dev@x.com", "noreply@anthropic.com"])
    assert pr_ai_tools(pr) == {"claude"}


def test_detects_claude_footer_without_email():
    """Squash-merge often keeps the footer even when trailers are stripped."""
    pr = _pr(messages=["feat: x\n\n🤖 Generated with [Claude Code](https://...)"])
    assert pr_ai_tools(pr) == {"claude"}


def test_detects_cursor_trailer():
    pr = _pr(messages=["Update\n\nCo-authored-by: Cursor <cursoragent@cursor.com>"])
    assert pr_ai_tools(pr) == {"cursor"}


def test_v1_ignores_aider_and_codex_but_v2_detects():
    pr = _pr(messages=["x\n\nCo-authored-by: aider <aider@aider.chat>"],
             emails=["codex@openai.com"])
    assert pr_ai_tools(pr, MARKERS_V1) == set()
    assert pr_ai_tools(pr, MARKERS_V2) == {"aider", "codex"}


def test_v2_detects_codex_cloud_via_committer():
    """Review finding: Codex cloud only appears as the COMMITTER; the old
    query/classifier never saw it."""
    pr = _pr(messages=["normal"])
    pr["commits"]["nodes"][0]["commit"]["committer"] = {
        "email": "", "user": {"login": "chatgpt-codex-connector"}}
    assert pr_ai_tools(pr, MARKERS_V2) == {"codex"}
    assert pr_ai_tools(pr, MARKERS_V1) == set()


def test_marker_specs_have_search_terms_and_needles():
    for spec in MARKERS_V2.values():
        assert spec.search_terms and spec.needles


def test_plain_pr_detects_nothing():
    assert pr_ai_tools(_pr(messages=["normal commit"], emails=["h@x.com"])) == set()


def test_bot_authored_pr_flagged_only_when_enabled():
    pr = _pr(messages=["done"], author="copilot-swe-agent[bot]")
    assert pr_ai_tools(pr) == set()
    assert pr_ai_tools(pr, include_bot_authors=True) == {"agent:copilot-swe-agent"}


def test_empty_commits_do_not_crash():
    assert pr_ai_tools({"commits": None}) == set()
    assert pr_ai_tools({}) == set()
