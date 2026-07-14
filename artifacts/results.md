# Results — AI-assisted development at leading AI organizations
CANONICAL (2026-07-13): every number below is from
`artifacts/report_generated.md`, produced end-to-end by
`scripts/regenerate.py` — complete census (8,284 covered + 284 waived of
8,568 repo-periods; 71 documented-inaccessible repos), window-scoped
contributor weights, unified >=5-PR floor, event-timestamp cutoff, seeded
2,000-draw CIs. Manifest hashes in `data/derived/census_manifest.json`.

> Caption: Q1-2024 rows are a detector-validity check and review-practice
> baseline, not an AI-usage estimate — no detectable channel existed yet,
> while autocomplete-era assistance was already widespread and invisible.
> All rates are floors, with one quantified two-sided exception (§3).

## Population
229 organizations = 182 full-org + 47 repo-scoped; 2,142 repositories
(1,278 full-org + 864 strata). The population is STABLE under uniform
census-derived evidence (stage-E convergence check).

## 1. Headline series (contributor-weighted, % of PRs)

| period | repos | **AI involved (primary)** | AI code (markers) | human rev (≠author) | AI review | merged | self-merged |
|---|---|---|---|---|---|---|---|
| Q1-2024 | 465 | 0.0 | 0.0 | 59.4 [52.5,65.6] | 0.7 | 76.7 | 52.7 |
| Q4-2025 | 825 | 2.9 [2.3,3.6] | 2.0 | 62.0 [58.4,65.4] | 24.5 | 73.3 | 51.8 |
| Q1-2026 | 1008 | 10.0 [8.8,11.4] | 8.4 | 56.6 [52.9,59.7] | 28.4 | 67.5 | 52.2 |
| Q2-2026 | 1154 | **16.6 [14.7,18.4]** | 13.6 | **52.6 [48.9,56.7]** | 26.7 | 61.0 | 53.7 |

## 2. Layered decomposition (pooled over 288k Q2 PRs; layers disjoint, B>A>C)

| period | PRs | A markers | B agent-authored | C branch-only | **union** |
|---|---|---|---|---|---|
| Q1-2024 | 72,297 | 0.00 | 0.00 | 0.00 | **0.00** |
| Q4-2025 | 134,104 | 2.45 | 0.97 | 0.26 | **3.68** |
| Q1-2026 | 197,995 | 9.30 | 1.21 | 0.98 | **11.49** |
| Q2-2026 | 288,461 | 12.81 | 0.43 | 3.38 | **16.62** |

## 3. Robustness (all in the generated report)
- **Balanced panel** (repos qualifying in all four quarters): Q2-2026 15.3
  [13.0,17.6] vs 16.6 cross-section — adoption growth is real, not cohort
  composition.
- **Two-sided bound** (weak-prefix indeterminates, the single potential
  overcount): 16.60 vs 16.56 — **0.05pp**.
- Contributor-weighted vs pooled Q2: 16.6 vs 16.6 — the two weightings agree
  at the headline this quarter.

## 4. Slices (Q2-2026, CW ai_involved)
private 20.7 [18.9,22.5] > AI-majority 18.2 > repo-scoped 13.0 > AI-heavy
12.4 ≈ community 12.3 — full tables incl. review gradients and the
self-merge study in `report_generated.md` §3–4.

## 5. Superseded analyses
`artifacts/v2_results.md` is the working log of interim analyses on interim
populations; re-derive before citing (its §11b self-merge collapse REVERSED
on complete data — see report §4).
