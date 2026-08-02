"""Churn pilot study (studies.churn): merge-quarter bucketing, the
within-org adoption contrast, balanced seeded draw, true medians,
selection-vs-store reconciliation, bug-window frontier alignment,
generated-path classifier. Round-1 PR-review items are named inline."""
from pipeline.studies import churn


def _pool(n_ai: int, n_non: int, per: str = "Q2-2026") -> dict:
    pool = {p: [] for p in churn.PERIODS}
    pool[per] = (
        [(f"o/r{i}", i, True, 100, 50) for i in range(n_ai)]
        + [(f"o/s{i}", i, False, 200, 20) for i in range(n_non)])
    return pool


def test_merge_quarter_buckets_by_merge_not_creation():
    """Review P1: churn is assigned by MERGE quarter; merges outside
    every censused quarter (incl. Q3-2025) map to None."""
    assert churn.merge_quarter("2026-04-02T09:00:00Z") == "Q2-2026"
    assert churn.merge_quarter("2024-03-31T23:59:00Z") == "Q1-2024"
    assert churn.merge_quarter("2024-04-15T00:00:00Z") is None  # spillover
    assert churn.merge_quarter("2025-08-01T00:00:00Z") is None  # Q3-2025
    assert churn.merge_quarter(None) is None


def test_adoption_contrast_is_within_org_low_vs_high():
    """Review P1: the headline replicates the source design — each org's
    highest-adoption quarter's churn over its lowest's."""
    pool = {p: [] for p in churn.PERIODS}
    # org "a": low-adoption quarter (0% AI, ratio 0.2), high (50% AI,
    # ratio 0.6) -> multiple 3.0. 20 PRs each to clear ORG_MIN_PRS.
    pool["Q4-2025"] = [("a/r", i, False, 100, 20) for i in range(20)]
    pool["Q2-2026"] = ([("a/r", i, True, 100, 60) for i in range(10)]
                      + [("a/r", 100 + i, False, 100, 60)
                         for i in range(10)])
    # org "b": qualifying quarters but zero adoption spread -> dropped.
    pool["Q4-2025"] += [("b/r", i, False, 100, 10) for i in range(20)]
    pool["Q2-2026"] += [("b/r", i, False, 100, 90) for i in range(20)]
    r = churn.adoption_rows(pool)
    assert r["dropped_flat"] == 1
    (org, lo_share, hi_share, lo_r, hi_r, mult), = r["multiples"]
    assert (org, lo_share, hi_share) == ("a", 0.0, 0.5)
    assert (lo_r, hi_r) == (0.2, 0.6)
    assert abs(mult - 3.0) < 1e-12


def test_adoption_contrast_caps_sides_per_pr():
    pool = {p: [] for p in churn.PERIODS}
    pool["Q4-2025"] = [("a/r", i, False, 100_000, 100) for i in range(20)]
    pool["Q2-2026"] = [("a/r", i, True, 100_000, 100) for i in range(20)]
    (_o, _ls, _hs, lo_r, hi_r, _m), = churn.adoption_rows(pool)["multiples"]
    assert lo_r == hi_r == 100 / churn.CAP


def test_draw_is_balanced_and_oversamples_ai():
    """Equal AI/nonAI halves per period even when AI is a small minority
    of the frame (the deliberate oversampling)."""
    pool = _pool(n_ai=500, n_non=9500)          # AI = 5% of frame
    sel = churn.draw(pool)
    ai = sum(1 for s in sel if s["ai"])
    assert len(sel) == 10                       # 0.1% of 10,000
    assert ai == 5 and len(sel) - ai == 5       # balanced, not 5%


def test_draw_backfills_when_an_arm_is_short():
    """Q1-2024 has no AI PRs: the AI half backfills from nonAI so the
    period still reaches its target size."""
    pool = _pool(n_ai=0, n_non=5000, per="Q1-2024")
    sel = churn.draw(pool)
    assert len(sel) == 5                        # 0.1% of 5,000
    assert all(not s["ai"] for s in sel)


def test_draw_is_deterministic_and_sorted():
    pool = _pool(n_ai=300, n_non=7000)
    a, b = churn.draw(pool), churn.draw(pool)
    assert a == b
    assert a == sorted(a, key=lambda d: (d["per"], d["repo"], d["num"]))


def test_census_rows_ratio_and_arms_partition():
    pool = _pool(n_ai=4, n_non=6)
    rows = churn.census_rows(pool)
    r_all = rows[("Q2-2026", "all")]
    assert r_all["n"] == rows[("Q2-2026", "AI")]["n"] \
        + rows[("Q2-2026", "nonAI")]["n"] == 10
    assert rows[("Q2-2026", "AI")]["ratio"] == 50 / 100
    assert r_all["adds"] == 4 * 100 + 6 * 200


def test_median_is_true_median_and_skips_zero_addition_prs():
    """Review P2: even-sized arms average the two middle values, and
    deletion-only PRs (adds=0) are excluded from the median rather than
    given an additions pseudocount."""
    pool = {p: [] for p in churn.PERIODS}
    pool["Q2-2026"] = [("o/r", 1, False, 100, 10),   # 0.1
                       ("o/r", 2, False, 100, 30),   # 0.3
                       ("o/r", 3, False, 100, 60),   # 0.6
                       ("o/r", 4, False, 100, 80),   # 0.8
                       ("o/r", 5, False, 0, 500)]    # no adds: excluded
    r = churn.census_rows(pool)[("Q2-2026", "all")]
    assert r["median_pr"] == (0.3 + 0.6) / 2
    assert r["del_dominant"] == 1 / 5            # the adds=0 PR still counts


def test_repo_pairs_floor_and_zero_adds_skip():
    """CW series: repos qualify per (period, arm) at >= MIN_PRS PRs with
    nonzero additions; delete-only repos are skipped, never zeroed."""
    pool = {p: [] for p in churn.PERIODS}
    pool["Q2-2026"] = (
        [("o/big", i, False, 100, 40) for i in range(5)]      # qualifies
        + [("o/tiny", i, False, 100, 10) for i in range(4)]   # under floor
        + [("o/delonly", i, False, 0, 50) for i in range(6)])  # no adds
    pairs = churn.repo_pairs(pool)
    got = pairs[("Q2-2026", "all")]
    assert [r for _v, r in got] == ["o/big"]
    assert got[0][0] == (5 * 40) / (5 * 100)
    assert ("Q2-2026", "AI") not in pairs


def test_repo_pairs_caps_each_side_per_pr():
    pool = {p: [] for p in churn.PERIODS}
    pool["Q2-2026"] = [("o/mega", i, True, 100_000, 10) for i in range(5)]
    (val, _repo), = churn.repo_pairs(pool)[("Q2-2026", "AI")]
    assert val == (5 * 10) / (5 * churn.CAP)   # adds capped at 20k/PR


def test_reconcile_drops_stale_keeps_current_lists_missing():
    """Review P2: the persisted files hold EXACTLY the current selection —
    stale draws are dropped, hydrated still-selected records are reused,
    unhydrated selections are listed as todo."""
    selected = [{"repo": "o/a", "num": 1}, {"repo": "o/b", "num": 2}]
    existing = [{"repo": "o/a", "num": 1, "files": []},   # reused
                {"repo": "o/z", "num": 9, "files": []},   # stale -> dropped
                {"repo": "o/b", "num": 2}]                # unhydrated
    kept, todo, stale = churn.reconcile(selected, existing,
                                        ("repo", "num"), "files")
    assert set(kept) == {("o/a", 1)}
    assert todo == [{"repo": "o/b", "num": 2}]
    assert stale == 1


def test_bug_window_truncates_at_maturity_frontier():
    """Review P2: numerator exposure ends at the maturity frontier, the
    last creation date an included (mature) PR can have."""
    as_of = "2026-08-01T00:00:00Z"                 # frontier 2026-06-06
    assert churn.maturity_frontier(as_of) == "2026-06-06"
    assert churn.bug_window("Q2-2026", as_of) == "2026-04-01..2026-06-06"
    assert churn.bug_window("Q1-2026", as_of) == "2026-01-01..2026-03-31"


def test_generated_path_classifier():
    for p in ("package-lock.json", "a/b/yarn.lock", "vendor/x.go",
              "web/dist/app.min.js", "proto/x_pb2.py", "img/logo.svg",
              "nb/analysis.ipynb", "src/__snapshots__/x.snap",
              "third_party/lib/y.c", "uv.lock"):
        assert churn.is_generated(p), p
    for p in ("src/main.py", "docs/lock_design.md", "distributed/run.py",
              "vendors.md", "locks/mutex.rs"):
        assert not churn.is_generated(p), p
