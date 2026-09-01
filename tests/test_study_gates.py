"""External review P1s (RED first): studies must honor the w8 maturity
gate and the AS_OF migration — analyze gating alone is not 'every paper
number obeys the frozen rule'."""

import json
import re

import pytest

from pipeline import detect
from pipeline.detect import MARKERS, classify_pr

# The data stamp advances with every re-pull (METHODS §1c), so a fixture's
# maturity must never ride on the module constant's current value. Pin it
# for the whole module; tests observing a different stamp re-pin their own.
PINNED_AS_OF = "2026-08-01T00:00:00Z"


@pytest.fixture(autouse=True)
def pin_as_of(monkeypatch):
    monkeypatch.setattr(detect, "AS_OF", PINNED_AS_OF)


def _pr(created, merged=None, num=1, reviews=(), merged_by="bob"):
    return {"number": num, "createdAt": created, "mergedAt": merged,
            "additions": 100, "deletions": 0,
            "author": {"login": "alice", "__typename": "User"},
            "mergedBy": ({"login": merged_by, "__typename": "User"}
                         if merged else None),
            "authorAssociation": "MEMBER",
            "commits": {"nodes": []}, "reviews": {"nodes": list(reviews)}}


IMMATURE = _pr("2026-06-20T00:00:00Z", merged="2026-06-25T00:00:00Z")
MATURE = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z", num=2)


def test_slices_skip_immature_outcomes(monkeypatch, capsys):
    """Reviewer repro: a synthetic immature PR was counted as merged /
    self-merged by slices while analyze skipped it."""
    from pipeline import frame
    from pipeline.studies import slices
    cells = {("o/r", "2026-04-01..2026-06-30"): [IMMATURE, MATURE] * 3}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(slices, "MIN_PRS", 1)
    rates = slices.repo_rates()
    r = rates[("o/r", "Q2-2026")]
    assert r["merged"] == 1.0          # only the mature PR in the denominator
    assert r["self_merged"] == 0.0     # mature PR was other-merged


def test_fates_maturity_and_events_follow_as_of(monkeypatch):
    """fates used CUTOFF for maturity AND rejected in-horizon events past
    it — bumping AS_OF must finalize Q2 rows."""
    from pipeline.studies import fates
    monkeypatch.setattr(detect, "AS_OF", "2026-09-01T00:00:00Z")
    spill = _pr("2026-06-20T00:00:00Z", merged="2026-07-10T00:00:00Z")
    out = fates.classify_at(spill, weeks=8)
    assert out == "merged"             # mature under AS_OF; event in horizon


def test_attention_counts_w8_windowed_comments_past_cutoff(monkeypatch):
    from pipeline.studies import attention
    rev = {"author": {"login": "bob", "__typename": "User"},
           "state": "COMMENTED", "comments": {"totalCount": 4},
           "submittedAt": "2026-07-05T00:00:00Z"}     # past CUTOFF, in w8
    pr = _pr("2026-06-20T00:00:00Z", merged="2026-06-28T00:00:00Z",
             reviews=[rev])
    assert attention.human_comment_count(pr) == 4


def _rev(login, n, at="2026-06-25T00:00:00Z"):
    return {"author": {"login": login, "__typename": "User"},
            "state": "COMMENTED", "comments": {"totalCount": n},
            "submittedAt": at}


def test_comments_capped_per_reviewer_per_pr():
    """One reviewer's exhaustive pass over a single PR is one act of
    review, not N units of attention: a documentation copy-edit left 355
    inline comments on one PR (the maximum of 112k reviewer-PR pairs,
    against a median of 2) and carried a whole month's fleet series.
    Cap per (reviewer, PR), mirroring the per-PR LOC cap."""
    from pipeline.studies import attention
    pr = _pr("2026-06-01T00:00:00Z", merged="2026-06-10T00:00:00Z",
             reviews=[_rev("writer", 355)])
    assert attention.human_comment_count(pr) == attention.COMMENT_CAP


def test_comment_cap_is_per_reviewer_not_per_pr():
    """The cap must not punish BROADLY reviewed PRs: several reviewers
    under the cap each count in full, so genuine multi-reviewer scrutiny
    survives while one exhaustive annotator does not."""
    from pipeline.studies import attention
    pr = _pr("2026-06-01T00:00:00Z", merged="2026-06-10T00:00:00Z",
             reviews=[_rev("a", 15), _rev("b", 15), _rev("c", 15)])
    assert attention.human_comment_count(pr) == 45


def test_comment_cap_applies_to_a_reviewers_total_across_reviews():
    """A reviewer who splits the same pass over several review objects
    must not evade the cap."""
    from pipeline.studies import attention
    pr = _pr("2026-06-01T00:00:00Z", merged="2026-06-10T00:00:00Z",
             reviews=[_rev("writer", 18), _rev("writer", 18),
                      _rev("other", 3)])
    assert attention.human_comment_count(pr) == attention.COMMENT_CAP + 3


def test_q2_provisionality_note_clears_on_finalization(monkeypatch):
    """Codex review P1: report captions asserted Q2 was 'w8-deflated for
    May/June PRs' unconditionally, so a finalized quarter would keep
    publishing the caveat. Derive it from the data stamp."""
    from pipeline.studies import productivity
    monkeypatch.setattr(detect, "AS_OF", "2026-08-25T00:00:00Z")
    assert "w8-deflated" in productivity.q2_provisionality_note()
    monkeypatch.setattr(detect, "AS_OF", "2026-08-26T00:00:00Z")
    assert productivity.q2_provisionality_note() == ""


def test_figure3_caption_drops_the_q2_caveat_on_finalization(monkeypatch):
    """Codex review P2: paper_tables.core() hard-coded '(Q2 provisional)',
    so both the quarterly and monthly regenerated reports would keep
    labelling Q2 provisional after the finalization re-pull."""
    from pipeline.studies import paper_tables
    monkeypatch.setattr(detect, "AS_OF", "2026-08-25T00:00:00Z")
    assert "(Q2 provisional)" in paper_tables.core_caption()
    monkeypatch.setattr(detect, "AS_OF", "2026-08-26T00:00:00Z")
    caption = paper_tables.core_caption()
    assert "provisional" not in caption
    assert "merged = w8 rule" in caption      # the rest of it survives


def test_event_study_mature_max_follows_as_of(monkeypatch):
    from pipeline.studies import event_study
    # Pin BOTH observation points: the contract is that maturity follows
    # AS_OF, so neither assertion may depend on the module constant's
    # current value (it advances with every re-pull, METHODS §1c).
    monkeypatch.setattr(detect, "AS_OF", "2026-06-30T23:59:59Z")
    assert event_study.mature_max() == event_study.WINDOW.index("2026-04")
    monkeypatch.setattr(detect, "AS_OF", "2026-09-05T00:00:00Z")
    assert event_study.mature_max() == event_study.WINDOW.index("2026-06")


def test_paper_tables_merged_columns_mature_only(monkeypatch):
    from pipeline.studies import paper_tables
    # 6 IMMATURE AI-involved merged PRs + 6 mature non-AI merged PRs:
    # without the gate mrg_pr = 6/12 = 0.5; with it, 0/6 = 0.0
    prs = []
    for i in range(6):
        p = _pr("2026-06-20T00:00:00Z", merged="2026-06-25T00:00:00Z",
                num=i)
        p["headRefName"] = "codex/x"
        prs.append(p)
    for i in range(6, 12):
        prs.append(_pr("2026-04-01T00:00:00Z",
                       merged="2026-04-05T00:00:00Z", num=i))
    cells = {("o/r", "2026-04-01..2026-06-30"): prs}
    from pipeline import frame
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(paper_tables, "weights", lambda: {"o/r": 1.0})
    rows = paper_tables.usage_rows()
    q2 = [r for r in rows if r["period"] == "Q2-2026"][0]
    assert q2["mrg_pr"][0] == 0.0      # immature AI merges excluded
    assert q2["repos"] == 1


def test_review_action_sample_is_versioned_for_the_mature_frame():
    """Review round 5 P1 (RED first): the PPS sample must be redrawn under
    the mature-gated eligibility frame — inclusion probabilities from the
    new frame do not apply to records drawn under the old one. A versioned
    sample file forces the clean redraw (old draws never union in via
    `done`)."""
    from pipeline.studies import review_action
    assert "v2" in review_action.SAMPLE.name
    assert review_action.OLD_SAMPLE.name == "review_action_sample.jsonl"


def test_channels_gate_on_maturity():
    """Review round 5 P1 (RED first): channel SHARES are not covered by
    the deflation argument — immature review/self-merge classifications
    move in either direction as events arrive. Immature merges carry no
    channel."""
    from pipeline.studies.productivity import merged_channel
    imm = classify_pr(IMMATURE, MARKERS)
    assert merged_channel(imm) is None
    mat = classify_pr(MATURE, MARKERS)
    assert merged_channel(mat) == "otherUnrev"      # merged by bob, no review


def test_event_study_cohort_caps(monkeypatch):
    """Review round 5 P1 (RED first): calendar balance is a property of
    the FIXED window (cap len(WINDOW)-3 regardless of AS_OF); the fully
    mature panel additionally needs t0 <= mature_max()-2. At a September
    AS_OF the old code admitted May/June adopters whose t+2 lies outside
    the window."""
    from pipeline.studies import event_study as es
    assert es.balanced_cap() == len(es.WINDOW) - 3
    assert es.mature_cap() == es.mature_max() - 2
    monkeypatch.setattr(detect, "AS_OF", "2026-09-05T00:00:00Z")
    assert es.balanced_cap() == len(es.WINDOW) - 3   # unchanged by AS_OF
    assert es.mature_cap() == es.WINDOW.index("2026-06") - 2


def _rec(repo, num, complete=True, ncommits=5):
    d = {"per": "Q1-2026", "repo": repo, "num": num, "loc": 100,
         "first_review": "2026-01-02T00:00:00Z", "author": "alice",
         "ai": False, "ins": True, "commits": [{}] * ncommits}
    if complete:
        d["commits_total"] = ncommits
        d["commits_complete"] = True
    return d


def _item(repo, num, per="Q1-2026", loc=100):
    return (repo, num, loc, "2026-01-02T00:00:00Z", "alice", False, True)


def test_pps_manifest_replaces_sample_on_frame_change(tmp_path, monkeypatch):
    """Review round 6 P1 (RED first): a frame change (AS_OF bump,
    eligibility, weights) must atomically REPLACE the selection — never
    union two draws. Reproduces the reviewer's A+B case."""
    import json as _json
    from pipeline.studies import review_action as ra
    monkeypatch.setattr(ra, "SAMPLE", tmp_path / "s_v2.jsonl")
    monkeypatch.setattr(ra, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(ra, "OLD_SAMPLE", tmp_path / "s_v1.jsonl")
    cache = {("o/a", 1): _rec("o/a", 1), ("o/b", 2): _rec("o/b", 2)}
    pool_a = {"Q1-2026": [_item("o/a", 1)]}
    m1, fresh1 = ra.ensure_manifest(pool_a)
    assert fresh1
    done = ra.rebuild_sample(m1, cache, pool_a)
    assert done == {("o/a", 1)}
    pool_b = {"Q1-2026": [_item("o/b", 2)]}      # frame changed
    m2, fresh2 = ra.ensure_manifest(pool_b)
    assert fresh2 and m2["fingerprint"] != m1["fingerprint"]
    done = ra.rebuild_sample(m2, cache, pool_b)
    assert done == {("o/b", 2)}                  # A is GONE, not unioned
    kept = [_json.loads(ln) for ln in
            (tmp_path / "s_v2.jsonl").read_text().splitlines()]
    assert [(d["repo"], d["num"]) for d in kept] == [["o/b", 2]] or \
           [(d["repo"], d["num"]) for d in kept] == [("o/b", 2)]
    # same frame again: manifest reused, not redrawn
    m3, fresh3 = ra.ensure_manifest(pool_b)
    assert not fresh3 and m3["fingerprint"] == m2["fingerprint"]


def test_hydration_reuse_requires_completeness_metadata():
    """Review round 6 P1 (RED first): legacy records without completeness
    metadata (476 in the drawn v2 file) are NOT reusable — a pre-fix
    partial response (20 of 50 commits) has no page-boundary signature."""
    from pipeline.studies import review_action as ra
    assert ra._complete(_rec("o/a", 1))
    legacy = _rec("o/a", 1, complete=False, ncommits=20)
    assert not ra._complete(legacy)
    assert not ra._complete(_rec("o/a", 1, complete=False, ncommits=100))


def test_pps_coverage_gaps_fail_hard(tmp_path, monkeypatch):
    """Review round 6 P1 (RED first): a selected PR with no complete
    record must fail pull/compute nonzero — a transient API failure can
    never silently publish a non-probability subset."""
    import pytest
    from pipeline.studies import review_action as ra
    manifest = {"fingerprint": "f", "selected":
                {"Q1-2026": [list(_item("o/a", 1)), list(_item("o/b", 2))]}}
    records = {("o/a", 1): _rec("o/a", 1)}
    gaps = ra.coverage_gaps(manifest, records)
    assert gaps == [("o/b", 2)]
    with pytest.raises(SystemExit):
        ra.require_complete_sample(manifest, records)
    records[("o/b", 2)] = _rec("o/b", 2, complete=False)   # incomplete
    assert ra.coverage_gaps(manifest, records) == [("o/b", 2)]


def test_event_study_labels_are_dynamic(monkeypatch):
    """Review round 6 P2 (RED first): table labels must follow the caps."""
    from pipeline.studies import event_study as es
    monkeypatch.setattr(detect, "AS_OF", "2026-09-05T00:00:00Z")
    assert "2026-06" in es.mature_month_label()
    assert es.mature_cap_label().endswith(es.WINDOW[es.mature_cap()])



def test_rebuild_rebinds_descriptive_fields_from_current_pool(tmp_path,
                                                              monkeypatch):
    """Review round 7 P1 (RED first): on a fingerprint match the selected
    KEYS survive, but descriptive fields (first_review, ai, ins) must be
    rebound from the CURRENT pool — a marker revision flips `ai` without
    changing eligibility or LOC, and the old value must not survive."""
    import json as _json
    from pipeline.studies import review_action as ra
    monkeypatch.setattr(ra, "SAMPLE", tmp_path / "s_v2.jsonl")
    monkeypatch.setattr(ra, "MANIFEST", tmp_path / "manifest.json")
    monkeypatch.setattr(ra, "OLD_SAMPLE", tmp_path / "s_v1.jsonl")
    old_rec = _rec("o/a", 1)
    old_rec["ai"] = False
    old_rec["first_review"] = "2026-01-02T00:00:00Z"
    cache = {("o/a", 1): old_rec}
    # current pool: same key/loc (fingerprint unchanged) but ai flipped
    # and the first-review anchor corrected
    item = ("o/a", 1, 100, "2026-01-03T00:00:00Z", "alice", True, True)
    pool = {"Q1-2026": [item]}
    m, _ = ra.ensure_manifest(pool)
    ra.rebuild_sample(m, cache, pool)
    (d,) = [_json.loads(ln) for ln in
            (tmp_path / "s_v2.jsonl").read_text().splitlines()]
    assert d["ai"] is True
    assert d["first_review"] == "2026-01-03T00:00:00Z"


def test_manifest_payload_validated_against_deterministic_draw(tmp_path,
                                                               monkeypatch):
    """Review round 7 P2 (RED first): a fingerprint-matching manifest with
    an empty/truncated selection must be repaired, not reused vacuously."""
    import json as _json
    from pipeline.studies import review_action as ra
    monkeypatch.setattr(ra, "MANIFEST", tmp_path / "manifest.json")
    pool = {"Q1-2026": [_item("o/a", 1)]}
    m1, _ = ra.ensure_manifest(pool)
    assert m1["selected"]["Q1-2026"]
    # truncate the payload but keep the fingerprint
    (tmp_path / "manifest.json").write_text(_json.dumps(
        {"fingerprint": m1["fingerprint"], "selected": {"Q1-2026": []}}))
    m2, fresh = ra.ensure_manifest(pool)
    assert m2["selected"] == m1["selected"]      # repaired to the true draw


def test_compute_side_selection_validation(tmp_path, monkeypatch):
    """Review round 8 P1 (RED first): the guard compute() calls
    (require_selection_matches) must reject a fingerprint-matching
    manifest whose selection was truncated — that case previously
    produced an EMPTY responsiveness table through compute(). (This test
    exercises the guard directly; compute() wires it after the
    fingerprint check.)"""
    import pytest
    from pipeline.studies import review_action as ra
    pool = {"Q1-2026": [_item("o/a", 1)]}
    good = {"fingerprint": ra.frame_fingerprint(ra._pool_items(pool)),
            "selected": ra._selection_of(pool)}
    ra.require_selection_matches(good, pool)          # passes silently
    truncated = {"fingerprint": good["fingerprint"],
                 "selected": {"Q1-2026": []}}
    with pytest.raises(SystemExit, match="rerun --pull"):
        ra.require_selection_matches(truncated, pool)


def test_draw_is_canonical_under_encounter_order(monkeypatch):
    """Review round 9 P1 (RED first): pull builds the pool in PERIODS
    dict order, compute in census encounter order — identical FRAMES must
    yield identical draws regardless of period or item order, and empty
    periods must normalize away (the fingerprint already sorts; the draw
    must too)."""
    from pipeline.studies import review_action as ra
    a, b, c = _item("o/a", 1), _item("o/b", 2, loc=300), _item("o/c", 3)
    fwd = {"Q1-2024": [a, b, c], "Q2-2026": [b, a], "Q4-2025": []}
    rev = {"Q2-2026": [a, b], "Q1-2024": [c, b, a]}   # no empty key at all
    d1, d2 = ra.draw(fwd), ra.draw(rev)
    assert d1 == d2
    assert "Q4-2025" not in d1                        # empty normalized
    assert ra._selection_of(fwd) == ra._selection_of(rev)


def test_definitive_nonresponse_tombstones(tmp_path, monkeypatch):
    """Round-11 (RED first): a SUCCESSFUL batch response with an explicit
    null pullRequest (repo privatized/deleted or PRs disabled after the
    census — measured: openai/plugins disabled PRs 2026-07-14) is
    DEFINITIVE nonresponse, not a transient failure. It tombstones, the
    tombstone resolves coverage (documented nonresponse, not missing
    work), is never treated as data, and repair retries it."""
    from pipeline.studies import review_action as ra
    # definitive miss detection
    assert ra._definitive_miss(None)                      # repo-level null
    assert ra._definitive_miss({"pullRequest": None})     # PR-level null
    assert not ra._definitive_miss({"pullRequest": {"commits": {}}})
    # tombstones: not complete, suspect (repair retries), resolve coverage
    tomb = ra._tombstone("Q1-2026", ("o/a", 1, 100,
                                     "2026-01-02T00:00:00Z", "alice",
                                     False, True))
    assert tomb["unretrievable"] is True
    assert not ra._complete(tomb)
    assert ra._suspect(tomb)
    manifest = {"fingerprint": "f", "selected":
                {"Q1-2026": [["o/a", 1, 100], ["o/b", 2, 100]]}}
    records = {("o/a", 1): tomb, ("o/b", 2): _rec("o/b", 2)}
    assert ra.coverage_gaps(manifest, records) == []
    ra.require_complete_sample(manifest, records)         # passes
    # a tombstone never counts as analyzable data
    assert ra.analyzable_keys(manifest, records) == [("o/b", 2)]


_PANEL_SCRIPT = r"""
import sys
from pipeline import frame
from pipeline.studies import slices

repos = [f"org/repo{i}" for i in range(20)]
RANGES = ["2024-01-01..2024-03-31", "2025-10-01..2025-12-31",
          "2026-01-01..2026-03-31", "2026-04-01..2026-06-30"]
cells = {}
for i, repo in enumerate(repos):
    for rng in RANGES:
        prs = []
        for j in range(20):
            p = {"number": j, "createdAt": rng[:10] + "T00:00:00Z",
                 "mergedAt": None, "additions": 100, "deletions": 0,
                 "author": {"login": f"u{i}", "__typename": "User"},
                 "mergedBy": None, "authorAssociation": "MEMBER",
                 "commits": {"nodes": []}, "reviews": {"nodes": []}}
            if j < i:                       # repo i: ai rate i/20, all distinct
                p["headRefName"] = "codex/x"
            prs.append(p)
        cells[(repo, rng)] = prs
frame.load_cells = lambda: cells
frame.population_repos = lambda: set(repos)
slices.MIN_PRS = 1
slices.weights = lambda: {r: 1.0 for r in repos}
slices.balanced_panel()
"""


def test_balanced_panel_ci_reproducible_across_hash_seeds():
    """Gate finding (2026-07-23, study-frame refactor verification): the
    balanced-panel bootstrap CIs drifted between otherwise-identical runs
    while every other section was byte-stable. balanced_panel iterated the
    `panel` SET when building the bootstrap pairs, so the pair order fed
    to the seeded RNG depended on PYTHONHASHSEED — violating frozen rule
    1d.7 ('seeded everything': reruns reproduce identical CIs)."""
    import os
    import subprocess
    import sys

    def run(seed):
        env = {**os.environ, "PYTHONHASHSEED": str(seed),
               "PYTHONPATH": "src"}
        r = subprocess.run([sys.executable, "-c", _PANEL_SCRIPT],
                           env=env, capture_output=True, text=True)
        assert r.returncode == 0, r.stderr
        assert "panel ai_involved" in r.stdout
        return r.stdout

    assert run(1) == run(2)


# ---- issue #2 resolution (2026-07-23): AI-contrast review-behavior ----
# outputs (Figure 6 by-AI, Figure 7, Figure 8, fates' AI/nonAI cohorts)
# share profile 'all' + fleet exclusion — agent-authored (layer-B) PRs
# count in the AI series; channels() aligns with review_mix on 'author'.

_REV = {"author": {"login": "bob", "__typename": "User"},
        "state": "COMMENTED", "comments": {"totalCount": 1},
        "submittedAt": "2026-04-02T00:00:00Z"}


def _agent_pr(num=1):
    p = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
            num=num, reviews=[dict(_REV)])
    p["author"] = {"login": "copilot-swe-agent[bot]", "__typename": "Bot"}
    return p


def test_fates_ai_cohort_includes_agent_prs_and_excludes_fleet(
        monkeypatch, capsys):
    """Issue #2 (RED first): an agent-authored PR must count in fates'
    AI cohort; a fleet-operator-authored PR must not count anywhere."""
    from pipeline import frame
    from pipeline.studies import fates, productivity
    fleet_pr = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
                   num=2)
    fleet_pr["author"] = {"login": "fleeter", "__typename": "User"}
    human = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
                num=3)
    cells = {("o/r", "2026-04-01..2026-06-30"):
             [_agent_pr(), fleet_pr, human]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: {"fleeter"})
    monkeypatch.setattr(fates, "MIN_N", 1)   # cohort membership, not the floor
    fates.fates_at(8)
    out = capsys.readouterr().out
    rows = {ln.split()[1]: int(ln.split()[2]) for ln in out.splitlines()
            if ln.startswith("Q2-2026")}
    assert rows.get("AI") == 1          # the agent PR
    assert rows.get("all") == 2         # agent + human; fleeter excluded
    assert "ext" not in rows            # agent PR not a human external


def test_review_mix_ai_cut_includes_agent_prs_role_cut_does_not(
        monkeypatch):
    """Issue #2 (RED first): Figure 6's by-AI slices run on 'all' (agent
    PRs in the ai slice); the role (ins/ext) cut stays 'author'."""
    from pipeline import frame
    from pipeline.studies import productivity
    human = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
                num=2, reviews=[dict(_REV)])
    cells = {("o/r", "2026-04-01..2026-06-30"): [_agent_pr(), human]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: set())
    ai_rows = productivity.review_mix(by="ai")
    assert ai_rows[("Q2-2026", "ai")]["n"] == 1
    assert ai_rows[("Q2-2026", "nonai")]["n"] == 1
    role_rows = productivity.review_mix()
    assert role_rows[("Q2-2026", "ins")]["n"] == 1      # human only
    assert ("Q2-2026", "ext") not in role_rows          # agent PR absent


def test_channels_align_with_review_mix_author_profile(monkeypatch,
                                                       capsys):
    """Issue #2 (RED first): channels() and review_mix are two views of
    the approval-channel estimand — both run on 'author', so a
    user-typed-bot pipeline's LOC no longer enters the channel shares."""
    from pipeline import frame
    from pipeline.studies import productivity
    bot = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
              num=1, merged_by="foo-bot")
    bot["author"] = {"login": "foo-bot", "__typename": "User"}
    cells = {("o/r", "2026-04-01..2026-06-30"): [bot, MATURE]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    productivity.channels()
    q2 = [ln for ln in capsys.readouterr().out.splitlines()
          if ln.startswith("Q2-2026")][0]
    # only MATURE (other-merged, unreviewed) remains: otherUnrev 100%
    assert q2.rstrip().endswith("100.0%")
    assert " 50.0%" not in q2           # bot selfUnrev LOC excluded


def test_responsiveness_frame_includes_agent_prs(monkeypatch):
    """Issue #2 (RED first): Figure 8's sampling frame is the reviewed
    merged population INCLUDING agent-authored PRs (fleet handled by
    domain estimation downstream)."""
    from pipeline import frame
    from pipeline.studies import review_action as ra
    cells = {("o/r", "2026-04-01..2026-06-30"): [_agent_pr()]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    pool = ra.eligible()
    assert [(r, n) for r, n, *_ in pool["Q2-2026"]] == [("o/r", 1)]


def test_attention_ai_slice_includes_agent_prs(monkeypatch):
    """Pins the Figure 7 side of issue #2: attention_by_ai already ran on
    the full population — agent-authored PRs stay in the ai slice."""
    from pipeline import frame
    from pipeline.studies import attention, productivity
    cells = {("o/r", "2026-04-01..2026-06-30"): [_agent_pr()]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: set())
    rows = attention.attention_by_ai()
    assert rows[("Q2-2026", "ai")]["n"] == 1


def test_author_edits_after_credits_agent_authored_prs():
    """Issue #2 rollout bug (RED first): census stores a Bot PR author
    WITHOUT the [bot] suffix (author 'devin-ai-integration') while commit
    authors/committers carry it ('devin-ai-integration[bot]'), so an
    agent's own post-ask commits never matched the PR author and the
    bot-committer exclusion (written for the human estimand) discarded
    them anyway — agent responsiveness was structurally forced to zero.
    The PR's OWN bot must count; other bots stay excluded."""
    from pipeline.studies.review_action import _author_edits_after
    def mk(login, date):
        return {"commit": {
            "additions": 50, "deletions": 0, "committedDate": date,
            "committer": {"user": {"login": login}, "email": "x@y"},
            "authors": {"nodes": [{"user": {"login": login}}]}}}
    d = {"author": "devin-ai-integration", "loc": 100,
         "commits": [mk("devin-ai-integration[bot]", "2026-01-05T00:00:00Z"),
                     mk("some-ci-bot", "2026-01-06T00:00:00Z")]}
    post, _total = _author_edits_after(d, "2026-01-01T00:00:00Z")
    assert post == 50          # agent's own commit counts; CI bot's does not


def _commit(date, add, login="alice"):
    return {"commit": {"additions": add, "deletions": 0,
                       "committedDate": date,
                       "committer": {"user": {"login": login},
                                     "email": "a@x"},
                       "authors": {"nodes": [{"user": {"login": login}}]}}}


def test_truncated_record_measured_against_its_own_commits(monkeypatch):
    """250-cap decision (RED first, 2026-07-26): GitHub serves at most 250
    commits per PR (measured: all 30 records claiming more retrieved exactly
    250, none anywhere exceeds it). The post-ask numerator therefore covers
    only those 250, while `max(total, d["loc"])` floored the DENOMINATOR with
    the census LOC of the whole PR — a 250-commit numerator over a full-PR
    denominator, biasing post-ask LOC share down on the largest PRs. For a
    truncated record, measure the first 250 commits against the LOC of those
    same commits."""
    from pipeline.studies.review_action import _author_edits_after
    d = {"author": "alice", "loc": 20_000,          # census LOC, WHOLE PR
         "commits": [_commit("2026-01-05T00:00:00Z", 400),    # post-ask
                     _commit("2025-12-01T00:00:00Z", 600)],   # pre-ask
         "commits_total": 250, "commits_api_total": 2391,
         "commits_complete": True}
    assert _author_edits_after(d, "2026-01-01T00:00:00Z") == (400, 1000)


def test_complete_record_keeps_the_census_loc_floor():
    """The other half: where commit data is COMPLETE the census LOC stays a
    floor on the denominator (a PR's diff can exceed the sum of the commit
    LOC the API reports). Only truncation removes the floor."""
    from pipeline.studies.review_action import _author_edits_after
    d = {"author": "alice", "loc": 20_000,
         "commits": [_commit("2026-01-05T00:00:00Z", 400),
                     _commit("2025-12-01T00:00:00Z", 600)],
         "commits_total": 2, "commits_api_total": 2,
         "commits_complete": True}
    assert _author_edits_after(d, "2026-01-01T00:00:00Z") == (400, 20_000)


def test_fates_suppresses_cohorts_below_the_floor(monkeypatch, capsys):
    """Review finding 6, resolved 2026-07-26: a 1-PR cohort printed
    percentages beside 63k-PR cohorts (`Q1-2024 AI 1 0.0% 0.0% 100.0%`).
    Every comparable table has a floor (review_action n<20, slices MIN_PRS).
    Suppressed cohorts are LISTED, not silently dropped."""
    from pipeline import frame
    from pipeline.studies import fates, productivity
    monkeypatch.setattr(frame, "load_cells", _polluted_cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: set())
    monkeypatch.setattr(fates, "MIN_N", 2)
    fates.fates_at(8)
    out = capsys.readouterr().out
    rows = {ln.split()[1] for ln in out.splitlines()
            if ln.startswith("Q2-2026")}
    assert "AI" not in rows            # the single agent PR: below the floor
    assert "all" in rows              # n=2, at the floor
    assert "AI n=1" in out            # ...but reported as suppressed


def test_eq_draw_canonical_capped_and_design_tagged_fingerprint(
        monkeypatch):
    """Issue #2 estimator decision (RED first): per-PR rate estimands
    move to an equal-probability companion sample — under PPS-by-LOC the
    inverse-inclusion weights of tiny-LOC PRs dominated small rate lanes
    (39% of Q1-2026 CLEAN+AI weight on one 75-LOC PR). The EQ draw must
    be canonical (pool-order independent), seeded, capped at
    PER_QUARTER, and its manifest fingerprint design-tagged so the two
    designs can never validate each other; the PPS fingerprint formula
    is unchanged."""
    from pipeline.studies import review_action as ra
    monkeypatch.setattr(ra, "PER_QUARTER", 10)
    items = [(f"o/r{i}", i, 100 + i, "t", "a", False, True)
             for i in range(30)]
    pool = {"Q1-2026": list(items)}
    sel = ra.draw_eq(pool)["Q1-2026"]
    assert len(sel) == 10 and set(sel) <= set(items)
    shuffled = {"Q1-2026": list(reversed(items))}
    assert ra.draw_eq(shuffled)["Q1-2026"] == sel      # canonical
    ids = ra._pool_items(pool)
    assert ra.frame_fingerprint(ids, design="pps") \
        == ra.frame_fingerprint(ids)                   # pps formula stable
    assert ra.frame_fingerprint(ids, design="eq") \
        != ra.frame_fingerprint(ids)


def test_lane_rates_from_eq_sample_loc_shares_from_pps(monkeypatch,
                                                       tmp_path):
    """Issue #2 estimator decision (RED first): responded% comes from the
    EQ sample with UNIT weights (uniform pi cancels in the ratio); the
    post-ask LOC share keeps the PPS sample + HT weights. With one big
    responder and one tiny non-responder both in sample, responded% must
    be 0.5 — not the HT ~0.002 the PPS weights produce."""
    import json as _json
    from pipeline import frame
    from pipeline.studies import review_action as ra
    ask_rev = {"author": {"login": "bob", "__typename": "User"},
               "state": "CHANGES_REQUESTED", "comments": {"totalCount": 1},
               "submittedAt": "2026-04-02T00:00:00Z"}
    big = _pr("2026-04-01T00:00:00Z", merged="2026-04-10T00:00:00Z",
              num=1, reviews=[dict(ask_rev)])
    big["additions"] = 10_000
    small = _pr("2026-04-01T00:00:00Z", merged="2026-04-10T00:00:00Z",
                num=2, reviews=[dict(ask_rev)])
    small["additions"] = 10
    cells = {("o/r", "2026-04-01..2026-06-30"): [big, small]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(ra, "PER_QUARTER", 2)
    monkeypatch.setattr(ra, "SAMPLE", tmp_path / "s_v2.jsonl")
    monkeypatch.setattr(ra, "MANIFEST", tmp_path / "m.json")
    monkeypatch.setattr(ra, "OLD_SAMPLE", tmp_path / "s_v1.jsonl")
    monkeypatch.setattr(ra, "SAMPLE_EQ", tmp_path / "s_eq.jsonl")
    monkeypatch.setattr(ra, "MANIFEST_EQ", tmp_path / "m_eq.json")
    import pipeline.studies.productivity as prod
    monkeypatch.setattr(prod, "fleet_logins", lambda: set())
    pool = ra.eligible()
    ra.ensure_manifest(pool)
    ra.ensure_manifest(pool, path=ra.MANIFEST_EQ, draw_fn=ra.draw_eq,
                       design="eq")

    def rec(num, loc, post_commits):
        commits = [{"commit": {
            "additions": loc, "deletions": 0,
            "committedDate": "2026-04-05T00:00:00Z",
            "committer": {"user": {"login": "alice"}, "email": "a@x"},
            "authors": {"nodes": [{"user": {"login": "alice"}}]}}}
            ] if post_commits else []
        return {"repo": "o/r", "num": num, "loc": loc, "per": "Q2-2026",
                "first_review": "2026-04-02T00:00:00Z", "author": "alice",
                "ai": False, "ins": True, "commits": commits,
                "commits_total": len(commits), "commits_complete": True}
    lines = [_json.dumps(rec(1, 10_000, True)),
             _json.dumps(rec(2, 10, False))]
    (tmp_path / "s_v2.jsonl").write_text("\n".join(lines) + "\n")
    (tmp_path / "s_eq.jsonl").write_text("\n".join(lines) + "\n")
    lanes, _nf, _nr = ra.lane_rows()
    a = lanes[("Q2-2026", "CLEAN")]
    assert a["n"] == 2
    assert abs(a["wacted"] / a["wn"] - 0.5) < 1e-9     # EQ unit weights
    assert a["post"] > 0 and a["total"] > 0            # PPS LOC share kept


# ---- review 2026-07-25: issue #2's 'all' profile over-widened the -------
# nonAI COMPARISON arm. Only layer-B agent-authored PRs were meant to join
# the AI series; 'all' also readmitted App dep-bots, user-typed bots and
# login-less authors, and they land in nonai/nonAI — the degenerate review
# dynamics profile 'pr' exists to exclude.


def _bot_pr(num, login, typename="Bot"):
    p = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z", num=num)
    p["author"] = {"login": login, "__typename": typename}
    return p


def _ghost_pr(num):
    p = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z", num=num)
    p["author"] = None                  # deleted account: no attributable login
    return p


def _polluted_cells():
    """One quarter: a layer-B agent PR and a human PR (the intended AI /
    nonAI pair) plus three non-human authors that must not enter either."""
    human = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z", num=2)
    return {("o/r", "2026-04-01..2026-06-30"): [
        _agent_pr(1), human,
        _bot_pr(3, "dependabot[bot]"),          # App bot, not AI-involved
        _bot_pr(4, "paddle-bot", typename="User"),   # user-typed bot
        _ghost_pr(5)]}


def _polluted_cells_reviewed():
    """_polluted_cells with a human review on every PR — the review-behavior
    studies (attention, responsiveness) only admit human-reviewed PRs, and a
    dep-bump PR that did get a human review is exactly the contaminating
    case."""
    cells = _polluted_cells()
    for p in cells[("o/r", "2026-04-01..2026-06-30")]:
        p["reviews"] = {"nodes": [dict(_REV)]}
    return cells


def test_attention_by_ai_nonai_slice_excludes_bots_and_ghosts(monkeypatch):
    """Review finding 1/2, Figure 7 side (RED first — NOT in the review's
    list, found applying its logic): attention_by_ai also runs on profile
    'all' with no author hygiene, so dep-bump PRs that received a human
    review enter the NONAI slice and deflate its comments/kLOC (a bump gets
    approved without discussion) and distort first-review latency."""
    from pipeline import frame
    from pipeline.studies import attention, productivity
    monkeypatch.setattr(frame, "load_cells", _polluted_cells_reviewed)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: set())
    rows = attention.attention_by_ai()
    assert rows[("Q2-2026", "ai")]["n"] == 1        # the agent PR
    assert rows[("Q2-2026", "nonai")]["n"] == 1     # the human PR ONLY


def test_review_mix_nonai_slice_excludes_bots_and_ghost_authors(monkeypatch):
    """Review finding 1 (RED first): review_mix(by='ai') on profile 'all'
    drops every author-hygiene filter, so dependabot, user-typed bots and
    login-less authors swell the NONAI arm — the published AI-vs-nonAI
    human-review gap narrows because auto-merged dep bumps were added to
    the baseline. Only ai_involved PRs may bypass author hygiene."""
    from pipeline import frame
    from pipeline.studies import productivity
    monkeypatch.setattr(frame, "load_cells", _polluted_cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: set())
    rows = productivity.review_mix(by="ai")
    assert rows[("Q2-2026", "ai")]["n"] == 1        # the agent PR (layer B)
    assert rows[("Q2-2026", "nonai")]["n"] == 1     # the human PR ONLY


def test_fates_nonai_cohort_excludes_bots_and_ghost_authors(monkeypatch,
                                                            capsys):
    """Review finding 2 (RED first): same over-widening in fates_at — the
    'all' cohort and the nonAI cohort absorbed bot-authored PRs, which also
    broke the table's reconciliation (all != AI + nonAI vs ins + ext by the
    bot mass). After the fix the only all-vs-ins+ext gap is layer-B agent
    PRs, which have no human author association by construction."""
    from pipeline import frame
    from pipeline.studies import fates, productivity
    monkeypatch.setattr(frame, "load_cells", _polluted_cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: set())
    monkeypatch.setattr(fates, "MIN_N", 1)   # hygiene, not the floor
    fates.fates_at(8)
    rows = {ln.split()[1]: int(ln.split()[2])
            for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("Q2-2026")}
    assert rows.get("nonAI") == 1              # the human PR ONLY
    assert rows.get("AI") == 1                 # the agent PR
    assert rows.get("all") == 2                # and nothing else
    assert rows["all"] == rows["AI"] + rows["nonAI"]
    assert rows.get("ins") == 1 and "ext" not in rows


def _fig8_module():
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "plot_fig8", "scripts/plot_fig8_responsiveness.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def test_fig8_locshare_gated_on_its_own_sample_count():
    """Review finding 3 (RED first): the two-design split gave rate fields
    (EQ sample, n) and LOC fields (PPS sample, n_loc) independent sample
    sizes, and compute() gates each on its own count — but Figure 8's val()
    still gated BOTH on n. A lane with EQ n >= 20 whose PPS draw has no
    members divides 0.0/0.0 on the defaultdict and kills the figure; a lane
    whose own PPS draw supports the estimate is dropped for EQ n < 20."""
    m = _fig8_module()
    lanes = {("Q1-2026", "CLEAN+AI"): {"n": 25, "wn": 25.0, "wacted": 5.0,
                                       "n_loc": 0, "post": 0.0,
                                       "total": 0.0},
             ("Q2-2026", "CLEAN+AI"): {"n": 17, "wn": 17.0, "wacted": 3.0,
                                       "n_loc": 21, "post": 40.0,
                                       "total": 100.0}}
    assert m.val(lanes, "Q1-2026", "CLEAN+AI", "locshare") is None
    assert m.val(lanes, "Q1-2026", "CLEAN+AI", "responded") == 20.0
    assert m.val(lanes, "Q2-2026", "CLEAN+AI", "locshare") == 40.0
    assert m.val(lanes, "Q2-2026", "CLEAN+AI", "responded") is None


def test_responsiveness_frame_excludes_bots_and_ghost_authors(monkeypatch):
    """Review finding 1/2, Figure 8 side (RED first): lane_rows' sampling
    frame runs on profile 'all', so a dependabot PR that happened to get a
    human review and an explicit ask was a frame member and landed in the
    CLEAN+nonAI lane — the same contamination of the nonAI comparison arm
    fixed in review_mix and fates. Layer-B agent PRs must stay (they are
    the AI lane). Changing the frame changes the fingerprint, so this
    forces a redraw + re-pull of both samples."""
    from pipeline import frame
    from pipeline.studies import review_action as ra
    monkeypatch.setattr(frame, "load_cells", _polluted_cells_reviewed)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    pool = ra.eligible()
    # 1 = layer-B agent (the AI lane), 2 = human; 3/4/5 = dep-bot,
    # user-typed bot, ghost — all non-AI, none may reach a lane
    assert sorted(n for _r, n, *_ in pool["Q2-2026"]) == [1, 2]


def test_hydration_cache_survives_the_first_design_rebuild(tmp_path,
                                                           monkeypatch):
    """Review finding 10 (RED first): pull() runs the PPS design first, and
    rebuild_sample truncates SAMPLE to the NEW PPS selection before the EQ
    pass builds its hydration cache — so a PR already hydrated in the old
    SAMPLE that drops out of the PPS redraw but enters the EQ selection was
    lost from the cache and re-fetched from the API (up to ~1,200 paginated
    PR pulls per quarter on any frame change, exactly the frame change the
    Figure 8 hygiene fix forces). Commit data is a PR-level fact, so the
    cache must be built once, before any rebuild prunes a file."""
    import json as _json
    from pipeline import frame
    from pipeline.studies import review_action as ra
    prs = []
    for i, add in enumerate((10, 100, 1000, 10_000), start=1):
        p = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
                num=i, reviews=[dict(_REV)])
        p["additions"] = add
        prs.append(p)
    monkeypatch.setattr(frame, "load_cells",
                        lambda: {("o/r", "2026-04-01..2026-06-30"): prs})
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(ra, "PER_QUARTER", 2)
    monkeypatch.setattr(ra, "SAMPLE", tmp_path / "s_v2.jsonl")
    monkeypatch.setattr(ra, "MANIFEST", tmp_path / "m.json")
    monkeypatch.setattr(ra, "OLD_SAMPLE", tmp_path / "absent_v1.jsonl")
    monkeypatch.setattr(ra, "SAMPLE_EQ", tmp_path / "s_eq.jsonl")
    monkeypatch.setattr(ra, "MANIFEST_EQ", tmp_path / "m_eq.json")
    # every eligible PR is ALREADY hydrated, and only in SAMPLE
    (tmp_path / "s_v2.jsonl").write_text("".join(
        _json.dumps({"repo": "o/r", "num": i, "per": "Q2-2026", "loc": 100,
                     "first_review": "2026-04-02T00:00:00Z",
                     "author": "alice", "ai": False, "ins": True,
                     "commits": [], "commits_total": 0,
                     "commits_complete": True}) + "\n"
        for i in range(1, 5)))
    seen = []
    monkeypatch.setattr(ra, "_pull_missing",
                        lambda manifest, pool, spath, done, design="pps":
                        seen.append((design, set(done),
                                     set(ra._selected_keys(manifest)))))
    ra.pull()
    designs = {d: (done, sel) for d, done, sel in seen}
    assert set(designs) == {"pps", "eq"}
    # fixture must be non-degenerate: EQ selects a PR the PPS redraw drops
    assert designs["eq"][1] - designs["pps"][1]
    for design, (done, selected) in designs.items():
        assert selected <= done, (
            f"{design}: {selected - done} already hydrated but re-fetched")


def test_compute_prints_row_when_only_one_design_supports_it(monkeypatch,
                                                             capsys):
    """Review finding 3, table side (RED first): compute() gates the whole
    ROW on the EQ count n, so the real Q1-2026 CLEAN+AI lane (n=17,
    n_loc=21) is absent from the report table — while Figure 8, now gating
    each panel on its own design, plots its LOC share. Every published
    figure point must have a table row; the unsupported column reads n/a."""
    from pipeline.studies import review_action as ra
    lanes = {("Q1-2026", "CLEAN+AI"): {"n": 17, "wn": 17.0, "wacted": 12.0,
                                       "n_loc": 21, "post": 40.0,
                                       "total": 100.0}}
    monkeypatch.setattr(ra, "lane_rows", lambda: (lanes, lanes, 0))
    ra.compute()
    rows = [ln for ln in capsys.readouterr().out.splitlines()
            if ln.startswith("Q1-2026 CLEAN+AI")]
    assert rows, "a lane whose own PPS draw supports the LOC share must print"
    assert "40.0%" in rows[0]           # its own design's estimate
    assert "n/a" in rows[0]             # responded% unsupported at n=17


# ---- 2026-07-25 mass-tombstoning incident -------------------------------
# A re-pull wrote 1,345 "unretrievable" tombstones (27.9% of the EQ
# selection) for PRs that were alive: GitHub answers a timed-out or
# rate-limited BATCH with null aliases plus an errors array, ghx discards
# errors, and _definitive_miss recorded the null as permanent nonresponse.
# The coverage guard passed it, because a tombstone IS documented
# nonresponse — so Q2-2026 CLEAN+AI published as n=0.


def _envelope(*errors, pr=None, repo_null=False):
    data = {"repository": None if repo_null else {"pullRequest": pr}}
    env = {"data": data}
    if errors:
        env["errors"] = [{"type": t, "message": m, "path": ["repository"]}
                         for t, m in errors]
    return json.dumps(env)


_GOOD_NODE = {"pullRequest": {"commits": {
    "nodes": [{"commit": {
        "committedDate": "2026-01-05T00:00:00Z",
        "additions": 10, "deletions": 0,
        "committer": {"user": {"login": "alice"}, "email": "a@x"},
        "authors": {"nodes": [{"user": {"login": "alice"}}]}}}],
    "pageInfo": {"hasNextPage": False, "endCursor": "c"},
    "totalCount": 1}}}


def _batch_envelope(alias_value, *errors):
    """A batch response for one alias a0, optionally carrying errors whose
    path points AT that alias — the shape GitHub returns for a timed-out or
    rate-limited batch."""
    env = {"data": {"a0": alias_value}}
    if errors:
        env["errors"] = [{"type": t, "message": m,
                          "path": ["a0", "pullRequest"]} for t, m in errors]
    return json.dumps(env)


def _batch_pull(monkeypatch, tmp_path, batch_env, confirm_env="{}"):
    """Run one _pull_missing chunk. `batch_env` answers the 8-alias batch
    query, `confirm_env` the single-PR confirmation — dispatched on whether
    the query carries an alias. Returns the records written to the sample."""
    from pipeline import ghx
    from pipeline.studies import review_action as ra
    monkeypatch.setattr(ghx, "_gh",
                        lambda args, timeout=90, allow_partial=False:
                        batch_env if "a0:" in " ".join(args) else confirm_env)
    monkeypatch.setattr(ghx, "graphql_budget_wait", lambda *_a: None)
    monkeypatch.setattr(ra.time, "sleep", lambda *_a: None)
    spath = tmp_path / "s.jsonl"
    spath.touch()
    item = _item("o/live", 7)
    manifest = {"fingerprint": "f", "selected": {"Q1-2026": [list(item)]}}
    try:
        ra._pull_missing(manifest, {"Q1-2026": [item]}, spath, set(), "eq")
    except SystemExit:
        pass          # a DEFERRED PR leaves coverage unresolved by design:
    # the pull exits nonzero to force a rerun. What matters here is what got
    # written to the sample file, which is permanent.
    return [json.loads(ln) for ln in spath.read_text().splitlines()]


def test_transient_null_alias_defers_instead_of_tombstoning(monkeypatch,
                                                            tmp_path):
    """RED first (2026-07-25 incident): a null alias in a batch response is
    NOT evidence the PR is gone. Under a rate-limited/timed-out response the
    PR must DEFER to the next pull — never be checkpointed as permanent
    nonresponse. Verified live: the exact 8-PR batch that produced 59
    vllm-project/vllm tombstones re-ran clean, and those PRs are MERGED."""
    written = _batch_pull(
        monkeypatch, tmp_path, _batch_envelope(None),
        _envelope(("RATE_LIMITED", "API rate limit exceeded")))
    assert written == [], f"tombstoned a live PR on a transient error: {written}"


def test_confirmed_not_found_still_tombstones(monkeypatch, tmp_path):
    """The other half of the same fix: a DEFINITIVE miss (repo resolves, PR
    explicitly NOT_FOUND — openai/plugins disabled PRs) must still record a
    tombstone, or coverage could never be resolved for real nonresponse."""
    written = _batch_pull(
        monkeypatch, tmp_path, _batch_envelope(None),
        _envelope(("NOT_FOUND", "Could not resolve to a PullRequest")))
    assert len(written) == 1 and written[0]["unretrievable"] is True


def test_batch_errors_are_logged_not_silently_discarded(monkeypatch, tmp_path,
                                                        capsys):
    """RED first (issue #3 follow-up 1): the incident's actual errors payload
    was never recorded — graphql_nodes discards it — so the trigger had to be
    inferred from re-running the batch afterwards. The pull must LOG the
    error types it received, or the next occurrence is undiagnosable too."""
    _batch_pull(monkeypatch, tmp_path,
                _batch_envelope(_GOOD_NODE,
                                ("RATE_LIMITED", "secondary rate limit")))
    out = capsys.readouterr().out
    assert "RATE_LIMITED" in out, f"errors discarded; log was: {out!r}"


def test_alias_tainted_by_transient_error_is_not_checkpointed(monkeypatch,
                                                              tmp_path):
    """RED first (issue #3 follow-up 2): the same null-vs-error confusion has
    a quieter form. When a response carries errors, a NON-null alias was
    still checkpointed `commits_complete: True` — and since GraphQL nulls an
    errored field inside an otherwise-valid list, a truncated commits
    connection could be recorded as complete, which `_suspect` then never
    revisits and `--repair` never revisits either. Measured: 0 null nodes in
    92,515 today, so this is latent, not active — but it silently biases
    post-ask LOC down if it ever fires, and the record looks clean forever.
    An alias touched by a non-NOT_FOUND error must DEFER."""
    written = _batch_pull(monkeypatch, tmp_path,
                          _batch_envelope(_GOOD_NODE,
                                          ("RATE_LIMITED", "rate limited")))
    assert written == [], (
        "checkpointed a record from an errored response: "
        f"{[(d.get('commits_total'), d.get('commits_complete')) for d in written]}")


def test_mass_nonresponse_fails_hard_even_though_documented():
    """RED first (2026-07-25 incident): require_complete_sample accepted
    27.9% tombstoned nonresponse because each stone is 'documented'. The
    guard exists to refuse a non-probability subset — mass nonresponse is
    exactly that, wearing the right paperwork. Genuine nonresponse has been
    0.1-0.3%, so a small ceiling separates the two — consulted only once
    enough stones exist for a rate to mean anything (a couple of genuine
    misses in a small draw is not a systemic failure)."""
    import pytest
    from pipeline.studies import review_action as ra

    def stone(i):
        return {"repo": "o/r", "num": i, "commits": [],
                "unretrievable": True, "commits_complete": False}
    sel = [list(_item("o/r", i)) for i in range(1000)]
    manifest = {"fingerprint": "f", "selected": {"Q1-2026": sel}}
    records = {("o/r", i): _rec("o/r", i) for i in range(1000)}
    ra.require_complete_sample(manifest, records)      # 0% nonresponse: fine
    for i in range(5):                                 # 0.5%: genuine range
        records[("o/r", i)] = stone(i)
    ra.require_complete_sample(manifest, records)
    for i in range(30):                                # 3%: incident signature
        records[("o/r", i)] = stone(i)
    with pytest.raises(SystemExit) as e:
        ra.require_complete_sample(manifest, records)
    assert "nonresponse" in str(e.value).lower()


def test_incomplete_sample_error_names_its_design_and_file():
    """Review finding 9 (RED first): require_complete_sample is now called
    for BOTH designs but hardcoded 'PPS sample incomplete', so an EQ-side
    coverage gap sends the operator to the wrong sample file."""
    import pytest
    from pipeline.studies import review_action as ra
    manifest = {"fingerprint": "f",
                "selected": {"Q1-2026": [list(_item("o/b", 2))]}}
    with pytest.raises(SystemExit) as e:
        ra.require_complete_sample(manifest, {}, design="eq",
                                   path=ra.SAMPLE_EQ)
    assert "eq" in str(e.value) and "sample_eq_v1" in str(e.value)
    with pytest.raises(SystemExit) as e:
        ra.require_complete_sample(manifest, {})
    assert "pps" in str(e.value).lower()


def test_bot_sensitivity_like_for_like_weighted_and_two_shares(
        monkeypatch, capsys):
    """Every invariant the companion advertises must be observable here, so
    the fixture is deliberately asymmetric: unequal contributor weights,
    different bot mixes per repo, an AI-AGENT bot (bot-authored yet
    AI-involved, so the two shares diverge), and a repo whose filtered subset
    falls under the floor and is therefore excluded from the shared set.
    Feature test, not a bug repro."""
    from pipeline import frame
    from pipeline.studies import slices

    def ai_pr(num):
        p = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
                num=num)
        p["commits"] = {"nodes": [{"commit": {
            "message": "x\n\nCo-Authored-By: Claude <noreply@anthropic.com>",
            "authors": {"nodes": []}}}]}
        return p
    cells = {
        # o/a: 1 AI + 3 dep-bots. Dropping the 3 leaves 1 PR, under the
        # floor of 3 -> no-dilution undefined -> EXCLUDED from the shared set
        ("o/a", "2026-04-01..2026-06-30"): [
            ai_pr(1), *[_bot_pr(i, "dependabot[bot]") for i in (2, 3, 4)]],
        # o/b: 3 AI humans + 1 AI AGENT bot + 1 dep-bot. published 4/5;
        # no-dilution drops only the dep-bot -> 4/4; no-bots drops the agent
        # too -> 3/3. bot% 2/5 vs dilbot% 1/5 — the shares must differ.
        ("o/b", "2026-04-01..2026-06-30"): [
            ai_pr(1), ai_pr(2), ai_pr(3), _agent_pr(4),
            _bot_pr(5, "dependabot[bot]")],
        # o/c: 4 non-AI humans, no bots — zero rate, drags the weighted
        # means down only if weighting is applied at all
        ("o/c", "2026-04-01..2026-06-30"): [
            _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z", num=i)
            for i in (1, 2, 3, 4)],
    }
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos",
                        lambda: {"o/a", "o/b", "o/c"})
    monkeypatch.setattr(slices, "MIN_PRS", 3)
    monkeypatch.setattr(slices, "weights",
                        lambda: {"o/a": 1.0, "o/b": 9.0, "o/c": 1.0})
    slices.bot_sensitivity()
    row = [ln for ln in capsys.readouterr().out.splitlines()
           if ln.startswith("Q2-2026")][0]
    repos = int(row.split()[1])
    pub_all = float(row.split()[2].rstrip("%"))
    means = [float(m) for m in re.findall(r"(\d+\.\d)\s+\[", row)]
    published, no_dilution, no_bots = means
    dilbot, bot = (float(x.rstrip("%")) for x in row.split()[-2:])

    assert repos == 2                  # o/a excluded by the filtered floor
    # pub(all) spans all THREE repos: (0.25*1 + 0.8*9 + 0*1)/11
    assert pub_all == 67.7
    # the shared-set columns are weighted 9:1 toward o/b, not 1:1
    assert published == 72.0           # (0.8*9 + 0*1)/10; equal weights: 40.0
    assert no_dilution == 90.0         # (1.0*9 + 0*1)/10
    assert no_bots == 90.0             # agent dropped, but o/b is all-AI
    # the two shares MUST differ: the agent bot counts in one, not the other
    assert dilbot == 18.0              # (1/5 * 9 + 0)/10
    assert bot == 36.0                 # (2/5 * 9 + 0)/10


def test_fleet_logins_ignores_stale_disk_cache(monkeypatch, tmp_path):
    """Issue #10 (RED first): fleet_logins() trusted data/derived/
    fleet_logins.txt unconditionally, so a stale (even committed) file
    silently mis-sliced Figure 3's fleet series, Figures 6-8, fates, and
    review_action. The fleet set must come from the current cells."""
    from pipeline.studies import productivity
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "data" / "derived"
    d.mkdir(parents=True)
    (d / "fleet_logins.txt").write_text("stale-operator\n")
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({}, {}, {}, {"fresh-operator"}))
    assert productivity.fleet_logins() == {"fresh-operator"}


def test_fleet_definition_has_a_single_source(monkeypatch, tmp_path):
    """Issue #10 (RED first): event_by_adoption_month's cohort path
    computes the fleet set fresh while fleet_logins() read the cache, so
    figure_2_comp_audits and figure_3_comp_audits could disagree about
    who is a fleet operator. Both must share one definition."""
    from pipeline.studies import productivity
    monkeypatch.chdir(tmp_path)
    d = tmp_path / "data" / "derived"
    d.mkdir(parents=True)
    (d / "fleet_logins.txt").write_text("stale-operator\n")
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({}, {}, {}, {"fresh-operator"}))
    *_rest, cohort_fleet = productivity._author_months_and_cohorts()
    assert productivity.fleet_logins() == cohort_fleet


def test_fleet_logins_writes_no_cache_file(monkeypatch, tmp_path):
    """Issue #10 (RED first): fleet_logins() must not persist an
    unfingerprinted cache for a later run to trust."""
    from pipeline.studies import productivity
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "derived").mkdir(parents=True)
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({}, {}, {}, {"a"}))
    assert productivity.fleet_logins() == {"a"}
    assert not (tmp_path / "data" / "derived"
                / "fleet_logins.txt").exists()


def test_fleet_logins_memoized_per_process(monkeypatch, tmp_path):
    """Feature test for the issue #10 fix: one author-frame pass per
    process — every consumer shares the computed set."""
    from pipeline.studies import productivity
    calls = []
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data" / "derived").mkdir(parents=True)
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: calls.append(1) or ({}, {}, {}, {"a"}))
    assert productivity.fleet_logins() == {"a"}
    assert productivity.fleet_logins() == {"a"}
    assert len(calls) == 1


def test_fleet_memo_cleared_between_tests_a(monkeypatch):
    """PR #12 review hardening (RED first, as a pair with _b below —
    definition order is the test): populate the fleet memo under
    monkeypatched cells, exactly what any consumer-calling test does."""
    from pipeline.studies import productivity
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({}, {}, {}, {"leaked-operator"}))
    assert productivity.fleet_logins() == {"leaked-operator"}


def test_fleet_memo_cleared_between_tests_b(monkeypatch):
    """Pair of _a: the memo populated there must not survive into this
    test — the autouse conftest fixture clears it, so fleet_logins()
    recomputes from THIS test's cells."""
    from pipeline.studies import productivity
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({}, {}, {}, {"own-operator"}))
    assert productivity.fleet_logins() == {"own-operator"}


def test_fleet_cohort_is_membership_in_fleet_all(monkeypatch):
    """PR #12 review, P2. Drift guard on real builder output (no red run
    exists: the duplicated FLEET_MIN predicates agreed pre-fix, so this
    is mutation-verified — editing either site's threshold fails it):
    at threshold-boundary data the 'fleet' cohort label, fleet_all, and
    fleet_logins() must agree — exactly FLEET_MIN merged PRs is fleet
    everywhere, one fewer is fleet nowhere."""
    from pipeline import frame
    from pipeline.studies import productivity

    def m(login, num):
        p = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
                num=num)
        p["author"] = {"login": login, "__typename": "User"}
        return p
    cells = {("o/r", "2026-04-01..2026-06-30"):
             [m("atmin", 1), m("atmin", 2), m("below", 3)]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "FLEET_MIN", 2)
    _acc, cohorts, _q_of, fleet_all = \
        productivity._author_months_and_cohorts()
    assert fleet_all == {"atmin"}
    assert cohorts["atmin"] == "fleet"
    assert cohorts["below"] != "fleet"
    assert {a for a, c in cohorts.items() if c == "fleet"} == fleet_all
    assert productivity.fleet_logins() == fleet_all


# --- monthly-finalized figures: Figure 2 / Figure 3 companions use only
# w8-final months (no provisional data on either figure) ---


def test_event_cohorts_require_w8_final_window(monkeypatch):
    """Figure 2 (monthly finalized update): an adoption-month cohort
    enters only when its full [-2..+2] window has passed w8 finalization
    at the AS_OF — a cohort whose t+2 month is still open is excluded,
    so no plotted offset is ever provisional."""
    from pipeline.studies import productivity

    def row(ai_prs):
        return [0.0, 0.0, ai_prs, 1, 0, 1.0, 0.0]

    acc = {"a": {"2026-04": row(1)}, "b": {"2026-03": row(1)}}
    cohorts = {"a": "medium", "b": "medium"}
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: (acc, cohorts, {}, set()))
    monkeypatch.setattr(detect, "AS_OF", "2026-08-01T00:00:00Z")
    # require_active=False isolates the WINDOW gate: these fixtures are
    # active only at t0, which the membership rule would drop
    out = productivity.event_by_adoption_month(require_active=False)
    assert "2026-03" in out        # t+2 = 2026-05, w8-final by the AS_OF
    assert "2026-04" not in out    # t+2 = 2026-06, window still open


def test_review_mix_monthly_granularity(monkeypatch):
    """Figure 3 companion (monthly finalized update): review_mix groups
    by calendar month when granularity='month', keying rows by month."""
    from pipeline import frame
    from pipeline.studies import productivity
    monkeypatch.setattr(detect, "AS_OF", "2026-09-01T00:00:00Z")
    apr = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
              num=2, reviews=[dict(_REV)])
    may = _pr("2026-05-02T00:00:00Z", merged="2026-05-06T00:00:00Z", num=3)
    cells = {("o/r", "2026-04-01..2026-06-30"): [apr, may]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: set())
    rows = productivity.review_mix(by="ai", granularity="month")
    assert rows[("2026-04", "nonai")]["n"] == 1
    assert rows[("2026-05", "nonai")]["n"] == 1
    assert ("Q2-2026", "nonai") not in rows


def test_attention_by_ai_monthly_granularity(monkeypatch):
    """Figure 3 companion (monthly finalized update): attention_by_ai
    keys rows by calendar month when granularity='month'."""
    from pipeline import frame
    from pipeline.studies import attention, productivity
    monkeypatch.setattr(detect, "AS_OF", "2026-09-01T00:00:00Z")
    apr = _pr("2026-04-01T00:00:00Z", merged="2026-04-05T00:00:00Z",
              num=2, reviews=[dict(_REV)])
    cells = {("o/r", "2026-04-01..2026-06-30"): [apr]}
    monkeypatch.setattr(frame, "load_cells", lambda: cells)
    monkeypatch.setattr(frame, "population_repos", lambda: {"o/r"})
    monkeypatch.setattr(productivity, "fleet_logins", lambda: set())
    rows = attention.attention_by_ai(granularity="month")
    assert ("2026-04", "nonai") in rows
    assert ("Q2-2026", "nonai") not in rows


def _fake_authors(monkeypatch, rows_by_login):
    """Pin _author_months_and_cohorts to a hand-built author table:
    login -> month -> [ai_mrg, nonai_mrg, ai_prs, prs, mrg_prs,
    submitted, sub_ai]."""
    from pipeline.studies import productivity
    acc = {login: {m: list(v) for m, v in months.items()}
           for login, (months, _c) in rows_by_login.items()}
    cohorts = {login: c for login, (_m, c) in rows_by_login.items()}
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: (acc, cohorts, {"2026-06": "Q2-2026"}, set()))
    return productivity


def test_adoption_monthly_median_is_not_dragged_by_one_operator():
    """The fleet cohort mean tripled Mar->Jun 2026 while its median stayed
    flat: one operator supplied 54.7% of June's merged LOC. The median
    variant must describe the typical member, not the sum."""
    import pytest
    from pipeline.studies import productivity
    mp = pytest.MonkeyPatch()
    try:
        _fake_authors(mp, {
            "big":   ({"2026-06": [0.0, 900.0, 0, 10, 10, 900.0, 0.0]}, "fleet"),
            "small1": ({"2026-06": [0.0, 10.0, 0, 5, 5, 10.0, 0.0]}, "fleet"),
            "small2": ({"2026-06": [0.0, 20.0, 0, 5, 5, 20.0, 0.0]}, "fleet"),
        })
        mean = productivity.adoption_monthly()[("2026-06", "fleet")]
        med = productivity.adoption_monthly(stat="median")[("2026-06", "fleet")]
    finally:
        mp.undo()
    assert mean["merged"] == pytest.approx(310.0)   # (900+10+20)/3
    assert med["merged"] == pytest.approx(20.0)     # the middle operator
    assert med["n"] == 3                            # n is a count either way


def test_adoption_monthly_rejects_an_unknown_stat():
    from pipeline.studies import productivity
    import pytest
    with pytest.raises(ValueError):
        productivity.adoption_monthly(stat="mode")


def test_core_rows_median_is_the_typical_core_author(monkeypatch):
    """METHODS 1d.4b: per-contributor LEVELS are quoted from the median,
    so the Figure 3 estimator must offer one. Stage 1 is the statistic
    over a repo's core authors; the CW stage across repos is unchanged."""
    from pipeline.studies import paper_tables

    # one repo-period, three core authors: 1, 2 and 97 kLOC merged
    authors = {"a": [0, 0, 1_000, 0, 1_000],
               "b": [0, 0, 2_000, 0, 2_000],
               "c": [0, 0, 97_000, 0, 97_000]}
    monkeypatch.setattr(paper_tables, "per_author",
                        lambda: {("o/r", "Q1-2024"): authors})
    monkeypatch.setattr(paper_tables, "weights", lambda: {"o/r": 1.0})

    class F:
        repo, period, author, insider = "o/r", "Q1-2024", None, True
    def frames():
        for login in authors:
            f = F()
            f.author = login
            yield f
    monkeypatch.setattr(paper_tables, "study_frame", lambda _p: frames())
    monkeypatch.setattr(paper_tables, "PERIODS", ["Q1-2024"])

    mean = paper_tables.core_rows()[0]["kloc"][0]
    med = paper_tables.core_rows(stat="median")[0]["kloc"][0]
    assert mean == pytest.approx((1 + 2 + 97) / 3)     # 33.33, the tail
    assert med == pytest.approx(2.0)                   # the middle author


def test_core_rows_rejects_an_unknown_stat():
    from pipeline.studies import paper_tables
    with pytest.raises(ValueError):
        paper_tables.core_rows(stat="mode")


def test_event_by_adoption_month_median_is_the_typical_adopter(monkeypatch):
    """Figure 2's event panels average per-author kLOC the same way the
    cohort series do, so they carry the same heavy tail. The median
    variant must describe the typical adopter."""
    from pipeline.studies import productivity
    # first AI evidence at WINDOW_MONTHS[2] so the [-2..+2] window fits
    t0_mon = productivity.WINDOW_MONTHS[2]
    # [ai_mrg, nonai_mrg, ai_prs, prs, mrg_prs, submitted, sub_ai]
    def rows(merged):
        # active in every offset month so the membership rule keeps them
        r = {m: [0.0, 0.0, 0, 1, 1, 0.0, 0.0]
             for m in productivity.WINDOW_MONTHS[0:5]}
        r[t0_mon] = [0.0, merged, 1, 1, 1, merged, 0.0]
        return r
    acc = {"a": rows(1.0), "b": rows(2.0), "c": rows(97.0)}
    cohorts = {"a": "early", "b": "early", "c": "early"}
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: (acc, cohorts, {}, set()))
    monkeypatch.setattr(productivity, "month_w8_mature", lambda _m: True)

    mean = productivity.event_by_adoption_month()[t0_mon]
    med = productivity.event_by_adoption_month(stat="median")[t0_mon]
    assert mean["n"] == med["n"] == 3
    assert mean["offsets"][0]["merged"] == pytest.approx((1 + 2 + 97) / 3)
    assert med["offsets"][0]["merged"] == pytest.approx(2.0)
    # offsets with no activity stay zero under either statistic
    assert med["offsets"][-2]["merged"] == pytest.approx(0.0)


def test_event_by_adoption_month_rejects_an_unknown_stat():
    from pipeline.studies import productivity
    with pytest.raises(ValueError):
        productivity.event_by_adoption_month(stat="mode")


def test_event_panels_require_activity_in_every_offset_month(monkeypatch):
    """30-48% of each Figure 2 cohort had NO activity at t-2/t-1 while 0%
    can be inactive at t0 (AI evidence requires a PR), so zero-filled
    inactive months made the step at adoption partly composition — people
    appearing in the data, not people producing more. Members must have
    submitted >=1 PR in EVERY offset month, so each has a real non-AI
    baseline to move from."""
    from pipeline.studies import productivity
    W = productivity.WINDOW_MONTHS
    t0_mon = W[2]

    def row(prs, ai_prs, merged):
        return [0.0, merged, ai_prs, prs, prs, merged, 0.0]

    steady = {W[i]: row(1, 0, 4.0) for i in (0, 1, 3, 4)}
    steady[t0_mon] = row(1, 1, 4.0)
    newcomer = {t0_mon: row(1, 1, 40.0), W[3]: row(1, 0, 40.0),
                W[4]: row(1, 0, 40.0)}          # nothing at t-2 / t-1
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({"steady": steady, "newcomer": newcomer},
                                 {"steady": "early", "newcomer": "early"},
                                 {}, set()))
    monkeypatch.setattr(productivity, "month_w8_mature", lambda _m: True)

    kept = productivity.event_by_adoption_month()[t0_mon]
    assert kept["n"] == 1                        # newcomer dropped
    assert kept["offsets"][-2]["merged"] == pytest.approx(4.0)

    both = productivity.event_by_adoption_month(require_active=False)[t0_mon]
    assert both["n"] == 2
    # the newcomer's zero-filled baseline halves the t-2 mean
    assert both["offsets"][-2]["merged"] == pytest.approx(2.0)


def test_zero_comment_share_does_not_condition_on_being_reviewed():
    """Issue #34: the write-up's '85-90% of fleet PRs had no commentary'
    came from an ad-hoc drill-down. The reproducible statistic must count
    ALL mature merged PRs in the slice — conditioning on human_reviewed
    (as the attention panels do) would define the answer away."""
    from pipeline.studies import attention
    silent = _pr("2026-01-05T00:00:00Z", merged="2026-01-09T00:00:00Z", num=1)
    talked = _pr("2026-01-06T00:00:00Z", merged="2026-01-10T00:00:00Z", num=2,
                 reviews=[{"author": {"login": "bob", "__typename": "User"},
                           "state": "COMMENTED",
                           "comments": {"totalCount": 3},
                           "submittedAt": "2026-01-07T00:00:00Z"}])
    assert attention.human_comment_count(silent) == 0
    assert attention.human_comment_count(talked) == 3
    # an unreviewed PR must still land in the denominator
    assert attention.has_no_human_commentary(silent) is True
    assert attention.has_no_human_commentary(talked) is False


def test_productivity_deciles_quarterly_basis_averages_three_months():
    """The single-month endpoints are dominated by month-to-month
    volatility (p10 0.08x to p90 19.9x on the full panel), so the
    quarterly basis averages Oct-Dec and Apr-Jun per contributor before
    taking deciles."""
    from pipeline.studies import productivity
    W = productivity.WINDOW_MONTHS

    def row(sub):
        return [0.0, sub, 0, 1, 1, sub, 0.0]

    # one contributor active every month; submitted 3/6/9 in Oct-Dec
    # (mean 6) and 10/20/30 in Apr-Jun (mean 20)
    vals = {W[0]: 3.0, W[1]: 6.0, W[2]: 9.0,
            W[3]: 1.0, W[4]: 1.0, W[5]: 1.0,
            W[6]: 10.0, W[7]: 20.0, W[8]: 30.0}
    acc = {"solo": {m: row(v) for m, v in vals.items()}}
    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(productivity, "_author_months_and_cohorts",
                   lambda: (acc, {"solo": "early"}, {}, set()))
        q = productivity.productivity_deciles(basis="quarter")
        m = productivity.productivity_deciles(basis="month")
    finally:
        mp.undo()
    # quarterly: means of the two 3-month windows
    assert q[("all", "submitted", "pre")][4] == pytest.approx(6.0)
    assert q[("all", "submitted", "post")][4] == pytest.approx(20.0)
    assert q[("all", "submitted", "ratio")][4] == pytest.approx(20.0 / 6.0)
    # monthly: the single endpoint months, which are noisier by design
    assert m[("all", "submitted", "pre")][4] == pytest.approx(3.0)
    assert m[("all", "submitted", "post")][4] == pytest.approx(30.0)


def test_activity_deciles_split_by_population_and_group():
    """The detection-based split is confounded by volume: detection needs
    a marker in a PR, so contributors submitting ~1 PR/quarter can barely
    be detected at all. The activity deciles expose that — in the loose
    population never-AI sits at 0.33 PRs/month, in the balanced panel at
    ~7 — so the two populations must be reported side by side."""
    from pipeline.studies import productivity

    W, B = productivity.WINDOW_MONTHS, productivity.BASELINE_MONTHS

    def row(prs, ai, kloc):
        return [0.0, 0.0, ai, prs, prs, kloc, 0.0]

    # "heavy" trips detection; "light" never does and is absent one month
    heavy = {m: row(9, 1 if m == W[3] else 0, 5.0) for m in W + B}
    light = {m: row(1, 0, 0.5) for m in W + B}
    light[W[4]] = row(0, 0, 0.0)                 # gap -> out of the panel
    mp = pytest.MonkeyPatch()
    try:
        mp.setattr(productivity, "_author_months_and_cohorts",
                   lambda: ({"heavy": heavy, "light": light},
                            {"heavy": "early", "light": "never"}, {}, set()))
        loose = productivity.activity_deciles(balanced=False)
        panel = productivity.activity_deciles(balanced=True)
    finally:
        mp.undo()
    assert loose[("Q4-2025", "never_ai", "prs", "n")][0] == 1.0
    assert panel.get(("Q4-2025", "never_ai", "prs", "n"), [0])[0] == 0.0
    assert panel[("Q4-2025", "ever_ai", "prs", "n")][0] == 1.0


def test_decile_studies_are_insider_only(monkeypatch):
    """Figure 3's "core author" population is INSIDERS
    (authorAssociation MEMBER/OWNER/COLLABORATOR). Outsiders are
    drive-by by nature, and _author_months_and_cohorts already keys its
    cohort map on insiders only — the decile studies must use the same
    population or they describe a different set of people."""
    from pipeline.studies import productivity
    W = productivity.WINDOW_MONTHS

    def row(prs):
        return [0.0, 0.0, 0, prs, prs, float(prs), 0.0]

    inside = {m: row(9) for m in W + productivity.BASELINE_MONTHS}
    outside = {m: row(1) for m in W + productivity.BASELINE_MONTHS}
    # cohort map carries INSIDERS ONLY, exactly as the shared builder does
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({"ins": inside, "out": outside},
                                 {"ins": "never"}, {}, set()))
    act = productivity.activity_deciles(balanced=False)
    dec = productivity.productivity_deciles(basis="quarter")
    assert act[("Q4-2025", "never_ai", "prs", "n")][0] == 1.0   # not 2
    assert dec[("all", "submitted", "n")][0] == 1.0             # not 2


def test_active_insider_deciles_require_the_floor_in_both_quarters():
    """The active-insiders panel (>=10 PRs in BOTH endpoint quarters)
    is what makes "never used AI" a behavioural claim: dozens of chances
    to trip a marker, none did. A contributor under the floor in either
    quarter must be excluded, and fleet operators always are."""
    import pytest as _pt
    from pipeline.studies import productivity
    W, B = productivity.WINDOW_MONTHS, productivity.BASELINE_MONTHS

    def row(prs, ai=0, kloc=0.0):
        return [0.0, kloc, ai, prs, prs, kloc, 0.0]

    active = {m: row(4, 0, 2.0) for m in W + B}      # 12/quarter, never AI
    active[W[3]] = row(4, 1, 2.0)                    # ...actually ever-AI
    quiet = {m: row(2, 0, 1.0) for m in W + B}       # 6/quarter: under floor
    fleeter = {m: row(200, 0, 50.0) for m in W + B}
    mp = _pt.MonkeyPatch()
    try:
        mp.setattr(productivity, "_author_months_and_cohorts",
                   lambda: ({"a": active, "q": quiet, "f": fleeter},
                            {"a": "early", "q": "never", "f": "fleet"},
                            {}, {"f"}))
        out = productivity.active_insider_deciles(pre="Q4-2025")
    finally:
        mp.undo()
    assert out[("ever_ai", "submitted", "n")][0] == 1.0   # only "a"
    assert ("never_ai", "submitted", "n") not in out or \
        out[("never_ai", "submitted", "n")][0] == 0.0
    # per-quarter ratio: 6 kLOC both quarters -> 1.0x at every decile
    assert out[("ever_ai", "submitted", "ratio")][4] == _pt.approx(1.0)
    assert out[("ever_ai", "prs", "ratio")][4] == _pt.approx(1.0)


def test_change_deciles_report_the_ratio_sample_size(monkeypatch):
    """Codex review P1: members with pre == 0 cannot have a change ratio
    and are dropped from the ratio deciles, while the figures quoted the
    FULL membership n — 453/475 on one A3 curve. Both decile studies must
    expose the metric-specific ratio sample so plots can label what they
    actually draw."""
    from pipeline.studies import productivity
    W = productivity.WINDOW_MONTHS

    def row(prs, merged):
        return [0.0, merged, 0, prs, prs, merged, 0.0]

    grew = {m: row(4, 2.0) for m in W + productivity.BASELINE_MONTHS}
    fresh = {m: row(4, 0.0) for m in W + productivity.BASELINE_MONTHS}
    for m in W[-3:]:
        fresh[m] = row(4, 3.0)         # active always, merges only at the end
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({"g": grew, "z": fresh},
                                 {"g": "never", "z": "never"}, {}, set()))
    dec = productivity.productivity_deciles(basis="quarter")
    act = productivity.active_insider_deciles(pre="Q4-2025")
    for out in (dec[("never_ai", "merged", "n_ratio")],
                act[("never_ai", "merged", "n_ratio")]):
        assert out[0] == 1.0           # only "g" has a pre > 0
    assert dec[("never_ai", "merged", "n")][0] == 2.0
    assert act[("never_ai", "prs", "n_ratio")][0] == 2.0   # prs pre > 0 both


def test_adoption_quarterly_pools_a_members_quarter(monkeypatch):
    """fleet_vs_nonadopters moves from months to quarters (monthly points
    are noisy). A member's quarter value is their TOTAL over its months,
    and membership is quarter-active (>=1 PR in the quarter), so one
    active month is enough to enter with their full quarter output."""
    from pipeline.studies import productivity
    W = productivity.WINDOW_MONTHS

    def row(prs, merged):
        return [0.0, merged, 0, prs, prs, merged, 0.0]

    steady = {m: row(1, 2.0) for m in W}          # 6 kLOC every quarter
    spiky = {W[0]: row(1, 9.0)}                   # Q4-2025 only, one month
    monkeypatch.setattr(productivity, "_author_months_and_cohorts",
                        lambda: ({"s": steady, "k": spiky},
                                 {"s": "never", "k": "never"},
                                 {}, set()))
    mean = productivity.adoption_quarterly()
    med = productivity.adoption_quarterly(stat="median")
    assert mean[("Q4-2025", "never")]["n"] == 2
    assert mean[("Q4-2025", "never")]["merged"] == pytest.approx((6 + 9) / 2)
    assert med[("Q4-2025", "never")]["merged"] == pytest.approx(7.5)
    # spiky is NOT quarter-active in Q1-2026: only steady remains
    assert mean[("Q1-2026", "never")]["n"] == 1
    assert mean[("Q1-2026", "never")]["merged"] == pytest.approx(6.0)
    with pytest.raises(ValueError):
        productivity.adoption_quarterly(stat="mode")
