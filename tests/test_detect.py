"""Detection semantics: commit markers (layer A), agent authors (B),
branch prefixes (C), and review classification incl. the reviewer!=author
correction (v2_results §11c)."""
from pipeline.detect import (MARKERS_V1, MARKERS_V2, classify_pr,
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


def test_v1_ignores_aider_and_codex_but_v2_detects():
    pr = _pr(messages=["x\n\nCo-authored-by: aider <aider@aider.chat>"],
             emails=["codex@openai.com"])
    assert pr_ai_tools(pr, MARKERS_V1) == set()
    assert pr_ai_tools(pr, MARKERS_V2) == {"aider", "codex"}


def test_v2_detects_codex_cloud_via_committer():
    """Review finding: Codex cloud only appears as the COMMITTER; the old
    query/classifier never saw it."""
    pr = _pr(messages=["normal"])
    pr["commits"]["nodes"][0]["commit"]["committer"] = {
        "email": "", "user": {"login": "chatgpt-codex-connector"}}
    assert pr_ai_tools(pr, MARKERS_V2) == {"codex"}
    assert pr_ai_tools(pr, MARKERS_V1) == set()


def test_marker_specs_have_search_terms_and_needles():
    for spec in MARKERS_V2.values():
        assert spec.search_terms and spec.needles


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
    c = classify_pr(pr)
    assert c.human_reviewed_any and not c.human_reviewed


def test_other_human_review_counts_and_substantive():
    pr = _pr_reviews(reviews=[_rev("bob", state="CHANGES_REQUESTED", comments=2)])
    c = classify_pr(pr)
    assert c.human_reviewed and c.substantive_review


def test_ai_reviewer_decomposed_from_ci_bots():
    pr = _pr_reviews(reviews=[_rev("greptile-apps[bot]", typename="Bot"),
                              _rev("some-ci[bot]", typename="Bot")])
    c = classify_pr(pr)
    assert c.ai_reviewed and c.other_bot_reviewed and not c.human_reviewed


# ------------------------------------------------------------ classify_pr

def test_self_merged_requires_mergedby_field():
    base = _pr_reviews()
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
