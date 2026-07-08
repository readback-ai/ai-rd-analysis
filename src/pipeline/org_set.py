"""Stage 0 — HOW THE POPULATION IS DEFINED: the tracked org set.

The study population is an enumeration of leading AI organizations built from
EXTERNAL sources — no per-repo domain classification anywhere:

1. Candidate sources (third-party lists, snapshotted in data/resume_state/v2/):
   - lfai_orgs.txt      LF AI & Data landscape orgs (by project count)
   - hf_orgs.tsv        Hugging Face hub top orgs (models, downloads)
   - gh_topic_orgs.txt  GitHub orgs prominent in AI topics
   - v1_carryover.txt   frontier labs + TechCrunch 2025 $100M+-funded AI
                        companies (third-party list, handles verified via API)
   Union -> candidates (with source tags, candidates.tsv/candidates_clean.txt).
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
    """Each third-party source list -> set of org handles."""
    return {
        "lfai": {ln.split()[-1] for ln in _lines("lfai_orgs.txt")},
        "hf-hub": {ln.split("\t")[0] for ln in _lines("hf_orgs.tsv")},
        "gh-topic": set(_lines("gh_topic_orgs.txt")),
        "v1": set(_lines("v1_carryover.txt")),
    }


def candidates() -> dict[str, str]:
    """org -> 'src1|src2' union over sources (mirrors candidates.tsv)."""
    out: dict[str, set[str]] = {}
    for src, orgs in source_orgs().items():
        for org in orgs:
            out.setdefault(org, set()).add(src)
    return {org: "|".join(sorted(tags)) for org, tags in out.items()}


def quality_gated() -> set[str]:
    """Orgs whose flagship repo clears FLAGSHIP_MIN_STARS (org_scale.tsv)."""
    keep = set()
    for ln in _lines("org_scale.tsv")[1:]:
        f = ln.split("\t")
        if len(f) >= 3 and f[2].isdigit() and int(f[2]) >= FLAGSHIP_MIN_STARS:
            keep.add(f[0])
    return keep


def active() -> list[str]:
    """The frozen census population (what every published number uses)."""
    return _lines("v2_active.txt")


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
    unsourced = act - set(cand)
    if unsourced:
        print(f"WARN: {len(unsourced)} active orgs missing from all source "
              f"snapshots: {sorted(unsourced)[:10]}")
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
