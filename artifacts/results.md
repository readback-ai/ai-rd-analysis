# Results — AI-assisted development at leading AI organizations
Regenerated 2026-07-09 on the clean five-rule population (docs/METHODS.md §1;
`data/derived/population.tsv`). Study cutoff 2026-06-30. Contributor-weighted
with bootstrap 95% CIs unless noted. Reproduce with
`PYTHONPATH=src python scripts/regenerate.py` (stages resume from checkpoints).

## Population
229 organizations = 182 full-org + 47 repo-scoped (AI-topic repos only);
~2,060 repositories (`data/derived/population_repos.txt` is the canonical
manifest; counts move slightly as inaccessible repos are documented). Convergence: the population
is STABLE when the evidence rule is recomputed uniformly from the census
itself (stage E) — admission does not depend on scan-window quirks.

## 1. Headline series (contributor-weighted, % of PRs)

| period | repos | AI-code (markers) | human review (reviewer!=author) | AI review | no review | merged | self-merged* |
|---|---|---|---|---|---|---|---|
| Q1-2024 | 397 | 0.0 | 64.3 [60.0,68.1] | 0.4 | 34.5 | 78.8 | 36.2* |
| Q4-2025 | 691 | 1.7 [1.3,2.2] | 63.6 [60.7,66.3] | 19.4 | 29.3 | 73.5 | 34.3* |
| Q1-2026 | 859 | 7.5 [6.6,8.4] | 58.6 [55.5,61.3] | 24.3 | 31.5 | 68.1 | 35.8* |
| Q2-2026 | 951 | **11.1 [9.8,12.5]** | **53.2 [50.2,56.1]** | 24.3 | 34.9 | 62.4 | 37.0* |

(*) self-merged is computed on the subset of cells that carry mergedBy
(post-2026-07-08 pulls, i.e. the strata repos for all quarters); older
full-org cells lack the field and are skipped.

## 2. Layered AI involvement (pooled share of population PRs; layers disjoint,
overlap-corrected per measured samples)

| period | A commit-markers | B agent-authored | C branch-only | **total** |
|---|---|---|---|---|
| Q1-2024 | 0.00 | 0.00 | 0.00 | **0.00** |
| Q4-2025 | 2.37 | 1.87 | 0.45 | **4.69** |
| Q1-2026 | 8.63 | 1.78 | 2.61 | **13.02** |
| Q2-2026 | 12.71 | 0.82 | 4.93 | **18.46** |

## 3. Stability across population revisions
The headline CW AI-code Q2-2026 value across every methodology revision:
11.5 (interim) -> 11.3 -> 11.6 -> **11.1** on the final population — all
within each other's CIs. The findings are properties of the phenomenon, not
of population construction.

## 4. Detailed analyses
The behavioral analyses in `artifacts/v2_results.md` are a working log
computed on interim populations and methods. Each finding must be re-derived
on the final population/method before use — §6 above documents one case
(self-merge review collapse) where re-derivation REVERSED the interim
conclusion for the typical repo. Do not cite the working log directly.

## 5. PRIMARY METRIC: AI involvement (A∪B∪C), by population slice
(2026-07-11; census-v2 complete — headRefName + mergedBy population-wide,
97.5% repo-period coverage, 70 inaccessible repos documented in
`data/derived/inaccessible_repos.txt`.)

The primary metric is now **ai_involved = union of the three detection
layers per PR** (commit markers ∪ agent authorship ∪ agent branch prefix) —
still a lower bound (squash-merge, local CLI defaults). Whole population,
contributor-weighted: **0.0 → 3.0 → 9.4 → 14.4% [13.1,15.9]** of PRs.

Q2-2026 by slice (CW; full series via `pipeline.studies.slices`):
| slice | repos | AI-involved % | human rev % | AI rev % | merged % |
|---|---|---|---|---|---|
| AI-majority | 779 | **16.3 [14.8,18.0]** | 52.5 | 24.0 | 62.1 |
| AI-heavy | 162 | 14.2 [10.6,19.3] | 49.2 | 20.3 | 69.8 |
| repo-scoped | 186 | 9.9 [7.2,13.4] | 54.1 | 24.4 | 59.7 |
| private | 665 | **18.5 [16.8,20.4]** | 46.5 | 21.8 | 63.5 |
| public | 314 | 11.9 [9.7,14.3] | 53.2 | 25.6 | 59.6 |
| community | 148 | 10.0 [7.3,13.5] | **62.1** | 24.7 | 64.0 |

Gradients: private > public > community in adoption; exactly reversed in
human review. AI-review deployment is uniform (~20-26%) across every slice.

## 6. Self-merge behavior on the primary metric, by slice

| Q2-2026 slice | self-merged % of merged | AI-inv of SELF-merged | AI-inv of OTHER-merged | humRev of self-merged AI | ...non-AI |
|---|---|---|---|---|---|
| AI-majority | 52.2 | **18.2** | 12.6 | 71.7 | 66.4 |
| AI-heavy | 52.2 | 13.4 | 12.3 | 46.4 | 55.1 |
| repo-scoped | 41.3 | 10.9 | 9.0 | 78.5 | 73.7 |
| private | 55.9 | **21.2** | 14.8 | 65.7 | 61.0 |
| public | 50.1 | 11.5 | 10.1 | 81.6 | 71.6 |
| community | 38.2 | 10.6 | 8.5 | 69.4 | 71.3 |

Findings on complete census data:
1. **Self-merge rates are FLAT over time in every slice** (e.g. AI-majority
   51.6 -> 52.2 from Q1-2024). Levels are cultural: private 56% > AI-labs ~52%
   > public 50% > repo-scoped 41% > community 38% (foundation governance).
2. **AI concentrates in self-merged PRs in every slice** (Q2-2026 ratios
   1.1-1.4x; strongest in private companies, 21.2 vs 14.8).
3. **IMPORTANT CORRECTION to the working log's §11b**: on the primary metric,
   complete mergedBy data, and contributor weighting, self-merged AI-involved
   PRs are human-reviewed at rates SIMILAR OR HIGHER than self-merged non-AI
   PRs (e.g. AI-majority 71.7 vs 66.4; public 81.6 vs 71.6). The earlier
   "review of self-merged AI code collapsed 69% -> 38%" came from a pooled,
   marker-only, 37-PR sample — that collapse characterizes the pooled mass
   (dominated by a few high-volume, low-review repos), NOT the typical repo.
   The exception with the old direction is AI-heavy (research labs): 46.4 vs
   55.1 — the only slice where self-merged AI code is reviewed less.
   Conditional cells use per-repo >=5-PR floors; "reviewed" = formal review by
   a User other than the author ("B reviewed, A merged" counts as reviewed).
