"""Paper figures 2 & 3 — headline tables in publication form.

Figure 2 (Traceable AI usage over time): per quarter, contributor-weighted
with bootstrap 95% CIs —
  - share of SUBMITTED PRs with traceable AI usage (ai_involved),
  - share of MERGED (w8) PRs with traceable AI usage,
  - share of SUBMITTED LOC coming from AI-involved PRs,
  - share of MERGED (w8) LOC coming from AI-involved PRs.
LOC = additions+deletions capped at 20k/PR. All four are floors (detection
is a lower bound; see METHODS §2). Q1-2024 is the detector-validity
baseline, 0% by construction.

Figure 3 (Merged LOC per core contributor): per quarter, CW mean of per-repo
merged (w8) kLOC per CORE (insider) PR author, bootstrap 95% CI, and the
multiple over the Q1-2024 baseline. Repos need >=2 insider authors in the
quarter (same rule as productivity --cut core). Q2-2026 is deflated by w8
right-censoring of May/June PRs (conservative for the growth multiple).

Aggregation follows the frozen conventions (METHODS §1d): repo floor >=5
PRs/quarter (merged-conditioned columns additionally >=5 merged PRs),
window contributor weights, seeded bootstrap (analyze._RNG, 2000 draws).

The *_rows() functions return the numbers (consumed by
scripts/plot_paper_tables.py); usage()/core() print the tables.

Usage:  python -m pipeline.studies.paper_tables --table {usage,core}
"""
from __future__ import annotations

import argparse
from collections import defaultdict

from pipeline.analyze import (bootstrap_ci, group_by_period, load_cells,
                              weighted_mean)
from pipeline.detect import MARKERS, classify_pr
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.productivity import LINE_CAP, PERIODS, per_author
from pipeline.studies.slices import population_repos, weights

MIN_PRS = 5


def _est(pairs: list[tuple[float, float]]) -> tuple[float, float, float]:
    """(weighted mean, ci_lo, ci_hi)."""
    return (weighted_mean(pairs), *bootstrap_ci(pairs))


def _fmt(est: tuple[float, float, float], pct: bool = True) -> str:
    m, lo, hi = est
    return (f"{m * 100:5.1f}% [{lo * 100:4.1f},{hi * 100:4.1f}]" if pct
            else f"{m:6.2f} [{lo:5.2f},{hi:5.2f}]")


def usage_rows() -> list[dict]:
    """Figure 2 rows: per period {period, repos, sub_pr, mrg_pr, sub_loc,
    mrg_loc} — each estimate a (mean, lo, hi) tuple of shares in [0,1]."""
    keep = population_repos()
    w = weights()
    # (repo, per) -> [prs, ai_prs, mrg_prs, ai_mrg_prs, loc, ai_loc,
    #                 mrg_loc, ai_mrg_loc]
    acc: dict = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0, 0])
    for (repo, per), prs in group_by_period(load_cells(),
                                            QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        row = acc[(repo, per)]
        for p in prs:
            c = classify_pr(p, MARKERS)
            loc = min((p.get("additions") or 0)
                      + (p.get("deletions") or 0), LINE_CAP)
            ai = c.ai_involved
            row[0] += 1
            row[4] += loc
            if ai:
                row[1] += 1
                row[5] += loc
            # merged columns are outcome-conditioned: mature PRs only
            # (frozen rule 1d.1; external review P1)
            if c.merged and c.w8_mature:
                row[2] += 1
                row[6] += loc
                if ai:
                    row[3] += 1
                    row[7] += loc
    rows = []
    for per in PERIODS:
        sub_pr, mrg_pr, sub_loc, mrg_loc = [], [], [], []
        for (repo, p), r in acc.items():
            if p != per or r[0] < MIN_PRS:
                continue
            wt = w.get(repo, 1.0)
            sub_pr.append((r[1] / r[0], wt))
            if r[4] > 0:
                sub_loc.append((r[5] / r[4], wt))
            if r[2] >= MIN_PRS:
                mrg_pr.append((r[3] / r[2], wt))
                if r[6] > 0:
                    mrg_loc.append((r[7] / r[6], wt))
        rows.append({"period": per, "repos": len(sub_pr),
                     "sub_pr": _est(sub_pr), "mrg_pr": _est(mrg_pr),
                     "sub_loc": _est(sub_loc), "mrg_loc": _est(mrg_loc)})
    return rows


def core_rows() -> list[dict]:
    """Figure 3 rows: per period {period, repos, kloc: (mean, lo, hi),
    mult} — kLOC merged (w8) per core author, CW."""
    pa = per_author()
    w = weights()
    ins_of = defaultdict(set)
    for (repo, per), prs in group_by_period(load_cells(),
                                            QUARTER_RANGES).items():
        for p in prs:
            a = p.get("author") or {}
            if a.get("login") and p.get("authorAssociation") in \
                    ("MEMBER", "OWNER", "COLLABORATOR"):
                ins_of[(repo, per)].add(a["login"])
    rows = []
    base = None
    for per in PERIODS:
        pairs = []
        for (repo, p), authors in pa.items():
            if p != per:
                continue
            core_a = {login: v for login, v in authors.items()
                      if login in ins_of[(repo, p)]}
            if len(core_a) >= 2:
                mrg = sum(v[2] for v in core_a.values())
                pairs.append((mrg / len(core_a) / 1000, w.get(repo, 1.0)))
        est = _est(pairs)
        base = base if base is not None else est[0]
        rows.append({"period": per, "repos": len(pairs), "kloc": est,
                     "mult": est[0] / base})
    return rows


def usage() -> None:
    print("Figure 2: Traceable AI usage over time")
    print("contributor-weighted repo means, bootstrap 95% CI; "
          "merged = w8 rule; LOC capped 20k/PR; all values are floors")
    print(f"{'period':9}{'repos':>6}{'AI% of submitted PRs':>22}"
          f"{'AI% of merged PRs':>21}{'AI-PR% of subm LOC':>21}"
          f"{'AI-PR% of merged LOC':>22}")
    for r in usage_rows():
        print(f"{r['period']:9}{r['repos']:>6}  {_fmt(r['sub_pr']):>20}"
              f"  {_fmt(r['mrg_pr']):>19}  {_fmt(r['sub_loc']):>19}"
              f"  {_fmt(r['mrg_loc']):>20}")


def core() -> None:
    print("Figure 3: Merged LOC per core contributor over time")
    print("contributor-weighted repo means, bootstrap 95% CI; merged = w8 "
          "rule; core = insider PR authors; repos with >=2 insider authors")
    print(f"{'period':9}{'repos':>6}{'CW merged kLOC/core author':>30}"
          f"{'x baseline':>12}")
    for r in core_rows():
        print(f"{r['period']:9}{r['repos']:>6}  "
              f"{_fmt(r['kloc'], pct=False):>28}{r['mult']:>11.2f}x")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=["usage", "core"], required=True)
    a = ap.parse_args()
    usage() if a.table == "usage" else core()
