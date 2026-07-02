# AI-written-code PRs — quarterly trend Q3-2025 → Q2-2026 (2026-06-26)

Reframed cohort (per Ron): classify PRs by whether they **contain AI-written code**
(commit co-author trailer `noreply@anthropic.com` / `cursoragent@cursor.com`, or footer
`Generated with [Claude Code]`), NOT by whether a bot authored the PR. This captures the
dominant real pattern — a human opens the PR but the commits were written with AI — which
the agent-author cohort missed (HF: 1556 Claude commits vs only 39 agent PRs).

Meta-controlled orgs EXCLUDED (pytorch, meta-llama, facebookresearch): Meta's AI use is
internal tooling, invisible to public attribution, so their signal is misleading.

Window: quarterly, Q3-2025 → Q2-2026 (Q2-2026 partial, through 06-26).
Sample: most-recent 100 PRs per org per quarter (GraphQL, commits+reviews).

## AI-code PR % by quarter

| org | Q3-2025 | Q4-2025 | Q1-2026 | Q2-2026 |
|---|---|---|---|---|
| vllm-project | 0% | 1% | 8% | **21%** |
| langchain-ai | 0% | 1% | 13% | 12% |
| huggingface | 0% | 7% | 3% | 8% |
| QwenLM | 2% | 2% | 4% | 1% |
| anthropics | 38% | 36% | 25% | 3% ⚠ |

Tool: almost entirely Claude in these orgs (Cursor only langchain Q2: 5; OpenBMB — not
sampled here — was Cursor-dominant earlier; tool mix is org-specific).

## Findings
1. **Sharp rise in AI-written-code PRs** where the trend is clean: vLLM 0→1→8→**21%**,
   LangChain 0→1→13→12% across Q3'25→Q2'26. By Q2 2026 ~1 in 5 of vLLM's recent PRs
   carried AI-written commits. This matches the expectation that Q3'25 and Q2'26 are
   qualitatively different regimes.
2. **The reframe matters**: PR-with-AI-code is a much larger, more representative signal
   than bot-authored PRs (which were tens per org and falling out of the picture).

## Caveats (bound the per-quarter precision)
- ⚠ **anthropics 38%→3% is a sampling artifact, not a real decline.** "Most-recent-100
  PRs/quarter" across a multi-repo org confounds *which repos were active*; a quarter whose
  recent PRs land in a docs/SDK repo (or a repo that squash-strips co-author trailers)
  reads low. Anthropic has 3452 Claude commits all-time — they are not using Claude less.
- Same bias likely **undercounts** huggingface/QwenLM and makes within-org quarter wobble
  unreliable. Trust the strong monotonic climbs (vllm, langchain) and the overall
  direction, not individual quarter deltas.
- Squash-merge can strip co-author trailers at merge → PR-level undercount; the footer
  text survives more often, which is why footer + trailer are both checked.

## Fix for trustworthy per-quarter rates (→ full-data plan)
- Sample **evenly within each quarter** (or full-enumerate) instead of most-recent-100.
- Detect at the **commit level then map to PRs** (search/commits trailer → associated PR),
  which avoids the repo-mix bias and recovers trailer-stripped-at-squash cases.
- Carry the same agent-PR census + stratified-human baseline plan from
  `pr_review_first_analysis.md`, quarterly Q3-2025→present.
