# Agentic-PR Collection Pipeline, scoped to AI R&D repositories

## Spec version
v0.1, drafted 2026-06-24. Owner: Ron. Status: design, pre-build.

## Purpose
Re-collect agent-authored GitHub pull requests (the AIDev methodology) with fresh
data through the present, and reduce the universe to repositories whose primary
purpose is AI research and development. The output is a queryable store that
supports trend analysis of how autonomous coding agents contribute to AI R&D
codebases specifically.

This spec replaces AIDev's notebook ETL with a staged, resumable pipeline. It
keeps AIDev's schema where it works and extends it where it does not.

## Why re-collect rather than reuse AIDev
The published `hao-li/AIDev` parquet files freeze at the 2025-08-01 crawl. The repo's
recent activity is paper-writing, not data refresh. Every 2026 paper built on it,
including AgenticFlict, re-analyzes that same frozen snapshot (AgenticFlict states it
downloaded AIDev "as of 2026-01-05" and still reports the identical 932,791 PRs).
Volume has grown by an order of magnitude since the cutoff, so any current claim
needs fresh collection. AIDev's value to us is its method, not its data.

## Scope decision that gates everything: the AI R&D definition
This is the single most important design choice. Write it down before building.

Operational definition (recommended default, refine in Phase 0):
> A repository qualifies as AI R&D if its primary purpose is building, training,
> serving, evaluating, or researching machine-learning models or autonomous agent
> systems. Repositories that merely *consume* an AI API (for example an app that
> calls an LLM) do not qualify.

Two cuts to keep distinct:
- BUILDS-AI: training frameworks, inference/serving engines, eval harnesses, agent
  frameworks, model repos, research code. This is the target.
- USES-AI: product apps wrapping a model API. Excluded by default.

The boundary case to resolve in Phase 0: an `openai`/`anthropic` SDK dependency
alone is a USES-AI signal, while `torch`/`transformers`/`jax`/`vllm`/`deepspeed`
is a BUILDS-AI signal. Decide how to treat repos that have both.

Record the final rubric in `RUBRIC.md` and version it. Every trend claim is only
as defensible as this definition, so it ships with the dataset.

---

## Architecture: five resumable stages over a local store

Each stage reads its input from the store, writes its output back, and is
idempotent. Re-running a stage must never duplicate rows or re-pay for cached work.

```
Stage 0  Seed       agent PR search, date-windowed      -> raw_pr
Stage 1  Repos      unique repos, full metadata          -> repository
Stage 2  Classify   AI R&D relevance, layered + cached   -> repo_label
Stage 3  Hydrate    PR sub-resources for kept repos only -> pr_* tables
Stage 4  Derive     task-type + analysis marts           -> marts
```

Storage: DuckDB as the query layer over Parquet files on disk. One Parquet file
per table, partitioned by `agent` and by `created_at` month for the large tables.
DuckDB gives SQL joins across tables without loading everything into memory and
reads/writes Parquet natively. Keep raw API JSON responses in a separate
`raw/` cache (gzipped, keyed by endpoint + id) so re-derivation never re-hits the API.

State and idempotency: a `checkpoint` table records, per stage and per work unit
(date window, repo id, or PR id), whether it is done and the ETag/last-fetched
timestamp. Resumption reads checkpoints and skips completed units.

---

## Stage 0: Seed (agent PR search)

Goal: enumerate every agent-authored PR and its repo slug. No hydration yet.

Endpoint: `GET /search/issues` with `is:pr` plus a per-agent author filter, OR
the GraphQL `search` connection. Both share the same two hard limits, so the
windowing logic below is required either way.

Hard constraints (verified 2026-06-24):
- Search returns at most 1000 results per query, even with pagination.
- Search is rate-limited to 30 requests/minute, separate from the 5000/hr core budget.

Windowing strategy (mandatory):
- Loop per agent, per `created:YYYY-MM-DD..YYYY-MM-DD` window.
- Start with monthly windows. If a window returns >= 1000 results, bisect it
  (split the date range) and retry until every sub-window is < 1000. Persist the
  window boundaries so re-runs resume mid-bisection.
- Throttle to <= 30 search requests/min with jitter; honor `Retry-After`.

Agent identities (verify current handles at build time, they drift):
| Agent | Primary signal | Notes |
| --- | --- | --- |
| Devin | author `devin-ai-integration[bot]` | Later activity shifted to a `Co-Authored-By: devin-ai` commit trailer. Cover both. |
| GitHub Copilot | author `copilot-swe-agent[bot]` | Also surfaces as "Copilot". |
| Cursor | author `cursor[bot]` / `cursoragent` | |
| OpenAI Codex | Codex connector bot account | Cloud Codex agent; confirm the exact login in Phase 0, it is the least stable. |
| Google Jules | author `google-labs-jules[bot]` | Postdates the AIDev snapshot, new to this collection. |
| Claude Code | `Co-Authored-By: Claude <noreply@anthropic.com>` commit trailer | NOT a bot author. Author-search misses it. Requires commit-message scanning, see below. |

Claude Code caveat: because Claude Code commits as the human author, you cannot
find its PRs by author. AIDev's low Claude Code count (5,137) is almost certainly
this undercount. Options: (a) scan commit messages for the co-author trailer across
candidate repos, (b) accept the undercount and label it. Decide in Phase 0.
`botcommits.dev` is a useful cross-reference for current bot handles.

Output table `raw_pr`: one row per PR.
`pr_id, number, agent, repo_slug, repo_id, user_login, user_id, state,`
`created_at, closed_at, merged_at, html_url, title, body`.

---

## Stage 1: Repos (full metadata, including the fields AIDev dropped)

Goal: one metadata row per unique repo, with the fields needed to classify.

AIDev's `repository` table has `id, url, license, full_name, language, forks,
stars` and is missing `topics` and `description`, which are exactly the
classification signals. This stage re-fetches them.

Endpoint: `GET /repos/{owner}/{repo}`. Core budget 5000/hr. Use conditional
requests (`If-None-Match` with stored ETag) so refreshes are nearly free.

Output table `repository` (extends AIDev):
`id, full_name, owner_login, owner_type, description, topics[], language,`
`stars, forks, license_spdx, is_fork, archived, pushed_at, created_at, size_kb,`
`etag, fetched_at`.

Optional manifest pull (gate behind a flag, only for repos that pass Stage 2
rules 1-2 or reach the LLM tier): fetch root dependency manifests
(`requirements.txt`, `pyproject.toml`, `package.json`, `setup.py`,
`environment.yml`) via `GET /repos/{owner}/{repo}/contents/{path}`. Store raw,
parse in Stage 2.

---

## Stage 2: Classify (AI R&D relevance, layered, cached)

Goal: label each repo BUILDS_AI / USES_AI / NOT_AI with a reason, cheaply.

Run cheap rules first to auto-decide the clear cases, send only the ambiguous
residual to an LLM. Cache every decision keyed by `repo_id` so re-runs never
re-classify or re-pay tokens. Persist the rule version so you can invalidate
selectively when the rubric changes.

Layered classifier:

1. Org allowlist (auto-accept, high precision):
   owners such as `openai, anthropic, google-deepmind, huggingface, meta-llama,
   mistralai, EleutherAI, allenai, vllm-project, pytorch, NVIDIA, google-research`.
   Seed this list in Phase 0; treat membership as BUILDS_AI.

2. Topic match (strong accept / reject):
   accept on `machine-learning, deep-learning, llm, large-language-models,
   transformers, pytorch, tensorflow, jax, rag, llmops, mlops, agents,
   reinforcement-learning, neural-network, diffusion-models`.
   Topics are incomplete (many repos set none) and noisy (marketing tags), so
   treat as a positive signal, never a sole rejection.

3. Dependency signal (disambiguates BUILDS vs USES):
   BUILDS_AI if manifest imports `torch, transformers, jax, flax, vllm, deepspeed,
   accelerate, peft, trl, sentence-transformers, diffusers`.
   USES_AI-only if the sole AI dependency is `openai` / `anthropic` / `cohere`
   client SDKs with no training/serving stack.

4. LLM classification (ambiguous residual only):
   Feed `description + topics + README head (first ~2KB) + manifest summary` to a
   classifier with the `RUBRIC.md` definition inline. Require a structured output:
   `{label, confidence, reason}`. Sample and hand-audit ~100 decisions per run to
   track precision. Reuse AIDev's task_type LLM pattern.

Output table `repo_label`:
`repo_id, label, decided_by (rule1|rule2|rule3|llm), confidence, reason,`
`rule_version, decided_at`.

Keep set for Stage 3 = repos labeled BUILDS_AI (and USES_AI too if you decide to
retain it as a comparison cohort; recommended to keep it labeled rather than dropped,
so you can contrast agent behavior across the two).

---

## Stage 3: Hydrate (PR sub-resources, kept repos only)

Goal: for PRs in kept repos, fetch the full interaction history. This is where the
filtering pays off, since hydration is the expensive part.

Use GraphQL, not the seven-REST-endpoints-per-PR approach. One GraphQL query
returns a PR with commits, reviews, review threads/comments, issue comments,
timeline items, and closing issue references against the single 5000-point/hr
budget. This is the primary efficiency win of the rewrite.

Reference GraphQL query (one PR, paginate the inner connections as needed):

```graphql
query($owner:String!, $name:String!, $number:Int!) {
  repository(owner:$owner, name:$name) {
    pullRequest(number:$number) {
      id number title body state createdAt closedAt mergedAt
      additions deletions changedFiles
      author { login __typename }
      commits(first:100) {
        totalCount
        nodes { commit {
          oid message additions deletions changedFilesIfAvailable
          authors(first:10) { nodes { name user { login } } }   # catches Co-Authored-By
        } }
      }
      reviews(first:50) { nodes { author { login } state submittedAt body } }
      reviewThreads(first:50) { nodes { comments(first:50) {
        nodes { author { login } path diffHunk body createdAt }
      } } }
      comments(first:100) { nodes { author { login __typename } body createdAt } }
      closingIssuesReferences(first:10) { nodes { number title } }
      timelineItems(first:100, itemTypes:[
        LABELED_EVENT, REFERENCED_EVENT, CROSS_REFERENCED_EVENT,
        CLOSED_EVENT, MERGED_EVENT, REVIEW_REQUESTED_EVENT, ASSIGNED_EVENT
      ]) { nodes { __typename ... on LabeledEvent { createdAt label { name } actor { login } } } }
    }
  }
}
```

Notes:
- The `commit.authors` node surfaces `Co-Authored-By` trailers, which is how you
  recover Claude Code attribution that author-search missed in Stage 0.
- Paginate inner connections (`commits`, `reviewThreads`, etc.) when `totalCount`
  exceeds the page size. Budget points: roughly node-count based, so large PRs
  cost more. Batch small PRs, handle large ones individually.
- Cache raw GraphQL responses in `raw/`. Re-derive tables from cache, never re-query
  to fix a parsing bug.

Output tables (mirror AIDev names so its analysis notebooks still run):
`pr_commits, pr_commit_details, pr_reviews, pr_review_comments, pr_comments,`
`pr_timeline, related_issue`. Same column semantics as AIDev's `data_table.md`.

---

## Stage 4: Derive (marts)

- `pr_task_type`: LLM classification of PR title + commit messages into
  conventional-commit categories (`feat, fix, docs, test, refactor, chore`),
  reusing AIDev's approach.
- Analysis marts: PR-level table joining repo label, agent, task type, merge
  outcome, turnaround (merged_at - created_at), size (additions/deletions), and
  review counts. This is the table trend charts read from.
- A `human_pull_request` comparison cohort per kept repo (optional), so agent vs
  human contrasts hold the repo population fixed.

---

## Cross-cutting requirements

Auth and budget:
- Authenticated PAT or GitHub App. App installs raise the search ceiling per
  installation if volume demands it.
- Core REST/GraphQL: 5000 points/hr. Search: 30/min. Track remaining budget from
  response headers and back off proactively, do not wait for 403s.

Idempotency and provenance:
- Every stage keyed and checkpointed. Re-runnable from any point.
- Stamp every row with `fetched_at` and the collection `run_id`. Record the global
  collection window (earliest..latest `created_at`) in a `run_manifest` so the
  dataset's coverage is self-documenting and you never overstate recency again.

Validation gates (must pass before a run is "published" internally):
- Row-count sanity vs previous run (no silent halving).
- Classifier precision spot-check >= target (set in Phase 0, e.g. 0.9 on a 100-repo audit).
- Date-window coverage has no gaps per agent.
- Claude Code recovery rate reported, not silently zero.

Out of scope for v0.1: patch/diff redistribution (license-sensitive, AIDev masks
some), real-time streaming, non-GitHub forges.

## Open questions to close in Phase 0
1. Final AI R&D rubric and the BUILDS/USES boundary for dual-signal repos.
2. Exact current Codex and Copilot bot logins.
3. Whether to scan for Claude Code co-author trailers (cost vs completeness).
4. Whether USES_AI is retained as a comparison cohort or dropped.
5. Target classifier precision and audit sample size.
