# Results — AI-assisted development at leading AI organizations
Regenerated 2026-07-09 on the clean five-rule population (docs/METHODS.md §1;
`data/derived/population.tsv`). Study cutoff 2026-06-30. Contributor-weighted
with bootstrap 95% CIs unless noted. Reproduce with
`PYTHONPATH=src python scripts/regenerate.py` (stages resume from checkpoints).

## Population
226 organizations = 178 full-org + 48 repo-scoped (AI-topic repos only);
2,055 repositories (1,274 full-org + 781 strata). Convergence: the population
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
The behavioral analyses (review reallocation, self-merge lane, accountability,
review-mode residue, per-tool trends, appendix cuts) live in
`artifacts/v2_results.md` as a working log; they were computed on interim
populations whose headline differs by <=0.4pp from the final one, and their
directional findings carry over. They will be re-run on the final population
as needed for the paper draft.
