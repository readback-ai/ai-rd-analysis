"""Direct (non-search) census route for repos GitHub's search index
refuses (HTTP 422 "cannot be searched"), found 2026-07-29 when 8
population repos with real PRs failed every search-based collection."""
import json

import pytest

from pipeline import census_direct, ghx
from pipeline.census_direct import MAX_PRS


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path))
    monkeypatch.setattr(census_direct.time, "sleep", lambda s: None)
    return tmp_path


def _pr(num, created, merged=None):
    return {"number": num, "createdAt": created, "mergedAt": merged,
            "closedAt": None, "authorAssociation": "MEMBER",
            "additions": 10, "deletions": 1, "changedFiles": 1,
            "headRefName": "topic", "author": {"login": "dev",
                                               "__typename": "User"},
            "mergedBy": None, "commits": {"nodes": []},
            "reviews": {"nodes": []}}


def _page(nodes, total, has_next=False, cursor=None):
    return {"totalCount": total,
            "pageInfo": {"hasNextPage": has_next, "endCursor": cursor},
            "nodes": nodes}


def test_unsearchable_repo_detected_from_the_422_signature(monkeypatch):
    """Three states: the 422 'cannot be searched' answer is a DEFINITIVE
    property of the repo; a clean search is definitively searchable; any
    other failure says nothing and is 'unknown'."""
    monkeypatch.setattr(
        census_direct, "search_error",
        lambda q: "Validation Failed: The listed users and repositories "
                  "cannot be searched either because the resources do "
                  "not exist or you do not have permission")
    assert census_direct.classify_searchability("o/r1") == "unsearchable"
    monkeypatch.setattr(census_direct, "search_error",
                        lambda q: "502 Bad Gateway")
    assert census_direct.classify_searchability("o/r2") == "unknown"
    monkeypatch.setattr(census_direct, "search_error", lambda q: None)
    assert census_direct.classify_searchability("o/r3") == "searchable"


def test_transient_classification_is_unknown_and_not_memoized(
        monkeypatch):
    """PR #20 re-review, P1: a probe that times out / 502s / rate-limits
    cannot tell us anything about the repo — the answer is 'unknown',
    and memoizing it as searchable would bless cached drift for the rest
    of the process. Transient answers re-probe; definitive answers
    memoize."""
    answers = iter(["502 Bad Gateway", "502 Bad Gateway", None, None])
    calls = []

    def flaky(q):
        calls.append(q)
        return next(answers)
    monkeypatch.setattr(census_direct, "search_error", flaky)
    assert census_direct.classify_searchability("o/t") == "unknown"
    assert census_direct.classify_searchability("o/t") == "unknown"
    assert len(calls) == 2                    # transient: re-probed
    assert census_direct.classify_searchability("o/t") == "searchable"
    assert census_direct.classify_searchability("o/t") == "searchable"
    assert len(calls) == 3                    # definitive: memoized


def test_unsearchability_is_probed_once_per_repo(monkeypatch):
    """Self-review: the census probes every cached cell that disagrees
    with its precount, and drift is the designed-for common case — the
    probe must cost at most one live search per repo per process."""
    calls = []
    monkeypatch.setattr(census_direct, "search_error",
                        lambda q: calls.append(q) or None)
    assert census_direct.classify_searchability("o/memo") == "searchable"
    assert census_direct.classify_searchability("o/memo") == "searchable"
    assert len(calls) == 1


def test_search_error_keeps_the_json_body_not_just_gh_stderr(monkeypatch):
    """Real gh behavior: the short line goes to stderr while the JSON
    body carrying the definitive reason goes to stdout. Dropping stdout
    made every unsearchable repo look merely 'Validation Failed', so the
    classifier read all 8 real cases as something other than
    unsearchable."""
    class R:
        returncode = 1
        stdout = ('{"message":"Validation Failed","errors":[{"message":'
                  '"The listed users and repositories cannot be searched '
                  'either because the resources do not exist or you do '
                  'not have permission to view them."}],"status":"422"}')
        stderr = "gh: Validation Failed (HTTP 422)\n"
    monkeypatch.setattr(ghx.subprocess, "run", lambda *a, **k: R())
    err = ghx.search_error("repo:o/r is:pr")
    assert "cannot be searched" in err
    monkeypatch.setattr(census_direct, "search_error", ghx.search_error)
    assert census_direct.classify_searchability("o/r") == "unsearchable"


def test_rate_limit_is_not_mistaken_for_unsearchable(monkeypatch):
    class R:
        returncode = 1
        stdout = '{"message":"API rate limit exceeded for user ID 1."}'
        stderr = "gh: API rate limit exceeded for user ID 1.\n"
    monkeypatch.setattr(ghx.subprocess, "run", lambda *a, **k: R())
    monkeypatch.setattr(census_direct, "search_error", ghx.search_error)
    assert census_direct.classify_searchability("o/r") == "unknown"


def test_pull_repo_prs_pages_until_explicit_false(monkeypatch):
    pages = [_page([_pr(1, "2026-01-05T00:00:00Z")], 2, True, "c1"),
             _page([_pr(2, "2026-02-05T00:00:00Z")], 2, False)]
    seen = []

    def fake(query, variables, jq, expect):
        seen.append(variables.get("cur"))
        return pages[len(seen) - 1]
    monkeypatch.setattr(census_direct, "graphql_nodes", fake)
    got = census_direct.pull_repo_prs("o/r")
    assert [p["number"] for p in got] == [1, 2]
    assert seen == [None, "c1"]


def test_pull_repo_prs_rejects_a_partial_page(monkeypatch):
    """Same rule as the search path: an absent/None hasNextPage is a
    PARTIAL response, never 'last page'. The page carries a usable cursor
    and a matching totalCount, so ONLY the pageInfo rule can reject it —
    otherwise this passes for the wrong reason."""
    calls = []
    monkeypatch.setattr(
        census_direct, "graphql_nodes",
        lambda *a, **k: calls.append(1) or {
            "totalCount": 1, "pageInfo": {"endCursor": "c1"},
            "nodes": [_pr(1, "2026-01-05T00:00:00Z")]})
    assert census_direct.pull_repo_prs("o/r") is None
    assert len(calls) == 1        # fails FAST, not by exhausting pages


def test_pull_repo_prs_fails_on_null_nodes(monkeypatch):
    """Self-review: graphql_nodes tolerates node-level errors, so a
    connection can carry null entries. A null is a MISSING PR — the
    history is incomplete and must fail, not crash the bucketing later
    or store a null in a cell."""
    monkeypatch.setattr(
        census_direct, "graphql_nodes",
        lambda *a, **k: _page([_pr(1, "2026-05-01T00:00:00Z"), None], 2))
    assert census_direct.pull_repo_prs("o/r") is None


def test_pull_repo_prs_requires_totalcount_agreement(monkeypatch):
    """The API's own totalCount is the completeness denominator here (no
    precount exists for an unsearchable repo): a short history fails."""
    monkeypatch.setattr(
        census_direct, "graphql_nodes",
        lambda *a, **k: _page([_pr(1, "2026-01-05T00:00:00Z")], 5, False))
    assert census_direct.pull_repo_prs("o/r") is None


def test_pull_repo_prs_refuses_oversized_histories(monkeypatch):
    """The fallback is for small unsearchable repos; a huge history must
    fail on the FIRST page (the totalCount is known immediately) rather
    than page through it."""
    calls = []
    monkeypatch.setattr(
        census_direct, "graphql_nodes",
        lambda *a, **k: calls.append(1) or _page(
            [], MAX_PRS + 1, True, "c"))
    assert census_direct.pull_repo_prs("o/r") is None
    assert len(calls) == 1


def test_pull_repo_prs_pagination_is_bounded(monkeypatch):
    """An API that answers hasNextPage:true forever (repeating cursor)
    must exhaust a PAGE BUDGET and fail, not loop indefinitely — the
    failure mode a partial-response mutation exposed."""
    calls = []
    monkeypatch.setattr(
        census_direct, "graphql_nodes",
        lambda *a, **k: calls.append(1) or _page(
            [_pr(len(calls), "2026-05-01T00:00:00Z")], MAX_PRS,
            True, "same-cursor"))
    assert census_direct.pull_repo_prs("o/r") is None
    assert len(calls) <= -(-MAX_PRS // census_direct.PAGE_SIZE) + 1


def test_census_repo_direct_buckets_into_quarter_cells(monkeypatch):
    """One verified history -> one cell per study quarter, keyed by the
    full quarter range so coverage sees gap-free coverage. Quarters with
    no PRs get a VERIFIED empty cell; PRs outside the study quarters are
    dropped."""
    hist = [_pr(1, "2024-02-01T00:00:00Z"),
            _pr(2, "2026-05-01T00:00:00Z"),
            _pr(3, "2026-06-01T00:00:00Z"),
            _pr(9, "2025-02-01T00:00:00Z")]      # outside study quarters
    monkeypatch.setattr(census_direct, "pull_repo_prs",
                        lambda repo: hist)
    written = census_direct.census_repo_direct("o/r")
    assert written == {"Q1-2024": 1, "Q4-2025": 0,
                       "Q1-2026": 0, "Q2-2026": 2}
    cell = ghx.cell_path("census-v2", "o/r", "2026-04-01..2026-06-30")
    assert [p["number"] for p in json.loads(cell.read_text())] == [2, 3]
    empty = ghx.cell_path("census-v2", "o/r", "2026-01-01..2026-03-31")
    assert json.loads(empty.read_text()) == []


def test_direct_history_replaces_a_poisoned_empty_cell(monkeypatch):
    """PR #20 review, P1: the verified direct history is AUTHORITATIVE —
    a pre-existing cell that disagrees (e.g. the [] a failed search run
    left behind) must be replaced, not preserved while the fresh count is
    reported as written. This lost 17 of the 364 recovered PRs."""
    cell = ghx.cell_path("census-v2", "o/r", "2026-04-01..2026-06-30")
    cell.parent.mkdir(parents=True, exist_ok=True)
    cell.write_text("[]")                      # poisoned empty
    monkeypatch.setattr(census_direct, "pull_repo_prs",
                        lambda repo: [_pr(1, "2026-05-01T00:00:00Z"),
                                      _pr(2, "2026-06-01T00:00:00Z")])
    written = census_direct.census_repo_direct("o/r")
    assert written["Q2-2026"] == 2
    assert [p["number"] for p in json.loads(cell.read_text())] == [1, 2]


def test_direct_history_leaves_an_agreeing_cell_untouched(monkeypatch):
    """No needless churn: a cell whose contents already match the
    verified history keeps its mtime."""
    cell = ghx.cell_path("census-v2", "o/r", "2026-04-01..2026-06-30")
    cell.parent.mkdir(parents=True, exist_ok=True)
    cell.write_text(json.dumps([_pr(1, "2026-05-01T00:00:00Z")]))
    before = cell.stat().st_mtime_ns
    monkeypatch.setattr(census_direct, "pull_repo_prs",
                        lambda repo: [_pr(1, "2026-05-01T00:00:00Z")])
    census_direct.census_repo_direct("o/r")
    assert cell.stat().st_mtime_ns == before


def test_census_repo_direct_writes_nothing_on_failure(monkeypatch):
    monkeypatch.setattr(census_direct, "pull_repo_prs", lambda repo: None)
    assert census_direct.census_repo_direct("o/r") is None
    store = ghx.cell_path("census-v2", "x", "y").parent
    assert not list(store.glob("o~r*.json"))


def test_cli_repos_exits_nonzero_on_unknown_classification(
        tmp_path, monkeypatch):
    """PR #20 re-review, P2: --repos advertises 'collect all listed' — a
    repo whose classification is transiently UNKNOWN was printed and then
    silently skipped with exit 0, so a timeout or rate limit could make a
    scripted collection pass while doing nothing."""
    lst = tmp_path / "repos.txt"
    lst.write_text("o/r\n")
    monkeypatch.setattr(census_direct, "classify_searchability",
                        lambda repo: "unknown")
    monkeypatch.setattr("sys.argv",
                        ["census_direct", "--repos", str(lst)])
    with pytest.raises(SystemExit) as exc:
        census_direct.main()
    assert exc.value.code           # nonzero / truthy


def test_cli_probe_reports_unknowns_without_failing(
        tmp_path, monkeypatch, capsys):
    """--probe is a report, not a collection: unknowns appear in the
    summary but do not fail the run."""
    lst = tmp_path / "repos.txt"
    lst.write_text("o/r\n")
    monkeypatch.setattr(census_direct, "classify_searchability",
                        lambda repo: "unknown")
    monkeypatch.setattr("sys.argv",
                        ["census_direct", "--probe", str(lst)])
    census_direct.main()
    assert "unclassifiable" in capsys.readouterr().out


def test_cells_carry_the_census_field_set(monkeypatch):
    """Shape parity: a direct cell must be indistinguishable to the frame
    from a search-collected one."""
    from pipeline.census import PR_QUERY
    monkeypatch.setattr(census_direct, "pull_repo_prs",
                        lambda repo: [_pr(1, "2026-05-01T00:00:00Z")])
    census_direct.census_repo_direct("o/r")
    cell = ghx.cell_path("census-v2", "o/r", "2026-04-01..2026-06-30")
    pr = json.loads(cell.read_text())[0]
    for field in ("number", "createdAt", "mergedAt", "closedAt",
                  "authorAssociation", "additions", "deletions",
                  "changedFiles", "headRefName", "author", "mergedBy",
                  "commits", "reviews"):
        assert field in pr, field
        assert field in PR_QUERY, f"{field} absent from the census query"
