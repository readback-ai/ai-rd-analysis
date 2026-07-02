# Phase 0 plan: API experimentation & the AI R&D definition

Status: planning, 2026-06-24. Branch `phase-0-definition`.
Source of truth: `PROJECT_PLAN.md` §"Phase 0" and `PIPELINE_SPEC.md` §Stage 0–2.

> **PIVOT 2026-06-26 — org provenance over domain classification.** The project
> reframed to **AI-assisted development practices at leading AI organizations**.
> We scope by a curated org allowlist (`ai_labs.yaml`) instead of classifying
> arbitrary repos as "AI R&D" (the gold audit showed that's a fuzzy, judgment-heavy
> task — and hobbyist/low-signal repos aren't the object of study). Provenance =
> inclusion (precision ~1.0). The classifier/gold/RUBRIC track is retained only as
> an OPTIONAL wild-cohort comparison, off the critical path. New primary deliverables:
> `ai_labs.yaml` (org set) + `agents.yaml`/`artifacts/agent_detection_cues.md`
> (detection). The two workstreams below (0.A, 0.B) supersede the old 0.2–0.4.

Phase 0 is read-only, cheap, and **gates all collection**. Goal (revised): finalize
the **org set** and the **agent/AI-detection methodology**, and know the full-run
(org-enumeration) cost. Do not start Phase 1 until the revised exit criteria hold.

---

## 0.A Org allowlist — NEW PRIMARY [IN PROGRESS]
- [x] `ai_labs.yaml`: ~70 lab/infra orgs (frontier, China, regional, academic,
      infra/framework) + ~35 $100M+ funded startups with public code; all handle-
      verified via `gh api` (2026-06-26). Tiered: Tier-1 whole-org pure-plays vs
      Tier-2 big-tech (sub-org/repo curation). Funded-but-no-OSS raisers listed as a
      deliberate exclusion. Funding grounded in TechCrunch's 2025 $100M+ list.
- [ ] Finish Tier-2 big-tech repo allowlists (`microsoft/DeepSpeed`, `NVIDIA/
      TensorRT-LLM`, …) with API verification.
- [ ] Decide long-tail boundary (how many orgs) and **member-vs-external-contributor**
      handling for "own practices" questions.

## 0.B Detection methodology — NEW PRIMARY [LARGELY DONE]
- [x] `agents.yaml` updated: Cursor commit co-author trailer `cursoragent@cursor.com`,
      `claude[bot]` PR app, Codegen/Amazon Q/Factory Droid; Windsurf etc. confirmed
      undetectable.
- [x] **Correction**: co-author trailers need **bare-term** commit search, not the
      `author-email:` qualifier (returns 0 org-scoped). Evidence + org×tool cross-tab
      in `artifacts/agent_detection_cues.md`.
- [x] First measured org × tool table over a 16-org sample
      (`artifacts/ai_detection_first_analysis.md`): bare-term Claude/Cursor undercount
      the `author-email:` method ~10-16x; tool profiles are sharply org-specific
      (anthropics=Claude-dogfood, OpenBMB=Cursor-dominant, hf=both-heavy).
- [ ] Scale the table to the full org set + add a **member filter** (staff vs external).

## 0.C Analysis previews (Phase-3 work pulled forward to validate the design) — 2026-06-26
Early findings (artifacts in `artifacts/`):
- **Adoption curve** (`ai_commit_adoption_curve.md`): AI-written-code commits
  (Claude/Cursor trailers) ÷ total commits across 33 orgs rose **<1% → ~10%** of all
  commits Q3-2025→Q2-2026, **inflection Q1-2026**. Floor (squash strips trailers). Genuine
  rate leader fw-ai 37%; HuggingFace 15% (big volume dilutes raw counts).
- **Concentration caveat** (sanity-checked): raw-count spikes are single-actor artifacts —
  anthropics Q1 = `claudes-c-compiler` (the `claude` agent committing) + bots;
  character-ai = one dev on `larch`; OpenBMB Q2 = `PilotDeck`, one repo but a real ~8-dev
  team. → normalize by total commits AND filter bot committers / single-author repos.
- **Review/attention** (`ai_code_review_comparison.md`): AI-code PRs get less human review
  (35% vs 47%), more often unreviewed (52% vs 43%), slightly more bot review, merge a bit
  less — but faster human review when reviewed. N=83, indicative.
- Superseded earlier cuts: agent-authored-PR timing/review
  (`pr_attention_first_analysis.md`, `pr_review_first_analysis.md`) — kept for reference;
  the AI-code-PR cohort replaces the agent-author cohort.

Remaining to harden before any published claim:
- [ ] Normalize the adoption leaderboard (drop bot committers + single-author repos).
- [x] Scaled the AI-code-PR review cohort to **N=205** by quarter (`ai_code_review_comparison.md`
      HARDENED): AI-code PRs lean more on bot review / less on human review than non-AI, and
      wait longer for human review. No clean automation-acceleration trend; the AI-vs-non
      gap in bot-reliance is the stable signal.
- [x] **Member filter** (via `authorAssociation`): AI-code PRs are 46% insider / 54%
      external — ~same as the 44% non-AI insider share, so AI-written code reflects the
      labs' OWN practice, not just outside contributors. Insider AI-code PRs merge 60% vs
      external 28%.
- [ ] `cost_estimate.md` for the full run.
- [ ] Normalize adoption leaderboard (exclude bot/single-author repos) — only open analysis item.

## 0.D Repo-level AI-evidence sampling design (Ron, 2026-06-26)
Move from org-level samples to a repo-targeted census across the FULL org set (~70):
1. **Org triage** — AI-commit scan over all orgs (33 done + ext scan `commit_trend_ext.tsv`)
   → orgs with any detectable AI. Extends well beyond the 7 used for step (b); ext scan
   already adds LAION-AI, togethercomputer, MiniMax-AI, Stanford labs, etc.
2. **AI-evidence repos** — `search/commits <trailer>` grouped by repository → the exact set
   of repos with AI-written code (efficient + direct; beats a 1% PR sample which misses
   low-rate repos). Auto-scopes big-tech (keeps `microsoft/DeepSpeed`, not the long tail).
3. **Denominators + discard** — per kept repo/period, AI-code-PR rate. **KEEP a repo if
   AI-code ≥0.1% of its PRs in any period OR ≥5 absolute in a period** (Ron). Discard the
   rest — NOT as "no-AI controls" (Windsurf/Codex-CLI/local tools are undetectable, so we
   can't certify them AI-free), just as no-signal.
4. **Analyze** kept repos across periods; AI-code PRs are now few enough to **census**, not
   sample. Review/attention/member split by quarter.
5. **Q1-2024 baseline** — sample the SAME kept repos in Q1-2024 (~nil AI usage) as a
   TEMPORAL control for each repo's own review culture (sound control, unlike no-detectable
   -AI repos). Periods: Q1-2024 (baseline) + Q3-2025 → Q2-2026.

**DONE 2026-06-26** (`artifacts/ai_code_census.md`): 74 AI-active orgs → 196 AI-evidence
repos → 175 product repos censused, 4 periods, **N(AI-code)=1,914**. Headlines: automated
PR review went **1% (Q1-2024) → ~31-40% (Q2-2026)** while human review fell 57%→37%;
AI-code PR rate 0%→21%; AI-code PRs lean more on bots; AI-code acceptance rose 39%→70%
(converging w/ human); AI-code is insider practice (37% vs 33%). Open: normalize adoption
leaderboard (single-actor repos) + `cost_estimate.md`.

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

## 0.2 Build the labeled gold set — DEPRIORITIZED (was the heart; now optional wild-cohort)
> Superseded by 0.A/0.B per the 2026-06-26 pivot. Retained as an optional "AI repos in
> the wild" comparison cohort; no precision target gates collection. The flagged gold
> audit (5/70 rows done) can be resumed if/when the contrast cohort is wanted.
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

## Implementation review — gaps & deficiencies (2026-07-02)

Full audit of the post-pivot implementation. Ordered by severity.

### P0 — durability & reproducibility (fix before anything else)
1. **Nothing since the pivot is committed.** Last commit = gold-set era (Jun 25). All of
   `ai_labs.yaml`, 10 artifacts, `data/ai_evidence_repos.csv`, `data/resume_state/` are
   uncommitted working tree — one worktree cleanup away from total loss. → Commit now
   (awaiting Ron's go-ahead), then commit at each milestone.
2. **No pipeline code in the repo.** Every post-pivot collection/analysis step (scans,
   census pullers, weighting analysis, v2 builder) exists only as ad-hoc shell/python
   heredocs in the conversation transcript. `src/` still holds only deprecated gold-set
   scripts. Violates PIPELINE_SPEC's own resumability requirement; none of the published
   numbers can be regenerated from the repo. → Codify as checked-in scripts (see plan).
3. **Raw data lives in a volatile session scratchpad** and is already partially lost
   (census 307/696 cells, census_big 926/2070, census_rich 394/2559 remain). The 50k-PR
   dataset behind the headline findings is not fully regenerable without re-pulling.
   PIPELINE_SPEC's `raw/` cache + DuckDB store were never stood up. → Durable store.

### P1 — validity of headline claims
4. **"Automated review 1%→33%" conflates CI/lint bots with AI reviewers.** The metric
   counts ANY `Bot`-typename reviewer. We observed gemini-code-assist / copilot-pr-reviewer
   / coderabbit, but never decomposed the surge by reviewer identity. The claim as stated
   may be substantially CI automation. → Decompose bot-review share by reviewer login
   (AI-reviewer allowlist vs other bots); re-state the finding.
5. **AI-code detection in the PR classifier is Claude+Cursor only.** `is_ai()` misses:
   aider trailers, Codex cloud (chatgpt-codex-connector committer / codex@openai.com),
   Gemini/Jules commit attribution, and PRs *authored by* claude[bot]/copilot-swe-agent
   with no trailer. Undercounts AI-code, especially for OpenAI-ecosystem orgs. Also
   `claude[bot]`'s app identity (Anthropic's) was never confirmed. → Extend the marker
   set; quantify the delta on a sample; confirm claude[bot].
6. **No statistical treatment.** No CIs on any rate, no significance tests on AI-vs-non
   gaps, no sensitivity analysis on the weighting choice. Contributor weights use ALL-TIME
   contributor counts (not window-scoped), biasing toward legacy-large repos. Cell Ns vary
   10x. → Bootstrap CIs per period/cohort; window-scoped contributor counts.
7. **Squash-merge undercount never quantified.** All AI-code rates are declared "a floor"
   but the floor's distance from truth is unmeasured. → Sample squash-merged PRs whose
   *head-branch commits* (pre-squash) carried trailers; estimate the loss rate.

### P2 — completeness & consistency
8. **v2 census not run.** All measured findings are v1 (74 orgs). v2 = 215-org list only;
   the 141 new orgs (incl. mlflow 2.9k, BerriAI 1.9k, langgenius 1.7k AI commits) are
   unenumerated/uncensused. Big-tech v2 entries (microsoft/NVIDIA/alibaba) need
   repo-scoping first.
9. **Q2-2026 windows end 06-26** (pull date), but the quarter is complete now. Final
   numbers should use full quarters.
10. **Number drift across docs**: v2 "216" vs file's 215; product repos "175" vs 174
    censused vs 172 in PR-totals; adoption-curve doc says "33 orgs" for what §2 of
    scope_and_methods calls the 105-org scan. Reconcile before anything is published.
11. **Comment-depth still rests on the 120/cell sample** (census_rich paused at 15%);
    full-scale time metrics corrected that sample's overstatements once already — depth
    numbers may shift too. Either finish the pull or caveat the depth findings as sample.
12. **Doc drift**: PIPELINE_SPEC still describes the pre-pivot 5-stage design with
    banners; RESUME.md has become a de-facto plan; `cost_estimate.md` (an exit criterion)
    was never written; gold/RUBRIC/signal_analysis read as active in places. → One
    consolidation pass; PIPELINE_SPEC v2 describing the org→repo→census pipeline actually
    in use.

### P3 — methodology refinements (known, accepted, documented)
13. Member filter = authorAssociation proxy (MEMBER undercounted, COLLABORATOR repo-scoped).
14. Bot committers / single-author repos still inside per-repo rates (concentration was
    flagged org-level; repo-level rates not yet bot-filtered).
15. Detection floor for local tools (Windsurf/Codex-CLI) — structural, documented.

## Remediation plan (proposed order)
- [ ] **R1. Commit everything now**; milestone commits thereafter. (P0.1 — needs Ron's OK)
- [ ] **R2. Codify the pipeline** into `src/` as idempotent, checkpointed scripts:
      `scan_orgs.py` (AI-evidence scan), `enum_repos.py`, `census.py` (rate-limit-aware,
      array-validated — port the fixes learned from the corruption bug), `analyze.py`
      (weighted metrics + bootstrap CIs). Raw JSON → `~/devel/ai-rd-analysis-data/raw/`
      (durable, gitignored, per CLAUDE.md shared-store convention); derived tables →
      committed CSVs. (P0.2, P0.3)
- [ ] **R3. Re-state the automated-review finding**: decompose Bot reviewers by login into
      AI-reviewers vs CI/other; recompute the 1%→33% split into "AI review" and "other
      automation". (P1.4 — highest-value single analysis fix)
- [ ] **R4. Extend AI-code markers** (aider, Codex committer/email, Gemini/Jules, bot-
      authored PRs); confirm claude[bot]; measure the detection delta on one org sample.
      (P1.5)
- [ ] **R5. Re-run the census as v2** with: 215-org set (big-tech repo-scoped), full
      quarters (Q2 through 06-30), extended markers, bootstrapped CIs, window-scoped
      contributor weights, repo-level bot/single-author filters. This subsumes the v1
      re-pull (raw cells lost anyway) and closes P1.6, P2.8, P2.9 in one run.
- [ ] **R6. Quantify squash undercount** on a sample (P1.7).
- [ ] **R7. Doc consolidation**: PIPELINE_SPEC v2, reconcile counts, write
      `cost_estimate.md` from measured throughput (~347 PRs/min detail, ~17 cells/min),
      fold RESUME.md status into this plan. (P2.10, P2.12)
- [ ] **R8. (Optional) finish census_rich** for full-scale comment depth, or ship depth
      findings clearly labeled as sampled. (P2.11)

## Exit criteria (REVISED 2026-06-26 — all must hold before Phase 1)
- [ ] `agents.yaml` (detection, bare-term correction) + `ai_labs.yaml` (verified org
      allowlist, Tier-2 repos finalized) complete; member-vs-contributor decided.
- [ ] Per-signal detection recall characterized across the org set
      (`agent_detection_cues.md` extended to a measured table).
- [ ] `cost_estimate.md`: org-enumeration full-run cost understood and acceptable.
- [ ] (Optional) wild-cohort gold set only if a contrast is wanted — NOT a gate.
~~Classifier precision on gold ≥ target~~ — no longer an exit gate.

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

Resolved (Ron, 2026-06-26 — strategic pivot):
10. **Scope by org provenance, not domain classification.** Analyze leading AI orgs
    (`ai_labs.yaml`) directly; drop per-repo AI-R&D classification from the critical
    path. Rationale: classification is fuzzy/impossible at the boundary, and hobbyist /
    low-signal repos are not the object of study — the goal is **evidence on how top AI
    developers work**. Classifier/gold/RUBRIC retained only as optional wild-cohort.
11. **Org set = top labs + $100M+ funded startups with public code**; funded-but-no-OSS
    raisers explicitly excluded (documented). Narrow agentic→BUILDS labels (decisions
    in RUBRIC) now matter only for the optional wild cohort.

Still open (defaults proposed; confirm during execution):
2. Gold sample size & double-labeling (default: ~180 repos, double-label ~30).
5. ~~Claude Code trailer-scanning~~ — RESOLVED in 0.1: no full repo scan needed.
   Search Commits indexes the co-author email (~6.3M commits), so Claude Code (and
   Codex) are enumerable directly via a commit-search seed loop. Recover and report
   the rate openly. Cost of commit→PR mapping to be sized in 0.5.
6. Pinned LLM model id for the classifier tier (default: current Claude model with
   structured output; pin in 0.4).
