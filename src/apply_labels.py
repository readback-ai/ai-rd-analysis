"""Phase 0.2: merge Claude's proposed labels into the gold worksheet.

LABELS is in the SAME ORDER as data/gold/gold_repos.csv (and evidence_dump.txt).
Each entry: (label, confidence H/M/L, flag_audit Y/'', reason). These are PROPOSED;
Ron audits -> fills human_label (blank = agrees with claude_label).
"""
from __future__ import annotations
import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold" / "gold_repos.csv"

LABELS = [
    ("USES_AI", "L", "Y", "sprawling solo 'cognitive engine'/sim consuming LLMs; vapor"),
    ("NOT_AI", "M", "Y", "npm scaffolding/linters to guide coding agents; devtool"),
    ("USES_AI", "M", "Y", "desktop AI assistant app + protocol"),
    ("USES_AI", "H", "", "self-hosted AI chat plugin (Ollama) on Steam Deck"),
    ("BUILDS_AI", "H", "", "Python causal-inference/econometrics ML library (torch)"),
    ("NOT_AI", "L", "Y", "OS dual-boot/ops convergence repo; openai dep incidental"),
    ("BUILDS_AI", "M", "Y", "agent-memory infra library (knowledge graph) [dual]"),
    ("USES_AI", "H", "", "job-search dashboard drafting resumes via LLM"),
    ("USES_AI", "M", "Y", "browser-native AI agent product"),
    ("USES_AI", "L", "Y", "web3 financial platform for agents; little AI building"),
    ("USES_AI", "M", "Y", "AI coding agent product (opencode fork)"),
    ("USES_AI", "H", "", "agentic webapp for B2B lead enrichment"),
    ("USES_AI", "L", "Y", "energy management platform applying ML forecasting"),
    ("BUILDS_AI", "M", "Y", "chatbot/agent framework library (MCP) [dual]"),
    ("BUILDS_AI", "L", "Y", "autonomous multi-agent software-dev system"),
    ("BUILDS_AI", "L", "Y", "edge agent harness w/ local LLM on Jetson/Pi"),
    ("BUILDS_AI", "H", "", "OCR engine (LSTM) -- ML model"),
    ("BUILDS_AI", "L", "Y", "multi-agent deliberation framework"),
    ("BUILDS_AI", "H", "", "popular AI agent framework (PraisonAI)"),
    ("USES_AI", "M", "Y", "political intelligence platform w/ AI-generated news"),
    ("USES_AI", "H", "", "LLM app scanning ToS for risky clauses"),
    ("NOT_AI", "L", "Y", "deterministic MMORPG/game engine; AI tags marketing"),
    ("BUILDS_AI", "H", "", "LLM serving platform (KVCache, vllm/sglang)"),
    ("BUILDS_AI", "H", "", "popular TS AI agent framework (mastra)"),
    ("NOT_AI", "H", "", "workout/nutrition tracker; 'ai' tag spurious"),
    ("USES_AI", "H", "", "AI writing-assistant Chrome extension"),
    ("NOT_AI", "M", "Y", "P2P tunneling/networking tool; AI tangential"),
    ("BUILDS_AI", "L", "Y", "Rust agent sandbox/self-evolution engine [infra]"),
    ("USES_AI", "H", "", "autonomous AI personal assistant app"),
    ("NOT_AI", "M", "Y", "task tracker whose users are agents; not AI-building"),
    ("USES_AI", "M", "Y", "political intelligence platform w/ AI news"),
    ("NOT_AI", "M", "Y", "code-search/context devtool for coding agents"),
    ("USES_AI", "H", "", "trading journal app with AI features"),
    ("USES_AI", "H", "", "syllabus-PDF->calendar via LLM extraction"),
    ("NOT_AI", "L", "Y", "web-scraping API (LLM-ready data); not model/agent building"),
    ("BUILDS_AI", "L", "Y", "portfolio of built AI/RAG/multi-agent systems"),
    ("NOT_AI", "H", "", "Docker wrapper image around OpenClaw"),
    ("USES_AI", "M", "Y", "Android AI chat/terminal IDE app"),
    ("NOT_AI", "M", "Y", "Claude Code plugin (workflow skills)"),
    ("NOT_AI", "H", "", "notifications infrastructure; AI tagline marketing"),
    ("USES_AI", "L", "Y", "desktop admin panel managing agents"),
    ("BUILDS_AI", "M", "", "Postgres vector-store extension (embeddings/quantization)"),
    ("NOT_AI", "L", "Y", "music-theory PWA; torch dep but app purpose [dep noise]"),
    ("USES_AI", "M", "Y", "autonomous pentesting agent app [dual]"),
    ("BUILDS_AI", "H", "", "popular agent orchestration framework (crewAI) [dual]"),
    ("BUILDS_AI", "M", "", "interactive NN training/backprop playground (ML)"),
    ("NOT_AI", "M", "Y", "context/memory harness utility for coding agents"),
    ("NOT_AI", "H", "", "JS syntax auto-upgrader (linter); 'ai' tag spurious"),
    ("BUILDS_AI", "M", "", "LangChain agent-loop runtime/framework (MCP)"),
    ("BUILDS_AI", "M", "Y", "agent-to-agent communication protocol/infra"),
    ("USES_AI", "H", "", "LLM agent app to find meals"),
    ("BUILDS_AI", "M", "", "self-hosted LLM serving cluster (+training env)"),
    ("NOT_AI", "H", "", "cyber-awareness LMS; 'training'=human"),
    ("BUILDS_AI", "M", "", "LLM inference benchmarking/optimization tooling"),
    ("NOT_AI", "M", "Y", "governance/process docs repo for 'HumanAIOS'"),
    ("NOT_AI", "M", "Y", "LLM-auto-edit experiment; output is a snake game"),
    ("BUILDS_AI", "M", "", "RAG chunking/retrieval library for PDFs"),
    ("BUILDS_AI", "H", "", "AirLLM inference-optimization library (torch)"),
    ("BUILDS_AI", "H", "", "PyTorch handwriting-recognition model (course project)"),
    ("BUILDS_AI", "M", "", "A2A agent framework (Kotlin)"),
    ("BUILDS_AI", "H", "", "deep-learning modulation-recognition research"),
    ("BUILDS_AI", "L", "Y", "ONNX inference engine + chat UI (C#)"),
    ("NOT_AI", "H", "", "collection of LLM prompts"),
    ("NOT_AI", "H", "", "triathlon training app; 'training'=human"),
    ("BUILDS_AI", "H", "", "decentralized LLM fine-tuning+inference (torch)"),
    ("BUILDS_AI", "H", "", "ML model training/deploy pipeline"),
    ("NOT_AI", "H", "", "airspace flight simulator; 'train'=human aircrew"),
    ("BUILDS_AI", "L", "Y", "framework for composable LLM workflows [vs USES]"),
    ("BUILDS_AI", "H", "", "diffusion LoRA dataset-prep toolkit [dual]"),
    ("BUILDS_AI", "H", "", "LLM-as-compressor information-theory research"),
    ("NOT_AI", "M", "Y", "tiny token-generation npm util for LLM prompts"),
    ("BUILDS_AI", "L", "Y", "DSL/framework for LLM-enabled apps [vs USES]"),
    ("NOT_AI", "H", "", "browser game (AI-crafted); not AI software"),
    ("BUILDS_AI", "M", "", "open-source AI agent framework (Cyrene)"),
    ("NOT_AI", "H", "", "strength-training PWA; 'training'=human"),
    ("BUILDS_AI", "L", "Y", "agent-memory-poisoning defense infra [vs USES]"),
    ("NOT_AI", "H", "", "clinical resuscitation reference web app"),
    ("NOT_AI", "H", "", "portfolio site"),
    ("NOT_AI", "H", "", "business/ecommerce website"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "Wix dashboard template"),
    ("NOT_AI", "H", "", "business website"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "options-greeks finance dashboard (BSM); no AI"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "freelance website"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "marketing dashboard app"),
    ("NOT_AI", "H", "", "portfolio website"),
    ("NOT_AI", "H", "", "personal website"),
    ("USES_AI", "L", "Y", "construction PM web app claiming 'AI integrated'"),
    ("NOT_AI", "H", "", "marketing site for a fishing app"),
    ("NOT_AI", "H", "", "portfolio management frontend"),
    ("USES_AI", "H", "", "LLM explain-highlighted-text web app"),
    ("NOT_AI", "H", "", "portfolio website"),
    ("NOT_AI", "H", "", "nightlife marketplace website"),
    ("NOT_AI", "H", "", "portfolio website"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "browser image-conversion site (WASM)"),
    ("NOT_AI", "H", "", "ecommerce ops dashboard"),
    ("NOT_AI", "H", "", "personal website"),
    ("NOT_AI", "H", "", "product landing page"),
    ("NOT_AI", "H", "", "university website"),
    ("NOT_AI", "H", "", "mentorship-program web app"),
    ("NOT_AI", "H", "", "personal dashboard app"),
    ("NOT_AI", "H", "", "Obsidian task dashboard plugin"),
    ("NOT_AI", "H", "", "CodeIgniter website template"),
    ("NOT_AI", "H", "", "clinical randomization web app"),
    ("NOT_AI", "H", "", "synth editor website"),
    ("NOT_AI", "H", "", "QR-code generator web app"),
    ("NOT_AI", "M", "Y", "Claude Code security plugin (Web3 hooks)"),
    ("USES_AI", "M", "Y", "Azure OpenAI chat proxy demo microservice"),
    ("NOT_AI", "M", "Y", "Reddit/Google niche-mining analytics tool"),
    ("NOT_AI", "H", "", "yt-dlp desktop downloader"),
    ("NOT_AI", "M", "Y", "HPC batch-experiment orchestrator (SLURM/PBS)"),
    ("NOT_AI", "M", "", "EU energy market data analytics; no AI"),
    ("NOT_AI", "H", "", "Pygame/MPD music player"),
    ("NOT_AI", "L", "Y", "empty readme; unknown"),
    ("NOT_AI", "M", "Y", "personal multi-agent install harness/config"),
    ("BUILDS_AI", "M", "Y", "multi-agent orchestration framework [dual]"),
    ("NOT_AI", "L", "Y", "crypto bot, empty readme; no AI"),
    ("NOT_AI", "H", "", "BI/KPI dashboard portfolio project"),
    ("NOT_AI", "M", "Y", "Jupyter tooling enabling agents; devtool"),
    ("NOT_AI", "L", "Y", "empty readme; openai dep only"),
    ("USES_AI", "H", "", "job aggregator tailoring resumes via Claude"),
    ("USES_AI", "M", "Y", "consumer RAG app (ChromaDB+OpenAI) -- dual rule misfires"),
    ("BUILDS_AI", "H", "", "LLM eval control-plane/harness (EvalGuard)"),
    ("USES_AI", "L", "Y", "AstrBot proactive-reply chatbot plugin"),
    ("NOT_AI", "M", "Y", "MCP toolbox/agent middleware; devtool"),
    ("NOT_AI", "H", "", "design-patterns Python library"),
    ("NOT_AI", "H", "", "health/activity dashboard (Garmin)"),
    ("USES_AI", "L", "Y", "mirror of Claude Code agentic CLI (agent product)"),
    ("NOT_AI", "L", "Y", "empty 'tutor'"),
    ("USES_AI", "M", "", "self-hosted conversational-wiki AI app"),
    ("NOT_AI", "H", "", "Solana wallet tracker; no AI"),
    ("BUILDS_AI", "L", "Y", "credit scorecard modeling (statistical ML)"),
    ("NOT_AI", "H", "", "generic python script examples"),
    ("NOT_AI", "H", "", "personal dotfiles"),
    ("NOT_AI", "H", "", "production management system"),
    ("NOT_AI", "M", "Y", "context-minify devtool for coding agents"),
    ("NOT_AI", "H", "", "substation/utility domain web app"),
    ("BUILDS_AI", "L", "Y", "clinical-AI governance research (sensitivity analysis)"),
    ("USES_AI", "L", "Y", "genAI+graph-ML LEGO recommendation demo"),
    ("USES_AI", "M", "", "local doc-ingestion RAG Q&A app"),
    ("NOT_AI", "L", "Y", "empty 'JARVIS'"),
    ("NOT_AI", "H", "", "Mattermost collaboration platform"),
    ("USES_AI", "L", "Y", "front-end UI wrapping ComfyUI (image gen)"),
    ("NOT_AI", "H", "", "React+Vite starter template"),
    ("NOT_AI", "H", "", "simple E2E-encrypted chat app"),
    ("NOT_AI", "H", "", "Windows photo viewer"),
    ("NOT_AI", "H", "", "World of Warcraft addon"),
    ("NOT_AI", "L", "Y", "empty readme"),
    ("USES_AI", "L", "Y", "Italian legal assistant via Claude/MCP"),
    ("NOT_AI", "H", "", "website (SEO todos)"),
    ("NOT_AI", "H", "", "cross-country rankings database site"),
    ("NOT_AI", "L", "Y", "travel-agency Next.js site; openai dep likely unused"),
    ("NOT_AI", "H", "", "comic-book reader app"),
    ("NOT_AI", "H", "", "cram-school website"),
    ("NOT_AI", "H", "", "React UI component library"),
    ("NOT_AI", "H", "", "repair-business site"),
    ("NOT_AI", "H", "", "OpenCart language pack"),
    ("USES_AI", "M", "", "AI music-creation (Suno-like) web app"),
    ("NOT_AI", "H", "", "Quarto personal page"),
    ("NOT_AI", "H", "", "RPG character-sheet web tool"),
    ("NOT_AI", "L", "Y", "empty work-tracker"),
    ("NOT_AI", "H", "", "Tiptap documentation site"),
    ("NOT_AI", "H", "", "'done list' productivity app"),
    ("NOT_AI", "H", "", "Shopify theme"),
    ("NOT_AI", "H", "", "iOS scanning app"),
    ("USES_AI", "L", "Y", "algo-trading sim w/ minor Gemini AI summaries"),
    ("NOT_AI", "H", "", "Flask+TS project scaffold"),
    ("NOT_AI", "H", "", "Laravel web app"),
    ("USES_AI", "L", "Y", "recipe app shipping MCP server + chat assistant"),
    ("NOT_AI", "L", "Y", "empty readme"),
    ("NOT_AI", "H", "", "song-presentation software"),
    ("NOT_AI", "H", "", "private-tracker (NexusPHP) site"),
    ("NOT_AI", "H", "", "bill-splitting web app"),
    ("NOT_AI", "H", "", "VS Code extension for Azure Pipelines"),
    ("NOT_AI", "H", "", "personal 'morning dashboard' page"),
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
        r["rule_label"] = r.pop("proposed_label")
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
