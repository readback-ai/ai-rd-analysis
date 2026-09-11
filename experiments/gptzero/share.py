"""Shareable dataset package for GPTZero (design share-v1).

Assembles, from explicit inputs only, a self-contained package of the
documents exactly as submitted, the study's per-document scores, the
endpoint comparison, the ablation and length-retest variants, the
agent case-study matrix (both endpoints x both model versions), and
the raw API responses as received — so the recipient can see exactly
what each endpoint did to each document.

Privacy: GitHub logins never leave. Human authors get sequential
pseudonyms assigned in doc-id order (stable for a given corpus,
not a reversible hash), which keeps the within-author pairing usable;
slot ids are dropped because they embed logins. Repo and PR number
stay as provenance for public open-source code.

Safety: nothing is copied wholesale — every output file is written
from a known source — and the finished package is scanned for the API
key; a hit aborts before the archive is made.
"""
from __future__ import annotations

import difflib
import hashlib
import json
import re
import shutil
from collections import Counter
from pathlib import Path

DESIGN = "share-v1"
FORBIDDEN_NAMES = (".env", "curl_headers", "api_key")

# The four agent-authored documents cited in the correspondence with
# GPTZero: one per agent vendor, all scored human on the corpus model.
CASE_STUDIES = (("cursor", "Giskard-AI/giskard-hub-python", 20),
                ("copilot-swe-agent", "lemonade-sdk/lemonade", 934),
                ("devin-ai-integration", "firecrawl/firecrawl", 2635),
                ("claude", "Arize-ai/openinference", 3156))
# The study's pinned model, and the newer default the dashboard serves.
CASE_VERSIONS = ("2026-07-04-base", "2026-08-09-base")


def arm_label(r: dict) -> str | None:
    return {"B3": "baseline_2022q3", "B1": "baseline_2024q1",
            "B2": "baseline_2024q1", "P": "paired",
            "PC": "agent"}.get(r["arm"])


def pseudonyms(rows: list[dict]) -> dict[str, str]:
    """login -> h0001.. for human authors, assigned in doc-id order so
    the numbering carries no information about the login."""
    out: dict[str, str] = {}
    for r in sorted(rows, key=lambda r: r["doc_sha"]):
        if r["arm"] == "PC" or not r.get("author"):
            continue
        if r["author"] not in out:
            out[r["author"]] = f"h{len(out) + 1:04d}"
    return out


def scores(r: dict) -> dict:
    """Flat score fields from a results row or a raw response doc."""
    cp = r.get("class_probabilities") or {}
    return {"predicted_class": r.get("predicted_class"),
            "p_ai": cp.get("ai"), "p_human": cp.get("human"),
            "p_mixed": cp.get("mixed"),
            "completely_generated_prob":
                r.get("completely_generated_prob")}


def response_doc(resp: dict) -> dict:
    return (resp.get("documents") or [{}])[0]


def normalization(sent: str, received: str | None) -> dict:
    """What the endpoint did to the document before scoring it."""
    if received is None:
        return {"received_bytes": None, "received_identical": None,
                "leading_ws_retained": None}

    def lead(text: str) -> int:
        return sum(len(ln) - len(ln.lstrip())
                   for ln in text.splitlines())
    sent_lead = lead(sent)
    return {"received_bytes": len(received.encode()),
            "received_identical": received == sent,
            "leading_ws_retained": (round(lead(received) / sent_lead, 4)
                                    if sent_lead else None)}


def canonical(text: str) -> str:
    """Whitespace-free form, for matching a response back to the
    document it scored despite the endpoint's rewriting."""
    return re.sub(r"\s+", "", text)


def adopt_legacy(legacy_dir: Path, dest: Path, sent: str,
                 version: str) -> bool:
    """Recover a response captured before the cache was namespaced by
    version: adopt a legacy response only if it reports `version` and
    its scored text matches this document closely enough to be
    unambiguous."""
    if dest.is_file():
        return True
    want = canonical(sent)
    for p in sorted(legacy_dir.glob("*.json")) if legacy_dir.is_dir() \
            else []:
        resp = json.loads(p.read_text())
        if resp.get("version") != version:
            continue
        got = canonical(response_doc(resp).get("inputText") or "")
        if got and difflib.SequenceMatcher(
                a=want, b=got, autojunk=False).ratio() > 0.95:
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(p.read_text())
            return True
    return False


def corruption_stats(pairs: list[tuple[str, str]]) -> dict:
    """Characterise what the files endpoint did to the documents:
    pairs are (submitted, scored) texts."""
    subs: Counter = Counter()
    dropped: Counter = Counter()
    ws_only = char_level = identical = 0
    for sent, got in pairs:
        if sent == got:
            identical += 1
            continue
        a, b = canonical(sent), canonical(got)
        if a == b:
            ws_only += 1
            continue
        char_level += 1
        for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                a=a, b=b, autojunk=False).get_opcodes():
            if tag == "replace":
                subs[(a[i1:i2][:8], b[j1:j2][:8])] += 1
            elif tag == "delete":
                dropped[a[i1:i2][:8]] += 1
    return {"n": len(pairs), "identical": identical,
            "whitespace_only": ws_only, "character_level": char_level,
            "substitutions": subs, "dropped": dropped}


def corruption_report(s: dict) -> str:
    """Standalone note on the files-endpoint rewriting."""
    def cell(t: str) -> str:
        return t.replace("|", r"\|")        # keep the table renderable
    sub = "\n".join(
        f"| `{cell(x)}` | `{cell(y)}` | {n} |" for (x, y), n in
        s["substitutions"].most_common(12))
    drop = ", ".join(f"`{x}` ({n})" for x, n in
                     s["dropped"].most_common(8))
    return f"""# What `/v2/predict/files` does to a document before scoring it

Measured over the {s['n']} documents in `corpus.jsonl`, by comparing
the bytes we uploaded against the `inputText` field of the response —
i.e. the text the model actually scored. The same bytes submitted to
`/v2/predict/text` arrive unchanged (96/96 in
`endpoint_comparison.jsonl`), so this is specific to the files
endpoint.

| outcome | documents |
|---|---|
| arrived unchanged | {s['identical']} |
| whitespace rewritten only | {s['whitespace_only']} |
| characters altered as well | {s['character_level']} |

## 1. Whitespace

Runs of spaces and tabs are collapsed and blank lines dropped, so
indentation is largely lost: across the corpus a median
{s['median_ws']:.0%} of leading whitespace survives. For source code
this removes block structure.

## 2. `|` becomes `"`

The most common substitution by a wide margin. This corrupts Python
type unions (`str | None`), logical OR (`a || b`), shell pipes and
Markdown tables.

| submitted | scored as | occurrences |
|---|---|---|
{sub}

## 3. Non-ASCII is mis-decoded

Characters outside ASCII arrive as mojibake or are dropped, the
signature of UTF-8 bytes being decoded as latin-1/cp1252 (`Â`
insertions, `Ã—` for `×`). Dropped entirely: {drop}.

Em dashes, arrows, box-drawing characters and emoji are all affected —
common in comments, docstrings and CLI help text.

## Does it change the scores?

Not on `2026-07-04-base`: `endpoint_comparison.jsonl` re-scores {s['ep_n']}
of these documents through the text endpoint on the same model and
finds {s['ep_flips']} verdict flips. It does on `2026-08-09-base` — see
`agent_case_studies.jsonl` and the README.
"""


def check_secret(out_dir: Path, secret: str | None) -> None:
    """Abort if any packaged file carries the API key or a credential
    file name."""
    for p in out_dir.rglob("*"):
        if any(bad in p.name for bad in FORBIDDEN_NAMES):
            raise SystemExit(f"share refused: forbidden file {p}")
        if secret and p.is_file() and secret.encode() in p.read_bytes():
            raise SystemExit(f"share refused: API key found in {p}")


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(r, sort_keys=True) + "\n"
                            for r in rows))


def write_manifest(out_dir: Path) -> None:
    lines = []
    for p in sorted(q for q in out_dir.rglob("*") if q.is_file()):
        digest = hashlib.sha256(p.read_bytes()).hexdigest()
        lines.append(f"{digest}  {p.relative_to(out_dir)}")
    (out_dir / "MANIFEST.sha256").write_text("\n".join(lines) + "\n")


def archive(out_dir: Path) -> Path:
    zip_base = out_dir.parent / out_dir.name
    shutil.make_archive(str(zip_base), "zip", out_dir.parent,
                        out_dir.name)
    return zip_base.with_suffix(".zip")


def readme(s: dict) -> str:
    """The package README, filled from the package's own counts."""
    return f"""# GPTZero on source code — calibration dataset

Prepared for GPTZero, {s['date']}. Companion to our correspondence
(July–September 2026).

## What this is

Documents built from merged pull requests in the public GitHub
repositories of AI organizations, scored with GPTZero's API during a
calibration study of whether text AI-detection works on source code.
Every document is included exactly as submitted, with the scores we
received and the raw API responses — including `inputText`, which
shows what each endpoint actually scored.

## Headline observations

- `/v2/predict/files` rewrites uploads before scoring — see
  `normalization_analysis.md`. Only {s['identical']} of {s['n_corpus']}
  documents arrived unchanged; a median {s['median_ws']:.0%} of leading
  whitespace survived, `|` is replaced by `"` ({s['pipe_subs']}
  occurrences), and non-ASCII is mis-decoded as latin-1/cp1252. The
  same bytes sent to `/v2/predict/text` arrive intact
  ({s['ep_identical']}/{s['ep_n']} documents).
- On `2026-07-04-base` that normalisation is inert: the {s['ep_n']}
  documents in `endpoint_comparison.jsonl` show {s['ep_flips']} verdict
  flips between endpoints.
- On `2026-08-09-base` it is not: `Arize-ai/openinference#3156` scores
  ai={s['cs_files']} via files and ai={s['cs_text']} via text under the
  newer model — human versus AI on identical bytes.{s['cs_note']} That
  document is `documents/{s['cs_doc']}.txt`.
- `perplexity` is 0 on every sentence we received; `overall_burstiness`
  is 0 and `writing_stats` is empty on every document.

A natural test of the newer model's structural sensitivity: run the
`endpoint_comparison.jsonl` documents through both endpoints on
`2026-08-09-base`.

## Document construction

- A document is the ADDED lines of one merged PR's code files
  (extension allowlist; vendored, generated and lock files dropped;
  deletions, context lines and diff markup stripped).
- One `// file: <path>` header per file; files are packed whole, in
  diff order, to a 600-word cap (only the first file may be truncated,
  at a hunk boundary); documents under 100 words are rejected.
- `doc_id` is the SHA-256 of the document bytes;
  `documents/<doc_id>.txt` is exactly what was submitted.

## Arms

| arm | meaning |
|---|---|
| `baseline_2022q3` | Q3 2022 PRs — before ChatGPT, human-written by construction |
| `baseline_2024q1` | Q1 2024 PRs without AI markers |
| `paired` | 2025–2026 PRs by developers with both AI-attributed and unmarked PRs in the same quarter; one of each per developer |
| `agent` | PRs authored end-to-end by coding-agent bot accounts (Devin, Copilot agent, Cursor, Claude) |

`ai_attributed` means the PR carried an explicit AI marker (co-author
trailer, agent branch prefix, etc.). Unmarked does not mean
human-written. `Q2-2026` covers PRs created April 1 – June 6, 2026.

## Files

- `corpus.jsonl` / `corpus.csv` — {s['n_corpus']} documents: arm,
  period, attribution, pseudonymous author, repo, PR, length, the
  scores we received, and what the files endpoint did to the bytes
  (`sent_bytes`, `received_bytes`, `received_identical`,
  `leading_ws_retained`).
- `endpoint_comparison.jsonl` — {s['ep_n']} corpus documents re-scored
  through `/v2/predict/text` on the same model (`files_*` vs `text_*`).
- `agent_case_studies.jsonl` — 4 agent documents across endpoints and
  model versions ({s['cs_cells']} of 16 cells; the remainder could not
  be captured because our API access was blocked, and the documents are
  in `documents/` for you to re-run).
- `normalization_analysis.md` — exactly what the files endpoint does to
  a document, measured against the `inputText` it returns.
- `ablation.jsonl` — {s['abl_n']} code-only / comments-only variants of
  {s['abl_n'] // 2} corpus documents; `parent_doc_id` links back.
- `length_retest.jsonl` — {s['rt_n']} documents re-assembled at a
  1,200-word cap; `parent_doc_id` links to the 600-word version.
- `responses/<endpoint>/<model_version>/<doc_id>.json` — raw API
  responses exactly as received.
- `MANIFEST.sha256` — checksums of every file.

## Privacy and use

GitHub logins are replaced by pseudonymous `author_id`s, stable within
this package (a developer keeps one id across quarters). Repository and
PR number are kept as provenance; the documents are excerpts of public
open-source code under their original licenses. Shared for evaluating
GPTZero's behaviour on source code — please check with us before
redistributing it or using it for training.
"""
