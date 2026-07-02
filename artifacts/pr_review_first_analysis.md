# First analysis (b): automated vs manual PR review (2026-06-26)

Sample: 2025H2 PRs in vllm-project / huggingface / pytorch, agent vs human cohorts,
pulled via GraphQL with each PR's reviews. **Automated vs manual = reviewer
`__typename`: Bot vs User.** Latency = PR createdAt → first review submittedAt.

## Results

| Org | cohort | N | no review | ≥1 human rev | ≥1 bot rev | med 1st-review (h) | med 1st-human (h) |
|---|---|---|---|---|---|---|---|
| vllm-project | agent | 45 | 53% | 42% | 27% | 0.5 | 0.5 |
| vllm-project | human | 100 | 3% | 73% | **80%** | **0.0** | 5.9 |
| huggingface | agent | 29 | 41% | 55% | 14% | 0.7 | 1.0 |
| huggingface | human | 100 | 63% | 34% | 6% | 138 | 156 |
| pytorch | agent | 19 | 68% | 32% | 11% | 1.6 | 1.6 |
| pytorch | human | 100 | 36% | 64% | 1% | 69 | 69 |

Bot/AI reviewers seen: **gemini-code-assist 71, copilot-pull-request-reviewer 23,
greptile-apps 1** (dedicated AI reviewers) — plus coding-agent logins appearing as
review authors: copilot-swe-agent 55, chatgpt-codex-connector 17, cursor 9 (needs
interpretation — agents reacting to / on their own PRs vs reviewing others').

## Findings

1. **Automated review is real and near-instant — but org-specific.** vLLM auto-reviews
   80% of human PRs (gemini-code-assist + Copilot reviewer), median first review **0.0h**
   (minutes) vs **5.9h** to first *human* review. So on vLLM, the *first* eyes on a PR
   are almost always a bot, hours before a human. HuggingFace is the opposite — 6% bot
   review, 63% no formal review, and **156h (6.5 days)** to first human review. pytorch
   is mostly manual (64% human, 1% bot, 69h). "Automated vs manual" is a culture/tooling
   choice that varies wildly between top orgs.

2. **Agent-authored PRs get *less* attention, not more.** No-review rates are high for
   agent PRs (vllm 53%, hf 41%, pytorch 68% receive no formal review at all). Combined
   with their low merge rates (prior analysis), many agent PRs are opened and dropped
   without anyone — human or bot — reviewing them. The minority that are reviewed get
   triaged fast (0.5–1.6h).

3. **Where review is manual, it's slow** (hf 6.5 days, pytorch ~3 days to first human
   review on human PRs); where automated, it's instant. The automation is compressing
   *first-touch* latency by ~1-2 orders of magnitude on the orgs that adopt it.

## Caveats
- 2025H2 only — no time trend for review automation yet (next: monthly 2024→2026).
- Small agent N (19–45); point estimates indicative.
- "no review" = no formal *review* submission; plain issue-comments aren't counted, so
  true "zero attention" may be slightly lower.
- Coding-agent logins as reviewers (copilot-swe-agent/codex/cursor) need a closer look
  before attributing them as "AI review."

## Scaling to full data — volume sizing

| Org | total PRs | agent PRs (all-time) |
|---|---|---|
| pytorch | 219,210 | 100 |
| huggingface | 98,289 | 39 |
| langchain-ai | 60,749 | 109 |
| vllm-project | 55,027 | 99 |
| openai | 34,999 | 86 |
| anthropics | 12,184 | 4 |
| QwenLM | 4,200 | 6 |
| modular | 3,590 | 0 |
| mistralai | 2,024 | 0 |
| deepseek-ai | 1,944 | 3 |
| OpenBMB | 1,772 | 0 |
| fw-ai | 932 | 0 |

**Takeaway:** total PRs are large for the big framework/infra orgs (pytorch 219k, hf
98k, langchain 61k) — full human-PR census across the whole org set is millions. BUT
**agent-authored PRs are a tiny census** (tens–low hundreds per org; many orgs zero) —
a few thousand total across all orgs. So:
- **Full census of agent PRs** across the entire org set is trivial — enumerate + hydrate
  reviews/timing for *every* agent PR.
- **Human PRs**: full-pull the small pure-play labs (≤ a few k each); **monthly-stratified
  sample** the big orgs (pytorch/hf/langchain/vllm) — enough for robust medians without
  pulling 200k PRs.
- **Commit-trailer adoption** (Claude/Cursor) stays as aggregate counts (already cheap).

## Next
- Recommended full-analysis scope: agent-PR census (all orgs) + stratified human baseline,
  pulled monthly 2024-01→2026-06, with reviews → gives the **time trend** in (a) attention
  and (b) review automation in one pass. Size GraphQL points + wall-clock in `cost_estimate.md`.
