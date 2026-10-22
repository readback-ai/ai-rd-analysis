"""Diff fetching and document assembly for the GPTZero calibration.

A document is the ADDED LINES of a PR's code files only — deletions and
context are other authors' earlier code, and diff markup is
out-of-distribution for a text detector. Per kept file: a
`// file: <path>` header, then that file's added lines. Files are packed
whole, in diff order, up to the word cap; only the FIRST eligible file
may be truncated (at a hunk boundary, never mid-hunk). One word counter
(count_words) feeds the packer, the ledger, and the budget guard.
"""
from __future__ import annotations

import subprocess
import time
from pathlib import Path

# Document-definition version: bump whenever the assembly rules change
# (allowlist, vendored filter, packing, headers) — fetched documents are
# retained across runs only when it matches.
ASSEMBLY = "v1"

CODE_EXTS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".mjs", ".go", ".rs", ".java",
    ".kt", ".kts", ".c", ".h", ".cc", ".cpp", ".hpp", ".cxx", ".cs",
    ".rb", ".php", ".swift", ".scala", ".sh", ".bash", ".sql", ".m",
    ".mm", ".lua", ".pl", ".r", ".jl", ".zig", ".dart", ".ex", ".exs",
}
VENDOR_DIRS = {"node_modules", "vendor", "dist", "build", "third_party",
               "generated", ".yarn"}
GENERATED_NAMES = {"package-lock.json", "yarn.lock", "pnpm-lock.yaml",
                   "cargo.lock", "poetry.lock", "uv.lock", "gemfile.lock"}


def count_words(text: str) -> int:
    return len(text.split())


def keep_file(path: str) -> bool:
    """Code files only (extension allowlist), minus vendored/generated
    paths and minified assets — machine text in both arms."""
    parts = path.split("/")
    name = parts[-1].lower()
    if any(p in VENDOR_DIRS for p in parts[:-1]):
        return False
    if name in GENERATED_NAMES or name.endswith(".lock"):
        return False
    if ".min." in name or name.endswith(".map"):
        return False
    dot = name.rfind(".")
    return dot >= 0 and name[dot:] in CODE_EXTS


def fetch_diff(repo: str, num: int, cache_dir: Path,
               pace: float = 0.5) -> str | None:
    """Unified diff via REST, cached forever (diffs of merged PRs are
    immutable). None = fetch failed (candidate skipped, retried on the
    next run)."""
    p = cache_dir / f"{repo.replace('/', '~')}@{num}.diff"
    if p.is_file():
        return p.read_text(errors="replace")
    # bytes + replacement decoding: real diffs can carry non-UTF-8
    # bytes, and text=True would raise inside subprocess
    out = subprocess.run(
        ["gh", "api", f"repos/{repo}/pulls/{num}",
         "-H", "Accept: application/vnd.github.diff"],
        capture_output=True)
    time.sleep(pace)
    if out.returncode != 0:
        return None
    text = out.stdout.decode("utf-8", errors="replace")
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(p)
    return text


def parse_diff(text: str) -> list[tuple[str, list[list[str]]]]:
    """[(new_path, [hunk, ...])] in diff order, each hunk a list of added
    lines (markup stripped). Binary files and pure deletions drop out."""
    files: list[tuple[str, list[list[str]]]] = []
    path: str | None = None
    hunks: list[list[str]] = []
    cur: list[str] | None = None
    binary = False

    def flush():
        nonlocal path, hunks, cur, binary
        if cur:
            hunks.append(cur)
        if path and not binary and any(hunks):
            files.append((path, [h for h in hunks if h]))
        path, hunks, cur, binary = None, [], None, False

    for ln in text.splitlines():
        if ln.startswith("diff --git "):
            flush()
        elif cur is None and ln.startswith("+++ "):
            # the file header only exists OUTSIDE a hunk: inside one,
            # '+++counter;' is an added source line beginning '++'
            p = ln[4:].split("\t")[0].strip()
            path = None if p == "/dev/null" else \
                (p[2:] if p.startswith("b/") else p)
        elif ln.startswith(("Binary files", "GIT binary patch")):
            binary = True
        elif ln.startswith("@@"):
            if cur:
                hunks.append(cur)
            cur = []
        elif cur is not None and ln.startswith("+"):
            cur.append(ln[1:])
    flush()
    return files


def build_document(files: list, cap: int, floor: int) \
        -> tuple[str | None, dict]:
    """(document text, meta). None when the assembled document falls
    under the word floor — short code is undetectable in principle, so
    the slot's next ranked candidate is tried instead."""
    kept, dropped, parts = [], [], []
    words = 0
    truncated = False
    for path, hunks in files:
        if not keep_file(path):
            dropped.append(path)
            continue
        body = [ln for h in hunks for ln in h]
        seg = "\n".join([f"// file: {path}"] + body)
        w = count_words(seg)
        if words + w <= cap:
            parts.append(seg)
            words += w
            kept.append(path)
            continue
        if not parts:
            head = f"// file: {path}"
            acc, aw = [head], count_words(head)
            for h in hunks:
                hw = count_words("\n".join(h))
                if aw + hw > cap:
                    break
                acc += h
                aw += hw
            if len(acc) > 1:
                parts.append("\n".join(acc))
                words = aw
                kept.append(path)
        truncated = True
        break
    meta = {"words": words, "kept": kept, "dropped": dropped,
            "truncated": truncated}
    if words < floor:
        return None, meta
    return "\n".join(parts), meta
