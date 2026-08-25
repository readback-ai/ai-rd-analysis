"""Detection semantics: commit markers (layer A), agent authors (B),
branch prefixes (C), and review classification incl. the reviewer!=author
correction (v2_results §11c)."""
from pipeline.detect import (MARKERS, classify_pr,
                             pr_agent_author, pr_ai_tools, pr_branch_tool)



def _pr(messages=(), emails=(), author=None):
    return {
        "author": {"login": author, "__typename": "Bot"} if author else None,
        "commits": {"nodes": [
            {"commit": {"message": m,
                        "authors": {"nodes": [{"email": e} for e in emails]}}}
            for m in messages or [""]
        ]},
    }


def test_detects_claude_coauthor_email():
    pr = _pr(messages=["fix bug"], emails=["dev@x.com", "noreply@anthropic.com"])
    assert pr_ai_tools(pr) == {"claude"}


def test_detects_claude_footer_without_email():
    """Squash-merge often keeps the footer even when trailers are stripped."""
    pr = _pr(messages=["feat: x\n\n🤖 Generated with [Claude Code](https://...)"])
    assert pr_ai_tools(pr) == {"claude"}


def test_detects_cursor_trailer():
    pr = _pr(messages=["Update\n\nCo-authored-by: Cursor <cursoragent@cursor.com>"])
    assert pr_ai_tools(pr) == {"cursor"}


def test_detects_aider_and_codex():
    pr = _pr(messages=["x\n\nCo-authored-by: aider <aider@aider.chat>"],
             emails=["codex@openai.com"])
    assert pr_ai_tools(pr, MARKERS) == {"aider", "codex"}


def test_detects_codex_cloud_via_committer():
    """Review finding: Codex cloud only appears as the COMMITTER; the old
    query/classifier never saw it."""
    pr = _pr(messages=["normal"])
    pr["commits"]["nodes"][0]["commit"]["committer"] = {
        "email": "", "user": {"login": "chatgpt-codex-connector"}}
    assert pr_ai_tools(pr, MARKERS) == {"codex"}


def test_marker_specs_have_search_terms_and_needles():
    for spec in MARKERS.values():
        assert spec.search_terms
        assert spec.needles or spec.identity_needles


def test_plain_pr_detects_nothing():
    assert pr_ai_tools(_pr(messages=["normal commit"], emails=["h@x.com"])) == set()


def test_bot_authored_pr_flagged_only_when_enabled():
    pr = _pr(messages=["done"], author="copilot-swe-agent[bot]")
    assert pr_ai_tools(pr) == set()
    assert pr_ai_tools(pr, include_bot_authors=True) == {"agent:copilot-swe-agent"}


def test_empty_commits_do_not_crash():
    assert pr_ai_tools({"commits": None}) == set()
    assert pr_ai_tools({}) == set()


# ------------------------------------------------------------ layers B & C

def test_agent_author_detected_only_for_bot_typed_accounts():
    assert pr_agent_author({"author": {"login": "copilot-swe-agent[bot]",
                                       "__typename": "Bot"}}) == "copilot-swe-agent"
    # a human account that happens to be named like an agent is NOT layer B
    assert pr_agent_author({"author": {"login": "cursor",
                                       "__typename": "User"}}) is None


def test_branch_prefix_detection():
    assert pr_branch_tool({"headRefName": "codex/fix-tests"}) == "codex"
    assert pr_branch_tool({"headRefName": "claude/peaceful-hertz-1"}) == "claude"
    assert pr_branch_tool({"headRefName": "feature/codex-support"}) is None
    assert pr_branch_tool({}) is None                 # pre-2026-07-08 cells


# ------------------------------------------------------------ review class

def _pr_reviews(author="alice", reviews=()):
    return {"author": {"login": author, "__typename": "User"},
            "commits": {"nodes": []},
            "reviews": {"nodes": list(reviews)}}


def _rev(login, typename="User", state="APPROVED", comments=0):
    return {"author": {"login": login, "__typename": typename},
            "state": state, "comments": {"totalCount": comments}}


def test_self_review_does_not_count_as_human_review():
    pr = _pr_reviews(reviews=[_rev("alice", state="COMMENTED", comments=3)])
    assert not classify_pr(pr).human_reviewed


def test_other_human_review_counts_and_substantive():
    pr = _pr_reviews(reviews=[_rev("bob", state="CHANGES_REQUESTED", comments=2)])
    c = classify_pr(pr)
    assert c.human_reviewed and c.substantive_review


def test_ai_reviewer_decomposed_from_ci_bots():
    pr = _pr_reviews(reviews=[_rev("greptile-apps[bot]", typename="Bot"),
                              _rev("some-ci[bot]", typename="Bot")])
    c = classify_pr(pr)
    assert c.ai_reviewed and c.other_bot_reviewed and not c.human_reviewed


def _bot_authored_pr(author_login, reviews):
    return {"author": {"login": author_login, "__typename": "Bot"},
            "commits": {"nodes": []},
            "reviews": {"nodes": list(reviews)}}


def test_agent_self_review_is_not_ai_review():
    """Issue #9 (spec flag F-16): reviewer!=author was enforced for humans
    but not bots, so an agent's formal review of its OWN PR (cursor, claude
    and copilot-swe-agent sit in both AGENT_PR_AUTHORS and AI_REVIEWERS)
    counted as AI review — pushing the PR out of review_action's clean lane,
    labeling its approval channel botOnly, and inflating ai_review rates.
    A self-review must set neither ai_reviewed nor other_bot_reviewed, and
    logins must compare after [bot] normalization (the author node and the
    review node may disagree about the suffix)."""
    for author, reviewer in (("claude", "claude[bot]"),
                             ("claude[bot]", "claude"),
                             ("cursor[bot]", "cursor[bot]")):
        c = classify_pr(_bot_authored_pr(
            author, [_rev(reviewer, typename="Bot", state="COMMENTED")]))
        assert not c.ai_reviewed, (author, reviewer)
        assert not c.other_bot_reviewed, (author, reviewer)
    # an INDEPENDENT AI reviewer on the agent's PR still counts
    c = classify_pr(_bot_authored_pr(
        "claude", [_rev("claude[bot]", typename="Bot"),
                   _rev("coderabbitai[bot]", typename="Bot")]))
    assert c.ai_reviewed and not c.other_bot_reviewed


def test_bot_self_review_is_not_other_bot_review():
    """Issue #9 (spec flag F-16): the reviewer!=author rule applies to
    non-AI bots too — a CI bot approving its own PR is not independent
    bot review activity."""
    c = classify_pr(_bot_authored_pr(
        "release-bot[bot]", [_rev("release-bot[bot]", typename="Bot")]))
    assert not c.other_bot_reviewed and not c.ai_reviewed


# ------------------------------------------------------------ classify_pr

def test_self_merged_requires_mergedby_field():
    base = dict(_pr_reviews(), createdAt="2026-04-10T00:00:00Z")
    assert classify_pr(base).self_merged is None      # not merged
    merged = dict(base, mergedAt="2026-05-01T00:00:00Z")
    assert classify_pr(merged).self_merged is None    # old cell: no mergedBy
    merged["mergedBy"] = {"login": "alice", "__typename": "User"}
    assert classify_pr(merged).self_merged is True
    merged["mergedBy"] = {"login": "bob", "__typename": "User"}
    assert classify_pr(merged).self_merged is False


def test_ai_involved_union_of_layers():
    pr = _pr_reviews()
    assert not classify_pr(pr).ai_involved
    assert classify_pr(dict(pr, headRefName="codex/x")).ai_involved
    bot = dict(pr, author={"login": "devin-ai-integration[bot]", "__typename": "Bot"})
    assert classify_pr(bot).ai_involved


# ------------------------------------------------------------ study cutoff

def test_event_windowing_is_w8_from_creation():
    """Events count within each PR's 56-day window — including past the
    frame-end CUTOFF (updated 2026-07-20: CUTOFF bounds PR creation, not
    events). Beyond the window they never count."""
    ok = dict(_pr_reviews(), createdAt="2026-04-10T00:00:00Z",
              mergedAt="2026-04-29T01:00:00Z",
              mergedBy={"login": "alice", "__typename": "User"})
    assert classify_pr(ok).merged and classify_pr(ok).self_merged is True
    spill = dict(_pr_reviews(), createdAt="2026-06-20T00:00:00Z",
                 mergedAt="2026-07-02T01:00:00Z",
                 mergedBy={"login": "alice", "__typename": "User"})
    assert classify_pr(spill).merged             # within w8, past frame end
    beyond = dict(_pr_reviews(), createdAt="2026-01-10T00:00:00Z",
                  mergedAt="2026-04-01T00:00:00Z",
                  mergedBy={"login": "alice", "__typename": "User"})
    assert not classify_pr(beyond).merged        # outside w8: never a w8 merge
    assert classify_pr(beyond).merged_ever       # but observed-ever, yes


def test_ci_committed_prefix_branch_is_not_layer_c():
    """Measured FP class: CI automation naming branches claude/* commits via
    github-actions[bot]; must not count as agent attribution."""
    pr = {"headRefName": "claude/canary-llama_index-1",
          "commits": {"nodes": [{"commit": {"committer": {
              "email": "41898282+github-actions[bot]@users.noreply.github.com"}}}]}}
    assert pr_branch_tool(pr) is None
    pr["commits"]["nodes"].append({"commit": {"committer": {"email": "dev@x.com"}}})
    assert pr_branch_tool(pr) == "claude"    # mixed committers still count


def test_strict_layer_c_requires_provenance_on_weak_prefixes():
    """Two-sided-bound lower arm: weak prefixes need web-flow or slug."""
    human_named = {"headRefName": "claude/eval-ci-docs",
                   "commits": {"nodes": [{"commit": {"committer": {"email": "dev@x.com"}}}]}}
    assert pr_branch_tool(human_named) == "claude"          # upper arm counts it
    assert pr_branch_tool(human_named, strict=True) is None  # lower arm drops it
    web_flow = {"headRefName": "claude/eval-ci-docs",
                "commits": {"nodes": [{"commit": {"committer": {"email": "noreply@github.com"}}}]}}
    assert pr_branch_tool(web_flow, strict=True) == "claude"
    slugged = {"headRefName": "cursor/fix-redis-2a9c", "commits": {"nodes": [
        {"commit": {"committer": {"email": "dev@x.com"}}}]}}
    assert pr_branch_tool(slugged, strict=True) == "cursor"


def test_droid_prefix_is_weak_with_date_slug_confirmation():
    """droid/ (Factory) added from the fleet audit: weak prefix; the
    YYYYMMDD suffix Factory appends is the confirming machine slug."""
    dated = {"headRefName": "droid/harden-bootstrap-api-20260504",
             "commits": {"nodes": [
                 {"commit": {"committer": {"email": "dev@x.com"}}}]}}
    assert pr_branch_tool(dated) == "droid"
    assert pr_branch_tool(dated, strict=True) == "droid"
    undated = {"headRefName": "droid/finding-quality-cleanup",
               "commits": {"nodes": [
                   {"commit": {"committer": {"email": "dev@x.com"}}}]}}
    assert pr_branch_tool(undated) == "droid"            # upper arm
    assert pr_branch_tool(undated, strict=True) is None  # lower arm
    # strong prefixes unaffected by strict
    codex = {"headRefName": "codex/fix-tests", "commits": {"nodes": []}}
    assert pr_branch_tool(codex, strict=True) == "codex"


def test_user_typed_bot_accounts_are_not_human_reviewers():
    """Bots registered as User accounts (PaddlePaddle-bot) must not count as
    human review — they inflated the human-comment numerator."""
    pr = _pr_reviews(reviews=[_rev("PaddlePaddle-bot", state="APPROVED"),
                              _rev("qwen-code-ci-bot", state="COMMENTED")])
    c = classify_pr(pr)
    assert not c.human_reviewed and c.other_bot_reviewed
    ok = _pr_reviews(reviews=[_rev("talbot", state="APPROVED")])
    assert classify_pr(ok).human_reviewed          # human name, no false positive


def test_w8_censoring_rule(monkeypatch):
    """Frozen convention: outcomes at 8 weeks post-creation; immature PRs
    carry no fate."""
    from pipeline import detect
    # Pin the data stamp: it advances with every re-pull (METHODS §1c),
    # so which fixture is immature must not ride on its current value.
    monkeypatch.setattr(detect, "AS_OF", "2026-08-01T00:00:00Z")
    base = {"reviews": {"nodes": []}, "commits": {"nodes": []}}
    fast = dict(base, createdAt="2026-01-01T00:00:00Z",
                mergedAt="2026-01-20T00:00:00Z")
    assert classify_pr(fast).merged and classify_pr(fast).w8_mature
    late = dict(base, createdAt="2026-01-01T00:00:00Z",
                mergedAt="2026-04-01T00:00:00Z")     # merged at w13
    c = classify_pr(late)
    assert not c.merged and c.merged_ever and c.w8_mature
    rejected = dict(base, createdAt="2026-01-01T00:00:00Z",
                    closedAt="2026-01-10T00:00:00Z")
    assert classify_pr(rejected).rejected
    immature = dict(base, createdAt="2026-06-20T00:00:00Z",
                    mergedAt="2026-06-21T00:00:00Z")
    assert not classify_pr(immature).w8_mature       # provisional


def test_first_human_ask_requires_changes_or_comments():
    """An APPROVED review with zero inline comments is not an ask."""
    import sys
    sys.path.insert(0, "src")
    from pipeline.studies.review_action import first_human_ask
    pr = _pr_reviews(reviews=[
        _rev("bob", state="APPROVED") | {"submittedAt": "2026-01-05T00:00:00Z"},
        _rev("carol", state="COMMENTED", comments=2) | {"submittedAt": "2026-01-07T00:00:00Z"}])
    pr["reviews"]["nodes"][0]["submittedAt"] = "2026-01-05T00:00:00Z"
    pr["reviews"]["nodes"][1]["submittedAt"] = "2026-01-07T00:00:00Z"
    assert first_human_ask(pr) == "2026-01-07T00:00:00Z"   # skips bare approve
    silent = _pr_reviews(reviews=[_rev("bob", state="APPROVED")])
    assert first_human_ask(silent) is None


def test_review_action_pagination_completeness(monkeypatch):
    """External review P1 round 2: incomplete pagination must return None
    (never checkpoint a truncated record as complete)."""
    from pipeline.studies import review_action as ra
    # missing endCursor with hasNextPage: would loop -> must bail
    monkeypatch.setattr(ra, "graphql_nodes", lambda *a, **k: {
        "nodes": [{}] * 100, "totalCount": 250,
        "pageInfo": {"hasNextPage": True, "endCursor": None}})
    assert ra._all_commits("o/r", 1) is None
    # clean terminal walk short of the API claim: complete-as-retrievable
    # (ghost commits; round 10 — supersedes the round-3 equality rule)
    monkeypatch.setattr(ra, "graphql_nodes", lambda *a, **k: {
        "nodes": [{}] * 90, "totalCount": 250,
        "pageInfo": {"hasNextPage": False, "endCursor": None}})
    assert ra._all_commits("o/r", 1) == ([{}] * 90, 90, 250)
    # exact single page -> (nodes, retrieved, api_total)
    monkeypatch.setattr(ra, "graphql_nodes", lambda *a, **k: {
        "nodes": [{}] * 90, "totalCount": 90,
        "pageInfo": {"hasNextPage": False, "endCursor": None}})
    assert ra._all_commits("o/r", 1) == ([{}] * 90, 90, 90)


def test_review_action_suspect_and_ht_weights():
    from pipeline.studies.review_action import _inv_pi, _suspect
    # legacy 60-cap record: suspect; complete-metadata record: not
    assert _suspect({"commits": [{}] * 60})
    assert _suspect({"commits": [{}] * 200, "commits_total": 250,
                     "commits_complete": True}) is True
    assert not _suspect({"commits": [{}] * 90, "commits_total": 90,
                         "commits_complete": True})
    assert not _suspect({"commits": [{}] * 3})   # small legacy: fine
    # HT: tiny PR nearly never drawn -> huge weight; W-sized PR -> weight 1
    assert _inv_pi(1.0, 1.0, k=1) == 1.0
    big = _inv_pi(1, 1_000_000)
    small = _inv_pi(10_000, 1_000_000)
    assert big > small > 1.0


def test_suspect_flags_metadata_short_records_regardless_of_length():
    """External review P1 round 3 (repro FIRST): a record whose own
    metadata declares it short/incomplete is suspect at ANY length —
    20/50-commit examples previously returned False."""
    from pipeline.studies.review_action import _suspect
    assert _suspect({"commits": [{}] * 20, "commits_total": 250,
                     "commits_complete": True})
    assert _suspect({"commits": [{}] * 50, "commits_complete": False})
    assert _suspect({"commits": [{}] * 90, "commits_complete": True})  # no total
    # complete-and-corroborated stays non-suspect
    assert not _suspect({"commits": [{}] * 20, "commits_total": 20,
                         "commits_complete": True})


def test_batch_connection_validation():
    """Rounds 3/10: the batch pull validates every connection — explicit
    terminal pageInfo and an integer totalCount are required; a terminal
    page short of the API claim is complete-as-retrievable (ghost
    commits), while genuinely partial responses defer."""
    from pipeline.studies.review_action import _conn_commits
    ok = {"nodes": [{}] * 3, "totalCount": 3,
          "pageInfo": {"hasNextPage": False}}
    assert _conn_commits(ok) == ([{}] * 3, 3, 3)
    # missing/non-integer totalCount -> defer
    assert _conn_commits({"nodes": [{}] * 3,
                          "pageInfo": {"hasNextPage": False}}) is None
    # terminal page short of the claim -> complete with ghosts (round 10)
    assert _conn_commits({"nodes": [{}] * 50, "totalCount": 250,
                          "pageInfo": {"hasNextPage": False}}) == \
        ([{}] * 50, 50, 250)
    # hasNextPage=True -> caller must paginate, never accept as-is
    assert _conn_commits({"nodes": [{}] * 100, "totalCount": 250,
                          "pageInfo": {"hasNextPage": True}}) is None
    # missing pageInfo entirely (partial GraphQL response) -> defer
    assert _conn_commits({"nodes": [{}] * 3, "totalCount": 3}) is None


def test_reviews_are_w8_windowed_like_fates():
    """Frozen-convention change 2026-07-20 (repro RED first): review events
    count only within 8 weeks of PR creation, same rule as fates —
    otherwise review rates on old quarters drift whenever the as-of
    advances. A review 9 weeks after creation must NOT count."""
    pr = _pr_reviews(reviews=[
        _rev("bob", state="CHANGES_REQUESTED", comments=2)
        | {"submittedAt": "2024-03-20T00:00:00Z"}])   # 9+ weeks after
    pr["createdAt"] = "2024-01-10T00:00:00Z"
    assert not classify_pr(pr).human_reviewed
    # inside the window it counts
    pr["reviews"]["nodes"][0]["submittedAt"] = "2024-02-20T00:00:00Z"
    c = classify_pr(pr)
    assert c.human_reviewed and c.substantive_review
    # AI reviewers are windowed by the same rule
    late_ai = _pr_reviews(reviews=[
        _rev("coderabbitai[bot]", typename="Bot")
        | {"submittedAt": "2024-04-01T00:00:00Z"}])
    late_ai["createdAt"] = "2024-01-10T00:00:00Z"
    assert not classify_pr(late_ai).ai_reviewed


def test_w8_events_after_frame_end_count_within_window():
    """Repro RED first (external review of w8 semantics): CUTOFF is the
    FRAME end (last PR-creation date), not an event guillotine. A merge or
    review inside a PR's 56-day window counts even when it lands after
    CUTOFF (that is the whole point of the Sept 1 finalization re-pull);
    events are implicitly bounded by CUTOFF + 56d since created <= CUTOFF.
    Three sites: fates (_within_w8), split_reviews, review_action anchors."""
    # 1) fates: created in-frame, merged 20 days later but past CUTOFF
    pr = dict(_pr_reviews(), createdAt="2026-06-20T00:00:00Z",
              mergedAt="2026-07-10T00:00:00Z",
              mergedBy={"login": "alice", "__typename": "User"})
    c = classify_pr(pr)
    assert c.merged and c.merged_ever
    # merged_ever has no as-of cap at all (secondary, "ever observed")
    late = dict(_pr_reviews(), createdAt="2026-04-01T00:00:00Z",
                mergedAt="2026-12-25T00:00:00Z",
                mergedBy={"login": "alice", "__typename": "User"})
    assert classify_pr(late).merged_ever and not classify_pr(late).merged
    # 2) split_reviews: post-CUTOFF review inside the PR's w8 window counts
    pr2 = _pr_reviews(reviews=[
        _rev("bob", state="CHANGES_REQUESTED", comments=1)
        | {"submittedAt": "2026-07-05T00:00:00Z"}])
    pr2["createdAt"] = "2026-06-20T00:00:00Z"
    assert classify_pr(pr2).human_reviewed
    # 3) review_action anchors see the same review as an ask
    from pipeline.studies.review_action import first_human_ask
    assert first_human_ask(pr2) == "2026-07-05T00:00:00Z"


def test_committer_audit_identities_detected():
    """Committer audit 2026-07-20 (RED first): OpenHands, the second
    Cursor cloud identity, and vetted self-identified homegrown agents
    must be layer-A detectable; CI bots must NOT be."""
    def committer(email, login=None):
        pr = _pr(messages=["normal"])
        pr["commits"]["nodes"][0]["commit"]["committer"] = {
            "email": email, "user": {"login": login} if login else None}
        return pr
    assert pr_ai_tools(committer("openhands@all-hands.dev",
                                 "openhands-agent")) == {"openhands"}
    assert pr_ai_tools(committer("agent@cursor.com")) == {"cursor"}
    assert pr_ai_tools(committer("hermes-agent@local")) == {"agent"}
    assert pr_ai_tools(committer("hermes-agent@revenueholdings.ai")) == {"agent"}
    assert pr_ai_tools(committer("agent@modal.com")) == {"agent"}
    assert pr_ai_tools(committer("pragma-agent@modular.com")) == {"agent"}
    # CI/automation identities from the same audit stay UNdetected
    assert pr_ai_tools(committer("xnnpack-github-robot@google.com")) == set()
    assert pr_ai_tools(committer("snyk-bot@snyk.io")) == set()
    assert pr_ai_tools(committer("bot@renovateapp.com")) == set()


def test_agent_suffixed_user_logins_are_bots():
    """openhands-agent commits under a User-typed account; '-agent' joins
    the user-bot suffixes so author/reviewer hygiene catches this class."""
    from pipeline.detect import is_bot_login
    assert is_bot_login("openhands-agent")
    assert is_bot_login("hermes_agent")
    assert not is_bot_login("reagent")        # suffix is hyphen-anchored


def test_w8_maturity_follows_data_as_of_not_frame_end(monkeypatch):
    """Repro RED first: maturity must be judged against detect.AS_OF (the
    data-collection stamp, bumped at re-pulls) — not frame-end CUTOFF —
    else June-2026 PRs stay 'immature' forever and the Sept finalization
    re-pull can never surface their fates."""
    from pipeline import detect
    pr = dict({"author": {"login": "alice", "__typename": "User"},
               "commits": {"nodes": []}, "reviews": {"nodes": []}},
              createdAt="2026-06-20T00:00:00Z",
              mergedAt="2026-07-10T00:00:00Z",
              mergedBy={"login": "alice", "__typename": "User"})
    # Pin BOTH observation points — the contract is that maturity tracks
    # AS_OF, so neither leg may depend on the constant's current value.
    monkeypatch.setattr(detect, "AS_OF", "2026-08-01T00:00:00Z")
    assert not classify_pr(pr).w8_mature          # before the re-pull
    monkeypatch.setattr(detect, "AS_OF", "2026-09-01T00:00:00Z")
    assert classify_pr(pr).w8_mature              # after the Sept re-pull
    assert classify_pr(pr).merged


def test_identity_needles_do_not_match_message_text():
    """Review P2 (RED first): identity markers must match only
    author/committer fields — a version-bump message MENTIONING
    openhands-agent (41 such commits in the store) is not evidence."""
    msg_only = _pr(messages=["chore: bump openhands-agent to 0.9.2"])
    assert pr_ai_tools(msg_only) == set()
    msg_only2 = _pr(messages=["docs: how to configure agent@modal.com runs"])
    assert pr_ai_tools(msg_only2) == set()
    # identity-field hits still detect
    ident = _pr(messages=["normal"])
    ident["commits"]["nodes"][0]["commit"]["committer"] = {
        "email": "openhands@all-hands.dev", "user": {"login": "openhands-agent"}}
    assert pr_ai_tools(ident) == {"openhands"}
    # trailer-based needles (claude co-author) still match message text
    trailer = _pr(messages=["x\n\nCo-authored-by: Claude <noreply@anthropic.com>"])
    assert pr_ai_tools(trailer) == {"claude"}


def test_every_needle_family_is_searchable():
    """Review P1 (RED first): stage 1/2 discovery runs on search_terms —
    every identity in the homegrown 'agent' marker must be discoverable,
    not just hermes."""
    from pipeline.detect import MARKERS
    spec = MARKERS["agent"]
    for ident in spec.identity_needles:            # ALL of them (round 6)
        assert any(ident in t for t in spec.search_terms), ident


def test_scan_cache_key_tracks_marker_fingerprint():
    """Review P1 (RED first): the scan/enum cache tag must change when the
    marker set changes, else stale caches silently omit new-marker
    evidence (reproduced with the OpenHands addition)."""
    from pipeline.detect import MARKERS, marker_fingerprint
    fp = marker_fingerprint()
    assert fp != "v2" and len(fp) >= 6
    extended = dict(MARKERS)
    from pipeline.detect import ToolSpec
    extended["newtool"] = ToolSpec(search_terms=("x@y.z",), needles=("x@y.z",))
    assert marker_fingerprint(extended) != fp


def test_fully_paginated_short_walks_are_complete_with_ghosts(monkeypatch):
    """Round-10 (RED first): GitHub's commits totalCount includes
    force-pushed/rebased-away commits it will never serve (measured:
    NVIDIA-NeMo/Speech#8622 walks cleanly to hasNextPage=false with 250
    of a claimed 281). A clean terminal walk IS complete-as-retrievable;
    commits_total records the RETRIEVED count (the invariant
    len == commits_total holds), commits_api_total keeps the API claim.
    Partial-response protections are unchanged: failed pages, missing
    endCursor, missing pageInfo/totalCount still defer."""
    from pipeline.studies import review_action as ra
    # single terminal page, short of the API claim -> complete w/ ghosts
    conn = {"nodes": [{}] * 90, "totalCount": 95,
            "pageInfo": {"hasNextPage": False}}
    assert ra._conn_commits(conn) == ([{}] * 90, 90, 95)
    # multi-page clean walk, short of the claim -> complete w/ ghosts
    pages = iter([
        {"nodes": [{}] * 100, "totalCount": 281,
         "pageInfo": {"hasNextPage": True, "endCursor": "c1"}},
        {"nodes": [{}] * 50, "totalCount": 281,
         "pageInfo": {"hasNextPage": False, "endCursor": None}}])
    monkeypatch.setattr(ra, "graphql_nodes", lambda *a, **k: next(pages))
    assert ra._all_commits("o/r", 1) == ([{}] * 150, 150, 281)
    # protections unchanged: missing totalCount / pageInfo still defer
    assert ra._conn_commits({"nodes": [{}] * 3,
                             "pageInfo": {"hasNextPage": False}}) is None
    assert ra._conn_commits({"nodes": [{}] * 3, "totalCount": 3}) is None
    # failed page still fails the walk
    monkeypatch.setattr(ra, "graphql_nodes", lambda *a, **k: None)
    assert ra._all_commits("o/r", 1) is None
