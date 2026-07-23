# Domain glossary

Terms with a precise meaning in this codebase. Use these words exactly — in code,
issues, tests, and docs — and don't drift to synonyms.

The study's measurement vocabulary (w8 maturity, AS_OF vs CUTOFF, census cells,
detection layers A/B/C, fleet operators, PPS/HT sampling) is defined in
`docs/METHODS.md` and `docs/CODE_GUIDE.md`; this file only holds terms that name
code structure.

## Study frame

The stream of eligible PRs a study consumes: census cells → period grouping →
population filter → eligibility profile → classified, capped **PR facts**.
Owned by `src/pipeline/frame.py`; studies contain only their accumulation
logic, never their own eligibility guards.

## PR fact

The named per-PR record the study frame yields: `(repo, period, pr, cls, loc,
author, insider, …)` where `cls` is the `detect.classify_pr` result and `loc`
is capped at `frame.CAP`. The raw census `pr` dict stays reachable for
study-specific fields.

## Eligibility profile

The named policy deciding which PRs enter a study frame:

- **`pr`** — the human-authored PR population: excludes PRs authored by GitHub
  App accounts (`__typename == "Bot"`: dependabot, renovate, CI, and coding
  agents). Used by the attention report table (`attention.main`) and the
  orphan studies, where the estimand is how humans review each other.
- **`author`** — attributable human authors: adds the user-typed-bot hygiene
  (`detect.is_bot_login`) on top of `pr`, because bots registered as User
  accounts (found by comment-volume audit) cannot be productivity units. Used
  by author-level studies (productivity, event studies), the Figure 6 role
  (ins/ext) cut, and `channels()` — a Bot's NONE association must not
  pollute the external slice, and a bot pipeline's LOC is not human
  approval behavior.
- **`all`** — no author filtering: population tables (`analyze`, Figure 2,
  layers, slices, bounds), insider-roster sweeps, responsiveness ask
  anchors — AND, per the issue #2 resolution (2026-07-23), the AI-contrast
  review-behavior outputs (Figure 6 by-AI, Figure 7, Figure 8, fates'
  AI/nonAI cohorts) with fleet-operator exclusion: human attention and
  responsiveness are defined regardless of who authored the PR, so
  agent-authored (layer-B) PRs count in the AI series. For agent-authored
  PRs, Figure 8 "responsiveness" means the agent/operator pushes commits
  after a human ask.
