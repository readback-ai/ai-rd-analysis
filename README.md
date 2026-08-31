# AI-Assisted Development Practices at Leading AI Organizations

An empirical study of how the organizations building AI use AI to build
software — measured from public GitHub metadata over 229 leading AI
organizations (182 full-org + 47 repo-scoped; 2,142 repositories) across
four quarters: Q1-2024 baseline, Q4-2025, Q1-2026, Q2-2026. **Study cutoff: 2026-06-30** — all activity data is windowed to the
cutoff; classification metadata is pinned as close to it as the API allows
(see METHODS §0).

## Abstract

We construct a population of leading AI organizations from third-party
sources (LF AI & Data landscape, Hugging Face hub rankings, GitHub AI topics,
TechCrunch's 2025 $100M+ AI funding list), enumerate their public
repositories with detectable AI-tool activity, and census pull requests in
four quarters spanning the agentic-coding transition. AI involvement is
detected in three independent layers: commit-forensic markers (co-author
trailers, generation footers, tool author/committer identities incl. a
committer-identity audit), agent bot authorship, and agent branch-naming
conventions; all per-PR events (merges, closes, reviews) follow an 8-week
window from PR creation, so mature classifications are immutable under
data refreshes. Findings (contributor-weighted unless noted): the primary
metric is AI INVOLVEMENT — the union of the three layers per PR — which
rose from 0% (Q1-2024) to 16.9% [14.9,18.7] of submitted PRs by Q2-2026
(pooled 17.1%; commit markers alone 13.8%); AI-involved PRs carry 22.4%
of submitted and 17.0% of merged LOC. A balanced-panel sensitivity
(15.6%) shows the growth is adoption, not cohort composition; the single
potential overcount (weak branch prefixes) is bounded two-sided at
0.11pp. Adoption is led by private companies (21.2%) over public (13.2%)
and community (12.3%). Volume: merged LOC per core contributor grew
×2.96 (6.5 → 19.1 kLOC/quarter, CW), driven entirely by AI-adopting
authors — non-adopters stayed flat — with event-time analysis showing a
discontinuity at each author's first AI evidence on a flat pre-trend,
in both their AI-marked AND unmarked output (the undetected-usage
signature). A new production mode emerged: ~43 "fleet operator" accounts
merging 300–4,400 PRs/quarter (~531 kLOC/author-month cohort mean by
Q2-2026), roughly half unmarked, isolated as their own cohort. Review:
human attention per merged line fell ~53% (insiders −61%) while
human-review coverage of merged PRs held (~69–75%) and responsiveness to
explicit human review asks stayed roughly stable (81.5% → 74.5%
provisional, HT-weighted) with post-ask LOC share rising 46% → 63%.
All rates are floors: squash-merge strips markers, and default local CLI
usage is structurally undetectable.

**Full results: [`artifacts/results.md`](artifacts/results.md) (regenerated) · metrics reference: [`docs/METRICS.md`](docs/METRICS.md) · working log: [`artifacts/v2_results.md`](artifacts/v2_results.md) ·
Methodology: [`docs/METHODS.md`](docs/METHODS.md) · **code review guide: [`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md)****

Generated report: [`artifacts/report_generated.md`](artifacts/report_generated.md)
(19 sections, quarterly; monthly twin `report_monthly.md`). Figures:
`artifacts/ai_usage.png` (traceable AI usage), `core_loc.png`
(merged LOC per core contributor), `fig4_adoption_cohorts.png` (adoption
cohorts incl. fleet).

## How to verify the three claims that matter

| question | where |
|---|---|
| How is data collected? | `src/pipeline/` stages 0–3c (below); every stage checkpoints raw cells to `$AIRD_DATA_DIR` and is idempotent/resumable |
| How is the population defined? | [`src/pipeline/org_set.py`](src/pipeline/org_set.py) + METHODS §1: five rules (candidates → quality → AI-developer identity → evidence → scope) + one override table. Inputs in `data/sources/`, outputs in `data/derived/population.tsv` |
| How is AI contribution & review detected? | [`src/pipeline/detect.py`](src/pipeline/detect.py) — the single home: three detection layers + review classification |
| How are metrics created? | [`src/pipeline/analyze.py`](src/pipeline/analyze.py) (census metrics, weighting, bootstrap CIs) and [`src/pipeline/studies/layers.py`](src/pipeline/studies/layers.py) (exact cross-layer decomposition) |
| How are orgs classified for appendix cuts? | METHODS §1b: developer-of-AI groups (topics-only + published adjudications in `data/sources/org_overrides.tsv`) and org-type (`data/sources/org_type.tsv`: public/private/community, ownership as-of cutoff) |

## Pipeline

| stage | module | what it does |
|---|---|---|
| 0 | `pipeline.org_set` | the five population rules over `data/sources/` -> `data/derived/population.tsv` |
| 1 | `pipeline.scan_orgs` | org-level AI-evidence scan (commit-marker search) |
| 2 | `pipeline.enum_repos` | repo enumeration inside AI-active orgs (keep rule: ≥5 marker commits or ≥0.1% of PRs) |
| 3a | `pipeline.precount` | batch PR-count denominators (aliased GraphQL) |
| 3b | `pipeline.census` | PR census: commits, reviews, sizes, authorship, headRefName, mergedBy |
| 3c | `pipeline.branch_scan` | branch-prefix PR counts per org×quarter (layer C) |
| — | `pipeline.pull_prs` | targeted hydration (mergedBy, comment authors, commit dates) + branch-PR sampling |
| 4 | `pipeline.analyze` | per-repo rates → contributor-weighted means + bootstrap CIs |
| 5 | `pipeline.studies.layers` | exact per-PR layered decomposition (B > A > C disjoint; union = ai_involved) |
| studies | `pipeline.studies.*` | one analysis = one module: paper figures, productivity/adoption cohorts, attention, fates, event study, responsiveness (HT-weighted), slices, layer-C precision |
| figures | `scripts/plot_all.py` (all), `scripts/plot_*.py` (one each) | each figure's plotted points -> `artifacts/data/<figure>.csv`, then the image is rendered from that table |
| monthly | `scripts/monthly_update.py` | incremental month ingestion (provisional-month revision + persistent month registry; `--revise-only` finalizes the revision window without collecting a partial target month) |
| monthly (scheduled) | `scripts/run_monthly_update.sh` | waits for a w8 finalization instant (`--at`), runs the update, logs to `data/derived/` |

## Reproduction

```bash
uv sync
uv run pytest -q
uv run python -m pipeline.org_set --verify   # population reconciliation
# The raw census store ($AIRD_DATA_DIR) is not in this repo (large; contains
# commit metadata) — available on request; analyze/studies FAIL loudly
# without it rather than printing empty reports. With the store present:
uv run python scripts/regenerate.py          # full pipeline -> artifacts/report_generated.md
PYTHONPATH=src uv run python scripts/report.py --granularity month   # monthly twin
PYTHONPATH=src uv run python scripts/plot_all.py                     # every figure
                                                                     # + artifacts/data/*.csv
# re-render from the committed tables (no census store needed):
PYTHONPATH=src uv run python scripts/plot_all.py --from-tables --format png,svg
```

To review the code, start with [`docs/CODE_GUIDE.md`](docs/CODE_GUIDE.md) —
reading order, module tour, invariants, and a claim → module map.

Collection from scratch is ~36h wall-clock (GitHub API rate-limit bound) via
stages 0→5 in order; every stage resumes from checkpoints after interruption.

## Data & caveats (short form)

Population is prominence-selected (leading AI orgs), so findings describe
practices *at these organizations*, not GitHub at large; the Q1-2024
same-repo baseline is the temporal control. Detection is evidence-based and
therefore a floor. Weighting is contributor-weighted throughout (repo-size
gradients make pooled/equal-weight rates differ; see v2_results §7). Full
caveats in `docs/METHODS.md`.
