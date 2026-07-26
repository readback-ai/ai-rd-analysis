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
        │                       $AIRD_DATA_DIR/raw/census-v2/*.json (single store)
        ▼
detect.py                 per-PR classification (the ONLY place detection lives)
        ▼
analyze.py                cells → per-repo rates → CW means + bootstrap CIs
studies/layers.py         exact layered decomposition (A/B/C disjoint)
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

### The census cell — the one data structure everything reads

A CELL is one JSON file in `$AIRD_DATA_DIR/raw/census-v2/`, keyed
`<repo>@<date-range>.json`, holding the list of PR nodes CREATED in that
range (from `census.PR_QUERY`; a repo-quarter is one full-range cell or
several contiguous sub-window cells). Per PR node:

```jsonc
{
  "number": 4711,
  "createdAt": "2026-04-02T09:15:00Z",   // period bucketing + w8 anchor
  "mergedAt":  "2026-04-03T10:00:00Z",   // null if unmerged
  "closedAt":  null,
  "authorAssociation": "MEMBER",          // insider = MEMBER/OWNER/COLLABORATOR
  "additions": 120, "deletions": 30,      // LOC (capped 20k/PR downstream)
  "changedFiles": 4,
  "headRefName": "codex/fix-race",        // layer C input
  "author":   {"login": "alice", "__typename": "User"},   // layer B if Bot
  "mergedBy": {"login": "bob",   "__typename": "User"},   // self-merge
  "commits":  {"nodes": [{"commit": {                      // FIRST 12 commits
      "message": "…trailers live here…",                   // layer A markers
      "authors":  {"nodes": [{"email": "noreply@anthropic.com"}]},  // <=6
      "committer": {"email": "…", "user": {"login": "…"}}}}]},
  "reviews":  {"nodes": [{                                 // FIRST 15 reviews
      "author": {"login": "gemini-code-assist", "__typename": "Bot"},
      "submittedAt": "2026-04-02T12:00:00Z",               // w8-windowed
      "state": "CHANGES_REQUESTED",
      "comments": {"totalCount": 3}}]}
}
```

**How a cell's date range is chosen** (`census.census_repo_period`):
the period token (a quarter or a YYYY-MM month) resolves to its full
range; if the precount says the repo has ≤45 PRs in it, one full-range
cell is pulled. Otherwise the range is split by `census.subwindows` into
k CONTIGUOUS, gap-free, non-overlapping sub-ranges — k adaptive from the
precount (ceil(total·1.1/45), capped at one window per day) so a
repo-period is never silently capped by pagination. So the store holds a
mix of quarter-shaped, month-shaped (monthly updates), and sub-window
cells; a repo-quarter = one full-range cell or its exact sub-window
partition.

**Cells are immutable snapshots.** A cell freezes its PRs' event state
at collection time and is never edited — late events (a June PR merged in
July) enter only when a monthly update wipes and fully re-queries the
trailing two months, writing NEW cells whose PRs supersede the stale
quarter cells' via the freshness rule below. Old cells stay on disk for
the months not being revised; overlap is safe because dedup is per-PR.

**Cells are storage units, not analysis units.** Periodization happens
PER PR, not per cell (`analyze.group_by_period`): quarterly tables
assign a cell's PRs to the quarter containing the cell's range; monthly
tables bucket each PR by its own `createdAt` month — so the monthly
report reads the SAME cells and re-partitions them exactly (every PR's
createdAt lies inside its cell's range by construction; a quarter-shaped
cell contributes its April PRs to April, May PRs to May, …). No separate
monthly collection exists, and overlapping cells (full-quarter +
sub-window + re-collected month) cannot double-count: PRs are deduped by
number within (repo, period), richer-then-fresher record winning.

What is deliberately NOT here: per-commit timestamps (the post-as-of
marker residual, METHODS §0), review/comment bodies (privacy), issue
comments (only formal review objects count). The 12-commit/15-review
truncation is a documented downward bias (METRICS §7). Studies needing
more (per-commit dates for review_action) run their own hydration pulls.
Everything a PRClass contains is derived from exactly these fields.

### Detection — `src/pipeline/detect.py`
The single canonical home of ALL detection. Nothing else defines a marker,
a bot list, or a review rule.

- **Layer A** `pr_ai_tools()` — commit-forensic markers (`MARKERS`:
  Claude, Cursor, aider, Codex, OpenHands, vetted self-identified
  agents; incl. committer identities). Floors: only
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
- `load_cells()` — reads the single census store (`raw/census-v2/`),
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

### Study frame — `src/pipeline/frame.py`
The one census pass every study consumes (cells → period grouping →
population filter → eligibility profile → classified, capped PR facts).
Studies contain only their accumulation logic; the guards live here once.

- `study_frame(level, periods, ranges, granularity)` — flat generator of
  `PRFact` records `(repo, period, pr, cls, loc, author, insider,
  bot_author)`; `study_groups(...)` is the group-shaped view for
  per-repo floors/rates (slices). Iteration order is load-bearing (the
  seeded bootstrap stream).
- Eligibility profiles (CONTEXT.md): `pr` = human-authored PR population
  (App-bot skip only — attention report table, orphans); `author` =
  attributable human authors (adds `is_bot_login` hygiene — author-level
  studies, Figure 6 role cut, channels); `all` = no author filter
  (population tables; AND the AI-contrast review-behavior outputs —
  Figures 6-by-AI/7/8 and fates' AI cohorts, with fleet exclusion —
  issue #2 resolution: agent-authored PRs count in the AI series).
- `ai_contrast_eligible(fact)` — MANDATORY on top of `all` at every
  AI-contrast site (2026-07-25 review): AI-involved PRs bypass author
  hygiene, everything else must clear `author`, so non-AI bots and
  login-less authors cannot enter the nonAI comparison arm. Applied in
  `review_mix(by="ai")`, `fates_at`, `attention_by_ai`, and the
  responsiveness frame (`eligible()` + `lane_rows` — keep the two
  identical or the manifest payload check fails).
- Owns `PERIODS`, `CAP` (20k LOC/PR), and `population_repos()`.
- Tests: `tests/test_frame.py` encodes the pre-refactor per-study guards
  verbatim as reference implementations.

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
| `layers.py` | exact A/B/C decomposition (report §4) | disjoint by precedence B > A > C |
| `paper_tables.py` | Figures 2–3 (AI usage; merged kLOC/core author ×2.66) | CW + seeded CIs; LOC capped 20k/PR |
| `productivity.py` | decomposition, persistent authors, aisplit, **adoption cohorts** (Figure 4) | fleet cohort (≥300 merged PRs/quarter) isolated BEFORE AI-timing cohorts; user-typed bot authors excluded |
| `event_study.py` | volume jump at first AI-marker month | w8-mature months only for merged outcome; submitted-LOC outcome needs no censoring |
| `attention.py` | comments/kLOC decline (−55/−57%) | bot-clean numerator via `split_reviews`; size-band decomposition |
| `fates.py` | matched-horizon merge/reject/limbo | never compares "ever" across cohorts; w8 primary, w26 sensitivity |
| `review_action.py` | responsiveness to human asks (CLEAN lane identified) | two designs, one frame: EQ sample → unweighted responded%, PPS-by-LOC + HT weights → post-ask LOC share; paginated commit pulls with completeness metadata (`_conn_commits`, `_suspect`); the PR's own bot counts as author response (issue #2) |
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
- `plot_*.py` — one script per figure (`plot_paper_tables.py` renders
  Figures 2 AND 3; `plot_fig6_review.py` renders both fig6 variants —
  core/external and AI/non-AI, formerly twin files). All house style
  lives in **`src/pipeline/figstyle.py`** (2026-07-26 architecture
  review, candidate 2): the broken x-axis panel pair (Q1-2024 sits ~7
  quarters before the continuous Q4-2025..Q2-2026 window), the
  w8-provisional shaded band, the paired dark/light slice hues, the six
  LOC series, and the unified zero-denominator suppression (`cell()` —
  an absent cell or an AI-conditioned rate at the Q1-2024 baseline is
  None, never a plotted zero). Scripts keep only their data wiring and
  panel layout; `tests/test_figstyle.py` pins the style constants.

## Cross-cutting conventions (the frozen rules — METHODS §1d)

1. All per-PR events — fates AND review submissions — at **8 weeks from
   creation** (w8), bounded by the as-of; mature PRs immutable under
   as-of advances. Q2-2026 provisional until the Sept 1, 2026 re-pull.
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

- **One cell store** (`raw/census-v2/` — the name is historical; the
  legacy generation was retired 2026-07-20 after re-collection). Studies
  still tolerate absent `headRefName`/`mergedBy` per-record (`self_merged`
  None, layer C None) for robustness.
- **`gh` swallows `--jq` on error** — never call `gh api --jq` directly
  for GraphQL that can partially fail; use `ghx.graphql_nodes`.
- **Bot filtering is two-sided**: `__typename == "Bot"` catches App bots;
  `is_bot_login()` catches User-registered bots. Reviewer classification
  uses both; author-level studies exclude both as authors.
- **Fleet operators**: ~43 human accounts merge 300–4,400 PRs/quarter
  (agent fleets, partly unmarked). Author-level means are whale-sensitive
  — the adoption study isolates them as their own cohort; any new
  author-level analysis should consider the same.
- **A null is not an absence** (2026-07-25 incident, cost: a full re-pull).
  `ghx.graphql_nodes` discards the `errors` array by design — one ghost
  account must not drop a whole repo-period — so its result cannot tell "the
  entity is gone" from "this batch timed out / hit the secondary rate
  limit": GitHub answers both with null aliases. A re-pull recorded **1,345
  live PRs** (59 in `vllm-project/vllm`, 31 in `apache/airflow`) as
  permanent `unretrievable` nonresponse, 27.9% of the EQ selection, which
  published Q2-2026 `CLEAN+AI` as **n=0**. Rules: (1) any code deciding an
  absence is PERMANENT must use `ghx.graphql_envelope` and inspect `errors`
  itself — only all-`NOT_FOUND` is definitive (`_confirm_gone`); (2) prefer
  deferring, which costs one refetch, over a tombstone, which silently
  corrupts the sample; (3) the heaviest repos fail first, so the damage
  concentrates in exactly the PRs that matter most.
- **"Documented" is not "acceptable"**: `coverage_gaps` treats a tombstone
  as resolved coverage, so mass nonresponse passed the fail-hard guard —
  a non-probability subset wearing the right paperwork.
  `require_complete_sample` now also enforces `MAX_NONRESPONSE` (2%) once
  `MIN_NONRESPONSE_N` (20) stones exist. Genuine nonresponse has run
  0.1-0.3%; `--repair` retries every tombstone.
- **Two samples, one frame — match the estimand to the design**: the
  review-action study draws the SAME eligibility frame twice. PPS-by-LOC
  (`review_action_sample_v2.jsonl` + `review_action_manifest_v2.json`)
  carries LOC-share estimands and **must** use the HT weights (`_inv_pi`);
  the equal-probability companion (`review_action_sample_eq_v1.jsonl` +
  `..._manifest_eq_v1.json`) carries per-PR RATE estimands and must use
  **raw counts** — uniform inclusion cancels in the ratio, and applying
  `_inv_pi` there reintroduces the tiny-LOC weight domination that forced
  the EQ draw (issue #2). Each manifest fingerprint is design-tagged so the
  two can never validate each other. Sample sizes are independent, so gate
  each output on ITS OWN count (`n` for rates, `n_loc` for LOC shares).
  compute() fails hard on frame mismatch or incomplete coverage, naming the
  design and file.

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
