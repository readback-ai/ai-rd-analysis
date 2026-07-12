"""Coverage gating in scripts/regenerate.py: waivers, gaps, corrupt cells."""
import sys

import pytest

sys.path.insert(0, "scripts")
import regenerate  # noqa: E402


@pytest.fixture(autouse=True)
def tmp_store(tmp_path, monkeypatch):
    monkeypatch.setenv("AIRD_DATA_DIR", str(tmp_path / "store"))
    monkeypatch.setattr(regenerate, "DRV", tmp_path / "derived")
    (tmp_path / "derived").mkdir()
    return tmp_path


def _cell(repo, rng, payload="[{}]"):
    from pipeline.ghx import cell_path
    p = cell_path("census-v2", repo, rng)
    p.write_text(payload)


def _manifest(tmp_path, repos):
    f = tmp_path / "repos.txt"
    f.write_text("\n".join(repos) + "\n")
    return f


Q2 = "2026-04-01..2026-06-30"


def test_full_quarter_cell_covers(tmp_path):
    for rng in ("2024-01-01..2024-03-31", "2025-10-01..2025-12-31",
                "2026-01-01..2026-03-31", Q2):
        _cell("o/r", rng)
    cov = regenerate.coverage_check(_manifest(tmp_path, ["o/r"]))
    assert cov["covered"] == 4


def test_partial_subwindow_does_not_cover(tmp_path):
    """A failed run's lone first sub-window must not count as coverage."""
    _cell("o/r", "2026-04-01..2026-04-09")
    with pytest.raises(SystemExit, match="coverage incomplete"):
        regenerate.coverage_check(_manifest(tmp_path, ["o/r"]))


def test_gapless_subwindows_cover_but_gappy_do_not(tmp_path):
    for rng in ("2024-01-01..2024-03-31", "2025-10-01..2025-12-31",
                "2026-01-01..2026-03-31"):
        _cell("o/r", rng)
    _cell("o/r", "2026-04-01..2026-05-15")
    _cell("o/r", "2026-05-16..2026-06-30")
    assert regenerate.coverage_check(_manifest(tmp_path, ["o/r"]))["covered"] == 4
    # now a repo with a hole in the middle of Q2
    _cell("o/x", "2026-04-01..2026-04-30")
    _cell("o/x", "2026-06-01..2026-06-30")
    with pytest.raises(SystemExit):
        regenerate.coverage_check(_manifest(tmp_path, ["o/x"]))


def test_corrupt_cell_is_not_coverage(tmp_path):
    _cell("o/r", Q2, payload='{"errors": [{"type": "RATE_LIMIT"}]}')
    with pytest.raises(SystemExit):
        regenerate.coverage_check(_manifest(tmp_path, ["o/r"]))


def test_inaccessible_repos_waived_and_excluded_from_collection(tmp_path):
    (regenerate.DRV / "inaccessible_repos.txt").write_text("o/dead\n")
    cov = regenerate.coverage_check(_manifest(tmp_path, ["o/dead"]))
    assert cov["waived"] == 4 and cov["covered"] == 0
    calls = []
    regenerate_run = regenerate.run
    regenerate.run = lambda *a: calls.append(a)
    try:
        regenerate.stage_c(_manifest(tmp_path, ["o/dead", "o/alive"]))
    finally:
        regenerate.run = regenerate_run
    collectable = (regenerate.DRV / "population_repos_collectable.txt").read_text().split()
    assert collectable == ["o/alive"]
