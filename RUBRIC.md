# RUBRIC: what counts as an AI R&D repository

Version: v0 (draft from Phase 0.2 gold-set labeling, 2026-06-25). Status: pending
Ron's audit of the gold set. This file is versioned; every trend claim ships with it.

## Definition

A repository qualifies as **AI R&D** if its *primary purpose* is building, training,
serving, evaluating, or researching machine-learning models or autonomous agent
systems. A repository that merely *consumes* an AI API (an app that calls an LLM)
does not qualify.

Three labels:
- **BUILDS_AI** (target): training frameworks, inference/serving engines, eval
  harnesses, agent *frameworks*, model repos, ML research/experiment code, and
  AI-specific infrastructure that provides core model/agent capability.
- **USES_AI**: products/apps that wrap a model API — chatbots, AI-powered web/mobile
  apps, RAG question-answering apps, assistants, AI features bolted onto a domain app.
- **NOT_AI**: no meaningful AI building or use — websites, portfolios, generic web
  apps, games, domain CRUD, dev utilities, dotfiles, docs.

The unit is the **repository's primary purpose**, judged from description + topics +
README (+ dependency manifest). Marketing tags and incidental dependencies do not
decide it.

## Decision rules (in priority order)

1. **Primary purpose governs.** Label by what the repo *is*, not by keywords it
   mentions. `ai`/`ai-agents`/`llm` topics frequently sit on apps and devtools
   (measured: the topic rule agreed with human labels <50% of the time) — never
   accept on a topic alone.

2. **BUILDS_AI — model work.** Training, fine-tuning, inference/serving, evaluation,
   quantization, datasets/data-prep for training, embeddings/vector infrastructure,
   or original ML research/experiments. Examples (gold): OCR/LSTM engine, LLM serving
   (KVCache), diffusion LoRA dataset prep, modulation-recognition DL research,
   LLM-as-compressor research, ONNX inference engine, decentralized fine-tuning,
   eval control-plane.

3. **BUILDS_AI — agent systems.** *Frameworks, runtimes, protocols, and SDKs for
   building autonomous agents* (e.g. crewAI, mastra, PraisonAI, LangChain agent
   loops, A2A protocols, agent-memory infrastructure libraries). The thing being
   built is reusable agent capability.

4. **USES_AI — agent/LLM products.** A *specific assistant or app* built on top of
   models/agents (a coding-agent product, a personal-assistant app, an AI Chrome
   extension, a RAG Q&A app, a domain dashboard with AI features). It consumes
   capability rather than providing it.

5. **The framework-vs-product line** (rules 3 vs 4) is the main BUILDS/USES boundary.
   Heuristic: *would another developer import this to build their own agent?* → BUILDS.
   *Is this a finished thing an end-user runs?* → USES. When genuinely both
   (a framework that is also a product), favor BUILDS if the reusable library is the
   point; flag for audit.

6. **Dual-signal deps (BUILDS dep + client SDK) → BUILDS_AI** *by Ron's decision*,
   BUT with a refinement found during labeling: **embeddings/RAG client libs
   (`sentence-transformers`, `chromadb`) are NOT a training/serving stack.** A
   consumer RAG app that pulls `sentence-transformers` + `openai` is **USES_AI**, not
   BUILDS. Reserve the auto-BUILDS dual rule for genuine training/serving deps
   (`torch`/`transformers`/`jax`/`vllm`/`deepspeed`/...). (gold ex: `Murs2024/RAG-
   reglament` is USES despite tripping the naive dual rule.)

7. **AI devtools/infra that is NOT core model/agent capability → NOT_AI.** Task
   trackers, context/prompt utilities, code-search helpers, MCP/skill configs,
   scrapers, dotfiles, plugins, and personal harnesses are NOT_AI even when "for
   agents." They tool *around* AI; they don't build it. (gold ex: claw-task-hub,
   context-engine, project-tiny-context-harness, MCP toolboxes, Claude Code plugins.)

8. **"Training" disambiguation.** Human training (LMS, fitness/triathlon apps, flight
   simulators) is NOT_AI. Only *model* training counts.

9. **Incidental / marketing AI → ignore.** A lone `openai` dep that the README never
   uses, or an `ai` topic on a workout tracker, does not move the label.

10. **Vapor / empty repos.** Grandiose claims with no substantiating content →
    judge by what's actually there (usually USES_AI if it calls an LLM, else NOT_AI).
    Empty/near-empty READMEs → NOT_AI, low confidence, flagged.

## Notes on the gold set
- Labels carry a confidence (H/M/L) and `flag_audit`; 66/180 are flagged (all L plus
  boundary M) for Ron's focused review. Flagged clusters: agent-framework-vs-product,
  AI-devtool-vs-BUILDS, dual-signal deps, and vapor/empty repos.
- The gold set over-samples positives (not base-rate); base rates in the wild are
  heavily NOT_AI. Report base-rate-reweighted precision, not raw gold precision.

## Open boundary questions for Ron
- Agent *frameworks* = BUILDS but agent *products* = USES — confirm the line (rule 5).
- AI devtools/infra (rule 7): confirm NOT_AI, or carve a separate "AI-INFRA" cohort?
- Dual-signal refinement (rule 6): confirm embeddings-only ≠ BUILDS.
- ML applied in a domain app (energy forecasting, credit scorecard): BUILDS or USES?
