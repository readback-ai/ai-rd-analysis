"""Stage-0 org-set rules and the layer-C collection helpers
(branch_scan checkpointing, pull_prs sampling weights contract)."""
import json

import pytest

from pipeline import branch_scan, pull_prs
from pipeline.detect import BRANCH_PREFIXES


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(branch_scan.time, "sleep", lambda s: None)
    monkeypatch.setattr(pull_prs.time, "sleep", lambda s: None)
    return tmp_path


# ------------------------------------------------------------- branch_scan

def test_branch_scan_checkpoints_and_skips_done(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(branch_scan, "rest_count",
                        lambda q, endpoint: calls.append(q) or 7)
    out = tmp_path / "scan.tsv"
    periods = {"Q2-2026": "2026-04-01..2026-06-30"}
    branch_scan.scan(["acme"], out, periods, {"codex": "codex/"})
    branch_scan.scan(["acme"], out, periods, {"codex": "codex/"})
    assert len(calls) == 1                      # second run fully cached
    assert branch_scan.load(out) == {("acme", "Q2-2026", "codex/"): 7}


def test_branch_scan_failed_count_never_written_as_zero(tmp_path, monkeypatch):
    monkeypatch.setattr(branch_scan, "rest_count", lambda q, endpoint: None)
    out = tmp_path / "scan.tsv"
    branch_scan.scan(["acme"], out, {"Q2-2026": "2026-04-01..2026-06-30"},
                     {"codex": "codex/"})
    assert branch_scan.load(out) == {}          # skipped, not zero


def test_all_detect_prefixes_are_scanned(tmp_path, monkeypatch):
    seen = []
    monkeypatch.setattr(branch_scan, "rest_count",
                        lambda q, endpoint: seen.append(q) or 0)
    out = tmp_path / "scan.tsv"
    branch_scan.scan(["acme"], out, {"Q2-2026": "2026-04-01..2026-06-30"},
                     BRANCH_PREFIXES)
    for prefix in BRANCH_PREFIXES.values():
        assert any(f"head:{prefix}" in q for q in seen)


# ---------------------------------------------------------------- pull_prs

def test_batch_pull_returns_only_hydrated_prs(monkeypatch):
    def fake_graphql(query, variables, jq, expect):
        return {"a0": {"pullRequest": {"number": 5}}, "a1": {"pullRequest": None}}
    monkeypatch.setattr(pull_prs, "graphql_nodes", fake_graphql)
    got = pull_prs.batch_pull([("o/r", 5), ("o/r", 6)])
    assert got == {("o/r", 5): {"number": 5}}   # missing PR absent, not faked


def test_sample_branch_prs_checkpoints_cells(tmp_path, monkeypatch):
    scan = tmp_path / "scan.tsv"
    scan.write_text("acme\tQ2-2026\tcodex/\t12\nacme\tQ1-2024\tcodex/\t3\n")
    calls = []
    monkeypatch.setattr(pull_prs, "graphql_nodes",
                        lambda *a, **k: calls.append(1) or [{"number": 1}])
    out = tmp_path / "codex_prs"
    pull_prs.sample_branch_prs("codex/", scan, out, ["Q2-2026"])
    pull_prs.sample_branch_prs("codex/", scan, out, ["Q2-2026"])
    assert len(calls) == 1                      # cached; Q1-2024 filtered out
    cells = pull_prs.load_branch_samples(out)
    assert cells == [{"org": "acme", "period": "Q2-2026", "pop_count": 12,
                      "prs": [{"number": 1}]}]  # pop_count kept for weighting


def test_sample_cells_carry_population_weight(tmp_path, monkeypatch):
    """Estimator contract: every cell must carry pop_count so org-weighted
    metrics can be computed without re-reading the scan."""
    scan = tmp_path / "scan.tsv"
    scan.write_text("acme\tQ2-2026\tcursor/\t999\n")
    monkeypatch.setattr(pull_prs, "graphql_nodes", lambda *a, **k: [])
    out = tmp_path / "cursor_prs"
    pull_prs.sample_branch_prs("cursor/", scan, out, ["Q2-2026"])
    cell = json.loads(next(out.glob("*.json")).read_text())
    assert cell["pop_count"] == 999


# ------------------------------------------------------------- census query

def test_census_query_has_layer_c_and_accountability_fields():
    from pipeline.census import PR_QUERY
    assert "headRefName" in PR_QUERY
    assert "mergedBy" in PR_QUERY


def test_branch_scan_scoped_org_counts_only_in_scope_repos(
        tmp_path, monkeypatch):
    """Issue #8 (RED first): for a repo-scoped org, branch_scan must count
    per in-scope repo (summed), never org-wide — org-wide counts include
    out-of-scope, non-AI repos and feed R4 admission evidence."""
    queries = []
    monkeypatch.setattr(branch_scan, "rest_count",
                        lambda q, endpoint: queries.append(q) or 1)
    out = tmp_path / "scan.tsv"
    branch_scan.scan(["bigco"], out, {"Q2-2026": "2026-04-01..2026-06-30"},
                     {"codex": "codex/"},
                     scoped={"bigco": ["bigco/ai-a", "bigco/ai-b"]})
    assert not any("org:" in q for q in queries)
    assert branch_scan.load(out) == {("bigco", "Q2-2026", "codex/"): 2}


def test_branch_scan_scoped_org_fails_cell_on_any_repo_failure(
        tmp_path, monkeypatch):
    """Issue #8: a partial per-repo sum understates silently — if any
    in-scope repo's count fails, the whole cell is skipped, not written."""
    monkeypatch.setattr(
        branch_scan, "rest_count",
        lambda q, endpoint: None if "ai-b" in q else 3)
    out = tmp_path / "scan.tsv"
    branch_scan.scan(["bigco"], out, {"Q2-2026": "2026-04-01..2026-06-30"},
                     {"codex": "codex/"},
                     scoped={"bigco": ["bigco/ai-a", "bigco/ai-b"]})
    assert branch_scan.load(out) == {}


def test_sample_branch_prs_filters_out_of_scope_repos(
        tmp_path, monkeypatch):
    """Issue #8 (RED first): layer-C sample cells for a repo-scoped org
    must not carry PRs from out-of-scope repos — they'd enter the
    precision estimates under the org's population weight."""
    scan = tmp_path / "scan.tsv"
    scan.write_text("bigco\tQ2-2026\tcodex/\t5\n")
    def node(repo):
        return {"number": 1, "headRefName": "codex/x",
                "repository": {"nameWithOwner": repo}}
    monkeypatch.setattr(
        pull_prs, "graphql_nodes",
        lambda *a, **k: [node("bigco/ai-a"), node("bigco/legacy")])
    out = tmp_path / "cells"
    pull_prs.sample_branch_prs("codex/", scan, out, ["Q2-2026"],
                               in_scope={"bigco": {"bigco/ai-a"}})
    cells = pull_prs.load_branch_samples(out)
    repos = [p["repository"]["nameWithOwner"]
             for c in cells for p in c["prs"]]
    assert repos == ["bigco/ai-a"]
    assert cells[0]["pop_count"] == 5


def test_layer_c_precision_filters_scoped_org_samples(
        tmp_path, monkeypatch, capsys):
    """Issue #8 (RED first): existing sample cells were drawn org-wide,
    so the precision study must drop a repo-scoped org's out-of-scope
    PRs at read time — they are outside the study universe (R5)."""
    from pipeline.studies import layer_c_precision as lcp

    def commit(email):
        return {"commit": {"committer": {"email": email}}}
    cell_dir = tmp_path / "raw" / "branch_samples" / "codex"
    cell_dir.mkdir(parents=True)
    (cell_dir / "bigco__Q2-2026.json").write_text(json.dumps({
        "org": "bigco", "period": "Q2-2026", "pop_count": 2, "prs": [
            {"headRefName": "codex/in-scope",
             "repository": {"nameWithOwner": "bigco/ai-a"},
             "commits": {"nodes": [commit("noreply@github.com")]}},
            {"headRefName": "codex/out-of-scope",
             "repository": {"nameWithOwner": "bigco/legacy"},
             "commits": {"nodes": [commit("human@example.com")]}},
        ]}))
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(lcp, "scoped_repos",
                        lambda: {"bigco": ["bigco/ai-a"]})
    lcp.main()
    row = [ln for ln in capsys.readouterr().out.splitlines()
           if ln.startswith("codex")][0]
    assert row.split()[1] == "1"          # the out-of-scope PR is gone
    assert row.split()[2] == "100.0%"     # web-flow share over in-scope only
