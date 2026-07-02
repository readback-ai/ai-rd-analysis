# AI-code PR census — product repos, with Q1-2024 baseline (2026-06-26)

Census of **174 product repos** (AI-evidence repos, meta/demo excluded) across 59 orgs,
4 periods, 50 most-recent PRs/repo/period with commits+reviews+authorAssociation.
~14k PRs; **N(AI-code)=1,914** (vs 83 in the first cut). AI-code = commit carries a Claude
(`noreply@anthropic.com` / footer) or Cursor (`cursoragent@cursor.com`) trailer.
Automated vs manual review = reviewer `__typename` (Bot vs User).

## Results by period

| period | cohort | N | merged | no review | human rev | **bot rev** | med 1st-human (h) |
|---|---|---|---|---|---|---|---|
| **Q1-2024** (baseline) | non-AI | 1733 | 82% | 43% | 57% | **1%** | 4.0 |
| Q4-2025 | AI-code | 127 | 39% | 35% | 41% | 31% | 1.4 |
| Q4-2025 | non-AI | 3122 | 76% | 35% | 56% | 23% | 3.3 |
| Q1-2026 | AI-code | 756 | 68% | 49% | 41% | 30% | 3.7 |
| Q1-2026 | non-AI | 3573 | 70% | 43% | 46% | 27% | 5.3 |
| Q2-2026 | AI-code | 1031 | 70% | 38% | 45% | **40%** | 2.5 |
| Q2-2026 | non-AI | 3807 | 60% | 45% | 37% | 31% | 1.6 |

AI-code PR rate of all PRs: **Q1-2024 0.0% → Q4-2025 3.9% → Q1-2026 17.5% → Q2-2026 21.3%.**

## Headline findings

1. **Automated PR review exploded.** Bot review of PRs went from **1% in Q1-2024 to ~31%
   (non-AI) / 40% (AI-code) by Q2-2026** — while **human review declined** (non-AI:
   57%→56%→46%→37%). Review is shifting from human to automated across the board, and the
   Q1-2024 baseline (same repos, pre-AI) shows automated review essentially did not exist.
   This is the clearest "automated vs manual review" signal in the whole study.

2. **AI-written code adoption at PR level: 0% → 21%** in product repos over 2024→2026 — a
   clean curve that confirms the commit-level adoption rate, now on the right population.

3. **AI-code PRs lean more on bot review than non-AI**, every period (Q4 31v23, Q2 40v31).
   Human review of AI-code is roughly at or below non-AI in 2026.

4. **AI-code PR acceptance improved and converged.** Merge rate of AI-code PRs rose
   39% (Q4-2025) → 68% (Q1-2026) → 70% (Q2-2026), converging with human PRs (~70%). Early
   AI-code PRs were rejected far more; by 2026 they land at ~human rates. (Q2 merge rates
   are depressed by recency censoring — compare within a period.)

5. **AI-written code is insider practice.** Pooled, AI-code PRs are **37% insider**
   (MEMBER/OWNER/COLLABORATOR) vs **33%** for non-AI — slightly MORE insider, so this is the
   labs' own staff/collaborators writing AI-assisted code, not outside drive-by PRs.

## Caveats
- Q2-2026 merge rates censored (recent PRs unresolved); compare cohorts within a period.
- 50-most-recent/repo/period = census for small repos, window-tail sample for big ones.
- "no review" = no formal review submission (issue-comments excluded).
- Floor on AI-code (squash-merge strips trailers); footer text recovers some.
- `COLLABORATOR` is an imperfect insider proxy; MEMBER undercounted (private membership).

## FINAL (2026-06-28): uniform-500 sampling + contributor-weighting, ~50k PRs

Refined census: capped repo-periods (>50 PRs) re-sampled to **up to 500 PRs uniformly
across the quarter** (10 sub-windows × 50); small repos use the ≤50 census. 175 product
repos, **49,935 PRs**. Per-repo rates (≥10 PRs/period), then averaged. The uniform
sampling also fixed Q2-2026 recency-censoring (merge rates now accurate). A rate-limit
corruption bug in the expansion was caught and fixed (error-objects written as cells;
`census/` was unaffected — see RESUME.md).

| period | weighting | AI-code% | bot rev% | human rev% | merge% |
|---|---|---|---|---|---|
| Q1-2024 | equal | 0.0 | 0.6 | 56.5 | 82 |
|  | **contrib** | **0.0** | **0.9** | **60.0** | **83** |
| Q4-2025 | equal | 3.4 | 22.3 | 54.2 | 76 |
|  | **contrib** | **2.0** | **24.4** | **59.7** | **74** |
| Q1-2026 | equal | 17.1 | 25.4 | 44.3 | 71 |
|  | **contrib** | **10.1** | **28.1** | **54.1** | **68** |
| Q2-2026 | equal | 22.7 | 28.0 | 40.1 | 69 |
|  | **contrib** | **15.9** | **33.3** | **49.1** | **63** |

**Final findings (contributor-weighted = how AI *teams* work):**
1. **AI-written code: 0% → 16% of PRs** at leading AI orgs, Q1-2024 → Q2-2026.
2. **Automated PR review exploded: ~1% → 33%** (was ~nil pre-2024) — the biggest signal.
3. **Human review declined 60% → 49%** as automated review rose.
4. **Merge rate eased 83% → 63%** — more (AI-assisted) PRs, modestly lower acceptance.
5. Contributor-weighting lowers AI-code rate (~16% vs ~23% equal-weight) and raises review
   rates: **larger teams adopt AI in a smaller share of PRs and review more** than solo repos.
Trend direction is robust across pooled/equal/contributor weightings; only levels shift.

## Scope reached
74 AI-active orgs (of ~70 in `ai_labs.yaml`; 31 dark dropped) → 196 AI-evidence repos →
175 product repos (`data/ai_evidence_repos.csv`). This is the census the org-provenance
design was built for: a defensible, broad, period-resolved view of AI-assisted development
practice at leading AI orgs.
