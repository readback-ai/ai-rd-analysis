# RUBRIC: what counts as an AI R&D repository

Version: v1 (Phase 0.2, 2026-06-25). Decisions resolved by Ron's gold-set audit.
Versioned; ships with every dataset/trend claim. Proposed gold labels applied;
human audit of flagged rows still finalizes `human_label`.

## Definition

A repository is **AI R&D** if its *primary purpose* is building, training, serving,
evaluating, or researching machine-learning models or autonomous agent systems.
Merely *consuming* an AI API does not qualify.

## Four labels

- **BUILDS_AI** (primary target): training/fine-tuning, inference/serving engines,
  eval harnesses, datasets/data-prep for training, original ML research/experiments,
  model repos, **AND all autonomous agent systems** — agent frameworks/runtimes/
  protocols *and* finished autonomous-agent products (Ron's call: "all agent systems
  = BUILDS").
- **AI_INFRA** (separate cohort): AI/agent-specific *tooling and infrastructure* that
  supports building/running AI but is not itself a model, training/serving engine,
  eval harness, or an autonomous agent. E.g. MCP servers/toolboxes, context/memory/
  retrieval utilities, vector/embeddings infra, RAG chunking libs, coding-agent
  scaffolding/plugins/skills/harnesses, agent task hubs, agent sandboxes, agent
  management UIs, LLM-data infra.
- **USES_AI**: products/apps that *consume* a model/agent — chatbots, AI features in
  a domain app, RAG Q&A apps, single-shot LLM utilities, **domain apps that train/run
  their own ML model** (applied ML is USES, not BUILDS — Ron's call).
- **NOT_AI**: no meaningful AI building or use — websites, portfolios, generic apps,
  games, domain CRUD, dev utilities, dotfiles, docs.

Keep-set for Stage 3 hydration: **BUILDS_AI** (primary). Retain **USES_AI** and
**AI_INFRA** as labeled comparison cohorts (do not drop).

## Decision rules (priority order)

1. **Primary purpose governs**, judged from description + topics + README (+ manifest).
   Marketing tags and incidental deps never decide it. (Measured: the cheap rule
   anchor agreed with human judgment only ~46% of the time — rules alone are
   insufficient; the LLM tier is required.)

2. **BUILDS_AI — model work**: train/fine-tune/serve/evaluate/quantize, datasets &
   data-prep for training, embeddings/vector work done as research, original ML
   experiments, model repos. (gold: OCR/LSTM engine, KVCache LLM serving, diffusion
   LoRA dataset prep, modulation-recognition DL, LLM-as-compressor research, ONNX
   inference engine, decentralized fine-tuning, eval control-plane.)

3. **BUILDS_AI — agent systems** (frameworks AND products): anything whose purpose is
   an autonomous agent — crewAI/mastra/PraisonAI/LangChain loops/A2A protocols, and
   also autonomous-agent *products* (a coding-agent tool, an autonomous assistant, an
   autonomous pentester). The distinction "framework vs product" does NOT change the
   label; both are BUILDS. This **includes agentic orchestration / self-evolution
   engines and platforms** that plan+act over multi-step reasoning loops (gold:
   `EXboys/skilllite` self-evolution agent loop; `alex-place/lantern-os` convergence-
   orchestration platform). "Agents are everywhere" — when a repo *is* or *runs* an
   agent, it is BUILDS, even if branded as a platform/OS/engine.

4. **AI_INFRA vs BUILDS agent systems** (narrow line — Ron's call 2026-06-25): the
   test is **does the repo itself plan/act?** If it *is* an agent, a framework to build
   agents, or an orchestration/self-evolution engine that plans+acts → BUILDS. If it is
   a **passive component consumed BY agents** and does not itself act (memory/context
   utils, vector/embeddings stores, RAG/chunking libs, MCP tool servers, coding-agent
   scaffolding/linters/plugins/skills, task hubs, sandboxes, mgmt UIs, installers) →
   AI_INFRA. "Supports agents" alone is not enough for BUILDS; it must act.
   - *Signal trap 1*: an "OS"/platform branded with systems-ops topics (dual-boot,
     windows, powershell) is NOT automatically NOT_AI. If it is an app-level platform
     orchestrating reasoning / multi-step cognitive work, it's **BUILDS** — the systems
     framing is surface noise (gold: `alex-place/lantern-os`, which the LLM tier
     mislabeled NOT_AI on the "OS + boot" framing).
   - *Signal trap 2*: "sandbox/engine" branding can hide an agent. `EXboys/skilllite`
     reads as a sandbox (→ would be AI_INFRA) but the README ships a full agent loop +
     swarm → **BUILDS**. Read past the one-liner before calling sandbox/engine repos.

5. **USES_AI** = consumes capability: a finished app/feature calling a model, a RAG
   Q&A app, a single-shot LLM utility, OR a domain product that trains/runs its own
   ML (applied ML = USES). Trivial "uses an LLM agent" apps are USES, not BUILDS.

6. **Dual-signal deps**: a real training/serving stack (`torch`/`transformers`/`jax`/
   `vllm`/`deepspeed`/...) + a client SDK → BUILDS_AI. BUT embeddings/RAG client libs
   (`sentence-transformers`, `chromadb`) are NOT a training stack — a consumer RAG app
   pulling them + `openai` is **USES_AI** (gold: `Murs2024/RAG-reglament`).

7. **"Training" disambiguation**: human training (LMS, fitness apps, flight sims) is
   NOT_AI. Only *model* training counts.

8. **Incidental / marketing AI → ignore** (lone unused `openai` dep, `ai` topic on a
   workout tracker). **Vapor/empty repos** → judge by actual content; usually USES_AI
   if it calls an LLM, else NOT_AI, low confidence, flagged.

## Gold set notes
- 4-class proposed distribution (180): BUILDS 38 / USES 25 / AI_INFRA 21 / NOT 96.
  70 flagged for audit (all L + boundary M). Confidence H/M/L per row.
- Over-samples positives (not base-rate); the wild is heavily NOT_AI. Report
  base-rate-reweighted precision, not raw gold precision.
- Per-stratum: `uses_desc` and `generic` strata are ~95% NOT_AI; `ai_topic` holds
  most BUILDS/AI_INFRA. The topic signal has poor precision AND recall.

## Residual judgment calls still flagged for Ron
- Vapor/grandiose solo repos (USES vs NOT_AI).
- A few agent-product-vs-AI_INFRA edges (e.g. agent-hosting IDE apps, mgmt panels).
- "Agentic newsroom/platform" repos: product (USES) vs autonomous agent (BUILDS).
- Empty-README repos defaulted to NOT_AI.
