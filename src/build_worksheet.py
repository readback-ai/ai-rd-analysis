"""Phase 0.2: fetch README head + dependency manifests for the gold candidates,
detect BUILDS vs USES dependency signals (and dual-signal repos), and write the
hand-labeling worksheet data/gold/gold_repos.csv.

The `proposed_label` column is a TRANSPARENT RULE ANCHOR only -- it exists to speed
human review, not to be ground truth. `human_label` is left blank for adjudication.
"""
from __future__ import annotations
import csv
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh import gql  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "sample" / "gold_candidates.csv"
OUT = ROOT / "data" / "gold" / "gold_repos.csv"
BATCH = 12
README_CHARS = 1500

MANIFESTS = {
    "req": "requirements.txt", "pyproject": "pyproject.toml", "setup": "setup.py",
    "pkg": "package.json", "envyml": "environment.yml",
}
READMES = {"rm_md": "README.md", "rm_low": "readme.md", "rm_rst": "README.rst"}

BUILDS_DEPS = re.compile(
    r"\b(torch|pytorch|transformers|tensorflow|keras|jax|flax|vllm|deepspeed|"
    r"accelerate|peft|trl|sentence[-_]transformers|diffusers|datasets|tokenizers|"
    r"bitsandbytes|onnxruntime|xgboost|lightgbm|scikit[-_]learn|sklearn)\b", re.I)
USES_DEPS = re.compile(
    r"(openai|anthropic|cohere|langchain|llama[-_]?index|litellm|groq|mistralai|"
    r"google-generativeai|@anthropic-ai|@openai|vercel/ai)", re.I)


def blob(node, key):
    o = node.get(key)
    return (o or {}).get("text") or ""


def esc(s):
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_query(batch):
    blocks = []
    fields = "\n".join(
        f'{k}: object(expression:"HEAD:{v}"){{... on Blob {{ text }}}}'
        for k, v in {**READMES, **MANIFESTS}.items()
    )
    for i, (owner, name) in enumerate(batch):
        blocks.append(f'r{i}: repository(owner:"{esc(owner)}", name:"{esc(name)}"){{{fields}}}')
    return "query {\n" + "\n".join(blocks) + "\n}"


def main():
    rows = list(csv.DictReader(IN.open()))
    pairs = [tuple(r["full_name"].split("/", 1)) for r in rows]

    enriched = []
    for start in range(0, len(pairs), BATCH):
        batch = pairs[start:start + BATCH]
        data = gql(build_query(batch))
        for i, base in enumerate(rows[start:start + BATCH]):
            node = data.get(f"r{i}") or {}
            readme = (blob(node, "rm_md") or blob(node, "rm_low") or blob(node, "rm_rst"))
            manifest_text = " ".join(blob(node, k) for k in MANIFESTS)
            has_build = bool(BUILDS_DEPS.search(manifest_text))
            has_use = bool(USES_DEPS.search(manifest_text))

            ai_topic = base["ai_topic"] == "True"
            builds_desc = base["builds_desc"] == "True"
            uses_desc = base["uses_desc"] == "True"

            # transparent rule anchor (NOT ground truth)
            if has_build or ai_topic:
                proposed, why = "BUILDS_AI", "build dep/AI topic"
            elif has_use and not has_build:
                proposed, why = "USES_AI", "client SDK only"
            elif builds_desc:
                proposed, why = "BUILDS_AI", "build-ish description"
            elif uses_desc:
                proposed, why = "USES_AI", "app-ish description"
            else:
                proposed, why = "NOT_AI", "no AI signal"

            enriched.append({
                "full_name": base["full_name"],
                "stratum": base["stratum"],
                "agents": base["agents"],
                "language": base["language"],
                "stars": base["stars"],
                "topics": base["topics"],
                "builds_dep": has_build,
                "uses_dep": has_use,
                "dual_signal": has_build and has_use,
                "proposed_label": proposed,
                "proposed_reason": why,
                "human_label": "",      # <- Ron fills/audits
                "note": "",
                "description": base["description"][:300],
                "readme_head": re.sub(r"\s+", " ", readme)[:README_CHARS],
            })
        print(f"  {start + len(batch)}/{len(pairs)} enriched", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(enriched[0].keys()))
        w.writeheader()
        w.writerows(enriched)

    dual = sum(r["dual_signal"] for r in enriched)
    prop = {}
    for r in enriched:
        prop[r["proposed_label"]] = prop.get(r["proposed_label"], 0) + 1
    print(f"\nWrote {len(enriched)} -> {OUT}", file=sys.stderr)
    print(f"dual-signal repos: {dual}", file=sys.stderr)
    print(f"proposed anchor distribution: {prop}", file=sys.stderr)


if __name__ == "__main__":
    main()
