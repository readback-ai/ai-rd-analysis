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
    from pipeline.studies import slices
    cells = {("o/r", "2026-04-01..2026-06-30"): [IMMATURE, MATURE] * 3}
    monkeypatch.setattr(slices, "load_cells", lambda: cells)
    monkeypatch.setattr(slices, "population_repos", lambda: {"o/r"})
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
    monkeypatch.setattr(paper_tables, "load_cells", lambda: cells)
    monkeypatch.setattr(paper_tables, "population_repos", lambda: {"o/r"})
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
