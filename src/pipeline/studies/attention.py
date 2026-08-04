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

from pipeline.detect import split_reviews
from pipeline.frame import CAP, PERIODS, ai_contrast_eligible, study_frame

BANDS = [(1, 10, "<=10"), (11, 100, "11-100"), (101, 1000, "101-1k"),
         (1001, CAP, ">1k")]


def _hours(a, b):
    return (datetime.fromisoformat(b.replace("Z", "+00:00"))
            - datetime.fromisoformat(a.replace("Z", "+00:00"))).total_seconds() / 3600


def human_comment_count(pr: dict) -> int:
    """Inline comments on reviewer!=author human reviews; split_reviews is
    bot-clean AND w8-windowed — no extra time filter belongs here."""
    human_other, _, _ = split_reviews(pr)
    return sum((r.get("comments") or {}).get("totalCount", 0)
               for r in human_other)


def attention_by_ai(fleet_slice: bool = False,
                    granularity: str = "quarter") -> dict:
    """Figure 7: attention proxies by PR AI involvement (FLEET-OPERATOR
    authors excluded) — pooled over
    mature, merged, human-reviewed PRs per quarter x {ai, nonai}:
    comments/kLOC (bot-clean human inline comments) and FIRST-REVIEW
    latency hours/kLOC (PR creation -> first human review submission,
    per kLOC — smaller = more LOC absorbed per elapsed hour). The ai
    slice is empty at the Q1-2024 baseline by construction.
    granularity="month": rows keyed by calendar month over the baseline
    + window months (the Figure 3 companion; display-side callers gate
    to w8-final months).

    Returns {(period, slice): {n, kloc, comments_per_kloc,
    first_rev_h_per_kloc}}."""
    from pipeline.studies.productivity import (BASELINE_MONTHS,
                                               WINDOW_MONTHS, fleet_logins)
    from pipeline.studies.review_action import first_human_review
    fleet = fleet_logins()
    frame_kw = {} if granularity == "quarter" else \
        {"periods": BASELINE_MONTHS + WINDOW_MONTHS, "granularity": "month"}
    agg = defaultdict(lambda: defaultdict(float))
    # profile "all", NOT "pr": this population never excluded Bot-typed
    # authors, so agent-authored PRs already count in the ai slice here
    # (unlike main()'s table) — see issue #2. ai_contrast_eligible keeps
    # non-AI bots and login-less authors OUT of the nonai slice, where
    # dep-bumps merged without discussion would deflate its comments/kLOC
    # (2026-07-25 review).
    for f in study_frame("all", **frame_kw):
        if not ai_contrast_eligible(f):
            continue
        is_fleet = f.author in fleet
        if is_fleet and not fleet_slice:
            continue                 # fleet pipelines distort review stats
        p, c = f.pr, f.cls
        if not (c.w8_mature and c.merged and c.human_reviewed
                and p.get("createdAt")):
            continue
        frt = first_human_review(p)
        if not frt or not f.loc:
            continue
        sl = "fleet" if is_fleet else ("ai" if c.ai_involved else "nonai")
        d = agg[(f.period, sl)]
        d["n"] += 1
        d["kloc"] += f.loc / 1000
        d["comments"] += human_comment_count(p)
        d["frt_hours"] += _hours(p["createdAt"], frt)
    return {k: {"n": int(d["n"]), "kloc": d["kloc"],
                "comments_per_kloc": d["comments"] / d["kloc"],
                "first_rev_h_per_kloc": d["frt_hours"] / d["kloc"]}
            for k, d in agg.items() if d["kloc"]}


def attention_by_ai_table() -> None:
    rows = attention_by_ai()
    print("\nattention by PR AI involvement (mature merged human-reviewed "
          "PRs, pooled, fleet-operator authors excluded)")
    print(f"{'period':9}{'slice':7}{'PRs':>7}{'kLOC':>9}"
          f"{'comments/kLOC':>15}{'first-rev h/kLOC':>18}")
    for per in PERIODS:
        for sl in ("ai", "nonai"):
            r = rows.get((per, sl))
            if not r:
                continue
            print(f"{per:9}{sl:7}{r['n']:>7}{r['kloc']:>9,.0f}"
                  f"{r['comments_per_kloc']:>15.2f}"
                  f"{r['first_rev_h_per_kloc']:>18.1f}")


def main() -> None:
    agg = defaultdict(lambda: defaultdict(float))
    band = defaultdict(lambda: defaultdict(float))
    for f in study_frame("pr"):
        p, c = f.pr, f.cls
        if not (c.w8_mature and c.merged and c.human_reviewed
                and p.get("createdAt") and p.get("mergedAt")):
            continue              # outcome-conditioned: mature PRs only
        if not f.loc:
            continue
        comments = human_comment_count(p)
        win = _hours(p["createdAt"], p["mergedAt"])
        for coh in ("all", "ins" if c.insider else "ext"):
            d = agg[(f.period, coh)]
            d["kloc"] += f.loc / 1000
            d["hours"] += win
            d["comments"] += comments
            d["n"] += 1
        for lo, hi, name in BANDS:
            if lo <= f.loc <= hi:
                b = band[(f.period, name)]
                b["kloc"] += f.loc / 1000
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
    attention_by_ai_table()
