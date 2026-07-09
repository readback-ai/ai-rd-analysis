# Methods

Methodology for the study of AI-assisted development practices at leading AI
organizations. Successor to the pre-pivot `PIPELINE_SPEC.md` and
`artifacts/scope_and_methods.md`; this document is canonical. Results live in
`artifacts/v2_results.md`; every module named here is in `src/pipeline/`.

## 1. Population: org-provenance, not repo classification

The unit of scoping is the ORGANIZATION. We do not classify repositories by
domain ("is this AI R&D?") — an earlier gold-set audit showed that boundary is
judgment-heavy and low-agreement (cheap rules matched human judgment 47%), and
hobbyist repos are not the object of study. Instead (`org_set.py`, stage 0):

1. **Candidate sources** — four third-party lists, snapshotted in
   `data/resume_state/v2/`: the LF AI & Data landscape (266 orgs), Hugging
   Face hub top organizations (114), GitHub AI-topic organizations (180), and
   a lab/startup list from TechCrunch's 2025 $100M+ AI funding round-up plus
   frontier labs of public prominence (47 carried into the final set;
   `v1_carryover.txt`, per-org category annotations). Our contribution to
   sourcing is TRANSCRIPTION, not membership judgment: mapping listed names to
   GitHub handles (e.g. Hugging Face's `laion` -> GitHub `LAION-AI`) and
   API-verifying them; `candidates.tsv` is the transcription record. Union:
   529 candidate orgs.
2. **Quality gate** — the org's flagship repository has ≥1,000 stars
   (`org_scale.tsv`): 364 orgs.
3. **AI-evidence keep** — the stage-1 marker scan found tool activity (≥5
   marker commits, or ≥0.1% of PRs for high-volume orgs): the frozen
   population `v2_active.txt`, **216 orgs**, of which 169 trace to the three
   public lists and 47 to the lab/startup list. Every active org traces to a
   source snapshot (`org_set.py --verify` reports the reconciliation).
4. **Repo enumeration** (`enum_repos.py`, stage 2) — inside active orgs, keep
   repos with detectable AI-tool commits under the same keep rule:
   **1,996 repos** (`census_repos.txt`).

**Flagship AI-topic gate (2026-07-09).** Generic ecosystem lists (LF AI &
Data landscape, GitHub topics) admit non-AI infrastructure orgs (kubernetes,
apache, trinodb). A two-tier admission rule fixes this without re-introducing
per-repo domain judgment: orgs on AI-SCOPED sources (TechCrunch $100M+ AI /
frontier-lab list, HF hub model publishers) are admitted by the source's own
scope; orgs whose only provenance is a generic list must pass a flagship
gate — >=2 of their top-10 starred repos carry maintainer-declared AI topics
(frozen 28-topic dictionary in `org_set.py`, anchored to GitHub's curated
topic vocabulary; "agents" deliberately excluded), or the #1 repo does
(single-product orgs, e.g. ollama), or the org login/description carries an
AI term (rescues topic-sparse AI orgs: flashinfer-ai, embeddings-benchmark).
Applied retroactively for consistency: 17 v2 orgs leave (trinodb, tikv,
MariaDB, dotnet, scipy...; also google/alibaba/Netflix, whose AI lives in
sibling orgs like google-deepmind — now admitted). Population v2.1 =
**255 orgs** (199 retained + 56 additions; `v21_active.txt`). The v2
216-org population remains the basis of §1-13 published numbers until v2.1
is re-baselined.

**Keep-rule re-audit (2026-07-08).** The original AI-evidence keep tested only
layer-A commit markers, and its scan window predated some orgs' adoption. A
layered re-audit of all 225 dropped-but-quality-gated (or v1-listed) orgs —
probing branch prefixes, agent authorship, and fresh markers for Q2-2026 —
found 110 now pass: 16 v1-listed AI labs regaining entry (google-deepmind,
xai-org, THUDM, replit, lm-sys...), 55 rescued only by layers B/C (ollama,
google-gemini, onnx... — confirming the marker-only keep was exclusionary),
and 39 late marker adopters that are mostly non-AI-core OSS foundations
(apache, elastic, grafana). The first two groups (**71 orgs, "v2.1
additions"**, `additions_orgs.txt`) are being enumerated and censused as an
extension stratum; the frozen 216-org population remains the basis of all
published numbers until the extension is re-baselined and reported
separately. The late-adopter group is deferred pending a population-scope
decision (adding apache/elastic shifts the object of study from "leading AI
organizations" toward "AI-ecosystem OSS at large").

Consequence for inference: the population is prominence-selected. Findings
describe practices at leading AI organizations; the Q1-2024 same-repo census
is the temporal control (pre-agentic baseline), not an external control group.

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
