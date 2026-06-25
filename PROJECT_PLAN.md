# Project plan: agentic PRs in AI R&D repositories

## Goal
Produce a fresh, queryable dataset of autonomous-coding-agent pull requests scoped
to AI research and development repositories, current through collection date, and
the analysis marts to support trend claims about agents contributing to AI codebases.

## Guiding principle
The bottleneck is not ETL. It is the operational definition of "AI R&D repository."
Phase 0 exists to nail that definition empirically against the live GitHub API
before committing to a full collection run. Build the classifier on evidence, not
on a guess about what topics or owners imply.

## Success criteria
- A versioned `RUBRIC.md` defining AI R&D, with a measured classifier precision
  on a hand-audited sample (target >= 0.90).
- A reproducible pipeline (per `PIPELINE_SPEC.md`) that runs end to end and
  resumes from any stage.
- A dataset with a self-documenting coverage window, so recency is never overstated.
- At least one validated trend chart that the AIDev snapshot cannot produce
  (post-2025-08 activity in AI R&D repos).

---

## Phase 0: API experimentation and definition (the critical phase)

Objective: turn "AI R&D project" from a phrase into a tested classifier. Everything
here is cheap, read-only, and runs against live GitHub. Do not start full
collection until Phase 0 exit criteria are met.

### 0.1 Confirm agent identities (half a day)
- For each agent, run a small `GET /search/issues?q=is:pr+author:<handle>` and
  inspect 10-20 real PRs to confirm the handle is live and correct.
- Resolve the two unstable ones: OpenAI Codex connector login and the current
  Copilot coding-agent login. Cross-check against `botcommits.dev`.
- Probe Claude Code: pick 3-5 repos known to use it, fetch recent PR commits via
  GraphQL, and confirm the `Co-Authored-By: Claude` trailer appears in
  `commit.authors`. Decide whether trailer-scanning is worth the cost.
- Deliverable: `agents.yaml` with confirmed handles, detection method per agent,
  and a known-undercount note for Claude Code.

### 0.2 Build a labeled gold set of repositories (1-2 days)
This is the heart of Phase 0. You cannot measure a classifier without ground truth.
- Pull the unique repo list from a small Stage 0 sample (for example, one recent
  month of Codex + Cursor + Devin PRs). Expect a few thousand unique repos.
- Hand-label a stratified sample of ~150-200 repos as BUILDS_AI / USES_AI / NOT_AI,
  using the repo page, description, topics, and README. Stratify so you capture
  edge cases: LLM wrapper apps, ML tutorials, infra/devtools used by ML, datasets,
  notebooks.
- This labeling is where the real definition gets decided. As you label, write down
  every boundary call you make. Those rules become `RUBRIC.md`.
- Deliverable: `gold_repos.csv` (repo_id, full_name, human_label, note) and a
  first draft `RUBRIC.md`.

### 0.3 Characterize the signals against the gold set (1 day)
Measure, do not assume, how well each cheap signal predicts the human label.
- Topics: what fraction of gold BUILDS_AI repos actually carry an AI topic?
  (Estimate recall of the topic rule. Expect it to be mediocre.)
- Org owner: how precise is an org allowlist? Build the allowlist from the gold set
  owners, then check leakage.
- Dependencies: pull manifests for the gold repos, test whether the
  torch/transformers vs openai-sdk split separates BUILDS from USES cleanly.
- Stars/language: are they useful as weak priors or just noise?
- Deliverable: `signal_analysis.md` with precision/recall per signal, and a decision
  on which signals become auto-accept/reject rules vs which defer to the LLM.

### 0.4 Prototype and measure the layered classifier (1 day)
- Implement the Stage 2 layered classifier (rules then LLM on residual).
- Run it on the gold set. Report confusion matrix, precision, recall per label.
- Tune the rubric and rule thresholds until precision clears target. Re-audit.
- Deliverable: classifier code + a measured precision number + final `RUBRIC.md` v1.

### 0.5 Estimate full-run cost (half a day)
- Extrapolate from the sample: unique AI R&D repos expected, PRs to hydrate,
  GraphQL points and wall-clock at 5000/hr, LLM tokens for classification + task_type.
- Decide PAT vs GitHub App based on the search-volume estimate.
- Deliverable: `cost_estimate.md` and a go/no-go on collection window
  (how far back to collect, what end date).

### Phase 0 exit criteria
- `agents.yaml`, `RUBRIC.md` v1, `gold_repos.csv`, `signal_analysis.md`,
  `cost_estimate.md` all exist.
- Classifier precision on the gold set >= target.
- Full-run cost is understood and acceptable.
Do not proceed to Phase 1 until all five hold.

---

## Phase 1: Build the pipeline (per PIPELINE_SPEC.md)

- Stand up the DuckDB + Parquet store and the `checkpoint` / `run_manifest` tables.
- Implement Stage 0 seed with date-window bisection and the 30/min throttle.
- Implement Stage 1 repo metadata with ETag conditional requests.
- Wire Stage 2 to the Phase 0 classifier.
- Implement Stage 3 GraphQL hydration with inner-connection pagination and raw
  response caching.
- Implement Stage 4 marts.
- Build the validation gates as automated checks, not manual steps.
- Test on a single-month, single-agent slice end to end before scaling.
Deliverable: pipeline that processes a slice and passes all validation gates.

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

- Reproduce AIDev's headline analyses (merge rate, turnaround, language, task type)
  on the AI R&D subset, and contrast with their whole-GitHub numbers.
- Build the trend lines that require post-cutoff data: agent adoption curve inside
  AI R&D repos, merge-acceptance trend, Jules and other post-snapshot agents.
- If retained, contrast BUILDS_AI vs USES_AI cohorts.
- Write the selection-bias statement: this is AI R&D repos that already adopted
  agents, a self-selected slice, valid for "how agents are used within AI R&D" and
  not generalizable to AI development at large. Ship it with every chart.
Deliverable: analysis notebook + figures + caveats.

---

## Risks and mitigations
- Definition drift: the AI R&D boundary is subjective. Mitigation: versioned rubric,
  measured precision, audit sample shipped with the data.
- Classifier precision below target: cheap rules may not separate BUILDS from USES.
  Mitigation: lean harder on dependency signals and LLM tier, accept lower recall to
  hold precision.
- Claude Code undercount: structural, not fixable by author-search. Mitigation:
  decide trailer-scanning in Phase 0, report the recovery rate openly.
- Rate-limit stalls on search: 30/min is the binding constraint at scale.
  Mitigation: date-window bisection, GitHub App for higher installation ceiling.
- Codex/Copilot handle changes: agent identities drift. Mitigation: `agents.yaml`
  re-validated at the start of every run.
- Scope creep into full-GitHub collection: tempting given AIDev's code. Mitigation:
  the AI R&D filter is the point, hold the line on it.

## Sequencing summary
Phase 0 (4-6 days, read-only experimentation) gates everything. Phases 1-3 only
begin once the definition is tested and the cost is known. The expensive work
(hydration, full run) happens last, on a repo set you have already proven you can
classify well.
