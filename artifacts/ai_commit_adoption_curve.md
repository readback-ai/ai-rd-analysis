# AI-written-code adoption curve — commit trailers, Q3-2025 → Q2-2026 (2026-06-26)

Robust, no-sampling version of the trend: `search/commits` `total_count` for AI co-author
trailers (`noreply@anthropic.com` = Claude Code, `cursoragent@cursor.com` = Cursor Agent)
by org × quarter, across 33 orgs (Meta excluded). Counts are author-dated. Q2-2026 is
partial (through 06-26). These are a FLOOR — squash-merge strips trailers.

## Overall trend (sum across all orgs)

| tool | Q3-2025 | Q4-2025 | Q1-2026 | Q2-2026 |
|---|---|---|---|---|
| Claude | 261 | 417 | 5320 | 6239 |
| Cursor | 16 | 22 | 231 | 1226 |
| **TOTAL** | **277** | **439** | **5551** | **7465** |

**~27× growth Q3-2025 → Q2-2026**, with the inflection at the turn into 2026
(Q4-2025 439 → Q1-2026 5551, ~13×). Q3-2025 and Q2-2026 are qualitatively different
regimes, as predicted. Claude is ~84% of the signal; Cursor is smaller but growing fast
(16 → 1226), concentrated in a few orgs.

## Adoption leaders (total AI-code commits; Claude/Cursor per quarter)

| org | total | Q3-25 | Q4-25 | Q1-26 | Q2-26 | tool |
|---|---|---|---|---|---|---|
| anthropics | 3387 | 178/0 | 212/0 | **2759**/0 | 238/0 | Claude |
| character-ai | 2007 | 0/0 | 0/0 | 78/0 | **1920**/9 | Claude |
| huggingface | 1815 | 12/0 | 37/0 | 540/101 | 959/166 | Claude |
| langchain-ai | 1476 | 11/0 | 27/0 | 736/41 | 622/39 | Claude |
| allenai | 984 | 8/1 | 39/0 | 529/25 | 357/25 | Claude |
| vllm-project | 873 | 14/0 | 34/0 | 122/17 | 629/57 | Claude |
| OpenBMB | 854 | 0/0 | 0/0 | 2/11 | 53/**788** | **Cursor** |
| sgl-project | 612 | 0/0 | 4/1 | 84/7 | 470/46 | Claude |
| NousResearch | 441 | 2/0 | 1/0 | 94/1 | 302/41 | Claude |
| QwenLM | 258 | 2/0 | 23/0 | 25/4 | 201/3 | Claude |
| basetenlabs | 158 | 0/0 | 1/0 | 85/10 | 56/6 | Claude |
| modelscope | 113 | 0/0 | 0/0 | 1/0 | 109/3 | Claude |

## Normalized adoption RATE (AI commits ÷ total commits) — the trustworthy metric

Denominator = total commits per org per quarter (`org:X author-date:RANGE`, 2026-06-26).

Overall, summed across the 33 orgs:
| | Q3-2025 | Q4-2025 | Q1-2026 | Q2-2026 |
|---|---|---|---|---|
| AI-commit rate | 0.55% | 0.87% | **8.0%** | **9.8%** |
| (AI / total) | 277/50298 | 439/50522 | 5551/69266 | 7465/76096 |

**<1% → ~10% of all commits in three quarters; inflection at Q1-2026.** Floor (squash
strips trailers).

Per-org rate, Q1-2026 → Q2-2026 (orgs with ≥15 AI commits total):
| org | Q1-26 | Q2-26 | note |
|---|---|---|---|
| fw-ai | 18% | **37%** | rate leader (genuine) |
| EleutherAI | 14% | 18% | |
| basetenlabs | 9% | 18% | |
| huggingface | 8% | 15% | high raw counts, diluted by volume |
| allenai | 9% | 14% | |
| anysphere | 9% | 14% | |
| QwenLM | 1% | 10% | |
| vllm-project | 2% | 8% | |
| langchain-ai | 10% | 8% | |
| sgl-project | 2% | 8% | |
| ByteDance-Seed | 1% | 8% | |
| modelscope | 0% | 7% | |
| anthropics | 48%* | 6% | *Q1 = claudes-c-compiler artifact; 6% is the real rate |
| mistralai | 1% | 5% | |
| character-ai | 68% | 65% ⚠ | single repo `larch`, ONE author — artifact |
| OpenBMB | 2% | 47% △ | Cursor; one repo `PilotDeck` but ~8-dev team — real team adoption, concentrated |

**Normalization reshuffles the leaderboard**: HuggingFace led on raw counts but sits at a
15% *rate*; Anthropic's 47.7% Q1 collapses to 5.7% once the artifact quarter is dropped;
Fireworks (fw-ai) is the genuine rate leader at 37%. Near-zero labs (deepseek, google-
deepmind, OpenGVLab, AI21, modular) stay <1%.

## Findings
1. **The adoption inflection is Q1-2026**, near-universal — most active orgs were <1% of
   commits in 2025 and are at 5-37% by Q2-2026. This is the central result.
2. **Claude dominates AI-written code** in public repos (~84%); **Cursor is org-specific**
   — OpenBMB is overwhelmingly Cursor (788 of 854), almost everyone else is Claude.
3. **Adoption leaders**: anthropics (dogfooding), character-ai, huggingface, langchain,
   allenai, vllm, sgl, NousResearch — a mix of frontier labs, infra/framework projects,
   and research orgs.
4. **Genuinely dark top labs** (≈0 across all quarters): google-deepmind, **deepseek-ai**,
   OpenGVLab, bigcode-project, AI21Labs, Tencent-Hunyuan, Aleph-Alpha, modular. They dev
   privately, strip trailers, or use untracked tools (Codex CLI / Windsurf). DeepSeek being
   near-zero is notable for a frontier lab.

## Spikes — RESOLVED: both are concentration artifacts (sanity-checked 2026-06-26)
- **anthropics Q1-2026 = 2759**: 70% of a 100-commit sample is ONE repo `claudes-c-compiler`
  committed by the user `claude` (the agent itself) + `github-actions[bot]` automation in
  the SDK; only ~6 distinct human authors. → a Claude-built experimental project + bot
  noise, NOT org-wide staff adoption.
- **character-ai Q2-2026 = 1920**: **100/100 sampled commits in a single repo `larch` by a
  single author `zhupanov`.** One prolific dev on one project.
- **LESSON**: raw commit counts are dominated by a few repos/authors/bots. The aggregate
  DIRECTION (27× growth, Q1-2026 inflection) holds, but the absolute leaderboard must be
  NORMALIZED — exclude bot committers + single-author repos, or measure AI-code as a
  FRACTION of PRs. Trust the distributed multi-contributor orgs (hf, vllm, langchain, sgl,
  allenai), not single-actor spikes.

## Caveats
- Counts are a FLOOR (squash-merge trailer stripping); footer-text would recover some.
- Q2-2026 partial → trend if anything understated.
- "Dark" ≠ no AI use (private repos / untracked tools / trailer stripping).
- Commits, not PRs or lines — volume proxy.

## Next
- Sanity-check the two spikes (which repos drive them).
- Pick the adoption leaders for the **commit → PR** deep pull: map AI-code commits to PRs,
  then run the attention / manual-vs-automated-review analysis by quarter on that clean
  cohort. Candidates: anthropics, character-ai, huggingface, langchain-ai, vllm-project,
  allenai, sgl-project, OpenBMB (the Cursor case).
