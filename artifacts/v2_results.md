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

## 8. The no-human-review mass, stratified (added 2026-07-07; human-authored PRs only, bot authors excluded)

Hypothesis tested (Ron): pre-AI no-review mass is mostly insider-trivial; if the
growing 2026 mass is not, the aggregate drift becomes a strong finding.
Strata: insider (MEMBER/OWNER/COLLABORATOR) vs external; size trivial (<=10
changed lines) / mid (11-100) / substantial (>100). CW throughout.

### Composition of no-human-review PRs
| period | ins-triv | ins-mid | ins-subst | ext-triv | ext-mid | ext-subst | AI-rev covered | AI-code |
|---|---|---|---|---|---|---|---|---|
| Q1-2024 | 12.2 | 11.0 | 12.5 | 21.1 | 20.7 | 22.4 | 0.3 | 0.0 |
| Q4-2025 | 10.6 | 11.2 | 17.3 | 15.7 | 17.5 | 27.6 | 15.4 | 2.6 |
| Q1-2026 | 9.1 | 10.5 | 17.8 | 13.6 | 19.3 | 29.8 | 20.5 | 9.7 |
| Q2-2026 | 7.6 | 10.0 | **17.5** | 12.6 | 20.4 | **31.8** | 21.0 | 13.4 |

### P(no human review | stratum)
| period | insider-trivial | insider-subst | external-trivial | external-subst |
|---|---|---|---|---|
| Q1-2024 | 32.9 [28.3,37.7] | 28.0 [24.0,32.3] | 32.7 [28.8,37.0] | 27.7 [24.1,31.5] |
| Q4-2025 | 32.6 | 28.6 | 30.4 | 31.0 |
| Q1-2026 | 35.5 | 32.1 | 36.3 | 35.9 |
| Q2-2026 | 38.5 [34.5,42.8] | 32.7 [29.7,35.7] | 40.4 [37.3,43.8] | **41.1 [38.6,43.7]** |

### Merged without human review (the risk mass)
Substantial share rose 27.4% -> 40.0%; insider-substantial nearly DOUBLED
(12.3 -> 23.7%); AI-written share 0 -> 15.0%; AI review covers only ~20% of the
mass (i.e., ~80% of merged-unreviewed code gets no review of any kind).

### Findings
1. **The hypothesized insider-trivial pre-AI mass was already a minority**
   (12.2% in Q1-2024; the 2024 unreviewed mass was ~64% external, size-mixed).
2. **The directional claim confirms strongly**: unreviewed PRs are getting
   BIGGER — substantial (>100-line) share of the unreviewed mass grew from
   ~35% to ~49%; trivial share fell 33% -> 20%.
3. **No-review rates rose in every stratum, but ~3x faster for
   external-substantial** (+13.4pp, 27.7 -> 41.1) than insider-substantial
   (+4.7pp) — large external contributions are the fastest-growing unreviewed
   class. Bot-author confound excluded (results ~identical with bots dropped).
4. In the merged risk mass, insider-substantial doubled and 15% is AI-written
   (slightly above the 11.5% population AI-code rate) — unreviewed merged code
   is increasingly big, insider, and AI-assisted, with AI review covering only
   a fifth of it.

## 9. SPIKE: what ARE the unreviewed-substantial PRs? (2026-07-07; small-N, pooled)

Sample: merged, human-authored, >100-line, no-human-review PRs — 120 (Q1-2024) +
200 (Q2-2026), lines-weighted dominant-content classification of file paths.
Population context (pooled, from cells): this mass grew 5,766 -> 32,717 PRs
(5.7x); AI-review coverage 0.4% -> 23.9%; AI-written 0 -> 19.6%.

| dominant content | Q1-2024 | Q2-2026 | Q2 insider | Q2 AI-code | Q2 AI-rev |
|---|---|---|---|---|---|
| **source code** | **61.7%** | **64.0%** | 71% | 19% | 31% |
| docs | 15.0% | 18.0% | 69% | 33% | 17% |
| lock/generated | 5.0% | 5.5% | 82% | 9% | 36% |
| config/CI | 3.3% | 5.0% | 30% | 20% | 10% |
| other/data/nb/i18n | 15.0% | 7.5% | — | — | — |

Findings:
1. **The benign explanation fails**: ~2/3 of merged unreviewed-substantial PRs
   are dominantly SOURCE CODE in both periods — not lockfiles/docs/config noise.
   Composition is stable; the 5.7x volume growth means ~6x more real source
   shipping without human review.
2. Unreviewed source shifted insider (58% -> 71%) and is now 19% AI-written,
   with test-line share up 21% -> 30%.
3. **Substitution evidence is WEAK-TO-MIXED**: AI review is disproportionately
   present on unreviewed merged source (31%) — but AI-reviewed PRs in this mass
   merge at the SAME rate as never-reviewed ones (41.3 vs 41.6%), so AI review
   is not acting as a merge gate; presence likely reflects repo-level bot
   defaults rather than a review decision.
Caveats: spike-scale N (120/200), pooled not CW, path heuristics unvalidated
against manual labels. Next iteration: manual-label ~50 to validate the
classifier; scale to a stratified 1-2k sample with CW; within-repo 2024-vs-2026
pairing.

## 10. Why unreviewed-substantial source PRs happen — qualitative read (2026-07-07)

Read all 203 source-dominant sampled PRs (73 Q1-2024, 130 Q2-2026): titles, file
paths, and commit messages, plus repo context (active authors/quarter).

**The baseline explanation (both eras): trusted-maintainer self-merge culture,
not absent reviewers.** Only 3-4% sit in solo-author repos; the typical case is
a 10-90-author, high-velocity project where core maintainers merge their own
work with CI as the gate (2024: HF candle CUDA kernels, pytorch NEON kernel,
litellm/Helicone founders shipping features, bisheng release trains, ggml sync
PRs). Note: several "external" authors are actually founders/staff with private
org membership — the §8 external-substantial finding partly reflects
misclassified insiders (documented caveat).

**What changed by Q2-2026 — three shifts, visible in the commits themselves:**
1. **The mass moved into AI/agent-product repos at extreme velocity** (imbue,
   kimi-code, microsoft/amplifier-* and TypeAgent, HKUDS, data-formulator,
   unsloth Studio): same self-merge lane, far bigger payloads — multi-kloc,
   multi-phase single-author PRs ("Phase 1..P5", 13-33k lines).
2. **The review loop moved inside the PR.** 12/130 (9%) of 2026 PRs carry
   commit trails like "Apply round-1..5 reviewer fixes", "Address Greptile
   review comments", "self-review fixes" — review-shaped iteration performed by
   AI reviewers/agents, with the GitHub human-review slot left EMPTY. Zero
   instances in 2024. (32% of the 2026 sample has AI-review objects; 18%
   AI-code markers.)
3. **Agentic process artifacts substitute for review conversation**: plan/
   blueprint/phase/beads-driven commits (13 vs 0 in 2024), design docs and
   project logs committed alongside code.

**Synthesis for the paper:** the no-review lane is old (maintainer self-merge);
what is new is what travels in it — agent-scale changes whose quality control
has visibly migrated from the human review slot into in-PR loops (AI reviewer
rounds, self-review commits, planning artifacts). Combined with §9 (AI review
present but not gating merges), the picture is PROCESS substitution without
GATE substitution.
Minor measurement note: ~5-10% of "source" is vendored-in-source (e.g., a 96k-
line miniaudio.h header, vendored curlconverter) — modest overcount of original
source.
