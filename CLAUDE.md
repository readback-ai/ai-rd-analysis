# Working in this repo

Project: a fresh, queryable dataset of autonomous-coding-agent pull requests
scoped to AI research & development repositories. See `PROJECT_PLAN.md` (phasing)
and `PIPELINE_SPEC.md` (architecture). Phase 0 — defining "AI R&D repo" as a
tested classifier — gates all collection work.

## Parallel work via git worktrees

Multiple Claude Code sessions can work features in parallel. Each session runs in
its OWN worktree so no two sessions share a working tree.

Layout (worktrees live in a common dir alongside the repo under `~/devel`):

```
~/devel/ai-rd-analysis                       # main repo  (branch: main)
~/devel/ai-rd-analysis-worktrees/
    phase-0-definition                       # branch: phase-0-definition
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
- Python 3.14 + `uv` for envs/deps. `jq` available. `duckdb` CLI not yet installed
  (only needed from Phase 1; `pip install duckdb` or `brew install duckdb`).

## Data store (Phase 1+)

The DuckDB/Parquet store and `raw/` API cache are large and regenerable, so they
are gitignored. To avoid each worktree re-collecting, point all worktrees at one
shared store outside the trees (e.g. `~/devel/ai-rd-analysis-data/`) via an env
var / config, rather than a per-worktree `data/`. Decide the exact path when
Phase 1 starts.

## Commit trailer

End commit messages with:
`Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>`
