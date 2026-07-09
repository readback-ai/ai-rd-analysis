"""Stage 0 — HOW THE POPULATION IS DEFINED: the tracked org set.

The study population is an enumeration of leading AI organizations built from
EXTERNAL sources — no per-repo domain classification anywhere:

1. Candidate sources (third-party lists, snapshotted in data/resume_state/v2/):
   - lfai_orgs.txt      LF AI & Data landscape orgs (by project count)
   - hf_orgs.tsv        Hugging Face hub top orgs (models, downloads) — HF
                        handles; TRANSCRIBED to GitHub handles in
                        candidates.tsv (e.g. laion -> LAION-AI)
   - gh_topic_orgs.txt  GitHub orgs prominent in AI topics
   - v1_carryover.txt   TRANSCRIBED lab/startup list: funded startups from
                        TechCrunch's 2025 $100M+ AI round-up + frontier labs
                        by public prominence; handles API-verified; per-org
                        category annotations included
   candidates.tsv is the transcription RECORD (GitHub handle -> source tags);
   verification compares against it, since raw HF handles differ from GitHub
   handles. All four sources are third-party lists; our contribution is handle
   transcription/verification, not membership judgment.
2. Quality gate: org's flagship repo has >=1,000 stars (org_scale.tsv,
   collected via API) — drops hobbyist/placeholder orgs.
3. AI-evidence keep: the org-level commit scan (stage 1) found tool-marker
   activity — >=5 marker commits OR >=0.1% of PRs in the scan window
   (ai_scan.tsv). An org with zero detectable AI evidence contributes nothing
   to AI-practice metrics and only noise to denominators.

The FROZEN population actually censused is v2_active.txt (215 orgs -> 1,996
repos, census_repos.txt). The keep step used live API data at scan time, so
re-deriving today drifts slightly; this module therefore (a) rebuilds the
candidate/gate layers reproducibly from the snapshot files and (b) VERIFIES
the frozen population against them, printing the reconciliation instead of
regenerating the set silently.

Usage:
  python -m pipeline.org_set --verify
"""
from __future__ import annotations

import argparse
from pathlib import Path

V2 = Path("data/resume_state/v2")
FLAGSHIP_MIN_STARS = 1000
KEEP_MIN_COMMITS = 5          # abs branch of the keep rule
KEEP_MIN_PR_RATE = 0.001      # rate branch (enum_repos.keep_reason mirrors this)


def _lines(name: str) -> list[str]:
    return [ln.strip() for ln in (V2 / name).read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


def source_orgs() -> dict[str, set[str]]:
    """Each third-party source list -> set of handles AS LISTED (HF handles
    for hf-hub; GitHub handles elsewhere). For membership checks use
    candidates(), which holds the transcribed GitHub handles."""
    return {
        "lfai": {ln.split()[-1] for ln in _lines("lfai_orgs.txt")},
        "hf-hub": {ln.split("\t")[0] for ln in _lines("hf_orgs.tsv")},
        "gh-topic": set(_lines("gh_topic_orgs.txt")),
        "v1": {ln.split("\t")[0] for ln in _lines("v1_carryover.txt")},
    }


def candidates() -> dict[str, str]:
    """GitHub handle -> 'src1|src2' source tags: the transcription record
    (candidates.tsv, GitHub handles) plus the v1 lab/startup list."""
    out: dict[str, str] = {}
    for ln in _lines("candidates.tsv"):
        f = ln.split("\t")
        if len(f) == 2:
            out[f[0]] = f[1]
    for org in source_orgs()["v1"]:
        out[org] = (out[org] + "|v1") if org in out else "v1"
    return out


def quality_gated() -> set[str]:
    """Orgs whose flagship repo clears FLAGSHIP_MIN_STARS (org_scale.tsv)."""
    keep = set()
    for ln in _lines("org_scale.tsv")[1:]:
        f = ln.split("\t")
        if len(f) >= 3 and f[2].isdigit() and int(f[2]) >= FLAGSHIP_MIN_STARS:
            keep.add(f[0])
    return keep


# Flagship AI-topic gate (2026-07-09): orgs whose ONLY provenance is a
# generic ecosystem list (LF AI & Data, GitHub topics) must show AI presence
# in their repo portfolio. Maintainer-declared topics, frozen dictionary.
# Pass if >=2 of the top-10 starred repos carry an AI topic, or the #1 repo
# does (single-product orgs), or the login/description carries an AI term
# (rescues topic-sparse AI orgs). AI-scoped sources (TechCrunch/frontier v1
# list, HF hub model publishers) are exempt: the source itself asserts
# AI-ness. Scan results: flagship_gate.tsv (pipeline-generated).
AI_TOPICS = {
    "machine-learning", "deep-learning", "artificial-intelligence", "ai",
    "neural-network", "neural-networks", "llm", "llms", "large-language-models",
    "nlp", "natural-language-processing", "computer-vision",
    "reinforcement-learning", "generative-ai", "transformers",
    "diffusion-models", "ai-agents", "mlops", "speech-recognition",
    "text-to-speech", "llmops", "language-model", "gpt", "chatgpt",
    "stable-diffusion", "rag", "fine-tuning", "model-serving",
}
LOGIN_FALLBACK = ("ai", "ml", "llm", "agi", "nlp", "intelligence")


def flagship_gate() -> dict[str, bool]:
    """org -> passed, from the scan snapshot (flagship_gate.tsv)."""
    out = {}
    for ln in _lines("flagship_gate.tsv"):
        f = ln.split("\t")
        if len(f) >= 2:
            out[f[0]] = f[1] == "1"
    return out


def active() -> list[str]:
    """The frozen v2 census population (basis of v2_results §1-13)."""
    return _lines("v2_active.txt")


def v21_active() -> list[str]:
    """The v2.1 population: v2 minus 17 gate-failing generic-list orgs
    (v21_retro_dropped.txt) plus 56 re-audited additions
    (additions_orgs_gated.txt). Frozen in v21_active.txt."""
    return _lines("v21_active.txt")


# Tier-2 repo-scoped orgs (2026-07-09): orgs that FAIL the flagship gate as a
# whole (not primarily AI developers) but have >=2 AI-topic repos with >=1k
# stars. Their AI-TOPIC REPOS ONLY are included as a labeled stratum — the
# org-level metrics exclude them or flag them, since their rate describes the
# org's AI unit, not the org. Qualification scan: repo_scope_scan.tsv;
# included repos: tier2_repos.txt (all AI-topic repos, full pagination).
def tier2_orgs() -> list[str]:
    return _lines("tier2_orgs.txt")


def tier2_repos() -> list[str]:
    return [ln.split("\t")[0] for ln in _lines("tier2_repos.txt")]


def verify() -> None:
    srcs = source_orgs()
    cand = candidates()
    gate = quality_gated()
    act = set(active())
    ext = act - srcs["v1"]
    print("sources: " + ", ".join(f"{k}={len(v)}" for k, v in srcs.items()))
    print(f"candidates (union): {len(cand)}")
    print(f"quality gate (flagship >= {FLAGSHIP_MIN_STARS} stars): {len(gate)}")
    print(f"frozen active population: {len(act)} "
          f"= {len(ext)} externally-listed + {len(act & srcs['v1'])} v1-carryover")
    lower = {c.lower() for c in cand}
    unsourced = {o for o in act if o.lower() not in lower}
    if unsourced:
        print(f"WARN: {len(unsourced)} active orgs missing from all source "
              f"snapshots: {sorted(unsourced)[:10]}")
    else:
        print("every active org traces to a source snapshot (case-insensitive)")
    ungated = ext - gate
    if ungated:
        print(f"note: {len(ungated)} externally-listed active orgs below the "
              f"gate snapshot (scan-time API drift): {sorted(ungated)[:10]}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify()
    else:
        print("\n".join(active()))


if __name__ == "__main__":
    main()
