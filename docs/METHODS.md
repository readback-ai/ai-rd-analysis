# Methods

(Metric-level definitions and the generated-report layout live in
[`METRICS.md`](METRICS.md).)

Methodology for the study of AI-assisted development practices at leading AI
organizations; this document is canonical. Results live in
`artifacts/results.md`; every module named here is in `src/pipeline/`.

## 0. Study cutoff and as-of policy

The study cutoff is **2026-06-30** (end of Q2-2026).
- **Activity data** (PRs, commits, reviews, branch-prefix counts) is strictly
  windowed: every query carries `created:<=2026-06-30` bounds. Because all
  per-PR fate outcomes follow the w8 rule (§1d.1), collection lag is not a
  bias: PRs whose 8-week window was still open at the as-of simply carry NO
  fate (None-skip) — less data on the trailing quarter, not skewed data.
  Q2-2026 fates finalize with the scheduled 2026-08-26 re-pull (§1c).
- **Classification metadata** (repo topics, descriptions, star counts,
  org descriptions) has no historical API — it was observed 2026-07-07..09,
  as close to the cutoff as possible, and applied uniformly to all orgs. Drift
  over those days is assumed negligible; the observation date is recorded in
  each snapshot file.
- **Ownership** (org-type cut) is pinned as-of the cutoff: e.g. xai-org
  counts as public (SpaceX acquisition + IPO completed before the cutoff).
- **Contributor weights** are WINDOW-SCOPED: core committers active in
  Q4-2025..Q2-2026 (≥5 commits, bots excluded) from GitHub's weekly
  contributor statistics (`repo_contributors_window.csv`); the all-time
  variant is retained only as a sensitivity file.

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
hand-curated remainder** (`curated_orgs.tsv`, 18 labs on neither Epoch nor
TechCrunch — mostly Chinese labs whose models Epoch attributes to parent
companies, and labs too new to have a notable model; trimmed 2026-07-10
from an initial 33 by counterfactual test, later re-additions included) is
stated plainly as curation.

**R2 — Quality.** Flagship repository >=1,000 stars. Members of the
AI-developer lists (Epoch/TechCrunch/curated) are exempt: those lists
already vet significance via notable models or $100M+ funding.

**R3 — AI-developer identity.** An org is an AI DEVELOPER iff it is on an
AI-developer list OR >=2 of its top-5 starred repos carry maintainer-declared
AI topics (frozen dictionary `AI_TOPICS` in `org_set.py`). Descriptions and
name heuristics are deliberately NOT used: maintainers SEO their metadata
("AI-powered" secrets scanners self-tag `llm-training`), and topics-only plus
lists proved the robust combination.

**R4 — Evidence.** >=5 distinct AI-evidence PRs/commits in the MAXIMUM
single evidence source (marker scan, layered recheck, branch counts, or
census-derived union). The max ACROSS sources avoids adding one PR's
evidence from two sources, and WITHIN a source no PR counts twice either:
recheck evidence is the max probe count (probes overlap — one PR can
match its branch and its markers), and branch evidence sums keyed
(org, quarter, prefix) cells, which is an exact distinct count because
creation-dated quarters partition PRs and the prefixes are pairwise
non-nested; Q1-2024, the false-positive control, never counts toward
admission. For repo-scoped orgs the branch counts cover their in-scope
repos only (per-repo queries), matching the census universe (R5).
Alternatively >=0.1% of the org's censused PRs (rate computed from the census
evidence pair only); windows all <= cutoff. An org with no measurable AI-tool footprint contributes
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

Result (2026-07-30 regeneration): **224 orgs = 179 full-org + 45
repo-scoped** (`population.tsv` is authoritative; docs quote it). Down
from the 2026-07-10 run's 229 under the corrected distinct-evidence R4
arithmetic applied uniformly: sony (probe-sum double-counting) and,
via the census-evidence recompute under current detection (CI-canary
branch exclusion), physical-intelligence, salesforceairesearch,
stability-ai, and thu-pacman.
Consequence for inference: the population is prominence-selected; findings
describe practices at leading AI organizations, with the Q1-2024 census as
the temporal control.

Repo-level population: full-org members contribute repos passing the same
R4 evidence rule (`enum_repos.py`); repo-scoped members contribute their
AI-topic repos. Appendix cuts (org-type public/private/community via
`org_type.tsv`; adoption-intensity groups) re-use these same source files.

## 1c. Incremental monthly updates (runbook)

`scripts/monthly_update.py YYYY-MM` adds a month of activity data:
1. RE-COLLECTS the previous TWO months first (wipes their census cells;
   cells are immutable snapshots, so refresh is always wipe + full
   re-query, reconciled against fresh precounts). The wipe happens ONCE
   per target month (logged in raw/monthly_wipes.json), so rerunning the
   update after a mid-collection failure RESUMES the checkpointed
   census instead of discarding it — N-1 for creation
   recency, and N-2 because under the w8 rule its last 8-week windows
   only just closed: a month's fate metrics are FINAL once it has been
   revised as N-2, i.e. two updates after first collection. Until then
   its rows are provisional (immature PRs carry no fate). Stale
   quarter-shaped cells overlapping a revised month are superseded PR-by-
   PR via the load-order freshness rule (`analyze.group_by_period`).
2. BUMP `detect.AS_OF` to the run's start date — maturity is judged
   against the data-collection stamp, and since mature PRs are immutable,
   bumping only ever ADDS newly-mature PRs. The stamp must clear the LAST
   creation date in the month being finalized: a PR created
   2026-06-30T23:59Z reaches 56 days only at 2026-08-26T00:00Z, so a
   stamp of 2026-08-25 leaves June's final day immature. It also records
   a pull that HAPPENED and is read directly by ~17 modules, so it is
   never committed ahead of its re-pull — a future stamp makes every
   reader treat stale cells as final, scoring unobserved events as
   non-events. `run_monthly_update.sh --bump-as-of` therefore advances it
   at the instant collection starts (rolling back if the run fails), and
   the one-line diff is committed with the regenerated artifacts of step
   5. `test_as_of_never_leads_the_wall_clock` pins the rule. Fixtures
   never assume the constant's current value — tests that turn on
   maturity pin their own `AS_OF` (it advances at every re-pull).
   Concretely for Q2-2026: the update adding 2026-07 (run ~Aug 1)
   re-collects and finalizes May (windows closed Jul 26); June finalizes
   on 2026-08-26 (windows closed Aug 25) — the monthly cadence IS the
   Q2 finalization, executed in two steps.
3. Collects the new month (precount + census; months are first-class period
   tokens via `scan_orgs.resolve_period`). `--revise-only` SKIPS this step
   and runs the revision window alone, for a finalization that lands
   mid-month: N-2's windows close 8 weeks after its month end, partway
   through month N, when N is still partial and not worth collecting. The
   target month stays uncollected and out of the incremental registry, and
   keeps its own wipe-log cycle (`{month}:revise-only`) so the later full
   update still wipes and re-collects its revision window. June's
   finalization takes this path: `monthly_update.py 2026-08 --revise-only`
   on 2026-08-26; August itself lands with a later update.
4. Prints the monthly trend tables (`analyze --granularity month`,
   2-PR/month floor ≈ the 5-PR/quarter threshold per unit time).
5. REGENERATE the published artifacts. New cells plus a new stamp change
   published numbers, so a finalization is not complete until
   `regenerate.py`, the monthly `report.py`, and `plot_all.py` have been
   rerun and committed alongside the `AS_OF` bump — otherwise figure
   tables, images and reports keep describing the previous stamp.
   Provisional annotations are DERIVED from the stamp, never hard-coded
   (`detect.w8_closed` is the single home of the question;
   `figstyle.shade_q2_partial` drops the Q2 band and
   `productivity.q2_provisionality_note` empties its caption once Q2
   closes), so regeneration alone clears them.
Step 2 is enforced, not merely documented: `check_finalizable` refuses the
run — BEFORE any cell is wiped — unless `AS_OF` both reaches the N-2
month's `finalization_stamp` (its last creation instant + 56d) and does
not lead the run's own clock. Too early a stamp publishes N-2 as final
with its last days immature, and N-2 is never re-collected afterwards, so
that undercount would be permanent; a stamp ahead of the run marks PRs
mature whose events the census has not observed, reading an unobserved
merge as never-merged. Because the finalizable instant is a time and not
a date, `scripts/run_monthly_update.sh --at <ISO-8601-Z> <args>` waits for
it and logs the run to the gitignored `data/derived/`.
Population and classification metadata stay FROZEN between deliberate
revisions so month-over-month movement reflects practice, not population
churn. Quarterly regeneration (`scripts/regenerate.py`) remains the
canonical headline path.
Plumbing (fixed 2026-07-20, external review): collection is restricted to
the collectable population (documented-inaccessible repos waived, same
rule as regenerate stage C), and the update persists its month tokens in
`data/derived/incremental_months.txt` — a registry `analyze` reads to
extend the frozen quarter map (`analyze.extended_quarters`; explicit
`--periods` tokens are additive) — previously a newly collected month's
cells were silently discarded by the static-quarter filter. Cached full-range census cells are re-validated
against the precount (same drift allowance as fresh pulls) before being
trusted, so brownout-poisoned empty caches self-heal on the next run.

## 1d. FROZEN methodology conventions (every paper number obeys these)

1. **Censoring rule**: ALL per-PR events — merges, closes, AND review
   submissions — count only within 8 WEEKS of PR creation
   (`detect.W8_DAYS`; review events adopted into the rule 2026-07-20;
   maturity curves show merges quiesce at w8, 98-99% of eventual). Fates
   close at w8, with w26 as appendix sensitivity (`studies.fates`).
   Immature PRs carry no fate (None-skip) — trailing quarters are
   PROVISIONAL and labeled; Q2-2026 finalizes with a re-pull on/after
   2026-08-26 (8 weeks past quarter end; runbook §1c). Corollary: mature
   PRs are immutable under as-of advances.
2. **Matched-horizon-only fate comparisons**: "ever resolved" is a
   different quantity per cohort and must never be compared across cohorts.
3. **Primary attention measure = HUMAN comments/kLOC** (bot comments
   excluded by construction: `detect.split_reviews` drops Bot-typed AND
   User-typed bot accounts, `is_bot_login`, pinning test). Window
   hours/kLOC corroborates, never leads. Size-band decomposition separates
   within-size thinning from composition (`studies.attention`).
4. **Weighting labeled on every number**: contributor-weighted primary
   (active-window weights), pooled secondary. One canonical marker set
   (`detect.MARKERS`).
4b. **Outlier policy — bound the unit contribution, or take the median.**
   Which applies follows from whether ONE unit's contribution to the
   numerator is bounded:
   - RATES (AI-usage %, review-mix shares, responded%) need neither: each
     PR adds exactly 1 to the denominator and at most 1 to the numerator,
     so no unit can dominate and the mean is already robust.
   - BOUNDED-DENOMINATOR RATIOS with an unbounded numerator are CAPPED at
     the unit that generates them: `attention.COMMENT_CAP` = 20 inline
     comments per (reviewer, PR), the analogue of `frame.CAP` = 20k LOC
     per PR. One reviewer's exhaustive pass over a single PR is one act
     of review, not N units of attention; a documentation copy-edit left
     355 comments on one PR — the maximum of 112k reviewer-PR pairs
     against a median of 2 — and carried a whole month's fleet series.
     The cap truncates 0.9% of pairs (3.2% of comments) and does not move
     the attention decline (−54% at every cap tested).
   - PER-CONTRIBUTOR VOLUMES are unbounded per unit (one operator merged
     4.8M lines in a month) and are reported as MEDIANS over cohort
     members. The growth multiple is robust to the choice (core kLOC
     ×2.95 mean vs ×2.92 median); the LEVELS are not (19.0 vs 10.0
     kLOC/author in Q2-2026), so quote levels from the median.
   Repo-level trimming/winsorization was considered and REJECTED: study-
   wide the most influential repo-period contributes 6% of comments on 2%
   of kLOC (3x), winsorizing cell rates at p99 moves the pooled rate by
   0.1%, and a percentile rule misses the motivating case anyway because
   the rate tail is dominated by near-zero-denominator cells.
5. **Layer-C hygiene**: CI-canary false-positive class excluded (pinning
   test); per-prefix provenance precision stated (§2); the ai_involved
   series carries its two-sided weak-prefix bound as a standing report
   section — the single quantified exception to the floors framing.
6. **Q1-2024 caption** on every table where the column appears:
   detector-validity check and review-practice baseline, not an AI-usage
   estimate.
7. **Determinism & completeness**: seeded bootstrap (seed 20260630; 2,000
   draws on the headline table, paper figures and productivity tables —
   slice tables use 500, the balanced panel and monthly trend prints
   1,000), seeded samples, SHA-256 manifest, fail-hard on incomplete or
   invalid cells, gap-free coverage gate with documented waivers.

## 2. Detection: three independent layers (`detect.py`)

**Layer A — commit markers** (commit-forensic, strongest evidence). Co-author
trailers and generation footers (Claude Code: `noreply@anthropic.com`,
`Generated with [Claude Code]`; Cursor: `cursoragent@cursor.com`; aider
trailer), and tool author/committer identities (Codex cloud's
`chatgpt-codex-connector[bot]` committer, `codex@openai.com`). One canonical
marker set (`detect.MARKERS`: Claude, Cursor, aider, Codex, OpenHands, and
a vetted self-identified-agent list — the earlier v1/v2 versioning was
collapsed 2026-07-20; adding aider+Codex had moved the headline +0.1pp).

**Committer-identity audit (2026-07-20)**: a full-store sweep for
agent-like committer identities not matched by the needles found (a)
OpenHands (`openhands@all-hands.dev`, 2,400 commits Q1–Q2 2026) — added
as a tool; (b) a second Cursor cloud identity (`agent@cursor.com`) —
added to cursor; (c) self-identified HOMEGROWN agent identities
(`hermes-agent@*`, `agent@modal.com`, `agent@deepagents.dev`,
`pragma-agent@modular.com`, `bot@imbue.com`, …) — added as the vetted
"agent" marker, each identity hand-checked; CI/release bots surfaced by
the same sweep (snyk, renovate, xnnpack, airflow, …) are deliberately
excluded. The audit also confirmed the structural floor: fleet operators
overwhelmingly commit under PERSONAL identities, which no needle can
catch. `-agent`/`_agent` joined the user-typed-bot login suffixes
(author/reviewer hygiene). Search-side rule: co-author trailers
are only findable by BARE-TERM commit search — the `author-email:` qualifier
matches primary authors only and returns ZERO for co-authored commits when
org-scoped (measured: 0 vs 251 for QwenLM, 0 vs 799 for OpenBMB; globally
the bare search finds ~3× more, 15.7M vs 5.31M — see
`artifacts/agent_detection_cues.md` cue 4). Qualifier terms remain correct for tools that
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
marker, no agent author; `studies.layer_c_precision`. Repo-scoped orgs'
cells are drawn from their in-scope repos — the scoped universe is
queried directly, before the per-cell page cap — and filtered again at
read time as belt-and-braces): the share carrying
positive provenance signals (GitHub web-flow committer, or the product's
machine-generated slug pattern) is codex/ 95%, copilot/ 98%, cursor/ 49%,
claude/ 42%. The web-flow identity (`noreply@github.com` committer) is any
web-UI/API commit and is NOT standalone agent evidence — it confirms only
CONDITIONED on the agent-named branch; these precision figures measure
exactly that combination. One false-positive class was MEASURED and is
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
width: **0.05pp in Q2-2026** (16.62 vs 16.57 CW, droid/ included),
<=0.01pp in earlier quarters — the weak-prefix volumes (462 claude/ + 73 cursor/ C-only sampled)
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
copilot/ (the bot authors those PRs). `studies/layers.py` combines layers
disjointly: total AI involvement = A + B + (C minus measured overlaps).

**Review classification** (`detect.split_reviews` — the single choke point
every review-based metric flows through). Each formal review object is
classified by its author into exactly one of three reviewer types:

1. **Human**: account `__typename == "User"` AND the login does not match
   the user-bot heuristic (below) AND, for the human-review flag, login !=
   the PR author (GitHub permits self-review-comments; counting them
   inflated the self-merge lane — correction §11c of the working log,
   aggregate impact <=2.2pp). Review events follow the SAME w8 rule as
   fates (adopted 2026-07-20): a review counts iff submitted within
   8 weeks of PR creation (`detect.split_reviews`). CUTOFF bounds PR
   CREATION (the frame), not events — an event inside a PR's window
   counts even when it lands after CUTOFF (implicitly capped at
   CUTOFF + 56d since created <= CUTOFF), which is exactly what lets the
   2026-08-26 re-pull finalize Q2 without changing the frame or any rule —
   only the AS_OF data stamp advances. Every
   per-PR quantity FINALIZES at w8; re-collection can never change a
   mature PR's classification — fates and review metrics alike. Measured impact of adopting the rule (pooled
   any-human-review rate): -0.47pp Q1-2024, -0.60pp Q4-2025, -0.40pp
   Q1-2026, -0.06pp Q2-2026 — late reviews past 8 weeks are rare, and
   the trailing quarter (whose PRs had no time for them) barely moves.
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

The reviewer != author rule applies to bots exactly as to humans: a bot
review whose login (with any `[bot]` suffix stripped) equals the PR
author's is excluded from classes 2 and 3. Coding agents (three logins —
cursor, claude, copilot-swe-agent — sit in both `AGENT_PR_AUTHORS` and
`AI_REVIEWERS`) post self-summaries as formal review objects on their own
PRs; counting those as AI review misclassified the PR's approval channel
and its review_action lane. Measured impact of adopting the rule (mature
PRs): `ai_reviewed` drops on 74 / 36 / 12 PRs in Q4-2025 / Q1-2026 /
Q2-2026 (0 in Q1-2024; 116 of the 122 are copilot-swe-agent
self-reviews), moving the weighted ai_review series by <= 0.04pp;
`other_bot_reviewed` drops on 385 PRs across the window.

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

**Author-side eligibility profiles** (`pipeline.frame`, definitions in
CONTEXT.md): which PRs enter a study is a named policy, not a per-study
guard. `pr` = the human-authored PR population (skips App-bot authors;
review-behavior studies — bot dep-bumps have degenerate review dynamics);
`author` = attributable human authors (adds the `is_bot_login` hygiene;
author-level productivity/event studies, the Figure 6 role cut, and
channel shares — a bot is not a productivity unit and its NONE
association is not an "external contributor"); `all` = no author filter
(population-level usage tables, where layer-B agent output must count).
The AI-contrast review-behavior outputs — Figure 6 by-AI, Figure 7,
Figure 8, and fates' AI/nonAI cohorts — share `all` with fleet-operator
exclusion (issue #2, resolved 2026-07-23): human attention and
responsiveness to a PR are defined regardless of its author, so
agent-authored PRs count in the AI series; for them, responsiveness
means the agent/operator pushes commits after a human ask. Those sites
additionally require `frame.ai_contrast_eligible` (2026-07-25 review): a
PR bypasses author hygiene only if it is AI-involved, because `all` alone
also readmits App dep-bots, user-typed bots and login-less authors — none
AI-involved, so all of them accrue to the **nonAI comparison arm** and
restore the degenerate dynamics `pr` excludes (undiscussed auto-merged
bumps), with bot volume trending upward over the window alongside AI
adoption. Under the gate `all = AI + nonAI` exactly, while `all = ins +
ext + agent-authored` since a Bot has no human author association; fates
footnotes that residual per quarter.

**What is undetectable** (all rates are floors): squash-merge strips trailers
(asymmetrically — Claude's footer survives squash more often, so non-Claude
tools are likelier undercounted); local tools with default settings
(Windsurf, Codex CLI, Copilot in-IDE) leave no public metadata; in-session
review (reading agent diffs before accepting) is invisible except through
residue (`studies.review_modes`).

## 3. Census design (`precount.py`, `census.py`)

For every population repo × 4 quarters (Q1-2024, Q4-2025, Q1-2026, Q2-2026
— full quarters): denominators via batched aliased-GraphQL counts; PR nodes
via the search API into the census store `raw/census-v2/` (the historical name
encodes the query version). Repo-quarters are collected COMPLETELY: the
sub-window count adapts to PR volume (integer-boundary date splits — float
rounding once produced inverted windows), each window paginates by cursor up
to the API's 1,000-node cap (= up to 1,000 PRs per day-window), cells are
written atomically (tmp+rename: torn writes cannot exist), and a repo-quarter
that still cannot be completed FAILS the run.
**Unsearchable repos** (`census_direct.py`): GitHub's search index refuses
some public repos outright (`repo:X` answers HTTP 422 "cannot be searched"),
so no precount and no search-collected cell can ever exist for them. Such a
repo is collected through `repository.pullRequests`, which does not use the
search index; its own `totalCount` is the completeness denominator (the full
history must arrive, verified page by page, or nothing is written), and
quarters with no PRs get a VERIFIED empty cell. Only the definitive 422
triggers this route — a transient failure still fails the repo-quarter.
Measured 2026-07-29: 8 population repos in this state, 364 in-window PRs
recovered rather than waived as inaccessible (they skew new and
AI-tooling-heavy, e.g. `ComposioHQ/awesome-claude-plugins` at 265, so
waiving them would bias AI rates DOWN). A zero denominator never
stands on one observation: search brownouts return 200 with a zero count,
so a 0 precount is re-queried and only a confirmed 0 (cache-marked) can
census as a complete empty repo-quarter — an unconfirmable zero FAILS
the cell. Report generation is gated on
gap-free valid-cell coverage of every manifest repo-quarter, with documented
inaccessible repos waived explicitly (`inaccessible_repos.txt`).
Fields per PR: commits (messages, author emails, committer), formal reviews
(author, type, state, inline-comment counts), author association, size,
timestamps, headRefName and mergedBy.

**Cell lifecycle: immutable snapshots, superseded — never edited.** A cell
freezes the event state (merges, closes, reviews) of its PRs at its
collection moment; nothing ever updates a cell in place. Late events reach
the dataset only through RE-COLLECTION: the monthly runbook (§1c) wipes
the trailing two months and re-queries them in full, producing NEW
month-shaped cells whose PRs supersede the same PRs in the original
quarter-shaped cells via the load-order freshness rule
(`analyze.load_cells` visits files oldest-mtime-first;
`analyze.group_by_period` lets the later-loaded record win at equal
richness). The old quarter cells stay on disk — they still serve the PRs
of un-revised months — so the store accumulates overlapping generations
by design, and per-PR dedup is what makes that safe. Combined with the
w8 event window and the AS_OF maturity stamp, this gives the update
calendar its meaning: a month's fates become final exactly when a
re-collection runs after its last 8-week window closed (May at the
~Aug 1 update, June at 2026-08-26), and nothing already mature can move.

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

## 4. Metrics and weighting (`analyze.py`, `studies/layers.py`)

Per-repo-period rates over PRs (repo floor: **≥5 PRs/quarter, ≥2
PRs/month** — comparable thresholds per unit time; `analyze --min-prs`,
`slices.MIN_PRS`), then **contributor-weighted** means across repos:
weight = the repo's core human contributors active in the study window
(≥5 commits authored in Q4-2025..Q2-2026, bots excluded, from GitHub
weekly contributor stats; `repo_contributors_window.csv`; all-time variant
kept for sensitivity). Contributor weighting answers "what does the
typical AI-org developer's PR flow look like"; pooled and equal-weight
variants differ through a repo-size gradient (small repos are AI-heavier)
and are reported only as reconciliation views.

**Bootstrap CIs — what is being resampled, and why a complete census has
CIs at all** (`analyze.bootstrap_ci`). The census is complete: every PR
of every qualifying repo-period is observed, so for THE FRAME ITSELF (the
2,142 repos in these quarters) any reported mean is an exact population
quantity with zero sampling error. The CIs answer the superpopulation
question a reader actually asks — "how much does this mean depend on the
particular repos that happen to make up the frame?" — by treating REPOS
as the exchangeable unit: each of 2,000 draws resamples the qualifying
(per-repo rate, weight) pairs with replacement to the original count and
recomputes the weighted mean; the interval is the 2.5th/97.5th
percentile. Wide CIs mean the mean is carried by few/heterogeneous
repos; narrow CIs mean it is a broad-based property. Within-repo
PR-level noise is deliberately NOT resampled (there is none to model —
complete enumeration), and no claim is made about GitHub beyond the
frame (METHODS §6). Each reported interval draws from its OWN seeded
stream, derived from the study seed (20260630) and a key naming the CI
cell — table, period, metric (`analyze.bootstrap_ci`, whose `key` argument
is required). So an interval is reproducible in isolation: identical reruns
reproduce it, and so does a run that computes a different set of other
intervals first. Studies
with their own uncertainty needs reuse the same helper (paper figures)
or document their estimator inline (review_action's two-design split —
equal-probability for rates, Horvitz–Thompson over PPS for LOC shares,
§5a2; author-level cohort tables bootstrap over AUTHORS, the analogous
unit).

Cross-layer decomposition (`studies/layers.py`) is exact and per-PR on the
census (disjoint by precedence B > A > C); the earlier sample-blended
integration and org-threshold approximations were removed 2026-07-20.

Accountability metrics (studies/accountability.py): self-merge =
mergedBy == author; one-person accountability = self-merged with no
other-human formal review and no other-human comment; GitHub forbids formal
self-approval, so a second-human merge is treated as tacit review.

## 5. Reproducibility

All stages are checkpointed, idempotent, and resume-safe; collection was
~36h wall-clock under rate limits with zero data loss across interruptions.
Studies use seeded sampling (published draws reproduce exactly); their
API-hydration steps re-pull live state. The unit-test suite (`uv run
pytest -q`; fast, no network) covers storage semantics (atomic cells,
cache validation, self-heal), window math and the w8 rule, detection
(marker/agent/branch layers incl. the as-of bound and the layer-C
false-positive exclusion), review classification and bot hygiene, dedup
freshness, the incremental-month registry, weighting, coverage gating,
pagination completeness, and the HT sampling weights — each test names
the finding or review item it pins. The end-to-end path is `scripts/regenerate.py`: a fixed-point
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
  descriptive companion only. "Author edits" match the PR author with the
  [bot] suffix normalized away (the census stores Bot authors without it,
  commit-level logins carry it), and the PR's OWN bot counts as the author
  responding (issue #2: an agent-authored PR responds when the agent
  pushes) while commits by any OTHER bot stay excluded. Caveats:
  committedDate rewritten by rebase/amend (drifts late — inflates
  attribution); squash branches keep original dates.
  Estimation (revised 2026-07-20; split into two designs 2026-07-23):
  TWO seeded samples over the same frame, each with its own
  frame-fingerprinted manifest. responded% comes from an
  EQUAL-PROBABILITY sample (min(1,200, N) distinct PRs/quarter, uniform)
  as an unweighted share — under the earlier PPS-only estimation the
  Horvitz-Thompson weights pi_i = 1-(1-w_i/W)^1200 let tiny-LOC PRs
  dominate small lanes (measured: 39% of a 22-PR lane's weight on one
  75-LOC PR; the lane swung tens of points between equally-valid draws).
  post-ask LOC share stays on the PPS-by-LOC sample (1,200 draws/quarter)
  as the ratio of HT LOC totals — the estimand that design is efficient
  for.
  Commit lists are paginated (100/page + follow-ups); the earlier
  first:60 cap chronologically truncated 261/4,233 sampled PRs, biasing
  responsiveness downward on high-commit PRs — those records were
  re-pulled in full (`review_action --repair`). Completeness = a clean
  terminal pagination walk: the commits totalCount can exceed what the API
  serves, so records store the RETRIEVED count as `commits_total` alongside
  the API claim (`commits_api_total`). Measured 2026-07-26, that shortfall
  is GitHub's hard **250-commit-per-PR cap**, not force-pushed commits as
  previously documented: every record claiming >250 retrieved exactly 250,
  and none anywhere exceeds 250 (30 of ~8,960 analyzable records, 0.3%).
  For those PRs **we analyze the first 250 commits, because that is all the
  data that exists for them** — and, decided 2026-07-26, we measure them
  against the LOC of *those same commits*: the census PR LOC is normally a
  FLOOR on the denominator, but flooring a truncated record would divide a
  250-commit numerator by a whole-PR denominator and bias post-ask LOC share
  downward. Truncated records are neither excluded (they are real PRs, and
  dropping the largest-commit ones would itself be selection) nor rescaled
  (nothing supports an estimate of what the unserved commits contain). The
  residual limitation stands: for these 30 records the estimand is
  "post-ask share of the first 250 commits' LOC", not of the whole PR.
  Identify them with `commits_total < commits_api_total`
  (`review_action._truncated`). UNIT
  NONRESPONSE: selected PRs whose repo left the live API between census
  and hydration (privatized, deleted, or PRs disabled — measured:
  openai/plugins disabled PRs 2026-07-14) are tombstoned as documented
  nonresponse (~0.5% of the selection), excluded from analysis with HT
  weights unchanged, reported in the table output, and retried on every
  repair in case retrievability returns. A tombstone requires a DEDICATED
  single-PR confirmation whose every error is `NOT_FOUND`: a null alias in a
  batch response also occurs when that batch times out or trips the
  secondary rate limit, and on 2026-07-25 that misreading recorded 1,345
  live PRs as permanent nonresponse (27.9% of one design's selection),
  which zeroed the Q2-2026 AI lane before the numbers were caught and
  repaired. Unconfirmed nulls DEFER to the next pull instead. Because
  "documented" nonresponse resolves coverage, publication is additionally
  refused above a nonresponse ceiling (2%, once 20+ tombstones exist) —
  at that scale a documented subset is still a non-probability subset.

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
- **Q2-2026 fate provisionality**: PRs created after ~2026-05-05 are
  w8-immature at the frozen as-of and carry no fate (excluded, not
  miscounted); Q2 fate cells have less data until the 2026-08-26 re-pull
  finalizes them (§1c).
- **Repo-periods permanently inaccessible** — each waived explicitly in
  `inaccessible_repos.txt` (75 repos; the census manifest carries the
  current repo-period coverage). The list GROWS as repos are deleted or
  taken private mid-study: the 2026-08-26 June finalization added four
  (`agno-agi/agent-platform-railway`,
  `dataelement/shougang-group-knowledge-portal`,
  `huggingface/transformers-test-ci`, `RunanywhereAI/RunAnywhereAgent`)
  whose owning orgs are alive but whose repositories now answer NOT_FOUND
  on both GraphQL and the rename-following REST route. These are a
  different case from the 422-unsearchable repos, which are RECOVERED via
  `census_direct` rather than waived (above) — a deleted repository has no
  object route left. Their pre-deletion cells stay in the store and keep
  counting; only the re-collection is waived. Between them they held 7
  June-2026 PRs at last observation, and `huggingface/transformers-test-ci`
  is left with a June coverage gap (its June sub-window cells were wiped
  by the revision and cannot be re-pulled), which is why the repo-level
  waiver — not a period-level one — is the honest treatment.
- **Branch-PR samples are first-page (created-desc) per org-quarter** — mild
  within-quarter recency bias.
- **Insider classification** (authorAssociation) misses staff whose org
  membership is private — several "external" substantial-PR authors are
  founders (working-log finding, retired log).
- **In-session review is unobservable**; §11d–e measure only its residue.
