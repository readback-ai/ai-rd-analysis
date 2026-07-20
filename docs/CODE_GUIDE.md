# Code guide — how to review this repository

A reviewer-oriented tour: what to read in what order, what each module
owns, the invariants the numbers depend on, and where every headline
claim is computed. Companion to `docs/METHODS.md` (what we measure and
why) and `docs/METRICS.md` (exact metric definitions); this file is about
the CODE.

## 30-second architecture

```
data/sources/*            third-party inputs (org lists, overrides) — checked in
        │
        ▼
src/pipeline/org_set.py   population: 5 rules + override table
        │                       → data/derived/population.tsv, population_repos.txt
        ▼
precount.py → census.py   PR census per (repo, period) into the CELL STORE
        │                       $AIRD_DATA_DIR/raw/{census,census-v2}/*.json
        ▼
detect.py                 per-PR classification (the ONLY place detection lives)
        ▼
analyze.py                cells → per-repo rates → CW means + bootstrap CIs
integrate.py              exact layered decomposition (A/B/C disjoint)
studies/*.py              one analysis = one module, all reproducible
        ▼
scripts/report.py         runs every section → artifacts/report_generated.md
scripts/regenerate.py     the canonical driver: stages A–F + coverage gates
```

Everything downstream of the cell store is deterministic and seeded
(bootstrap seed 20260630); rerunning any module reproduces its table
byte-for-byte from the same cells.

## Suggested reading order

1. `src/pipeline/detect.py` (~300 lines) — every claim depends on it.
2. `src/pipeline/analyze.py` — cell loading, dedup/freshness, weighting, CIs.
3. `src/pipeline/org_set.py` — who is in the population and why.
4. `src/pipeline/census.py` + `precount.py` — how cells get complete.
5. `scripts/report.py` — the 19 sections; each names its module.
6. `src/pipeline/studies/*` — pick the studies behind claims you care about.
7. `tests/` — the invariants, each named for the finding it pins.

## Module tour (what each file owns, and its load-bearing details)

### Detection — `src/pipeline/detect.py`
The single canonical home of ALL detection. Nothing else defines a marker,
a bot list, or a review rule.

- **Layer A** `pr_ai_tools()` — commit-forensic markers (`MARKERS_V2`:
  Claude, Cursor, aider, Codex incl. committer identities). Floors: only
  first 12 commits per PR; squash strips trailers.
- **Layer B** `pr_agent_author()` — PR author is a Bot-typed account in
  `AGENT_PR_AUTHORS`. Requires `__typename == "Bot"`.
- **Layer C** `pr_branch_tool()` — agent branch prefixes
  (`BRANCH_PREFIXES`: codex/, copilot/, cursor/, claude/, droid/).
  `WEAK_PREFIXES` (cursor, claude, droid) are the study's only potential
  overcount; `strict=True` is the lower arm of the two-sided bound
  (`branch_provenance_confirmed`: web-flow committer OR product slug —
  the web-flow identity is evidence only conditioned on the prefix).
  Measured FP class excluded: all-github-actions-committed branches.
- **Reviews** `split_reviews()` — the choke point for every review-based
  metric: human (User-typed, not `is_bot_login`, ≠ author) / AI
  (`AI_REVIEWERS` allowlist) / other bot. `is_bot_login()` catches bots
  registered as User accounts (suffix-anchored so "talbot" is human).
- **`classify_pr()` → `PRClass`** — one frozen dataclass per PR;
  `ai_involved` = A ∪ B ∪ C. `merged` is the **w8 rule** (merged within
  56 days of creation, ≤ cutoff); `merged_ever` is the secondary; fate
  fields are None when the PR is not `w8_mature`.

Review invariant worth checking: an unlisted AI review product falls into
"other bot", never "human" — the human-attention numerator cannot be
contaminated by an unrecognized AI reviewer.

### Metrics engine — `src/pipeline/analyze.py`
- `load_cells()` — merges cell generations (census → census-v2, v2 wins),
  visiting files **oldest-mtime-first** so fresher cells land later.
- `group_by_period()` — dedup by PR number within (repo, period): richer
  record (has `headRefName`) beats poorer; at equal richness the
  **later-loaded (fresher) record wins** — this is how a monthly
  re-collection supersedes a stale overlapping quarter cell.
- `extended_quarters()` / `incremental_months()` — frozen quarters plus
  the persistent registry `data/derived/incremental_months.txt` (written
  by `scripts/monthly_update.py`), so incremental months survive across
  invocations. Frozen quarters keep `period_of` priority.
- Aggregation: per-repo rate → weighted mean (weights =
  `repo_contributors_window.csv`, window-active core committers) →
  seeded bootstrap CI (2,000 draws). Repo floor ≥5 PRs/quarter,
  ≥2 PRs/month.

### Population — `src/pipeline/org_set.py`
Five rules (R1 candidates from five third-party lists → R2 quality → R3
identity → R4 evidence → R5 scope w/ conglomerates) + one override table
(`org_overrides.tsv`). `--verify` reconciles the checked-in population
file against a fresh rule run; `--explain <org>` shows why an org is
in/out. Population files are SHA-256'd into the census manifest.

### Collection — `precount.py`, `census.py`
- Precount: batch PR-count denominators (aliased GraphQL).
- `census.pull_cell()` — adaptive sub-windows + cursor pagination;
  502-pathology fallback to 5-PR pages; atomic tmp+rename writes (cells
  are complete-or-absent, never partial).
- `census.census_repo_period()` — count vs precount with drift allowance
  max(2%, 3 PRs); cached full-range cells are **re-validated against the
  precount** before being trusted; one self-heal pass (invalidate +
  re-pull) before failing hard. An incomplete census FAILS; it is never
  a warning.
- `pipeline/ghx.py` — GH plumbing. Known quirk: on nonzero `gh` exit the
  `--jq` filter is NOT applied, so `graphql_nodes()` walks the raw
  `{data, errors}` envelope manually (`_walk`) and can accept partial
  data (ghost-account node errors).

### Studies — `src/pipeline/studies/` (one analysis = one module)
Each module's docstring states its estimand, caveats, and revision
history; the report section title names the module. Highlights:

| module | claim it produces | key design point |
|---|---|---|
| `paper_tables.py` | Figures 2–3 (AI usage; merged kLOC/core author ×2.66) | CW + seeded CIs; LOC capped 20k/PR |
| `productivity.py` | decomposition, persistent authors, aisplit, **adoption cohorts** (Figure 4) | fleet cohort (≥300 merged PRs/quarter) isolated BEFORE AI-timing cohorts; user-typed bot authors excluded |
| `event_study.py` | volume jump at first AI-marker month | w8-mature months only for merged outcome; submitted-LOC outcome needs no censoring |
| `attention.py` | comments/kLOC decline (−55/−57%) | bot-clean numerator via `split_reviews`; size-band decomposition |
| `fates.py` | matched-horizon merge/reject/limbo | never compares "ever" across cohorts; w8 primary, w26 sensitivity |
| `review_action.py` | responsiveness to human asks (CLEAN lane identified) | PPS sample + Horvitz–Thompson weights; paginated commit pulls with completeness metadata (`_conn_commits`, `_suspect`) |
| `slices.py` | adoption groups / org types; two-sided bound | conditional metrics re-floor the conditioning denominator |
| `layer_c_precision.py` | per-prefix precision | hand-validated samples; droid/ basis is complete enumeration (METHODS §2) |

### Drivers — `scripts/`
- `regenerate.py` — canonical quarterly path: fixed-point population loop,
  DONE sentinels, gap-free cell coverage gates, manifest with SHA-256s;
  stage F refuses to write a report over incomplete coverage.
- `report.py` — the 19 sections at quarter/month granularity; monthly
  runs tag inherently-quarterly sections `[quarterly]`.
- `monthly_update.py` — incremental month: wipes+re-collects provisional
  month, collectable-population filter, appends to the month registry.
- `plot_paper_tables.py`, `plot_adoption_cohorts.py` — Figures 2/3/4
  (broken x-axis: Q1-2024 is ~7 quarters before the continuous window).

## Cross-cutting conventions (the frozen rules — METHODS §1d)

1. All per-PR outcomes at **8 weeks from creation** (w8); Q2-2026
   provisional until the Sept 1, 2026 re-pull.
2. Fate comparisons only at **matched horizons**.
3. Primary attention = **human** comments/kLOC (bot comments can never
   share a numerator with human comments).
4. Weighting labeled on every number; CW with window weights primary.
5. Layer C: measured FP class excluded; per-prefix precision stated;
   two-sided bound on weak prefixes.
6. Q1-2024 is a detector-validity baseline, not an AI-usage estimate.
7. Seeded everything; SHA-256 manifests; fail-hard on incomplete cells.

Plus: LOC = additions+deletions capped at 20,000/PR; all detection rates
are floors (one quantified exception: the two-sided bound).

## Gotchas a reviewer should know before reading code

- **Two cell-store generations** coexist (census, census-v2); only v2 has
  `headRefName`/`mergedBy`. Studies must tolerate their absence — that is
  why `self_merged` can be None and layer C returns None on old cells.
- **`gh` swallows `--jq` on error** — never call `gh api --jq` directly
  for GraphQL that can partially fail; use `ghx.graphql_nodes`.
- **Bot filtering is two-sided**: `__typename == "Bot"` catches App bots;
  `is_bot_login()` catches User-registered bots. Reviewer classification
  uses both; author-level studies exclude both as authors.
- **Fleet operators**: ~43 human accounts merge 300–4,400 PRs/quarter
  (agent fleets, partly unmarked). Author-level means are whale-sensitive
  — the adoption study isolates them as their own cohort; any new
  author-level analysis should consider the same.
- **PPS sample ≠ uniform sample**: anything computed on
  `review_action_sample.jsonl` must use the HT weights (`_inv_pi`), not
  raw counts.

## Tests as documentation — `tests/`

118+ tests, each docstring naming the finding/review item it pins
(repo rule: reproduce a bug with a RED test before fixing it — see
CLAUDE.md). Fast (`uv run pytest -q`, <1s, no network). Good entry
points: `test_detect.py` (detection + review semantics, w8, cutoff),
`test_analyze.py` (dedup/freshness, registry, weighting),
`test_census.py` (completeness, self-heal, fail-hard).

## Where does number X in the paper come from?

Every table in `artifacts/report_generated.md` is emitted by exactly one
module invocation, printed in its section header by `scripts/report.py`.
To reproduce one number: run that module with `PYTHONPATH=src` (the
section title contains the exact `--table`/`--cut` argument); to
reproduce everything: `scripts/regenerate.py`. Figures map 1:1 to
`scripts/plot_*.py`.
