# How AI-written-code PRs are reviewed vs non-AI PRs (first cut, 2026-06-26)

Step (b) on the right cohort: split PRs by whether they CONTAIN AI-written code (commit
trailers/footers) and compare review/attention. Computed from the quarterly GraphQL pull
(commits + reviews already attached — zero new API calls). Pooled across distributed
leaders **huggingface / vllm-project / langchain-ai / QwenLM**, Q3-2025→Q2-2026.
**anthropics excluded** (its AI-code is the `claudes-c-compiler` single-repo/bot artifact).
Automated vs manual = reviewer `__typename` (Bot vs User).

| cohort | N | merged | no review | human rev | bot rev | med 1st-review (h) | med 1st-*human* (h) |
|---|---|---|---|---|---|---|---|
| AI-code PRs | 83 | 49% | **52%** | **35%** | 30% | 0.1 | **2.0** |
| non-AI PRs | 1517 | 59% | 43% | 47% | 25% | 0.3 | 4.1 |

## Read
- AI-code PRs get **less human review** (35% vs 47%) and are **more often unreviewed**
  (52% vs 43%) — they pass through with lighter human scrutiny.
- They get slightly **more automated/bot review** (30% vs 25%).
- They **merge a bit less** (49% vs 59%).
- But when a human *does* review an AI-code PR, it happens **~2× faster** (2.0h vs 4.1h).
- Coherent picture: AI-written-code PRs are reviewed more lightly and lean more on bots;
  the human attention they do get is quicker (smaller/triaged changes?).

## Caveats
- N(AI-code)=83 — indicative, not conclusive. Scale by targeting AI-code PRs (commit→PR
  mapping) rather than relying on the ~5-20% that fall into a most-recent-100 sample.
- Most-recent-100/quarter sampling bias (favours window-end); pooled across orgs of
  different review cultures (vllm bot-heavy, hf manual-heavy).
- "no review" = no formal review submission (issue-comments not counted).

## Next to harden this
- Target AI-code PRs via commit→PR mapping for N in the hundreds.
- Split by quarter to test whether AI-code-PR review is getting more automated over time.
- Add a member filter (staff vs external contributor).

---

# HARDENED (N=205, by quarter + member filter) — supersedes the N=83 cut above (2026-06-26)

7 distributed orgs (huggingface, vllm, langchain, sgl-project, allenai, QwenLM, fw-ai),
Q4-2025→Q2-2026, ~100 PRs/org/quarter, with `authorAssociation` for the member filter.

## AI-code vs non-AI PR review, by quarter
| quarter | cohort | N | merged | noRev | humRev | botRev | med 1st-human (h) |
|---|---|---|---|---|---|---|---|
| Q4-2025 | AI-code | 22 | 77% | 36% | 55% | **55%** | 36.0 |
| Q4-2025 | non-AI | 578 | 67% | 41% | 48% | 30% | 8.7 |
| Q1-2026 | AI-code | 53 | 64% | 45% | 42% | 30% | 24.7 |
| Q1-2026 | non-AI | 547 | 63% | 35% | 56% | 28% | 12.0 |
| Q2-2026 | AI-code | 130 | 28%* | 45% | 28% | **41%** | 2.1 |
| Q2-2026 | non-AI | 570 | 32%* | 48% | 31% | 34% | 0.5 |

\*Q2-2026 merge rates depressed by recency censoring (recent PRs not yet resolved).

**Findings (larger N corrects the earlier hunch):**
- **AI-code PRs lean MORE on bot/automated review and LESS on human review** than non-AI —
  consistent every quarter (botRev gap: Q4 55v30, Q2 41v34; humRev: Q1 42v56, Q2 28v31).
- **AI-code PRs wait LONGER for first human review** (Q4 36h vs 8.7h; Q1 24.7 vs 12; Q2
  2.1 vs 0.5) — opposite of the small-N first cut; the hardened result supersedes it.
- **No clean "automation rising" temporal trend** — bot-review share of AI-code PRs is
  Q4 55% / Q1 30% / Q2 41% (Q4 small N). The stable signal is the *AI-vs-non gap* in
  bot-reliance, not acceleration.

## Member filter (staff vs external) — AI-code PRs, N=205 pooled
- **Insider (MEMBER/OWNER/COLLABORATOR): 46% | External (CONTRIBUTOR/NONE): 54%.**
  Breakdown: COLLABORATOR 86, CONTRIBUTOR 62, NONE 49, MEMBER 8.
- non-AI insider share is **44%** — i.e. AI-written code is **NOT disproportionately from
  outsiders**; insiders produce AI-code PRs at ~their normal share. The AI-adoption signal
  genuinely reflects the labs' OWN practice, not just drive-by external contributions.
- **Insider AI-code PRs**: merged 60%, humRev 43%, botRev 51%. **External AI-code PRs**:
  merged 28%, noRev 52%, humRev 27%. → outside AI-code PRs are far more often ignored and
  rarely merged; insider AI-code PRs are reviewed and land.

## Caveats
- Q2-2026 merge rates censored (recency); compare cohorts *within* a quarter, not merge
  across quarters.
- `COLLABORATOR` is an imperfect insider proxy (repo-scoped write access); MEMBER is
  under-counted because org membership is often private.
- Most-recent-100/org/quarter sampling (window-tail bias), consistent across cells.

---

# AI-code vs non-AI on the FULL census + review DEPTH/TIME (2026-06-29)

## Rate comparison (full 50k-PR census, pooled by period)
| period | cohort | N | merge% | noRev% | humRev% | botRev% |
|---|---|---|---|---|---|---|
| Q4-2025 | AI-code | 243 | 44 | 39 | 47 | 28 |
| | non-AI | 9000 | 79 | 26 | 65 | 30 |
| Q1-2026 | AI-code | 1727 | 57 | 56 | 37 | 20 |
| | non-AI | 12292 | 70 | 35 | 54 | 29 |
| Q2-2026 | AI-code | 2733 | 65 | 40 | 50 | 33 |
| | non-AI | 13942 | 64 | 38 | 47 | 34 |
**AI-code PRs were second-class in late 2025 (merge 44% vs 79%) but CONVERGED to parity by
Q2-2026 (merge 65% vs 64%; review rates ~equal).**

## Review depth & time (840-PR balanced sample: 120/cohort/period)
| period | cohort | %human-rev | mean rounds | mean inline cmts | %substantive | med rev→merge h | med PR size |
|---|---|---|---|---|---|---|---|
| Q1-2024 | non-AI | 55 | 2.8 | 2.3 | 58 | 2.3 | 43 |
| Q4-2025 | AI-code | 47 | 1.6 | 1.0 | 34 | 0.2 | 137 |
| | non-AI | 62 | 2.8 | 2.0 | 47 | 1.2 | 66 |
| Q1-2026 | AI-code | 36 | 2.8 | 2.0 | 53 | 1.6 | 192 |
| | non-AI | 61 | 2.7 | 2.5 | 48 | 0.9 | 66 |
| Q2-2026 | AI-code | 43 | 3.7 | 2.7 | 65 | 5.9 | 137 |
| | non-AI | 50 | 2.2 | 1.6 | 53 | 0.7 | 82 |

Metrics: %human-rev = share with ≥1 human (User) review; rounds = mean human reviews per
reviewed PR; inline cmts = mean inline review comments; %substantive = reviewed PRs with
≥1 inline comment or non-empty review body; rev→merge = first-human-review→merge hours;
size = additions+deletions.

**Findings:**
1. **AI-code PRs are ~2× larger** (130-190 vs ~65-80 lines).
2. **Review of AI code INTENSIFIED over time** — from under-reviewed/rubber-stamped in
   Q4-2025 (34% substantive, 1.0 comment, 0.2h to merge) to MORE scrutinized than human
   PRs by Q2-2026: more rounds (3.7 vs 2.2), more inline comments (2.7 vs 1.6), more
   substantive (65% vs 53%), ~8× longer in review (5.9h vs 0.7h).
3. AI-code PRs remain slightly less likely to get ANY human review (43% vs 50%) — bots
   handle more of the first pass.

## Caveats (depth/time)
- 120/cohort/period sample → latency & body-length means are noisy (outlier-sensitive).
- Most human reviews are bare approvals (median inline comments = 0), so depth signal is
  in the means / substantive-share, not medians.
- "time in review" = first-human-review→merge; review *span* is ~0 for single-review PRs.
