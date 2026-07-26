# Working in this repo

Project: a fresh, queryable dataset of **AI-assisted development practices at leading
AI organizations** — how top AI labs and well-funded AI startups use autonomous coding
agents / AI assistance in their public repos. See `README.md` (overview) and
`docs/METHODS.md` (methodology). **Pivoted 2026-06-26** from per-repo "AI R&D"
classification to **org-provenance scoping**: the tracked population is the org
enumeration built from third-party lists (`src/pipeline/org_set.py`; LF AI landscape +
HF top orgs + GitHub topics, quality-gated). Detection methodology = `src/pipeline/detect.py`
(single canonical home; the old agents.yaml was archived 2026-07-12 — it was
unused by code and disagreed with detect.py). Canonical docs: `README.md`,
`docs/METHODS.md`, results in `artifacts/results.md`.

## Bug fixes: reproduce with a failing test FIRST

When fixing any defect (including review findings): write a unit test that
REPRODUCES the issue and confirm it FAILS against the unfixed code, then
apply the fix and show the test passing. Never land a fix whose test was
only written (or only run) after the code change — the red run is the
evidence the test actually captures the bug. Name the review/finding in
the test docstring so the regression stays traceable.

## Parallel work via git worktrees

Multiple Claude Code sessions can work features in parallel. Each session runs in
its OWN worktree so no two sessions share a working tree.

Layout (worktrees live in a common dir alongside the repo under `~/devel`):

```
~/devel/ai-rd-analysis                       # main repo  (branch: main)
~/devel/ai-rd-analysis-worktrees/
    ai-dev-practices                         # branch: ai-dev-practices
    <feature>                                # branch: <feature>
```

Manage them with the helper:

```bash
scripts/worktree.sh new <name> [base]   # create worktree + branch (base default: main)
scripts/worktree.sh list
scripts/worktree.sh rm <name>           # remove worktree, keep branch
scripts/worktree.sh prune
```

Conventions:
- One worktree per in-flight feature; branch name == worktree dir name.
- Branch from `main` unless a feature builds on another branch.
- Commit on the feature branch; merge back to `main` via PR/merge when green.
- Keep `main` clean: shared specs, scripts, rubric, docs.

## Credentials & tooling

- GitHub: use `gh api ...` / `gh` — it inherits the keyring auth (no PAT env var
  needed). All Phase 0 calls are read-only.
- Python 3.11 (`.python-version`) + `uv` for envs/deps. `jq` available. `duckdb` CLI not yet installed
  (only needed from Phase 1; `pip install duckdb` or `brew install duckdb`).

## Data store (Phase 1+)

The DuckDB/Parquet store and `raw/` API cache are large and regenerable, so they
are gitignored. To avoid each worktree re-collecting, point all worktrees at one
shared store outside the trees (e.g. `~/devel/ai-rd-analysis-data/`) via an env
var / config, rather than a per-worktree `data/`. Decide the exact path when
Phase 1 starts.

## Commit trailer

End commit messages with a trailer naming the model that wrote the code:
`Co-Authored-By: Claude <model> <noreply@anthropic.com>`
e.g. `Claude Fable 5`, `Claude Opus 5 (1M context)`, `Claude Sonnet 5`.

## Agent skills

### Issue tracker

Issues live in this repo's GitHub Issues (`gh` CLI; PRs-as-request-surface off). See `docs/agents/issue-tracker.md`.

### Domain docs

Single-context: `CONTEXT.md` at the root + `docs/adr/`, created lazily; study vocabulary also lives in `docs/METHODS.md`/`docs/METRICS.md`/`docs/CODE_GUIDE.md`. See `docs/agents/domain.md`.
