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

## 0.0 Prerequisites (a few hours)

- [ ] Confirm `gh auth status` works and `gh api rate_limit` shows the search +
      core budgets. (Search: 30/min; core: 5000/hr.)
- [ ] Scaffold the Python env with `uv` (deps: `httpx`/`requests`, `pyyaml`,
      `anthropic` for the LLM tier; `duckdb` deferred to Phase 1).
- [ ] Create artifact dirs: `data/gold/`, `data/sample/`, `src/`, `artifacts/`.
- [ ] Add a thin GitHub client wrapper: search-window iterator with 30/min
      throttle + `Retry-After` handling, and a `gh api graphql` helper. Read-only.
- Deliverable: runnable env + `rate_limit` confirmed.

## 0.1 Confirm agent identities (½ day)
- [ ] For each agent in `PIPELINE_SPEC.md` table, run
      `GET /search/issues?q=is:pr+author:<handle>`, inspect 10–20 real PRs.
- [ ] Resolve the unstable two: OpenAI **Codex** connector login and current
      **Copilot** coding-agent login. Cross-check `botcommits.dev`.
- [ ] Probe **Claude Code**: 3–5 known repos, fetch recent PR commits via GraphQL,
      confirm `Co-Authored-By: Claude` appears in `commit.authors`. Decide whether
      trailer-scanning earns its cost (Open Q3).
- Deliverable: **`agents.yaml`** — confirmed handles, detection method per agent,
  Claude Code undercount note.

## 0.2 Build the labeled gold set (1–2 days) — the heart of Phase 0
- [ ] Stage 0 mini-sample: one recent month of Codex + Cursor + Devin PRs; extract
      unique repos (expect a few thousand). Save to `data/sample/`.
- [ ] Hand-label a **stratified ~150–200** repos BUILDS_AI / USES_AI / NOT_AI.
      Strata to force coverage of edge cases: LLM-wrapper apps, ML tutorials,
      infra/devtools used by ML, datasets, notebooks, **and dual-signal repos
      (torch + openai)**.
- [ ] Log every boundary call while labeling — these become the rubric.
- [ ] Double-label ~30 for an agreement number (see review note 3).
- Deliverable: **`data/gold/gold_repos.csv`** (`repo_id, full_name, human_label,
  note`) + first-draft **`RUBRIC.md`**.

## 0.3 Characterize signals vs the gold set (1 day)
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

## Open decisions (owner: Ron — needed to finalize, defaults in parens)
1. Target precision & **recall floor** (0.90 precision / 0.70 recall?).
2. Gold sample size & whether to double-label a subset (180 / yes-30?).
3. Treatment of dual-signal repos (torch+openai → BUILDS_AI by default?).
4. Retain USES_AI as a comparison cohort or drop it? (retain, labeled — recommended).
5. Claude Code trailer-scanning: scan now or accept+label the undercount?
6. Pinned LLM model id for the classifier tier.
