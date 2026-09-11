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

import hashlib
import json
import shutil
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

- `/v2/predict/files` normalises uploads before scoring:
  {s['identical']} of {s['n_corpus']} corpus documents arrived
  byte-identical, and a median {s['median_ws']:.0%} of leading whitespace
  survived. `/v2/predict/text` is byte-faithful
  ({s['ep_identical']}/{s['ep_n']} documents).
- On `2026-07-04-base` that normalisation is inert: the {s['ep_n']}
  documents in `endpoint_comparison.jsonl` show {s['ep_flips']} verdict
  flips between endpoints.
- On `2026-08-09-base` it is not: see `agent_case_studies.jsonl`, where
  `Arize-ai/openinference#3156` scores ai={s['cs_files']:.3f} via files
  and ai={s['cs_text']:.3f} via text under the newer model.
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
- `agent_case_studies.jsonl` — 4 agent documents × 2 endpoints × 2
  model versions.
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
