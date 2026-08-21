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


def test_exposure_truncated_at_the_period_end(monkeypatch):
    """A PR merged near the period's end carries only the risk days that
    fall inside it — partial exposure, not a whole window."""
    _exposure_fixture(monkeypatch, [("2024-03-25", 1.0)], [])
    rows, _meta = churn.exposure_rows("quarter")
    # 2024-03-25..2024-03-31 inclusive = 7 of RISK_DAYS days
    assert rows[0]["pr_windows"] == 7 / RISK_DAYS
