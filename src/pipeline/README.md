# Pipeline: AI-assisted-development practices at leading AI orgs

Checkpointed, idempotent stages organized around three verifiable questions:
how data is collected (stages 0-3c), how AI contribution/review is detected
(`detect.py` — the single home), and how metrics are created (`analyze.py`,
`studies/`). All raw pulls go to a durable store
outside the worktree (`$AIRD_DATA_DIR`, default `~/devel/ai-rd-analysis-data`)
so session/scratchpad loss never costs collected data. Re-running any stage
skips cells that already validate; failed cells are retried on the next run.

The end-to-end path is `scripts/regenerate.py` (staged, resumable). The
stages it drives, runnable individually:

```
uv run python -m pipeline.org_set                   # -> data/derived/population.tsv
uv run python -m pipeline.enum_strata               # repo-scoped orgs' AI repos
uv run python -m pipeline.precount --repos data/derived/population_repos.txt
uv run python -m pipeline.census   --repos data/derived/population_repos.txt
uv run python -m pipeline.branch_scan               # layer-C org counts (evidence)
uv run python -m pipeline.analyze  --repos data/derived/population_repos.txt \
    --contributors data/derived/repo_contributors_window.csv --bootstrap 2000
uv run python -m pipeline.studies.layers            # exact layer decomposition
```

| stage | what | raw cells |
|---|---|---|
| `org_set` | population from third-party lists + quality gate; verifies frozen set | (reads snapshots) |
| `scan_orgs` | AI-marker commit counts per org x period (bare-term search) | `raw/scan_orgs/` |
| `enum_repos` | AI-evidence repos per org (paginated marker hits by repo) | `raw/enum_repos/` |
| `census` | PR nodes (commits+reviews+assoc+size+headRefName+mergedBy); adaptive sub-windows + cursor pagination, atomic writes, fail-hard on saturation | `raw/census-v2/` |
| `enum_strata` | AI-topic repos of repo-scoped orgs (full pagination, DONE sentinels) | TSV append |
| `contributors` | window-scoped contributor weights (Q4-2025..Q2-2026 active core) | CSV |
| `branch_scan` | branch-prefix PR counts per org x quarter (detection layer C) | TSV append |
| `pull_prs` | targeted PR hydration + org-stratified branch-PR samples | JSON cells |
| `analyze` | per-repo rates -> equal- & contributor-weighted means + bootstrap 95% CIs; bot review decomposed into `ai_review` vs `other_bot_review` | (reads cells) |
| `studies.layers` | exact per-PR layer decomposition (B > A > C, union = ai_involved) on the population manifest | (reads cells) |
| `studies/*` | slices (6 populations, self-merge, balanced panel), layer-C precision, behavioral studies | (reads cells + API) |

Encoded lessons (why this code looks the way it does — evidence in
`artifacts/agent_detection_cues.md`):
- **Bare-term commit search**, never the `author-email:` qualifier (matches
  primary authors only: zero results for co-authored commits org-scoped,
  ~3x undercount globally).
- **Validate response shape before writing a cell** — GitHub returns
  `{"errors":[{"type":"RATE_LIMIT"}]}` bodies that once corrupted 267 cells.
- **Sleep to the advertised GraphQL reset** when the point budget runs low;
  fixed short retries just burn attempts against an hourly window.
- **Uniform date sub-windows** for big repo-periods (most-recent-N has
  window-tail bias); per-month/window caps stop mega-repos dominating.
- One canonical marker set (`detect.MARKERS`); scan/enum cache keys carry
  a content fingerprint so marker changes invalidate stale caches
  automatically.
