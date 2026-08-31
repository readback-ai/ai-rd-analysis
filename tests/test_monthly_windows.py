"""analyze.month_window — the monthly figures' period resolver.

The window is FIGURE_WINDOW_START..`through` over censused months only
(frozen quarters + the incremental registry); the default `through` is
the frozen-quarter end so the default window equals figstyle.WINDOW.
"""
import pytest

from pipeline import analyze, figstyle
from pipeline.analyze import month_window


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
