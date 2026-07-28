# Results — AI-assisted development at leading AI organizations
CANONICAL (2026-07-26): every number below is from
`artifacts/report_generated.md`, produced end-to-end by the pipeline at
this commit — complete census (single store, legacy retired), w8 event
windows on fates AND reviews, maturity-gated outcome metrics, marker set
incl. the committer-identity audit additions, manifest-bound two-design
responsiveness samples (equal-probability for rates, PPS-by-LOC + HT for
LOC shares), study-frame eligibility profiles (issue #2: agent-authored
PRs count in the AI-contrast review-behavior series, fleet excluded — and
per the 2026-07-26 review, non-AI bots and login-less authors are excluded
from the nonAI comparison arm in every one of those series),
window-scoped contributor weights, seeded 2,000-draw CIs.

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
  [13.4,17.9] vs 16.9 cross-section — adoption growth, not composition.
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

## 6. Adoption cohorts & event alignment (Figures 4–5, A1–A2)
- Fixed cohorts by first AI evidence — fleet (≥300 merged PRs/quarter,
  assigned first) / early (≤2026-02) / middle (2026-03..04) / late
  (≥2026-05) / non-adopters: every cohort steps up in its own adoption
  window (early 11.9→26.8 kLOC/quarter; middle 9.2→21.6; late 8.7→15.2
  despite w8 deflation; non-adopters flat 3.8→6.2). The 2024 baseline
  gradient (early > middle > late > never) is quantified adopter
  selection.
- **Figure 4** (pooled balanced event panel, first AI use 2025-12..2026-04, raw levels) and **Figure A2** (per-cohort, net of non-adopters): flat positive
  pre-period premiums (early ~+4.2, middle ~+1.7..3.3 kLOC/month), then a
  t0 discontinuity (early 4.5→12.6, middle 3.3→10.1 submitted) settling
  ~+8.5–9.5 through t+2; the NON-AI series jumps at t0 in every cohort
  (early 4.6→8.6, middle 3.2→5.7) — the undetected-usage signature under
  constant composition. t0 partly reflects ascertainment; the
  plateau-vs-pre-period comparison is the conservative estimate.
- **Fleet operators** (Figure 5, vs the non-adopter control): ~43
  accounts merging 300–4,400 PRs/quarter (mean 531 kLOC/author in
  Q2-2026, ×13 the 2024 automation baseline);
  half-ish unmarked; review coverage varies 0%–84% by org. A new
  production mode, reported as its own cohort, never averaged into
  per-contributor claims.

## 7. Review attention & responsiveness (report §§16–18)
- Human comments per merged kLOC (bot-clean, mature PRs): 3.98 → **1.88**
  (−53% pooled; insiders 3.52 → 1.37, −61%) — attention per line thinned
  while merged-PR human-review coverage held (m_hum_rev ~69–75% CW).
- Responsiveness to explicit human asks (CLEAN lane = no AI reviewer,
  identified; fleet-excluded; estimator revised 2026-07-23, issue #2 —
  responded% is the unweighted share of an equal-probability companion
  sample, because the earlier HT-over-PPS estimator let tiny-LOC PRs carry
  up to 39% of a lane's weight and equally-valid draws swung small lanes by
  tens of points; the "asked AI PRs respond at 92–93%" reading is
  WITHDRAWN as a draw artifact. Both samples were REDRAWN and re-pulled
  2026-07-26 under the author-hygiene frame fix — non-AI bots and
  login-less authors no longer enter the CLEAN+nonAI lane): CLEAN-lane
  responded% is FLAT — 79.7% (Q1-2024) → 80.9% → 79.8% → 80.8% (Q2-2026,
  provisional). Where the AI lane clears its own n≥20 floor it responds at
  the same rate as non-AI (Q1-2026: 81.8%, n=22, vs 79.5%); the Q2-2026 AI
  lane falls below the floor for the RATE (n=18) while its own PPS draw
  still supports the LOC share (n_loc=46), the two designs being gated
  independently.
  - **The "AI signal is in volume, not rate" reading is WITHDRAWN too.**
    Post-ask LOC share for the AI lane reads 85.9% in Q1-2026 (n_loc=21)
    but 47.7% in Q2-2026 (n_loc=46) — straddling the non-AI level (46.4%
    and 62.9%) in BOTH directions. The previously published "64.3% vs
    45.3% in Q2" was a small-lane artifact of the same family as the
    92–93% rate reading. No directional AI claim on post-ask volume
    survives at these lane sizes; report the non-AI series and the
    parity-in-rate finding only.
  - Frame includes agent-authored PRs (the PR's own bot counts as the
    author responding). GitHub serves at most 250 commits per PR, so 30
    records (0.3%) are analyzed on their first 250 commits and measured
    against the LOC of those same commits — not against the whole-PR
    census LOC, which would divide a 250-commit numerator by a full-PR
    denominator (METHODS §5). Measured effect on the numbers above: none —
    the 20k per-PR LOC cap already binds for all 30. Unit nonresponse 0.1%
    (EQ) / 0.3% (PPS) — all
    remaining tombstones verified genuine (`openai/plugins` PRs disabled
    2026-07-14, plus three deleted PRs). The redraw's first pull recorded
    1,345 live PRs as nonresponse from timed-out batch queries (27.9% of
    the EQ selection, which zeroed the Q2-2026 AI lane); those were
    repaired before these numbers were produced, and both the confirmation
    step and a nonresponse ceiling now make that failure publishable-proof
    (METHODS §5).
- Triage at matched horizons (w8, pooled; population revised 2026-07-26:
  agent-authored PRs count in all/AI/nonAI while non-AI bots and
  login-less authors are excluded from EVERY arm — they were inflating the
  nonAI baseline with auto-merged dep-bumps; fleet-operator authors
  excluded; ins/ext remain human-authored, so all = ins + ext +
  agent-authored, footnoted per quarter in the report): merged 75.5 → 54.5
  with limbo 6.4 → 17.5 — and the decline is concentrated in EXTERNAL PRs
  (ext merged 72.8 → 44.7 while insiders hold 81.6 → 77.8). The
  AI-vs-nonAI merge gap closes to parity by Q2-2026 (54.7% vs 54.5%, from
  57.6 vs 72.6 in Q4-2025).

## 8. Superseded analyses
The interim working log (`v2_results.md`, interim populations and interim
marker sets) was retired 2026-07-27; its section numbers (§7, §10–§12)
survive only as historical finding labels in module docstrings. Re-derive
any interim analysis on the final population before citing.
