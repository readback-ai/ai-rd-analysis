"""Comment/code ablation (design abl-v1): what carries the signal?

GPTZero's support team's reading (2026-08-19) is that the detector's
apparent skill on code comes from prose-with-code-snippets in its
training data, most likely keying on comments and structure. This arm
tests that directly and, at the same time, the era-drift question:
each selected document is re-scored in two variants —

  code    — every comment line removed, code lines only
  comment — every comment line only, code removed

against its already-scored ORIGINAL. Both eras are ablated (pre-2025
baselines and Q2-2026 paired documents), so the decomposition answers
two questions at once: does removing prose collapse the score, and
does the era gap survive inside code-only text?

Variants keep the slot's identity and record their parent doc_sha, so
the analysis pairs strictly within document. Selection is deterministic
(seeded shuffle over eligible documents, then a prefix), and both
variants must clear WORD_FLOOR — a variant too short to score would
measure length, not style.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from diffs import count_words
from sampling import SEED

ASSEMBLY = "abl1"
WORD_FLOOR = 80          # per variant; below this a score reads length
N_PER_GROUP = 20
COMMENT_STARTS = ("#", "//", "/*", "*", "*/")


def split_document(text: str) -> tuple[str, str]:
    """(code-only, comments-only). The `// file:` headers belong to the
    document format rather than to either stream, so they are dropped
    from both — leaving them in would score our own construction."""
    code: list[str] = []
    comment: list[str] = []
    for line in text.splitlines():
        if line.startswith("// file: "):
            continue
        stripped = line.strip()
        if stripped.startswith(COMMENT_STARTS):
            comment.append(line)
        else:
            code.append(line)
    return "\n".join(code) + "\n", "\n".join(comment) + "\n"


def eligible(score_rows: list[dict], doc_cache: Path) -> list[dict]:
    """Scored documents whose BOTH variants clear the floor, with the
    variant texts attached."""
    out = []
    for r in score_rows:
        p = doc_cache / f"{r['doc_sha']}.txt"
        if not p.is_file():
            continue
        code, comment = split_document(p.read_text())
        if count_words(code) < WORD_FLOOR \
                or count_words(comment) < WORD_FLOOR:
            continue
        out.append({**r, "_variants": {"code": code,
                                       "comment": comment}})
    return out


def _group(r: dict) -> str | None:
    if r["arm"] in ("B1", "B2", "B3"):
        return "baseline"
    if r["arm"] == "P" and r["period"] == "Q2-2026":
        return "Q2-2026"
    return None


def build_rows(score_rows: list[dict], doc_cache: Path) -> list[dict]:
    """Deterministic variant rows: per group, a seeded shuffle of the
    eligible documents then an N_PER_GROUP prefix (so raising N keeps
    earlier selections), two rows per selected document."""
    pool: dict[str, list[dict]] = {}
    for r in eligible(score_rows, doc_cache):
        g = _group(r)
        if g:
            pool.setdefault(g, []).append(r)
    rows = []
    for g in sorted(pool):
        ordered = sorted(pool[g], key=lambda r: r["slot"])
        random.Random(f"{SEED}:gptzero:ablation:{g}").shuffle(ordered)
        for r in ordered[:N_PER_GROUP]:
            for variant, text in sorted(r["_variants"].items()):
                sha = hashlib.sha256(text.encode()).hexdigest()
                doc_cache.mkdir(parents=True, exist_ok=True)
                (doc_cache / f"{sha}.txt").write_text(text)
                rows.append({
                    **{k: r[k] for k in ("slot", "arm", "author",
                                         "period", "ai", "repo",
                                         "num")},
                    "group": g, "variant": variant,
                    "parent_doc_sha": r["doc_sha"], "doc_sha": sha,
                    "words": count_words(text),
                    "assembly": ASSEMBLY})
    return rows


def write_rows(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    tmp.replace(path)
