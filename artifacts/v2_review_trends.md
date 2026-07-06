# Human-review trends by cohort — v2 census (2026-07-06)

Pooled over the full v2 census (~370k PRs; dedup'd; per-period cohorts).
Cohort cuts: (1) PR contains AI-written code (v1 markers); (2) PR received an
AI-reviewer review. Quality proxies: review rounds, inline comments per
human-reviewed PR, % substantive (>=1 inline comment or COMMENTED/
CHANGES_REQUESTED). Body text is not stored, so text-depth is not measured.
Pooled, not repo-weighted — composition shifts across repos can contribute.

## 1) Human review of AI-code vs non-AI-code PRs
| period | cohort | N | humRev% | med 1st-human (h) | med rev->merge (h) | rounds | inline/PR | subst% |
|---|---|---|---|---|---|---|---|---|
| Q1-2024 | non-AI | 61,111 | 65.3 | 3.6 | 1.3 | 2.78 | 2.27 | 37.9 |
| Q4-2025 | AI-code | 2,665 | 44.7 | 6.8 | 1.0 | 2.58 | 2.17 | 44.5 |
| | non-AI | 101,879 | 66.3 | 3.7 | 1.3 | 2.65 | 2.04 | 37.2 |
| Q1-2026 | AI-code | 12,866 | 47.8 | 6.9 | 1.9 | 2.86 | 2.39 | 47.6 |
| | non-AI | 126,938 | 59.8 | 4.0 | 1.3 | 2.65 | 2.05 | 38.2 |
| Q2-2026 | AI-code | 22,794 | 52.4 | 5.2 | 2.0 | 2.88 | 2.39 | 46.9 |
| | non-AI | 147,562 | 54.6 | 4.2 | 1.0 | 2.51 | 1.84 | 38.3 |

- Human-review-rate GAP converged: -21.6pp (Q4-25) -> -2.2pp (Q2-26); AI-code
  review rate RISING (44.7->52.4) while non-AI FALLING (66.3->54.6).
- When reviewed, AI-code gets DEEPER review than non-AI: more substantive
  (46.9 vs 38.3), more inline comments (2.39 vs 1.84), more rounds, and ~2x
  longer first-review->merge (2.0h vs 1.0h).

## 2) Human review of AI-reviewed vs non-AI-reviewed PRs
| period | cohort | N | humRev% | med 1st-human (h) | med rev->merge (h) | rounds | inline/PR | subst% |
|---|---|---|---|---|---|---|---|---|
| Q1-2024 | AI-rev | 165* | 69.1 | 28.1 | 53.5 | 4.70 | 6.24 | 79.8 |
| | no | 60,946 | 65.3 | 3.6 | 1.3 | 2.77 | 2.25 | 37.8 |
| Q4-2025 | AI-rev | 23,562 | 76.5 | 3.4 | 3.9 | 3.23 | 2.77 | 51.8 |
| | no | 80,982 | 62.6 | 3.9 | 0.8 | 2.44 | 1.78 | 32.2 |
| Q1-2026 | AI-rev | 35,196 | 71.8 | 4.0 | 4.9 | 3.43 | 2.95 | 55.4 |
| | no | 104,608 | 54.3 | 4.2 | 0.7 | 2.33 | 1.68 | 31.6 |
| Q2-2026 | AI-rev | 44,019 | 67.6 | 3.9 | 4.4 | 3.34 | 2.81 | 57.3 |
| | no | 126,337 | 49.6 | 4.6 | 0.6 | 2.19 | 1.49 | 30.9 |
(*tiny early-adopter N)

- **AI review is a PR-level COMPLEMENT, not substitute**: AI-reviewed PRs get
  human review at +18pp (67.6 vs 49.6, Q2-26) with far deeper human review
  (subst 57.3 vs 30.9; inline 2.81 vs 1.49; in-review 4.4h vs 0.6h).
- The aggregate human-review decline is compositional: it concentrates on the
  growing mass of PRs receiving NEITHER kind of review.
- Selection caveat: repos/PRs that adopt AI reviewers likely differ in rigor;
  no causal claim.

## 3) Human review-time trends
- Median time-to-first-human-review roughly stable (3.6 -> ~4.2-4.6h on
  ordinary PRs; AI-code PRs wait longer but converging 6.8 -> 5.2h).
- Time-in-review (first human review -> merge) is POLARIZING: ordinary
  non-AI-reviewed PRs sped up 1.3 -> 0.6h (quicker rubber-stamps) while
  AI-involved PRs hold at 2-5h.

## 4) Human comment-quality trends (proxies)
- On ordinary PRs, human review is getting SHALLOWER: inline comments/PR
  2.25 -> 1.49, rounds 2.77 -> 2.19, substantive 37.8% -> 30.9% (2024->Q2-26).
- Where AI is involved (code or review), human depth HOLDS or RISES
  (subst 44.5 -> 46.9 on AI-code; 51.8 -> 57.3 on AI-reviewed).
- Net narrative: **attention polarization** — human scrutiny is draining from
  ordinary PRs and concentrating on AI-involved ones.
