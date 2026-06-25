"""Phase 0.3: measure how well cheap signals predict the gold labels.
Prints the tables summarized in signal_analysis.md. Read-only over data/gold.
"""
from __future__ import annotations
import csv
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
GOLD = ROOT / "data" / "gold" / "gold_repos.csv"
AI_TOPICS = {
    "machine-learning", "deep-learning", "llm", "large-language-models", "transformers",
    "pytorch", "tensorflow", "jax", "rag", "llmops", "mlops", "agents", "ai-agents",
    "reinforcement-learning", "neural-network", "neural-networks", "diffusion-models",
    "artificial-intelligence", "ai", "ml", "nlp", "computer-vision", "generative-ai",
    "gpt", "langchain", "embeddings", "vector-database", "fine-tuning", "genai",
    "deep-neural-networks", "image-generation", "stable-diffusion", "agentic-ai",
}


def main():
    rows = list(csv.DictReader(GOLD.open()))
    for r in rows:
        t = set(r["topics"].split("|")) if r["topics"] else set()
        r["ai_topic"] = bool(t & AI_TOPICS)
        r["has_topic"] = bool(t)
        r["bd"] = r["builds_dep"] == "True"
        r["ud"] = r["uses_dep"] == "True"
        r["dual"] = r["dual_signal"] == "True"
        r["py"] = r["language"] == "Python"
        r["L"] = r["claude_label"]

    print("gold base rates (OVER-SAMPLED):", dict(Counter(r["L"] for r in rows)))

    def pr(name, pred, target):
        tp = sum(1 for r in rows if pred(r) and r["L"] in target)
        fp = sum(1 for r in rows if pred(r) and r["L"] not in target)
        fn = sum(1 for r in rows if not pred(r) and r["L"] in target)
        p = tp / (tp + fp) if tp + fp else 0
        rc = tp / (tp + fn) if tp + fn else 0
        print(f"  {name:30} P={p:.2f} R={rc:.2f}  (tp={tp} fp={fp} fn={fn})")

    print("\n[A] predicting BUILDS_AI:")
    for n, f in [("ai_topic", lambda r: r["ai_topic"]), ("builds_dep", lambda r: r["bd"]),
                 ("dual_signal", lambda r: r["dual"]), ("any_topic", lambda r: r["has_topic"]),
                 ("python", lambda r: r["py"])]:
        pr(n, f, {"BUILDS_AI"})
    print("\n[B] predicting BUILDS_AI or AI_INFRA:")
    for n, f in [("ai_topic", lambda r: r["ai_topic"]), ("builds_dep", lambda r: r["bd"]),
                 ("any_AI_dep", lambda r: r["bd"] or r["ud"]), ("any_topic", lambda r: r["has_topic"])]:
        pr(n, f, {"BUILDS_AI", "AI_INFRA"})
    print("\n[C] predicting NOT_AI:")
    for n, f in [("no_topic_and_no_dep", lambda r: not r["has_topic"] and not r["bd"] and not r["ud"]),
                 ("no_topic", lambda r: not r["has_topic"])]:
        pr(n, f, {"NOT_AI"})
    print("\n[D] uses_dep-only predicting USES_AI:")
    pr("uses_dep & not builds_dep", lambda r: r["ud"] and not r["bd"], {"USES_AI"})

    print("\n[E] rule-anchor confusion (rows=rule_label, cols=label):")
    labs = ["BUILDS_AI", "USES_AI", "AI_INFRA", "NOT_AI"]
    print("    rule\\label  " + " ".join(f"{x[:7]:>8}" for x in labs))
    for rl in labs:
        line = [sum(1 for r in rows if r["rule_label"] == rl and r["L"] == cl) for cl in labs]
        print(f"    {rl:12}" + " ".join(f"{x:>8}" for x in line))


if __name__ == "__main__":
    main()
