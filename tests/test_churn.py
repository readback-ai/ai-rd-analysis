"""Churn pilot study (studies.churn): frame construction, same-quarter
trimming, the within-org adoption contrast, balanced seeded draw, true
medians, selection-vs-store reconciliation, frozen-selection manifests,
bug-window frontier alignment, generated-path classifier. PR-review
items are named inline."""
from pipeline import detect, frame
from pipeline.studies import churn


def _fact(created: str, merged: str, repo: str = "o/r", num: int = 1):
    pr = {"number": num, "createdAt": created, "mergedAt": merged,
          "additions": 10, "deletions": 5,
          "author": {"login": "alice", "__typename": "User"}}
    period = churn.merge_quarter(created)      # = the creation quarter
    return frame.PRFact(repo, period, pr, detect.classify_pr(pr), 15,
                        "alice", False, False)


def test_eligible_splits_trimmed_churn_frame_from_created_denominator(
        monkeypatch):
    """Review round 3, P2 — regression pins for the round-2 frame fixes:
    (a) an IMMATURE but already-merged same-quarter PR enters the churn
    frame (an observed merge is terminal; maturity must not truncate the
    trailing quarter); (b) a mature PR created in Q1-2026 and merged in
    Q2-2026 enters created["Q1-2026"] but never the trimmed frame;
    (c) an in-quarter mature merge enters both frames."""
    monkeypatch.setattr(detect, "AS_OF", "2026-08-01T00:00:00Z")
    facts = [
        _fact("2026-06-20T00:00:00Z", "2026-06-25T00:00:00Z", num=1),
        _fact("2026-03-20T00:00:00Z", "2026-04-02T00:00:00Z", num=2),
        _fact("2026-01-10T00:00:00Z", "2026-01-20T00:00:00Z", num=3),
    ]
    monkeypatch.setattr(churn, "study_frame", lambda level: iter(facts))
    trimmed, created, cross, periods = churn.eligible()
    assert periods == churn.PERIODS
    assert [x[1] for x in trimmed["Q2-2026"]] == [1]   # (a) immature kept
    assert created["Q2-2026"] == []                    # (a) not mature
    assert [x[1] for x in created["Q1-2026"]] == [2, 3]  # (b)+(c)
    assert [x[1] for x in trimmed["Q1-2026"]] == [3]   # (b) cross excluded
    assert cross == 1


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


def test_adoption_endpoints_exclude_q1_2024():
    """Review round 2, P1: Q1-2024's zero adoption is by construction
    (marker availability), so it is never an endpoint — an org whose only
    other qualifying quarter is Q1-2024 is not contrasted."""
    pool = {p: [] for p in churn.PERIODS}
    pool["Q1-2024"] = [("a/r", i, False, 100, 20) for i in range(20)]
    pool["Q2-2026"] = [("a/r", i, True, 100, 60) for i in range(20)]
    r = churn.adoption_rows(pool)
    assert r["multiples"] == []
    assert r["orgs_any"] == 1                  # one org, one ERA quarter
    assert r["orgs_ge2"] == 0                  # never reaches contrast


def test_migrate_bug_rows_stamps_full_quarter_range():
    """Review round 2, P2: pre-stamp bug rows were queried with the full
    quarter range — migration stamps exactly that, so unchanged windows
    are reused and frontier-trimmed ones (Q2-2026) retire as stale."""
    rows = churn.migrate_bug_rows([
        {"repo": "o/r", "per": "Q1-2026", "bugs": 3},
        {"repo": "o/r", "per": "Q2-2026", "bugs": 5},
        {"repo": "o/r", "per": "Q4-2025", "rng": "keep..asis", "bugs": 1}])
    assert rows[0]["rng"] == "2026-01-01..2026-03-31"
    assert rows[1]["rng"] == "2026-04-01..2026-06-30"   # full Q2 = stale
    assert rows[2]["rng"] == "keep..asis"


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


def test_bug_window_accepts_month_tokens():
    """Monthly pull crashed with KeyError('2024-01'): bug_window resolved
    tokens via QUARTER_RANGES instead of resolve_period. Month tokens
    must resolve, with the frontier a no-op on finalized months."""
    as_of = "2026-08-01T00:00:00Z"
    assert churn.bug_window("2024-01", as_of) == "2024-01-01..2024-01-31"
    assert churn.bug_window("2026-05", as_of) == "2026-05-01..2026-05-31"
    assert churn.bug_window("2026-06", as_of) == "2026-06-01..2026-06-06"


def test_adoption_attrition_counts_are_separated():
    """Review round 3, P2: orgs with >= 1 vs >= 2 qualifying era quarters
    are tracked separately, and endpoint-ratio exclusions get their own
    counter (they are not silently folded into either)."""
    pool = {p: [] for p in churn.PERIODS}
    # contrastable org
    pool["Q4-2025"] = [("a/r", i, False, 100, 20) for i in range(20)]
    pool["Q2-2026"] = [("a/r", i, True, 100, 60) for i in range(20)]
    # one era quarter only
    pool["Q4-2025"] += [("solo/r", i, False, 100, 10) for i in range(20)]
    # two quarters, spread, but zero-addition low endpoint
    pool["Q4-2025"] += [("badr/r", i, False, 0, 10) for i in range(20)]
    pool["Q2-2026"] += [("badr/r", i, True, 100, 10) for i in range(20)]
    r = churn.adoption_rows(pool)
    assert (r["orgs_any"], r["orgs_ge2"]) == (3, 2)
    assert r["dropped_ratio"] == 1
    assert [m[0] for m in r["multiples"]] == ["a"]


def test_drift_line_reports_frozen_vs_live_frame():
    """Review round 3, P2: tables report the FROZEN selection; a moved
    live store is flagged, never silently re-drawn."""
    m = {"frame": "abc", "as_of": "X"}
    assert "MATCHES" in churn._drift_line(m, "abc")
    assert "MOVED" in churn._drift_line(m, "def")
    assert "unknown" in churn._drift_line({}, "abc")


def test_freeze_verify_roundtrip_and_refusal(tmp_path):
    """Review round 4, P2: every freeze writes data + manifest
    crash-consistently (manifest carries a data digest and row count);
    print paths refuse on any skew instead of reporting mixed state."""
    import pytest
    data, mani = tmp_path / "d.jsonl", tmp_path / "m.json"
    recs = [{"repo": "o/a", "per": "Q2-2026", "bugs": 3}]
    churn._freeze(data, mani, recs, "fp123", selected=2)
    rows, manifest = churn._verify(data, mani)
    assert rows == recs
    assert (manifest["held"], manifest["selected"]) == (1, 2)
    data.write_text(data.read_text() + '{"repo":"o/b"}\n')   # tamper
    with pytest.raises(SystemExit, match="does not match its manifest"):
        churn._verify(data, mani)
    with pytest.raises(SystemExit, match="missing"):
        churn._verify(data, tmp_path / "absent.json")


def test_bug_stats_come_only_from_frozen_records():
    """Review round 4, P2: denominators and Q2 group inputs are read
    from the stamped records — no live-frame input at print time. The
    q2 stamp rides EVERY row (round 5), so a repo missing its Q2 cell
    still carries group membership."""
    rows = [
        {"repo": "o/a", "per": "Q1-2024", "bugs": 4, "merged": 100,
         "q2": [30, 50]},
    ]
    bugs, merged, ai_share = churn.bug_stats(rows)
    assert bugs[("o/a", "Q1-2024")] == 4
    assert merged[("o/a", "Q1-2024")] == 100
    assert ai_share["o/a"] == (30, 50)


def test_rank_groups_excludes_undefined_q2_shares():
    """Review round 5, P2: a zero Q2 denominator is an UNDEFINED adoption
    share — the repo joins neither AI half (treating it as 0.0 silently
    filed it under low-AI) while still counting in 'all'."""
    with_bugs = {"a", "b", "c", "d", "nodata"}
    ai_share = {"a": (0, 10), "b": (2, 10), "c": (5, 10), "d": (9, 10),
                "nodata": (0, 0)}
    lo, hi, unranked = churn.rank_groups(with_bugs, ai_share)
    assert lo == {"a", "b"}
    assert hi == {"c", "d"}
    assert unranked == {"nodata"}


def test_stamp_denominators_freezes_created_frame_values():
    """Review round 4, P2: stamping embeds the creation-bucketed
    denominator per cell and the Q2 AI numerator per repo, refreshed on
    every freeze (reused bug counts, re-stamped denominators)."""
    created = {p: [] for p in churn.PERIODS}
    created["Q1-2024"] = [("o/a", i, False, 1, 1) for i in range(7)]
    created["Q2-2026"] = ([("o/a", i, True, 1, 1) for i in range(3)]
                         + [("o/a", 10 + i, False, 1, 1) for i in range(2)])
    records = {
        ("o/a", "Q1-2024", "r"): {"repo": "o/a", "per": "Q1-2024",
                                  "rng": "r", "bugs": 1},
        ("o/a", "Q2-2026", "r"): {"repo": "o/a", "per": "Q2-2026",
                                  "rng": "r", "bugs": 2,
                                  "merged": 999, "ai_num": 999},  # stale
    }
    churn._stamp_denominators(records, created)
    assert records[("o/a", "Q1-2024", "r")]["merged"] == 7
    assert records[("o/a", "Q2-2026", "r")]["merged"] == 5
    # round 5: q2 group inputs stamped on EVERY row; legacy ai_num gone
    assert records[("o/a", "Q1-2024", "r")]["q2"] == [3, 5]
    assert records[("o/a", "Q2-2026", "r")]["q2"] == [3, 5]
    assert "ai_num" not in records[("o/a", "Q2-2026", "r")]


def test_fingerprint_covers_ai_flags_and_both_pools():
    """Review round 4, P2: the fingerprint changes when an item's AI flag
    flips (group membership input) and when a second pool is passed
    (the bug freeze depends on trimmed AND created)."""
    a = {p: [] for p in churn.PERIODS}
    a["Q2-2026"] = [("o/r", 1, False, 10, 5)]
    b = {p: [] for p in churn.PERIODS}
    b["Q2-2026"] = [("o/r", 1, True, 10, 5)]
    assert churn.frame_fingerprint(a) != churn.frame_fingerprint(b)
    assert churn.frame_fingerprint(a) != churn.frame_fingerprint(a, b)


def test_finalized_months_apply_w8_finalization(monkeypatch):
    """Monthly mode: a month reports only once month_end + 56d <= AS_OF —
    at AS_OF 2026-08-01, May 2026 is the last reportable month (June
    finalizes ~Aug 25, July ~Sep 25)."""
    from pipeline.studies import productivity
    monkeypatch.setattr(detect, "AS_OF", "2026-08-01T00:00:00Z")
    assert productivity.month_w8_mature("2026-05")
    assert not productivity.month_w8_mature("2026-06")
    assert not productivity.month_w8_mature("2026-07")


def test_adoption_era_and_group_periods_by_granularity():
    """Monthly endpoints start at the adoption era (2024 baseline months
    never rank); the grouping window is the latest era quarter or the
    last three finalized era months."""
    months = ["2024-01", "2024-02", "2025-10", "2025-11", "2025-12",
              "2026-01", "2026-02", "2026-03", "2026-04", "2026-05"]
    assert churn.adoption_era(months) == months[2:]
    assert churn.group_periods(months) == ["2026-03", "2026-04", "2026-05"]
    assert churn.adoption_era(churn.PERIODS) == churn.ADOPTION_PERIODS
    assert churn.group_periods(churn.PERIODS) == ["Q2-2026"]


def test_stamp_denominators_monthly_grouping_window():
    """Monthly grouping inputs sum over the passed window (last three
    finalized months), stamped on every row."""
    created = {"2026-04": [("o/a", 1, True, 1, 1), ("o/a", 2, False, 1, 1)],
               "2026-05": [("o/a", 3, True, 1, 1)],
               "2026-03": [("o/a", 4, False, 1, 1)],
               "2024-01": [("o/a", 5, False, 1, 1)]}
    records = {("o/a", "2024-01", "r"): {"repo": "o/a", "per": "2024-01",
                                         "rng": "r", "bugs": 0}}
    churn._stamp_denominators(records, created,
                              ("2026-03", "2026-04", "2026-05"))
    rec = records[("o/a", "2024-01", "r")]
    assert rec["merged"] == 1
    assert rec["q2"] == [2, 4]      # 2 AI of 4 merged in the window


def test_generated_path_classifier():
    for p in ("package-lock.json", "a/b/yarn.lock", "vendor/x.go",
              "web/dist/app.min.js", "proto/x_pb2.py", "img/logo.svg",
              "nb/analysis.ipynb", "src/__snapshots__/x.snap",
              "third_party/lib/y.c", "uv.lock"):
        assert churn.is_generated(p), p
    for p in ("src/main.py", "docs/lock_design.md", "distributed/run.py",
              "vendors.md", "locks/mutex.rs"):
        assert not churn.is_generated(p), p
