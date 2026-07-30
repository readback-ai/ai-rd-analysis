"""Shared fixtures: reset per-process memos so no test inherits state
populated under another test's monkeypatched cells, and keep the suite
off the network."""

import subprocess

import pytest


@pytest.fixture(autouse=True)
def _clear_fleet_memo():
    from pipeline.studies import productivity
    productivity.fleet_logins.cache_clear()
    yield
    productivity.fleet_logins.cache_clear()


@pytest.fixture(autouse=True)
def _clear_unsearchable_memo():
    from pipeline import census_direct
    census_direct.repo_unsearchable.cache_clear()
    yield
    census_direct.repo_unsearchable.cache_clear()


@pytest.fixture(autouse=True)
def _no_live_gh(monkeypatch):
    """No test may shell out to `gh`. Census failure paths classify a repo
    by asking GitHub search, and a fixture repo name like 'o/r' draws the
    same 422 a genuinely unsearchable repo does — so an unmocked call does
    not merely leak network access, it changes the collection route under
    the test. Tests that exercise a gh-backed path patch subprocess.run
    (or a higher seam) themselves, which overrides this."""
    real_run = subprocess.run

    def guard(cmd, *a, **k):
        argv = cmd if isinstance(cmd, (list, tuple)) else [cmd]
        if argv and str(argv[0]) == "gh":
            raise AssertionError(f"live gh call from a test: {argv[:3]}")
        return real_run(cmd, *a, **k)

    monkeypatch.setattr(subprocess, "run", guard)
