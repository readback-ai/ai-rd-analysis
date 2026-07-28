"""The five population rules + overrides, exercised on synthetic sources."""
import json

import pytest

from pipeline import org_set


@pytest.fixture()
def world(tmp_path, monkeypatch):
    src = tmp_path / "sources"
    drv = tmp_path / "derived"
    src.mkdir()
    drv.mkdir()
    monkeypatch.setattr(org_set, "SRC", src)
    monkeypatch.setattr(org_set, "DRV", drv)

    (src / "candidates.tsv").write_text(
        "lab\tlfai\nbigco\tlfai\nwasher\tgh-topic\nsoloai\tgh-topic\n"
        "tiny\tgh-topic\nquiet\tlfai\n")
    (src / "epoch_org_map.tsv").write_text("Lab Inc\tlab\nUnmapped\t-\n")
    (src / "techcrunch_ai_orgs.tsv").write_text("startup\n")
    (src / "curated_orgs.tsv").write_text("")
    (src / "conglomerates.txt").write_text("bigco\n")
    (src / "org_overrides.tsv").write_text(
        "washer\texclude\tAI-washed topics\nsparse\tinclude-full\treal lab\n")

    def t5(ai_flags, stars=None):
        stars = stars or [5000] * len(ai_flags)
        return [{"name": f"r{i}", "stars": s, "ai": a}
                for i, (a, s) in enumerate(zip(ai_flags, stars))]
    rows = {
        "lab":    t5([False] * 5),          # dev-list identity, topic-sparse
        "bigco":  t5([True] * 5),           # conglomerate despite AI topics
        "washer": t5([True, True]),         # would pass, but excluded
        "soloai": t5([True, False, False]), # 1 AI flagship -> repo-scoped
        "tiny":   t5([True, True], stars=[400, 300]),   # fails quality
        "quiet":  t5([True, True]),         # fails evidence
        "startup": t5([False]),             # techcrunch + small stars: exempt
        "sparse": t5([False] * 5),          # include-full override
    }
    (drv / "top5_topics.jsonl").write_text(
        "\n".join(json.dumps({"org": o, "top5": v}) for o, v in rows.items()))
    (src / "candidates.tsv").write_text(
        (src / "candidates.tsv").read_text() + "sparse\tlfai\n")
    (drv / "org_scale.tsv").write_text("org\trepos\tflagship_stars\n")
    (drv / "ai_scan.tsv").write_text(
        "lab\t50\t0\tx\nbigco\t50\t0\tx\nwasher\t50\t0\tx\nsoloai\t50\t0\tx\n"
        "tiny\t50\t0\tx\nstartup\t50\t0\tx\nsparse\t50\t0\tx\n")
    (drv / "recheck_scan.tsv").write_text("")
    (drv / "branch_scan.tsv").write_text("")
    (drv / "census_org_evidence.json").write_text(json.dumps({"quiet": [1, 5000]}))
    return src, drv


def test_rules(world):
    pop = org_set.build()
    assert pop["lab"][:2] == ("full", "dev-list")          # R3 via Epoch transcription
    assert pop["bigco"][:2] == ("repo", "conglomerate")    # R5 declared umbrella
    assert "washer" not in pop                         # override exclude wins
    assert pop["soloai"][:2] == ("repo", "ai-flagship")    # single-product -> stratum
    assert "tiny" not in pop                           # R2 quality (not dev-listed)
    assert pop["startup"][0] == "full"                 # R2 exemption for dev lists
    assert "quiet" not in pop                          # R4: 1/5000 PRs, no rate pass
    assert pop["sparse"][:2] == ("full", "override")       # include-full asserts R3


def test_rate_branch_passes_evidence(world):
    src, drv = world
    (drv / "census_org_evidence.json").write_text(json.dumps({"quiet": [6, 5000]}))
    pop = org_set.build()
    assert "quiet" in pop                              # 6/5000 >= 0.1%


def test_top5_ai_recorded_independently_of_admission(world):
    """A dev-list org's measured concentration must still be visible."""
    pop = org_set.build()
    assert pop["lab"][2] == 0            # admitted dev-list, measured 0/5
    assert pop["bigco"][2] == 5          # conglomerate, measured 5/5


@pytest.fixture()
def evidence_world(tmp_path, monkeypatch):
    drv = tmp_path / "derived"
    drv.mkdir()
    monkeypatch.setattr(org_set, "DRV", drv)
    (drv / "ai_scan.tsv").write_text("")
    (drv / "recheck_scan.tsv").write_text("")
    (drv / "branch_scan.tsv").write_text("")
    (drv / "census_org_evidence.json").write_text("{}")
    return drv


def test_recheck_probes_take_max_not_sum(evidence_world):
    """Issue #6 (RED first): one PR can match several recheck probes (its
    branch AND its markers), so probe counts overlap and their sum is not
    a distinct-PR count — an org's recheck evidence is the max probe."""
    (evidence_world / "recheck_scan.tsv").write_text(
        "dbl\tclaude_br\t3\ndbl\tclaude_mk\t3\ndbl\ttotal_pr\t100\n")
    ev, _ = org_set.evidence()
    assert ev["dbl"] == 3


def test_branch_evidence_dedups_and_excludes_the_2024_control(
        evidence_world):
    """Issue #6 (RED first): branch_scan admission evidence must be a
    distinct-PR count — Q1-2024 is the deliberate false-positive control
    and must not admit anyone, and re-appended checkpoint rows must not
    count twice. (Quarters partition PRs by created date and prefixes are
    pairwise non-nested, so the keyed non-control cells sum exactly.)"""
    (evidence_world / "branch_scan.tsv").write_text(
        "ctrl\tQ1-2024\tclaude/\t4\n"
        "ctrl\tQ4-2025\tclaude/\t2\n"
        "ctrl\tQ1-2026\tcodex/\t1\n"
        "ctrl\tQ1-2026\tcodex/\t1\n")
    ev, _ = org_set.evidence()
    assert ev["ctrl"] == 3


def test_scoped_repos_includes_zero_repo_orgs(tmp_path, monkeypatch):
    """PR #13 review, P2 (RED first): a repo-scoped org with no manifest
    repos has an EMPTY universe — omitting it from the map makes every
    consumer fall back to org-wide (branch_scan would query org:, the
    precision read-filter would be disabled)."""
    drv = tmp_path / "derived"
    drv.mkdir()
    monkeypatch.setattr(org_set, "DRV", drv)
    (drv / "population.tsv").write_text(
        "bigco\trepo\tconglomerate\t0\nacme\tfull\tdev-list\t3\n")
    (drv / "population_repos.txt").write_text("acme/x\nother/y\n")
    assert org_set.scoped_repos() == {"bigco": []}
