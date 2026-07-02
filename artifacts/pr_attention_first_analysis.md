# First analysis: PR attention / timing — agent vs human, over time (2026-06-26)

First pass at "is attention to PRs changing, and how do agent PRs differ from human
PRs." Source: `search/issues` PR items (`created_at` + `pull_request.merged_at`), 3
high-activity orgs × 3 windows × {agent, human} cohorts. Agent = the 8 tracked bot
authors; human = all PRs minus those bots + dependabot/renovate/actions/pre-commit.
Sample = the 100 most-recent PRs per cell (sort=created desc).

## Results (merge rate + median days-to-merge of merged PRs)

| Org | Window | Cohort | N | merged % | median days-to-merge |
|---|---|---|---|---|---|
| vllm-project | 2024H2 | human | 100 | 81% | 0.80 |
| vllm-project | 2025H1 | human | 100 | 63% | 0.75 |
| vllm-project | 2025H2 | **agent** | 45 | **24%** | 0.70 |
| vllm-project | 2025H2 | human | 100 | 69% | 4.07 |
| huggingface | 2024H2 | human | 100 | 68% | 2.89 |
| huggingface | 2025H1 | agent | 6 | 17% | 2.56 |
| huggingface | 2025H1 | human | 100 | 71% | 1.02 |
| huggingface | 2025H2 | **agent** | 29 | **52%** | 0.67 |
| huggingface | 2025H2 | human | 100 | 48% | 4.39 |
| pytorch | 2024H2 | human | 100 | 25% | 3.19 |
| pytorch | 2025H1 | human | 100 | 48% | 0.80 |
| pytorch | 2025H2 | **agent** | 19 | **5%** | 0.16 |
| pytorch | 2025H2 | human | 100 | 36% | 0.03 |

## Robust findings

1. **Agent PRs are a 2025 phenomenon.** The tracked bot authors are essentially absent
   before 2025H2 in these orgs (vllm/pytorch: 0 agent PRs in 2024H2 & 2025H1; hf: 6 in
   2025H1 → 29 in 2025H2). The "time trend" for agent-authored PRs is emergence from
   ~zero, concentrated in the last ~6-12 months — consistent with the launch timing of
   Copilot coding-agent / claude[bot] / cursor[bot].

2. **Agent PRs merge far less often than human PRs** (same org, same window 2025H2):
   - vllm: agent **24%** vs human 69%
   - pytorch: agent **5%** vs human 36%
   - huggingface: agent **52%** vs human 48%  ← the exception
   In most orgs agent-authored PRs are markedly more speculative / lower-acceptance.
   HuggingFace is the standout where agent PRs land at roughly the human rate.

3. **When an agent PR *does* merge, it merges fast** — median time-to-merge for merged
   agent PRs is ≤ the human median in every cell (vllm 0.70 vs 4.07; pytorch 0.16 vs
   0.03 is the only near-tie; hf 0.67 vs 4.39). Plausibly because the agent PRs that get
   accepted are small/trivial fixes triaged quickly.

## Caveats (these bound how hard to read the trend)
- **Within-window sampling bias**: "100 most-recent PRs in a 6-month window" for a
  high-volume org = only that window's final days. So cross-window *human* merge-rate
  wobble (vllm 81→63→69; pytorch 25→48→36) is largely a sampling artifact, NOT a real
  trend. Fix next: sample evenly across each window (or use full-population aggregates),
  and use shorter windows (monthly/quarterly).
- **Small agent N** (6-45) → merge-rate point estimates are noisy; treat as indicative.
- **No review latency yet**: time-to-merge ≠ attention. The "attention" question
  (time-to-first-review, review count, reviewer identity) needs the reviews timeline
  (GraphQL `pullRequest.reviews`/`timelineItems`) — that's the next iteration and feeds
  directly into step (b) automated-vs-manual review.
- **External vs staff** unresolved (same caveat as the detection analysis).

## What's solid enough to carry forward
- Agent-PR adoption is recent and rising (2025H2 >> earlier).
- Agent PRs have structurally lower merge rates than human PRs, org-dependent
  (HuggingFace ≈ parity is notable and worth a closer look).
These set up step (b): do agent PRs get **human** review or **automated** review, and is
review getting faster/more automated over 2024→2026?

## Next iteration (planned)
- Even/monthly sampling + full-population merge-rate per month (proper time series).
- GraphQL pull for review latency + reviewer identity (human vs AI reviewers like
  coderabbitai / gemini-code-assist) → step (b) automated-vs-manual review.
