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

from pipeline import detect
from pipeline.frame import PERIODS, ai_contrast_eligible, study_frame

MIN_N = 20   # floor for a printed cohort row, aligned with review_action's
             # lane floor and slices' MIN_PRS: a handful of PRs cannot carry
             # a percentage next to a 63k-PR cohort (review finding 6).
             # Suppressed cohorts are listed under the table, never dropped
             # silently.


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
    """Population: profile 'all' + ai_contrast_eligible, with fleet-operator
    authors excluded (issue #2) — agent-authored PRs count in all/AI/nonAI
    so layer-B output gets a fate, while non-AI bots and login-less authors
    stay out of the nonAI comparison arm (2026-07-25 review). ins/ext stay
    human-authored (a Bot's NONE association is not an 'external
    contributor'), so `all` exceeds ins+ext by the layer-B agent PRs —
    footnoted under the table."""
    from pipeline.studies.productivity import fleet_logins
    fleet = fleet_logins()
    agg = defaultdict(lambda: defaultdict(int))
    for f in study_frame("all"):
        if not ai_contrast_eligible(f):
            continue          # bots/ghosts would swell the nonAI arm
        if f.author in fleet:
            continue          # fleet pipelines distort fate rates
        fate = classify_at(f.pr, weeks)
        if fate is None:
            continue                     # immature at this horizon: skip
        cohorts = ["all", "AI" if f.cls.ai_involved else "nonAI"]
        if f.bot_author:
            agg[(f.period, "layerB")]["n"] += 1   # footnote: the all-ins-ext gap
        else:
            cohorts.append("ins" if f.cls.insider else "ext")
        for coh in cohorts:
            agg[(f.period, coh)][fate] += 1
            agg[(f.period, coh)]["n"] += 1
    print(f"--- fates at w{weeks} (matched horizon; immature PRs excluded) ---")
    print(f"{'cohort':16}{'n':>8}{'merged%':>9}{'rejected%':>10}{'limbo%':>8}")
    thin = []
    for per in PERIODS:
        for coh in ("all", "ins", "ext", "AI", "nonAI"):
            d = agg[(per, coh)]
            if not d["n"]:
                continue
            if d["n"] < MIN_N:
                thin.append(f"{per} {coh} n={d['n']}")
                continue
            print(f"{per + ' ' + coh:16}{d['n']:>8}"
                  f"{100*d['merged']/d['n']:>8.1f}%"
                  f"{100*d['rejected']/d['n']:>9.1f}%"
                  f"{100*d['limbo']/d['n']:>7.1f}%")
    if thin:
        print(f"suppressed (n < {MIN_N}, too few PRs to carry a rate): "
              + "; ".join(thin))
    gap = {per: agg[(per, "layerB")]["n"] for per in PERIODS}
    if any(gap.values()):
        print("note: all = AI + nonAI exactly; all = ins + ext + "
              "agent-authored (a Bot has no human author association) — "
              + ", ".join(f"{p} {n}" for p, n in gap.items() if n))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizons", nargs="+", type=int, default=[8, 26])
    for w in ap.parse_args().horizons:
        fates_at(w)
        print()


if __name__ == "__main__":
    main()
