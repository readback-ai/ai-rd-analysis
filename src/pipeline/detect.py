"""How AI contribution and AI/human review are DETECTED — the single home.

Three independent detection layers, reported disjointly by classify_pr:

A. COMMIT MARKERS (strongest evidence, commit-forensic): co-author trailers,
   generation footers, and tool author/committer identities inside a PR's
   commits. Floors — squash-merge strips trailers, and default local Codex CLI
   leaves no marker at all (openai/codex#9449).
B. AGENT PR AUTHORS: PRs authored by coding-agent bot accounts (Copilot
   coding agent, Devin, Jules, ...). No trailer needed; the author IS the tool.
C. BRANCH PREFIXES (PR-level, PRarena-style): agent web/cloud flows create
   head branches named codex/*, copilot/*, cursor/*, claude/*. Commits carry
   USER identity, so layer A misses these entirely. Empirically clean in this
   population: zero prefix-named PRs in Q1-2024, before the products existed.
   PR-level attribution only — no commit-level proof, CLI vs cloud unknown.

Layer overlaps measured on org-stratified samples (2026-07): A∩C ≈ 2%,
B∩C high for copilot/ (the bot authors those PRs) — integrate.py corrects.

Review classification: a PR counts as HUMAN-REVIEWED only if a User-typed
account OTHER THAN THE PR AUTHOR submitted a formal review (GitHub allows
self-review-comments; counting them inflated the self-merge lane —
v2_results §11c). human_reviewed_any keeps the legacy (any-User) definition
that published tables §1/§4/§5 used. AI review = Bot-typed reviewer in
AI_REVIEWERS (dedicated review bots), decomposed from other CI bots.
"""
from __future__ import annotations

from dataclasses import dataclass

# Study cutoff: events after this instant are excluded from classification
# even when the API returns them (collection ran days after the cutoff, so
# late merges/reviews would otherwise leak in — METHODS §0). Residual: census
# cells do not carry per-commit timestamps, so a marker-bearing commit pushed
# to a still-open PR after the cutoff is not filterable; PRs are
# creation-windowed, so the exposure is days and affects layer A only.
CUTOFF = "2026-06-30T23:59:59Z"

# ---------------------------------------------------------------- layer A

@dataclass(frozen=True)
class ToolSpec:
    """One AI tool's commit-marker identity.
    search_terms: full commit-search query fragments (bare trailer terms —
      the author-email: qualifier returns 0 for co-authored commits — or
      qualifier terms for tools that ARE the author/committer, e.g. Codex
      cloud's bot committer). Stage counts use max-over-terms: terms overlap
      on the same commits, so summing double-counts; max is an honest floor.
    needles: substrings matched against a PR's commit messages + author AND
      committer emails/logins by pr_ai_tools."""
    search_terms: tuple[str, ...]
    needles: tuple[str, ...]


# v1 marker set: what every published Phase-0 number used (comparability).
MARKERS_V1 = {
    "claude": ToolSpec(
        search_terms=("noreply@anthropic.com", '"Generated with [Claude Code]"'),
        needles=("noreply@anthropic.com", "Generated with [Claude Code]")),
    "cursor": ToolSpec(
        search_terms=("cursoragent@cursor.com",),
        needles=("cursoragent@cursor.com",)),
}
# v2 adds aider + Codex (delta on headline: +0.1pp — see v2_results §1).
# Codex cloud commits VIA the bot committer need qualifier search + the
# committer field in the census GraphQL query (bare terms only match message
# text, and the bot never appears there).
MARKERS_V2 = MARKERS_V1 | {
    "aider": ToolSpec(
        search_terms=('"Co-authored-by: aider"',),
        needles=("Co-authored-by: aider",)),
    "codex": ToolSpec(
        search_terms=("committer:chatgpt-codex-connector[bot]",
                      "author-email:codex@openai.com"),
        needles=("codex@openai.com", "chatgpt-codex-connector")),
}


def pr_ai_tools(pr: dict, markers: dict[str, ToolSpec] = MARKERS_V1,
                include_bot_authors: bool = False) -> set[str]:
    """Layer A: which AI tools left commit-marker evidence in this PR
    (search-API PullRequest node with commits{nodes{commit{message
    authors{...} committer{...}}}})."""
    found: set[str] = set()
    for c in (pr.get("commits") or {}).get("nodes") or []:
        commit = c.get("commit") or {}
        hay = commit.get("message") or ""
        for a in (commit.get("authors") or {}).get("nodes") or []:
            hay += "\n" + ((a or {}).get("email") or "")
        committer = commit.get("committer") or {}
        hay += "\n" + (committer.get("email") or "")
        hay += "\n" + (((committer.get("user") or {}).get("login")) or "")
        for tool, spec in markers.items():
            if any(n in hay for n in spec.needles):
                found.add(tool)
    if include_bot_authors:
        agent = pr_agent_author(pr)
        if agent:
            found.add(f"agent:{agent}")
    return found


# ---------------------------------------------------------------- layer B

# PR authors that are coding agents (bot-authored PRs carry no trailer).
AGENT_PR_AUTHORS = {
    "copilot-swe-agent", "devin-ai-integration", "cursor", "google-labs-jules",
    "codegen-sh", "amazon-q-developer", "factory-droid", "claude",
}


def pr_agent_author(pr: dict) -> str | None:
    """Layer B: the coding-agent bot that authored this PR, if any."""
    author = pr.get("author") or {}
    if author.get("__typename") != "Bot":
        return None
    login = (author.get("login") or "").removesuffix("[bot]")
    return login if login in AGENT_PR_AUTHORS else None


# ---------------------------------------------------------------- layer C

# head-branch prefixes created by agent web/cloud flows (PRarena-style).
BRANCH_PREFIXES = {
    "codex": "codex/",
    "copilot": "copilot/",
    "cursor": "cursor/",
    "claude": "claude/",
}


def pr_branch_tool(pr: dict) -> str | None:
    """Layer C: the agent whose branch-naming convention the PR's head branch
    matches, if any. Requires headRefName in the PR node (census cells pulled
    before 2026-07-08 lack it)."""
    head = pr.get("headRefName") or ""
    for tool, prefix in BRANCH_PREFIXES.items():
        if head.startswith(prefix):
            return tool
    return None


# ---------------------------------------------------------------- review

AI_REVIEWERS = {  # dedicated AI code-review bots seen in the data (extend as found)
    "gemini-code-assist", "copilot-pull-request-reviewer", "coderabbitai",
    "greptile-apps", "qodo-merge-pro", "cursor", "chatgpt-codex-connector",
    "copilot-swe-agent", "claude",
}
INSIDER = {"MEMBER", "OWNER", "COLLABORATOR"}


def split_reviews(pr: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """-> (human_other, human_self, bot) formal review objects submitted on
    or before the study CUTOFF."""
    author = (pr.get("author") or {}).get("login")
    human_other, human_self, bot = [], [], []
    for r in (pr.get("reviews") or {}).get("nodes") or []:
        ra = r.get("author")
        if not ra:
            continue
        if (r.get("submittedAt") or "") > CUTOFF:
            continue
        if ra["__typename"] == "User":
            (human_self if ra.get("login") == author else human_other).append(r)
        elif ra["__typename"] == "Bot":
            bot.append(r)
    return human_other, human_self, bot


def substantive(reviews: list[dict]) -> bool:
    """A review with inline comments or a non-approve state — more than a
    rubber-stamp APPROVED."""
    return any(((r.get("comments") or {}).get("totalCount", 0) > 0)
               or r.get("state") in ("COMMENTED", "CHANGES_REQUESTED")
               for r in reviews)


# ---------------------------------------------------------------- classify

@dataclass(frozen=True)
class PRClass:
    """Everything metrics need about one PR, computed once.
    Detection layers are kept separate so metrics can report them disjointly
    (marker-attributed / agent-authored / branch-only) — see integrate.py."""
    marker_tools: frozenset[str]      # layer A
    agent_author: str | None          # layer B
    branch_tool: str | None           # layer C (None when headRefName absent)
    merged: bool
    self_merged: bool | None          # None when the cell lacks mergedBy
    insider: bool
    human_reviewed: bool              # User reviewer != PR author (corrected)
    human_reviewed_any: bool          # any User reviewer (legacy, published §1/§4/§5)
    substantive_review: bool          # of the reviewer!=author reviews
    ai_reviewed: bool
    other_bot_reviewed: bool

    @property
    def ai_involved(self) -> bool:
        """Union of all three detection layers."""
        return bool(self.marker_tools) or self.agent_author is not None \
            or self.branch_tool is not None


def classify_pr(pr: dict, markers: dict[str, ToolSpec] = MARKERS_V1) -> PRClass:
    human_other, human_self, bot = split_reviews(pr)
    ai_rev = [r for r in bot
              if (r["author"].get("login") or "").removesuffix("[bot]") in AI_REVIEWERS]
    author = (pr.get("author") or {}).get("login")
    merged = bool(pr.get("mergedAt")) and (pr.get("mergedAt") or "") <= CUTOFF
    merged_by = pr.get("mergedBy")
    self_merged = None
    if merged and merged_by is not None:
        self_merged = (merged_by or {}).get("login") == author and author is not None
    return PRClass(
        marker_tools=frozenset(pr_ai_tools(pr, markers)),
        agent_author=pr_agent_author(pr),
        branch_tool=pr_branch_tool(pr),
        merged=merged,
        self_merged=self_merged,
        insider=pr.get("authorAssociation") in INSIDER,
        human_reviewed=bool(human_other),
        human_reviewed_any=bool(human_other or human_self),
        substantive_review=substantive(human_other),
        ai_reviewed=bool(ai_rev),
        other_bot_reviewed=len(ai_rev) < len(bot),
    )
