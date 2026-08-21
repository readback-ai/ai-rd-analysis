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
