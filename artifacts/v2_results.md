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

## 11. Accountability test: zero-human vs one-human review (2026-07-08)

Ron's alternative hypothesis to §10's "automated within-PR review": humans ARE
reviewing AI code — the shift is from "human A develops, human B reviews" to
"AI develops, human A supervises and approves" (one-person accountability, not
zero). Test signals: who authored the review-fix commits (AI trailer forensics,
from cells) and who MERGED (mergedBy vs author — GitHub forbids formal
self-approval, so mergedBy!=author is tacit second-human review) plus other-
human comments (engagement without formal review).

Population scale first: the "review-fix commits, no human review" pattern is
not 12 sample PRs — it is **1,414 merged unreviewed-substantial PRs in Q2-2026**
(9% of that mass), of which 455 (32%) have AI-authored fix commits and 299
(21%) are majority-AI-authored.

| cohort (n=samples of populations) | self-merge | other-human merge | other-human comment | **one-person accountability** |
|---|---|---|---|---|
| Q1-2024 baseline: merged unreviewed-subst (n=120/3,348) | 76% | 24% | 21% | **67%** |
| Q2-2026 smoking-gun: +review-fix commits (n=150/1,414) | 88% | 12% | 6% | **84%** |
| Q2-2026 broad: merged AI-code, no human review (n=150/5,242) | 81% | 19% | 12% | **77%** |

**Verdict: Ron's hypothesis is largely right — with a measured shift.**
1. The dominant mode is one-HUMAN accountability, not zero: a human author
   develops with AI, iterates (often via AI reviewer feedback), and personally
   merges. Zero-human PRs (bot-merged, no human anywhere) are ~0%.
2. But it IS a shift, not just old culture: one-person accountability rose
   67% -> 77-84%, and second-human ENGAGEMENT (comments) halved (21% -> 6-12%).
   Pre-AI, a quarter of self-merged big PRs still had another human watching;
   now it is one-in-ten or fewer.
3. §10's "automated review" survives as the LABOR claim: in a third of the
   smoking-gun mass the review-response commits are AI-authored. Synthesis:
   **AI performs the review-shaped labor; human A retains (sole) approval** —
   two-person -> one-person+AI, at 6x the pre-AI volume.

## Methods note: Codex detection and why we rejected AIDev's `head:codex/` for commit attribution — and its PR-level rehabilitation (2026-07-08)

**How the v2 marker set detects Codex** (`src/pipeline/ghx.py`): (1) Codex cloud
via the GitHub App: `committer:chatgpt-codex-connector[bot]` (564 commits
globally, consistent with agents.yaml's original 556) — one of the few
qualifier terms, correct because the tool IS the committer (bare-term is for
co-author trailers, which qualifiers miss); (2) Codex CLI with opt-in
attribution: `author-email:codex@openai.com` + classifier needles matched
against commit messages, author emails, and committer email/login (the census
GraphQL query was extended to fetch committer{} in the code-review fixes —
without it Codex-cloud was structurally invisible to the PR classifier).

**Why `head:codex/` was rejected for COMMIT attribution** (agents.yaml, 0.1/0.B):
false positives (branch names are human-typed strings) and false negatives —
in the chain-ml/agent-reputation test, Codex-CLI PRs on codex-* branches left
ZERO attributable commits; an OpenAI maintainer confirmed (openai/codex
discussion #9449) that "Codex itself doesn't create commits", commit identity
is entirely the user's git config, and no Co-Authored-By is added by default.
Default local Codex CLI is structurally undetectable by any metadata method.

**PRarena reconciliation (aavetis/PRarena; probed live 2026-07-08): the
branch-name signal is real and LARGE at PR level.** `is:pr head:codex/` =
**5,446,129 PRs globally; 1,676,291 in Q2-2026 alone**; inside our population,
sample org counts for Q2-2026: vllm-project 368, huggingface 287, microsoft
226, langchain-ai 106, milvus-io 46. Today's Codex-web flow creates codex/
branches whose commits carry USER identity — invisible to trailer/committer
search but visible in the head-branch name. Consequently our Codex figure
(0.15% of PRs) is a floor specifically for MARKER-ATTRIBUTED Codex; a
branch-level signal captures far more. Both AIDev/PRarena's count (noisy but
sensitive) and ours (clean but narrow) are defensible for different purposes;
the paper should report Codex-branch PR share as a separate, clearly-labeled
signal. Population-wide codex-branch share by quarter: per-org scan in
`data/resume_state/v2/codex_branch_scan.tsv` (in progress).

Similarly for agent-AUTHORED PRs (PRarena's Copilot/Jules lines): in OUR
population these are a small share of census PRs — Q4-2025 1.95%, Q1-2026
1.84%, Q2-2026 0.84% (Copilot dominant; the decline tracks Copilot's global
dip) — versus millions globally: scope difference (top-org population vs all
of GitHub, which is hobbyist-heavy). Note the headline ai_code metric counts
trailer evidence only and does NOT include bot-authored PRs
(include_bot_authors=False), so it understates total AI involvement by
roughly the agent-authored share above plus branch-only Codex.

### 11b. Self-merged PRs: AI usage and review-of-AI trends (2026-07-08)

Fresh sample: 250 merged human-authored PRs per period (unconditioned on review
status), classified by mergedBy==author. Pooled; small-N cells flagged.

| period | class | n | share of merged | AI-code% | human-rev% | AI-rev% |
|---|---|---|---|---|---|---|
| Q1-2024 | SELF-merged | 134 | 54% | 0.0 | 67.9 | 0.0 |
| | other-merged | 116 | 46% | 0.0 | 83.6 | 0.0 |
| Q4-2025 | SELF-merged | 140 | 56% | 2.9 | 75.0 | 22.1 |
| | other-merged | 110 | 44% | 1.8 | 85.5 | 27.3 |
| Q1-2026 | SELF-merged | 160 | 64% | 10.0 | 70.6 | 30.0 |
| | other-merged | 90 | 36% | 4.4 | 93.3 | 26.7 |
| Q2-2026 | SELF-merged | 157 | **63%** | **23.6** | 67.5 | 26.1 |
| | other-merged | 93 | 37% | 10.8 | **88.2** | 30.1 |
| Q2-2026 | self+AI-code | 37 | — | — | **43.2** | 27.0 |
| Q1-2026 | self+AI-code | 16* | — | — | 68.8* | 25.0* |

Findings:
1. **Self-merging itself rose** 54% -> 63% of merged PRs.
2. **AI code concentrates in the self-merge lane**: 23.6% of self-merged PRs
   carry AI code vs 10.8% of other-merged (2.2x) — AI usage flows
   disproportionately through the lane with the weakest external gate.
3. **Review of AI code inside the self-merge lane collapsed in Q2-2026**:
   human review of self-merged AI-code PRs fell ~69% -> 43% in one quarter
   while non-AI self-merged held ~68% (and other-merged rose to 88-93%).
   The newest quarter shows AI-code + self-merge decoupling from second-person
   review specifically. (n=37; ~95% CI 28-60% vs 60-75% for the lane overall —
   suggestive-to-solid; scale-up would firm it.)
4. AI review does NOT differentially compensate (flat ~26-30% in both classes).
Attention polarization mechanism identified: the other-merged lane intensified
(88-93% reviewed) while the growing, increasingly-AI self-merge lane thinned.

### 11c. Measurement note + self-review correction (2026-07-08)
"Human review" throughout = formal GitHub PR review objects authored by
User-typed accounts (census `reviews(first:15)` field). Commits are used only
for AI-code classification (trailers/footers) and §10's qualitative themes;
conversation comments are not counted (except §11's explicit engagement
metric). Probing this surfaced a flaw: reviews authored by the PR AUTHOR
(self-review-comments; GitHub blocks self-approval but not self-comments) were
being counted. Corrected to reviewer!=author: aggregates shift <=2.2pp, but the
key cell strengthens — **self-merged AI-code PRs reviewed by another human,
Q2-2026: 37.8%** (was 43.2% incl. self-reviews) vs 68.8% in Q1-2026 and ~66%
for the self-merge lane overall. All §11b conclusions hold or strengthen.

### 11d. Where would the author's own review of AI code show up? Evidence by mode (2026-07-08)

Ron's point: authors likely review AI code BEFORE committing (in the tool
session) or after committing but before/at PR time — none of which appears in
the formal review slot. Each mode leaves a measurable residue:

**Mode 1 — pre-commit review; residue = human commits interleaved with AI
commits** (population-scale, all merged human-authored AI-code PRs):
| period | N | all-AI commits | mixed human+AI | human fix-up after AI |
|---|---|---|---|---|
| Q4-2025 | 1,530 | 46% | 54% | 26% |
| Q1-2026 | 8,335 | 54% | 46% | 21% |
| Q2-2026 | 15,289 | **59%** | 41% | **18%** |
Visible human-touch residue inside AI-code PRs is DECLINING as volume grows 10x.

**Mode 2 — post-commit/pre-PR branch review; residue = pause between last
commit and PR open**: median ~1 min for every cohort and era, and **0.4-0.5 min
for self-merged AI-code PRs** — PRs open essentially immediately after the last
commit. No evidence of a distinct branch-review pause anywhere. (committedDate
resets on rebase/amend, biasing all cohorts toward 0 — the cross-cohort
comparison stands: self+AI is the shortest.)

**Mode 3 — post-open/pre-merge self-review; residue = open->merge window**
(same-repo CI as the natural floor):
| Q2-2026 cohort | n | median open->merge |
|---|---|---|
| self-merged AI-code | 37 | **72 min** (was 178 in Q1) |
| self-merged non-AI | 120 | 242 min |
| other-merged non-AI | 83 | 1,072 min |
Self-merged AI PRs have the SHORTEST post-open window of any cohort — roughly
CI duration — and it halved quarter-over-quarter. Post-open commits (~54-62%)
are uniform across cohorts (CI-driven iteration, not review-specific).

**Synthesis:** the one mode we cannot observe (in-session diff review while
working with the agent) may well be where author review lives — but every
OBSERVABLE out-of-session review surface for self-merged AI code is small and
contracting simultaneously: interleaved human commits down, fix-ups down,
pre-PR pause ~zero, post-open window ~CI-time and halving, second-human review
38%, comments 6-12%. Honest paper claim: author review of AI code, if it
happens, has moved entirely inside the tool session; all externally visible
verification surfaces are thin and shrinking. Caveats: AI cells n=16-37;
committedDate/rebase bias; CI confound in open->merge (netted via cohort
contrast).

### 11e. Inside-session review residue: commit-message evidence in all-AI-commit PRs (2026-07-08)

Ron's Mode-1 probe: even when EVERY commit in a merged PR is AI-authored, the
commit messages of the 2nd+ commits can reveal whether a human steered the
agent mid-session. Two-tier read: (a) population-scale keyword pass, (b) a
110-PR corpus of multi-commit all-AI PRs read in full and hand-classified.

**Population pass (multi-commit all-AI-commit merged PRs):**
| period | all-AI PRs | multi-commit | human-direction lang | mech self-heal only | neither |
|---|---|---|---|---|---|
| Q1-2026 | 4,506 | 1,627 | 41% | 12% | 47% |
| Q2-2026 | 9,089 | 3,663 | 42% | 10% | 48% |

**Read corpus (110 multi-commit all-AI PRs, Q2-2026), hand-classified by what
the follow-up commits reveal:**
- **58% plain feature-progression** — sequential build steps, no visible
  correction ("Add X", "Add tests for X", "Phase 1..7"). The agent executed a
  plan; no steering is legible in the messages.
- **22% explicit EXTERNAL-review residue** — "Address PR #710 review feedback",
  "address greptile", "Address Copilot CR feedback", "address codex review",
  "per @bevzzz review". These are AI commits RESPONDING to a review that
  happened (bot or human) — review did occur, just as follow-up commits rather
  than in the formal review slot.
- **11% mechanical self-heal only** — "fix lint", "cargo fmt", "fix CI",
  "regenerate baselines". Agent reacting to tooling, no human input evident.
- **9% author in-session direction** — the interesting cases: "revert: make
  X always-on", "swap --sort-order for --reverse", "instead of broken /v1/models
  API", "Restore original shutdown ordering", "drop R4". A human changed their
  mind mid-build and redirected the agent — legible steering.

**Interpretation for Ron's question.** The commit trail DOES carry evidence of
author review of AI code, but mostly as VISIBLE correction (9% in-session
redirects + 22% review-response = ~31% show a human reacting to the code). The
majority (58%) show no legible correction at all — consistent EITHER with clean
first-try AI output accepted as-is OR with review that happened silently in the
tool session and left no commit-message trace. We cannot separate those two from
metadata. What we CAN say: about a third of even the all-AI-commit PRs carry
explicit textual evidence of a human engaging with and redirecting the AI's
output — a floor on inside-session/iterative review that the formal review-slot
metric (§11b-c) entirely misses. This meaningfully softens the "verification has
vanished" reading: for ~1/3 it demonstrably has not; for the rest it is
unobservable, not provably absent. Caveats: keyword+read on 110 PRs; "external
review residue" conflates bot and human reviewers (bot-heavy in this set).
