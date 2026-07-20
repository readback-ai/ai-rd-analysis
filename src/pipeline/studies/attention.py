"""Study: per-line review attention (paper point 3).

PRIMARY measure: HUMAN inline review comments per changed kLOC on merged,
human-reviewed PRs — bot comments are excluded from the numerator by
construction (comments are summed from detect.split_reviews' human_other
bucket, which excludes Bot-typed AND User-typed bot accounts).
CORROBORATING proxy (never the lead): creation->merge window hours/kLOC.
The size-band table separates within-size thinning from the composition
shift toward larger PRs; both are reported.

Usage:  python -m pipeline.studies.attention
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import CUTOFF, MARKERS, classify_pr, split_reviews
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.slices import population_repos

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
CAP = 20_000
BANDS = [(1, 10, "<=10"), (11, 100, "11-100"), (101, 1000, "101-1k"),
         (1001, CAP, ">1k")]


def _hours(a, b):
    return (datetime.fromisoformat(b.replace("Z", "+00:00"))
            - datetime.fromisoformat(a.replace("Z", "+00:00"))).total_seconds() / 3600


def main() -> None:
    keep = population_repos()
    agg = defaultdict(lambda: defaultdict(float))
    band = defaultdict(lambda: defaultdict(float))
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot":
                continue
            c = classify_pr(p, MARKERS)
            if not (c.merged and c.human_reviewed and p.get("createdAt")
                    and p.get("mergedAt")):
                continue
            loc = min((p.get("additions") or 0) + (p.get("deletions") or 0), CAP)
            if not loc:
                continue
            human_other, _, _ = split_reviews(p)     # bot-clean by construction
            comments = sum((r.get("comments") or {}).get("totalCount", 0)
                           for r in human_other
                           if (r.get("submittedAt") or "") <= CUTOFF)
            win = _hours(p["createdAt"], p["mergedAt"])
            for coh in ("all", "ins" if c.insider else "ext"):
                d = agg[(per, coh)]
                d["kloc"] += loc / 1000
                d["hours"] += win
                d["comments"] += comments
                d["n"] += 1
            for lo, hi, name in BANDS:
                if lo <= loc <= hi:
                    b = band[(per, name)]
                    b["kloc"] += loc / 1000
                    b["comments"] += comments
                    break
    print("attention per line — merged, human-reviewed PRs (pooled)")
    print(f"{'cohort':14}{'PRs':>8}{'kLOC':>9}{'comments/kLOC':>14}"
          f"{'window h/kLOC':>14}")
    for per in PERIODS:
        for coh in ("all", "ins", "ext"):
            d = agg[(per, coh)]
            if not d["n"]:
                continue
            print(f"{per + ' ' + coh:14}{int(d['n']):>8}{d['kloc']:>9,.0f}"
                  f"{d['comments']/d['kloc']:>14.2f}{d['hours']/d['kloc']:>14.1f}")
    print("\ncomments/kLOC within FIXED size bands (composition-controlled)")
    print(f"{'band':9}" + "".join(f"{p:>11}" for p in PERIODS))
    for _, _, name in BANDS:
        line = f"{name:9}"
        for per in PERIODS:
            b = band[(per, name)]
            line += f"{b['comments']/b['kloc']:>11.2f}" if b["kloc"] else f"{'—':>11}"
        print(line)


if __name__ == "__main__":
    main()
