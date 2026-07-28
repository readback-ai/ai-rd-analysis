# GPTZero code-detection calibration (design v1-50k)

Can GPTZero detect LLM-generated **code**? The study's detection layers
(markers / agent authors / branch prefixes, A∪B∪C) are floors; a text
detector that works on diffs could see AI use the layers can't (default
Codex CLI leaves no trace). Before trusting it for anything, this
experiment calibrates GPTZero against the study's own labels.

## Protocol

- **Document** = the ADDED LINES of one PR's code files (extension
  allowlist; vendored/generated paths dropped; deletions, context, and
  diff markup stripped). Per file: a `// file: <path>` header. Packed
  whole-file in diff order to a **600-word cap** (only the first file
  may be truncated, at a hunk boundary); documents under **100 words**
  are rejected and the slot's next candidate is tried.
- **Arms** (author-centric; humans only, non-fleet, merged + w8-mature,
  raw LOC 50–2000, `ai_contrast_eligible`):
  - **P** — 30 Q2-2026 authors with ≥1 AI-involved and ≥1 unmarked PR;
    one document per arm per author (within-author contrast).
  - **B1** — those authors' own Q1-2024 PRs where they exist
    (same-author-across-eras anchor).
  - **B2** — independent Q1-2024 authors, to 20 baseline docs total.
- **Determinism**: study seed 20260630, namespaced streams; manifest
  fingerprints AS_OF/CUTOFF/params/pool and is rebuilt-not-trusted.
  Candidate lists are seeded whole-pool shuffles, so deepening `k_cand`
  refills unfilled slots without disturbing fetched ones.
- **Budget**: ≤80 docs × ≤600 words ≤ 48k, under a hard 50k ceiling
  enforced before any HTTP; responses cached by document sha256 and
  never re-billed; the ledger is recomputed from the results file.

## Run

```
python experiments/gptzero/gz.py --sample   # manifest + pool sizes
python experiments/gptzero/gz.py --fetch    # diffs -> documents
python experiments/gptzero/gz.py --score --limit 2   # smoke first
python experiments/gptzero/gz.py --score
python experiments/gptzero/gz.py            # analysis report
```

API key: `GPTZERO_API_KEY` env var, or paste into `local/api_key`.
Everything data-shaped (manifest, documents, diffs, responses, scores)
lives under `local/` — gitignored; only code and this README are
committed.

## What the numbers do and don't license

- Paired authors are by construction **AI adopters**: the contrast is
  "does GPTZero separate the same adopter's marked vs unmarked code" —
  not a population detection rate, and not AI vs verified-human.
- **Unmarked ≠ human**; undisclosed AI in the unmarked arm biases the
  separation down, so detection estimates are conservative.
- **Q1-2024 is descriptive**: near-human-era code with some early-model
  AI, not verified ground truth.
- The paired arm is **A∪C-heavy** (layer-B bot logins can't anchor a
  human-paired design).
- Known selection effect from the fetch stage: AI-marked PRs fail the
  100-word code floor more often than unmarked ones (docs/config-heavy
  agent PRs) — `--fetch` prints the per-arm unfilled counts.

v2 (the ~2M-word sweep across all quarters) = a new design tag with
bigger quotas; the response cache carries over, so overlapping
documents are never re-billed.
