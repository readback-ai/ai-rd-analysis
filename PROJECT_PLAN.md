# Project plan: AI-assisted development practices at leading AI organizations

## Goal
Produce a fresh, queryable dataset of how **leading AI organizations** use
autonomous coding agents and AI assistance in their **public** development, and the
analysis marts to support trend claims about agent/AI adoption among top AI builders.

## Guiding principle (PIVOTED 2026-06-26)
Scope by **org provenance, not domain classification.** The original plan tried to
classify arbitrary GitHub repos as "AI R&D" via a layered LLM classifier — a fuzzy,
low-precision, judgment-heavy task (the gold audit showed even humans disagree on
core-vs-auxiliary). We replace that with an externally-sourced set
of top AI organizations: frontier/research labs, and
well-funded ($100M+) AI startups. Any repo under an allowlisted org is in-scope by
construction (precision ~1.0, no classifier). This deliberately targets the
practices of **top AI developers** and excludes hobbyist / low-signal repos, which
are not the object of study. The bottleneck is no longer "what is an AI repo" but
**reliable detection of agent / AI-assistance activity inside a known org set**
(see `agents.yaml`, `artifacts/agent_detection_cues.md`).

## Success criteria
- A versioned, verified `ai_labs.yaml` org allowlist (tiered: whole-org pure-plays
  vs sub-org-curated big-tech) covering the leading labs + $100M+ funded startups.
- A versioned `agents.yaml` detection methodology with measured recall per signal
  (bot-author PRs, commit co-author trailers, config-file adoption).
- A reproducible pipeline (per `PIPELINE_SPEC.md`) that enumerates org repos and
  scans each for agent/AI signals, end to end and resumable.
- A dataset with a self-documenting coverage window, so recency is never overstated.
- At least one validated finding: **agent/AI-assistance adoption by org and by tool**
  across top AI orgs (e.g. HuggingFace→Claude Code, OpenBMB→Cursor), incl. usage
  invisible to naive author-search.

## Retained as optional secondary cohort (was the primary plan)
**UPDATE 2026-07-08: the domain classifier / gold set / `RUBRIC.md` track was
REMOVED** (git history preserves it). The org set is no longer hand-curated
(`ai_labs.yaml` deleted): it is built from four third-party source lists — LF
AI & Data landscape, Hugging Face top orgs, GitHub AI topics, and TechCrunch's
2025 $100M+ AI funding round-up (+ frontier labs; transcription record
`v1_carryover.txt`) — with a quality gate
(>=1 repo with >=1k stars) and an AI-evidence keep rule; see
`src/pipeline/org_set.py` and `docs/METHODS.md`.
The old note is kept below for history:
The hand-labeled gold set may serve as a small "AI repos in the wild" comparison
cohort to contrast against the top-org cohort. It is no longer on the critical path
and its precision target no longer gates collection.

---

## Phase 0: define the org set and the detection methodology (the critical phase)

Objective: lock down **which orgs** are in scope and **how to detect** agent/AI
activity in their repos. Everything here is cheap, read-only, live GitHub. Do not
start full collection until exit criteria are met.

### 0.1 Confirm agent identities — DONE
- `agents.yaml`: confirmed bot-author handles (Devin, Copilot, Cursor[bot], Jules)
  + commit-search agents (Codex, Claude Code). Plus 2026-06-26 additions: Cursor
  **commit co-author trailer** `cursoragent@cursor.com`, `claude[bot]` PR app, and
  Codegen / Amazon Q / Factory Droid.
- **Key correction**: detect co-author trailers via **bare-term** commit search, NOT
  the `author-email:` qualifier (which misses them org-scoped). Evidence:
  `artifacts/agent_detection_cues.md`.

### 0.2 Build the org allowlist (the new heart of Phase 0) — IN PROGRESS
- `ai_labs.yaml`: ~70 lab/infra orgs (frontier, China, regional, academic, infra/
  framework) + ~35 $100M+ funded startups with public code. All handle-verified via
  `gh api`. Tiered: Tier-1 whole-org pure-plays vs Tier-2 big-tech (sub-org/repo
  curation). Funded-but-no-OSS raisers documented as a deliberate excluded list.
- Remaining: (a) finish Tier-2 big-tech repo allowlists (`microsoft/DeepSpeed` etc.)
  with verification; (b) decide the long-tail boundary; (c) decide
  **member-vs-external-contributor** handling (the org's own staff practices vs
  outside contributors using agents on its repos).

### 0.3 Characterize detection signals against the org set (was: vs gold) — PARTIAL
Measure recall of each detection signal inside the org set, not classifier precision.
- Bot-author PRs (per agent), commit co-author trailers (Claude/Cursor/aider),
  committed config files (CLAUDE.md / AGENTS.md / .cursorrules / copilot-instructions).
- Cross-tab adoption by org × tool (started: HuggingFace→Claude Code, OpenBMB→Cursor,
  vLLM/pytorch→external-contributor agent PRs).
- Deliverable: extend `artifacts/agent_detection_cues.md` into a measured signal table.

### 0.4 (Optional / deprioritized) Domain classifier comparison cohort
- The gold set + `RUBRIC.md` are retained but OFF the critical path. If a "wild AI
  repos" contrast is wanted later, finish the gold audit and measure the classifier.
  No precision target gates collection anymore.

### 0.5 Estimate full-run cost (half a day)
- Org-first enumeration is far cheaper than global agent-PR search: ~100 orgs × repos
  via list-org-repos (core API, 5000/hr) + per-repo agent scans. Extrapolate repos to
  enumerate, commits/PRs to hydrate, GraphQL points, wall-clock.
- Decide PAT vs GitHub App. Deliverable: `cost_estimate.md` + collection-window go/no-go.

### Phase 0 exit criteria (REVISED)
- `agents.yaml` (detection methodology, with bare-term correction) and `ai_labs.yaml`
  (verified org allowlist) finalized; member-vs-contributor decision made.
- Per-signal detection recall characterized inside the org set.
- Full-run (org-enumeration) cost understood and acceptable.
Do not proceed to Phase 1 until these hold. (Classifier precision is no longer a gate.)

---

## Phase 1: Build the pipeline (per PIPELINE_SPEC.md)

> **REVISED by the 2026-07-02 implementation review** (`PHASE_0_PLAN.md` §"Implementation
> review"). Phase 0's analysis previews produced strong findings but as ad-hoc, unversioned
> pulls into volatile storage — none of it is reproducible from the repo, and the raw cells
> are already partially lost. Phase 1 is therefore **codification + one defensible v2
> re-run**, per the remediation plan R1–R8: commit everything; port the pullers (with the
> rate-limit/corruption fixes already learned) into checkpointed `src/` scripts writing to
> a durable raw store; decompose the bot-review headline into AI-review vs CI; extend
> AI-code markers beyond Claude+Cursor; then run the v2 census (215 orgs, full quarters,
> bootstrap CIs) as the publishable dataset. The bullets below are subsumed by R2/R5.

- Stand up the DuckDB + Parquet store and the `checkpoint` / `run_manifest` tables.
- Implement Stage 0 seed = **enumerate repos under `ai_labs.yaml` orgs** (list-org-repos,
  core API; Tier-2 orgs use the curated repo allowlist). Optional secondary seed:
  global agent-PR search for the deprioritized wild cohort.
- Implement Stage 1 repo metadata with ETag conditional requests.
- Stage 2 = **org-provenance gate** (in-scope iff owner is allowlisted) — provenance
  is the label; the LLM classifier is optional and only runs for the wild cohort.
- Per-repo **agent/AI scan**: bot-author PRs + bare-term commit-trailer search
  (Claude/Cursor/aider) + config-file presence, per `agents.yaml`.
- Implement Stage 3 GraphQL hydration with inner-connection pagination and raw
  response caching. Implement Stage 4 marts.
- Build the validation gates as automated checks. Test on a few orgs end to end first.
Deliverable: pipeline that processes a few orgs and passes all validation gates.

## Phase 2: Full collection run

- Pick the collection window from Phase 0 (recommend collecting from the AIDev
  cutoff 2025-08-01 forward, so your data extends rather than duplicates AIDev,
  plus a backfill overlap month to validate against AIDev's numbers).
- Run staged, monitor budget headers, resume on interruption.
- Validate: row counts, classifier precision spot-check, coverage gaps, Claude Code
  recovery rate.
- Stamp `run_manifest` with the true coverage window.
Deliverable: v1 dataset with documented coverage.

## Phase 3: Analysis and trend marts

> **Preliminary findings (2026-06-26, from Phase-0 analysis previews — see `artifacts/`):**
> - **Adoption curve**: AI-written-code commits (Claude/Cursor trailers) rose **<1% → ~10%
>   of all commits** across 33 leading-AI orgs, Q3-2025→Q2-2026, **inflection Q1-2026**.
>   Claude ≈ 84% of the signal; Cursor org-specific. Genuine rate leader fw-ai 37%.
> - **Normalize** by total commits and filter bot committers / single-author repos — raw
>   counts are dominated by single-actor spikes (anthropics `claudes-c-compiler`,
>   character-ai `larch`).
> - **Review**: PRs containing AI-written code get *less* human review and more often go
>   unreviewed than non-AI PRs (lean more on bot reviewers); faster human review when
>   reviewed. (Indicative; needs scaling + member filter.)
> These validate the org-provenance design; the bullets below are the full-run versions.

- **Adoption by org × tool**: which top orgs use which agents/assistance, in the open,
  and the trend over time (incl. signal invisible to author-search — config files,
  co-author trailers). This is the headline the org cohort uniquely enables.
- Reproduce AIDev's headline analyses (merge rate, turnaround, language, task type)
  on the top-org cohort, and contrast with AIDev's whole-GitHub numbers.
- **Staff vs external contributors**: separate the org's own AI-assisted development
  from outside contributors using agents on its repos (member filter).
- Optional: contrast the top-org cohort against the deprioritized wild cohort.
- Write the selection statement: this is **prominence-selected top AI orgs**, valid for
  "how leading AI builders develop in the open," NOT a representative sample of AI
  development at large, and limited to *public* repos. Ship it with every chart.
Deliverable: analysis notebook + figures + caveats.

---

## Risks and mitigations
- Org-list completeness/selection: the allowlist defines the universe, so omissions =
  blind spots and inclusion choices are editorial. Mitigation: versioned, tiered,
  criteria-documented `ai_labs.yaml`; the funded-but-no-OSS exclusions are listed
  explicitly; revisit the long tail openly.
- Not representative: top orgs ≠ AI development at large. Mitigation: state the
  prominence-selection caveat on every chart; optional wild-cohort contrast.
- Invisible local tooling undercount: Cursor IDE / Windsurf / Codex CLI leave no
  public marker. Mitigation: use every available signal (bot PRs, bare-term commit
  trailers, config files); report what is structurally undetectable.
- `author-email:` mis-recall: it misses co-authored commits org-scoped. Mitigation:
  bare-term commit search (already corrected in `agents.yaml`).
- Public-only bias: labs do much work in private repos. Mitigation: state it; the
  claim is about *public* practices only.
- Staff vs external contributor conflation: a bot PR on an org repo may be an outsider.
  Mitigation: member filter for "own practices" questions.
- Agent handle drift: Mitigation: `agents.yaml` re-validated at the start of every run.

## Sequencing summary
Phase 0 (now mostly DONE: org list + detection methodology built) gates everything.
Phases 1-3 begin once the org set and detection are finalized and cost is known. The
pivot to org provenance removes the classifier bottleneck and shrinks the collection
to a bounded, high-signal set of leading-AI-org repos.
