"""Monthly figure windows: analyze.month_window (the period resolver)
and the study-layer `window=` threading that feeds extension months into
the monthly series without moving any frozen default.
"""
import pytest

from pipeline import analyze, detect, figstyle, frame
from pipeline.analyze import month_window
from pipeline.studies import paper_tables, productivity
from pipeline.studies.productivity import WINDOW_MONTHS

# The data stamp advances with every re-pull (METHODS §1c); pin it so
# fixture maturity never rides on the module constant's current value.
PINNED_AS_OF = "2026-10-01T00:00:00Z"


@pytest.fixture(autouse=True)
def pin_as_of(monkeypatch):
    monkeypatch.setattr(detect, "AS_OF", PINNED_AS_OF)


@pytest.fixture
def registry(tmp_path, monkeypatch):
    """Point the incremental registry at a tmp file; write() sets its
    contents, starting absent (no incremental months)."""
    reg = tmp_path / "incremental_months.txt"
    monkeypatch.setattr(analyze, "INCREMENTAL_REGISTRY", reg)
    return reg


def test_default_window_is_the_frozen_figstyle_window(registry):
    assert month_window() == figstyle.WINDOW


def test_registered_month_extends_the_window(registry):
    registry.write_text("2026-07\n")
    assert month_window("2026-07") == figstyle.WINDOW + ["2026-07"]
    # the DEFAULT stays frozen even with the registry populated:
    # extension is opt-in via `through`
    assert month_window() == figstyle.WINDOW


def test_earlier_through_truncates(registry):
    assert month_window("2026-02") == ["2025-10", "2025-11", "2025-12",
                                       "2026-01", "2026-02"]


def test_malformed_and_out_of_range_tokens_raise(registry):
    with pytest.raises(ValueError, match="malformed"):
        month_window("2026/07")
    with pytest.raises(ValueError, match="predates"):
        month_window("2024-01")


def test_uncensused_month_raises_and_names_the_remedy(registry):
    registry.write_text("2026-07\n")
    with pytest.raises(ValueError, match=r"monthly_update"):
        month_window("2026-09")
    with pytest.raises(ValueError, match=r"last censused month: 2026-07"):
        month_window("2026-08")


def test_registry_gap_raises(registry):
    registry.write_text("2026-08\n")           # 2026-07 never collected
    with pytest.raises(ValueError, match="gap between 2026-06 and 2026-08"):
        month_window("2026-08")


# ---------------------------------------------------- study threading

def _pr(num, created, author="dev1", assoc="MEMBER", ai=False):
    emails = ["noreply@anthropic.com"] if ai else []
    return {"number": num, "createdAt": created, "mergedAt": None,
            "additions": 1000, "deletions": 0,
            "author": {"login": author, "__typename": "User"},
            "authorAssociation": assoc, "mergedBy": None,
            "commits": {"nodes": [{"commit": {
                "message": "change", "authors": {
                    "nodes": [{"email": e} for e in emails]}}}]},
            "reviews": {"nodes": []}}


@pytest.fixture
def july_cells(registry, monkeypatch):
    """A frozen-window author (non-AI, insider) who turns AI-involved in
    the registered extension month 2026-07."""
    registry.write_text("2026-07\n")
    cells = {
        ("o/r", "2026-04-01..2026-06-30"): [
            _pr(1, "2026-04-10T00:00:00Z"),
            _pr(2, "2026-04-12T00:00:00Z", author="dev2")],
        ("o/r", "2026-07-01..2026-07-31"): [
            _pr(3, "2026-07-10T00:00:00Z", ai=True)],
    }
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    return cells


def test_month_frame_kw_gates_the_extended_ranges(monkeypatch):
    """The frozen monthly path must keep the default QUARTER_RANGES:
    group iteration order feeds the seeded bootstrap draws, so the
    extended period map is applied only when the window actually
    reaches past WINDOW_MONTHS."""
    sentinel = {"X": "2026-07-01..2026-07-31"}
    monkeypatch.setattr(productivity, "_extended_ranges", lambda: sentinel)
    assert "ranges" not in productivity.month_frame_kw()
    assert "ranges" not in productivity.month_frame_kw(WINDOW_MONTHS)
    kw = productivity.month_frame_kw(WINDOW_MONTHS + ["2026-07"])
    assert kw["ranges"] is sentinel
    assert kw["periods"][-1] == "2026-07"


def test_extension_extends_series_never_cohorts(july_cells):
    """A window month past the frozen quarters adds series points but
    must not reassign cohorts: dev1's first AI PR lands in 2026-07, so
    with the extended window dev1 still reads 'never' (the frozen
    assignment), while the 2026-07 activity appears in the series."""
    base = productivity.adoption_monthly()
    assert not any(mon == "2026-07" for mon, _ in base)
    ext = productivity.adoption_monthly(
        window=WINDOW_MONTHS + ["2026-07"])
    assert ext[("2026-07", "never")]["n"] == 1
    # frozen months identical between the two calls
    assert {k: v for k, v in ext.items() if k[0] != "2026-07"} == base


def test_extension_months_never_admit_new_insiders(registry, monkeypatch):
    """adoption_cohorts June rows moved under --through 2026-08 with
    June cells byte-identical: the insider set was built from every
    fact, so an author whose only insider PR falls in an extension month
    entered the cohort table and their frozen-month activity shifted
    the frozen months' means. Insider status, like cohort and fleet
    membership, is frozen with the quarters."""
    registry.write_text("2026-07\n")
    cells = {
        ("o/r", "2026-04-01..2026-06-30"): [
            _pr(1, "2026-06-10T00:00:00Z", author="late", assoc="NONE"),
            _pr(2, "2026-06-12T00:00:00Z", author="core")],
        ("o/r", "2026-07-01..2026-07-31"): [
            _pr(3, "2026-07-10T00:00:00Z", author="late")],   # MEMBER now
    }
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    base = productivity.adoption_monthly()
    ext = productivity.adoption_monthly(window=WINDOW_MONTHS + ["2026-07"])
    assert base[("2026-06", "never")]["n"] == 1        # only 'core'
    assert ext[("2026-06", "never")] == base[("2026-06", "never")]


def test_usage_rows_monthly_applies_the_per_month_floor(july_cells,
                                                        monkeypatch):
    """Monthly fig2 rows use the 2-PR/month floor (the 5-PR/quarter
    threshold per unit time): a 2-PR month clears it, a 1-PR month does
    not."""
    monkeypatch.setattr(paper_tables, "weights", lambda: {})
    rows = {r["period"]: r for r in paper_tables.usage_rows(
        granularity="month", window=WINDOW_MONTHS + ["2026-07"])}
    assert rows["2026-04"]["repos"] == 1      # two PRs >= MIN_PRS_MONTH
    assert rows["2026-07"]["repos"] == 0      # one PR misses the floor
    # quarterly floor stays 5: the same cells clear no quarter
    q = {r["period"]: r for r in paper_tables.usage_rows()}
    assert q["Q2-2026"]["repos"] == 0


def test_core_rows_monthly_carries_no_baseline_multiple(july_cells,
                                                        monkeypatch):
    """A single noisy baseline month is not the frozen Q1-2024 baseline
    estimate: monthly fig3 rows omit mult/sub_mult; quarterly rows keep
    them."""
    monkeypatch.setattr(paper_tables, "weights", lambda: {})
    monthly = paper_tables.core_rows(granularity="month",
                                     window=WINDOW_MONTHS + ["2026-07"])
    assert monthly and all("mult" not in r and "sub_mult" not in r
                           for r in monthly)
    by_per = {r["period"]: r for r in monthly}
    assert by_per["2026-04"]["repos"] == 1    # dev1+dev2 clear the core gate
    quarterly = paper_tables.core_rows()
    assert all("mult" in r and "sub_mult" in r for r in quarterly)
