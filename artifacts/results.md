# Results — AI-assisted development at leading AI organizations
CANONICAL (2026-07-21): every number below is from
`artifacts/report_generated.md`, produced end-to-end by the pipeline at
this commit — complete census (single store, legacy retired), w8 event
windows on fates AND reviews, maturity-gated outcome metrics, marker set
incl. the committer-identity audit additions, manifest-bound HT
responsiveness sample, window-scoped contributor weights, seeded
2,000-draw CIs.

> Caption: Q1-2024 rows are a detector-validity check and review-practice
> baseline, not an AI-usage estimate — no detectable channel existed yet,
> while autocomplete-era assistance was already widespread and invisible.
> All rates are floors, with one quantified two-sided exception (§3).

## Population
229 organizations = 182 full-org + 47 repo-scoped; 2,142 repositories.
Stable under uniform census-derived evidence (stage-E convergence check).

## 1. Headline series (contributor-weighted, % of PRs)

| period | repos | **AI involved (primary)** | AI code (markers) | human rev (mature, ≠author) | AI review | merged (w8) | self-merged |
|---|---|---|---|---|---|---|---|
| Q1-2024 | 465 | 0.0 | 0.0 | 58.7 [51.3,64.6] | 0.7 | 75.6 | 53.2 |
| Q4-2025 | 825 | 3.0 [2.4,3.7] | 2.1 | 61.0 [57.0,64.6] | 24.4 | 72.0 | 52.2 |
| Q1-2026 | 1008 | 10.3 [9.0,11.7] | 8.7 | 55.7 [52.2,58.8] | 28.3 | 66.9 | 52.4 |
| Q2-2026 | 1154 | **16.9 [14.9,18.7]** | 13.8 | **54.7 [50.7,58.7]** | 28.0 | 64.3 | 51.4 |

Figure 2 companions (CW): by Q2-2026, 13.6% of MERGED (w8, mature) PRs
are AI-involved; AI-involved PRs carry 22.4% of submitted and 17.0% of
merged LOC.

## 2. Layered decomposition (pooled over 288k Q2 PRs; disjoint, B>A>C)

| period | PRs | A markers | B agent-authored | C branch-only | **union** |
|---|---|---|---|---|---|
| Q1-2024 | 72,290 | 0.00 | 0.00 | 0.00 | **0.00** |
| Q4-2025 | 134,091 | 2.62 | 0.97 | 0.26 | **3.85** |
| Q1-2026 | 197,845 | 9.65 | 1.21 | 0.99 | **11.84** |
| Q2-2026 | 288,236 | 13.20 | 0.43 | 3.48 | **17.11** |

## 3. Robustness (all in the generated report)
- **Balanced panel** (repos qualifying in all four quarters): Q2-2026 15.6
  [13.2,17.9] vs 16.9 cross-section — adoption growth, not composition.
- **Two-sided bound** (weak-prefix indeterminates incl. droid/): 16.85 vs
  16.74 pooled — **0.11pp**.
- Marker set includes the committer-identity audit additions (OpenHands,
  agent@cursor.com, vetted homegrown agents); identity needles match only
  author/committer fields (METHODS §2).

## 4. Slices (Q2-2026, CW ai_involved)
private 21.2 [19.6,23.1] > AI-majority 18.4 > repo-scoped 13.7 > public
13.2 ≈ AI-heavy 12.4 ≈ community 12.3. Human-review level still follows
governance (community 63.8 > public 58.9 > private 49.4) while the CW
series declined ~4pp from baseline (58.7 → 54.7). Full tables incl.
self-merge and reviewer profiles in the report.

## 5. Volume: output per core contributor (report §§ Fig 3, 12–14)
- **Merged (w8) kLOC per core (insider) author, CW**: 6.45 → 10.04 →
  10.71 → **19.08** = **×2.96** [Q2 CI 13.19,26.95] (Figure 3). Q2 is
  w8-deflated for May/June PRs — conservative; finalizes 2026-09.
- **AI-split (aisplit)**: non-adopting core authors are FLAT
  (6.45 → 5.90 kLOC); AI-using authors reach ~30.7 kLOC (9.68 in
  AI-tracked PRs + 20.99 in their non-AI PRs) — adopters' untracked
  output roughly doubled too: direct evidence detection undercounts
  impact.

## 6. Adoption cohorts & event alignment (Figures 4–5)
- Fixed cohorts by first AI evidence — fleet (≥300 merged PRs/quarter,
  assigned first) / early (≤2026-02) / middle (2026-03..04) / late
  (≥2026-05) / non-adopters: every cohort steps up in its own adoption
  window (early 11.9→26.8 kLOC/quarter; middle 9.2→21.6; late 8.7→15.2
  despite w8 deflation; non-adopters flat 3.8→6.2). The 2024 baseline
  gradient (early > middle > late > never) is quantified adopter
  selection.
- **Figure 5** (balanced event panel, net of non-adopters): flat positive
  pre-period premiums (early ~+4.2, middle ~+1.7..3.3 kLOC/month), then a
  t0 discontinuity (early 4.5→12.6, middle 3.3→10.1 submitted) settling
  ~+8.5–9.5 through t+2; the NON-AI series jumps at t0 in every cohort
  (early 4.6→8.6, middle 3.2→5.7) — the undetected-usage signature under
  constant composition. t0 partly reflects ascertainment; the
  plateau-vs-pre-period comparison is the conservative estimate.
- **Fleet operators**: ~43 accounts merging 300–4,400 PRs/quarter (mean
  531 kLOC/author in Q2-2026, ×13 the 2024 automation baseline);
  half-ish unmarked; review coverage varies 0%–84% by org. A new
  production mode, reported as its own cohort, never averaged into
  per-contributor claims.

## 7. Review attention & responsiveness (report §§16–18)
- Human comments per merged kLOC (bot-clean, mature PRs): 3.98 → **1.88**
  (−53% pooled; insiders 3.52 → 1.37, −61%) — attention per line thinned
  while merged-PR human-review coverage held (m_hum_rev ~69–75% CW).
- Responsiveness to explicit human asks (CLEAN lane = no AI reviewer,
  identified; manifest-bound PPS sample, Horvitz–Thompson PR-weighted;
  unit nonresponse 0.3%): 81.5% (Q1-2024) → 83.1% → 79.3% → 74.5%
  (Q2-2026, provisional) — roughly stable with a modest late dip; the
  post-ask LOC share RISES 46% → 63%, and asked PRs with AI involvement
  respond at 92–93%.
- Triage at matched horizons (w8): merged CW 75.6 → 64.3 with
  rejected_w8 16.6 → 21.3 and limbo 7.9 → 14.4.

## 8. Superseded analyses
`artifacts/v2_results.md` is the working log of interim analyses on
interim populations; re-derive before citing.
