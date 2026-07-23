"""External review P1s (RED first): studies must honor the w8 maturity
gate and the AS_OF migration — analyze gating alone is not 'every paper
number obeys the frozen rule'."""

from pipeline import detect
from pipeline.detect import MARKERS, classify_pr


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


def test_event_study_mature_max_follows_as_of(monkeypatch):
    from pipeline.studies import event_study
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
