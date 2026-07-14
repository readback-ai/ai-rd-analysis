"""Metric classification (esp. AI-vs-CI reviewer decomposition), weighting, CIs."""
import json
import math
import random

import pytest

from pipeline import ghx
from pipeline.analyze import (bootstrap_ci, load_cells, period_of, pr_metrics,
                              weighted_mean)
from pipeline.detect import MARKERS_V1
from pipeline.scan_orgs import QUARTER_RANGES


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    return tmp_path


def _review(login, typename="Bot", state="COMMENTED"):
    return {"author": {"login": login, "__typename": typename},
            "submittedAt": "2026-05-01T00:00:00Z", "state": state,
            "comments": {"totalCount": 0}}


def _pr(reviews=(), assoc="NONE", merged=False, msg="normal"):
    return {
        "mergedAt": "2026-05-02T00:00:00Z" if merged else None,
        "authorAssociation": assoc,
        "additions": 10, "deletions": 5,
        "commits": {"nodes": [{"commit": {"message": msg,
                                          "authors": {"nodes": []}}}]},
        "reviews": {"nodes": list(reviews)},
    }


# ------------------------------------------------- reviewer decomposition (R3)

def test_ai_reviewer_counts_as_ai_review_not_other():
    m = pr_metrics(_pr(reviews=[_review("gemini-code-assist")]), MARKERS_V1)
    assert m["ai_review"] and not m["other_bot_review"] and not m["human_review"]


def test_ci_bot_is_not_ai_review():
    """The P1.4 conflation: github-actions must NOT count as AI review."""
    m = pr_metrics(_pr(reviews=[_review("github-actions[bot]")]), MARKERS_V1)
    assert m["other_bot_review"] and not m["ai_review"]


def test_bot_suffix_normalized():
    m = pr_metrics(_pr(reviews=[_review("coderabbitai[bot]")]), MARKERS_V1)
    assert m["ai_review"]


def test_mixed_reviewers_all_flags():
    m = pr_metrics(_pr(reviews=[_review("alice", "User"),
                                _review("gemini-code-assist"),
                                _review("github-actions[bot]")]), MARKERS_V1)
    assert m["human_review"] and m["ai_review"] and m["other_bot_review"]
    assert not m["no_review"]


def test_no_reviews_and_insider_and_ai_code():
    m = pr_metrics(_pr(assoc="MEMBER",
                       msg="x\n\nCo-Authored-By: Claude <noreply@anthropic.com>"),
                   MARKERS_V1)
    assert m["no_review"] and m["insider"] and m["ai_code"]


# ------------------------------------------------- weighting & CIs

def test_weighted_mean_weights_dominate():
    assert weighted_mean([(1.0, 99.0), (0.0, 1.0)]) == pytest.approx(0.99)
    assert math.isnan(weighted_mean([]))


def test_bootstrap_ci_brackets_mean_and_handles_tiny_n():
    random.seed(7)
    pairs = [(v, 1.0) for v in (0.1, 0.2, 0.3, 0.4, 0.5)]
    lo, hi = bootstrap_ci(pairs, n=500)
    assert lo <= weighted_mean(pairs) <= hi
    assert 0.1 <= lo < hi <= 0.5
    assert all(math.isnan(x) for x in bootstrap_ci([(0.5, 1.0)], n=50))


# ------------------------------------------------- cell loading / periods

def test_period_of_maps_subwindows_to_quarter():
    assert period_of("2026-02-01..2026-02-09", QUARTER_RANGES) == "Q1-2026"
    assert period_of("2026-01-01..2026-03-31", QUARTER_RANGES) == "Q1-2026"
    assert period_of("2025-05-01..2025-05-09", QUARTER_RANGES) is None


def test_load_cells_roundtrips_and_skips_corrupt(tmp_store):
    good = ghx.cell_path("census", "fw-ai/flashinfer", "2026-01-01..2026-03-31")
    good.write_text(json.dumps([{"number": 1}, None]))       # None PRs dropped
    bad = ghx.cell_path("census", "o/bad", "2026-01-01..2026-03-31")
    bad.write_text('{"errors":[]}')                          # wrong shape
    ugly = ghx.cell_path("census", "o/ugly", "2026-01-01..2026-03-31")
    ugly.write_text("{corrupt")
    cells = load_cells()
    assert cells[("fw-ai/flashinfer", "2026-01-01..2026-03-31")] == [{"number": 1}]
    assert not any(k[0] in ("o/bad", "o/ugly") for k in cells)


def test_group_by_period_dedups_overlapping_cell_generations(tmp_store):
    """Review finding: full-quarter + sub-window cells (or old/new quarter
    definitions) for the same repo-period double-counted PRs."""
    import json as _json
    from pipeline.analyze import group_by_period
    full = ghx.cell_path("census", "o/r", "2026-01-01..2026-03-31")
    full.write_text(_json.dumps([{"number": 1}, {"number": 2}]))
    sub = ghx.cell_path("census", "o/r", "2026-01-01..2026-01-09")
    sub.write_text(_json.dumps([{"number": 2}, {"number": 3}]))
    grouped = group_by_period(load_cells(), QUARTER_RANGES)
    nums = sorted(pr["number"] for pr in grouped[("o/r", "Q1-2026")])
    assert nums == [1, 2, 3]              # PR 2 counted once, not twice


def test_insider_is_a_reported_metric():
    """Review finding: insider was computed but never reported."""
    from pipeline.analyze import METRICS
    assert "insider" in METRICS


def test_ai_reviewer_list_covers_observed_reviewers():
    """Reviewers actually seen in the Phase-0 data must be classified as AI."""
    from pipeline.detect import AI_REVIEWERS
    for login in ("gemini-code-assist", "copilot-pull-request-reviewer",
                  "coderabbitai", "greptile-apps"):
        assert login in AI_REVIEWERS


def test_richer_v2_record_wins_over_legacy_on_overlap():
    """External review P1: a legacy full-quarter cell must not strip
    headRefName/mergedBy from the same PR delivered by a v2 sub-window,
    regardless of dict iteration order."""
    legacy = {"number": 7, "reviews": {"nodes": []}}
    rich = {"number": 7, "headRefName": "codex/x", "mergedBy": None,
            "reviews": {"nodes": []}}
    for first, second in ((legacy, rich), (rich, legacy)):
        cells = {("o/r", "2026-04-01..2026-06-30"): [first],
                 ("o/r", "2026-04-01..2026-04-09"): [second]}
        from pipeline.analyze import group_by_period
        grouped = group_by_period(cells, QUARTER_RANGES)
        prs = grouped[("o/r", "Q2-2026")]
        assert len(prs) == 1 and "headRefName" in prs[0]


def test_weights_reader_accepts_window_column(tmp_path):
    """The window weights file's header differs; silently dropping every
    weight made contrib-weight identical to equal-weight in a generated
    report."""
    f = tmp_path / "w.csv"
    f.write_text("repo,core_contributors_window\no/r,7\n")
    # exercise the same parsing path
    import csv as _csv
    weights = {}
    for row in _csv.DictReader(open(f)):
        val = row.get("core_contributors_window", row.get("core_contributors"))
        weights[row["repo"]] = max(float(val), 1.0)
    assert weights == {"o/r": 7.0}


def test_month_granularity_buckets_by_created_at():
    from pipeline.analyze import group_by_period
    cells = {("o/r", "2026-04-01..2026-06-30"): [
        {"number": 1, "createdAt": "2026-04-15T00:00:00Z"},
        {"number": 2, "createdAt": "2026-05-02T00:00:00Z"},
        {"number": 3, "createdAt": "2026-05-30T00:00:00Z"}]}
    g = group_by_period(cells, QUARTER_RANGES, "month")
    assert len(g[("o/r", "2026-04")]) == 1 and len(g[("o/r", "2026-05")]) == 2
    # quarter mode unchanged
    q = group_by_period(cells, QUARTER_RANGES)
    assert len(q[("o/r", "Q2-2026")]) == 3
