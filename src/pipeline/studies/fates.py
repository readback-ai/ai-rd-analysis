"""Study: PR fates at MATCHED exposure horizons (paper point 4).

FROZEN CONVENTION: never compare fates across cohorts except at matched
horizons — "ever resolved" is a different quantity per cohort/quarter
(the mixed-horizon error). Primary horizon w8 (merges quiesce, 98-99% of
eventual); w26 as appendix sensitivity for slow rejections/limbo.

Usage:  python -m pipeline.studies.fates [--horizons 8 26]
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime

from pipeline.analyze import group_by_period, load_cells
from pipeline import detect
from pipeline.detect import MARKERS, classify_pr
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.slices import population_repos

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]


def _iso(ts):
    return datetime.fromisoformat(ts.replace("Z", "+00:00"))


def classify_at(p: dict, weeks: int) -> str | None:
    """Fate at a matched horizon: None if immature (horizon still open at
    the data AS_OF — not the frame-end CUTOFF, so bumping AS_OF after a
    re-pull finalizes trailing rows); events count within the horizon
    regardless of the frame end (external review P1)."""
    horizon = weeks * 7
    created = p.get("createdAt")
    if not created or (_iso(detect.AS_OF) - _iso(created)).days < horizon:
        return None

    def within(ev):
        return bool(ev) and (_iso(ev) - _iso(created)).days < horizon
    if within(p.get("mergedAt")):
        return "merged"
    if not p.get("mergedAt") and within(p.get("closedAt")):
        return "rejected"
    return "limbo"


def fates_at(weeks: int) -> None:
    keep = population_repos()
    agg = defaultdict(lambda: defaultdict(int))
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot":
                continue
            fate = classify_at(p, weeks)
            if fate is None:
                continue                     # immature at this horizon: skip
            c = classify_pr(p, MARKERS)
            for coh in ("all", "ins" if c.insider else "ext",
                        "AI" if c.ai_involved else "nonAI"):
                agg[(per, coh)][fate] += 1
                agg[(per, coh)]["n"] += 1
    print(f"--- fates at w{weeks} (matched horizon; immature PRs excluded) ---")
    print(f"{'cohort':16}{'n':>8}{'merged%':>9}{'rejected%':>10}{'limbo%':>8}")
    for per in PERIODS:
        for coh in ("all", "ins", "ext", "AI", "nonAI"):
            d = agg[(per, coh)]
            if not d["n"]:
                continue
            print(f"{per + ' ' + coh:16}{d['n']:>8}"
                  f"{100*d['merged']/d['n']:>8.1f}%"
                  f"{100*d['rejected']/d['n']:>9.1f}%"
                  f"{100*d['limbo']/d['n']:>7.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", nargs="+", type=int, default=[8, 26])
    for w in ap.parse_args().horizons:
        fates_at(w)
        print()


if __name__ == "__main__":
    main()
