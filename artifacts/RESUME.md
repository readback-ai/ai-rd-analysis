# RESUME STATE — updated 2026-06-28

## v2 ORG SET: DONE (2026-07-02) — 216 defensible AI-active orgs
`data/resume_state/v2/v2_active.txt` (74 v1 + 142 new). Pipeline & result in
`scope_and_methods.md` §"v2 RESULT". Superset of v1; nothing dropped.
- NOTE: scratchpad partially cleared over the multi-day gap — v1 census cells now
  307/696 (census/) + 926/2070 (census_big/). All v1 *findings* persist in artifacts/;
  durable inputs in data/resume_state/. v2 census would re-pull anyway.
- NEXT for v2 analysis (multi-hour, not yet run): AI-evidence-repo enumeration on the 142
  NEW orgs → product repos → census (Q1-2024 baseline + Q3'25→Q2'26) → weighted analysis.
  v1 orgs already enumerated (but cells partially cleared — may need re-pull).

## (superseded) v2 build log (2026-06-29): externally-sourced defensible org set
Replacing hand-curated v1 (105 orgs) with a reproducible set from EXTERNAL sources:
- **Sources**: HF Hub top model-orgs (API); Epoch AI notable/frontier models CSV
  (epoch.ai/data/notable_ai_models.csv — `Organization` col); LF AI&Data landscape
  (github.com/lfai/lfai-landscape, github URLs); GitHub topic+stars (search API);
  TechCrunch $100M+ 2025 (funded startups). Extracts in `data/resume_state/v2/`.
- **Candidate pool**: 482 GitHub orgs, provenance-tagged (`data/resume_state/v2/candidates.tsv`:
  org \t sources). 457 not in v1; 43 in ≥2 sources. New vs v1: BAAI/FlagOpen, BentoML,
  MLflow, Langfuse, Dify, mem0ai, predibase, open-webui, browser-use, h2oai, ludwig, etc.
- **RUNNING `b9mzd7gls`**: all-time AI-evidence scan (Claude+Cursor trailers) over all 482
  → AI-active v2 set (≥5 commits). Non-existent/mismapped orgs return 0 (auto-excluded).
- **NEXT after scan**: quarterly scan + AI-evidence-repo enumeration on the AI-active v2
  orgs; reuse v1 census cells where orgs overlap; pull only NEW orgs; then re-run the
  per-repo equal/contributor-weighted analysis (Q1-2024 baseline + Q3'25→Q2'26).
- Name-mapping note: HF/Epoch use non-GitHub names; alias map applied for major ones
  (Qwen→QwenLM, laion→LAION-AI, BAAI→FlagOpen, facebook→facebookresearch, etc.). gh-topic
  + LF orgs are literal GitHub orgs (no mapping).

## PAUSED: enriched full-census re-pull `bwmti2ml3` (part-2 depth refinement)
Expanding part-2 (review depth) to full 50k scale. Re-pulls census search with a SUPERSET
node (adds `additions/deletions/changedFiles`, review `state`, `comments.totalCount`) →
`<scratchpad>/census_rich/{tid}.json`, 2,559 tasks (`enriched_tasks.tsv`: tid,repo,period,
range). Robust puller (array-validate + rate-limit-aware). ~3-4 hr. RESUMABLE: relaunch
skips valid-array cells.
- Time-in-review metrics ALREADY computed at full 50k (free, from existing census) — they
  CORRECTED the 120-sample overstatement (AI review→merge 1.7h vs 1.0h, not 5.9 vs 0.7;
  rounds 2.43 vs 2.35, not 3.7 vs 2.2). %human-review converged to parity Q2-2026 (48/46).
- ON COMPLETION: validate (0 corrupt; big repos full); recompute part-2 comment-depth
  (mean inline comments, %substantive via state∈{COMMENTED,CHANGES_REQUESTED} or comments>0),
  PR size, AI vs non by period at full scale. census_rich supersedes census/census_big for
  all metrics. Update `ai_code_review_comparison.md`.

## STATUS (part 1): COMPLETE (2026-06-28) — final result in `ai_code_census.md` §FINAL
Expansion done & validated: 2,070/2,070 cells, 0 corrupt, big repos hit ~500 (llama.cpp
Q1-2024 fixed 10→500). Merged dataset = 49,935 PRs. Final contributor-weighted: AI-code
0%→16%, automated review ~1%→33%, human review 60%→49%, Q1-2024→Q2-2026. No open data work.

## Uniform-500 expansion — DONE (robust puller `bna6em6fn`)
Pull up to 500 PRs **sampled uniformly across each quarter** (10 sub-windows × 50) for
the **207 repo-periods with >50 PRs** (79 distinct repos). 2,070 sub-window cells in
`<scratchpad>/census_big/`, named `{idx}_{period}_{subwin}.json` (idx→repo in
`data/resume_state/big_manifest.tsv`).

### BUG FOUND & FIXED (2026-06-28)
The first expansion runs (`bvvwk4ytf`, `b9vz7y8ja`) had a corruption bug: when the
GraphQL **hourly point budget** was exhausted, the API's `{"errors":[{"type":
"RATE_LIMIT"}]}` object was written *as the cell* (non-empty, so the retry/skip logic
treated it as done). 267/1,679 cells were corrupt error-objects → those repo-periods
showed wild undercounts (e.g. llama.cpp Q1-2024 got 10 PRs vs 857 real).
- **`census/` (clean 50-cap, 696 cells) is UNAFFECTED** — verified 0 corrupt. So the
  earlier N=1,914 contributor-weighted results STAND.
- Fix in `bna6em6fn`: (1) only write if response is a JSON **array** (`[`...); (2)
  `need_budget()` polls `gh api rate_limit` and sleeps until reset when graphql
  remaining <200, instead of a useless 20s retry; (3) skip only cells that are valid
  arrays (re-pull corrupt/missing). Corrupt cells were deleted before relaunch.

### To resume if interrupted
Relaunch `bna6em6fn`'s script (idempotent: skips valid-array cells, re-pulls the rest).
Then VALIDATE before trusting: (a) `head -c1` of every census_big cell is `[` (no `{`);
(b) big repos (weaviate, qdrant, llama.cpp, tt-metal) have ~500 PRs in active quarters,
cross-checked vs `data/resume_state/repo_pr_totals.tsv`.

## To resume (zero gaps)
1. **Relaunch the expansion** — re-run the `bvvwk4ytf` command (same script). It skips the
   1,585 existing `census_big/*.json` cells and fills the remaining ~485. ~20–30 min.
   - Work-list: `data/resume_state/big_tasks.tsv` (tid \t repo \t date-range).
   - Output dir: `<scratchpad>/census_big/` (named `{idx}_{period}_{subwin}.json`).
   - Manifest idx→repo,period: `data/resume_state/big_manifest.tsv`.
2. **Sanity-check** the output (avoid the earlier `census2` bug): confirm big repos
   (weaviate/weaviate, qdrant/qdrant, ggml-org/llama.cpp) have non-empty cells across
   their sub-windows.
3. **Merge + final analysis**: for each capped (repo,period) use the combined uniform-500
   from `census_big/`; for non-capped cells use `census/` (≤50). Then re-run the
   per-repo **equal-weight** and **contributor-weight** analysis by period vs the Q1-2024
   baseline (same code as the corrected run on 2026-06-27).

## Key data (durable, in repo)
- `data/ai_evidence_repos.csv` — 196 AI-evidence repos (175 product, 21 meta/demo tagged).
- `data/repo_contributors.csv` — core human contributors per repo (weighting).
- `data/resume_state/` — big_tasks.tsv, big_manifest.tsv, product_repos.txt, contributor +
  commit-trend tsvs (so resume works even if scratchpad is cleared; raw cells would re-pull).
- `artifacts/ai_code_census.md`, `ai_code_review_comparison.md`, `ai_commit_adoption_curve.md`.

## Scratchpad (session-scoped — raw pulls; regenerable if lost)
`/private/tmp/claude-501/-Users-ronbodkin-devel-ai-rd-analysis-worktrees/79657d3a-545d-4154-be12-65db47d9746e/scratchpad`
holds `census/` (clean 50-cap, 696 cells), `census_big/` (1,585 uniform cells), the tsvs.

## Current best findings (pre-expansion, contributor-weighted, clean census)
AI-code in PRs rose **0% (Q1-2024) → ~16% (Q2-2026)**; automated/bot PR review rose
**~1% → ~34%** while human review fell **57% → ~42%**; big teams adopt AI in a smaller
share than solo repos but review more. Trend robust across weightings. The expansion
refines the *levels* for the big team repos (better sampling), not the direction.
