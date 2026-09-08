"""productivity.insider_medians / insider_growth — the person-level median
insider kLOC/quarter under three populations x three AI slices, fleet
excluded."""
import math

import pytest

from pipeline.studies import productivity
from pipeline.studies.productivity import (ACTIVE_FLOOR, BASELINE_MONTHS,
                                           QUARTER_MONTHS, WINDOW_MONTHS,
                                           insider_medians)

ALL_MONTHS = BASELINE_MONTHS + WINDOW_MONTHS


def _months(prs_per_month, sub_kloc, mrg_kloc, ai=False, only=None):
    """login -> month rows [ai_mrg, nonai_mrg, ai_prs, prs, mrg_prs,
    submitted, ai_submitted], one identical row per month in `only`
    (default: every study month); `ai` puts one AI PR in each window
    month, none in the baseline."""
    out = {}
    for m in (only or ALL_MONTHS):
        is_window = m in WINDOW_MONTHS
        ai_prs = 1 if (ai and is_window) else 0
        out[m] = [mrg_kloc if ai_prs else 0.0, 0.0 if ai_prs else mrg_kloc,
                  ai_prs, prs_per_month, prs_per_month, sub_kloc, 0.0]
    return out


def _by_quarter(prs_per_quarter: dict, sub_kloc_per_quarter: dict):
    """Rows whose PR count differs by quarter: the quarter's PRs are put
    on its first month, its kLOC spread evenly, so quarterly sums are
    exact."""
    out = {}
    for q, months in QUARTER_MONTHS.items():
        for i, m in enumerate(months):
            n = prs_per_quarter[q] if i == 0 else 0
            out[m] = [0.0, 1.0, 0, n, n, sub_kloc_per_quarter[q] / 3, 0.0]
    return out


@pytest.fixture
def authors(monkeypatch):
    """Insiders plus a fleet operator. Per QUARTER (3 months):
    a: 12 PRs, 30 submitted / 18 merged kLOC, ever-AI, active always
    b:  3 PRs,  6 / 3, never-AI, active always
    c: 15 PRs, 60 / 30, never-AI, active in Q2-2026 only
    d: 1 PR at baseline then 9, 9, 12 (window mean 10.0, overall 7.75)
       — a window ramp-up; submitted 3 then 15 kLOC/quarter, never-AI
    e: 1 PR at baseline then 8, 12, 9 — never-AI; clears 10 in one
       quarter, misses in two
    g: 6, 10, 12, 12 PRs (min 6, mean 10.0) — submitted 6 then 12
       kLOC/quarter, never-AI: the productive rule's boundary member
    h: 4, 20, 20, 20 PRs (mean 16 but a 4-PR baseline) — 20 kLOC/quarter,
       never-AI
    f: fleet operator, active always, must never count"""
    acc = {
        "a": _months(4, 10.0, 6.0, ai=True),
        "b": _months(1, 2.0, 1.0),
        "c": _months(5, 20.0, 10.0, only=WINDOW_MONTHS[6:9]),
        "d": _by_quarter({"Q1-2024": 1, "Q4-2025": 9, "Q1-2026": 9,
                          "Q2-2026": 12},
                         {"Q1-2024": 3.0, "Q4-2025": 15.0, "Q1-2026": 15.0,
                          "Q2-2026": 15.0}),
        "e": _by_quarter({"Q1-2024": 1, "Q4-2025": 8, "Q1-2026": 12,
                          "Q2-2026": 9},
                         {q: 9.0 for q in QUARTER_MONTHS}),
        "g": _by_quarter({"Q1-2024": 6, "Q4-2025": 10, "Q1-2026": 12,
                          "Q2-2026": 12},
                         {"Q1-2024": 6.0, "Q4-2025": 12.0, "Q1-2026": 12.0,
                          "Q2-2026": 12.0}),
        "h": _by_quarter({"Q1-2024": 4, "Q4-2025": 20, "Q1-2026": 20,
                          "Q2-2026": 20},
                         {q: 20.0 for q in QUARTER_MONTHS}),
        "f": _months(200, 500.0, 400.0, ai=True),
    }
    cohorts = {w: "never" for w in acc}
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda window=None: (acc, cohorts, {}, {"f"}))
    return acc


def test_any_population_is_the_quarter_active_insiders(authors):
    out = insider_medians(draws=50)
    q2 = out[("any", "all", "submitted", "Q2-2026")]
    # a, b, c, d, e, g, h -> 30, 6, 60, 15, 9, 12, 20
    assert q2["n"] == 7 and q2["median"] == 15.0
    q1 = out[("any", "all", "submitted", "Q1-2024")]
    # a, b, d, e, g, h -> 30, 6, 3, 9, 6, 20
    assert q1["n"] == 6 and q1["median"] == 7.5


def test_productive_panel_is_symmetric_across_quarters(authors):
    """Membership is decided once from >=5 PRs in EVERY quarter and a
    mean of >=10 over all four, the baseline weighted like any other
    quarter: g (6, 10, 12, 12) is in everywhere; d (1, 9, 9, 12 — a
    window ramp-up with window mean 10) and h (4, 20, 20, 20 — mean 16
    but a 4-PR baseline) are out everywhere, as is e (1, 8, 12, 9), which
    a per-quarter floor would admit in one quarter only."""
    out = insider_medians(draws=50)
    assert (ACTIVE_FLOOR, productivity.PRODUCTIVE_MIN_QUARTER) == (10, 5)
    for q in QUARTER_MONTHS:
        cell = out[("productive", "all", "submitted", q)]
        assert cell["n"] == 2, q                       # a and g, every quarter
    assert out[("productive", "all", "submitted", "Q1-2024")]["median"] == 18.0
    assert out[("productive", "all", "submitted", "Q2-2026")]["median"] == 21.0


def test_panel_is_the_same_people_in_every_quarter(authors):
    out = insider_medians(draws=50)
    for q in QUARTER_MONTHS:
        cell = out[("panel", "all", "submitted", q)]
        assert cell["n"] == 6, q                       # a, b, d, e, g, h (not c)
    # c is quarter-active only in Q2-2026, so never in the panel
    assert out[("panel", "all", "submitted", "Q2-2026")]["median"] == 13.5


def test_ai_slices_split_on_window_evidence_and_fleet_is_excluded(authors):
    out = insider_medians(draws=50)
    ever = out[("any", "ever_ai", "submitted", "Q2-2026")]
    never = out[("any", "never_ai", "submitted", "Q2-2026")]
    assert ever["n"] == 1 and ever["median"] == 30.0       # a only; f excluded
    assert never["n"] == 6 and never["median"] == 13.5     # b, c, d, e, g, h
    assert math.isnan(ever["lo"]) and math.isnan(ever["hi"])   # n < 2: no CI


def test_growth_normalizes_each_series_to_its_own_baseline(authors):
    """Every population x slice starts at 1.0 and later quarters are the
    ratio of that series' median to its own Q1-2024 median."""
    out = productivity.insider_growth(draws=50)
    for pop in ("any", "productive", "panel"):
        base = out[(pop, "all", "submitted", "Q1-2024")]
        assert (base["mult"], base["lo"], base["hi"]) == (1.0, 1.0, 1.0)
    assert out[("any", "all", "submitted", "Q2-2026")]["mult"] == \
        pytest.approx(15.0 / 7.5)
    assert out[("productive", "all", "submitted", "Q2-2026")]["mult"] == \
        pytest.approx(21.0 / 18.0)
    q2 = out[("any", "all", "submitted", "Q2-2026")]
    assert q2["n"] == 7 and q2["n_base"] == 6


def test_growth_ci_is_paired_for_fixed_panels(monkeypatch):
    """The growth bootstrap resampled the baseline and later quarters
    independently even for the fixed panels, whose members are the same
    people in every quarter: with every member exactly doubling, the
    interval spanned 0.25x-16x instead of collapsing to 2x. Fixed panels
    resample person indices jointly."""
    subs = {"p1": 1.0, "p2": 2.0, "p3": 3.0, "p4": 4.0}
    acc = {w: _by_quarter({q: 12 for q in QUARTER_MONTHS},
                          {"Q1-2024": s, "Q4-2025": 2 * s, "Q1-2026": 2 * s,
                           "Q2-2026": 2 * s})
           for w, s in subs.items()}
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda window=None: (acc, {w: "never" for w in acc},
                                             {}, set()))
    out = productivity.insider_growth(draws=100)
    for pop in ("panel", "productive"):           # 12 PRs/q clears both
        cell = out[(pop, "all", "submitted", "Q2-2026")]
        assert cell["n"] == 4
        assert (cell["mult"], cell["lo"], cell["hi"]) == (2.0, 2.0, 2.0), pop


def test_growth_ratio_ci_brackets_the_multiple_or_is_nan(authors):
    out = productivity.insider_growth(draws=200)
    cell = out[("any", "all", "submitted", "Q2-2026")]
    assert cell["lo"] <= cell["mult"] <= cell["hi"]
    single = out[("any", "ever_ai", "submitted", "Q2-2026")]   # a alone
    assert single["mult"] == 1.0 and math.isnan(single["lo"])


def test_bootstrap_ci_brackets_the_median_and_is_seeded(authors):
    a = insider_medians(draws=200)[("any", "all", "submitted", "Q2-2026")]
    b = insider_medians(draws=200)[("any", "all", "submitted", "Q2-2026")]
    assert a["lo"] <= a["median"] <= a["hi"]
    assert (a["lo"], a["hi"]) == (b["lo"], b["hi"])        # same seed stream
