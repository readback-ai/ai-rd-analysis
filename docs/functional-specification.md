# Functional specification — AI-assisted development practices study

**Purpose: enable a clean-room reimplementation that validates the published
results.** This document specifies WHAT the pipeline and every analysis
compute — inputs, rules, estimators, outputs — without prescribing how. A
reimplementation built solely from this document, given the same external
inputs, should reproduce the published numbers to the bar defined in §1.2.

Provenance: written 2026-07-26 against commit `7370182`; revised 2026-07-27
against `feat/primary-implementation` at `cc37f06`; revised 2026-07-28 at
`8c89503` after the fix wave — issues #6 (R4 evidence dedup, population
refresh), #7 (zero-precount confirmation), #3 (GraphQL envelope logging +
strict pagination) closed; #8 (layer-C scoping) code landed with the
scoped re-scan in flight; #10 (fleet cache) fixed in code; the per-cell
bootstrap-stream fix merged (F-30/F-43); one report section added
(botcheck, §8.2.10). Revised again 2026-07-28 on the #9 merge (PR #16,
bot self-reviews excluded — DET-V1/V3). Where the codebase and the
prose docs (METHODS/METRICS) disagreed, this spec follows the **code as
implemented** (so published numbers reproduce) and records the divergence
in Appendix A; the published report/results artifacts still reflect the
pre-refresh population until the next full regeneration (see §10.3).

Conventions used here:

- Normative rules carry stable IDs (`POP-3`, `DET-A2`, …) for reference from
  validation findings.
- `source:` tags name the module/function that implements a rule. They are
  traceability aids only — nothing about module structure is normative.
- "MUST/NEVER" mark rules whose violation changes published numbers;
  "SHOULD" marks rules whose violation changes robustness or failure
  behavior but not the headline numbers.
- Appendix B collects every constant in one table.

---

## 1. Scope and reproduction bar

### 1.1 What the system is

An empirical measurement system that, from public GitHub metadata:

1. Constructs a **population of leading AI organizations** (228 orgs after
   the 2026-07-27 issue-#6 refresh: 182 admitted whole, 46 admitted only
   for their AI-topic repos; the 2026-07-10 run had 229/47 — sony dropped
   under the deduplicated R4 evidence) from third-party lists plus
   measured evidence (§4).
2. Enumerates their qualifying repositories (2,136 at the refresh) and performs
   a **complete census of pull requests** in four calendar quarters —
   Q1-2024 (baseline/detector-validity control), Q4-2025, Q1-2026, Q2-2026 —
   with a hard study cutoff of **2026-06-30** on PR creation (§5).
3. Classifies every PR for **AI involvement** via three independent
   detection layers (commit markers, agent authorship, agent branch naming)
   and classifies its reviews into human / AI-reviewer / other-bot (§6).
4. Aggregates per-repo rates into contributor-weighted period series with
   bootstrap confidence intervals (§7), and runs 21 named analyses
   (usage, volume/productivity, adoption cohorts, event study, review
   attention, PR fates, responsiveness, slices/bounds) emitted as one
   generated report plus figures (§8), with three sampled auxiliary studies
   (§9).

### 1.2 Reproduction bar (what "validated" means)

- **VAL-1** Deterministic quantities MUST match exactly: population
  membership and scopes, repo manifest, per-PR classifications on identical
  census records, per-repo rates, weighted point estimates, seeded sample
  membership (the responsiveness study's two draws), and all counts.
- **VAL-2** Bootstrap confidence intervals are **per-cell reproducible**
  (fixed 2026-07-28; formerly a shared call-order-dependent stream — flag
  F-30): each reported CI draws from its own stream derived from the cell
  key (AGG-8), so a CI depends only on (key, the ordered per-repo pair
  list, draw count) — not on what else the run computed. Bit-for-bit CI
  reproduction additionally requires Python's Mersenne-Twister
  `random.Random` semantics (seeded per AGG-8's derivation) and the same
  pair-construction order (the frame's iteration order, which is part of
  the contract); an implementation on a different RNG matches
  statistically (same interval to ~display precision).
- **VAL-3** Anything collected live from GitHub (rather than replayed from
  the shared census store) can differ legitimately: repos get deleted,
  privatized, force-pushed. Validation of collection is therefore
  reconciliation-shaped (counts within documented drift allowances), while
  validation of classification/analysis on a shared store is exact.
- Validation anchors — published values a reimplementation should hit — are
  in §10.3.

---

## 2. Vocabulary and the study frame

### 2.1 Units and periods

- **FR-1** The unit of scoping is the **organization** (a GitHub org/user
  account owning repos). The unit of observation is the **pull request**,
  censused per (repository, period). Repositories belong to exactly one org
  (the `owner/` prefix of `owner/name`).
- **FR-2** Periods are the frozen quarter map (source: `scan_orgs.QUARTER_RANGES`):

  | token | inclusive date range |
  |---|---|
  | Q1-2024 | 2024-01-01 .. 2024-03-31 |
  | Q3-2025 | 2025-07-01 .. 2025-09-30 |
  | Q4-2025 | 2025-10-01 .. 2025-12-31 |
  | Q1-2026 | 2026-01-01 .. 2026-03-31 |
  | Q2-2026 | 2026-04-01 .. 2026-06-30 |

  **Q3-2025 is defined but NOT part of the study**: it was partially
  collected (~60 repos) early on, is excluded from the censused-quarter
  list, the coverage gate, and the analysis frame, and must never surface
  in reported output (flag F-13 records two leak paths). The four
  **censused quarters** are Q1-2024, Q4-2025, Q1-2026, Q2-2026.
- **FR-3** Month tokens `YYYY-MM` are first-class period tokens resolving to
  calendar-month inclusive ranges. Month-granularity analysis re-buckets the
  same censused PRs by the month of their creation timestamp (no separate
  collection); a month is reportable only if it lies inside a censused
  quarter or is explicitly registered as an incremental month (§5.8).
- **FR-4** A PR belongs to a period by its **creation timestamp**: cells are
  collected with a `created:` range filter, and a cell maps to a quarter by
  whether the cell's start date falls inside the quarter's range.

### 2.2 Time semantics: CUTOFF, AS_OF, and the w8 rule

- **FR-5 (CUTOFF)** The frame end is `2026-06-30T23:59:59Z`: the last PR
  creation date in the study. It bounds PR **creation only**, never events,
  and never changes.
- **FR-6 (AS_OF)** A separate **data-collection stamp** records when census
  data was last (re-)pulled. At the initial collection it equals CUTOFF; it
  is advanced manually at each scheduled re-pull. It governs **maturity
  only** (FR-8). (Flag F-27: it is hand-maintained with no cross-check.)
- **FR-7 (w8 event window)** ALL per-PR events — merges, closes, AND review
  submissions — count iff they occur strictly **within 56 days of the PR's
  creation**: `(event_time − created_time)` truncated to whole days `< 56`.
  An event inside the window counts even if it lands after CUTOFF. Events
  with no timestamp never count. (Note the comparison is strict-less-than on
  truncated days, and a malformed event timestamp *earlier* than creation
  also passes — flag F-24.)
- **FR-8 (maturity)** A PR is **w8-mature** iff `(AS_OF − created_time)` in
  truncated days `≥ 56`. Fate and review metrics are **undefined** (skipped,
  never zeroed) on immature PRs. Consequences: trailing quarters are
  provisional until a re-pull after their last window closes (for Q2-2026:
  on/after 2026-09-01); mature PRs are immutable under re-collection — an
  AS_OF advance only ever adds newly mature PRs.
- **FR-9 (matched horizons)** Fate comparisons across cohorts MUST use the
  same horizon (w8 primary; w26 = 182 days as sensitivity). "Ever resolved"
  quantities must never be compared across cohorts.

### 2.3 Per-PR derived facts

- **FR-10 (LOC)** A PR's LOC is `additions + deletions`, **capped at
  20,000** wherever it enters a study aggregate (so one vendored monster
  cannot dominate a numerator or denominator).
- **FR-11 (insider)** A PR author is an **insider** iff the PR's author
  association is `MEMBER`, `OWNER`, or `COLLABORATOR`. (Known limitation:
  private org membership makes real staff look external.)

### 2.4 Eligibility profiles (which PRs enter a study)

Every study consumes the same stream — census cells → period grouping →
population filter (repo must be in the repo manifest, §4.6) → eligibility
profile → classified PR facts — and differs only in its named profile
(source: `frame.py`):

- **FR-12 profile `all`** — no author filtering. Used by population-level
  usage tables where agent-authored output must count.
- **FR-13 profile `pr`** — drop PRs authored by **App-typed bot accounts**
  (author `__typename == "Bot"`: dependabot, renovate, CI, and coding
  agents). Used where the estimand is how humans review each other.
- **FR-14 profile `author`** — `pr` plus: the author must have a login and
  the login must not match the user-typed-bot heuristic (DET-R2). Used by
  author-level productivity/event studies (a bot is not a productivity
  unit).
- **FR-15 (`ai_contrast_eligible`)** — the mandatory companion gate for
  AI-vs-nonAI contrasts running on profile `all`: a PR bypasses author
  hygiene **only if it is AI-involved** (DET-4); otherwise it must satisfy
  the `author` conditions. This keeps agent-authored PRs in the AI arm while
  barring dep-bots/user-bots/login-less authors from the nonAI arm.
  Consequences: `all = AI + nonAI` exactly, while `all = insiders +
  externals + bot-authored` (a Bot has no author association) — the
  residual is footnoted where relevant.
- **FR-16 (fleet exclusion)** The AI-contrast review-behavior outputs
  (Figure 6 by-AI, Figure 7, Figure 8, fates' AI/nonAI cohorts) additionally
  exclude PRs authored by **fleet operators** (§8.14), or split them into
  their own slice where a figure calls for it.

### 2.5 Three bot-detection heuristics (deliberately different scopes)

- **DET-R1 (App bots)** Account `__typename == "Bot"` — GitHub
  App-installed identities.
- **DET-R2 (user-typed bots)** A login (lowercased) is a bot iff it ends
  with one of `-bot`, `_bot`, `[bot]`, `-ci`, `-robot`, `-agent`, `_agent`,
  or starts with `bot-`. Anchored so human names ("talbot") never match.
- **DET-R3 (contributor-stats bots)** In contributor weighting only, a
  login is excluded iff it ends with `[bot]` or is empty.

These three are **intentionally not unified** in the current system; the
inconsistency (weights count user-typed bots as humans; a commit-level
variant in the responsiveness study is weaker still) is flag F-17/F-18.

---

## 3. External dependencies

Everything the system consumes from outside. A reimplementation needs
equivalent access; the **search-semantics assumptions** (EXT-9) must be
re-verified, since the study's numbers silently depend on them.

### 3.1 GitHub REST search

- **EXT-1 Commit search counts** (`GET /search/commits`, field
  `total_count`): used by the org marker scan and evidence rules. Query
  shapes: `org:{org} {term}` and `org:{org} {term}
  author-date:{YYYY-MM-DD..YYYY-MM-DD}`. Note windowing is by
  **author-date**, not committer-date (flag F-20).
- **EXT-2 Commit search results** (paginated items, field
  `repository.full_name` only): used by repo enumeration. Hard API cap:
  **1,000 results per query**; saturation must be detected (COL-4).
- **EXT-3 Issue search counts** (`GET /search/issues`, field
  `total_count`): PR-count denominators (`repo:{r} is:pr created:{range}`),
  branch-prefix counts (`org:{o} is:pr head:{prefix} created:{range}`).

### 3.2 GitHub GraphQL

- **EXT-4 PR search nodes** — the census query. For a search
  `repo:{repo} is:pr created:{range} sort:created-desc`, page size 50,
  cursor pagination, each PR node carries exactly:
  - scalars: `number createdAt mergedAt closedAt authorAssociation
    additions deletions changedFiles headRefName`
  - `author{login __typename}`, `mergedBy{login __typename}`
  - `commits(first:12){ commit{ message, authors(first:6){email},
    committer{email, user{login}} } }`
  - `reviews(first:15){ author{login __typename}, submittedAt, state,
    comments{totalCount} }`

  **The caps are normative**: only the first 12 commits (6 author emails
  each) and first 15 reviews of a PR are ever observed by the census; no
  per-PR pagination. Both truncations bias detection downward (consistent
  with the study's floors framing). Conversation comments and per-commit
  timestamps/LOC are NOT in the census (studies needing them re-pull, §9).
- **EXT-5 PR hydration** — targeted re-pulls add to EXT-4's field set:
  `repository{nameWithOwner}`, per-commit `committedDate` (and, in the
  responsiveness study, per-commit `additions deletions` with commit-author
  `user{login}`), and `comments(first:40){author{login __typename}}`.
  The responsiveness study paginates commit lists at 100/page to a clean
  terminal page (§9.1); GitHub serves at most **250 commits per PR**
  regardless of the claimed total (measured 2026-07-26).
- **EXT-6 Org repo enumeration** — for repo-scoped orgs: public, non-fork
  repos ordered by stars descending, 100/page, fields `name`,
  `stargazerCount`, and up to 20 repository topics (`topic.name`).
- **EXT-7 GraphQL rate budget** — `GET /rate_limit`
  (`resources.graphql.remaining/reset`) consulted to pace collection.
  Pacing affects results only through give-up semantics (COL-1).

### 3.3 GitHub REST (non-search)

- **EXT-8 Contributor statistics** (`GET /repos/{repo}/stats/contributors`):
  per-contributor weekly buckets `{author.login, weeks[{w: week-start epoch,
  c: commit count}]}`. Semantics that matter: the endpoint computes lazily
  (HTTP 202 with empty body until ready — retry, never record), and returns
  at most the **top 100 contributors** per repo (an undocumented-in-repo
  ceiling on weights; flag F-19).

### 3.4 Search-semantics assumptions (MUST re-verify)

- **EXT-9a Bare-term commit search** matches co-author trailers in commit
  message bodies; the `author-email:` qualifier matches **primary authors
  only** and returns zero for co-authored commits. All trailer-based
  discovery MUST use bare terms. (Measured consequence of getting this
  wrong: order-of-magnitude undercount.)
- **EXT-9b** GitHub commit search has **no committer-email qualifier**;
  search terms for committer-identity tools under-recall by construction and
  are only discovery floors — per-PR classification uses the census's actual
  committer fields instead.
- **EXT-9c** `head:{prefix}` in issue search behaves as a **prefix match**
  on head branch names (e.g. `head:codex/` matches `codex/fix-bug`). Every
  layer-C count relies on this; a tokenization change would silently zero
  the counts rather than error.
- **EXT-9d** Commit search indexes **default branches only** — an inherent
  bound on every commit-marker count (not previously stated in the repo;
  flag F-21).
- **EXT-9e** Search endpoints exhibit **brownouts**: HTTP 200 responses with
  empty/partial result sets, and rate-limit error bodies shaped as JSON.
  Normative consequences: every response is shape-validated before storage;
  a count query returning non-numeric content is a failure, not a zero; and
  census completeness is gated against an independent precount (COL-8).

### 3.5 Third-party inputs (files, as interfaces)

Snapshot/transcription files. Formats are tab-separated unless noted; `#`
lines and blank lines are comments everywhere.

| input | interface (fields consumed) | role |
|---|---|---|
| candidates list | `handle \t tag[\|tag…]`; tags `lfai`, `hf-hub`, `gh-topic` | transcription record of three ecosystem lists (LF AI & Data landscape, Hugging Face top orgs, GitHub AI-topic orgs) — the ONLY ecosystem input the code reads; the raw list snapshots are provenance only |
| Epoch org map | `EpochName \t github-handle`, `-` = unmapped | Epoch AI notable-models orgs (epoch.ai, CC-BY) → tag `epoch` |
| TechCrunch orgs | col 0 = handle | 2025 $100M+ AI funding round-up transcription → tag `techcrunch` |
| curated orgs | col 0 = handle | declared hand-curated remainder → tag `curated` |
| conglomerates | one handle per line | umbrella orgs forced repo-scoped (google, microsoft, alibaba, apple, apache, …) |
| org overrides | `handle \t exclude\|include-full \t rationale` | published adjudications (12 excludes, 3 includes at the current run) |
| org types | `org \t public\|private\|community` | ownership classification as-of cutoff, for slices; every population org MUST have a row |

Classification metadata (topics, stars, descriptions) has no historical API:
it was observed 2026-07-07..09 and applied uniformly (as-of policy). See
EXT-15 for the replay-vs-re-scan rule this implies.

### 3.6 Derived inputs whose generators are NOT in the repo (flag F-1)

The population rules consume four machine-generated scan files, and the repo
manifest consumes a fifth, for which **no generating code exists in the
repository** — their committed contents are frozen inputs of the published
run. This section specifies both the interface AND the regeneration
procedure, so a clean-room build can either replay the committed files
(exact reproduction of the published population) or regenerate equivalents
(a fresh scan may admit a slightly different population; see COL-1/F-22 on
run-dependence). METHODS §1's five rules are the *decision* logic; these
are the *measurement* inputs those rules consume.

- **EXT-10 `ai_scan`** — headerless `org \t n1 \t n2 \t sources`; only
  column `n1` is read, as an org-level all-time AI-marker commit count.
  Regeneration: the org marker scan (COL-3a) over the candidate set with
  no date window — `n1` = the largest per-tool max-over-terms count.
  (The committed values are legacy: they reflect the pre-audit 2-tool
  claude/cursor marker set; flag F-2. Regenerating with the current
  6-tool set is a superset — evidence can only grow, and R4 admission is
  a max across sources, so replay-vs-regenerate differences are one-sided.)
- **EXT-11 `recheck_scan`** — `org \t probe \t n`, per candidate org:
  `{codex,copilot,cursor,claude}_br` = issue-search counts of
  prefix-branch PRs (`org:{org} is:pr head:{prefix}`, EXT-3);
  `{claude,cursor}_mk` = commit-search marker counts for those tools
  (EXT-1, bare terms); `{copilot,devin}_ag` = issue-search counts of
  PRs authored by that coding agent; `total_pr` = the org's PR count
  (collected but never consumed — flag F-3). The original scan's date
  windows are unrecorded in the repo (METHODS bounds them at ≤ cutoff);
  a regeneration should use the study window and note the substitution.
- **EXT-12 `org_scale`** — header + `org \t repos \t flagship_stars \t
  top5_stars \t sources \t in_v1`; only `flagship_stars` (≥1k test) is
  consumed. Regeneration: `flagship_stars` = star count of the org's
  most-starred public repo (first result of EXT-6's stars-descending
  enumeration).
- **EXT-13 `top5_topics`** — JSON-lines `{org, top5: [{name, stars, ai}×5]}`
  ordered stars-descending; `ai` is 0/1 = "repo declares ≥1 topic in the
  AI_TOPICS dictionary" (POP-3). Regeneration: first 5 of EXT-6's
  enumeration with the topic test applied (topics observed as-of the
  classification snapshot, 2026-07-07..09 for the published run).
- **EXT-14 `fullorg_repos`** — plain list of `owner/repo`: the repos of
  full-scope population orgs passing the enumeration keep rule (2,006 at
  the current run). Regeneration: run COL-3/COL-4 over full-scope orgs
  and take the kept repos (column 1 of the enumeration output).
- Also generator-less: the all-time contributor-weights sensitivity file
  (`repo, core_contributors`, ≥10 commits ever) — same procedure as
  COL-14 with no date window and a ≥10 floor; sensitivity-only.

### 3.7 Snapshot replay vs re-scan (EXT-15)

Several inputs are **point-in-time observations of state GitHub and the
list providers keep no history for**: repo topics and star counts
(EXT-6, EXT-12, EXT-13), the Hugging Face hub rankings and other
ecosystem lists behind the candidates transcription, org descriptions,
and org-type/ownership. These drift continuously; the published run
observed them 2026-07-07..09 and applied them uniformly (the as-of
policy).

- **EXT-15a (replay — normative for validation).** Any run whose purpose
  is to reproduce or validate the published results MUST consume the
  committed snapshot files as-is (candidates transcription, Epoch/
  TechCrunch/curated lists, org types, `org_scale`, `top5_topics`,
  strata rows, and the frozen scan outputs of §3.6). This is what makes
  the population a pure function of committed inputs (VAL-1) and keeps
  known drift out of the comparison.
- **EXT-15b (re-scan — for fresh studies only).** Regenerating any
  snapshot (via the §3.6 procedures or EXT-6) is a **deliberate
  population/classification revision**: the new observation date MUST be
  recorded in the regenerated file, the change treated as a new
  classification snapshot (METHODS §0), and results not compared
  number-for-number against the published run — membership and slice
  assignments may legitimately move with the drifted metadata. Between
  deliberate revisions, population and classification metadata stay
  frozen (COL-13).

---

## 4. Population construction

Deterministic, API-free: source lists + prior scans → the population table
(`org, scope ∈ {full, repo}, why, top5_ai`). Source: `org_set.py`.

### 4.1 Candidates (R1)

- **POP-1** The candidate set is the union of: the three ecosystem-list
  transcriptions (tags `lfai`, `hf-hub`, `gh-topic`), Epoch AI notable-model
  orgs (`epoch`), TechCrunch $100M+ funding orgs (`techcrunch`), and the
  declared curated remainder (`curated`). Handles are canonicalized
  case-insensitively; the **first-seen casing wins** and becomes the literal
  string used in every downstream `org:` search (candidates are iterated in
  case-insensitive sorted order, so this is deterministic given fixed
  inputs; flag F-4).
- **POP-2** The **AI-developer lists** are `epoch ∪ techcrunch ∪ curated`.

### 4.2 Identity dictionary

- **POP-3** `AI_TOPICS` — a frozen 28-topic dictionary of
  maintainer-declared AI topics: machine-learning, deep-learning,
  artificial-intelligence, ai, neural-network, neural-networks, llm, llms,
  large-language-models, nlp, natural-language-processing, computer-vision,
  reinforcement-learning, generative-ai, transformers, diffusion-models,
  ai-agents, mlops, speech-recognition, text-to-speech, llmops,
  language-model, gpt, chatgpt, stable-diffusion, rag, fine-tuning,
  model-serving. Generic/gameable terms ("agents") are deliberately absent.
  Descriptions and org-name heuristics are deliberately NOT used.

### 4.3 The rules, in evaluation order

For each candidate org (lowercased key `lo`):

- **POP-4 (overrides first)** If the override table says `exclude` → out,
  unconditionally.
- **POP-5 (R2 quality)** Out unless `lo` passes the star test OR is on an
  AI-developer list. Star test: `flagship_stars ≥ 1,000` in the org-scale
  input, OR the org's top-1 starred repo (from the top-5 input) has
  ≥ 1,000 stars.
- **POP-6 (R4 evidence)** Out unless evidence(`lo`) ≥ 5 OR the rate branch
  holds. Evidence is a **distinct-AI-evidence-PR count**: the maximum
  across four sources (so no PR adds evidence from two sources), and
  within a source no PR counts twice either:
  1. the ai_scan count (column n1, a single number);
  2. the **MAX** over recheck probes except `total_pr` (probes overlap —
     one PR can match its branch and its markers);
  3. the sum over **keyed** (org, quarter, prefix) branch-scan cells
     (dedups re-appended checkpoint rows), **excluding Q1-2024** (the
     false-positive control never admits) — an exact distinct count,
     since creation-dated quarters partition PRs and the prefixes are
     pairwise non-nested;
  4. the census-derived org evidence count `e` (POP-11).

  Rate branch: from the census evidence pair `(e, t)` only:
  `t > 0 AND e ≥ 1 AND e/t ≥ 0.001`.
- **POP-7 (R3 identity)** The org is an AI developer iff it is on an
  AI-developer list, OR `top5_ai ≥ 2` (count of its top-5 starred repos
  whose `ai` flag is set), OR its override is `include-full`.
- **POP-8 (R5 scope)** In priority order:
  1. org ∈ conglomerates list → scope `repo`, reason `conglomerate`
     (regardless of R3);
  2. AI developer → scope `full`, reason `override` > `dev-list` >
     `top5:{n}` (in that precedence);
  3. else if any top-5 repo has the `ai` flag AND ≥ 1,000 stars → scope
     `repo`, reason `ai-flagship`;
  4. else out.
- **POP-9** Output row: `org (original casing), scope, why, top5_ai`. The
  `why` column is the admission reason only; slice groupings (§8.5) use
  `top5_ai`, never `why`.

### 4.4 Census-derived evidence and the fixed point

- **POP-10** Population evidence and the census depend on each other
  (branch-scan and census evidence are produced by scanning the current
  population). The system resolves this as a **bounded fixed-point loop**:
  up to 3 rounds of (enumerate strata → assemble manifest → collect →
  weights → recompute census evidence → rebuild population); if membership
  changes in a round, loop; if it fails to converge in 3 rounds the run
  aborts. The published population is the converged one.
- **POP-10a (why 3 rounds suffice)** Evidence is strictly per-org and the
  cell store only accumulates, so one org's membership change never
  alters another org's evidence: the membership DECISION settles in a
  single recomputation. The loop's extra rounds are not re-adjudication:
  - The round after an ADDITION does **collection completeness** work —
    the manifest is assembled before the rebuild, so an org admitted by
    a round's rebuild has not been collected that round; the next round
    backfills its cells so the published frame covers every member.
  - One rule is **non-monotone under that backfill**: R4's rate branch
    (`e/t ≥ 0.1%`). The absolute branch can only grow with more cells,
    but full collection grows the rate's denominator, so an org admitted
    on a partially-collected rate can dilute below threshold once fully
    collected and drop on the next rebuild.
  The longest possible chain is therefore: addition → backfill
  collection → rate-dilution drop → confirming round = 3 rounds. A drop
  triggers no new collection (census evidence is computed over the whole
  store, so a dropped org keeps its historical evidence — no
  oscillation), and no cross-org effect exists, so no fourth-round
  change is reachable; failing to converge in 3 can only mean
  nondeterministic collection or a monotonicity-breaking rule change,
  which is why the run aborts rather than publishing round 3.
- **POP-11** Census-derived org evidence: for every censused PR of every
  manifest repo, count it as evidence if any detection layer fires (union,
  DET-4); aggregate per org as `(evidence_prs, total_prs)`.

### 4.5 Repo-level population

- **POP-12 (full-org members)** contribute their repos passing the
  enumeration keep rule (COL-3), as recorded in the full-org repo list
  (EXT-14).
- **POP-13 (repo-scoped members)** contribute their AI-topic repos from
  strata enumeration (COL-5).

### 4.6 Repo manifest assembly and validation

- **POP-14** The canonical repo manifest = (full-org repos whose owner is a
  full-scope population org) ∪ (strata repos whose org is a repo-scope
  population org). Assembly MUST validate: every repo-scoped org has a
  completed-enumeration sentinel; every entry matches `owner/name` with
  `[\w.-]` characters; no repo from an org outside the population; every
  population org has an org-type row. Current run: 2,136 repos (2,142
  before the 2026-07-27 population refresh).
- **POP-15** The **collectable manifest** = manifest minus the documented
  inaccessible-repos list (71 repos at the pre-refresh run — deleted,
  privatized, or DMCA'd; each is a standing waiver, see COL-10).
  Unsearchable-but-reachable repos are NOT waivers: they are collected
  through the object API (COL-10b).

---

## 5. Collection

### 5.1 Universal durability rules

- **COL-1 (absence ≠ zero)** A failed external query is NEVER recorded as a
  zero or an empty result. Every retry budget exhausting turns the unit
  (org, repo, cell) into an explicit absence — skipped and visible — not
  data. Note the run-dependence consequence: which absences occur depends on
  transient API conditions (flag F-22).
- **COL-2 (validated, atomic, keyed storage)** Every stored cell is
  shape-validated before write (a parseable-JSON body of the wrong shape —
  e.g. a rate-limit error object — is a failure); writes are atomic
  (complete-or-absent); cache keys include every content-determining
  parameter (repo, resolved date range, and — for marker scans — a
  fingerprint hash of the entire marker set, so any marker change
  invalidates stale scan caches). Exception recorded as flag F-6: PR-count
  cells are keyed by period *token*, not resolved range.

### 5.2 Org marker scan (evidence input)

- **COL-3a** For each (org, period, tool): count = **max over the tool's
  search terms** of the commit-search total (EXT-1) — terms overlap on the
  same commits, so summing would double-count; max is the honest floor.
  Any term's count failing fails the whole cell.

### 5.3 Repo enumeration inside full-scope orgs

- **COL-3** Keep a repo iff, over the **admission window 2025-07-01 ..
  2026-06-30** (12 months — deliberately wider than the censused quarters):
  - `abs` branch: total marker-commit hits ≥ 5 (per-tool hits are
    max-over-terms; the total **sums across tools**), or
  - `rate` branch: hits ≥ 1 AND hits / (the repo's PR count in the window)
    ≥ 0.001.
- **COL-4** Enumeration walks full commit-search pagination per (org, term);
  if results saturate the 1,000-cap, the true total is fetched and a warning
  emitted, but the truncated tally is still used (flag F-7). A failed term
  enumeration skips the whole org (visible absence).

### 5.4 Strata enumeration (repo-scoped orgs)

- **COL-5** For each repo-scoped org: enumerate ALL public non-fork repos
  stars-descending (EXT-6); keep those with ≥ 1 topic in `AI_TOPICS`. No
  star floor. Completeness is strict: a missing pagination marker fails the
  org (never treated as "last page"); a hard ceiling of 100 pages (10,000
  repos) fails loudly if exceeded. Output rows `org, repo, stars` are
  terminated by a per-org `DONE` sentinel; resume re-enumerates any org
  without a sentinel.

### 5.5 PR-count denominators (precount)

- **COL-6** For every (collectable repo, period): the PR count from issue
  search (EXT-3), fetched either via batched aliased GraphQL search counts
  (20 per document) or singly. Only integer results are stored.

### 5.6 The PR census

- **COL-7 (completeness by construction)** For each (repo, period):
  - if precount ≤ 50: one full-range query;
  - else split the period into `k` contiguous integer-boundary date
    sub-windows covering it exactly once (no gaps/overlaps/inversions),
    where `k = max(10, ceil(total × 1.1 / 45))`, capped at one window per
    day. Each window cursor-paginates (EXT-4) up to the API's 1,000-node
    cap; pagination terminates ONLY on an explicit "no next page" — a
    missing/partial page marker fails the window (never cached). A window
    whose 50-PR pages fail server-side is retried at 5-PR pages.
- **COL-8 (reconciliation gate)** Collected count `n` vs precount `total`
  passes iff `n ≥ total × 0.98` OR `total − n ≤ 3` (drift allowance for
  PRs deleted between precount and census). On first failure: **self-heal**
  — delete the period's cells (sub-windows and full-range), wait 60s
  (brownouts are minutes-scale), re-pull once. On second failure the
  repo-period FAILS the run. The cached fast path applies the same
  allowance, so a brownout-poisoned cached empty falls through to
  self-heal. A `total = 0` denominator never stands on one observation
  (it passes both gate arms trivially): it is re-queried fresh, and only
  a confirmed 0 (cache-marked `confirmed`) can census as a complete
  empty repo-period — a nonzero recount replaces the cached value, an
  unconfirmable zero FAILS the cell. The confirmation is temporally
  independent: a zero observed within the last 60s (the brownout
  horizon, same as self-heal) is re-counted only after waiting out the
  remainder; an older cached zero re-counts immediately. (Flag F-8: the
  allowance tolerates up to 2% silent undercount.)
- **COL-9 (cell lifecycle)** Cells are immutable snapshots freezing event
  state at collection; nothing edits a cell in place. Late events enter
  only via re-collection: new month-shaped cells whose PRs supersede the
  same PRs in older quarter-shaped cells **PR-by-PR** at analysis time
  (§7.1). Old cells stay on disk serving un-revised months.
- **COL-10 (coverage gate)** Report generation refuses to run unless every
  (manifest repo × censused quarter) either has gap-free valid-cell
  coverage — the repo's parseable cells must union to the whole quarter
  with no gaps — or the repo is on the documented inaccessible list
  (counted as waived). Coverage numbers re-derive per run manifest
  (RPT-2); pre-refresh run: 8,568 repo-periods = 8,284 covered + 284
  waived (71 repos × 4 quarters).
- **COL-10b (unsearchable repos)** A public repo GitHub's search index
  refuses outright (`repo:X` answers a definitive HTTP 422 "cannot be
  searched") can never have a precount or a search-collected cell; it is
  collected via `repository.pullRequests` (`census_direct.py`), which
  bypasses the search index. The connection's own `totalCount` is the
  completeness denominator — the full history must arrive, verified page
  by page, or nothing is written — and quarters with no PRs get a
  VERIFIED empty cell. Only the definitive 422 selects this route; a
  transient failure still fails the repo-quarter. Such repos are
  COLLECTED, not waived (measured 2026-07-29: 8 population repos, 364
  in-window PRs recovered; they skew new and AI-tooling-heavy, so
  waiving them would bias AI rates down).

### 5.7 Branch-prefix scan (layer-C counts)

- **COL-11** For each (population org × all five quarters × five prefixes):
  the issue-search count of `org:{org} is:pr head:{prefix}
  created:{range}` — except repo-scoped orgs, whose cells are counted per
  in-scope repo (`repo:{r} ...`, summed; a cell with any failed per-repo
  count is skipped, never written partial) so their universe matches the
  census (R5). Q1-2024 is scanned deliberately as the built-in
  false-positive check (measured 0 across all orgs). Failed counts are
  skipped, never written as zero; completed triples are append-cached.

### 5.8 Monthly incremental updates

- **COL-12** Adding month N re-collects months N−2 and N−1 first (wipe
  their cells — any cell whose start date falls inside the month — plus
  their precounts; then precount + census for N−2, N−1, N over the
  collectable manifest). Rationale: N−1 for creation recency; N−2 because
  its last 8-week windows have only just closed — a month's fates are
  FINAL once it has been revised as N−2. The scheduled cadence executes
  the Q2-2026 finalization: the ~Aug 1 update finalizes May, the ~Sep 1
  update finalizes June.
- **COL-13** Month tokens outside the frozen quarters are persisted in an
  **incremental-month registry** consumed by analysis (so a later update
  cannot silently drop an earlier month). Population and classification
  metadata stay frozen between deliberate revisions. Each re-pull requires
  the manual AS_OF bump (FR-6).

### 5.9 Contributor weights

- **COL-14** For each manifest repo, from weekly contributor stats (EXT-8):
  weight = number of distinct logins with **≥ 5 commits in weeks whose
  start date falls within 2025-10-01 .. 2026-06-30** (inclusive;
  week-start bucketing means up to ±6 days of edge slop — flag F-19),
  excluding DET-R3 bot logins. Repos where GitHub never materializes stats
  are waived on a documented list and default to weight 1.0 downstream. On
  give-up the repo gets no row and the run fails (visible absence).

### 5.10 Branch-PR samples (layer-C precision input)

- **COL-15** For each (org, quarter) with a nonzero branch-scan count for a
  prefix: fetch **one page of the 50 most recently created** matching PRs
  (EXT-4 fields), storing the org-quarter's total count alongside as the
  population weight. NOT a random sample — a deterministic recency sample
  with documented within-quarter recency bias; no seed. Default periods
  Q4-2025..Q2-2026. Repo-scoped orgs are sampled over their **in-scope
  universe** (issue #8, 2026-07-28): the query enumerates their manifest
  repos as `repo:` qualifiers (chunked to the search-string length limit)
  so scoping applies BEFORE the 50-newest cap; scoped cells are tagged
  (`universe='scoped'`), legacy org-wide-drawn cells are re-drawn, and an
  org with no manifest repos has an explicitly empty universe (never an
  org-wide fallback).

---

## 6. Detection

Three independent layers, plus review classification. Source: `detect.py`
(single canonical home). All rules operate on the census record shape
(EXT-4).

### 6.1 Layer A — commit markers

- **DET-A1 (match domains)** Each tool defines up to three term sets:
  - *search terms*: commit-search query fragments — used ONLY by the
    discovery scans (COL-3a), never for per-PR classification;
  - *needles*: substrings matched against `message + identity` text;
  - *identity needles*: substrings matched ONLY against identity text
    (a message merely *mentioning* an identity is not evidence).

  For each of a PR's (≤12) commits, identity text = all commit-author
  emails + committer email + committer login, newline-joined. A tool
  matches the PR if any commit matches any of its needles (in
  message+identity) or identity needles (in identity). The result is the
  **set of matched tools** (layer A fires iff non-empty).
- **DET-A2 (the canonical marker set)** Six tools, one canonical set:

  | tool | needles (message+identity) | identity needles only | search terms |
  |---|---|---|---|
  | claude | `noreply@anthropic.com`, `Generated with [Claude Code]` | — | bare: `noreply@anthropic.com`, `"Generated with [Claude Code]"` |
  | cursor | `cursoragent@cursor.com`, `agent@cursor.com` | — | same, bare |
  | aider | `Co-authored-by: aider` | — | bare, quoted |
  | codex | `codex@openai.com`, `chatgpt-codex-connector` | — | `committer:chatgpt-codex-connector[bot]`, `author-email:codex@openai.com` |
  | openhands | — | `openhands@all-hands.dev`, `openhands-agent` | `author-email:openhands@all-hands.dev`, `committer:openhands-agent` |
  | agent (vetted homegrown) | — | `hermes-agent@` (prefix), `agent@hermes`, `agent@modal.com`, `agent@deepagents.dev`, `pragma-agent@modular.com`, `agent@qwenpaw.local`, `agent@example.com`, `bot@imbue.com` | `author-email:` forms of the same eight |

  The "agent" list is the hand-vetted product of a full-store
  committer-identity audit (2026-07-20); CI/release bots surfaced by the
  same audit (snyk-bot, renovate, xnnpack, airflow, …) are deliberately
  excluded. Flags F-25/F-26 record two suspicious members
  (`agent@example.com`, the open-ended `hermes-agent@` prefix).
- **DET-A3 (fingerprint)** Scan caches are keyed by a content hash of the
  entire marker set (tools + all three term lists, sorted), so any marker
  change invalidates them.

### 6.2 Layer B — agent PR authorship

- **DET-B1** Layer B fires iff the PR author is **App-typed** (DET-R1) and
  its login, with a trailing `[bot]` stripped, is one of:
  `copilot-swe-agent`, `devin-ai-integration`, `cursor`,
  `google-labs-jules`, `codegen-sh`, `amazon-q-developer`,
  `factory-droid`, `claude`. A User-typed account with the same login
  never triggers layer B.

### 6.3 Layer C — agent branch prefixes

- **DET-C1 (prefixes)** Head branch name starts with one of: `codex/`,
  `copilot/`, `cursor/`, `claude/`, `droid/` (droid = Factory Droid,
  added 2026-07-17 as a weak prefix). Weak prefixes (indeterminate
  provenance): `cursor`, `claude`, `droid`.
- **DET-C2 (CI-canary exclusion)** If the PR's commit list is non-empty and
  EVERY committer email ends with
  `github-actions[bot]@users.noreply.github.com`, layer C does NOT fire —
  a measured false-positive class (CI automation naming branches after the
  product; 18.4% of C-only `claude/` samples).
- **DET-C3 (provenance confirmation)** A prefix branch is
  provenance-confirmed iff any commit's committer email is
  `noreply@github.com` (GitHub web-flow) OR the head branch matches the
  tool's machine-generated slug pattern:

  | tool | slug regex |
  |---|---|
  | codex | `^codex/[a-z0-9][a-z0-9-]*$` |
  | copilot | `^copilot/[a-z0-9][a-z0-9-]*$` |
  | cursor | `^cursor/.+-[0-9a-f]{4}$` |
  | claude | `^claude/(issue-\d+\|[a-z]+-[a-z]+-[0-9a-f]{4,})` |
  | droid | `^droid/.+-20\d{6}$` |

  (Note: the web-flow committer is any web-UI/API commit and is evidence
  only *conditioned on* the agent-named branch; flag F-28 records that the
  strict arm is therefore not conservative against human web-UI commits.)
- **DET-C4 (two arms)** Default (headline/upper) arm: any prefix match not
  excluded by DET-C2 fires. **Strict (lower) arm**: weak prefixes
  additionally require DET-C3 confirmation. The headline series is
  reported with a standing two-sided bound between the arms (§8.9).
  Layer C is PR-level attribution only, never commit-level proof.
- **DET-C5 (measured precision, context)** Org-stratified C-only samples,
  FINAL under the completed scoped re-draw (issue #8; the re-drawn
  samples changed no figure — the read-time scope filter had already
  converged): codex/ 95%, copilot/ 98% confirmed; cursor/ 49%, claude/
  43% (CI-canary FP class 19.6% of C-only claude/); the remainder
  (cursor/ 51%, claude/ 38%) is indeterminate — the study's ONLY
  potential overcount (everything else is a floor).

### 6.4 AI involvement (the primary metric)

- **DET-4** `ai_involved` = layer A fired ∪ layer B fired ∪ layer C fired.
  An explicit lower bound on true AI involvement (squash-merge strips
  trailers; local CLI tools leave no public metadata).
- **DET-5 (disjoint decomposition)** Where layers are reported disjointly,
  precedence is **B > A > C**: an agent-authored PR counts as B even if it
  also carries markers; a marker PR counts as A even on an agent branch;
  C is the branch-only remainder. Union = A + B + C(disjoint).

### 6.5 Review classification

- **DET-V1 (taxonomy)** Every formal review object with an author is
  classified into exactly one of:
  1. **human-other**: User-typed (DET-R1), login not a user-typed bot
     (DET-R2), login ≠ PR author;
  2. **human-self**: same but login = PR author (tracked separately;
     currently consumed by no reported metric);
  3. **bot**: everything else (App-typed, or User-typed bot login) —
     EXCEPT a bot review whose login equals the PR author's (compared
     after stripping a trailing `[bot]` from both sides), which is
     dropped entirely: reviewer ≠ author applies to bots as to humans
     (issue #9, 2026-07-28 — coding agents post self-summaries as formal
     review objects on their own PRs; those are not review activity).
- **DET-V2 (event window)** A review counts iff submitted within the PR's
  w8 window (FR-7). Reviews without a submission timestamp are dropped
  (on records lacking a creation timestamp — legacy fixtures only — the
  fallback bound is CUTOFF + 56 days; flag F-24 notes the asymmetry).
- **DET-V3 (AI reviewers)** Among bot reviews, a review is an **AI review**
  iff the author login (trailing `[bot]` stripped) is in the curated
  allowlist: `gemini-code-assist`, `copilot-pull-request-reviewer`,
  `coderabbitai`, `greptile-apps`, `qodo-merge-pro`, `cursor`,
  `chatgpt-codex-connector`, `copilot-swe-agent`, `claude`. The list is
  extend-as-found and deliberately errs toward under-counting AI review
  (an unlisted AI product counts as other-bot, never as human).
  **Other-bot review** = any remaining bot review (CI/automation), kept as
  its own class so AI review is never conflated with CI noise. Both
  classes count only reviewer ≠ author (DET-V1 rule 3): three logins sit
  in both the agent-author and AI-reviewer lists (`cursor`, `claude`,
  `copilot-swe-agent`), and their self-reviews are excluded (F-16,
  fixed).
- **DET-V4 (substantive)** A review set is substantive iff any review has
  inline comments (> 0) or state `COMMENTED`/`CHANGES_REQUESTED` — more
  than a rubber-stamp APPROVED. (Computed over human-other reviews;
  currently consumed by no reported metric.)

### 6.6 Per-PR classification record

- **DET-6** Classifying a PR yields exactly these facts (source:
  `detect.classify_pr`):

  | fact | rule |
  |---|---|
  | `marker_tools` | DET-A1/A2 tool set |
  | `agent_author` | DET-B1 login or none |
  | `branch_tool` | DET-C1..C4, default arm |
  | `merged` | has creation time AND merge time within w8 (FR-7) |
  | `merged_ever` | has a merge time at all (no window — secondary) |
  | `rejected` | never merged AND close time within w8 |
  | `w8_mature` | FR-8 |
  | `self_merged` | undefined unless `merged` and the record carries the merger; then merger login = author login (and author non-null) |
  | `insider` | FR-11 |
  | `human_reviewed` | ≥ 1 human-other review (DET-V1/V2) |
  | `substantive_review` | DET-V4 over human-other reviews |
  | `ai_reviewed` | ≥ 1 AI review by a bot other than the PR author (DET-V3) |
  | `other_bot_reviewed` | ≥ 1 non-AI bot review by a bot other than the PR author |
  | `ai_involved` | DET-4 |

---

## 7. Aggregation

### 7.1 Loading, grouping, dedup

- **AGG-1 (dedup by PR number)** Within a (repo, period), PRs from
  overlapping cell generations (full-quarter + sub-window, or quarter +
  re-collected month) are deduplicated by PR number. The **richer** record
  wins — one carrying the head-branch field beats one lacking it; at equal
  richness the record from the **more recently collected** cell wins.
  ⚠ Portability (flag F-11): the original orders cells by file
  modification time, which does not survive copying the store. A
  reimplementation MUST express freshness as a property of the data (e.g.
  a collection stamp per cell) and, for validation against the original
  store, reproduce its mtime ordering.
- **AGG-2 (period mapping)** Quarter granularity: a cell's PRs belong to
  the quarter containing the cell's start date (frozen quarters take
  precedence over any same-token month). Month granularity: PRs re-bucket
  by creation month, restricted to months inside censused quarters plus
  registered incremental months.

### 7.2 Per-repo rates

- **AGG-3 (the 14 census metrics)** Per PR (via DET-6):
  `ai_code` (= layer A only), `ai_involved`, `merged`, `rejected_w8`,
  `limbo_w8` (mature, neither merged nor rejected), `human_review`,
  `ai_review`, `other_bot_review`, `no_review` (no formal review of any
  kind), `insider`, `self_merged`, and merged-conditioned `m_hum_rev`,
  `m_ai_rev`, `m_no_rev` (defined only on mature merged PRs; `m_no_rev`
  = no review of any class). Maturity gating: all fate and review columns
  are **undefined** on immature PRs; `self_merged` is additionally
  undefined when the record lacks the merger; `ai_code`, `ai_involved`,
  `insider` are always defined.
- **AGG-4 (None-skip)** A repo-period's rate for a metric = defined values
  summed / count of defined values; a metric with no defined values is
  undefined for that repo-period (skipped, never zeroed).
- **AGG-5 (repo floor)** A repo-period qualifies iff it has ≥ 5 PRs
  (quarter) / ≥ 2 PRs (month) — comparable thresholds per unit time.

### 7.3 Weighting and uncertainty

- **AGG-6 (weights)** Two aggregation rows per period: equal-weight
  (weight 1 per repo) and **contributor-weight** (primary; weight =
  COL-14, floored at 1.0; repos missing from the weights file default to
  1.0 with a per-period warning). Answers "the typical currently-active
  AI-org developer's PR flow". Pooled (per-PR) shares are a secondary,
  labeled view.
- **AGG-7 (weighted mean)** Σ rate·weight / Σ weight over qualifying
  repos whose rate is defined.
- **AGG-8 (bootstrap CI)** 95% interval by resampling **repos**: from the
  list of (rate, weight) pairs, draw with replacement to the original
  count, recompute the weighted mean; repeat N times; report the
  **linear-interpolated 2.5th and 97.5th percentiles** (the numpy/R
  type-7 method) of the sorted resampled means. Undefined (NaN) when
  fewer than 2 pairs. Rationale: the census is complete, so the CI
  answers the superpopulation question (dependence on the particular
  repos), not sampling error. Draw counts as implemented: **2,000** for
  the headline table, paper figures and productivity tables; **500** for
  slice tables; **1,000** for the balanced panel, the botcheck table,
  and the monthly-update trend print (flag F-12 — the docs' blanket
  "2,000 draws" was inaccurate). Seeding (per-cell, 2026-07-28): every
  reported CI cell has a unique key naming its table/period/metric; the
  cell's RNG is seeded with the first 8 bytes (big-endian integer) of
  SHA-256(`"20260630|{key}"`), giving one independent stream per cell —
  reproducible in isolation, independent of call order. Reusing a key
  across two cells would share draws and is forbidden.

---

## 8. The generated report and its 21 sections

### 8.1 Report assembly contract

- **RPT-1** The canonical output is one generated report per granularity
  (quarterly primary; a monthly twin runs the same sections, tagging
  inherently-quarterly ones). The report is built **all-or-nothing**: each
  section is an independent invocation whose output is embedded verbatim;
  any section failure discards the partial build — a mid-run failure must
  never leave a truncated report in place.
- **RPT-2** Report generation is gated (COL-10) and accompanied by a
  **census manifest**: SHA-256 prefixes (16 hex chars) of the repo
  manifest and population table, the repo count, and the coverage
  numbers (covered / waived / total repo-periods).
- **RPT-3** Every table where the Q1-2024 column appears carries the
  caption: Q1-2024 is a **detector-validity check and review-practice
  baseline, not an AI-usage estimate** — none of the three detectable
  channels existed yet, so 0% is by construction (autocomplete-era
  assistance was widespread and invisible).
- **RPT-4** All rates are floors except the weak-prefix indeterminates,
  which get the standing two-sided bound section (§8.9).

### 8.2 The sections

Numbering below = report order. "CW" = contributor-weighted (AGG-6..8).

**§8.2.1 Contributor-weighted metrics** — the 14 census metrics (AGG-3)
per period × {equal-weight, contrib-weight}, each as mean [95% CI], repo
floor AGG-5, over the full repo manifest. (Profile: all PRs; bot-authored
PRs are included and classified via layer B.)

**§8.2.2 Figure 2 — traceable AI usage** (profile `all`). Per
(repo, period) accumulate: PR count, AI-involved PR count, merged (w8,
mature) PR count, AI-involved merged count, and the same four in capped
LOC. Four CW series with CIs: AI share of submitted PRs (floor: ≥ 5 PRs),
of merged PRs (floor: ≥ 5 merged), of submitted LOC (LOC > 0), of merged
LOC (≥ 5 merged).

**§8.2.3 Figure 3 — merged LOC per core contributor** (profile `author`
for output; insider status from an unfiltered pass). Per (repo, period):
core = insider authors; requires ≥ 2 core authors; value = Σ merged-w8
capped LOC by core authors / |core| / 1,000 (and the submitted analogue).
CW mean with CI, plus the multiple vs the Q1-2024 baseline mean
(published ×2.96 by Q2-2026).

**§8.2.4 Layered decomposition** (profile `all`, pooled/unweighted,
per-PR-exact). Per period over all census PRs: disjoint shares B, A,
C-only (DET-5) and the union. This is the exact decomposition — no
sampling, no weighting. Fails loudly on an empty store.

**§8.2.5–8.2.10 Slices** (profile `all`; source: `studies.slices`).
Org slices — every org belongs to (a) one adoption/scope group:
`repo-scoped` (scope = repo), `AI-majority` (top5_ai ≥ 3 OR admission
reason dev-list/override), else `AI-heavy`; and (b) one org type
(public/private/community) from the org-type table. Per-repo rates with
floor 5/2 in each metric's own denominator:

- **involvement** (§8.2.5): `ai_involved` over ALL PRs (no maturity gate,
  no fleet exclusion, no AI-contrast gate — flag F-14 notes this is a
  third involvement variant), plus human-review/AI-review/merged rates
  over mature PRs; CW means per slice with 500-draw CIs.
- **self-merge** (§8.2.6): self-merged share over merged-with-known-merger;
  AI share of self-merged vs other-merged; human-review rate of
  self-merged AI vs non-AI PRs.
- **balanced panel** (§8.2.7): panel = repos qualifying in EVERY reported
  period; CW `ai_involved` on the panel vs the cross-section
  (adoption-vs-composition sensitivity; published Q2-2026: 15.6 panel vs
  16.9 cross-section); 1,000-draw CIs.
- **reviewer profile** (§8.2.8): 2×2 of merged PRs per slice — human-only
  / AI-only / both / neither (computed when ≥ floor merged PRs).
- **two-sided bound** (§8.2.9): the headline `ai_involved` CW series
  recomputed with layer C in default arm (upper, = the reported headline)
  vs strict arm (lower, DET-C4); the delta in pp is the bound. No CIs.
  Published width: ≤ 0.05pp CW in Q2-2026 (0.11pp pooled), ≤ 0.01pp
  earlier.
- **botcheck** (§8.2.10, added 2026-07-28): involvement sensitivity to
  bot-authored PRs in the denominator — three `ai_involved` variants on
  ONE shared repo set (all three defined per repo): `published` (profile
  `all`, as reported), `no-dilution` (non-AI bot-authored PRs dropped,
  layer-B agents kept — the clean denominator-dilution counterfactual),
  `no-bots` (profile `pr`: all bot authors dropped including agents,
  which removes AI signal too). CW means with 1,000-draw CIs, plus the
  CW shares of non-AI-bot authorship and all-bot authorship, and the
  published rate over every qualifying repo for comparison.

**§8.2.11–8.2.17 Productivity family** (source: `studies.productivity`).
Shared substrate: per (repo, period, author-login) — profile `author` —
accumulate PR count, merged count (w8 but NOT maturity-gated — a
documented one-sided deflation of trailing quarters), merged capped LOC,
AI-involved PR count, submitted capped LOC.

- **decomposition** (§8.2.11): balanced repo panel (repos with authors in
  all 4 quarters, no PR floor); per period: PRs, repo-author pairs
  (labeled "authors" — flag F-15), PRs per pair, merged per pair, merged
  kLOC per pair.
- **persistent authors** (§8.2.12): same (repo, login) present in Q1-2024
  AND Q2-2026; means/medians of PRs and merges per quarter; then split by
  2026 AI usage (any AI-involved PR), with merged-count and merged-kLOC
  ratios 2026/2024 (selection caveat printed).
- **core LOC** (§8.2.13): the Figure 3 series (independent second
  implementation — flag F-31).
- **AI-split** (§8.2.14): among repos with ≥ 2 core (insider) authors,
  three CW author-mean series: kLOC of authors with zero AI-involved PRs
  ("non-adopters", published flat ~6); AI-users' AI-PR kLOC; AI-users'
  nonAI-PR kLOC (the undetected-usage signature).
- **adoption cohorts** (§8.2.15, Figure A1): author cohorts assigned once
  from monthly history — **fleet first**: ≥ 300 merged PRs in any single
  quarter; else by first month with an AI-involved PR: ≤ 2026-02 `early`,
  ≤ 2026-04 `medium`, later `late`, none `never`. Cohort table restricted
  to insiders; the fleet login list is computed over all `author`-profile
  logins in the same pass that assigns cohorts — no persisted cache
  (memoized per process), so every consumer (Figures 3/6–8, fates,
  review_action) shares one fleet definition derived from the current
  cells. Per (quarter, cohort) over quarter-active members:
  pooled author-level means of AI / nonAI / total merged kLOC, CI over
  authors, plus median.
- **approval channels** (§8.2.16): each mature merged PR gets exactly one
  channel by precedence: human-reviewed → `humanRev`; else any bot review
  → `botOnly`; else self-merged → `selfUnrev`; else known-other-merger →
  `otherUnrev`; else `unknown` (in totals but unprinted — flag F-32).
  Shares of merged capped LOC per channel (profile `author`).
- **review mix** (§8.2.17, Figure 6): same channels; slices ins/ext (by
  insider, profile `author`) or AI/nonAI (profile `all` +
  `ai_contrast_eligible`, fleet excluded or split out); per (period,
  slice): channel shares of merged PR count and of merged capped LOC.

**§8.2.18 Attention per line** (source: `studies.attention`). Primary
attention measure = **human comments per merged kLOC** (frozen
convention): comments = Σ inline-comment counts over human-other reviews
only (bot comments can never share the numerator). Two tables:

- main: profile `pr` (no fleet exclusion — flag F-33), cohorts
  all/insider/external over mature merged human-reviewed PRs with
  timestamps and LOC; columns: PRs, kLOC, comments/kLOC, and
  merge-window hours per kLOC (Σ hours creation→merge / Σ kLOC —
  corroborating, never leading). Then the same by fixed size bands on
  capped LOC (≤10, 11–100, 101–1k, >1k) to separate within-size thinning
  from composition.
- by-AI (Figure 7): profile `all` + `ai_contrast_eligible`, fleet
  excluded; AI vs nonAI slices; comments/kLOC and
  first-human-review-latency hours per kLOC (both ratios of totals).

**§8.2.19 PR fates at matched horizons** (source: `studies.fates`).
Profile `all` + `ai_contrast_eligible`, fleet excluded. At horizon h ∈
{8, 26} weeks (h×7 days, maturity per horizon): merged / rejected /
limbo shares per (period, cohort) for cohorts all, insider, external
(non-bot-authored only), AI, nonAI. Rows with n < 20 are listed as
suppressed, never silently dropped; the bot-authored residual (all −
ins − ext) is footnoted.

**§8.2.20 Responsiveness to human asks** (Figure 8) — see §9.1.

**§8.2.21 Adoption event study** (source: `studies.event_study`).
Profile `author`, month granularity. Window = the 9 months
2025-10..2026-06; baseline = 2024-01..03. Align authors who: were insider
in ≥ 1 observed month, had NO AI-involved PR in the baseline, and whose
first AI month within the window has index > 0. Event time e ∈ −4..+4
around each author's first-AI month t0; value = that author's merged kLOC
(outcome A) or submitted kLOC (outcome B) in month t0+e, with inactive
months = 0. Cohorts: all alignable; balanced (2 ≤ t0-index ≤ 6, so
offsets −2..+2 are all observed); mature (balanced ∩ offsets inside
w8-mature months). Rows print only at ≥ 30 observations: authors, mean,
median. Descriptive only — no regression, no CIs. (The 21-month
observation gap 2024-04..2025-09 means t0 is first *observed* AI month —
flag F-34.)

### 8.3 Figures

Canonical figure table (resolves the historical numbering collisions —
flag F-35; "series" defines the data contract, styling is free):

| file | content |
|---|---|
| `fig2_ai_usage.png` | §8.2.2's four CW series with CI bands, broken x-axis (Q1-2024 \| Q4-2025..Q2-2026) |
| `fig3_core_loc.png` | §8.2.3 submitted + merged series with baseline-multiple annotations; Q2 merged shaded provisional |
| `fig_a1_adoption_cohorts.png` | §8.2.15: per cohort (fleet, early, medium, late, never), six monthly series (submitted/merged × total/nonAI/AI kLOC per author) |
| `fig_a2_adoption_event.png` | event-time panels for early/medium cohorts, values net of the contemporaneous never-cohort mean; immature offsets shaded with their immature share |
| `figure_2_comp_audits.png` | per-adoption-month balanced cohorts (t0 = 2025-12..2026-04): six raw kLOC series in event time −2..+2 |
| `figure_3_comp_audits.png` | human-review coverage of merged PRs and comments/kLOC for ai/nonai/fleet slices |
| `fig5_fleet_vs_nonadopters.png` | monthly six-series for the fleet cohort vs totals for never |
| `fig6_review_mix.png`, `fig6_review_mix_by_ai.png` | §8.2.17 channel shares (PR and LOC panels), ins/ext and ai/nonai variants |
| `fig7_attention_by_ai.png` | §8.2.18 by-AI: comments/kLOC and first-review h/kLOC |
| `fig8_responsiveness_by_ai.png` | §9.1: responded% (EQ, n ≥ 20) and post-ask LOC share (PPS/HT, n ≥ 20) for CLEAN+AI vs CLEAN+nonAI |

Shared figure conventions that carry meaning: Q1-2024 is plotted
disjointly from the window (broken axis); AI-slice values are suppressed
at Q1-2024; provisional (w8-immature) spans are shaded; zero-denominator
cells are gaps, not zeros.

---

## 9. Sampled and auxiliary studies

### 9.1 Responsiveness to human asks (report §19, Figure 8)

The one analysis with real survey-sampling machinery. Source:
`studies.review_action`.

- **STU-R1 (frame)** Eligible PRs: profile `all` + `ai_contrast_eligible`,
  w8-mature, merged (w8), human-reviewed, with a first human review
  timestamp and LOC > 0. Anchors: *first human review* = earliest
  human-other review; *first human ask* = earliest human-other review
  with state CHANGES_REQUESTED or ≥ 1 inline comment (a zero-comment
  APPROVED is not an ask).
- **STU-R2 (two designs, one frame)** Per censused quarter, from the
  sorted eligible list (by repo, number, LOC):
  - **PPS-by-LOC**: 1,200 draws with replacement, probability ∝ capped
    LOC, seeded `"{20260630}:{period}"`; distinct selections retained.
    Estimand: post-ask LOC share, as the ratio of Horvitz–Thompson
    totals with weight 1/π, π = 1 − (1 − loc/W)^1200 (W = the
    period-frame's total capped LOC).
  - **Equal-probability**: min(1,200, N) distinct PRs uniformly without
    replacement, seeded `"{20260630}:eq:{period}"`. Estimand: responded%
    as the plain unweighted share. (History: PPS-only estimation let
    tiny-LOC PRs dominate small lanes.)
- **STU-R3 (integrity)** Each design has a manifest with a **frame
  fingerprint** = hash of (AS_OF, CUTOFF, 1,200, seed, the sorted
  eligible (period, repo, number, LOC) tuples, + a design tag for non-PPS).
  A manifest is reusable only if the fingerprint matches AND its stored
  selection equals a fresh deterministic draw. Only selection identity is
  persisted; descriptive fields are rebound from the current census at
  use time.
- **STU-R4 (hydration & completeness)** Selected PRs are hydrated with
  full commit lists (100/page, paginated to a clean terminal page —
  explicit "no next page" plus an integer total; anything less defers,
  never checkpoints). Records store retrieved count AND the API-claimed
  count. Records where retrieved < claimed hit GitHub's hard 250-commit
  cap (0.3% of records): they are analyzed against the LOC of the
  retrieved commits (numerator and denominator from the same commits) —
  neither excluded nor rescaled.
- **STU-R5 (nonresponse)** A selected PR may be tombstoned as documented
  nonresponse ONLY after a dedicated single-PR confirmation whose every
  error is NOT_FOUND; a null in a batch response defers to the next pull
  (the 2026-07-25 incident: 1,345 live PRs mass-tombstoned from
  misread batch nulls). Tombstones are excluded from analysis with
  weights unchanged, reported, and retried on every repair. Publication
  is refused when nonresponse > 2% once ≥ 20 tombstones exist.
- **STU-R6 (the action measure)** For a hydrated record, walk its commits:
  total LOC = Σ commit additions+deletions; a commit attributes to the
  author iff ≥ 1 commit-author login matches the PR author (with `[bot]`
  normalized off both sides) AND the committer is not a *foreign* bot
  (committer login/email containing `[bot]` or ending `-bot`, other than
  the PR's own author — the PR's own bot responding counts). Post-anchor
  LOC = Σ over attributing commits with commit timestamp strictly after
  the anchor. Both are capped at 20,000; the total is floored at the
  census PR LOC except for 250-cap-truncated records (STU-R4). Caveat:
  commit timestamps are rewritten by rebase/amend (drifts late — inflates
  attribution).
- **STU-R7 (lanes and output)** Each sampled PR contributes to lanes:
  `all-cause` (anchor = first review, everyone); and if an ask exists:
  `CLEAN` (no AI-reviewer activity on the PR) or `mixed`, plus
  `CLEAN+AI`/`CLEAN+nonAI` (and mixed±AI, accumulated but unprinted —
  flag F-36) by AI involvement. Everything is computed twice: all
  authors, and with fleet operators excluded (the published Figure 8 uses
  the no-fleet variant). Printed per (period, lane), each gated
  independently at n ≥ 20 in its own design: responded% (EQ) and
  post-ask LOC share (PPS/HT). The identified estimate is the CLEAN
  lane; mixed is descriptive (interleaved human/AI comments are causally
  ambiguous).

### 9.2 Layer-C precision (feeds DET-C5; not a report section)

- **STU-P1** Over the branch-PR samples (COL-15), keep C-only PRs (no
  marker, no agent author); repo-scoped orgs' cells are filtered to their
  in-scope repos at read time (R5) — org-wide-drawn samples may carry
  out-of-scope PRs. Classify each into exactly one of, in order:
  `ci_committed` (DET-C2 condition), `web_flow` (any `noreply@github.com`
  committer), `machine_slug` (DET-C3 regex), `indeterminate`. Report the
  four shares per prefix; confirmed = web_flow ∪ machine_slug.

### 9.3 LOC-hygiene sensitivity (methodology defense; not a report section)

- **STU-H1** On an LOC-weighted sample of merged PRs with per-file paths
  (~950/quarter), measure the generated-content share of merged LOC
  (lockfiles, vendor/dist/third_party, minified, protobuf, snapshots,
  svg, notebooks). Published: 18.3% (Q1-2024) → 8.5% → 11.2% → 17.1%
  (Q2-2026) — endpoint below baseline; volume growth and attention
  decline survive exclusion (×4.2 vs ×4.1; −56% vs −57%).

### 9.4 Auxiliary behavioral studies (not in the report — UNVALIDATED;
interim working log retired 2026-07-27; re-derive on the final population
before citing)

These three bypass the study frame: they read census cells directly with
NO population filter, NO eligibility profile, and use merged-ever rather
than merged-w8 (flag F-37). A reimplementation targeting the published
report does not need them; they are specified for completeness.

- **STU-X1 accountability**: seeded uniform sample (250/period, seed 13,
  global-RNG seeding — flag F-38) of non-bot-authored merged-ever PRs;
  hydrate conversation-comment authors; among PRs with known merger and
  w8 merge, lanes self-merged vs other-merged (≥ 10 rows): share, layer-A
  rate, human-review rate, AI-review rate, and "one-person
  accountability" = self-merged with no other-human review AND no
  other-human comment (structurally zero in the other-merged lane — flag
  F-39).
- **STU-X2 review modes**: over merged-ever PRs of non-bot authors with
  ≥ 1 commit, an AI-commit = message+author-emails matching layer-A
  *needles only* (misses committer-identity tools — flag F-40).
  Interleaving: shares of all-AI, mixed, and human-fixup-after-AI
  (first non-AI commit after an AI commit whose message contains a
  fix-word: fix, clean, tweak, address, correct, adjust, polish, revert,
  typo, review). Session residue: in multi-commit all-AI PRs, classify
  follow-up commit messages by first match of external-review-response >
  author-direction > mechanical > plain.
- **STU-X3 corpus**: seeded qualitative draws — unreviewed-large (merged
  w8, uncapped LOC > 100, no human review; n=130, seed 7) and all-AI
  session PRs — dumped as flagged markdown for hand reading.

---

## 10. Validation protocol

### 10.1 Suggested order

1. **Population** (pure function of committed inputs): rebuild from
   §3.5/§3.6 inputs + §4 rules; compare membership, scope, `why`,
   `top5_ai` line-by-line against the committed population table.
2. **Manifest**: rebuild §4.6 from the same inputs; compare the 2,136
   repos and the manifest hashes.
3. **Classification** (shared census store): run DET-6 over every stored
   PR; compare per-PR facts, then the pooled layered decomposition
   (§8.2.4) — it is exact and weighting-free, so it isolates detection
   from aggregation.
4. **Rates & weighting**: AGG-3..8 per repo-period, then the §8.2.1 table
   point estimates.
5. **Studies**: §8.2.2 onward; for §9.1 first reproduce the two sample
   memberships exactly (seeded draws over the reconstructed frame — the
   manifest fingerprint machinery validates this), then the estimates.
6. **Collection** (optional, live): re-collect a repo sample and
   reconcile within COL-8 allowances.

### 10.2 What may legitimately differ

Live GitHub state (deleted/privatized repos, force-pushes, late events on
immature PRs), CI interval endpoints (VAL-2), warning text/formatting,
and anything Appendix A marks as environment-dependent (F-11, F-22,
F-30).

### 10.3 Validation anchors (published values, current artifacts)

Contributor-weighted unless noted; from the regenerated results artifact.
⚠ TIMING (2026-07-28): these anchors were generated on the pre-refresh
population (229 orgs / 2,142 repos) with the pre-fix bootstrap and fleet
cache. The population files now say 228 / 2,136 (issue #6), and the
botcheck section, per-cell CI streams, computed fleet set, and the bot
self-review exclusion (issue #9, ≤ 0.04pp on ai_review) land in the
NEXT full regeneration — re-pin this table from the regenerated artifacts
then. Point estimates are expected to move imperceptibly (sony's repos
were a ~0.3% sliver); CIs will shift within their displayed precision.

| quantity | Q1-2024 | Q4-2025 | Q1-2026 | Q2-2026 |
|---|---|---|---|---|
| ai_involved (CW, % of PRs) | 0.0 | 3.0 [2.4,3.7] | 10.3 [9.0,11.7] | 16.9 [14.9,18.7] |
| ai_code (layer A only) | 0.0 | 2.1 | 8.7 | 13.8 |
| qualifying repos | 465 | 825 | 1008 | 1154 |
| layered union (pooled, %) | 0.00 (72,290 PRs) | — | — | 17.11 (288,236 PRs): A 13.20 + B 0.43 + C 3.48 |
| merged kLOC / core author | 6.45 | 10.04 | 10.71 | 19.08 (×2.96) |
| human comments / merged kLOC | 3.98 | — | — | 1.88 (insiders 3.52 → 1.37) |
| fates w8: merged% (all) | 75.5 | — | — | 54.5 (ins 77.8, ext 44.7) |
| responsiveness CLEAN lane responded% | 79.7 | 80.9 | 79.8 | 80.8 |

Cross-checks: balanced-panel Q2-2026 15.6 [13.4,17.9]; two-sided bound
Q2-2026 16.85 vs 16.74 pooled (0.11pp; ≤ 0.05pp CW); AI share of
submitted LOC 22.4% / merged LOC 17.0%; fleet cohort ~42 logins (now
computed per run, no file — §8.2.15); layer-C precision per DET-C5
(final); coverage 8,284/8,568 + 284 waived (pre-refresh manifest;
the 2026-07-30 regeneration re-derives it — 364 PRs from 8
unsearchable repos now collected via COL-10b, FunAudioLLM excluded
per F-51).

---

## Appendix A — Flagged issues

Discovered while writing this spec (2026-07-26 review of the full
codebase and docs). "Spec follows code" = the behavior is normative above
and a reimplementation must copy it to reproduce published numbers.

### A.1 Reproducibility gaps (each now covered by a spec rule)

- **F-1** Four population inputs (`ai_scan`, `recheck_scan`, `org_scale`,
  `top5_topics`) and the full-org repo list have **no generating code in
  the repo**. RESOLVED at spec level 2026-07-27: §3.6 now specifies both
  the interfaces and regeneration procedures, and EXT-15 makes the mode
  choice explicit — replay the committed snapshots for validation (drift
  cannot enter), re-scan only as a deliberate revision (METHODS §1 holds
  the decision rules, §3.6 the measurement inputs they consume).
  Regenerating the code for these scans in-repo remains desirable.
- **F-11** Cell freshness (AGG-1 tie-break) is keyed on file
  **modification time**, which no copy/checkout preserves. The spec makes
  the portable rule normative (AGG-1: freshness = collection recency,
  recorded as data); validation against the original store must replay
  its mtime order.
- **F-30** All bootstrap CIs in one process shared a single seeded RNG,
  so intervals depended on the **call order of the whole program run**.
  Point estimates were unaffected. **RESOLVED 2026-07-28** (merged from
  `fix/bootstrap-ci-independence`): every CI cell now draws from its own
  key-derived stream with interpolated percentiles (AGG-8); VAL-2
  updated — CIs are per-cell reproducible, with only the RNG algorithm
  itself (Mersenne Twister) remaining implementation-bound. Within-cell
  pair order is still part of the contract (frame iteration order).
- **F-22** Retry give-up thresholds convert transient API conditions into
  permanent absences (orgs skipped by enumeration, repos without weights),
  so two from-scratch collections can produce slightly different
  populations/manifests. The committed artifacts are the reference.
- **F-27** AS_OF (FR-6) is a hand-maintained constant with no cross-check
  against actual collection dates. A forgotten bump silently withholds
  mature PRs; a premature bump admits immature ones.
- **F-29** The persisted fleet-operator list is written on first use and
  then trusted unconditionally — no fingerprint ties it to the frame,
  AS_OF, or marker set (unlike the responsiveness manifests). A stale
  list silently mis-slices Figure 3's fleet series, Figures 6–8, fates,
  and review_action, and can disagree with the adoption-cohort path,
  which recomputes fleet fresh — two definitions in one codebase.
  (= F-47) RESOLVED 2026-07-27 (issue #10): cache dropped and the file
  deleted from git; `fleet_logins()` now delegates to the
  `_author_months_and_cohorts` pass (memoized per process), so both
  paths share one definition. §8.2.15 updated.

### A.2 Doc/code contradictions (docs corrected 2026-07-26 where objective)

- **F-5** METHODS §1 said R4 maxima "avoid double-counting one PR across
  sources", but within two sources the code **sums** (recheck probes;
  branch-scan rows across all quarters × prefixes — Q1-2024 included), so
  one PR can count several times toward the ≥ 5 evidence threshold.
  **Adjudicated a bug 2026-07-27 — issue #6** (no PR may count more than
  once). RESOLVED 2026-07-28: recheck takes the max probe; branch cells
  are keyed and Q1-2024 excluded. POP-6 re-specified; METHODS §1
  re-tightened. Measured impact: −sony (probe-sum 9 vs distinct 4),
  no additions.
- **F-12** "2,000 bootstrap draws" was stated categorically; actual draw
  counts are 2,000 / 1,000 / 500 by table (AGG-8). Docs updated.
- Corrected as stale in docs: 19 → 20 report sections (21 since the
  2026-07-28 botcheck addition, §8.2.10); "31 repo-periods
  (0.4%) inaccessible" → 284 waived repo-periods, 71 repos (3.3%);
  monthly update's month-token plumbing described as an `analyze
  --periods` pass when it is a persisted registry; ×2.66 → ×2.96 core-LOC
  multiple; nonexistent figure names; four- vs five-list candidate
  descriptions; the all-time weights file cited where the window file is
  primary.
- **F-48** METHODS claimed the `author-email:` co-author undercount is
  "~10–16×"; the underlying memo's measurements are ~3× globally and
  total misses (0 vs 251/799) org-scoped. RESOLVED 2026-07-27: METHODS
  §2 now states the memo's actual numbers.
- **F-49** The curated-orgs count is stated three ways (file header "14",
  18 data rows, prose "~33"). Membership, not the count, is normative
  (POP-1).

### A.3 Cross-module inconsistencies (spec follows code; candidates for cleanup)

- **F-14** Three coexisting `ai_involved` denominators are printed as "the
  primary metric" in adjacent sections: §8.2.1/§8.2.5 (all PRs incl.
  immature, no fleet/contrast gates), §8.2.2 (floor-5 repos), §8.2.4
  (pooled). Real, labeled differences — but easy to misread as one number.
- **F-16** `cursor`, `claude`, `copilot-swe-agent` are both agent authors
  (DET-B1) and AI reviewers (DET-V3). Reviewer ≠ author was enforced for
  humans but not for bots, so an agent's formal review on its OWN PR
  counted as AI review — moving the PR out of the responsiveness CLEAN
  lane and into `botOnly`-channel accounting. **RESOLVED 2026-07-28
  (issue #9, PR #16)**: bot reviews by the PR's own author (logins
  compared after `[bot]` normalization) are dropped, mirroring
  human-self; DET-V1/V3 and DET-6 updated. Measured impact on mature
  PRs: `ai_reviewed` flips on 122 (74/36/12 across Q4-2025..Q2-2026;
  116 copilot-swe-agent), weighted ai_review series moves ≤ 0.04pp;
  `other_bot_reviewed` flips on 385.
- **F-17** The three bot heuristics (§2.5) disagree: contributor weights
  count user-typed bots (e.g. `*-agent` accounts, `qwen-code-ci-bot`) as
  core human contributors while every metric they weight excludes them.
- **F-18** The responsiveness commit walk uses a fourth, weaker bot rule
  (`[bot]` substring or `-bot` suffix): a `foo-ci`/`foo_agent` committer
  is a bot for review classification but a human there.
- **F-23** Two contributor-weight loaders exist (different default paths,
  column conventions, and fallbacks); the report's section 1 and the
  slice/productivity tables can silently weight by different vectors if
  invoked outside the canonical driver. Related **F-42**: one loader's
  default weights path does not exist, in which case output labeled
  contributor-weighted is silently equal-weighted (the canonical driver
  always passes the real file).
- **F-41** The headline metrics table applies the population filter only
  when given a repo list; every frame-based study applies it always. The
  canonical driver passes the manifest, but a bare invocation reports on
  whatever is in the store.
- **F-31** Figure 3 has two independent implementations (§8.2.3 and
  §8.2.13) that must agree; only one carries CIs.
- **F-13** Q3-2025 leaks: the population-convergence evidence pass counts
  Q3-2025 cells, though the coverage gate skips that quarter; and
  quarter-granularity frames built without an explicit period list would
  admit stray Q3-2025 cells into the layered/slice tables if any were
  present in the store.
- **F-40** The auxiliary review-modes/corpus "AI commit" test matches
  needles only (message + author emails): committer-identity tools
  (openhands, the vetted agent list) are invisible there, so their
  "all-AI" populations are not layer-A populations.
- **F-37** The three §9.4 studies bypass population filter, eligibility,
  and w8 fates entirely (merged-ever). Documented as
  working-log-only; do not compare their numbers to report numbers.

### A.4 Latent bugs (would bite under other inputs; currently benign or rare)

- **F-9** A precount of 0 passes the census gate trivially — a browned-out
  zero is indistinguishable from a real zero and caches a "complete"
  empty cell (the self-heal path only triggers on nonzero deficits).
  **Logged as issue #7.** RESOLVED 2026-07-28: a 0 precount is re-queried
  fresh — after waiting out the 60s brownout horizon when the zero was
  observed within it, so both samples cannot share one brownout; only a
  confirmed 0 censuses as a complete empty, an unconfirmable zero fails
  the cell. COL-8 updated.
- **F-24** w8 arithmetic accepts events timestamped before creation
  (negative day-diffs pass `< 56`); and reviews lacking a submission
  timestamp are dropped on normal records but kept on records lacking a
  creation timestamp.
- **F-43** The bootstrap percentile used raw index ⌊0.975·N⌋ (= 1,950 of
  2,000), off-by-one from the conventional order statistic and
  out-of-bounds for N < 40. **RESOLVED 2026-07-28** with F-30:
  linear-interpolated type-7 percentiles (AGG-8).
- **F-44** Dedup replacement locates the superseded record by value
  equality; two structurally identical records under different PR numbers
  could swap the wrong one.
- **F-45** The persistent-author table divides by the 2024 cohort mean
  with no zero guard; §8.2.3's baseline multiple likewise.
- **F-46** Month-token derivation from a quarter start assumed the
  quarter starts ≤ October (a Nov/Dec-starting period would yield month
  "13"). **FIXED test-first in `cc37f06`** (walks the range); kept here
  as a record.
- **F-50** When no window month is mature, the event-study maturity
  labels silently mislabel (negative index) instead of failing.
- **F-51 (population drift, OPEN — issue #17)** FunAudioLLM (full-org,
  top5:3) was RENAMED on GitHub to QwenAudio after the population was
  built: `org:` searches answer 422, `GET /orgs/FunAudioLLM` 404, and
  search does not follow org renames. Its existing census cells remain
  valid historical observations; new collection fails loudly
  (absence-of-evidence rule), and the org is EXCLUDED from the
  2026-07-30 regeneration. The population is frozen between deliberate
  revisions (§1c / METHODS), so the handle migration — re-admitting the
  data under QwenAudio, or converting the org to a documented waiver —
  is deferred to a deliberate population revision. A `GET /orgs/{org}`
  sweep over population.tsv before the next collection run would
  enumerate any further drift.
- **F-8** The census drift allowance (COL-8) tolerates up to 2% silent,
  possibly non-uniform undercount per repo-period; brownout losses are
  not uniform in time.
- **F-7** Enumeration search-cap saturation is warned but the truncated
  tally is cached and used — repo admission for the largest orgs is
  known-incomplete, recorded nowhere machine-readable.

### A.5 Design ambiguities / suspicious constants (documented judgment calls)

- **F-2** `ai_scan` values predate the 2026-07-20 marker audit (2-tool
  era) and only its first count column is read; it functions as a frozen
  legacy evidence floor, not a current scan.
- **F-3** `recheck_scan`'s `total_pr` probe is collected but never used.
- **F-4** Population handle casing is first-seen-wins; the literal casing
  feeds every downstream `org:` query (case-insensitive on GitHub's side,
  but the strings differ).
- **F-6** PR-count cells are keyed by period token, census cells by
  resolved range: redefining a quarter would silently reuse stale
  denominators while re-pulling cells.
- **F-10** Branch-prefix counts (and the layer-C sample universe +
  weights) are org-wide even for repo-scoped orgs — out-of-scope repos'
  prefix PRs count toward R4 evidence and stratification. **Adjudicated
  a bug 2026-07-27 — issue #8.** RESOLVED 2026-07-28: repo-scoped orgs
  are counted per in-scope repo (COL-11); samples query the scoped
  universe (chunked repo: qualifiers within the 256-char search limit)
  BEFORE the 50-newest cap, cells carry universe='scoped' and legacy
  org-wide-drawn cells are re-drawn, with a read-time filter besides
  (STU-P1); a repo-scoped org with no manifest repos has an explicit
  empty universe (never org-wide fallback); the org-wide branch-scan
  rows were purged (admission depended on them for 0 of 47 repo-scoped
  orgs, measured). Scoped re-scan COMPLETED 2026-07-28 (PR #18): all
  1,150 repo-scoped cells collected (only FunAudioLLM's 25 uncollected —
  org renamed, see F-51 / issue #17), Q1-2024 false-positive control 0
  in every scoped cell, samples re-drawn under universe='scoped', no
  headline number changed (DET-C5 figures final).
- **F-15** The productivity-decomposition "authors" column counts
  (repo, author) pairs, not people.
- **F-19** Contributor weights inherit the stats endpoint's top-100
  ceiling (binds exactly on the largest repos) and week-start bucketing
  (±6 days at window edges).
- **F-20** Marker scans window by author-date while the census windows by
  PR creation; rebased/cherry-picked commits can change windows between
  the two views.
- **F-21** Commit search sees default branches only — a floor on every
  layer-A discovery count (per-PR classification via the census is
  unaffected).
- **F-25** `agent@example.com` (the RFC-2606 placeholder domain) is a
  vetted agent identity — any fixture/tutorial commit using it classifies
  as agent-authored.
- **F-26** `hermes-agent@` matches as an open-ended prefix while its
  sibling identities are exact addresses.
- **F-28** In the strict layer-C arm, a web-flow committer
  (`noreply@github.com`) counts as positive provenance even though it
  marks any web-UI commit; the lower bound is not conservative against
  human web-UI commits on prefix branches.
- **F-32** The approval-channel `unknown` residue (merged, unreviewed,
  merger unrecorded) is inside denominators but has no printed column, so
  channel shares do not sum to 100%.
- **F-33** The attention section mixes two populations: the main table
  (profile `pr`, fleet included) and the by-AI table (contrast-gated,
  fleet excluded) — not directly comparable despite adjacency.
- **F-34** Event-study t0 is the first *observed* AI month; 2024-04..
  2025-09 is unobserved (21-month gap), so left-censoring extends beyond
  the acknowledged window edge.
- **F-36** Responsiveness lanes mixed+AI / mixed+nonAI are accumulated
  but never printed — dead output or an undocumented available cut.
- **F-38** The accountability sample seeds the global RNG (not an
  isolated stream): reproducibility depends on nothing else drawing
  first.
- **F-39** Accountability's "one-person%" is structurally zero in the
  other-merged lane (the flag it summarizes implies self-merge) yet is
  printed as if measured.
- **F-35** Historical figure numbering collides ("Figure 2/3" each name
  two artifacts; "Figure 4" had three names and a differently-named file).
  §8.3's table is canonical.
- Six different small-cell suppression floors coexist (30 / 20 / 20 / 10 /
  2 authors / 100 LOC) — only the 30 is without stated basis.
- The fleet threshold (≥ 300 merged PRs/quarter) has no published
  sensitivity analysis.

### A.6 Dead or vestigial surface (do not reimplement)

- `merged_ever` and `substantive_review` are computed per PR but feed no
  reported metric; the human-self review bucket is always discarded; one
  layer-A option (`include_bot_authors`) and one helper (cell validity
  check) have no production callers; the slug regexes exist in two
  identical copies; stale references to two removed/archived artifacts
  (an integration module and an agents.yaml) survive in comments/memos;
  compiled bytecode of the removed integration module lingers and can
  mask an accidental import.

---

## Appendix B — Canonical constants

| constant | value | where defined (source) |
|---|---|---|
| Study cutoff (frame end) | 2026-06-30T23:59:59Z | `detect.CUTOFF` |
| Data-collection stamp | = CUTOFF until first re-pull | `detect.AS_OF` |
| Event/maturity window | 56 days (w8); sensitivity 26 weeks | `detect.W8_DAYS`, `fates` |
| Censused quarters | Q1-2024, Q4-2025, Q1-2026, Q2-2026 | `analyze.CENSUSED_QUARTERS` |
| Quarter date ranges | see FR-2 | `scan_orgs.QUARTER_RANGES` |
| Per-PR LOC cap | 20,000 | `frame.CAP` |
| Census page size / field caps | 50 PRs/page; 12 commits, 6 author emails, 15 reviews per PR | `census.PAGE_SIZE`, `census.PR_QUERY` |
| Hydration caps | 100 commits/page (paginated); 40 conversation comments | `review_action`, `pull_prs` |
| GitHub hard limits relied on | 1,000 search results/query; 250 commits/PR; top-100 contributor stats | EXT-2, EXT-5, EXT-8 |
| Census sub-windowing | k = max(10, ceil(total×1.1/45)), ≤ 1/day | `census.census_repo_period` |
| Census drift allowance | n ≥ 98% of precount, or deficit ≤ 3 | `census.census_repo_period` |
| Flagship star floor | 1,000 | `org_set.FLAGSHIP_MIN_STARS` |
| Evidence floor / rate | ≥ 5; or ≥ 1 and ≥ 0.1% of censused PRs | `org_set.KEEP_MIN_EVIDENCE`, `KEEP_MIN_PR_RATE` |
| Top-5 AI-topic threshold | ≥ 2 (slice split at ≥ 3) | `org_set.TOP5_MIN_AI`, `slices` |
| AI topics dictionary | 28 topics (POP-3) | `org_set.AI_TOPICS` |
| Enum admission window | 2025-07-01..2026-06-30; keep ≥ 5 commits or rate ≥ 0.001 | `enum_repos` |
| Marker set | 6 tools (DET-A2) | `detect.MARKERS` |
| Agent PR authors | 8 logins (DET-B1) | `detect.AGENT_PR_AUTHORS` |
| Branch prefixes / weak | codex/, copilot/, cursor/, claude/, droid/; weak = cursor, claude, droid | `detect.BRANCH_PREFIXES`, `WEAK_PREFIXES` |
| Slug regexes | DET-C3 table | `detect._SLUG` |
| AI reviewers | 9 logins (DET-V3) | `detect.AI_REVIEWERS` |
| User-bot login rule | suffixes -bot, _bot, [bot], -ci, -robot, -agent, _agent; prefix bot- | `detect.is_bot_login` |
| Insider associations | MEMBER, OWNER, COLLABORATOR | `detect.INSIDER` |
| Repo qualification floor | ≥ 5 PRs/quarter, ≥ 2/month | `analyze`, `slices.MIN_PRS` |
| Contributor-weight rule | ≥ 5 commits in 2025-10-01..2026-06-30, `[bot]` excluded, floor 1.0 | `contributors` |
| Bootstrap | per-cell streams: seed = first 8 bytes (big-endian) of SHA-256("20260630\|{cell key}"); draws 2,000 (headline/figures/productivity), 1,000 (panel, botcheck, monthly), 500 (slices); linear-interpolated (type-7) 2.5/97.5 percentiles | `analyze`, `slices`, `monthly_update` |
| Responsiveness sampling | 1,200/quarter; PPS seed "20260630:{per}", EQ seed "20260630:eq:{per}"; HT π = 1−(1−loc/W)^1200 | `review_action` |
| Nonresponse ceiling | 2% once ≥ 20 tombstones | `review_action` |
| Fleet threshold | ≥ 300 merged PRs in any quarter | `productivity.FLEET_MIN` |
| Adoption cohort cuts | first AI month ≤ 2026-02 early, ≤ 2026-04 medium, later late | `productivity` |
| Event-study window / baseline | 2025-10..2026-06; 2024-01..03; offsets −4..+4 (balanced −2..+2) | `event_study` |
| Suppression floors | 30 (event study), 20 (fates, responsiveness lanes), 10 (accountability), 2 core authors, > 100 LOC (corpus) | respective modules |
| Attention size bands | ≤10, 11–100, 101–1k, >1k (capped LOC) | `attention.BANDS` |
| Aux seeds | accountability 13 (global RNG); corpus 7 | respective modules |
| Coverage (published run) | 2,142 repos; 8,568 repo-periods = 8,284 covered + 284 waived (71 repos); population refreshed 2026-07-27 to 228 orgs / 2,136 repos — the 2026-07-30 regeneration re-derives the manifest (unsearchable repos collected per COL-10b; FunAudioLLM excluded per F-51) | census manifest |

---

## Appendix C — Replication protocol (clean-room acceptance criteria)

A clean-room reimplementation validates this study by rebuilding from
this specification plus the declared `data/sources/` snapshots alone —
no reference to the original implementation. It need not use the same
language; a different language is preferred (structural independence).
Equivalence against the reference output is judged in two tiers:

- **REP-1 (deterministic tier — exact match).** Every quantity whose
  definition involves no random draw MUST match the reference exactly:
  population membership and scoping (POP-*), repo manifests and coverage
  counts, per-PR classifications and layer attributions (DET-*), fate
  and maturity outcomes, counts, rates, weighted means, medians, trimmed
  means, decomposition terms — every table's point estimates. Compare
  VALUES, not rendered strings (REP-3). Any tier-1 deviation is a defect
  in one of the two implementations: diagnose to root cause and record
  which side was wrong; never widen a tolerance to absorb it.
- **REP-2 (stochastic tier — statistical agreement).** Bootstrap CI
  endpoints depend on the seeded RNG stream, which is implementation-
  specific (the reference pins Python's Mersenne Twister; a replica
  needs only a documented, seeded PRNG of its own — reproducibility
  within each implementation, not across them). The resampled UNITS and
  their weights are deterministic and therefore tier-1; only the draw
  stream differs. Endpoints are equivalent when, per table cell: (a) the
  two intervals mutually overlap; (b) each endpoint differs by at most
  10% of the reference interval's width; and (c) every categorical
  claim the text hangs on an interval (sign, exclusion of a value,
  non-overlap of two groups) holds under both implementations. A tier-2
  miss under these criteria is expected Monte-Carlo divergence only if
  re-running the replica under a different seed moves the endpoint by a
  comparable amount; otherwise treat it as tier-1.
- **REP-3 (portability watch-list).** Known cross-language traps, to be
  tested rather than assumed: regex dialect (the spec's patterns are
  Python-flavored; port each and pin with the spec's positive AND
  negative examples); login casefolding (ASCII lowercase suffices —
  document any non-ASCII login encountered); ISO-8601 date arithmetic at
  day precision with no timezone drift (all bounds are date-inclusive as
  written); float printing (round-half-even vs round-half-up changes a
  printed 1-decimal digit — another reason tier-1 compares values);
  and memory discipline over the ~31k census cells (stream or database
  them; a whole-store materialization is not required by anything in
  this spec).
- **REP-4 (replication report).** The deliverable is a per-table report:
  tier-1 status (exact / deviating, with root cause and which
  implementation erred), tier-2 endpoint deltas, and any spec ambiguity
  discovered en route — an ambiguity that two reasonable readings
  resolve differently is itself a finding; record it as a spec flag
  (Appendix A style) rather than silently choosing.




