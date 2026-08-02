"""Churn pilot study: balanced seeded draw, ratio math, generated-path
classifier (studies.churn)."""
from pipeline.studies import churn


def _pool(n_ai: int, n_non: int, per: str = "Q2-2026") -> dict:
    pool = {p: [] for p in churn.PERIODS}
    pool[per] = (
        [(f"o/r{i}", i, True, 100, 50) for i in range(n_ai)]
        + [(f"o/s{i}", i, False, 200, 20) for i in range(n_non)])
    return pool


def test_draw_is_balanced_and_oversamples_ai():
    """Equal AI/nonAI halves per period even when AI is a small minority
    of the frame (the deliberate oversampling)."""
    pool = _pool(n_ai=500, n_non=9500)          # AI = 5% of frame
    sel = churn.draw(pool)
    ai = sum(1 for s in sel if s["ai"])
    non = len(sel) - ai
    assert len(sel) == 10                       # 0.1% of 10,000
    assert ai == 5 and non == 5                 # balanced, not 5%


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
    r_ai = rows[("Q2-2026", "AI")]
    r_non = rows[("Q2-2026", "nonAI")]
    assert r_all["n"] == r_ai["n"] + r_non["n"] == 10
    assert r_ai["ratio"] == 50 / 100            # dels/adds
    assert r_non["ratio"] == 20 / 200
    assert r_all["adds"] == 4 * 100 + 6 * 200


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


def test_generated_path_classifier():
    for p in ("package-lock.json", "a/b/yarn.lock", "vendor/x.go",
              "web/dist/app.min.js", "proto/x_pb2.py", "img/logo.svg",
              "nb/analysis.ipynb", "src/__snapshots__/x.snap",
              "third_party/lib/y.c", "uv.lock"):
        assert churn.is_generated(p), p
    for p in ("src/main.py", "docs/lock_design.md", "distributed/run.py",
              "vendors.md", "locks/mutex.rs"):
        assert not churn.is_generated(p), p
