# Agent-detection cues beyond PR-author bots (2026-06-26)

Investigation prompted by the org-provenance slice (`ai_labs.yaml`): top model labs
showed ~zero **attributed** agent activity (no bot-authored PRs, no
`author-email:` Claude trailers). Hypothesis: they ARE using AI assistance, just
via local IDE/CLI tools that don't surface through author attribution. Confirmed —
and the investigation overturned a core methodology assumption in `agents.yaml`.

## TL;DR findings

1. **The "dark labs" are heavy AI users.** They were invisible only because we used
   the wrong queries. Real usage surfaces through (a) committed agent-config files,
   (b) the **Cursor co-author trailer**, and (c) the **Claude Code footer text**.
2. **`author-email:` is the wrong qualifier for co-authored commits.** Org-scoped, it
   returns 0; bare free-text search returns the true counts. Stage 0 seed loops must
   use bare-term search, not the `author-email:` qualifier.
3. **Cursor has a commit-trailer detection path we were missing entirely**
   (`Co-authored-by: Cursor <cursoragent@cursor.com>`). OpenBMB alone: 799 commits.

## Cue 1 — committed agent-config files (repo-level adoption signal)
Code search (`filename:`), partial run before rate-limit:

| Org | CLAUDE.md | AGENTS.md | .cursorrules |
|---|---|---|---|
| mistralai | 2 | 9 | 0 |
| QwenLM | 2 | 12 | 0 |
| deepseek-ai | 0 | 0 | 0 |

mistralai/QwenLM commit `AGENTS.md`/`CLAUDE.md` despite 0 attributed agent PRs.
Concrete: `mistralai/{client-python,cookbook,mistral-common,mistral-vibe,
platform-docs-public,workflows-starter-app}` carry AGENTS.md; `QwenLM/{qwen-code,
open-computer-use}` carry CLAUDE.md. Caveat: code-index coverage is uneven
(deepseek's 0 may be indexing, not absence — see Cue 3 where deepseek DOES use Claude).

## Cue 2 — Cursor co-author trailer (NEW detection path)
Cursor's *Agent* writes a co-author trailer; the human remains author/committer, so
`author:cursor[bot]` (our only Cursor path) misses it. Example —
`OpenBMB/MA-ProofBench@123bc54`:
```
Update Readme

Co-authored-by: Cursor <cursoragent@cursor.com>
```
(author = pulushi@modelbest.cn, the human). Bare-term `cursoragent@cursor.com` counts:
OpenBMB **799**, QwenLM 7, mistralai 6. Add `cursoragent@cursor.com` as a commit-
trailer identity for Cursor in `agents.yaml`.

## Cue 3 — Claude Code footer text (more reliable than the email trailer here)
`QwenLM/qwen-code@e15dd2f` and `deepseek-ai/DeepEP@309785a` both carry:
```
🤖 Generated with [Claude Code](https://claude.com/claude-code)
Co-Authored-By: Claude <noreply@anthropic.com>
```
deepseek's DeepEP (a flagship CUDA repo) uses Claude Code — yet the org-scoped
`author-email:` query said 0. The footer text `Generated with [Claude Code]` and the
bare email are reliable; the qualifier is not (Cue 4).

## Cue 4 — `author-email:` qualifier vs bare-term (CRITICAL methodology correction)
Same org, three query forms:

| Org | `author-email:noreply@anthropic` | bare `noreply@anthropic.com` | footer text |
|---|---|---|---|
| deepseek-ai | 0 | 5 | 5 |
| QwenLM | **0** | **251** | 26 |
| SakanaAI | 0 | 33 | 11 |
| OpenBMB (cursor trailer) | 0 | 799 | — |

Global sanity: `author-email:noreply@anthropic.com` = 5.31M; bare
`noreply@anthropic.com` = 15.7M. The qualifier matches only commits where the bot
email is the **primary author**; co-authored commits (human author + agent trailer)
slip through it when org-scoped. **Use bare free-text email/footer search.**

Consequence: the cross-tab "Claude-trail" column (which used `author-email:`) is a
floor, not the truth. huggingface's real Claude usage is ≥99; QwenLM's is ≥251 (not
0); every model lab's Claude/Cursor footprint is materially higher than first measured.

## Secondary marker scan (commit-message text, bare-term)
| Org | "Generated with Claude" | "Co-authored-by: Cursor" | cursoragent | aider | 🤖 |
|---|---|---|---|---|---|
| mistralai | 2 | 6 | 6 | 0 | 1 |
| deepseek-ai | 5 | 0 | 0 | 0 | 5 |
| QwenLM | 65 | 32 | 7 | 2 | 79 |
| SakanaAI | 14 | 0 | 0 | 0 | 11 |
| OpenBMB | 2 | 799 | 799 | 0 | 0 |

Tool profiles differ by lab: OpenBMB → Cursor-heavy; QwenLM → Claude + Cursor + a
little aider; SakanaAI/deepseek → Claude Code. `aider` is detectable via its own
trailer (small volume). Windsurf/Tabnine/Augment/Zencoder remain undetectable (no
trailer, no bot).

## New PR-authoring agents found (global is:pr author counts)
Beyond the original six: `codegen-sh[bot]` 9,564; `claude[bot]` 18,718 (Claude
GitHub app/Action — confirm it's Anthropic's); `amazon-q-developer[bot]` 2,240;
`factory-droid[bot]` 670. Adding them barely moved the lab cross-tab, so the original
six + claude[bot] capture nearly all *detectable* agent PRs.

## Implications
- **Stage 0 seed (commit path): switch from `author-email:` to bare-term** email +
  footer search; add Cursor (`cursoragent@cursor.com`) and aider trailers. Re-verify
  the global Claude figure with bare-term (rate-limited mid-run; ~15.7M bare).
- **The org slice gains a second, higher-recall lens**: even labs with no bot PRs
  reveal AI adoption via config files + co-author trailers + footers. "Adoption by
  lab, by tool" is now measurable and is a headline result.
- **`agents.yaml` needs correction** (Cursor trailer path; author-email caveat) —
  applied alongside this file.

## Open / to re-run after rate-limit cooldown
- Finish config-file matrix for SakanaAI/OpenBMB/EleutherAI (+ copilot-instructions.md,
  GEMINI.md, .windsurfrules).
- Confirm `claude[bot]` is Anthropic's app (inspect one PR's author app slug).
- Re-measure the cross-tab with bare-term Claude + Cursor trailers for a true
  adoption-by-lab table.
