"""Per-PR risk-window bug rates (pipeline.studies.churn).

The dated bug artifact exists so a window choice is a computation, not a
re-pull; these pin the arithmetic that depends on it — exposure counted
per PR-day, issues deduped across deliberately overlapping cell windows,
and the burn-in that keeps exposure from being understated at a period's
start.
"""
from pipeline.studies import churn
from pipeline.studies.churn import (RISK_DAYS, _days, _split_range,
                                    bug_date_window, bug_days_by_repo)


def test_bug_date_window_extends_by_the_risk_window():
    """A period's dated pull must cover every risk window a PR merged on
    its last day opens, or that PR's exposure is unobservable."""
    rng = bug_date_window("Q1-2024", as_of="2026-08-01T00:00:00Z")
    assert rng == "2024-01-01..2024-04-28"    # 2024-03-31 + 28d


def test_bug_date_window_stops_at_what_the_freeze_can_observe():
    rng = bug_date_window("Q1-2024", as_of="2024-02-10T00:00:00Z")
    assert rng == "2024-01-01..2024-02-10"


def test_overlapping_windows_do_not_double_count_issues():
    """Adjacent periods' windows overlap by RISK_DAYS on purpose, so the
    same issue appears in two cells; it must be counted once."""
    rows = [{"repo": "o/r", "per": "2026-01", "rng": "x",
             "days": [[7, "2026-02-03"], [8, "2026-02-04"]]},
            {"repo": "o/r", "per": "2026-02", "rng": "y",
             "days": [[7, "2026-02-03"], [9, "2026-02-05"]]}]
    days = bug_days_by_repo(rows)
    assert days["o/r"] == {"2026-02-03": 1, "2026-02-04": 1,
                           "2026-02-05": 1}


def test_split_range_halves_an_overfull_window():
    """Search cannot page past 1000 results, so an over-full range is
    bisected rather than silently truncated."""
    parts = _split_range("2024-01-01..2024-01-11")
    assert parts == ["2024-01-01..2024-01-06", "2024-01-07..2024-01-11"]
    assert _split_range("2024-01-01..2024-01-01") == \
        ["2024-01-01..2024-01-01"]


def test_days_spans_both_endpoints():
    assert _days("2024-01-01..2024-01-03") == \
        ["2024-01-01", "2024-01-02", "2024-01-03"]


def _exposure_fixture(monkeypatch, merges, issue_days):
    monkeypatch.setattr(churn, "_verify", lambda *_a: (
        [{"repo": "o/r", "per": "Q1-2024", "rng": "r",
          "days": [[i, d] for i, d in enumerate(issue_days)]}],
        {"held": 1, "selected": 1, "as_of": churn.AS_OF}))
    monkeypatch.setattr(churn, "merged_exposure",
                        lambda g="quarter": ({("o/r", "Q1-2024"): merges},
                                             ["Q1-2024"]))


def test_one_pr_one_window_is_one_unit_of_exposure(monkeypatch):
    """A single PR merged after the burn-in carries RISK_DAYS of exposure
    inside the period = exactly one PR-risk-window, so one bug filed in
    its window reads as a rate of 1.0 per window."""
    _exposure_fixture(monkeypatch, [("2024-02-01", 2.0)], ["2024-02-10"])
    rows, _meta = churn.exposure_rows("quarter")
    assert len(rows) == 1
    assert rows[0]["pr_windows"] == 1.0
    assert rows[0]["kloc_windows"] == 2.0
    assert rows[0]["per_pr"] == 1.0
    assert rows[0]["per_kloc"] == 0.5


def test_burn_in_excludes_the_periods_first_risk_days(monkeypatch):
    """Days whose lookback reaches before the censused window are skipped:
    a bug filed inside the burn-in is not counted, because the merges that
    could explain it were never collected."""
    _exposure_fixture(monkeypatch, [("2024-02-01", 1.0)], ["2024-01-05"])
    rows, _meta = churn.exposure_rows("quarter")
    assert rows[0]["bugs"] == 0


def test_exposure_is_proportional_to_open_windows(monkeypatch):
    """Two PRs merged the same day carry twice the exposure of one, so the
    per-PR rate halves on the same bug count."""
    _exposure_fixture(monkeypatch,
                      [("2024-02-01", 1.0), ("2024-02-01", 3.0)],
                      ["2024-02-10"])
    rows, _meta = churn.exposure_rows("quarter")
    assert rows[0]["pr_windows"] == 2.0
    assert rows[0]["per_pr"] == 0.5
    assert rows[0]["kloc_windows"] == 4.0


def test_repos_outside_the_bug_pull_are_not_rated(monkeypatch):
    """Exposure exists for every censused repo, but only the pilot repos
    have a bug numerator — rating the rest would divide real exposure by
    an absent count and drag every rate toward zero."""
    monkeypatch.setattr(churn, "_verify", lambda *_a: (
        [{"repo": "o/pilot", "per": "Q1-2024", "rng": "r",
          "days": [[1, "2024-02-10"]]}],
        {"held": 1, "selected": 1, "as_of": churn.AS_OF}))
    monkeypatch.setattr(churn, "merged_exposure", lambda g="quarter": (
        {("o/pilot", "Q1-2024"): [("2024-02-01", 1.0)],
         ("o/never-pulled", "Q1-2024"): [("2024-02-01", 1.0)]},
        ["Q1-2024"]))
    rows, _meta = churn.exposure_rows("quarter")
    assert [r["repo"] for r in rows] == ["o/pilot"]


def test_label_users_drops_repos_with_no_labeled_issues_ever():
    """A repo with zero bug-labeled issues in every period is read as not
    using the label, not as defect-free."""
    rows = [{"repo": "o/uses", "bugs": 0}, {"repo": "o/uses", "bugs": 3},
            {"repo": "o/never", "bugs": 0}, {"repo": "o/never", "bugs": 0}]
    assert churn.label_users(rows) == {"o/uses"}


def test_unfrozen_cell_is_not_rated_as_zero_bugs(monkeypatch):
    """Review finding 1: a (repo, period) whose dated cell never froze
    (the pull gave up) has no numerator — rating it reads real exposure
    against zero issues and drags the period toward 0."""
    monkeypatch.setattr(churn, "_verify", lambda *_a: (
        [{"repo": "o/r", "per": "Q1-2024", "rng": "r",
          "days": [[1, "2024-02-10"]]}],
        {"held": 1, "selected": 2, "as_of": churn.AS_OF}))
    monkeypatch.setattr(churn, "merged_exposure", lambda g="quarter": (
        {("o/r", "Q1-2024"): [("2024-02-01", 1.0)],
         ("o/r", "Q4-2025"): [("2025-11-01", 1.0)]},
        ["Q1-2024", "Q4-2025"]))
    rows, _meta = churn.exposure_rows("quarter")
    assert [r["per"] for r in rows] == ["Q1-2024"]


def test_burn_in_starts_the_first_day_with_a_full_lookback(monkeypatch):
    """Review finding 8: day RISK_DAYS-1 of a period looks back over
    exactly RISK_DAYS censused days, so it is rated, not burnt in."""
    _exposure_fixture(monkeypatch, [("2024-01-01", 1.0)], ["2024-01-28"])
    rows, _meta = churn.exposure_rows("quarter")
    assert rows[0]["bugs"] == 1


def test_lookback_crosses_into_a_contiguous_prior_period(monkeypatch):
    """Review finding 2: Q4-2025..Q2-2026 (and every finalized month) are
    contiguous, so a period's early days have a fully censused lookback
    into the period before it — they are rated, and the prior period's
    merges carry exposure into them. Burn-in belongs only at the start of
    a censused block."""
    monkeypatch.setattr(churn, "_verify", lambda *_a: (
        [{"repo": "o/r", "per": "Q4-2025", "rng": "r", "days": []},
         {"repo": "o/r", "per": "Q1-2026", "rng": "r",
          "days": [[1, "2026-01-05"]]}],
        {"held": 2, "selected": 2, "as_of": churn.AS_OF}))
    monkeypatch.setattr(churn, "merged_exposure", lambda g="quarter": (
        {("o/r", "Q4-2025"): [("2025-12-20", 1.0)],
         ("o/r", "Q1-2026"): []},
        ["Q4-2025", "Q1-2026"]))
    rows, _meta = churn.exposure_rows("quarter")
    q1 = next(r for r in rows if r["per"] == "Q1-2026")
    assert q1["bugs"] == 1
    # the Dec-20 merge is at risk through Jan-16: 16 days inside Q1-2026
    assert q1["pr_windows"] == 16 / RISK_DAYS


def test_deletion_only_merges_keep_the_per_pr_rate(monkeypatch):
    """Review finding 5: zero added lines makes per-kLOC undefined, not
    the whole row — the PR-window rate and the bugs stay reported."""
    _exposure_fixture(monkeypatch, [("2024-02-01", 0.0)], ["2024-02-10"])
    rows, _meta = churn.exposure_rows("quarter")
    assert rows[0]["per_pr"] == 1.0
    assert rows[0]["per_kloc"] is None


def test_short_page_does_not_freeze_a_truncated_cell(monkeypatch):
    """Review finding 3: a page that comes back short of the reported
    total (search timeout, incomplete_results) must not be frozen as the
    cell's issues — reconcile would reuse the understated count forever."""
    monkeypatch.setattr(churn, "rest_count", lambda *_a, **_k: 150)
    pages = iter([[[i, "2024-01-01"] for i in range(100)],
                  [[i, "2024-01-02"] for i in range(30)]])
    monkeypatch.setattr(churn, "_gh_search_page",
                        lambda _q, _p: next(pages))
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    assert churn.search_issue_days("o/r", "2024-01-01..2024-01-31") is None


def test_search_pages_in_a_stable_order(monkeypatch):
    """Review finding 3: without a creation-order sort GitHub pages by
    best-match score, which can shift between requests and skip an issue
    across a page boundary."""
    seen = []

    def fake_gh(args, **_k):
        seen.append(args)
        return "[]"
    monkeypatch.setattr(churn, "_gh", fake_gh)
    churn._gh_search_page("q", 1)
    assert any(a.startswith("sort=created") for a in seen[0])


def test_search_page_retries_a_transient_failure(monkeypatch):
    """Review finding 6: one failed request on one page threw away every
    page already fetched and marked the whole cell MISSING; rest_count
    retries with backoff, so must the page fetch."""
    calls = iter([None, "[[1, \"2024-01-01\"]]"])
    monkeypatch.setattr(churn, "_gh", lambda *_a, **_k: next(calls))
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    assert churn._gh_search_page("q", 1) == [[1, "2024-01-01"]]


def test_empty_cell_fetches_no_page(monkeypatch):
    """Review finding 6: a zero-count cell needs no page request."""
    monkeypatch.setattr(churn, "rest_count", lambda *_a, **_k: 0)

    def no_page(*_a):
        raise AssertionError("page fetched for an empty cell")
    monkeypatch.setattr(churn, "_gh_search_page", no_page)
    assert churn.search_issue_days("o/r", "2024-01-01..2024-01-31") == []


def test_print_exposure_reports_frame_drift(monkeypatch, capsys):
    """Review finding 4: the numerator is frozen while the denominator is
    read live, so the table must say when the live frame no longer
    matches the frozen selection, as the counted table does."""
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        [{"repo": "o/r", "per": "Q1-2024", "bugs": 1, "pr_windows": 1.0,
          "kloc_windows": 1.0, "per_pr": 1.0, "per_kloc": 1.0}],
        (["Q1-2024"], {"held": 1, "selected": 1, "as_of": churn.AS_OF,
                       "frame": "frozen-fp"})))
    churn.print_exposure("quarter", live_fp="moved-fp")
    assert "MOVED" in capsys.readouterr().out


def test_pull_bug_dates_reports_the_shortfall(monkeypatch, capsys):
    """Review finding 10: a partial pull must end by saying how many
    cells are still unpulled, as the counted pull does — the read side
    cannot tell a missing cell from a quiet one."""
    monkeypatch.setattr(churn, "bug_date_cells", lambda *_a, **_k: [
        {"repo": "o/r", "per": "Q1-2024", "rng": "r"}])
    monkeypatch.setattr(churn, "_load_jsonl", lambda _p: [])
    monkeypatch.setattr(churn, "bugs_fingerprint", lambda *_a: "fp")
    monkeypatch.setattr(churn, "_freeze", lambda *_a: None)
    monkeypatch.setattr(churn, "search_issue_days", lambda *_a: None)
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    churn.pull_bug_dates({}, {}, None)
    assert "1 cells still unpulled" in capsys.readouterr().out


def test_exposure_truncated_at_the_period_end(monkeypatch):
    """A PR merged near the period's end carries only the risk days that
    fall inside it — partial exposure, not a whole window."""
    _exposure_fixture(monkeypatch, [("2024-03-25", 1.0)], [])
    rows, _meta = churn.exposure_rows("quarter")
    # 2024-03-25..2024-03-31 inclusive = 7 of RISK_DAYS days
    assert rows[0]["pr_windows"] == 7 / RISK_DAYS
