"""Phase 0.2: compute cheap signals over the seed sample and draw a stratified
gold-set sample (~180) that deliberately over-samples edge cases.

Run `python src/stratify.py` to print stratum counts; add `--select` to write
data/sample/gold_candidates.csv (the repos to build the labeling worksheet from).
"""
from __future__ import annotations
import csv
import random
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SAMPLE = ROOT / "data" / "sample" / "repo_sample.csv"
META = ROOT / "data" / "sample" / "repo_meta.csv"
OUT = ROOT / "data" / "sample" / "gold_candidates.csv"
SEED = 20260625
TARGET = 180

AI_TOPICS = {
    "machine-learning", "deep-learning", "llm", "large-language-models", "transformers",
    "pytorch", "tensorflow", "jax", "rag", "llmops", "mlops", "agents", "ai-agents",
    "reinforcement-learning", "neural-network", "neural-networks", "diffusion-models",
    "artificial-intelligence", "ai", "ml", "nlp", "computer-vision", "generative-ai",
    "gpt", "langchain", "embeddings", "vector-database", "fine-tuning", "genai",
    "deep-neural-networks", "image-generation", "stable-diffusion", "agentic-ai",
}
# BUILDS-ish description terms (training/serving/research vocabulary)
BUILDS_RE = re.compile(
    r"\b(train(ing|ed)?|fine[- ]?tun|inference|transformer|neural net|deep learning|"
    r"machine learning|reinforcement learning|diffusion|quantiz|embedding|llm|"
    r"language model|pytorch|tensorflow|\bjax\b|vllm|serving|dataset|benchmark|"
    r"eval(uation)? harness|agent framework|model (training|serving|weights))\b",
    re.I,
)
# USES-ish terms (consumer apps wrapping a model)
USES_RE = re.compile(
    r"\b(chatbot|chat app|wrapper|web ?app|website|portfolio|landing page|saas|"
    r"dashboard|discord bot|telegram bot|slack bot|browser extension|mobile app|"
    r"e-?commerce|boilerplate|starter (kit|template)|clone)\b",
    re.I,
)


def load():
    meta = {r["full_name"]: r for r in csv.DictReader(META.open())}
    out = []
    for s in csv.DictReader(SAMPLE.open()):
        m = meta.get(s["full_name"])
        if not m:
            continue
        topics = set(m["topics"].split("|")) if m["topics"] else set()
        desc = m["description"]
        row = {**m, "agents": s["agents"], "n_hits": s["n_hits"],
               "ai_topic": bool(topics & AI_TOPICS),
               "builds_desc": bool(BUILDS_RE.search(desc)),
               "uses_desc": bool(USES_RE.search(desc)),
               "is_notebook": m["language"] == "Jupyter Notebook",
               "is_python": m["language"] == "Python",
               "no_desc": desc == ""}
        out.append(row)
    return out


def stratum_of(r) -> str:
    if r["ai_topic"]:
        return "1_ai_topic"                      # strong BUILDS candidate
    if r["builds_desc"]:
        return "2_builds_desc_no_topic"          # BUILDS without a topic (tests topic recall)
    if r["uses_desc"]:
        return "3_uses_desc"                     # likely USES_AI app
    if r["is_notebook"] or r["is_python"]:
        return "4_py_or_nb_no_signal"            # ML-ish lang, no text signal (edge)
    return "5_generic_no_signal"                 # likely NOT_AI


ALLOC = {  # over-samples positives for BUILDS/USES boundary coverage; NOT base-rate
    "1_ai_topic": 50,             # ~all 53 strong-positive candidates
    "2_builds_desc_no_topic": 26, # all available (tests topic-rule recall)
    "3_uses_desc": 34,
    "4_py_or_nb_no_signal": 35,
    "5_generic_no_signal": 35,
}


def main(select: bool) -> None:
    rows = load()
    buckets: dict[str, list] = {}
    for r in rows:
        buckets.setdefault(stratum_of(r), []).append(r)

    print(f"Total joined: {len(rows)}\n")
    print(f"{'stratum':28} {'available':>9} {'target':>7}")
    for k in sorted(ALLOC):
        print(f"{k:28} {len(buckets.get(k, [])):>9} {ALLOC[k]:>7}")
    print("\nsignal totals:")
    for sig in ("ai_topic", "builds_desc", "uses_desc", "is_notebook", "is_python", "no_desc"):
        print(f"  {sig:14} {sum(r[sig] for r in rows)}")

    if not select:
        print("\n(run with --select to write gold_candidates.csv)")
        return

    rng = random.Random(SEED)
    picked = []
    for k, n in ALLOC.items():
        pool = buckets.get(k, [])
        rng.shuffle(pool)
        chosen = pool[:n]
        for r in chosen:
            r["stratum"] = k
        picked.extend(chosen)

    cols = ["full_name", "stratum", "agents", "n_hits", "language", "stars",
            "topics", "ai_topic", "builds_desc", "uses_desc", "description"]
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols, extrasaction="ignore")
        w.writeheader()
        w.writerows(picked)
    print(f"\nSelected {len(picked)} repos -> {OUT}")


if __name__ == "__main__":
    main("--select" in sys.argv)
