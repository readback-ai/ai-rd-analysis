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
trailers, generation footers, tool committer identities), agent bot
authorship, and agent branch-naming conventions. Findings (contributor-
weighted unless noted): The primary metric is AI INVOLVEMENT — the union of
the three layers per PR — which rose from 0% (Q1-2024) to 16.6%
contributor-weighted (16.6% pooled) of PRs by Q2-2026; commit markers alone
reach 13.6%. A balanced-panel sensitivity (15.3%) shows the growth is
adoption, not cohort composition. Among these (by construction AI-active) organizations, adoption is
broad, led by private companies (18.5%) over public (11.9%) and community
(10.0%). Human review declined ~10pp everywhere while its LEVEL follows
governance (community 62% > public 53% > private 47%); AI review deployment
is uniform (~20-26%). Self-merge rates are flat over time and cultural in
level (private 56% > labs 52% > public 50% > community 38%); AI concentrates
modestly in self-merged PRs (1.1-1.4x). On complete merged-by data,
self-merged AI-involved PRs are human-reviewed at similar-or-higher rates
than non-AI ones in most slices — an earlier sampled finding of a review
collapse characterized the pooled mass of a few high-volume repos, not the
typical repo; the one slice where self-merged AI code IS reviewed less is
research labs (46 vs 55%). Delegated-agent lanes move the human gate from
line-level review to merge triage (38% of codex-branch PRs merge vs 68%
baseline). All rates are floors: squash-merge strips markers, and default
local CLI usage is structurally undetectable.

**Full results: [`artifacts/results.md`](artifacts/results.md) (regenerated) · metrics reference: [`docs/METRICS.md`](docs/METRICS.md) · working log: [`artifacts/v2_results.md`](artifacts/v2_results.md) ·
Methodology: [`docs/METHODS.md`](docs/METHODS.md)**

## How to verify the three claims that matter

| question | where |
|---|---|
| How is data collected? | `src/pipeline/` stages 0–3c (below); every stage checkpoints raw cells to `$AIRD_DATA_DIR` and is idempotent/resumable |
| How is the population defined? | [`src/pipeline/org_set.py`](src/pipeline/org_set.py) + METHODS §1: five rules (candidates → quality → AI-developer identity → evidence → scope) + one override table. Inputs in `data/sources/`, outputs in `data/derived/population.tsv` |
| How is AI contribution & review detected? | [`src/pipeline/detect.py`](src/pipeline/detect.py) — the single home: three detection layers + review classification |
| How are metrics created? | [`src/pipeline/analyze.py`](src/pipeline/analyze.py) (census metrics, weighting, bootstrap CIs) and [`src/pipeline/integrate.py`](src/pipeline/integrate.py) (cross-layer union) |
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
| 5 | `pipeline.integrate` | layered union (marker ∪ agent-author ∪ branch-only) with measured overlap corrections |
| studies | `pipeline.studies.*` | reproducible analyses behind v2_results §10–12 (accountability, review-mode residue, corpora) |

## Reproduction

```bash
uv sync
uv run pytest -q
uv run python -m pipeline.org_set --verify   # population reconciliation
# The raw census store ($AIRD_DATA_DIR) is not in this repo (large; contains
# commit metadata) — available on request; analyze/integrate FAIL loudly
# without it rather than printing empty reports. With the store present:
uv run python scripts/regenerate.py          # full pipeline -> artifacts/report_generated.md
```

Collection from scratch is ~36h wall-clock (GitHub API rate-limit bound) via
stages 0→5 in order; every stage resumes from checkpoints after interruption.

## Data & caveats (short form)

Population is prominence-selected (leading AI orgs), so findings describe
practices *at these organizations*, not GitHub at large; the Q1-2024
same-repo baseline is the temporal control. Detection is evidence-based and
therefore a floor. Weighting is contributor-weighted throughout (repo-size
gradients make pooled/equal-weight rates differ; see v2_results §7). Full
caveats in `docs/METHODS.md`.
