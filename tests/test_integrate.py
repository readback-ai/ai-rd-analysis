"""Layered-union math: branch-count merging, sample-weighted overlap stats,
and the disjointness contract (marker / agent-author / branch-only)."""
import json

import pytest

from pipeline import integrate


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    return tmp_path


def test_branch_counts_merges_both_tsv_formats(tmp_path):
    four = tmp_path / "branch_scan.tsv"
    four.write_text("acme\tQ2-2026\tclaude/\t10\n")
    three = tmp_path / "codex_branch_scan.tsv"
    three.write_text("acme\tQ2-2026\t7\n")
    counts = integrate.branch_counts(four, three)
    assert counts == {("acme", "Q2-2026", "claude/"): 10,
                      ("acme", "Q2-2026", "codex/"): 7}


def test_branch_counts_four_col_wins_over_legacy(tmp_path):
    """If the same codex cell exists in both files, the explicit 4-col row is
    authoritative (setdefault on the legacy format)."""
    four = tmp_path / "a.tsv"
    four.write_text("acme\tQ2-2026\tcodex/\t99\n")
    three = tmp_path / "b.tsv"
    three.write_text("acme\tQ2-2026\t7\n")
    assert integrate.branch_counts(four, three)[("acme", "Q2-2026", "codex/")] == 99


def test_missing_scan_files_are_tolerated(tmp_path):
    assert integrate.branch_counts(tmp_path / "nope.tsv") == {}


def _cell(tmp_path, name, pop, prs):
    d = tmp_path / "samples"
    d.mkdir(exist_ok=True)
    (d / f"{name}.json").write_text(json.dumps(
        {"org": name.split("__")[0], "period": "Q2-2026",
         "pop_count": pop, "prs": prs}))
    return d


def _pr(marker=False, bot_author=False, merged=True):
    pr = {"author": {"login": "copilot-swe-agent[bot]", "__typename": "Bot"}
          if bot_author else {"login": "alice", "__typename": "User"},
          "mergedAt": "2026-05-01T00:00:00Z" if merged else None,
          "reviews": {"nodes": []},
          "commits": {"nodes": [{"commit": {
              "message": "x\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
                         if marker else "x",
              "authors": {"nodes": []}}}]}}
    return pr


def test_sample_stats_weighted_by_population_count(tmp_path):
    """org A (pop 90): all marker-overlap; org B (pop 10): none.
    Weighted overlap must be 0.9, not the unweighted 0.5."""
    d = _cell(tmp_path, "a__Q2-2026", 90, [_pr(marker=True)])
    _cell(tmp_path, "b__Q2-2026", 10, [_pr(marker=False)])
    stats = integrate.sample_stats(d)
    assert stats["Q2-2026"]["marker_overlap"] == pytest.approx(0.9)


def test_sample_stats_measures_bot_author_overlap(tmp_path):
    d = _cell(tmp_path, "a__Q2-2026", 50, [_pr(bot_author=True), _pr()])
    stats = integrate.sample_stats(d)
    assert stats["Q2-2026"]["bot_author"] == pytest.approx(0.5)


def test_layer_disjointness_agent_author_wins_over_marker(tmp_path, monkeypatch):
    """A bot-authored PR whose commits also carry markers must count ONCE
    (as layer B), or the union double-counts."""
    from pipeline import analyze
    pr = _pr(marker=True, bot_author=True)
    pr["number"] = 1
    monkeypatch.setattr(analyze, "load_cells", lambda: {})
    monkeypatch.setattr(integrate, "load_cells",
                        lambda: {("o/r", "2026-04-01..2026-06-30"): [pr]})
    layers = integrate.census_layers()
    assert layers["Q2-2026"] == {"marker": 0.0, "agent": 1.0}
