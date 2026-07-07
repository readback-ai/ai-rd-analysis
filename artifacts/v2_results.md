# v2 results — AI-assisted development at leading AI orgs (2026-07-05)

Full pipeline run on the externally-sourced v2 population: **215 orgs → 1,996
product repos → 7,953/7,984 repo-periods censused (99.6%)**, 26,819 raw cells,
0 corrupt. Periods: Q1-2024 (pre-AI baseline), Q4-2025, Q1-2026, Q2-2026 (full
quarters). Per-repo rates over repos with ≥10 PRs/period; contributor-weighted
(core human contributors); bootstrap 95% CIs over repos. Marker sets v1
(Claude+Cursor) and v2 (+aider, +codex incl. committer search) both run.
Raw outputs: `data/resume_state/v2/analysis_v{1,2}.txt`.

## Headline table (contributor-weighted, v1 markers, 95% CI)

| period | repos | AI-code PRs | human review | **AI review** | other-bot review | merged | insider |
|---|---|---|---|---|---|---|---|
| Q1-2024 | 485 | 0.0 | 59.9 [52.9,66.2] | 0.1 [0.0,0.3] | 0.9 [0.2,2.3] | 82.4 | 33.9 |
| Q4-2025 | 869 | 2.3 [1.8,3.0] | 59.0 [54.1,63.7] | 14.5 [9.2,22.1] | 9.0 [4.1,14.6] | 74.9 | 34.9 |
| Q1-2026 | 1120 | 10.3 [8.7,12.3] | 52.9 [47.8,57.7] | 18.0 [12.9,24.9] | 9.1 [4.8,14.4] | 69.3 | 34.1 |
| Q2-2026 | 1286 | **15.2 [13.2,17.3]** | 47.9 [42.4,52.9] | **20.7 [15.4,26.6]** | 10.3 [6.3,15.2] | 64.9 | 33.4 |

## Findings

1. **The v1 findings replicate on a 10× population.** AI-code PR rate reaches
   **15.2%** by Q2-2026 (v1 said 15.9% on 174 repos) — same curve, now with CIs,
   on 1,996 externally-sourced repos. The result is robust to the population.

2. **The automated-review surge is genuinely AI review, not CI.** This was the
   review's P1.4 concern (the v1 metric conflated all bots). Decomposed:
   **AI code-reviewers went 0.1% → 20.7% of PRs** (gemini-code-assist,
   copilot-pr-reviewer, coderabbit, etc.) while other bots went only 0.9% →
   10.3%. Two-thirds of the automation shift is AI reviewing code.

3. **Human review declined ~12 points** (59.9% → 47.9%) as AI code and AI review
   arrived — humans review less overall, and AI review is not (yet) additive
   compensation: no-review rose 39.5% → 41.4%.

4. **Merge rate drifted down** (82.4% → 64.9%; Q2-2026 retains mild recency
   censoring), consistent with more speculative/AI-heavy PR volume.

5. **Insider share is stable (~34%)** across the entire wave — the AI transition
   did not shift who contributes (staff vs external), it shifted how.

6. **Detection delta v1→v2 markers: ~0.1pp — negligible.** With codex made
   genuinely searchable (committer qualifier; 564 commits globally) and aider
   included, measured AI-code rates changed from 15.6% to 15.7% (equal-weight).
   Claude+Cursor trailers capture essentially all detectable AI-code evidence
   in these orgs' public repos; Codex-cloud/aider are rare there. This is now a
   MEASURED result (the cache-key fix made it real, not a stale-cache artifact).

7. **Population growth is itself a finding**: repos with ≥10 PRs/period grew
   485 (Q1-2024) → 1,286 (Q2-2026) within a fixed repo set — activity in
   AI-evidence repos is expanding.

## Caveats
- Floor effects: squash-merge strips trailers; local tools (Windsurf, Codex CLI
  default) invisible. AI-code rates are lower bounds.
- 31 repo-periods (0.4%) permanently failed (inaccessible repos); documented.
- Q2-2026 merge/no-review slightly recency-censored (quarter ended 5 days
  before collection).
- Population = repos with detectable AI evidence at quality-gated orgs
  (prominence-selected); baseline Q1-2024 is the same-repo temporal control.
- Big repos sampled uniformly at up to 500 PRs/quarter (10 sub-windows × 50);
  sub-window saturation warned and logged where it occurred.

## Reproducibility
`src/pipeline/` (scan_orgs → enum_repos → precount → census → analyze), all
stages checkpointed to $AIRD_DATA_DIR; org/repo sets and analysis outputs in
`data/resume_state/v2/`; 64 tests. Total collection: ~36h wall (rate-limit
bound), interrupted repeatedly (laptop sleeps, task kills) with zero data loss.

---

# CORRECTION + per-tool rates with TRUE contributor weights (2026-07-07)

**Weight-coverage bug found while building the per-tool table**: the contributor
file covered only v1's 174 repos, so prior v2 "contrib-weight" rows silently used
weight=1.0 for ~91% of repos (≈ equal-weight). Core-contributor counts were pulled
for all census repos (1,994/1,996; data/resume_state/v2/repo_contributors_v2.csv)
and everything recomputed. Directional findings unchanged; magnitudes corrected:

| metric (Q2-2026) | published (mislabeled) | TRUE contrib-weight |
|---|---|---|
| AI-code PRs | 15.2 | **11.5 [10.4,12.6]** |
| AI review | 20.7 | **23.5 [20.8,26.6]** |
| human review | 47.9 | **57.5 [55.0,60.0]** |
| no review | 41.4 | **33.6** |
| insider | 33.4 | 34.2 (stable) |

True weighting emphasizes big-team repos, which have LOWER AI-code rates (size
gradient) and RETAIN more human review (decline 65.9 -> 57.5 = -8.4pp, vs -12pp
mislabeled). Full table: data/resume_state/v2/analysis_v1_trueweights.txt.
Equal-weight rows were always correct as labeled.

## Per-tool detection rate, % of PRs, TRUE contributor-weighted [95% CI]

| period | repos | Claude Code | Cursor | aider | Codex | any tool |
|---|---|---|---|---|---|---|
| Q1-2024 | 485 | 0.00 | 0.00 | 0.00 | 0.00 | 0.00 |
| Q4-2025 | 869 | 1.52 [1.22,1.85] | 0.17 [0.09,0.28] | 0.01 | 0.00 | 1.69 [1.37,2.08] |
| Q1-2026 | 1120 | 7.08 [6.37,7.90] | 0.62 [0.46,0.80] | 0.00 | 0.01 | 7.68 [6.92,8.50] |
| Q2-2026 | 1286 | 10.35 [9.32,11.39] | 1.20 [0.90,1.56] | 0.00 | 0.15 [0.07,0.26] | 11.60 [10.57,12.75] |

- Claude Code is ~89% of all detected AI-code PRs (10.35 of 11.60 in Q2-2026),
  growing ~7x in two quarters (1.52 -> 10.35).
- Cursor is second and accelerating (0.17 -> 1.20; ~7x) but an order of
  magnitude smaller.
- Codex appears in Q2-2026 only (0.15%) — real but marginal; aider ~0.
- Detectability caveat: rates are floors and Claude's footer survives squash
  better than others' trailers, so non-Claude shares are likely more undercounted.
