# Phase 0 plan: API experimentation & the AI R&D definition

Status: planning, 2026-06-24. Branch `phase-0-definition`.
Source of truth: `PROJECT_PLAN.md` §"Phase 0" and `PIPELINE_SPEC.md` §Stage 0–2.

Phase 0 is read-only, cheap, and **gates all collection**. Goal: turn "AI R&D
repository" from a phrase into a measured classifier (precision ≥ target) and
know the full-run cost before spending it. Do not start Phase 1 until all five
exit criteria hold.

---

## Review notes on the specs (gaps to resolve here, not later)

1. **Auth is a hard prerequisite, not implied.** All of 0.1–0.3 hit live search
   (30 req/min, authenticated). `gh` is already authed via keyring; Phase 0
   scripts should call `gh api` (REST + GraphQL) to inherit it. No PAT env var
   needed. Added below as step 0.0.
2. **Precision target has no recall floor.** "Hold precision ≥0.90, accept lower
   recall" can converge on a classifier that accepts almost nothing. Set a
   *minimum recall sanity bound* (proposal: recall ≥0.70 on gold BUILDS_AI) so
   the keep-set isn't gutted. Decide the exact number in 0.4.
3. **Single-labeler gold set → measured "precision" is vs one person's labels.**
   Cheap mitigation: double-label ~30 of the ~180 repos (or a second pass after a
   cooling period) and report agreement, so the ground truth itself has an error
   bar. Optional but strengthens every downstream claim.
4. **Dual-signal repos (torch *and* openai) are the crux.** Spec flags it as an
   open question; the gold set must over-sample these so the rule/LLM boundary is
   actually tested, not guessed. Baked into the 0.2 stratification.
5. **LLM model not pinned.** Default to a current Claude model with structured
   output `{label, confidence, reason}`; pin the exact id in 0.4 and record it in
   `RUBRIC.md` for reproducibility.
6. **Gold population = repos that already use agents** (sampled from Stage 0 PRs).
   That's the correct population to measure on (it's what the classifier runs on),
   but it means precision/recall do **not** generalize to all of GitHub. State
   this in `signal_analysis.md`; it's also the selection-bias caveat for Phase 3.

---

## 0.0 Prerequisites (a few hours) — DONE 2026-06-24
- [x] `gh auth status` OK (keyring, rbodkin); `gh api rate_limit` confirms
      search 30/min, core 5000/hr, graphql 5000/hr.
- [x] Create artifact dirs: `data/gold/`, `data/sample/`, `src/`, `artifacts/`.
- [ ] Scaffold the Python env with `uv` (deps: `httpx`/`requests`, `pyyaml`,
      `anthropic` for the LLM tier; `duckdb` deferred to Phase 1). — deferred until
      0.2 needs scripted collection; 0.1 done via `gh api` directly.
- [ ] Thin GitHub client wrapper (search-window iterator w/ 30/min throttle +
      `Retry-After`; `gh api graphql` helper). — build alongside 0.2.

## 0.1 Confirm agent identities (½ day) — DONE 2026-06-24
- [x] Probed every handle against live search. Confirmed PR-author bots:
      `devin-ai-integration[bot]` (177k), `copilot-swe-agent[bot]` (1.96M),
      `cursor[bot]` (51k), `google-labs-jules[bot]` (303k). `cursoragent` is dead.
- [x] **Codex resolved**: NOT a PR-author bot. Cloud = committer
      `chatgpt-codex-connector[bot]`; CLI = `author-email:noreply@openai.com`.
      Found only via Search Commits, then map commit→PR.
- [x] **Claude Code resolved**: Search Commits indexes the co-author email, so
      `author-email:noreply@anthropic.com` ≈ 6.3M commits globally (vs AIDev's
      5,137). GraphQL `commit.authors` confirms recovery at hydration.
- [x] Cross-checked `botcommits.dev` (trailer-only method; complementary to author search).
- Deliverable: **`agents.yaml`** ✔ — handles, per-agent detection method, counts,
  Claude Code recovery note.
- **Stage 0 consequence**: two seed loops — author-search (4 agents) + commit-search
  (Codex, Claude Code) — both date-windowed under the 1000/30-min limits.

## 0.2 Build the labeled gold set (1–2 days) — the heart of Phase 0  [IN PROGRESS]
- [x] Stage 0 mini-sample (May 2026, all 6 agents incl. commit-search) → 2016 unique
      repos (`data/sample/repo_sample.csv`). `src/seed_sample.py`.
- [x] Batch metadata via GraphQL (`src/fetch_meta.py`): web-app skewed, 16.5% have
      any topic, 51% have no description.
- [x] Stratified **180** candidates over 5 strata, over-sampling positives
      (`src/stratify.py`). 7 dual-signal cases.
- [x] Evidence (README head + manifests, dep-based BUILDS/USES) →
      `data/gold/gold_repos.csv` (`src/build_worksheet.py`).
- [x] Claude proposed all 180 labels w/ confidence + audit flags
      (`src/apply_labels.py`): BUILDS 37 / USES 35 / NOT 108; 66 flagged.
      **Cheap-rule anchor agreed with judgment only 47%** → rules alone inadequate.
- [x] First-draft **`RUBRIC.md` v0** with boundary rules from the labeling.
- [ ] **Ron audits** the 66 flagged rows (+ spot-check) → fills `human_label`;
      finalize RUBRIC.  ← NEXT, BLOCKING
- [ ] Double-label ~30 for an agreement number (review note 3).
- Deliverable: `data/gold/gold_repos.csv` + `RUBRIC.md` (both started; await audit).

## 0.3 Characterize signals vs the gold set (1 day)  [DONE]
Measure each cheap signal's precision/recall against the human labels:
- [ ] **Topics** — recall of the topic-accept rule on gold BUILDS_AI (expect mediocre).
- [ ] **Org owner** — build allowlist from gold owners, check leakage/precision.
- [ ] **Dependencies** — pull root manifests for gold repos; test whether
      torch/transformers vs openai-sdk-only separates BUILDS from USES cleanly.
- [ ] **Stars/language** — weak prior or noise?
- Deliverable: **`signal_analysis.md`** — precision/recall per signal + decision on
  which become auto-accept/reject rules vs which defer to the LLM.

## 0.4 Prototype & measure the layered classifier (1 day)
- [ ] Implement Stage 2 layered classifier (rules → LLM on residual), per
      `PIPELINE_SPEC.md` §Stage 2. Cache by `repo_id`, stamp `rule_version`.
- [ ] Run on gold; report confusion matrix + precision/recall per label.
- [ ] Tune rubric + thresholds until precision ≥ target AND recall ≥ floor; re-audit.
- Deliverable: classifier code in `src/` + measured precision + **`RUBRIC.md` v1**.

## 0.5 Estimate full-run cost (½ day)
- [ ] Extrapolate from the sample: expected unique AI R&D repos, PRs to hydrate,
      GraphQL points + wall-clock at 5000/hr, LLM tokens for classify + task_type.
- [ ] PAT vs GitHub App decision based on search-volume estimate.
- Deliverable: **`cost_estimate.md`** + go/no-go on collection window
  (recommend: 2025-08-01 forward + one backfill-overlap month vs AIDev).

---

## Exit criteria (all must hold before Phase 1)
- [ ] `agents.yaml`, `RUBRIC.md` v1, `gold_repos.csv`, `signal_analysis.md`,
      `cost_estimate.md` all exist.
- [ ] Classifier precision on gold ≥ target (and recall ≥ floor).
- [ ] Full-run cost understood and acceptable.

## Decisions

Resolved (Ron, 2026-06-24):
1. **Quality bar: precision ≥0.90 AND recall ≥0.70** on gold BUILDS_AI. Tune in 0.4
   until both hold; re-audit.
3. **Dual-signal repos → BUILDS_AI** by rule, REFINED in 0.2: only a genuine
   training/serving stack counts; embeddings/RAG libs (sentence-transformers,
   chromadb) do not — consumer RAG apps stay USES_AI.
4. **Retain USES_AI as a labeled comparison cohort** (not dropped).

Resolved (Ron, 2026-06-25 gold-set audit):
7. **4-class scheme**: BUILDS_AI / USES_AI / **AI_INFRA** / NOT_AI. AI_INFRA is a
   separate cohort for AI/agent-specific tooling/infra (MCP servers, context/memory
   utils, vector infra, plugins, scaffolding, task hubs). Retain it labeled too.
8. **All agent systems = BUILDS_AI** — autonomous-agent products count, not just
   frameworks.
9. **Applied ML in a domain product = USES_AI** (the ML is a means, not the purpose).

Still open (defaults proposed; confirm during execution):
2. Gold sample size & double-labeling (default: ~180 repos, double-label ~30).
5. ~~Claude Code trailer-scanning~~ — RESOLVED in 0.1: no full repo scan needed.
   Search Commits indexes the co-author email (~6.3M commits), so Claude Code (and
   Codex) are enumerable directly via a commit-search seed loop. Recover and report
   the rate openly. Cost of commit→PR mapping to be sized in 0.5.
6. Pinned LLM model id for the classifier tier (default: current Claude model with
   structured output; pin in 0.4).
