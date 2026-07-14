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
- **Cutoff filtering** (`detect.CUTOFF = 2026-06-30T23:59:59Z`): reviews
  submitted after the cutoff are ignored; a PR merged after the cutoff counts
  as NOT merged. Residual: per-commit timestamps are not collected, so a
  marker-bearing commit pushed post-cutoff to a still-open in-window PR is
  not filterable (exposure ≈ the 1–9 day collection lag, layer A only).
- **Dedup** (`analyze.group_by_period`): PRs are deduplicated by number
  within (repo, quarter) across overlapping cell generations; when duplicates
  differ, the record carrying `headRefName` (the census-v2 query) wins
  regardless of iteration order.
- **Bot-authored PRs are included** in denominators and classified via layer
  B. (Studies that need human-authored subsets filter explicitly and say so.)

## 2. Per-PR classification (`detect.classify_pr` → PRClass)

| field | definition | notes / caveats |
|---|---|---|
| `marker_tools` (layer A) | any commit in the PR carries a tool marker: Claude (`noreply@anthropic.com` co-author / "Generated with [Claude Code]" footer), Cursor (`cursoragent@cursor.com`), aider trailer, Codex (`codex@openai.com` author or `chatgpt-codex-connector` committer) | commit-forensic, strongest evidence; floors — squash strips trailers; only first 12 commits fetched |
| `agent_author` (layer B) | PR author is a Bot-typed account in `AGENT_PR_AUTHORS` (copilot-swe-agent, devin-ai-integration, cursor, google-labs-jules, codegen-sh, amazon-q-developer, factory-droid, claude) | the author IS the tool; no trailer needed |
| `branch_tool` (layer C) | head branch matches an agent prefix: `codex/`, `copilot/`, `cursor/`, `claude/` | PR-level attribution only; measured precision per prefix in METHODS §2 (codex/copilot ~95%+; cursor/claude indeterminates are the study's only potential overcount, bounded at 0.06pp on the Q2-2026 headline — report section 6); all-github-actions-committed branches excluded as measured FPs; requires census-v2 cells |
| **`ai_involved`** | **A ∪ B ∪ C — the PRIMARY metric** | an explicit lower bound on true AI involvement |
| `merged` | `mergedAt` present and ≤ cutoff | |
| `self_merged` | merged and `mergedBy.login == author.login` | None (excluded from rates) when the cell lacks `mergedBy` |
| `insider` | `authorAssociation ∈ {MEMBER, OWNER, COLLABORATOR}` | misses staff with private org membership |
| `human_reviewed` | ≥1 formal review by a User **other than the PR author**, submitted ≤ cutoff | the corrected definition; conversation comments never count |
| `human_reviewed_any` | as above but including the author's self-review-comments | legacy definition, reported for comparability only |
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
- **Marker set**: v2 (Claude, Cursor, aider, Codex) everywhere in the
  generated report (`--markers v2` is passed explicitly).

## 5. The generated report (`artifacts/report_generated.md`)

Produced only by `scripts/regenerate.py` stage F, which refuses to run until:
stages exit zero, every repo-scoped org has a DONE strata sentinel, and every
manifest repo-quarter has gap-free valid-cell coverage or a documented
inaccessibility waiver. The report has five sections:

1. **Contributor-weighted metrics** (`pipeline.analyze`) — per quarter ×
   {equal-weight, contrib-weight} rows; columns = `ai_code` (layer A only),
   **`ai_involved`**, `merged`, `human_review` (legacy any-User),
   `human_rev_other` (corrected), `ai_review`, `other_bot_review`,
   `no_review` (no review of any kind), `insider`, `self_merged`; each as
   `mean [95% CI]`.
2. **Layered decomposition** (`pipeline.integrate`) — pooled shares per
   quarter: A-marker / B-agent / C-branch-only / union, exact per-PR on the
   population manifest.
3. **Slices: involvement** (`pipeline.studies.slices --table involvement`) —
   six slices (adoption groups AI-majority / AI-heavy / repo-scoped from
   `population.tsv` scope + measured `top5_ai`; org types public / private /
   community from `org_type.tsv`) × {`ai_involved`, `hum_rev` (corrected),
   `ai_rev`, `merged`} per quarter.
4. **Slices: self-merge** — per slice: `self_merged` (share of merged, where
   mergedBy known), `ai_of_selfm` / `ai_of_otherm` (AI-involvement of
   self- vs other-merged PRs), `humrev_selfm_ai` / `humrev_selfm_non`
   (reviewer≠author rate on self-merged AI vs non-AI PRs).
5. **Balanced-panel sensitivity** (`--table panel`) — the `ai_involved`
   series restricted to repos qualifying in ALL four quarters, next to the
   repeated cross-section, separating adoption growth from cohort
   composition (METHODS §1 estimand note).
6. **Two-sided bound** (`--table bounds`) — headline `ai_involved` with and
   without the weak-prefix (cursor/, claude/) indeterminate C-only PRs; the
   study's single potential overcount, quantified (METHODS §2).

Alongside the report, `data/derived/census_manifest.json` records SHA-256
prefixes of the population files, repo count, and cell-coverage numbers
(covered / waived / total repo-periods).

## 6. Auxiliary analyses (not in the generated report)

- `pipeline.integrate --thresholds` — org adoption thresholds using the
  historical branch-share approximation; superseded in accuracy by per-PR
  layer C and retained for comparison only.
- `pipeline.studies.accountability`, `review_modes`, `corpus` — the
  behavioral studies behind the working log (sampled, seeded); re-derive on
  the final population before citing.
- `data/derived/branch_sample_classifications.tsv` — minimized (identity-free)
  per-PR classifications of the branch-prefix samples.

## 7. Metric-level limitations (beyond METHODS §6)

- Per-PR truncation: first 12 commits / 15 reviews per PR (downward bias on
  layer A and review detection for very long PRs).
- `self_merged` availability tracks census-v2 coverage; rates skip unknown.
- `no_review` means no formal review object of any kind; informal comment
  engagement is not part of the generated report.
- Slice membership is as-of the classification snapshot (topics observed
  2026-07-07..10); ownership as-of cutoff.
