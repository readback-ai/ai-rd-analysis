# v2 results — AI-assisted development at leading AI orgs (updated 2026-07-07)

**Weighting policy: every number in this document is contributor-weighted** —
per-repo rates (repos with ≥10 PRs/period; cohort cells need ≥5 PRs) averaged
across repos weighted by core human contributors (≥10 commits, bots excluded;
`data/resume_state/v2/repo_contributors_v2.csv`, 1,994/1,996 repos), with
bootstrap 95% CIs over repos. Markers: v1 (Claude+Cursor) unless noted.
Population: 215 externally-sourced orgs → 1,996 product repos → 7,953/7,984
repo-periods censused (99.6%), 26,819 cells, 0 corrupt. Periods: Q1-2024
(pre-AI baseline), Q4-2025, Q1-2026, Q2-2026 (full quarters).
Earlier pooled/equal-weight versions of these cuts are retained in
`v2_review_trends.md` as secondary views; where they differ, THIS document is
canonical. (Changelog at bottom.)

## 1. Headline metrics by quarter

| period | repos | AI-code PRs | AI review | other-bot review | human review | no review | merged | insider |
|---|---|---|---|---|---|---|---|---|
| Q1-2024 | 485 | 0.0 | 0.4 [0.1,0.9] | 1.6 | 65.9 [62.4,69.4] | 33.4 | 80.1 | 31.3 |
| Q4-2025 | 869 | 1.7 [1.4,2.0] | 18.5 [15.5,21.6] | 4.0 | 66.3 [63.9,68.7] | 28.5 | 74.8 | 36.0 |
| Q1-2026 | 1120 | 7.7 [6.9,8.5] | 22.7 [19.7,25.7] | 4.5 | 61.7 [59.4,64.1] | 30.6 | 70.4 | 34.7 |
| Q2-2026 | 1286 | **11.5 [10.4,12.6]** | **23.5 [20.8,26.6]** | 6.2 | **57.5 [55.0,60.0]** | 33.6 | 65.0 | 34.2 |

- AI-written code: **0 → 11.5%** of PRs in 2¼ years; inflection Q4-2025→Q1-2026.
- AI code review: **0.4 → 23.5%** — AI reviewers (gemini-code-assist,
  copilot-pr-reviewer, coderabbit…) touch ~2× more PRs than AI writes; the
  automation surge is genuinely AI review, not CI bots (other-bot: 1.6→6.2).
- Human review declined modestly, **65.9 → 57.5%** (−8.4pp), and remains the norm.
- Insider share stable ~34% throughout — AI changed how, not who.
- Detection delta v1→v2 markers: 11.5 → 11.6% (+0.1pp) — Claude+Cursor trailers
  capture essentially all detectable public AI-code evidence
  (`analysis_v{1,2}_trueweights.txt`).

## 2. Per-tool detection rate (% of PRs)

| period | repos | Claude Code | Cursor | aider | Codex | any tool |
|---|---|---|---|---|---|---|
| Q1-2024 | 485 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Q4-2025 | 869 | 1.52 [1.22,1.85] | 0.17 [0.09,0.28] | 0.01 | 0.00 | 1.69 [1.37,2.08] |
| Q1-2026 | 1120 | 7.08 [6.37,7.90] | 0.62 [0.46,0.80] | 0.00 | 0.01 | 7.68 [6.92,8.50] |
| Q2-2026 | 1286 | **10.35 [9.32,11.39]** | 1.20 [0.90,1.56] | 0.00 | 0.15 [0.07,0.26] | 11.60 [10.57,12.75] |

Claude Code ≈ 89% of detected AI-code PRs; Cursor second (~7×/2-quarters growth
both); Codex first registers Q2-2026 (0.15%); aider ≈ 0. Floors, asymmetric:
Claude's footer survives squash better, so non-Claude shares are likelier
undercounted. (Markers v2 for this table.)

## 3. Organizational adoption thresholds
Org rate = contributor-weighted mean over its qualifying repos.

| org AI-code rate | Q1-2026 (186 orgs) | Q2-2026 (193 orgs) |
|---|---|---|
| ≥ 10% | 75 — 40.3% | 101 — **52.3%** |
| ≥ 25% | 24 — 12.9% | 41 — **21.2%** |
| ≥ 50% | 3 — 1.6% | 4 — 2.1% |
| ≥ 75% | 1 — 0.5% | 0 — 0.0% |

Adoption broadens in the middle: a majority of orgs now exceed 10% AI-code and
a fifth exceed 25%, but majority-AI orgs stay rare (~2%). Q2 leaders:
character-ai 62%, supertone-inc 60%, imbue-ai 59%, comet-ml 54%.

## 4. Human review of AI-code vs non-AI-code PRs

| period | cohort | repos | human review % | substantive % (of reviewed) |
|---|---|---|---|---|
| Q1-2024 | non-AI | 485 | 65.9 [62.7,69.6] | 41.4 [38.4,44.4] |
| Q4-2025 | AI-code | 97 | 53.4 [44.5,61.9] | 50.0 [39.6,60.0] |
| | non-AI | 869 | 66.4 [63.9,68.9] | 39.1 [36.8,41.2] |
| Q1-2026 | AI-code | 471 | 57.1 [53.2,61.1] | 53.5 [49.7,57.4] |
| | non-AI | 1107 | 61.7 [59.1,64.0] | 40.5 [38.2,43.0] |
| Q2-2026 | AI-code | 685 | **57.0 [53.7,60.4]** | **54.4 [50.7,58.3]** |
| | non-AI | 1261 | **57.4 [55.1,59.7]** | 39.7 [37.3,41.9] |

Human-review RATE reached parity by Q2-2026 (57.0 vs 57.4) — AI-code rising,
non-AI falling. But review DEPTH stays higher on AI code: 54 vs 40% substantive.
AI-code PRs wait longer for first human review (weighted mean of per-repo
medians, Q2: 25.5h vs 16.5h), converging.

## 5. Human review of AI-reviewed vs non-AI-reviewed PRs

| period | cohort | repos | human review % | substantive % (of reviewed) |
|---|---|---|---|---|
| Q1-2024 | no-AI-rev | 484 | 66.0 [62.5,69.5] | 41.2 [38.1,44.2] |
| Q4-2025 | AI-rev | 315 | 79.8 [76.9,82.5] | 59.6 [55.6,63.4] |
| | no | 849 | 62.6 [59.9,65.0] | 35.0 [32.9,37.2] |
| Q1-2026 | AI-rev | 454 | 73.5 [70.5,76.5] | 61.9 [58.2,65.1] |
| | no | 1103 | 57.5 [54.8,59.9] | 33.9 [31.6,36.5] |
| Q2-2026 | AI-rev | 503 | **71.1 [67.4,74.2]** | **61.0 [57.6,64.0]** |
| | no | 1251 | **52.7 [50.3,55.1]** | 31.6 [29.1,34.2] |

**AI review complements human review** (+18pp human-review rate, +29pp
substantive depth on AI-reviewed PRs) — it is not substituting at the PR level.
The aggregate human decline concentrates on PRs receiving neither. On ordinary
(non-AI-reviewed) PRs human review is thinning: 66.0→52.7% rate, 41.2→31.6%
substantive. Selection caveat: AI-reviewer adoption correlates with repo rigor.

## 6. Tool-majority org slice (majority of Q2-2026 AI-code PRs; ≥10 AI PRs)

| group | period | repos | AI-code % | AI-review % | human review % |
|---|---|---|---|---|---|
| Claude-majority (142 orgs) | Q4-2025 | 794 | 1.7 [1.4,2.1] | 18.5 [15.6,21.7] | 66.7 |
| | Q1-2026 | 1026 | 7.7 [6.9,8.6] | 22.8 [19.8,26.2] | 62.5 |
| | Q2-2026 | 1188 | 11.7 [10.6,13.0] | **23.7 [21.0,26.6]** | 58.2 |
| Cursor-majority (7 orgs) | Q4-2025 | 18 | 0.6 [0.2,1.4] | 9.8 [1.6,15.6] | 64.4 |
| | Q1-2026 | 22 | 2.7 [1.8,4.5] | 4.9 [2.0,7.0] | 53.3 |
| | Q2-2026 | 29 | 12.3 [7.9,17.4] | **6.7 [2.3,16.7]** | 55.4 |

AI-code adoption converged (11.7 vs 12.3, overlapping CIs) but the AI-REVIEW gap
is large and robust: 23.7 vs 6.7% — Claude-ecosystem orgs pair AI code with AI
review ~3.5× more. Human-review decline is tool-agnostic. Cursor group is 7
orgs/29 repos — wide CIs; indicative.

## 7. Metric-reconciliation notes
- Pooled population AI-code (Q2-2026) is 13.4%; equal-weight per-repo 15.6%;
  contributor-weighted 11.5%. The spread is the repo-size gradient: smallest-
  quartile repos run 19.5% AI-code vs 12.2% in the largest quartile — AI code
  concentrates in smaller, lower-traffic repos. Every rate must state its
  weighting; this document standardizes on contributor-weighted.
- Orgs below both keep-rule thresholds contribute the low tail (pooled 5.5%);
  there are no high-AI "other tool" orgs (v2-marker delta +0.1pp).

## Caveats
- All rates are floors: squash-merge strips trailers (asymmetrically favoring
  Claude's footer); local tools (Windsurf, Codex CLI default) are invisible.
- 31 repo-periods (0.4%) permanently inaccessible; Q2-2026 mildly
  recency-censored (collected ~1 week after quarter end).
- Population is prominence-selected (externally-sourced, quality-gated orgs
  with detectable AI evidence); Q1-2024 same-repo baseline is the temporal
  control. Review-time metrics are weighted means of per-repo medians.
- Contributor counts are all-time (not window-scoped) — a residual known
  limitation (P1.6).

## Reproducibility
`src/pipeline/` (scan_orgs → enum_repos → precount → census → analyze), all
stages checkpointed to $AIRD_DATA_DIR; inputs/outputs in `data/resume_state/v2/`;
64 tests. Collection ~36h wall (rate-limit bound), zero data loss across
interruptions.

## Changelog
- 2026-07-05: initial results (v1-weight file covered only 174 repos, so
  "contrib-weight" rows were ≈equal-weight; superseded).
- 2026-07-07: true contributor weights for all 1,996 repos; every table
  recomputed. Q2-2026 AI-code 15.2→11.5, human review 47.9→57.5, AI review
  20.7→23.5. Added per-tool rates, org thresholds, CW cohort cuts, CW
  tool-majority slice. Directional findings unchanged throughout.
