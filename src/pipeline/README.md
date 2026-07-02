# Pipeline: AI-assisted-development practices at leading AI orgs

Four checkpointed, idempotent stages. All raw pulls go to a durable store
outside the worktree (`$AIRD_DATA_DIR`, default `~/devel/ai-rd-analysis-data`)
so session/scratchpad loss never costs collected data. Re-running any stage
skips cells that already validate; failed cells are retried on the next run.

```
PYTHONPATH=src python3 -m pipeline.scan_orgs  --orgs data/resume_state/v2/v2_active.txt \
    --quarters Q1-2024 Q4-2025 Q1-2026 Q2-2026 --out scan.tsv
PYTHONPATH=src python3 -m pipeline.enum_repos --orgs active_orgs.txt --out repos.tsv
PYTHONPATH=src python3 -m pipeline.census     --repos repos.tsv
PYTHONPATH=src python3 -m pipeline.analyze    --bootstrap 2000
```

| stage | what | raw cells |
|---|---|---|
| `scan_orgs` | AI-marker commit counts per org x period (bare-term search) | `raw/scan_orgs/` |
| `enum_repos` | AI-evidence repos per org (paginated marker hits by repo) | `raw/enum_repos/` |
| `census` | PR nodes (commits+reviews+assoc+size); full census <=cap, else uniform date sub-windows | `raw/census/` |
| `analyze` | per-repo rates -> equal- & contributor-weighted means + bootstrap 95% CIs; bot review decomposed into `ai_review` vs `other_bot_review` | (reads cells) |

Encoded lessons (why this code looks the way it does — evidence in
`artifacts/agent_detection_cues.md` and `artifacts/RESUME.md`):
- **Bare-term commit search**, never the `author-email:` qualifier (misses
  co-authored commits org-scoped; 10-16x undercount).
- **Validate response shape before writing a cell** — GitHub returns
  `{"errors":[{"type":"RATE_LIMIT"}]}` bodies that once corrupted 267 cells.
- **Sleep to the advertised GraphQL reset** when the point budget runs low;
  fixed short retries just burn attempts against an hourly window.
- **Uniform date sub-windows** for big repo-periods (most-recent-N has
  window-tail bias); per-month/window caps stop mega-repos dominating.
- Marker sets are versioned: `v1` (Claude + Cursor; all published Phase-0
  numbers) and `v2` (adds aider, Codex committer/email) — run both to
  quantify the detection delta before switching headlines (review gap P1.5).
