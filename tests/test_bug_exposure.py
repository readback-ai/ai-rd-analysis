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


def test_dated_cells_cover_every_repo_with_eligible_prs(monkeypatch):
    """The dated pull surveys the population, not the pilot: every repo
    with an eligible merged PR in any period gets its cells, whether or
    not the seeded PR draw happened to land on it. The PR side is a
    census, so the bug side must be one too for the rate to describe the
    study rather than the largest repos."""
    monkeypatch.setattr(churn, "draw", lambda _pool: [
        {"repo": "o/big", "per": "Q1-2024", "num": 1}])
    pool = {"Q1-2024": [("o/big", 1, False, 1, 0),
                        ("o/small", 2, False, 1, 0)],
            "Q4-2025": [("o/other", 3, True, 1, 0)]}
    cells = churn.bug_date_cells(pool, ["Q1-2024", "Q4-2025"])
    assert {c["repo"] for c in cells} == {"o/big", "o/small", "o/other"}
    assert len(cells) == 6


def test_dated_fingerprint_names_the_selection_policy(monkeypatch):
    """PR #43 review: the dated artifact's fingerprint hashed only the
    frame, so a pilot-scoped freeze and a population-scoped one on the
    same frame were indistinguishable — the drift line said MATCHES
    before the population pull had run. The selection policy is part of
    the fingerprint; the frame alone is not enough."""
    pools = ({"Q1-2024": [("o/r", 1, False, 1, 0)]},
             {"Q1-2024": [("o/r", 1, False, 1, 0)]})
    dated = churn.dated_fingerprint(*pools)
    assert dated != churn.bugs_fingerprint(*pools)
    monkeypatch.setattr(churn, "DATED_SELECTION", "pilot-draw")
    assert churn.dated_fingerprint(*pools) != dated


def test_dated_freeze_is_stamped_with_the_selection_fingerprint(
        monkeypatch):
    seen = {}
    monkeypatch.setattr(churn, "bug_date_cells", lambda *_a, **_k: [
        {"repo": "o/r", "per": "Q1-2024", "rng": "r"}])
    monkeypatch.setattr(churn, "_load_jsonl", lambda _p: [])
    monkeypatch.setattr(churn, "_freeze",
                        lambda _p, _m, _r, fp, *_a: seen.update(fp=fp))
    monkeypatch.setattr(churn, "search_issue_days", lambda *_a: [])
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    churn.pull_bug_dates({}, {}, None)
    assert seen["fp"] == churn.dated_fingerprint({}, {})


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


def test_label_users_come_from_the_frozen_cells():
    """Second review, finding 2: label use is a property of the repo's
    frozen issues, not of the rated days — a repo whose only labeled
    issue fell in burn-in still uses the label, and its zero-bug rated
    rows are real observations."""
    cells = [{"repo": "o/burn", "per": "Q1-2024", "rng": "r",
              "days": [[1, "2024-01-05"]]},
             {"repo": "o/never", "per": "Q1-2024", "rng": "r", "days": []}]
    assert churn.label_users(cells) == {"o/burn"}


def test_burn_in_issue_keeps_the_repo_in_the_table(monkeypatch, capsys):
    """Second review, finding 2, end to end: a repo with a labeled issue
    in burn-in and exposure on rated days is rated (bugs 0), not dropped
    as a label non-user."""
    monkeypatch.setattr(churn, "_verify", lambda *_a: (
        [{"repo": "o/burn", "per": "Q1-2024", "rng": "r",
          "days": [[1, "2024-01-05"]]}],
        {"held": 1, "selected": 1, "as_of": churn.AS_OF}))
    monkeypatch.setattr(churn, "merged_exposure", lambda g="quarter": (
        {("o/burn", "Q1-2024"): [("2024-02-01", 1.0)]}, ["Q1-2024"]))
    churn.print_exposure("quarter")
    out = capsys.readouterr().out
    assert "0 repos with zero bug-labeled issues" in out
    assert any(ln.startswith("Q1-2024") and ln.split()[1] == "all"
               and ln.split()[2] == "1" for ln in out.splitlines())


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
    monkeypatch.setattr(churn, "_search_count", lambda *_a: 150)
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
        return '{"inc": false, "items": []}'
    monkeypatch.setattr(churn, "_gh", fake_gh)
    churn._gh_search_page("q", 1)
    assert any(a.startswith("sort=created") for a in seen[0])


def test_search_page_retries_a_transient_failure(monkeypatch):
    """Review finding 6: one failed request on one page threw away every
    page already fetched and marked the whole cell MISSING; rest_count
    retries with backoff, so must the page fetch."""
    calls = iter([None, '{"inc": false, "items": [[1, "2024-01-01"]]}'])
    monkeypatch.setattr(churn, "_gh", lambda *_a, **_k: next(calls))
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    assert churn._gh_search_page("q", 1) == [[1, "2024-01-01"]]


def test_incomplete_page_is_refused(monkeypatch):
    """Second review, finding 1: a search that times out returns a
    SUCCESSFUL response with partial matches and incomplete_results
    true; treating it as a page freezes an understated cell."""
    monkeypatch.setattr(churn, "_gh", lambda *_a, **_k:
                        '{"inc": true, "items": [[1, "2024-01-01"]]}')
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    assert churn._gh_search_page("q", 1) is None


def test_search_follows_a_renamed_repo(monkeypatch):
    """Population survey: 23 repos were unpullable because search refuses
    a repo's former name, while the census still knows them by it. A
    renamed repo keeps its issues and the API redirects the old name, so
    a refused count is retried under the resolved name — the cell stays
    keyed by the census name."""
    queries = []

    def count(q, *_a):
        queries.append(q)
        return None if "repo:old/name" in q else 1
    monkeypatch.setattr(churn, "_search_count", count)
    monkeypatch.setattr(churn, "_resolve_repo", lambda _r: "new/name")
    monkeypatch.setattr(churn, "_gh_search_page",
                        lambda _q, _p: [[1, "2024-01-01"]])
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    assert churn.search_issue_days("old/name", "2024-01-01..2024-01-31") \
        == [[1, "2024-01-01"]]
    assert any("repo:new/name" in q for q in queries)


def test_unresolvable_repo_stays_missing(monkeypatch):
    """A deleted repo resolves to nothing; the cell stays missing rather
    than being recorded as empty."""
    monkeypatch.setattr(churn, "_search_count", lambda *_a: None)
    monkeypatch.setattr(churn, "_resolve_repo", lambda _r: None)
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    assert churn.search_issue_days("gone/repo", "2024-01-01..2024-01-31") \
        is None


def test_resolve_repo_reads_the_canonical_name(monkeypatch):
    monkeypatch.setattr(churn, "_gh", lambda *_a, **_k: "hydra-ecosystem/hydra\n")
    assert churn._resolve_repo("facebookresearch/hydra") == \
        "hydra-ecosystem/hydra"
    monkeypatch.setattr(churn, "_gh", lambda *_a, **_k: None)
    assert churn._resolve_repo("gone/repo") is None


def test_incomplete_count_is_not_trusted(monkeypatch):
    """Second review, finding 1: if the count query itself was
    incomplete, `len(rows) == total` is false assurance — the count is
    refused and the cell stays missing."""
    monkeypatch.setattr(churn, "_gh", lambda *_a, **_k:
                        '{"inc": true, "n": 1}')
    monkeypatch.setattr(churn, "_gh_search_page",
                        lambda _q, _p: [[1, "2024-01-01"]])
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    assert churn._search_count("q") is None
    assert churn.search_issue_days("o/r", "2024-01-01..2024-01-31") is None


def test_complete_count_is_read(monkeypatch):
    monkeypatch.setattr(churn, "_gh", lambda *_a, **_k:
                        '{"inc": false, "n": 7}')
    assert churn._search_count("q") == 7


def test_empty_cell_fetches_no_page(monkeypatch):
    """Review finding 6: a zero-count cell needs no page request."""
    monkeypatch.setattr(churn, "_search_count", lambda *_a: 0)

    def no_page(*_a):
        raise AssertionError("page fetched for an empty cell")
    monkeypatch.setattr(churn, "_gh_search_page", no_page)
    assert churn.search_issue_days("o/r", "2024-01-01..2024-01-31") == []


_ONE = [{"repo": "o/r", "per": "Q1-2024", "bugs": 1, "pr_windows": 1.0,
         "kloc_windows": 1.0, "per_pr": 1.0, "per_kloc": 1.0}]


def _meta(**extra):
    return {"held": 1, "selected": 1, "as_of": churn.AS_OF,
            "label_users": {"o/r"}, "ai_share": {}, **extra}


def test_print_exposure_counts_unpulled_cells_positively(monkeypatch,
                                                        capsys):
    """The unpulled-cell count printed as a negative number (held minus
    selected); it is selected minus held."""
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        _ONE, (["Q1-2024"], _meta(held=764, selected=768))))
    churn.print_exposure("quarter")
    out = capsys.readouterr().out
    assert "4 cells UNPULLED" in out and "-4" not in out


def test_print_exposure_header_states_the_block_burn_in(monkeypatch,
                                                        capsys):
    """Lookback crosses contiguous periods, so burn-in is RISK_DAYS-1
    days at the start of a censused block — not the first RISK_DAYS of
    every period, which the header still claimed."""
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        [], (["Q1-2024"], _meta(label_users=set()))))
    churn.print_exposure("quarter")
    out = capsys.readouterr().out
    assert f"first {RISK_DAYS} days of each quarter" not in out
    assert "censused block" in out


def test_print_exposure_cuts_balanced_and_ai_halves(monkeypatch, capsys):
    """The table carries the appendix cuts: the balanced panel (repos
    rated in every period) and the low/high-AI halves, beside all. The
    halves come from grouping inputs frozen WITH the dated cells (second
    review, finding 3): the counted artifact is never read, so the two
    freezes cannot silently disagree."""
    rows = [{"repo": r, "per": p, "bugs": 1, "pr_windows": 1.0,
             "kloc_windows": 1.0, "per_pr": 1.0, "per_kloc": 1.0}
            for r, ps in (("o/a", ["Q1-2024", "Q4-2025"]),
                          ("o/b", ["Q4-2025"]))
            for p in ps]
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        rows, (["Q1-2024", "Q4-2025"],
               _meta(label_users={"o/a", "o/b"},
                     ai_share={"o/a": (1, 10), "o/b": (9, 10)}))))

    def no_v1(*_a):
        raise AssertionError("counted artifact read for grouping")
    monkeypatch.setattr(churn, "_verify", no_v1)
    churn.print_exposure("quarter")
    out = capsys.readouterr().out
    q4 = [ln for ln in out.splitlines() if ln.startswith("Q4-2025")]
    assert [ln.split()[1] for ln in q4] == ["all", "balanced", "low-AI",
                                           "high-AI"]
    assert q4[0].split()[2] == "2" and q4[1].split()[2] == "1"


def test_footer_states_the_population_selection(monkeypatch, capsys):
    """PR #43 review: the footer still described the pilot's PR-level
    draw (repos entering probability-proportional-to-size) after the
    selection became every repo with an eligible PR."""
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        _ONE, (["Q1-2024"], _meta())))
    churn.print_exposure("quarter")
    out = capsys.readouterr().out
    assert "probability-proportional" not in out
    assert "every repo with an eligible merged PR" in out


def test_print_exposure_reports_frame_drift(monkeypatch, capsys):
    """Review finding 4: the numerator is frozen while the denominator is
    read live, so the table must say when the live frame no longer
    matches the frozen selection, as the counted table does."""
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        _ONE, (["Q1-2024"], _meta(frame="frozen-fp"))))
    churn.print_exposure("quarter", live_fp="moved-fp")
    assert "MOVED" in capsys.readouterr().out


def test_dated_freeze_stamps_grouping_inputs(monkeypatch):
    """Second review, finding 3: the dated freeze carries each repo's
    grouping-window AI share (`q2`) the way the counted freeze does, so
    the low/high-AI halves are read from the same artifact as the rates."""
    frozen = {}
    monkeypatch.setattr(churn, "bug_date_cells", lambda *_a, **_k: [
        {"repo": "o/r", "per": "Q2-2026", "rng": "r"}])
    monkeypatch.setattr(churn, "_load_jsonl", lambda _p: [])
    monkeypatch.setattr(churn, "bugs_fingerprint", lambda *_a: "fp")
    monkeypatch.setattr(churn, "_freeze",
                        lambda _p, _m, recs, *_a: frozen.update(
                            {r["repo"]: r for r in recs}))
    monkeypatch.setattr(churn, "search_issue_days", lambda *_a: [])
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)
    created = {"Q2-2026": [("o/r", 1, True, 10, 0),
                           ("o/r", 2, False, 10, 0)]}
    churn.pull_bug_dates({}, created, None)
    assert frozen["o/r"]["q2"] == [1, 2]


def _pull_fixture(monkeypatch, existing, frozen, pulled):
    monkeypatch.setattr(churn, "bug_date_cells", lambda *_a, **_k: [
        {"repo": "o/r", "per": "Q1-2024", "rng": "r"}])
    monkeypatch.setattr(churn, "_load_jsonl", lambda _p: existing)
    monkeypatch.setattr(churn, "bugs_fingerprint", lambda *_a: "fp")
    monkeypatch.setattr(churn, "_freeze",
                        lambda _p, _m, recs, *_a: frozen.update(
                            {r["repo"]: r for r in recs}))
    monkeypatch.setattr(churn, "search_issue_days",
                        lambda *_a: pulled.append(1) or [[1, "2024-02-10"]])
    monkeypatch.setattr(churn.time, "sleep", lambda _s: None)


def test_cells_from_an_older_collector_are_repulled(monkeypatch):
    """Third review: reuse by (repo, per, rng) alone kept cells collected
    before the completeness and ordering fixes, so a corrected collector
    never reached the frozen artifact. A cell carries the collector that
    produced it and is stale under any other."""
    frozen, pulled = {}, []
    _pull_fixture(monkeypatch, [{"repo": "o/r", "per": "Q1-2024",
                                 "rng": "r", "days": [[9, "2024-01-01"]]}],
                  frozen, pulled)
    churn.pull_bug_dates({}, {}, None)
    assert pulled, "cell from an unstamped collector was reused"
    assert frozen["o/r"]["days"] == [[1, "2024-02-10"]]
    assert frozen["o/r"]["collector"] == churn.COLLECTOR


def test_cells_from_the_current_collector_are_reused(monkeypatch):
    frozen, pulled = {}, []
    _pull_fixture(monkeypatch, [{"repo": "o/r", "per": "Q1-2024",
                                 "rng": "r", "days": [[9, "2024-01-01"]],
                                 "collector": churn.COLLECTOR}],
                  frozen, pulled)
    churn.pull_bug_dates({}, {}, None)
    assert not pulled
    assert frozen["o/r"]["days"] == [[9, "2024-01-01"]]


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
