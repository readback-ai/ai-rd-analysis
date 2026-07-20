# Metrics & generated reports — reference

What every number in the generated report means, exactly as the current code
computes it. Companion to `docs/METHODS.md` (population/detection/collection);
this document covers classification → rates → aggregation → report layout.
Source of truth for each definition is cited as `module.function`.

## 0. Reading the Q1-2024 column

Q1-2024 rows exist as a DETECTOR-VALIDITY CHECK and review-practice
baseline, not an AI-usage estimate: none of the three detectable channels
(trailers, agent bot accounts, agent branch conventions) existed yet, so the
column is 0% BY CONSTRUCTION even though autocomplete-era assistance
(Copilot suggestions) was already widespread and is invisible to every
detection layer. Every generated table carries this caption.

## 1. Unit of observation and eligibility

The unit is the PULL REQUEST, censused per (repo, quarter):
- **Window**: PRs are selected by CREATION date inside the quarter
  (`census.pull_cell` query `created:<range>`); quarters are Q1-2024,
  Q4-2025, Q1-2026, Q2-2026.
- **As-of bound and the w8 rule** (`detect.CUTOFF = 2026-06-30T23:59:59Z`):
  CUTOFF is the data AS-OF stamp, not the outcome horizon. Per-PR outcomes
  are measured at **8 weeks from PR creation** (`PRClass.merged/rejected`,
  frozen convention §1d): a merge counts iff it happened within 56 days of
  creation AND on or before the as-of; fate metrics are None (skipped) on
  w8-immature PRs. Review events follow the SAME w8 rule (adopted
  2026-07-20): a review counts only if submitted within 56 days of PR
  creation and on or before the as-of — so mature PRs are immutable under
  as-of advances. PRs
  created after ~2026-05-05 have open w8 windows at the current as-of, so
  Q2-2026 fate cells are PROVISIONAL until the scheduled **Sept 1, 2026
  re-pull** (re-collect Q2 cells, bump CUTOFF), after which every Q2 window
  is complete — the pipeline is built for this update (monthly_update /
  regenerate re-collection; nothing else changes). Residual: per-commit
  timestamps are not collected, so a marker-bearing commit pushed after the
  as-of to a still-open in-window PR is not filterable (layer A only;
  exposure grows with re-collection lag).
- **Dedup & freshness** (`analyze.group_by_period`): PRs are deduplicated
  by number within (repo, period) across overlapping cells (full-quarter +
  sub-window, or quarter + re-collected month); the richer record (carrying
  `headRefName`) wins, and at equal richness the fresher cell (later file
  mtime) wins. Single cell store since 2026-07-20 (`raw/census-v2/`); the
  legacy `census` store was retired after its 187 remaining repo-quarters
  were re-collected.
- **Bot-authored PRs are included** in denominators and classified via layer
  B. (Studies that need human-authored subsets filter explicitly and say so.)

## 2. Per-PR classification (`detect.classify_pr` → PRClass)

| field | definition | notes / caveats |
|---|---|---|
| `marker_tools` (layer A) | any commit in the PR carries a tool marker: Claude (`noreply@anthropic.com` co-author / "Generated with [Claude Code]" footer), Cursor (`cursoragent@cursor.com`), aider trailer, Codex (`codex@openai.com` author or `chatgpt-codex-connector` committer) | commit-forensic, strongest evidence; floors — squash strips trailers; only first 12 commits fetched |
| `agent_author` (layer B) | PR author is a Bot-typed account in `AGENT_PR_AUTHORS` (copilot-swe-agent, devin-ai-integration, cursor, google-labs-jules, codegen-sh, amazon-q-developer, factory-droid, claude) | the author IS the tool; no trailer needed |
| `branch_tool` (layer C) | head branch matches an agent prefix: `codex/`, `copilot/`, `cursor/`, `claude/`, `droid/` (weak, added 2026-07-17) | PR-level attribution only; measured precision per prefix in METHODS §2 (codex/copilot ~95%+; cursor/claude indeterminates are the study's only potential overcount, bounded at 0.06pp on the Q2-2026 headline — report section 6); all-github-actions-committed branches excluded as measured FPs; requires census-v2 cells |
| **`ai_involved`** | **A ∪ B ∪ C — the PRIMARY metric** | an explicit lower bound on true AI involvement |
| `merged` | merged WITHIN 8 WEEKS of creation (frozen censoring rule; METHODS §1d) | `merged_ever` retains the ≤-cutoff-anytime variant; fate metrics are None on w8-immature PRs |
| `rejected` | closed unmerged within 8 weeks | limbo = w8-mature, neither |
| `self_merged` | merged and `mergedBy.login == author.login` | None (excluded from rates) when the cell lacks `mergedBy` |
| `insider` | `authorAssociation ∈ {MEMBER, OWNER, COLLABORATOR}` | misses staff with private org membership |
| `human_reviewed` | ≥1 formal review by a User **other than the PR author** (bot-logins excluded), submitted within w8 of creation and ≤ as-of | conversation comments never count; the legacy any-User variant was removed 2026-07-20 |
| `substantive_review` | a reviewer≠author review with inline comments or state COMMENTED/CHANGES_REQUESTED | "more than a rubber-stamp APPROVED"; only first 15 reviews fetched |
| `ai_reviewed` | ≥1 review by a Bot in `AI_REVIEWERS` (gemini-code-assist, copilot-pull-request-reviewer, coderabbitai, greptile-apps, qodo-merge-pro, cursor, chatgpt-codex-connector, copilot-swe-agent, claude) | decomposed from CI bots |
| `other_bot_reviewed` | ≥1 Bot review not in `AI_REVIEWERS` | CI/automation noise kept separate |

Disjoint layer decomposition (for the layered table only): B wins over A wins
over C, so each PR counts once (`integrate.layered_table`).

### 2b. Merged-conditioned review metrics
Unmerged PRs are implicitly reviewed-and-rejected (merge triage), so reviewer
coverage OF WHAT SHIPS is reported separately: `m_hum_rev`, `m_ai_rev`,
`m_no_rev` (analyze columns, None-skip conditioning on merged) and the
2x2 reviewer profile (`slices --table reviewers`: human-only / AI-only /
both / neither, per slice). Key property: conditioned on merging, any-human
review coverage ROSE vs the 2024 baseline while all-PRs coverage fell —
both framings are reported.

## 3. From PRs to rates (per repo-quarter)

- **`analyze.pr_metrics`**: per-repo-quarter rate = share of that repo's
  censused PRs with the property. Metrics whose field is unavailable on a PR
  (e.g. `self_merged` on a legacy cell) are skipped, not zeroed.
- **Repo qualification floor**: **≥5 PRs/quarter, ≥2 PRs/month** —
  comparable thresholds per unit time (`analyze --min-prs` defaults by
  `--granularity`; `studies.slices` likewise). Slice CONDITIONAL metrics
  additionally require the same floor in the conditioning denominator.
- **Granularity**: quarters are the headline unit (precision); months are
  the trend unit (`--granularity month` in analyze/slices). Month buckets
  re-partition the sampled quarters exactly (bucketing is by each PR's
  createdAt, which always lies inside its cell's range) — no separate
  collection. The newest month in an incremental update is PROVISIONAL
  (reviews/merges lag; see METHODS runbook).
- Census sampling: repo-quarters are collected completely (adaptive windows
  + pagination + fail-hard saturation); rates are over ALL of a repo's PRs
  in the window, coverage-gated at report time.

## 4. Aggregation

- **Contributor weighting (primary)**: weighted mean of per-repo rates,
  weight = repo's core human contributors ACTIVE IN THE STUDY WINDOW —
  ≥5 commits authored during Q4-2025..Q2-2026, bots excluded, from GitHub's
  weekly contributor statistics (`pipeline.contributors` →
  `data/derived/repo_contributors_window.csv`). Answers "the typical
  currently-active AI-org developer's PR flow"; a dormant project's
  historical committers no longer inflate its weight. The all-time variant
  (≥10 commits ever, `repo_contributors_v2.csv`) is retained as a
  sensitivity file.
- **Pooled (secondary)**: share over all PRs (repo-size-dominated; the
  layered decomposition table is pooled and labeled as such).
- **Uncertainty**: bootstrap 95% CIs over repos, 2,000 resamples, seeded RNG
  (`analyze._RNG`, seed 20260630) — identical reruns give identical CIs.
- **Marker set**: one canonical set (`detect.MARKERS`: Claude, Cursor,
  aider, Codex) — the v1/v2 versioning was removed 2026-07-20; historical
  scan/enum cache files keep their "v2" filename tag.

## 5. The generated report (`artifacts/report_generated.md`)

Produced by `scripts/report.py` (canonically invoked by
`scripts/regenerate.py` stage F, which refuses to run until: stages exit
zero, every repo-scoped org has a DONE strata sentinel, and every manifest
repo-quarter has gap-free valid-cell coverage or a documented
inaccessibility waiver). The monthly twin (`report_monthly.md`,
`--granularity month`) runs the same sections; sections whose module is
inherently quarterly carry an explicit `[quarterly]` tag there.

The 19 sections, in order (each title names its producing module and
argument — one section = one module invocation):

1. **Contributor-weighted metrics** (`pipeline.analyze`) — per period ×
   {equal-weight, contrib-weight}; columns = `ai_code` (layer A),
   **`ai_involved`**, w8 fates (`merged`, `rejected_w8`, `limbo_w8`),
   `human_review` (reviewer≠author, bot-clean), `ai_review`,
   `other_bot_review`, `no_review`, `insider`, `self_merged`,
   merged-conditioned `m_*`; each as `mean [95% CI]`.
2. **Figure 2: Traceable AI usage** (`paper_tables --table usage`) — AI%
   of submitted/merged PRs and AI-PR share of submitted/merged LOC (CW,
   CIs). Rendered as `artifacts/fig2_ai_usage.png`.
3. **Figure 3: Merged LOC per core contributor** (`paper_tables --table
   core`) — CW merged (w8) kLOC per insider author + baseline multiple
   (×2.66 by Q2-2026). Rendered as `fig3_core_loc.png`.
4. **Layered decomposition** (`pipeline.studies.layers`) — pooled
   disjoint shares: B-agent > A-marker > C-branch-only, plus union
   (exact per-PR; replaced `pipeline.integrate`'s sampled blending,
   removed 2026-07-20).
5. **Slices: involvement** (`slices --table involvement`) — six slices
   (adoption groups + org types) × {ai_involved, hum_rev, ai_rev, merged}.
6. **Slices: self-merge** (`--table selfmerge`).
7. **Balanced-panel sensitivity** (`--table panel`) — adoption vs cohort
   composition.
8. **Reviewer profile of merged PRs** (`--table reviewers`) — human-only /
   AI-only / both / neither, per slice.
9. **Two-sided bound** (`--table bounds`) — headline with/without
   weak-prefix (cursor/, claude/, droid/) indeterminates; 0.05pp at the
   Q2-2026 headline.
10. **Productivity decomposition** (`productivity --cut decomposition`) —
    PRs = authors × PRs/author on the balanced repo panel.
11. **Persistent-author productivity** (`--cut persistent`) — same person,
    same repo, 2024↔2026, AI-split.
12. **Core-contributor merged LOC** (`--cut core`) — the Figure 3 series.
13. **Core-contributor LOC split by AI involvement** (`--cut aisplit`) —
    noAI-author kLOC (flat) vs AI users' AI-PR + nonAI-PR kLOC.
14. **Figure 4: adoption cohorts** (`--cut adoption`) — fixed cohorts
    early/medium/late/never/**fleet** (≥300 merged PRs/quarter, assigned
    first); AI/nonAI/total kLOC per author with CI + median. Rendered as
    `fig4_adoption_cohorts.png`.
15. **Merged LOC by approval channel** (`--cut channels`) — humanRev /
    botOnly / selfUnrev / otherUnrev shares of merged LOC.
16. **Attention per line** (`studies.attention`) — HUMAN comments/kLOC
    (bot-clean) + window h/kLOC, all/ins/ext + size bands.
17. **PR fates at matched horizons** (`studies.fates`) — w8 primary, w26
    sensitivity, per cohort; immature PRs excluded per horizon.
18. **Responsiveness to human asks** (`studies.review_action`) — CLEAN
    lane identified; Horvitz–Thompson weighted (PPS sample → PR-weighted
    responded%, population LOC share); commit lists paginated with
    completeness metadata.
19. **Adoption event-study** (`studies.event_study`) — merged (w8,
    mature-months-only) and submitted kLOC in event time around each
    author's first AI-marker month.

Alongside the report, `data/derived/census_manifest.json` records SHA-256
prefixes of the population files, repo count, and cell-coverage numbers
(covered / waived / total repo-periods). Incremental months live in
`data/derived/incremental_months.txt` (see METHODS §1c).

## 6. Auxiliary analyses (not in the generated report)

- `pipeline.studies.accountability`, `review_modes`, `corpus` — the
  behavioral studies behind the working log (sampled, seeded); re-derive on
  the final population before citing.
- `data/derived/branch_sample_classifications.tsv` — minimized (identity-free)
  per-PR classifications of the branch-prefix samples.

## 6b. Complete census vs. sampled studies

The PR census is a COMPLETE ENUMERATION, not a sample: every population
repo-quarter is collected in full (adaptive sub-windows + pagination sized
from the precount; high-volume repos like pytorch get up to one sub-window
per day), gated by count-vs-precount reconciliation with a
max(2%, 3 PRs) drift allowance, one self-heal re-pull, and FAIL-HARD on
saturation — a repo-quarter is either fully collected or explicitly
failed/waived, never silently truncated. All report tables run on this
complete census.

Sampling exists only in three clearly-labeled auxiliary studies, each with
its own inference machinery: `review_action` (PPS: 1,200 LOC-proportional
draws/quarter, Horvitz–Thompson weighted back to population estimands),
the LOC-hygiene sensitivity (~3.7k PRs with file lists), and the layer-C
precision samples (org-stratified branch-PR pages). Per-PR field
truncation (first 12 commits / 15 reviews in census cells) is a separate,
documented downward bias — see §7.

## 7. Metric-level limitations (beyond METHODS §6)

- Per-PR truncation: first 12 commits / 15 reviews per PR (downward bias on
  layer A and review detection for very long PRs).
- `self_merged` availability tracks census-v2 coverage; rates skip unknown.
- `no_review` means no formal review object of any kind; informal comment
  engagement is not part of the generated report.
- Slice membership is as-of the classification snapshot (topics observed
  2026-07-07..10); ownership as-of cutoff.
