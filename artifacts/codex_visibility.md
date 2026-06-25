# Codex commit visibility & undercount estimate (Phase 0.1 finding)

Measured 2026-06-24 against the live GitHub Search Commits API (global, pre
AI-R&D filtering). Purpose: quantify how much Codex usage is recoverable from
commit metadata, given that Codex adds NO attribution by default
(openai/codex#9449; the actual commit identity is the user's Git setup).

## Codex attribution signals, ranked by prevalence

| Signal | Visible commits | Source |
| --- | --- | --- |
| `author-email:codex@openai.com`        | 118,685 | opt-in identity (christiantietze.de, Mar 2026) |
| `committer-email:codex@openai.com`     | 115,921 | same (author==committer on most) |
| `author-email:noreply@openai.com`      | 4,589   | older CLI variant ("OpenAI"/"Codex"/"GPT Codex") |
| `committer-email:noreply@openai.com`   | 3,741   | same |
| `committer:chatgpt-codex-connector[bot]` | 556   | cloud Codex (GitHub App) |

Combined visible Codex ≈ **~120k commits**, dominated by the opt-in
`codex@openai.com` identity. Sample author names are clean ("Codex",
"OpenAI Codex"), so false positives on that email are negligible.

## The opt-in convention is recent — historical Codex is unrecoverable

`codex@openai.com` commits by committer-date:

| Window | Commits |
| --- | --- |
| before 2026-01-01      | 1,592 |
| 2026-01..02            | 2,231 |
| 2026-03 (blog)         | 10,849 |
| 2026-04                | 18,352 |
| 2026-05                | 42,214 |
| 2026-06 (partial)      | 43,449 |

The convention barely existed before the March 2026 blog post; adoption is
ramping but young.

## Undercount magnitude (vs Claude Code, default-on baseline)

Claude Code writes `Co-Authored-By: Claude <noreply@anthropic.com>` by default,
so it is a near-complete baseline:

| Window | Codex visible | Claude Code | Codex / Claude |
| --- | --- | --- | --- |
| 2026-05      | 42,214 | 1,419,008 | 3.0% |
| 2026-06 (p)  | 43,449 | 1,270,139 | 3.4% |

Both are flagship agents from the two leading labs, so real usage is plausibly
the same order of magnitude. Under that assumption, Codex commit-level
visibility is **~3% of true volume (a ~30x undercount) at best, and effectively
0% before March 2026**. Even if true Codex usage were materially lower than
Claude Code's, visibility would still sit in the low-single-digit percent.

## Implications for the pipeline

1. Codex volume must be reported as an **attributed-only lower bound** with a
   stated, unquantifiable dark figure — never as a headline count.
2. The recoverable slice is **biased** (self-selected to users who configured
   audit-trail attribution), so Codex cohort stats are not representative of
   Codex usage at large. Ship this caveat with every Codex chart.
3. Time trends for Codex conflate *adoption of the attribution convention* with
   *adoption of Codex itself*. Do not present a rising Codex line without this
   disclaimer; the rise is mostly attribution uptake.
4. Detection set for Stage 0 commit-search seed (Codex):
   author/committer-email in {`codex@openai.com`, `noreply@openai.com`} OR
   committer `chatgpt-codex-connector[bot]`.

Sources:
- openai/codex#9449 (no default attribution; maintainer statement)
- christiantietze.de/posts/2026/03/identify-codex-cli-git-commits-for-audit-trail/
- Empirical test: chain-ml/agent-reputation (0 Codex commits detected pre-finding)
