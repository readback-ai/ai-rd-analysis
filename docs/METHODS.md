# Methods

(Metric-level definitions and the generated-report layout live in
[`METRICS.md`](METRICS.md).)

Methodology for the study of AI-assisted development practices at leading AI
organizations. Successor to the pre-pivot `PIPELINE_SPEC.md` and
`artifacts/scope_and_methods.md`; this document is canonical. Results live in
`artifacts/v2_results.md`; every module named here is in `src/pipeline/`.

## 0. Study cutoff and as-of policy

The study cutoff is **2026-06-30** (end of Q2-2026).
- **Activity data** (PRs, commits, reviews, branch-prefix counts) is strictly
  windowed: every query carries `created:<=2026-06-30` bounds. Collection ran
  2026-07-01..09, so review/merge events landing after collection are
  censored (mild recency effect on the last quarter, noted in §6).
- **Classification metadata** (repo topics, descriptions, star counts,
  org descriptions) has no historical API — it was observed 2026-07-07..09,
  as close to the cutoff as possible, and applied uniformly to all orgs. Drift
  over those days is assumed negligible; the observation date is recorded in
  each snapshot file.
- **Ownership** (org-type cut) is pinned as-of the cutoff: e.g. xai-org
  counts as public (SpaceX acquisition + IPO completed before the cutoff).
- **Contributor weights** are all-time counts at pull date (known limitation,
  §6): GitHub does not expose windowed contributor statistics cheaply.

## 1. Population: five rules, one override table

The unit of scoping is the ORGANIZATION; per-repo domain classification is
deliberately avoided (an early audit showed the "is this AI R&D?" boundary is
judgment-heavy: cheap rules matched human judgment 47%). The population is
produced by `pipeline.org_set` from the inputs in `data/sources/` and the
scans in `data/derived/`; output is `data/derived/population.tsv` with a
scope and a one-word reason per org.

**R1 — Candidates.** Union of five third-party lists (snapshots and handle
transcriptions in `data/sources/`): the LF AI & Data landscape, Hugging Face
hub top organizations, GitHub AI-topic organizations, **Epoch AI's
notable-models organizations** (epoch.ai, CC-BY; `epoch_org_map.tsv` is the
name->handle transcription), and TechCrunch's 2025 $100M+ AI funding
round-up (`techcrunch_ai_orgs.tsv`, rote transcription). A **declared
hand-curated remainder** (`curated_orgs.tsv`, ~33 labs on neither Epoch nor
TechCrunch — mostly Chinese labs whose models Epoch attributes to parent
companies, and labs too new to have a notable model) is stated plainly as
curation.

**R2 — Quality.** Flagship repository >=1,000 stars. Members of the
AI-developer lists (Epoch/TechCrunch/curated) are exempt: those lists
already vet significance via notable models or $100M+ funding.

**R3 — AI-developer identity.** An org is an AI DEVELOPER iff it is on an
AI-developer list OR >=2 of its top-5 starred repos carry maintainer-declared
AI topics (frozen dictionary `AI_TOPICS` in `org_set.py`). Descriptions and
name heuristics are deliberately NOT used: maintainers SEO their metadata
("AI-powered" secrets scanners self-tag `llm-training`), and topics-only plus
lists proved the robust combination.

**R4 — Evidence.** >=5 AI-evidence PRs/commits in the MAXIMUM single
evidence source (marker scan, layered recheck, branch counts, or census-
derived union — maxima avoid double-counting one PR across sources), or
>=0.1% of the org's censused PRs; windows all <= cutoff. An org with no measurable AI-tool footprint contributes
nothing to AI-practice metrics and only noise to denominators.

**R5 — Scope.** AI developers enter FULL-ORG, except the declared
conglomerate umbrellas (`conglomerates.txt`: google, microsoft, alibaba,
apple, apache, ...) which enter REPO-SCOPED — only their AI-topic repos
count, as a labeled stratum. Dedicated AI subsidiaries (google-deepmind,
bytedance-seed) are separate GitHub orgs and enter on their own merits.
Non-developers with a >=1k-star AI-topic flagship also enter repo-scoped
(this uniformly covers single-product orgs like ollama). Everything else is
out.

**Overrides** (`org_overrides.tsv`, published, one line of rationale each):
12 excluded AI-USERS whose metadata is AI-washed (gitleaks, meilisearch,
daytonaio, streamlit, datahub-project, ...) and 3 included topic-sparse AI
developers (flashinfer-ai, embeddings-benchmark, AnswerDotAI). Exclusion
beats every rule; inclusion asserts R3 only (quality/evidence still apply).

Result (2026-07-10 run): **229 orgs = 182 full-org + 47 repo-scoped** (`population.tsv` is authoritative; docs quote it).
Consequence for inference: the population is prominence-selected; findings
describe practices at leading AI organizations, with the Q1-2024 same-repo
census as the temporal control.

Repo-level population: full-org members contribute repos passing the same
R4 evidence rule (`enum_repos.py`); repo-scoped members contribute their
AI-topic repos. Appendix cuts (org-type public/private/community via
`org_type.tsv`; adoption-intensity groups) re-use these same source files.

## 2. Detection: three independent layers (`detect.py`)

**Layer A — commit markers** (commit-forensic, strongest evidence). Co-author
trailers and generation footers (Claude Code: `noreply@anthropic.com`,
`Generated with [Claude Code]`; Cursor: `cursoragent@cursor.com`; aider
trailer), and tool author/committer identities (Codex cloud's
`chatgpt-codex-connector[bot]` committer, `codex@openai.com`). Two frozen
marker sets: v1 (Claude+Cursor — all published headline numbers) and v2
(+aider, +Codex; headline delta +0.1pp). Search-side rule: co-author trailers
are only findable by BARE-TERM commit search — the `author-email:` qualifier
matches primary authors only and returns zero for co-authored commits
(measured ~10–16× undercount). Qualifier terms remain correct for tools that
ARE the author/committer.

**Layer B — agent PR authorship.** PRs authored by coding-agent bot accounts
(Copilot coding agent, Devin, Jules, Codegen, Cursor cloud, Claude GitHub
app...). These carry no trailer; the author is the tool.

**Layer C — branch prefixes** (PR-level, PRarena-style). Agent web/cloud
flows create head branches `codex/*`, `copilot/*`, `cursor/*`, `claude/*`
while commits carry USER identity — invisible to layers A and B. History:
we initially REJECTED `head:codex/` for commit attribution (false positives:
human-typed branch names; false negatives: Codex CLI leaves zero commit
evidence — confirmed by an OpenAI maintainer, openai/codex#9449). At PR level
in this population the signal proved clean and large: exactly 0 prefix-named
PRs in Q1-2024 (before the products existed — the built-in false-positive
check) vs 3.8% of population PRs by Q2-2026. Layer C is reported as
PR-level attribution, never commit-level proof.

**Layer overlap** is measured, not assumed, on org-stratified samples
(`pull_prs.sample_branch_prs`): A∩C ≈ 2% for codex/; B∩C is high for
copilot/ (the bot authors those PRs). `integrate.py` combines layers
disjointly: total AI involvement = A + B + (C minus measured overlaps).

**Review classification.** A PR is HUMAN-REVIEWED only if a User-typed
account other than the PR author submitted a formal review object (GitHub
permits self-review-comments; counting them inflated the self-merge lane —
correction documented in v2_results §11c, aggregate impact ≤2.2pp). AI review
= reviewer in the `AI_REVIEWERS` bot list (gemini-code-assist, coderabbitai,
greptile-apps, copilot-pull-request-reviewer, ...), decomposed from other CI
bots. Substantive review = inline comments or a non-approve state.

**What is undetectable** (all rates are floors): squash-merge strips trailers
(asymmetrically — Claude's footer survives squash more often, so non-Claude
tools are likelier undercounted); local tools with default settings
(Windsurf, Codex CLI, Copilot in-IDE) leave no public metadata; in-session
review (reading agent diffs before accepting) is invisible except through
residue (v2_results §11d–e).

## 3. Census design (`precount.py`, `census.py`)

For each of 1,996 repos × 4 quarters (Q1-2024, Q4-2025, Q1-2026, Q2-2026 —
full quarters): denominators via batched aliased-GraphQL counts; PR nodes via
the search API. Repo-periods with ≤50 PRs are fully censused in one call;
larger ones are sampled by splitting the quarter into ≤10 uniform date
sub-windows of ≤50 PRs each (uniform-over-time; integer boundary math —
float rounding produced inverted windows). Collected-vs-total is compared and
undercounts WARN — silent truncation is how a census becomes a biased sample.
Fields per PR: commits (messages, author emails, committer), formal reviews
(author, type, state, inline-comment counts), author association, size,
timestamps, and (from 2026-07-08) headRefName + mergedBy. Coverage:
7,953/7,984 repo-periods (99.6%), 26,819 cells, 0 corrupt.

Per-repo-period completeness: sub-window counts adapt to PR volume and
paginate within windows (up to 1,000 PRs/day); a repo-period that still
cannot be completed FAILS rather than silently truncating. Per-PR field
caps remain: the census fetches each PR's first 12 commits and 15 reviews
(no per-PR pagination — one search call per ~45 PRs is what makes a
2,000-repo census feasible). Consequence: a marker appearing only after a
PR's 12th commit, or a review after the 15th, is unobserved. Both
truncations bias DOWNWARD (consistent with the floor framing); PRs with
>12 commits are a small minority and markers typically recur across a
session's commits.

Durability rules (`ghx.py`): every response is shape-validated before being
written (GitHub serves rate-limit error bodies that naive checks store as
data — this corrupted 267 cells once); failed calls are never recorded as
zero; cell keys include every content-determining parameter; the store lives
outside the worktree in `$AIRD_DATA_DIR`.

## 4. Metrics and weighting (`analyze.py`, `integrate.py`)

Per-repo-period rates over PRs (repos need ≥10 PRs/period to qualify), then
**contributor-weighted** means across repos: weight = the repo's core human
contributors (≥10 commits, bots excluded; `repo_contributors_v2.csv`).
Contributor weighting answers "what does the typical AI-org developer's PR
flow look like"; pooled and equal-weight variants differ through a repo-size
gradient (small repos are AI-heavier: 19.5% vs 12.2% AI-code in the smallest
vs largest quartile) and are reported only as reconciliation views.
Uncertainty: bootstrap 95% CIs over repos (2,000 resamples).

Cross-layer integration weights census-based and sample-based components by
their population PR counts, corrects layer C for measured marker/bot-author
overlap per prefix, and never silently assumes an overlap where no sample
exists. Org adoption thresholds add the org's branch share to its
contributor-weighted marker rate (upper-bound union approximation, flagged).

Accountability metrics (studies/accountability.py): self-merge =
mergedBy == author; one-person accountability = self-merged with no
other-human formal review and no other-human comment; GitHub forbids formal
self-approval, so a second-human merge is treated as tacit review.

## 5. Reproducibility

All stages are checkpointed, idempotent, and resume-safe; collection was
~36h wall-clock under rate limits with zero data loss across interruptions.
Studies use seeded sampling (published draws reproduce exactly); their
API-hydration steps re-pull live state. 84 unit tests cover storage
semantics, window math, detection, weighting, and integration math.
Verification after the 2026-07-08 restructure: the headline contributor-
weighted AI-code series reproduces exactly (0.0 / 1.7 / 7.7 / 11.5%).

## 6. Known limitations

- **Floors, asymmetric across tools** (§2). The Codex marker floor (0.15% of
  PRs) vs its branch-level rate (3.6%) shows the gap can be ~24×.
- **Prominence-selected population**; no claim about GitHub at large.
- **Q2-2026 mild recency censoring** (collected ~1 week after quarter end;
  late reviews/merges undercounted).
- **Contributor counts are all-time**, not window-scoped.
- **31 repo-periods (0.4%) permanently inaccessible.**
- **Branch-PR samples are first-page (created-desc) per org-quarter** — mild
  within-quarter recency bias.
- **Insider classification** (authorAssociation) misses staff whose org
  membership is private — several "external" substantial-PR authors are
  founders (v2_results §10 caveat).
- **In-session review is unobservable**; §11d–e measure only its residue.
