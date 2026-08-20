"""Endpoint-comparison arm (design ep-v1): files vs text.

/v2/predict/files silently normalises uploads before scoring — across
this study's corpus only 0.4% of documents reached the model as sent,
mean byte loss 13.6%, and just 15.9% of leading whitespace survived, so
code indentation is largely destroyed. /v2/predict/text preserves the
bytes and is what the dashboard's Advanced Scan runs. On four
spot-checked agent documents the endpoints agreed on three and flipped
the fourth from human (0.023) to ai (0.596).

This arm measures the disagreement rate properly: a stratified,
seeded sample of already-scored documents is re-scored through the
TEXT endpoint under the SAME pinned model version as the corpus, so
the only variable is the endpoint. Selection is prefix-stable, so
raising N_PER_STRATUM deepens the sample without redrawing it.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

from sampling import SEED

DESIGN = "ep-v1"
N_PER_STRATUM = 12


def stratum(r: dict) -> str | None:
    """The reporting arm a scored row belongs to."""
    if r["arm"] in ("B1", "B2", "B3"):
        return "baseline"
    if r["arm"] == "PC":
        return "known-AI"
    if r["arm"] == "P":
        return f"{r['period']}-{'AI' if r['ai'] else 'nonAI'}"
    return None


def select(score_rows: list[dict],
           n_per_stratum: int | None = None) -> list[dict]:
    """Deterministic stratified sample: per stratum a seeded shuffle of
    its documents, then a prefix. Rows keep their identity plus the
    stratum label and the files-endpoint doc_sha they pair against."""
    n = n_per_stratum or N_PER_STRATUM
    pool: dict[str, list[dict]] = {}
    for r in score_rows:
        s = stratum(r)
        if s:
            pool.setdefault(s, []).append(r)
    out = []
    for s in sorted(pool):
        ordered = sorted(pool[s], key=lambda r: r["slot"])
        random.Random(f"{SEED}:gptzero:endpoint:{s}").shuffle(ordered)
        for r in ordered[:n]:
            out.append({**{k: r[k] for k in
                           ("slot", "arm", "author", "period", "ai",
                            "repo", "num", "doc_sha")},
                        "stratum": s, "words": r.get("words"),
                        "design": DESIGN})
    return out


def write_rows(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    tmp.replace(path)
