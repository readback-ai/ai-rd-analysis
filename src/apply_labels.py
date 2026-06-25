"""Phase 0.2: merge Claude's proposed labels into the gold worksheet.

4-class scheme (per Ron's audit 2026-06-25): BUILDS_AI / USES_AI / AI_INFRA / NOT_AI.
- All agent SYSTEMS (frameworks AND autonomous products) = BUILDS_AI.
- AI_INFRA = AI/agent-specific tooling/infra that is not a model/engine/eval/agent
  (MCP servers, context/memory utils, vector/embeddings infra, plugins, scaffolding,
  agent task hubs, sandboxes, agent mgmt UIs).
- Applied ML inside a domain product = USES_AI. Embeddings-only RAG apps = USES_AI.

LABELS is in the SAME ORDER as data/gold/gold_repos.csv. Each entry:
(label, confidence H/M/L, flag_audit Y/'', reason). PROPOSED; Ron fills human_label.
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold" / "gold_repos.csv"

LABELS = [
    ("USES_AI", "L", "Y", "sprawling solo 'cognitive engine'/sim consuming LLMs; vapor"),
    ("AI_INFRA", "M", "Y", "npm scaffolding/linters for coding agents"),
    ("BUILDS_AI", "M", "Y", "autonomous agent product + .agents protocol"),
    ("USES_AI", "H", "", "self-hosted AI chat (Ollama); not autonomous"),
    ("BUILDS_AI", "H", "", "causal-inference/econometrics ML library (torch)"),
    ("NOT_AI", "L", "Y", "OS dual-boot/ops repo; openai dep incidental"),
    ("AI_INFRA", "M", "Y", "agent-memory infra library (knowledge graph)"),
    ("USES_AI", "H", "", "resume-drafting app via LLM"),
    ("BUILDS_AI", "M", "Y", "browser-native autonomous agent product"),
    ("USES_AI", "L", "Y", "web3 finance platform for agents; little AI"),
    ("BUILDS_AI", "M", "Y", "AI coding agent product (opencode fork)"),
    ("BUILDS_AI", "L", "Y", "agentic lead-enrichment webapp (search agent)"),
    ("USES_AI", "L", "Y", "energy platform applying ML forecasting [applied ML=USES]"),
    ("BUILDS_AI", "M", "", "chatbot/agent framework library (MCP) [dual]"),
    ("BUILDS_AI", "M", "", "autonomous multi-agent software-dev system"),
    ("BUILDS_AI", "L", "Y", "edge agent harness w/ local LLM (Jetson/Pi)"),
    ("BUILDS_AI", "H", "", "OCR engine (LSTM) -- ML model"),
    ("BUILDS_AI", "M", "", "multi-agent deliberation framework"),
    ("BUILDS_AI", "H", "", "AI agent framework (PraisonAI)"),
    ("USES_AI", "M", "Y", "political-intel platform; agentic newsroom is a feature"),
    ("USES_AI", "H", "", "LLM ToS-clause scanner app"),
    ("NOT_AI", "L", "Y", "MMORPG/game engine; AI tags marketing"),
    ("BUILDS_AI", "H", "", "LLM serving platform (KVCache, vllm/sglang)"),
    ("BUILDS_AI", "H", "", "TS AI agent framework (mastra)"),
    ("NOT_AI", "H", "", "workout/nutrition tracker; 'ai' tag spurious"),
    ("USES_AI", "H", "", "AI writing-assistant Chrome extension"),
    ("NOT_AI", "M", "Y", "P2P networking tool; AI tangential (not AI-specific)"),
    ("AI_INFRA", "L", "Y", "Rust agent sandbox/self-evolution engine"),
    ("BUILDS_AI", "M", "Y", "autonomous AI personal-assistant system"),
    ("AI_INFRA", "M", "Y", "task hub for AI agents"),
    ("USES_AI", "M", "Y", "political-intel platform; agentic newsroom feature"),
    ("AI_INFRA", "M", "Y", "context/code-search infra for coding agents"),
    ("USES_AI", "M", "Y", "trading-journal app with AI features"),
    ("USES_AI", "H", "", "syllabus-PDF->calendar via LLM"),
    ("AI_INFRA", "L", "Y", "LLM-ready web-scraping data infra"),
    ("BUILDS_AI", "L", "Y", "portfolio of built AI/RAG/multi-agent systems"),
    ("AI_INFRA", "L", "Y", "Docker wrapper/tooling around OpenClaw"),
    ("USES_AI", "L", "Y", "Android AI chat/IDE app hosting agents"),
    ("AI_INFRA", "M", "Y", "Claude Code workflow-skills plugin"),
    ("NOT_AI", "H", "", "notifications infra; AI tagline marketing"),
    ("AI_INFRA", "M", "Y", "desktop panel managing AI agents"),
    ("AI_INFRA", "M", "Y", "Postgres vector-store/embeddings extension"),
    ("NOT_AI", "L", "Y", "music-theory PWA; torch dep is noise"),
    ("BUILDS_AI", "M", "Y", "autonomous pentesting agent system [dual]"),
    ("BUILDS_AI", "H", "", "agent orchestration framework (crewAI) [dual]"),
    ("BUILDS_AI", "M", "", "interactive NN training/backprop (ML)"),
    ("AI_INFRA", "M", "Y", "context/memory harness for coding agents"),
    ("NOT_AI", "H", "", "JS syntax linter; 'ai' tag spurious"),
    ("BUILDS_AI", "M", "", "LangChain agent-loop runtime/framework"),
    ("BUILDS_AI", "M", "", "agent-to-agent protocol (agent system)"),
    ("USES_AI", "L", "Y", "trivial meal-finder app using an LLM agent"),
    ("BUILDS_AI", "M", "", "self-hosted LLM serving cluster (+training)"),
    ("NOT_AI", "H", "", "cyber-awareness LMS; 'training'=human"),
    ("BUILDS_AI", "M", "", "LLM inference benchmarking/optimization"),
    ("NOT_AI", "M", "Y", "governance/process docs for 'HumanAIOS'"),
    ("NOT_AI", "M", "Y", "LLM-auto-edit experiment; output is a game"),
    ("AI_INFRA", "M", "Y", "RAG chunking/retrieval library [not training]"),
    ("BUILDS_AI", "H", "", "AirLLM inference-optimization (torch)"),
    ("BUILDS_AI", "H", "", "PyTorch handwriting model (course project)"),
    ("BUILDS_AI", "M", "", "A2A agent framework (Kotlin)"),
    ("BUILDS_AI", "H", "", "deep-learning modulation-recognition research"),
    ("BUILDS_AI", "L", "Y", "ONNX inference engine + chat UI (C#)"),
    ("NOT_AI", "H", "", "collection of LLM prompts"),
    ("NOT_AI", "H", "", "triathlon training app; 'training'=human"),
    ("BUILDS_AI", "H", "", "decentralized LLM fine-tuning+inference"),
    ("BUILDS_AI", "H", "", "ML training/deploy pipeline"),
    ("NOT_AI", "H", "", "flight sim; 'train'=human aircrew"),
    ("BUILDS_AI", "L", "Y", "framework for composable LLM workflows"),
    ("BUILDS_AI", "H", "", "diffusion LoRA dataset-prep [dual]"),
    ("BUILDS_AI", "H", "", "LLM-as-compressor research"),
    ("AI_INFRA", "L", "Y", "tiny LLM-token-generation npm util"),
    ("BUILDS_AI", "L", "Y", "DSL/framework for LLM-enabled apps"),
    ("NOT_AI", "H", "", "browser game (AI-crafted)"),
    ("BUILDS_AI", "M", "", "open-source AI agent framework (Cyrene)"),
    ("NOT_AI", "H", "", "strength-training PWA; 'training'=human"),
    ("AI_INFRA", "L", "Y", "agent memory-poisoning defense infra"),
    ("NOT_AI", "H", "", "clinical resuscitation reference app"),
    ("NOT_AI", "H", "", "portfolio site"),
    ("NOT_AI", "H", "", "business/ecommerce website"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "Wix dashboard template"),
    ("NOT_AI", "H", "", "business website"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "options-greeks finance dashboard; no AI"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "freelance website"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "marketing dashboard app"),
    ("NOT_AI", "H", "", "portfolio website"),
    ("NOT_AI", "H", "", "personal website"),
    ("USES_AI", "L", "Y", "construction PM app claiming 'AI integrated'"),
    ("NOT_AI", "H", "", "marketing site for fishing app"),
    ("NOT_AI", "H", "", "portfolio management frontend"),
    ("USES_AI", "H", "", "LLM explain-text web app"),
    ("NOT_AI", "H", "", "portfolio website"),
    ("NOT_AI", "H", "", "nightlife marketplace website"),
    ("NOT_AI", "H", "", "portfolio website"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "browser image-conversion site (WASM)"),
    ("NOT_AI", "H", "", "ecommerce ops dashboard"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "product landing page"),
    ("NOT_AI", "H", "", "university website"),
    ("NOT_AI", "H", "", "mentorship web app"),
    ("NOT_AI", "H", "", "personal dashboard app"),
    ("NOT_AI", "H", "", "Obsidian task dashboard plugin"),
    ("NOT_AI", "H", "", "CodeIgniter website template"),
    ("NOT_AI", "H", "", "clinical randomization web app"),
    ("NOT_AI", "H", "", "synth editor website"),
    ("NOT_AI", "H", "", "QR-code generator app"),
    ("AI_INFRA", "M", "Y", "Claude Code security plugin"),
    ("USES_AI", "M", "Y", "Azure OpenAI chat-proxy demo"),
    ("NOT_AI", "M", "Y", "Reddit/Google niche-mining analytics"),
    ("NOT_AI", "H", "", "yt-dlp desktop downloader"),
    ("NOT_AI", "M", "Y", "HPC batch orchestrator (slash commands)"),
    ("NOT_AI", "M", "", "EU energy market analytics; no AI"),
    ("NOT_AI", "H", "", "Pygame/MPD music player"),
    ("NOT_AI", "L", "Y", "empty readme"),
    ("AI_INFRA", "L", "Y", "personal multi-agent install harness"),
    ("BUILDS_AI", "M", "Y", "multi-agent orchestration framework [dual]"),
    ("NOT_AI", "L", "Y", "crypto bot, empty; no AI"),
    ("NOT_AI", "H", "", "BI/KPI dashboard project"),
    ("AI_INFRA", "M", "Y", "Jupyter tooling for AI agents"),
    ("NOT_AI", "L", "Y", "empty; openai dep only"),
    ("USES_AI", "M", "Y", "job app tailoring resumes via Claude"),
    ("USES_AI", "M", "Y", "consumer RAG app (ChromaDB+OpenAI) [dual refined]"),
    ("BUILDS_AI", "H", "", "LLM eval control-plane/harness (EvalGuard)"),
    ("AI_INFRA", "L", "Y", "AstrBot chatbot plugin"),
    ("AI_INFRA", "M", "Y", "MCP toolbox/agent middleware"),
    ("NOT_AI", "H", "", "design-patterns Python library"),
    ("NOT_AI", "H", "", "health/activity dashboard (Garmin)"),
    ("BUILDS_AI", "L", "Y", "Claude Code agentic CLI mirror (agent system)"),
    ("NOT_AI", "L", "Y", "empty 'tutor'"),
    ("USES_AI", "M", "", "conversational-wiki AI app"),
    ("NOT_AI", "H", "", "Solana wallet tracker; no AI"),
    ("USES_AI", "L", "Y", "credit-scorecard applied ML [applied ML=USES]"),
    ("NOT_AI", "H", "", "python script examples"),
    ("NOT_AI", "H", "", "personal dotfiles"),
    ("NOT_AI", "H", "", "production management system"),
    ("AI_INFRA", "M", "Y", "context-minify devtool for coding agents"),
    ("NOT_AI", "H", "", "substation/utility web app"),
    ("BUILDS_AI", "L", "Y", "clinical-AI governance research (sensitivity)"),
    ("USES_AI", "L", "Y", "genAI+graph-ML LEGO recommendation demo"),
    ("USES_AI", "M", "", "local doc-ingestion RAG Q&A app"),
    ("NOT_AI", "L", "Y", "empty 'JARVIS'"),
    ("NOT_AI", "H", "", "Mattermost collaboration platform"),
    ("USES_AI", "L", "Y", "front-end wrapping ComfyUI (image gen)"),
    ("NOT_AI", "H", "", "React+Vite starter template"),
    ("NOT_AI", "H", "", "E2E-encrypted chat app"),
    ("NOT_AI", "H", "", "Windows photo viewer"),
    ("NOT_AI", "H", "", "WoW addon"),
    ("NOT_AI", "L", "Y", "empty readme"),
    ("AI_INFRA", "L", "Y", "Italian-legal MCP server for Claude"),
    ("NOT_AI", "H", "", "website (SEO todos)"),
    ("NOT_AI", "H", "", "cross-country rankings DB site"),
    ("NOT_AI", "L", "Y", "travel-agency site; openai dep likely unused"),
    ("NOT_AI", "H", "", "comic-book reader app"),
    ("NOT_AI", "H", "", "cram-school website"),
    ("NOT_AI", "H", "", "React UI component library"),
    ("NOT_AI", "H", "", "repair-business site"),
    ("NOT_AI", "H", "", "OpenCart language pack"),
    ("USES_AI", "M", "", "AI music-creation (Suno-like) app"),
    ("NOT_AI", "H", "", "Quarto personal page"),
    ("NOT_AI", "H", "", "RPG character-sheet tool"),
    ("NOT_AI", "L", "Y", "empty work-tracker"),
    ("NOT_AI", "H", "", "Tiptap documentation"),
    ("NOT_AI", "H", "", "'done list' app"),
    ("NOT_AI", "H", "", "Shopify theme"),
    ("NOT_AI", "H", "", "iOS scanning app"),
    ("USES_AI", "L", "Y", "algo-trading sim w/ minor Gemini summaries"),
    ("NOT_AI", "H", "", "Flask+TS scaffold"),
    ("NOT_AI", "H", "", "Laravel web app"),
    ("NOT_AI", "L", "Y", "recipe app shipping MCP server (primary=recipe app)"),
    ("NOT_AI", "L", "Y", "empty readme"),
    ("NOT_AI", "H", "", "song-presentation software"),
    ("NOT_AI", "H", "", "private-tracker site"),
    ("NOT_AI", "H", "", "bill-splitting app"),
    ("NOT_AI", "H", "", "VS Code Azure Pipelines ext"),
    ("NOT_AI", "H", "", "personal morning-dashboard page"),
    ("NOT_AI", "L", "Y", "empty repo"),
]


def main():
    rows = list(csv.DictReader(GOLD.open()))
    assert len(rows) == len(LABELS), f"{len(rows)} rows vs {len(LABELS)} labels"

    cols = ["full_name", "stratum", "agents", "language", "stars", "topics",
            "builds_dep", "uses_dep", "dual_signal", "rule_label",
            "claude_label", "confidence", "flag_audit", "claude_reason",
            "human_label", "note", "description", "readme_head"]
    out = []
    for r, (label, conf, flag, reason) in zip(rows, LABELS):
        # idempotent: support both the original worksheet and a relabeled one
        r["rule_label"] = r.pop("proposed_label", None) or r.get("rule_label", "")
        r.pop("proposed_reason", None)
        r["claude_label"] = label
        r["confidence"] = conf
        r["flag_audit"] = flag
        r["claude_reason"] = reason
        out.append(r)

    with GOLD.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(out)

    from collections import Counter
    dist = Counter(l[0] for l in LABELS)
    flags = sum(1 for l in LABELS if l[2] == "Y")
    confs = Counter(l[1] for l in LABELS)
    agree = sum(1 for r in out if r["rule_label"] == r["claude_label"])
    print("label distribution:", dict(dist))
    print("confidence:", dict(confs), "| flagged for audit:", flags)
    print(f"rule-anchor vs claude agreement: {agree}/{len(out)} "
          f"({100*agree//len(out)}%)")


if __name__ == "__main__":
    main()
