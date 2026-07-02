# First analysis: AI-code-assistance detection across the org set (2026-06-26)

First pass of the org-provenance detection methodology over a 16-org representative
sample (frontier labs, China labs, infra/framework, funded startups). Signals:
bot-authored PRs (8 agents OR'd), Claude-Code commits (BARE-TERM `noreply@anthropic.com`),
Cursor-Agent commits (BARE-TERM `cursoragent@cursor.com`). Counts are GitHub search
`total_count`, public repos only, not yet member-filtered.

## Results

| Org | bot-PRs | Claude commits | Cursor commits | profile |
|---|---|---|---|---|
| anthropics | 4 | **3452** | 0 | Claude dogfood; no Cursor |
| huggingface | 39 | **1556** | 267 | heaviest overall adopter; both tools |
| langchain-ai | 109 | 1411 | 80 | Claude-leaning + many bot-PRs |
| vllm-project | 99 | 799 | 74 | both; high bot-PR (ext. contributors) |
| pytorch | 100 | 253 | 94 | both; high bot-PR |
| QwenLM | 6 | 251 | 7 | Claude-leaning |
| fw-ai (Fireworks) | 0 | 67 | 32 | both, no bot-PRs |
| MoonshotAI | 5 | 56 | 3 | Claude-leaning |
| OpenBMB | 0 | 55 | **799** | Cursor-dominant |
| openai | 86 | 37 | 0 | bot-PRs (Copilot/Codex) + some Claude |
| anysphere (Cursor) | 0 | 33 | 4 | Claude > own Cursor trailer (interesting) |
| mistralai | 0 | 19 | 6 | modest; invisible to author-search |
| deepseek-ai | 3 | 5 | 0 | light public footprint |
| google-deepmind | 3 | 3 | 0 | near-dark in public |
| meta-llama | 0 | 0 | 0 | dark (private dev / untracked tools) |
| lumalabs | 0 | 0 | 0 | dark |

## Headline findings

1. **The bare-term correction is enormous.** Compare to the earlier `author-email:`
   cross-tab (which is what naive tooling / prior work would use):

   | Org | `author-email:` (old) | bare-term (correct) | undercount |
   |---|---|---|---|
   | huggingface | 99 | 1556 | ~16x |
   | vllm-project | 0 | 799 | ∞ |
   | QwenLM | 0 | 251 | ∞ |
   | pytorch | 0(n/a) | 253 | — |

   Any agent-adoption measurement using `author-email:` undercounts Claude-Code usage
   by ~10-16x (and misses it entirely where the agent is only a co-author). **Use
   bare-term.** This is the single most important methodological result so far.

2. **Tool profiles are sharply org-specific** — adoption is not monolithic:
   - **Claude-dogfood**: anthropics (3452, zero Cursor — they use their own tool).
   - **Cursor-dominant**: OpenBMB (799 Cursor vs 55 Claude).
   - **Both, heavy**: huggingface, vllm, pytorch, langchain, fw-ai.
   - **Claude-leaning**: QwenLM, MoonshotAI.
   This "adoption by org × tool" cut is the unique payoff of the org-provenance design.

3. **The "dark labs" split into two kinds.** Some are *not* dark once you use bare-term
   (mistralai 19+6, QwenLM 251+7, MoonshotAI 56+3 — invisible to author-search, visible
   via trailers). Others stay genuinely dark (meta-llama 0, lumalabs 0, google-deepmind
   ~3) — consistent with private-repo development or untracked local tools (Codex CLI,
   Windsurf), which leave no public marker at all.

4. **Two different behaviors are being measured.** bot-PRs = delegated CLOUD agents that
   open PRs (Copilot/Devin/Codex-cloud); commit trailers = IDE/CLI co-authoring
   (Claude Code, Cursor Agent). They cluster differently: bot-PRs peak at big community
   OSS (langchain 109, pytorch 100, vllm 99) where many openers are EXTERNAL
   contributors; trailers peak at labs dogfooding their own dev (anthropics, hf).

## Caveats (to resolve next)
- **External vs staff**: bot-PRs and trailers on an org's repos include outside
  contributors. The "own practices" claim needs a member filter (PR/commit author ∈ org).
- **Public only**: labs do much work in private repos; meta-llama/lumalabs "0" is a
  public-visibility statement, not "no AI use".
- **Bare-term false positives**: a commit literally quoting the email/footer counts;
  expected to be a tiny fraction vs real trailers.
- **Commits != PRs != lines**: these are commit/PR counts, not volume of AI-written code.

## Next step (per Ron, 2026-06-26)
Investigate **change over time** in (a) PR attention — time-to-first-review,
time-to-merge, review latency — and (b) **automated vs manual PR review** (e.g.
human reviews vs bot/AI reviewers like coderabbitai/gemini-code-assist, review
turnaround, approval patterns). This first detection pass gives the org × tool
denominator those time-series will be sliced against.
