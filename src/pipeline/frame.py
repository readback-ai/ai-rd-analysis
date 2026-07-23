"""Study frame: the eligible-PR stream every study consumes.

One pass — census cells -> period grouping -> population filter ->
eligibility profile -> classified, capped PR facts — that studies iterate
instead of re-implementing the loop and its guards (before 2026-07 the
same pass existed at ~23 call sites with drifting variants).

Eligibility profiles (see CONTEXT.md):

- "pr" — the human-authored PR population. Skips PRs authored by GitHub
  App accounts (__typename == "Bot": dependabot, renovate, CI, and coding
  agents). Review-behavior studies (fates, attention, responsiveness) use
  this because bot-authored PRs have degenerate review dynamics
  (auto-merged dep bumps would swamp attention metrics). NOTE: this also
  removes layer-B agent-authored PRs from those studies, so their AI
  series compare AI-assisted humans vs unassisted humans — whether that
  is the right semantics is tracked pre-publication (issue #2).
- "author" — attributable human authors. Adds the user-typed-bot hygiene
  on top of "pr": requires a login and rejects is_bot_login matches (bots
  registered as User accounts — found by comment-volume audit — cannot be
  productivity units). Author-level studies use this.
- "all" — no author filtering. Escape hatch for call sites that need the
  full stream (responsiveness anchors are computed over every PR before
  eligibility applies to the sampled lanes).

Iteration order is load-bearing: facts come in group_by_period(...).items()
order with cell lists intact, because the seeded bootstrap RNG stream
(analyze._RNG) reproduces identical CIs only for an identical sequence of
draws.
"""
from collections.abc import Iterable, Iterator
from dataclasses import dataclass

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import MARKERS, PRClass, classify_pr, is_bot_login
from pipeline.org_set import DRV
from pipeline.scan_orgs import QUARTER_RANGES

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
CAP = 20_000    # per-PR LOC cap so one vendored monster can't dominate


def population_repos() -> set[str]:
    return set((DRV / "population_repos.txt").read_text().split())


@dataclass(frozen=True)
class PRFact:
    """What a study needs to know about one eligible PR. The raw census
    dict stays reachable via .pr for study-specific fields."""
    repo: str
    period: str
    pr: dict
    cls: PRClass          # detect.classify_pr result
    loc: int              # additions + deletions, capped at CAP
    author: str | None
    insider: bool         # authorAssociation MEMBER/OWNER/COLLABORATOR
    bot_author: bool      # GitHub App author (__typename == "Bot") — lets
                          # "all"-profile sites apply the "pr" skip mid-
                          # stream (lane_rows anchors)


def _eligible(pr: dict, level: str) -> bool:
    if level == "all":
        return True
    author = pr.get("author") or {}
    if author.get("__typename") == "Bot":
        return False
    if level == "pr":
        return True
    if level == "author":
        return bool(author.get("login")) and not is_bot_login(author["login"])
    raise ValueError(f"unknown eligibility profile: {level!r}")


def study_groups(level: str,
                 periods: Iterable[str] | None = tuple(PERIODS),
                 ranges: dict | None = None,
                 granularity: str = "quarter",
                 ) -> Iterator[tuple[tuple[str, str], list[PRFact]]]:
    """Group-shaped view: ((repo, period), eligible PRFacts) in canonical
    census order, for studies with per-repo floors or rates (slices).
    Groups left empty by the eligibility profile are skipped."""
    pset = None if periods is None else set(periods)
    keep = population_repos()
    for (repo, per), prs in group_by_period(
            load_cells(), ranges or QUARTER_RANGES, granularity).items():
        if repo not in keep or (pset is not None and per not in pset):
            continue
        facts = []
        for p in prs:
            if not _eligible(p, level):
                continue
            c = classify_pr(p, MARKERS)
            a = p.get("author") or {}
            loc = min((p.get("additions") or 0)
                      + (p.get("deletions") or 0), CAP)
            facts.append(PRFact(repo, per, p, c, loc,
                                a.get("login") or None, c.insider,
                                a.get("__typename") == "Bot"))
        if facts:
            yield (repo, per), facts


def study_frame(level: str,
                periods: Iterable[str] | None = tuple(PERIODS),
                ranges: dict | None = None,
                granularity: str = "quarter") -> Iterator[PRFact]:
    """Yield PRFacts for every eligible PR in the population, in the
    canonical census order. `periods` narrows to study periods (pass the
    month set with granularity="month" for monthly callers; None = every
    censused period, e.g. the event study's baseline months); `ranges`
    overrides the quarter map."""
    for _key, facts in study_groups(level, periods, ranges, granularity):
        yield from facts
