"""Created-file arm: documents that are single WHOLE files.

A file created by a PR appears in its diff as a `new file mode` block
whose added lines are the complete file as authored — one author
intent, no interleaving with earlier code, and exactly the whole-file
unit code detectors (sem13c) are trained on. Per slot with at least
one eligible created code file (keep_file allowlist, word floor), the
LARGEST such file becomes the slot's newfile document, in two
variants: capped at the design word cap (comparable to the diff
documents and affordable for GPTZero) and the full uncapped file (the
sem13c domain-repair probe, free to score locally).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

from diffs import count_words, keep_file

WORD_CAP = 600
WORD_FLOOR = 100
ASSEMBLY = "nf1"


def created_files(raw: str) -> list[tuple[str, str]]:
    """(path, file text) for every created code file in a unified
    diff: a `new file mode` block's added lines are the whole file."""
    out: list[tuple[str, str]] = []
    path: str | None = None
    lines: list[str] = []
    new = False

    def flush() -> None:
        if new and path and keep_file(path) and lines:
            out.append((path, "\n".join(lines) + "\n"))

    for ln in raw.splitlines():
        if ln.startswith("diff --git "):
            flush()
            path, lines, new = None, [], False
        elif ln.startswith("new file mode"):
            new = True
        elif ln.startswith("+++ b/"):
            path = ln[6:].strip()
        elif ln.startswith("+") and not ln.startswith("+++"):
            lines.append(ln[1:])
    flush()
    return out


def _cap(text: str, cap: int) -> tuple[str, bool]:
    words = text.split()
    if len(words) <= cap:
        return text, False
    return " ".join(words[:cap]), True


def build_rows(doc_rows: list[dict], diff_cache: Path,
               doc_cache: Path) -> list[dict]:
    """One newfile row per scored slot whose PR created at least one
    eligible code file (>= WORD_FLOOR words): the largest such file,
    with capped and full variants written to the document cache."""
    rows = []
    for d in doc_rows:
        p = diff_cache / f"{d['repo'].replace('/', '~')}@{d['num']}.diff"
        if not p.is_file():
            continue
        eligible = [(path, t) for path, t in
                    created_files(p.read_text(errors="replace"))
                    if count_words(t) >= WORD_FLOOR]
        if not eligible:
            continue
        path, text = max(eligible, key=lambda x: count_words(x[1]))
        full = f"// file: {path}\n{text}"
        capped, truncated = _cap(full, WORD_CAP)
        sha = hashlib.sha256(capped.encode()).hexdigest()
        sha_full = hashlib.sha256(full.encode()).hexdigest()
        doc_cache.mkdir(parents=True, exist_ok=True)
        (doc_cache / f"{sha}.txt").write_text(capped)
        (doc_cache / f"{sha_full}.txt").write_text(full)
        rows.append({**{k: d[k] for k in ("slot", "arm", "author",
                                          "period", "ai", "repo",
                                          "num")},
                     "path": path, "assembly": ASSEMBLY,
                     "doc_sha": sha, "words": count_words(capped),
                     "truncated": truncated,
                     "doc_sha_full": sha_full,
                     "words_full": count_words(full)})
    return rows


def write_rows(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in rows))
    tmp.replace(path)
