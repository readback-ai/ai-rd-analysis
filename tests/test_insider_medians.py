"""productivity.insider_medians — the person-level median insider
kLOC/quarter under three populations x three AI slices, fleet excluded."""
import math

import pytest

from pipeline.studies import productivity
from pipeline.studies.productivity import (ACTIVE_FLOOR, BASELINE_MONTHS,
                                           WINDOW_MONTHS, insider_medians)

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


@pytest.fixture
def authors(monkeypatch):
    """Four insiders plus a fleet operator. Per QUARTER (3 months):
    a: 12 PRs, 30 submitted / 18 merged kLOC, ever-AI, active always
    b:  3 PRs,  6 / 3, never-AI, active always
    c: 15 PRs, 60 / 30, never-AI, active in Q2-2026 only
    f: fleet operator, active always, must never count"""
    acc = {
        "a": _months(4, 10.0, 6.0, ai=True),
        "b": _months(1, 2.0, 1.0),
        "c": _months(5, 20.0, 10.0, only=WINDOW_MONTHS[6:9]),
        "f": _months(200, 500.0, 400.0, ai=True),
    }
    cohorts = {w: "never" for w in acc}
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda window=None: (acc, cohorts, {}, {"f"}))
    return acc


def test_any_population_is_the_quarter_active_insiders(authors):
    out = insider_medians(draws=50)
    q2 = out[("any", "all", "submitted", "Q2-2026")]
    assert q2["n"] == 3 and q2["median"] == 30.0        # a, b, c -> 6, 30, 60
    q1 = out[("any", "all", "submitted", "Q1-2024")]
    assert q1["n"] == 2 and q1["median"] == 18.0        # a, b -> 30, 6


def test_productive_population_applies_the_active_floor(authors):
    out = insider_medians(draws=50)
    q2 = out[("productive", "all", "submitted", "Q2-2026")]
    assert q2["n"] == 2 and q2["median"] == 45.0        # a (12 PRs), c (15)
    assert ACTIVE_FLOOR == 10
    q1 = out[("productive", "all", "merged", "Q1-2024")]
    assert q1["n"] == 1 and q1["median"] == 18.0        # only a clears 10


def test_panel_is_the_same_people_in_every_quarter(authors):
    out = insider_medians(draws=50)
    for q in ("Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"):
        cell = out[("panel", "all", "merged", q)]
        assert cell["n"] == 2 and cell["median"] == 10.5   # a, b -> 18, 3
    # c is quarter-active only in Q2-2026, so never in the panel
    assert out[("panel", "all", "submitted", "Q2-2026")]["median"] == 18.0


def test_ai_slices_split_on_window_evidence_and_fleet_is_excluded(authors):
    out = insider_medians(draws=50)
    ever = out[("any", "ever_ai", "submitted", "Q2-2026")]
    never = out[("any", "never_ai", "submitted", "Q2-2026")]
    assert ever["n"] == 1 and ever["median"] == 30.0       # a only; f excluded
    assert never["n"] == 2 and never["median"] == 33.0     # b, c -> 6, 60
    assert math.isnan(ever["lo"]) and math.isnan(ever["hi"])   # n < 2: no CI


def test_bootstrap_ci_brackets_the_median_and_is_seeded(authors):
    a = insider_medians(draws=200)[("any", "all", "submitted", "Q2-2026")]
    b = insider_medians(draws=200)[("any", "all", "submitted", "Q2-2026")]
    assert a["lo"] <= a["median"] <= a["hi"]
    assert (a["lo"], a["hi"]) == (b["lo"], b["hi"])        # same seed stream
