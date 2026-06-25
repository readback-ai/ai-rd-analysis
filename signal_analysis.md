# Signal analysis (Phase 0.3)

Measured 2026-06-25 on the 180-repo gold set (labels = Claude's proposed 4-class,
post Ron's policy audit; flagged rows pending final confirmation). Reproduce:
`uv run python src/signal_analysis.py` (numbers below inlined).

The gold set **over-samples positives** (BUILDS 38 / USES 25 / AI_INFRA 21 / NOT 96),
so precision here is optimistic vs the wild, where NOT_AI dominates far more. Treat
recall as the more transferable number; reweight precision to base rates downstream.

## Per-signal precision/recall

Predicting **BUILDS_AI**:

| signal | precision | recall | note |
| --- | --- | --- | --- |
| AI topic present  | 0.40 | 0.53 | topics sit on many apps → weak precision |
| any topic present | 0.37 | 0.58 | worse |
| training/serving dep (`builds_dep`) | 0.69 | 0.29 | precise-ish, low recall |
| dual-signal dep   | 0.71 | 0.13 | precise, rare |
| language = Python | 0.34 | 0.53 | noise |

Predicting **BUILDS_AI ∪ AI_INFRA** ("broad AI R&D"):

| signal | precision | recall |
| --- | --- | --- |
| training/serving dep | **0.81** | 0.22 |
| AI topic present | 0.62 | 0.53 |
| any AI dep (build or client) | 0.68 | 0.36 |
| any topic | 0.55 | 0.56 |

Predicting **NOT_AI** (for auto-reject):

| signal | precision | recall |
| --- | --- | --- |
| no topic AND no AI dep | 0.75 | 0.82 |
| no topic | 0.68 | 0.84 |

Predicting **USES_AI**:

| signal | precision | recall |
| --- | --- | --- |
| client SDK only (`uses_dep` & not build) | 0.27 | 0.16 |

Rule-anchor confusion (rows = cheap-rule guess, cols = audited label):

```
    rule\label    BUILDS  USES  INFRA  NOT
    BUILDS_AI         33    14    13    15     (precision 44%)
    USES_AI            2     3     1    34
    NOT_AI             3     8     7    47
```
(The cheap rule agreed with the audited label only ~46% overall.)

## What the numbers mean

1. **No cheap signal is good enough to auto-decide the positive class.** The best
   precision for an auto-accept is a real training/serving dependency
   (`torch/transformers/jax/vllm/...`) at P≈0.81 for broad AI R&D — but it fires on
   only ~22% of true positives. Topics are weak in BOTH directions (P 0.40 / R 0.53).
2. **Absence is not safe to auto-reject.** "No topic and no AI dep" predicts NOT_AI at
   P=0.75 — i.e. ~1 in 4 no-signal repos is actually AI (apps/infra that declare no
   topic and pull no recognized dep). Auto-rejecting on absence would wrongly drop a
   quarter of AI repos. Recall of the keep-set matters (floor 0.70), so we cannot.
3. **Client-SDK presence does not identify USES** (P=0.27); the BUILDS/USES line is
   semantic, not dependency-based, beyond the training-stack case.
4. **Org allowlist is near-useless in THIS population.** The agent-PR universe is
   overwhelmingly small personal repos (1845 owners / 2016 repos); a big-AI-org
   allowlist would have very high precision but negligible recall here. Keep it as a
   cheap high-precision accept, but expect it to cover a tiny fraction.

## Decisions for the Stage 2 layered classifier

- **Auto-accept (high precision, low coverage):**
  - Org allowlist membership → BUILDS_AI (precision high; coverage tiny here).
  - Real training/serving dependency present → BUILDS_AI candidate (P≈0.8). Note:
    embeddings/RAG libs excluded per RUBRIC rule 6.
- **Auto-reject:** none on cheap signals alone — absence is only P≈0.75, below what a
  ≥0.70 recall floor tolerates. (Optionally pre-reject obvious non-software, but the
  data shows little safe headroom.)
- **Everything else → LLM tier.** In practice that is the large majority of repos.
  The spec's "cheap rules first, LLM on residual" still holds, but the residual is
  big: **budget LLM classification for ~70–80% of candidate repos**, not a small
  tail. This materially affects the cost estimate (0.5).
- The LLM tier must implement the full RUBRIC (4 classes, agent-systems=BUILDS,
  applied-ML=USES, dual-signal refinement), since that is where almost all accuracy
  comes from.

## Caveats
- Labels are provisional pending audit of the 70 flagged rows; re-run after audit.
- Single-month (May 2026), agent-PR-sourced population: small personal repos dominate;
  signal behavior may differ for an org-seeded or multi-month population.
