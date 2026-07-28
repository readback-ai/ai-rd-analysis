"""Shared fixtures: reset per-process memos so no test inherits state
populated under another test's monkeypatched cells."""

import pytest


@pytest.fixture(autouse=True)
def _clear_fleet_memo():
    from pipeline.studies import productivity
    productivity.fleet_logins.cache_clear()
    yield
    productivity.fleet_logins.cache_clear()
