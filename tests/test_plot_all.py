"""Batch figure generation (scripts/plot_all.py).

The driver's contract is that one broken figure must not cost the rest of
the run — the census pass is expensive and is shared by every figure in
it.
"""
import sys

import pytest

sys.path.insert(0, "scripts")
import plot_all  # noqa: E402

from pipeline import figdata  # noqa: E402
from pipeline.figstyle import plt  # noqa: E402


def _fig(_table):
    return plt.figure()


def _table(name):
    t = figdata.Table(name)
    t.add("p", "s", 0, 1.0)
    return t


def test_study_systemexit_does_not_abort_the_batch(tmp_path, monkeypatch,
                                                   capsys):
    """A study that bails with SystemExit — review_action raises it for a
    missing or stale selection manifest, which is Figure 8's normal state
    between redraws — must not skip the figures queued behind it."""
    monkeypatch.setattr(figdata, "DATA_DIR", tmp_path)

    def boom():
        raise SystemExit("no eq selection manifest — run --pull first")

    monkeypatch.setattr(plot_all, "FIGURES", [
        (str(tmp_path / "broken.png"), boom, _fig),
        (str(tmp_path / "later.png"), lambda: _table("later"), _fig),
    ])

    with pytest.raises(SystemExit) as exc:
        plot_all.main([])

    assert "broken" in str(exc.value)
    assert (tmp_path / "later.png").exists(), \
        "figure queued after the failing one was skipped"
    assert "FAILED broken" in capsys.readouterr().out


def test_monthly_stems_are_unique_and_never_clobber(monkeypatch):
    """Every *_monthly variant must claim its own PNG and CSV stem —
    figdata keys the committed table by the output stem, so a collision
    would silently overwrite a quarterly figure's data."""
    monkeypatch.setattr(plot_all, "month_window",
                        lambda through=None: ["2025-10"])
    stems = [s for s, _c, _r in (plot_all.FIGURES
                                 + plot_all.monthly_figures())]
    assert len(stems) == len(set(stems))
    monthly = plot_all.monthly_figures()
    assert all(s.endswith("_monthly.png") for s, _c, _r in monthly)


def test_monthly_prints_the_quarterly_skips(monkeypatch, capsys):
    """The quarterly-only figures have no monthly twin (responsiveness:
    frozen quarter-keyed manifest draw; fleet_vs_nonadopters: moved to
    quarters); --monthly must declare each gap instead of leaving it
    silent — the report.py '[quarterly]' precedent."""
    monkeypatch.setattr(plot_all, "FIGURES", [])
    monkeypatch.setattr(plot_all, "monthly_figures",
                        lambda through=None: [])
    plot_all.main(["--monthly"])
    out = capsys.readouterr().out
    assert "skipped responsiveness_by_ai_monthly [quarterly]" in out
    assert "skipped fleet_vs_nonadopters_monthly [quarterly]" in out


def test_through_implies_monthly_and_forwards_the_month(monkeypatch,
                                                        capsys):
    """--through YYYY-MM renders the monthly set without a separate
    --monthly flag and hands the month to the window resolution."""
    seen = []

    def fake_monthly(through=None):
        seen.append(through)
        return []

    monkeypatch.setattr(plot_all, "FIGURES", [])
    monkeypatch.setattr(plot_all, "monthly_figures", fake_monthly)
    monkeypatch.setattr(plot_all, "month_window", lambda t=None: [t])
    plot_all.main(["--through", "2026-08"])
    assert seen == ["2026-08"]
    assert "[quarterly]" in capsys.readouterr().out


def test_batch_closes_each_figure_after_saving(tmp_path, monkeypatch):
    """plot_all discarded each rendered figure without closing it, so
    pyplot retained every canvas — the 25-figure run tripped Matplotlib's
    'More than 20 figures have been opened' warning and held them all
    until process exit."""
    monkeypatch.setattr(figdata, "DATA_DIR", tmp_path)
    plt.close("all")
    monkeypatch.setattr(plot_all, "FIGURES", [
        (str(tmp_path / "a.png"), lambda: _table("a"), _fig),
        (str(tmp_path / "b.png"), lambda: _table("b"), _fig),
    ])
    plot_all.main([])
    assert plt.get_fignums() == []


def test_batch_closes_figures_on_failed_saves_too(tmp_path, monkeypatch):
    """plot_all closed each figure only after save() succeeded, so the
    keep-going path skipped the close: 21 failed saves left 21 figures
    open and tripped Matplotlib's more-than-20-figures warning. The
    close belongs in a finally so a failing figure also releases its
    canvas."""
    monkeypatch.setattr(figdata, "DATA_DIR", tmp_path)
    plt.close("all")

    def boom_save(fig, out, formats):
        raise OSError("disk full")

    monkeypatch.setattr(plot_all, "save", boom_save)
    monkeypatch.setattr(plot_all, "FIGURES", [
        (str(tmp_path / "a.png"), lambda: _table("a"), _fig),
        (str(tmp_path / "b.png"), lambda: _table("b"), _fig),
    ])
    with pytest.raises(SystemExit):
        plot_all.main([])
    assert plt.get_fignums() == []


def test_keyboard_interrupt_still_stops_the_batch(tmp_path, monkeypatch):
    """Keeping going applies to figure failures, not to the operator
    interrupting the run."""
    monkeypatch.setattr(figdata, "DATA_DIR", tmp_path)

    def interrupted():
        raise KeyboardInterrupt

    monkeypatch.setattr(plot_all, "FIGURES", [
        (str(tmp_path / "a.png"), interrupted, _fig),
        (str(tmp_path / "b.png"), lambda: _table("b"), _fig),
    ])

    with pytest.raises(KeyboardInterrupt):
        plot_all.main([])
    assert not (tmp_path / "b.png").exists()
