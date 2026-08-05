# GPTZero code-detection calibration (designs v1-50k + eras-v1 + retest)

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
  - **Eras** (design eras-v1) — the paired contrast at 90 authors per
    quarter across Q4-2025, Q1-2026 and Q2-2026 (own manifest,
    quarter-namespaced seeds, prefix-stable deepening). Q2-2026 is an
    expansion: v1's authors are excluded and keep their v1 slots, so
    the pooled quarter is 90 distinct authors.
  - **Length sensitivity** — every document truncated at the 600-word
    cap is also scored at a 1200-word assembly (`--retest`, separate
    results file): the dose-response section bounds what document
    length does to the detector.
  - **Known-AI positive control** (design pc-v1) — agent-authored
    (layer-B) PRs from Q1/Q2-2026 through the same pipeline: validates
    the instrument and sets the score ceiling for reading the paired
    arms' mixtures. One slot per (agent, repo), per-login cap.
- **Determinism**: study seed 20260630, namespaced streams; manifest
  fingerprints AS_OF/CUTOFF/params/pool and is rebuilt-not-trusted.
  Candidate lists are seeded whole-pool shuffles, so deepening `k_cand`
  refills unfilled slots without disturbing fetched ones.
- **Budget**: a hard ceiling (`gptzero_client.BUDGET_WORDS`, raised
  only with the user's explicit approval — history in git) enforced
  against a durable **reservation ledger** — one row is appended before
  EVERY HTTP attempt, because an attempt can be billed server-side even
  when its response is lost (connection drop, crash before the cache
  write). Responses are cached by (detector version, document sha256)
  and a cached document is never re-billed under the same version.
  The ledger therefore over-counts after failures; **reconcile against
  the GPTZero dashboard**: archive
  `local/results/reservations_v1.jsonl` beside itself and seed a fresh
  ledger with one `{"doc_sha": "reconcile:<date>:gptzero-dashboard",
  "words": <dashboard credits>}` row. GPTZero credits equal this
  pipeline's word counts 1:1; refused/timed-out batches have never
  been billed at three reconciliations.
- **Batching**: `/v2/predict/files`, ≤50 files AND ≤20k words per
  request (bigger uploads time out server-side, returning HTTP 200
  error envelopes); transient failures retry with fresh reservations.
- **Version discipline**: the full run requires a pinned detector
  version. The smoke run may go unpinned; once pinned, requests carry
  the version, responses that report a different version are refused,
  results scored under any other (or no) version are invalidated and
  rescored, and the report refuses to pool mixed versions.

## Run

```
python experiments/gptzero/gz.py --sample            # manifest + pool sizes
python experiments/gptzero/gz.py --sample-eras       # Q4-2025/Q1-2026 arms
python experiments/gptzero/gz.py --fetch             # diffs -> documents
python experiments/gptzero/gz.py --sample-b3         # Q3-2022 arm
python experiments/gptzero/gz.py --sample-pc         # known-AI agents arm
python experiments/gptzero/gz.py --score --limit 2   # unpinned smoke
# read the smoke output's model version, then set
#   gptzero_client.PINNED_VERSION = "<that version>"
python experiments/gptzero/gz.py --score             # refuses while unpinned
python experiments/gptzero/gz.py --retest            # 1200-word sensitivity
python experiments/gptzero/gz.py                     # analysis report
python experiments/gptzero/gz.py --freeze            # commit-ready audit set
```

`frozen/` holds the committed audit set for the reported numbers
(manifests, row metadata, scores, generated report, provenance);
regenerate it with `--freeze` after any scoring change.

API key: `GPTZERO_API_KEY` env var, or paste into `local/api_key`.
Raw data (documents, diffs, API responses, reservations) lives under
`local/` — gitignored. Committed alongside the code: this README and
the `frozen/` audit set (validated manifests, row metadata, scores,
paragraph summaries, generated report, provenance) that backs any
reported numbers.

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
- **Q2-2026 covers April 1 – June 6 creations** (w8 maturity at AS_OF
  2026-08-01); June 7–30 is unmeasured until a later AS_OF. Never
  present Q2-2026 as a complete quarter.
- The sampling frame tracks the study's canonical census: when AS_OF
  advances (monthly update), manifests redraw and fingerprints change
  by design — the 2026-08-04 frozen set under the July frame remains
  in git history (PR #28) as the prior snapshot.

v2 (the ~2M-word sweep across all quarters) = a new design tag with
bigger quotas; the response cache carries over, so overlapping
documents are never re-billed.
