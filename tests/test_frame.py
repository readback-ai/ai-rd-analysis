"""Study-frame refactor (2026-07 architecture review, candidate 1): the
frame module must reproduce the exact eligibility semantics of the legacy
per-study loops before any call site migrates. Each profile test encodes
the legacy guard verbatim as its reference implementation."""

from pipeline import frame
from pipeline.detect import is_bot_login


def _pr(num, author, association="NONE", additions=100, deletions=0):
    return {"number": num, "createdAt": "2026-04-01T00:00:00Z",
            "mergedAt": "2026-04-05T00:00:00Z",
            "additions": additions, "deletions": deletions,
            "author": author, "authorAssociation": association,
            "mergedBy": {"login": "bob", "__typename": "User"},
            "commits": {"nodes": []}, "reviews": {"nodes": []}}


HUMAN = {"login": "alice", "__typename": "User"}
INSIDER = {"login": "carol", "__typename": "User"}
APP_BOT = {"login": "dependabot", "__typename": "Bot"}
AGENT_BOT = {"login": "copilot-swe-agent[bot]", "__typename": "Bot"}
USER_TYPED_BOT = {"login": "paddle-bot", "__typename": "User"}
NO_LOGIN = {"__typename": "User"}

PRS = [_pr(1, HUMAN), _pr(2, APP_BOT), _pr(3, AGENT_BOT),
       _pr(4, USER_TYPED_BOT), _pr(5, NO_LOGIN),
       _pr(6, INSIDER, association="MEMBER")]
CELLS = {("o/r", "2026-04-01..2026-06-30"): PRS}


def _patched(monkeypatch, cells=None, keep=None):
    monkeypatch.setattr(frame, "load_cells", lambda: cells or CELLS)
    monkeypatch.setattr(frame, "population_repos", lambda: keep or {"o/r"})


def test_pr_profile_matches_legacy_review_study_guard(monkeypatch):
    """Legacy guard in attention/fates/review_action: skip only
    __typename == "Bot" — user-typed bots and login-less Users stay."""
    _patched(monkeypatch)
    got = {f.pr["number"] for f in frame.study_frame("pr")}
    ref = {p["number"] for p in PRS
           if (p.get("author") or {}).get("__typename") != "Bot"}
    assert got == ref == {1, 4, 5, 6}


def test_author_profile_matches_legacy_productivity_guard(monkeypatch):
    """Legacy guard in productivity/event_study: skip Bot type, missing
    login, and user-typed bots (is_bot_login)."""
    _patched(monkeypatch)
    got = {f.pr["number"] for f in frame.study_frame("author")}
    ref = set()
    for p in PRS:
        a = p.get("author") or {}
        if a.get("__typename") == "Bot" or not a.get("login") \
                or is_bot_login(a["login"]):
            continue
        ref.add(p["number"])
    assert got == ref == {1, 6}


def test_all_profile_is_unfiltered(monkeypatch):
    """lane_rows anchors consume every PR before eligibility applies;
    bot_author lets that site keep its App-bot skip after the anchors."""
    _patched(monkeypatch)
    facts = list(frame.study_frame("all"))
    assert [f.pr["number"] for f in facts] == [p["number"] for p in PRS]
    assert [f.pr["number"] for f in facts if not f.bot_author] \
        == [f.pr["number"] for f in frame.study_frame("pr")]


def test_loc_capped_and_null_tolerant(monkeypatch):
    _patched(monkeypatch, cells={("o/r", "2026-04-01..2026-06-30"): [
        _pr(1, HUMAN, additions=25_000, deletions=5_000),
        {**_pr(2, HUMAN), "additions": None, "deletions": None}]})
    locs = [f.loc for f in frame.study_frame("pr")]
    assert locs == [frame.CAP, 0]


def test_population_and_period_filters(monkeypatch):
    _patched(monkeypatch, cells={
        ("o/r", "2026-04-01..2026-06-30"): [_pr(1, HUMAN)],
        ("x/y", "2026-04-01..2026-06-30"): [_pr(2, HUMAN)],      # not in pop
        ("o/r", "2025-07-01..2025-09-30"): [_pr(3, HUMAN)]})     # Q3-2025
    got = [(f.repo, f.period, f.pr["number"])
           for f in frame.study_frame("pr")]
    assert got == [("o/r", "Q2-2026", 1)]


def test_yield_order_is_group_then_cell_order(monkeypatch):
    """The seeded bootstrap RNG stream depends on iteration order: facts
    must come in group_by_period(...).items() order, inner lists intact."""
    cells = {("o/r", "2026-01-01..2026-03-31"): [_pr(1, HUMAN), _pr(2, HUMAN)],
             ("o/r", "2026-04-01..2026-06-30"): [_pr(3, HUMAN)]}
    _patched(monkeypatch, cells=cells)
    ref = [(repo, per, p["number"]) for (repo, per), prs in
           frame.group_by_period(cells, frame.QUARTER_RANGES).items()
           for p in prs]
    got = [(f.repo, f.period, f.pr["number"])
           for f in frame.study_frame("pr")]
    assert got == ref


def test_fact_fields(monkeypatch):
    _patched(monkeypatch)
    by_num = {f.pr["number"]: f for f in frame.study_frame("author")}
    alice, carol = by_num[1], by_num[6]
    assert (alice.author, alice.insider) == ("alice", False)
    assert (carol.author, carol.insider) == ("carol", True)
    assert alice.cls.merged and alice.loc == 100
    assert alice.repo == "o/r" and alice.period == "Q2-2026"


def test_month_granularity_buckets_by_created_month(monkeypatch):
    """Monthly callers (_author_months_and_cohorts) pass granularity and
    their own period set; buckets must re-partition by createdAt month."""
    _patched(monkeypatch)
    got = [(f.period, f.pr["number"]) for f in frame.study_frame(
        "pr", periods={"2026-04"}, granularity="month")]
    assert got == [("2026-04", n) for n in (1, 4, 5, 6)]


def test_periods_none_means_no_period_filter(monkeypatch):
    """event_study.author_months takes every censused month (baseline
    2024 months included) — periods=None must not narrow."""
    baseline_pr = {**_pr(1, HUMAN), "createdAt": "2024-02-10T00:00:00Z",
                   "mergedAt": "2024-02-12T00:00:00Z"}
    cells = {("o/r", "2024-01-01..2024-03-31"): [baseline_pr],
             ("o/r", "2026-04-01..2026-06-30"): [_pr(2, HUMAN)]}
    _patched(monkeypatch, cells=cells)
    got = [(f.period, f.pr["number"]) for f in frame.study_frame(
        "pr", periods=None, granularity="month")]
    assert got == [("2024-02", 1), ("2026-04", 2)]


def test_study_groups_matches_flat_frame(monkeypatch):
    """Group-shaped studies (slices repo floors) need ((repo, period),
    facts) in canonical order; flattening the groups must equal the flat
    stream, and group lists carry every eligible PR of that cell group."""
    cells = {("o/r", "2026-01-01..2026-03-31"): [_pr(1, HUMAN),
                                                 _pr(2, APP_BOT)],
             ("o/r", "2026-04-01..2026-06-30"): [_pr(3, HUMAN)]}
    _patched(monkeypatch, cells=cells)
    groups = list(frame.study_groups("all"))
    assert [k for k, _ in groups] == [("o/r", "Q1-2026"), ("o/r", "Q2-2026")]
    assert [[f.pr["number"] for f in fs] for _, fs in groups] == [[1, 2], [3]]
    assert [f.pr["number"] for _, fs in groups for f in fs] \
        == [f.pr["number"] for f in frame.study_frame("all")]


def test_constants_match_legacy_values():
    """PERIODS ×7 and CAP ×4 copies collapse onto these; any drift here
    would silently change every study."""
    assert frame.PERIODS == ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
    assert frame.CAP == 20_000
