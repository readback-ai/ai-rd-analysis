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
describe practices at leading AI organizations, with the Q1-2024 census as
the temporal control.

Repo-level population: full-org members contribute repos passing the same
R4 evidence rule (`enum_repos.py`); repo-scoped members contribute their
AI-topic repos. Appendix cuts (org-type public/private/community via
`org_type.tsv`; adoption-intensity groups) re-use these same source files.

## 1c. Incremental monthly updates (runbook)

`scripts/monthly_update.py YYYY-MM` adds a month of activity data:
1. RE-COLLECTS the previous month first (wipes its census cells) — the
   provisional-month revision: reviews and merges lag PR creation, so the
   newest month is always preliminary until the following update.
2. Collects the new month (precount + census; months are first-class period
   tokens via `scan_orgs.resolve_period`).
3. Prints the monthly trend tables (`analyze --granularity month`,
   2-PR/month floor ≈ the 5-PR/quarter threshold per unit time).
Population and classification metadata stay FROZEN between deliberate
revisions so month-over-month movement reflects practice, not population
churn. Quarterly regeneration (`scripts/regenerate.py`) remains the
canonical headline path.

## 1d. FROZEN methodology conventions (every paper number obeys these)

1. **Censoring rule**: all per-PR outcomes are measured at 8 WEEKS from PR
   creation (`detect.W8_DAYS`; maturity curves show merges quiesce at w8,
   98-99% of eventual). Fates close at w8, with w26 as appendix sensitivity
   (`studies.fates`). Immature PRs carry no fate (None-skip) — trailing
   quarters are PROVISIONAL and labeled; Q2-2026 finalizes with a re-pull
   on/after 2026-09-01 (8 weeks past quarter end; runbook §1c).
2. **Matched-horizon-only fate comparisons**: "ever resolved" is a
   different quantity per cohort and must never be compared across cohorts.
3. **Primary attention measure = HUMAN comments/kLOC** (bot comments
   excluded by construction: `detect.split_reviews` drops Bot-typed AND
   User-typed bot accounts, `is_bot_login`, pinning test). Window
   hours/kLOC corroborates, never leads. Size-band decomposition separates
   within-size thinning from composition (`studies.attention`).
4. **Weighting labeled on every number**: contributor-weighted primary
   (active-window weights), pooled secondary. Marker set v2 everywhere.
5. **Layer-C hygiene**: CI-canary false-positive class excluded (pinning
   test); per-prefix provenance precision stated (§2); the ai_involved
   series carries its two-sided weak-prefix bound as a standing report
   section — the single quantified exception to the floors framing.
6. **Q1-2024 caption** on every table where the column appears:
   detector-validity check and review-practice baseline, not an AI-usage
   estimate.
7. **Determinism & completeness**: seeded bootstrap (20260630, 2,000
   draws), seeded samples, SHA-256 manifest, fail-hard on incomplete or
   invalid cells, gap-free coverage gate with documented waivers.

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

**Measured layer-C precision** (org-stratified samples, C-only PRs — no
marker, no agent author; `studies.layer_c_precision`): the share carrying
positive provenance signals (GitHub web-flow committer = agent cloud flow,
or the product's machine-generated slug pattern) is codex/ 95%, copilot/
98%, cursor/ 49%, claude/ 42%. One false-positive class was MEASURED and is
EXCLUDED from detection: branches named after the product but committed
entirely by github-actions[bot] (CI canaries; 18.4% of C-only claude/
samples). The remainder (cursor/ 51%, claude/ 39%) is INDETERMINATE:
user-pushed commits on a prefix branch are consistent both with an agent
branch continued locally (true positive) and a human-named branch (false
positive); the Q1-2024 zero shows no pre-product baseline of such naming,
but fame-driven naming can grow with the period. This indeterminate mass is the study's ONLY potential
overcount — everywhere else "all rates are floors" holds one-sidedly. It is
therefore reported as a TWO-SIDED BOUND (`studies.slices --table bounds`,
a standing section of the generated report): the headline ai_involved series
with the weak-prefix indeterminates (upper arm, the reported number) and
with weak prefixes requiring positive provenance (lower arm). Measured
width: **0.06pp in Q2-2026** (17.66 vs 17.60 CW), <=0.01pp in earlier
quarters — the weak-prefix volumes (462 claude/ + 73 cursor/ C-only sampled)
are dwarfed by codex/ (4,698, 95% confirmed) and layers A/B. With that one
quantified exception stated, every other rate in the study is a floor.

**droid/ (Factory Droid), added 2026-07-17 as a WEAK prefix** after the
agent-fleet audit surfaced it as a measured detection gap. Measurement
before inclusion (all census cells): 271 droid/ PRs, 270 in Q2-2026, 269
from a single fleet-operator account (writer/cerebro); on-PR layer-A/B
confirmation 4.8%; exactly one pre-AI-era PR (Q1-2024, unrelated repo)
demonstrates the droid!=Factory naming collision, giving ~0.4% measured
contamination. Confirmation slug for the strict arm: the `-YYYYMMDD`
suffix Factory appends to generated branches. Consequences: droid/ enters
the headline via the weak-prefix upper arm and the two-sided bound absorbs
its indeterminate mass; the Q1-2024 caption gains one known FP-class PR
(excluded by the strict arm, invisible at reported precision).

**Layer overlap** is measured, not assumed, on org-stratified samples
(`pull_prs.sample_branch_prs`): A∩C ≈ 2% for codex/; B∩C is high for
copilot/ (the bot authors those PRs). `integrate.py` combines layers
disjointly: total AI involvement = A + B + (C minus measured overlaps).

**Review classification** (`detect.split_reviews` — the single choke point
every review-based metric flows through). Each formal review object is
classified by its author into exactly one of three reviewer types:

1. **Human**: account `__typename == "User"` AND the login does not match
   the user-bot heuristic (below) AND, for the human-review flag, login !=
   the PR author (GitHub permits self-review-comments; counting them
   inflated the self-merge lane — correction §11c of the working log,
   aggregate impact <=2.2pp). Reviews submitted after the study cutoff are
   excluded before classification.
2. **AI reviewer**: Bot-typed (or user-bot) account whose login (with any
   `[bot]` suffix stripped) is in the curated `AI_REVIEWERS` allowlist —
   dedicated AI code-review products observed in the data:
   gemini-code-assist, copilot-pull-request-reviewer, coderabbitai,
   greptile-apps, qodo-merge-pro, cursor, chatgpt-codex-connector,
   copilot-swe-agent, claude. The list is extend-as-found; it deliberately
   errs toward under-counting AI review (an unlisted AI product lands in
   class 3, not class 1 or 2).
3. **Other bot**: any remaining Bot-typed or user-bot account — CI,
   automation, dependency bots. Kept as its own class so AI review is never
   conflated with CI noise.

**The user-typed-bot problem** (`detect.is_bot_login`): GitHub's
`__typename` distinguishes App-installed bots, but organizations also run
bots as ordinary User accounts (found by a comment-volume audit:
PaddlePaddle-bot, all-hands-bot, qwen-code-ci-bot), which would otherwise
count as human reviewers and pollute the human-attention numerator exactly
in the AI era. The heuristic is anchored to avoid false positives on human
names: a login is a bot iff it ends with `-bot`, `_bot`, `[bot]`, `-ci`,
`-robot`, or starts with `bot-` (so "talbot" is human; pinning tests cover
both directions). Residual risk: an unmarked User bot with a plain name
passes as human — mitigated by the audit (top comment producers reviewed by
hand) and by the direction of the bias (any residual bot inflates the human
numerator, making the reported human-attention decline conservative).

Substantive review = a human (reviewer != author) review with inline
comments or a non-APPROVED state. All comment counts in attention metrics
sum ONLY over class-1 reviews — bot comments can never share a numerator
with human comments (frozen convention §1d.3).

**What is undetectable** (all rates are floors): squash-merge strips trailers
(asymmetrically — Claude's footer survives squash more often, so non-Claude
tools are likelier undercounted); local tools with default settings
(Windsurf, Codex CLI, Copilot in-IDE) leave no public metadata; in-session
review (reading agent diffs before accepting) is invisible except through
residue (v2_results §11d–e).

## 3. Census design (`precount.py`, `census.py`)

For every population repo × 4 quarters (Q1-2024, Q4-2025, Q1-2026, Q2-2026
— full quarters): denominators via batched aliased-GraphQL counts; PR nodes
via the search API into the versioned census-v2 store (the cell-store name
encodes the query version). Repo-quarters are collected COMPLETELY: the
sub-window count adapts to PR volume (integer-boundary date splits — float
rounding once produced inverted windows), each window paginates by cursor up
to the API's 1,000-node cap (= up to 1,000 PRs per day-window), cells are
written atomically (tmp+rename: torn writes cannot exist), and a repo-quarter
that still cannot be completed FAILS the run. Report generation is gated on
gap-free valid-cell coverage of every manifest repo-quarter, with documented
inaccessible repos waived explicitly (`inaccessible_repos.txt`).
Fields per PR: commits (messages, author emails, committer), formal reviews
(author, type, state, inline-comment counts), author association, size,
timestamps, headRefName and mergedBy.

Per-PR field caps: the census fetches each PR's first 12 commits and 15 reviews
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
contributors active in the study window (≥5 commits authored in
Q4-2025..Q2-2026, bots excluded, from GitHub weekly contributor stats;
`repo_contributors_window.csv`; all-time variant kept for sensitivity).
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
API-hydration steps re-pull live state. 97 unit tests cover storage
semantics, window math, detection (incl. cutoff filtering and the layer-C
false-positive exclusion), weighting, coverage gating, and the layered
decomposition. The end-to-end path is `scripts/regenerate.py`: a fixed-point
loop over collection stages, hard gates (nonzero exits, strata DONE
sentinels, gap-free coverage with explicit waivers), then a generated report
(`artifacts/report_generated.md`) plus a hashed census manifest — canonical
numbers come only from that artifact.

## 5a2. Review-effectiveness triangle (pinned definitions)

- Talk: HUMAN comments/kLOC (`studies.attention`, primary attention measure).
- How much talk: comment length — requires a body pull; not yet collected.
- ACTION: conditional responsiveness to HUMAN ASKS
  (`studies.review_action`) — among PRs where a human reviewer requested
  changes or left inline comments, author edits after the first ask.
  IDENTIFIED estimate = the CLEAN lane (no AI-reviewer activity on the PR);
  the mixed lane is descriptive (post-ask edits are causally ambiguous when
  human and AI comments interleave); all-cause post-review edits are a
  descriptive companion only. Caveats: committedDate rewritten by
  rebase/amend (drifts late — inflates attribution); squash branches keep
  original dates. Sampled, LOC-weighted, seeded.

## 5b. LOC hygiene sensitivity (generated content)

Objection pre-empted: if AI-era PRs carried more generated content
(lockfiles, vendored code, build artifacts), LOC denominators would inflate
and per-line attention would thin mechanically. Measured on an LOC-weighted
sample of merged PRs with per-file paths (~950 PRs/quarter,
`data/derived/loc_hygiene_sample.jsonl`; pattern list covers lockfiles,
vendor/dist/third_party, minified, protobuf-generated, snapshots, svg,
notebooks): generated share of merged LOC is **18.3% (Q1-2024) -> 8.5% ->
11.2% -> 17.1% (Q2-2026)** — the endpoint is BELOW the 2024 baseline.
Excluding generated content, merged-volume growth is marginally LARGER
(x4.2 vs x4.1) and the attention decline is unchanged (-56% vs -57%).
The volume and attention series are therefore not artifacts of generated
content.

## 6. Known limitations

- **Floors, asymmetric across tools** (§2). The Codex marker floor (0.15% of
  PRs) vs its branch-level rate (3.6%) shows the gap can be ~24×.
- **Prominence-selected population**; no claim about GitHub at large.
- **Q2-2026 mild recency censoring** (collected ~1 week after quarter end;
  late reviews/merges undercounted).
- **31 repo-periods (0.4%) permanently inaccessible.**
- **Branch-PR samples are first-page (created-desc) per org-quarter** — mild
  within-quarter recency bias.
- **Insider classification** (authorAssociation) misses staff whose org
  membership is private — several "external" substantial-PR authors are
  founders (v2_results §10 caveat).
- **In-session review is unobservable**; §11d–e measure only its residue.
