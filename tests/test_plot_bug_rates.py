"""Bug-rate figure (scripts/plot_bug_rates.py): the balanced-panel
per-PR and per-kLOC risk-window rates, pooled and median, drawn from the
same cuts the appendix table prints."""
import sys

sys.path.insert(0, "scripts")
import plot_bug_rates  # noqa: E402

from pipeline.studies import churn  # noqa: E402


def _cuts():
    out = {}
    for i, per in enumerate(churn.PERIODS):
        out[(per, "balanced")] = {
            "repos": 67, "bugs": 100, "pr_windows": 400.0,
            "kloc_windows": 120.0,
            "pooled_per_pr": 0.25 - 0.03 * i, "median_per_pr": 0.09,
            "pooled_per_kloc": 0.85 - 0.15 * i,
            "median_per_kloc": 0.45 - 0.1 * i}
        out[(per, "all")] = dict(out[(per, "balanced")], repos=130)
    return out


def test_collect_builds_both_panels_from_the_balanced_cuts(monkeypatch):
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        [], (list(churn.PERIODS), {"ai_share": {}, "label_users": set(),
                                   "held": 1, "selected": 1})))
    monkeypatch.setattr(churn, "exposure_cuts", lambda *_a: _cuts())
    t = plot_bug_rates.collect()
    assert t.panels() == ["per_pr", "per_kloc"]
    assert t.series_in("per_pr") == ["pooled", "median"]
    assert t.values("per_pr", "pooled")[0] == 0.25
    assert t.values("per_kloc", "median")[-1] == \
        _cuts()[(churn.PERIODS[-1], "balanced")]["median_per_kloc"]
    assert [p["x_label"] for p in t.points("per_pr", "pooled")] == \
        list(churn.PERIODS)


def test_panel_titles_carry_the_balanced_panel_size(monkeypatch):
    """The n changes with the selection (pilot 67; population larger),
    so the title states it rather than a caption."""
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        [], (list(churn.PERIODS), {"ai_share": {}, "label_users": set(),
                                   "held": 1, "selected": 1})))
    monkeypatch.setattr(churn, "exposure_cuts", lambda *_a: _cuts())
    t = plot_bug_rates.collect()
    assert "n=67" in t.label_of("per_pr")
    assert "balanced panel" in t.label_of("per_kloc")


def test_render_draws_two_broken_panels(monkeypatch):
    monkeypatch.setattr(churn, "exposure_rows", lambda g="quarter": (
        [], (list(churn.PERIODS), {"ai_share": {}, "label_users": set(),
                                   "held": 1, "selected": 1})))
    monkeypatch.setattr(churn, "exposure_cuts", lambda *_a: _cuts())
    fig = plot_bug_rates.render(plot_bug_rates.collect())
    axes = fig.get_axes()
    assert len(axes) == 4                     # 2 panels x (left, right)
    assert all(ax.get_ylim()[0] == 0 for ax in axes)
    assert fig._suptitle is None
    plot_bug_rates.plt.close(fig)
