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
  agents). Used by review-behavior studies (fates, attention, responsiveness),
  which measure how humans review and respond; bot-authored PRs have
  degenerate review dynamics. Note: this also excludes layer-B agent-authored
  PRs from those studies — whether that is the right semantics for the
  attention/responsiveness AI series is an open pre-publication question
  (see the tracked issue).
- **`author`** — attributable human authors: adds the user-typed-bot hygiene
  (`detect.is_bot_login`) on top of `pr`, because bots registered as User
  accounts (found by comment-volume audit) cannot be productivity units. Used
  by author-level studies (productivity, event studies).
- **`all`** — escape hatch, no author filtering; for call sites that need the
  full stream (e.g. responsiveness anchors are computed over all PRs before
  eligibility applies to sampled lanes).
