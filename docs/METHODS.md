# Methods

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

**Admission rules layered on the base pipeline** (chronological order of
adoption; all applied retroactively so the final population is
rule-consistent; every input/output file is in `data/resume_state/v2/`):

5. **Keep-rule re-audit** (fixes a detection artifact). The original
   AI-evidence keep tested only layer-A commit markers with an early scan
   window. A layered re-audit of all 225 dropped-but-quality-gated (or
   v1-listed) orgs — branch prefixes, agent authorship, fresh markers, all
   windowed to the cutoff — found 110 passing: 16 v1-listed labs regaining
   entry (google-deepmind, xai-org, THUDM...), 55 rescued only by layers B/C
   (ollama, google-gemini, onnx...), 39 late marker adopters (mostly
   generic-OSS foundations). Groups 1+2 = the "v2.1 additions"
   (`additions_orgs.txt` -> gated -> `additions_orgs_gated.txt`).
   Files: `recheck_orgs.txt`, `recheck_scan.tsv`.
6. **Flagship AI-topic gate** (fixes generic-list leakage: kubernetes,
   apache, trinodb arrived via the LF AI & Data landscape / GitHub topics).
   Two-tier admission: orgs on AI-SCOPED sources (TechCrunch/frontier v1
   list) are admitted by the source's own scope; orgs whose only provenance
   is a generic ecosystem list must pass: >=2 of top-10 starred repos carry
   maintainer-declared AI topics (frozen dictionary `AI_TOPICS` in
   `org_set.py`), OR the #1 repo does (single-product orgs), OR the org
   login/description carries an AI term (rescues topic-sparse AI orgs).
   Validated before adoption: probe separated kubernetes 0/10, apache 1/10,
   elastic 0/10 from deepmind 4/10, onnx 6/10, intel 3/10.
   Source-override false-positive analysis: TechCrunch/frontier list FP 2-3%
   (replit) — adopted; HF-publisher list FP ~50% of promotions (microsoft,
   apple, awslabs) — rejected as an override.
   Applied retroactively: 17 v2 orgs leave (`v21_retro_dropped.txt`).
   Files: `flagship_gate.tsv`.
7. **Tier-2 repo-scoped orgs** (recovers big-tech AI units). A gate-failed
   org with >=2 AI-topic repos of >=1k stars re-enters with ONLY its
   AI-topic repos (full pagination), censused as a labeled stratum: google
   (adk-python, langextract...), alibaba (MNN...), apache (airflow, tvm...),
   dotnet, IBM, Netflix. Org-level adoption stats flag the stratum — a
   repo-scoped org's rate describes its AI unit, not the company.
   Files: `repo_scope_scan.tsv`, `tier2_orgs.txt`, `tier2_repos.txt`.

**Resulting populations.**
- **v2 (frozen)**: 216 orgs / 1,996 repos — the basis of v2_results §1-13.
- **v2.1**: 255 orgs (199 retained + 56 gated additions; `v21_active.txt`,
  `v21_repos.txt`) + 6 tier-2 repo-scoped strata (338 repos). Re-baseline
  check: the headline CW AI-code series moves 11.5% -> 11.3% (Q2-2026) —
  the findings are not composition artifacts.

## 1b. Appendix segmentations (reviewable classification layers)

Two labeled cuts for appendix reporting, both orthogonal to admission:

**Developer-of-AI groups** (v2_results §14b). The study's object is
organizations that DEVELOP AI; orgs that merely USE AI to build non-AI
products (vscode-class work) are segmented out. Because maintainers SEO
their metadata with AI terms (a secrets scanner self-tags `llm-training`),
no single field decides this: repo AI-ness = maintainer TOPICS only
(descriptions dropped after measured over-promotion), org grouping =
- AI-majority: v1-listed OR >=3 of top-5 starred repos topic-AI OR
  adjudicated single-product AI developer;
- AI-heavy: exactly 2 of top-5;
- repo-scoped: the rest — only their AI-classified repos count.
The ~40 single-product borderline orgs carry a PUBLISHED one-line
adjudication each (`single_product_adjudication.json`): 30 AI-developers
(ollama, dify, litellm, AutoGPT...), 11 AI-users demoted (gitleaks,
meilisearch, streamlit, daytonaio...). Files: `top5_topics.jsonl`,
`org_groups.json`, `group_*_repos.txt`.

**Org-type cut** (v2_results §15). Ownership as-of the cutoff, hand-
classified into a published table (`org_type.tsv`): public (38) / private
(179) / community (44; foundations, academic labs, nonprofits).
Subsidiaries and research arms take the parent's type (google-deepmind ->
public; ray-project -> Anyscale -> private).

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
