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
v2_results §11c; the legacy any-User variant was removed 2026-07-20).
AI review = Bot-typed reviewer in
AI_REVIEWERS (dedicated review bots), decomposed from other CI bots.
"""
from __future__ import annotations

from dataclasses import dataclass

# CUTOFF is the FRAME end (last PR-creation date; never changes). Events
# — merges, closes, reviews — are NOT bounded by it: they count within
# each PR's 56-day window (METHODS §0/§2). Residual: census cells do not
# carry per-commit timestamps, so a marker-bearing commit pushed to a
# still-open in-window PR after collection is not filterable (layer A
# only; exposure grows with re-collection lag).
CUTOFF = "2026-06-30T23:59:59Z"
# AS_OF: the data-collection stamp — when the census cells were last
# (re-)pulled. Governs w8 MATURITY only (a PR's fate is reportable once
# its 56-day window closed before we last looked). Kept conservatively at
# the frame end while the initial 2026-07-01..09 collection stands; BUMP
# at each re-pull (monthly updates, the 2026-09-01 Q2 finalization) to
# the run's start date — mature PRs are immutable, so bumping only ever
# ADDS newly-mature PRs (METHODS §1c).
AS_OF = "2026-08-01T00:00:00Z"

# FROZEN CENSORING RULE (METHODS conventions): all per-PR outcomes are
# measured at 8 WEEKS after PR creation. The maturity curves show merges
# quiesce by w8 (98-99% of eventual merges in every cohort), so a uniform
# w8 horizon removes right-censoring bias from cross-period comparisons.
# A PR is w8-MATURE iff its 8-week window closed on or before the cutoff;
# fate metrics are undefined (None -> skipped) on immature PRs, which is
# what makes trailing-edge quarters PROVISIONAL until re-observed.
W8_DAYS = 56


def _iso(ts: str):
    from datetime import datetime
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def _within_w8(created: str, event: str | None) -> bool:
    """Event inside the PR's 56-day window. CUTOFF bounds PR CREATION
    (the frame), not events: an event within the window counts even when
    it lands after CUTOFF — implicitly capped at CUTOFF + 56d since every
    in-frame PR has created <= CUTOFF. This is what lets the Sept 2026
    re-pull finalize Q2 — only the AS_OF data stamp advances; the frame
    and every rule stay fixed."""
    if not event:
        return False
    return (_iso(event) - _iso(created)).days < W8_DAYS

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
    needles: tuple[str, ...]              # matched in message + identity text
    identity_needles: tuple[str, ...] = ()  # matched ONLY in author/committer
                                            # fields (a message MENTIONING an
                                            # identity is not evidence)


# The canonical marker set (one set; the v1/v2 versioning was collapsed
# 2026-07-20).
MARKERS = {
    "claude": ToolSpec(
        search_terms=("noreply@anthropic.com", '"Generated with [Claude Code]"'),
        needles=("noreply@anthropic.com", "Generated with [Claude Code]")),
    "cursor": ToolSpec(
        search_terms=("cursoragent@cursor.com", "agent@cursor.com"),
        needles=("cursoragent@cursor.com", "agent@cursor.com")),
}
# Codex cloud commits VIA the bot committer, needing qualifier search + the
# committer field in the census GraphQL query (bare terms only match message
# text, and the bot never appears there).
MARKERS |= {
    "aider": ToolSpec(
        search_terms=('"Co-authored-by: aider"',),
        needles=("Co-authored-by: aider",)),
    "codex": ToolSpec(
        search_terms=("committer:chatgpt-codex-connector[bot]",
                      "author-email:codex@openai.com"),
        needles=("codex@openai.com", "chatgpt-codex-connector")),
}
# Committer-identity audit additions (2026-07-20; full-store sweep of
# agent-like committers not matched above — METHODS §2). "openhands" is a
# commercial coding agent; "agent" is the VETTED list of self-identified
# homegrown agent identities (each hand-checked — CI/release bots from the
# same audit, e.g. snyk-bot/renovate/xnnpack, are deliberately absent).
MARKERS |= {
    "openhands": ToolSpec(
        search_terms=("author-email:openhands@all-hands.dev",
                      "committer:openhands-agent"),
        needles=(),
        identity_needles=("openhands@all-hands.dev", "openhands-agent")),
    # SEARCH-SIDE CAVEAT: GitHub commit search has no committer-email
    # qualifier, and these are committer identities — author-email: terms
    # under-recall them (only commits AUTHORED under the identity match).
    # Search terms here are discovery/admission heuristics and a FLOOR;
    # census-side pr_ai_tools (identity_needles against actual
    # author/committer fields) is the authoritative classifier.
    "agent": ToolSpec(
        search_terms=("author-email:hermes-agent@local",
                      "author-email:agent@hermes",
                      "author-email:agent@qwenpaw.local",
                      "author-email:agent@modal.com",
                      "author-email:agent@deepagents.dev",
                      "author-email:pragma-agent@modular.com",
                      "author-email:agent@example.com",
                      "author-email:bot@imbue.com"),
        needles=(),
        identity_needles=("hermes-agent@", "agent@hermes", "agent@modal.com",
                          "agent@deepagents.dev", "pragma-agent@modular.com",
                          "agent@qwenpaw.local", "agent@example.com",
                          "bot@imbue.com")),
}


def marker_fingerprint(markers: dict[str, ToolSpec] = None) -> str:
    """Content-derived cache tag for scan/enum stages: any change to the
    marker set (tools, terms, needles) changes the tag, so stale caches
    can never silently omit new-marker evidence (external review P1)."""
    import hashlib
    m = markers if markers is not None else MARKERS
    blob = "|".join(f"{t}:{','.join(sp.search_terms)}:{','.join(sp.needles)}"
                    f":{','.join(sp.identity_needles)}"
                    for t, sp in sorted(m.items()))
    return "m" + hashlib.sha256(blob.encode()).hexdigest()[:10]


def pr_ai_tools(pr: dict, markers: dict[str, ToolSpec] = MARKERS,
                include_bot_authors: bool = False) -> set[str]:
    """Layer A: which AI tools left commit-marker evidence in this PR
    (search-API PullRequest node with commits{nodes{commit{message
    authors{...} committer{...}}}})."""
    found: set[str] = set()
    for c in (pr.get("commits") or {}).get("nodes") or []:
        commit = c.get("commit") or {}
        ident = ""
        for a in (commit.get("authors") or {}).get("nodes") or []:
            ident += "\n" + ((a or {}).get("email") or "")
        committer = commit.get("committer") or {}
        ident += "\n" + (committer.get("email") or "")
        ident += "\n" + (((committer.get("user") or {}).get("login")) or "")
        # trailer/footer needles live in message text (co-author trailers
        # ARE message text); identity needles match only identity fields
        hay = (commit.get("message") or "") + ident
        for tool, spec in markers.items():
            if any(n in hay for n in spec.needles) \
                    or any(n in ident for n in spec.identity_needles):
                found.add(tool)
    if include_bot_authors:
        agent = pr_agent_author(pr)
        if agent:
            found.add(f"agent:{agent}")
    return found


# ---------------------------------------------------------------- layer B

# PR authors that are coding agents. Bot-authored PRs MAY carry no
# trailer (many do: Claude Code web produces A markers on B-authored
# PRs — the layered decomposition makes B win; see studies.layers).
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
    "droid": "droid/",   # Factory Droid; added 2026-07-17 (fleet audit)
}
# Measured C-only precision is ~95%+ for codex//copilot/ but cursor//claude/
# carry an INDETERMINATE mass (user-pushed commits on a prefix branch:
# agent-branch-continued-locally and human-named-branch are observationally
# identical). These are the study's only potential OVERCOUNT; the headline is
# therefore reported as a two-sided bound (studies.slices --table bounds).
WEAK_PREFIXES = {"cursor", "claude", "droid"}
_SLUG = {
    "codex": __import__("re").compile(r"^codex/[a-z0-9][a-z0-9-]*$"),
    "cursor": __import__("re").compile(r"^cursor/.+-[0-9a-f]{4}$"),
    "claude": __import__("re").compile(r"^claude/(issue-\d+|[a-z]+-[a-z]+-[0-9a-f]{4,})"),
    "copilot": __import__("re").compile(r"^copilot/[a-z0-9][a-z0-9-]*$"),
    # Factory appends a YYYYMMDD slug to generated branches
    "droid": __import__("re").compile(r"^droid/.+-20\d{6}$"),
}


def branch_provenance_confirmed(pr: dict, tool: str) -> bool:
    """Positive provenance for a prefix branch: an agent-cloud web-flow
    committer on any commit, or the product's machine-slug pattern."""
    for c in (pr.get("commits") or {}).get("nodes") or []:
        email = ((c.get("commit") or {}).get("committer") or {}).get("email")
        if email == "noreply@github.com":
            return True
    return bool(_SLUG[tool].match(pr.get("headRefName") or ""))


def pr_branch_tool(pr: dict, strict: bool = False) -> str | None:
    """Layer C: the agent whose branch-naming convention the PR's head branch
    matches, if any. headRefName is present on every PR in the store
    (verified over all 712k PRs, 2026-07-20); absence is tolerated
    defensively and returns None.

    Measured false-positive class excluded: PRs whose commits are ALL
    committed by github-actions[bot] — CI automation that names branches
    after the product (e.g. claude/canary-*) without any agent involvement;
    18.4% of C-only claude/ samples (studies.layer_c_precision).

    strict=True additionally requires positive provenance for the WEAK
    prefixes (cursor/, claude/) — the lower arm of the two-sided bound."""
    head = pr.get("headRefName") or ""
    for tool, prefix in BRANCH_PREFIXES.items():
        if head.startswith(prefix):
            emails = [((c.get("commit") or {}).get("committer") or {}).get("email") or ""
                      for c in (pr.get("commits") or {}).get("nodes") or []]
            if emails and all(e.endswith("github-actions[bot]@users.noreply.github.com")
                              for e in emails):
                return None
            if strict and tool in WEAK_PREFIXES \
                    and not branch_provenance_confirmed(pr, tool):
                return None
            return tool
    return None


# ---------------------------------------------------------------- review

# Bots registered as regular User accounts (invisible to __typename=Bot):
# suffix heuristic, hyphen/underscore-anchored so human names like
# "talbot" never match. Found by comment-volume audit (PaddlePaddle-bot,
# all-hands-bot, qwen-code-ci-bot).
_USER_BOT_SUFFIXES = ("-bot", "_bot", "[bot]", "-ci", "-robot",
                      "-agent", "_agent")


def is_bot_login(login: str | None) -> bool:
    lo = (login or "").lower()
    return lo.endswith(_USER_BOT_SUFFIXES) or lo.startswith("bot-")


AI_REVIEWERS = {  # dedicated AI code-review bots seen in the data (extend as found)
    "gemini-code-assist", "copilot-pull-request-reviewer", "coderabbitai",
    "greptile-apps", "qodo-merge-pro", "cursor", "chatgpt-codex-connector",
    "copilot-swe-agent", "claude",
}
INSIDER = {"MEMBER", "OWNER", "COLLABORATOR"}


def split_reviews(pr: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """-> (human_other, human_self, bot) formal review objects. Review
    events follow the SAME w8 rule as fates (frozen convention, adopted
    2026-07-20): a review counts only if submitted within 8 weeks of PR
    creation AND on or before the as-of — so every per-PR quantity
    finalizes at w8 and advancing the as-of never changes mature numbers.
    PRs lacking createdAt (legacy fixtures) fall back to the as-of bound
    alone.

    The reviewer!=author rule applies to bots as it does to humans: a bot
    review by the PR's own author (coding agents post self-summaries as
    formal review objects) is not independent review activity and is
    excluded from the bot bucket. Bot logins compare after [bot]
    normalization — the author and review nodes can disagree about the
    suffix."""
    author = (pr.get("author") or {}).get("login")
    created = pr.get("createdAt") or ""
    human_other, human_self, bot = [], [], []
    for r in (pr.get("reviews") or {}).get("nodes") or []:
        ra = r.get("author")
        if not ra:
            continue
        sub = r.get("submittedAt") or ""
        if created:
            if not _within_w8(created, sub or None):
                continue
        elif sub and (_iso(sub) - _iso(CUTOFF)).days >= W8_DAYS:
            continue          # no createdAt (legacy fixture): frame end + w8
        if ra["__typename"] == "User" and not is_bot_login(ra.get("login")):
            (human_self if ra.get("login") == author else human_other).append(r)
        elif author and (ra.get("login") or "").removesuffix("[bot]") \
                == author.removesuffix("[bot]"):
            pass              # bot self-review: reviewer == PR author
        else:
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
    merged: bool                      # merged WITHIN 8 WEEKS of creation
    merged_ever: bool                 # merged at ANY observed time (secondary;
                                      #   differs from merged on >56d merges)
    rejected: bool                    # closed unmerged within 8 weeks
    w8_mature: bool                   # 8-week window closed by the cutoff
    self_merged: bool | None          # None when the cell lacks mergedBy
    insider: bool
    human_reviewed: bool              # User reviewer != PR author
    substantive_review: bool          # of the reviewer!=author reviews
    ai_reviewed: bool
    other_bot_reviewed: bool

    @property
    def ai_involved(self) -> bool:
        """Union of all three detection layers."""
        return bool(self.marker_tools) or self.agent_author is not None \
            or self.branch_tool is not None


def classify_pr(pr: dict, markers: dict[str, ToolSpec] = MARKERS) -> PRClass:
    human_other, human_self, bot = split_reviews(pr)
    ai_rev = [r for r in bot
              if (r["author"].get("login") or "").removesuffix("[bot]") in AI_REVIEWERS]
    author = (pr.get("author") or {}).get("login")
    created = pr.get("createdAt") or ""
    merged_ever = bool(pr.get("mergedAt"))
    merged = bool(created) and _within_w8(created, pr.get("mergedAt"))
    rejected = (not merged_ever and bool(created)
                and _within_w8(created, pr.get("closedAt")))
    w8_mature = bool(created) and \
        (_iso(AS_OF) - _iso(created)).days >= W8_DAYS
    merged_by = pr.get("mergedBy")
    self_merged = None
    if merged and merged_by is not None:
        self_merged = (merged_by or {}).get("login") == author and author is not None
    return PRClass(
        marker_tools=frozenset(pr_ai_tools(pr, markers)),
        agent_author=pr_agent_author(pr),
        branch_tool=pr_branch_tool(pr),
        merged=merged,
        merged_ever=merged_ever,
        rejected=rejected,
        w8_mature=w8_mature,
        self_merged=self_merged,
        insider=pr.get("authorAssociation") in INSIDER,
        human_reviewed=bool(human_other),
        substantive_review=substantive(human_other),
        ai_reviewed=bool(ai_rev),
        other_bot_reviewed=len(ai_rev) < len(bot),
    )
