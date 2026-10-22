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
window contributor weights, seeded bootstrap (analyze.bootstrap_ci, 2000
draws, one keyed stream per reported interval).

The *_rows() functions return the numbers (consumed by
scripts/plot_paper_tables.py); usage()/core() print the tables.

Usage:  python -m pipeline.studies.paper_tables --table {usage,core}
"""
from __future__ import annotations

import argparse
import statistics
from collections import defaultdict

from pipeline.analyze import bootstrap_ci, weighted_mean
from pipeline.frame import PERIODS, study_frame
from pipeline.studies.productivity import per_author
from pipeline.studies.slices import weights

MIN_PRS = 5
MIN_PRS_MONTH = 2    # the quarterly floor per unit time (METHODS §1c.4)


def _periods_kw(granularity: str,
                window: list[str] | None) -> tuple[dict, list[str], int]:
    """(study_frame kwargs, period list, repo PR floor) for a table's
    granularity. The monthly path runs over the baseline + window months
    with the per-month floor; the quarterly path is untouched defaults."""
    if granularity == "quarter":
        return {}, PERIODS, MIN_PRS
    from pipeline.studies.productivity import month_frame_kw
    kw = month_frame_kw(window)
    return kw, kw["periods"], MIN_PRS_MONTH


def _est(pairs: list[tuple[float, float]],
         key: str) -> tuple[float, float, float]:
    """(weighted mean, ci_lo, ci_hi). `key` names the CI cell so its draw
    stream is independent of every other CI in the run (analyze.bootstrap_ci)."""
    return (weighted_mean(pairs), *bootstrap_ci(pairs, key=key))


def _fmt(est: tuple[float, float, float], pct: bool = True) -> str:
    m, lo, hi = est
    return (f"{m * 100:5.1f}% [{lo * 100:4.1f},{hi * 100:4.1f}]" if pct
            else f"{m:6.2f} [{lo:5.2f},{hi:5.2f}]")


def usage_rows(granularity: str = "quarter",
               window: list[str] | None = None) -> list[dict]:
    """Figure 2 rows: per period {period, repos, sub_pr, mrg_pr, sub_loc,
    mrg_loc} — each estimate a (mean, lo, hi) tuple of shares in [0,1].
    granularity="month": monthly rows over the baseline + window months,
    per-month repo floor (MIN_PRS_MONTH)."""
    frame_kw, periods, floor = _periods_kw(granularity, window)
    w = weights()
    # (repo, per) -> [prs, ai_prs, mrg_prs, ai_mrg_prs, loc, ai_loc,
    #                 mrg_loc, ai_mrg_loc]
    acc: dict = defaultdict(lambda: [0, 0, 0, 0, 0, 0, 0, 0])
    for f in study_frame("all", **frame_kw):   # population table: bot PRs count
        row = acc[(f.repo, f.period)]
        ai = f.cls.ai_involved
        row[0] += 1
        row[4] += f.loc
        if ai:
            row[1] += 1
            row[5] += f.loc
        # merged columns are outcome-conditioned: mature PRs only
        # (frozen rule 1d.1; external review P1)
        if f.cls.merged and f.cls.w8_mature:
            row[2] += 1
            row[6] += f.loc
            if ai:
                row[3] += 1
                row[7] += f.loc
    rows = []
    for per in periods:
        sub_pr, mrg_pr, sub_loc, mrg_loc = [], [], [], []
        for (repo, p), r in acc.items():
            if p != per or r[0] < floor:
                continue
            wt = w.get(repo, 1.0)
            sub_pr.append((r[1] / r[0], wt))
            if r[4] > 0:
                sub_loc.append((r[5] / r[4], wt))
            if r[2] >= floor:
                mrg_pr.append((r[3] / r[2], wt))
                if r[6] > 0:
                    mrg_loc.append((r[7] / r[6], wt))
        rows.append({"period": per, "repos": len(sub_pr),
                     "sub_pr": _est(sub_pr, f"usage|{per}|sub_pr"),
                     "mrg_pr": _est(mrg_pr, f"usage|{per}|mrg_pr"),
                     "sub_loc": _est(sub_loc, f"usage|{per}|sub_loc"),
                     "mrg_loc": _est(mrg_loc, f"usage|{per}|mrg_loc")})
    return rows


def core_rows(stat: str = "mean", granularity: str = "quarter",
              window: list[str] | None = None) -> list[dict]:
    """Figure 3 rows: per period {period, repos, kloc, sub_kloc (each an
    (estimate, lo, hi) tuple), mult, sub_mult} — merged (w8) and submitted
    kLOC per core author, CW. Submitted has no censoring.

    granularity="month": monthly rows over the baseline + window months.
    The >=2-insider-authors core gate is an author-count rule per period,
    not a PR-per-time floor, so it applies unchanged. Monthly rows carry
    NO mult/sub_mult: a single noisy baseline month is not the frozen
    Q1-2024 baseline estimate, so a per-month multiple would misstate
    growth.

    `stat` selects the STAGE-1 statistic over a repo's core authors; the
    contributor-weighted stage across repos is unchanged either way.
    Per-contributor output is heavy-tailed, so levels are quoted from the
    median (METHODS §1d.4b) while the growth MULTIPLE is robust to the
    choice — ×2.95 mean vs ×2.92 median — and the levels are not (19.0 vs
    10.0 kLOC/author in Q2-2026)."""
    if stat not in ("mean", "median"):
        raise ValueError(f"unknown stat: {stat!r} (mean|median)")
    mid = statistics.median if stat == "median" else \
        (lambda xs: sum(xs) / len(xs))
    frame_kw, periods, _floor = _periods_kw(granularity, window)
    pa = per_author(granularity, window)
    w = weights()
    ins_of = defaultdict(set)
    for f in study_frame("all", **frame_kw):
        if f.author and f.insider:
            ins_of[(f.repo, f.period)].add(f.author)
    rows = []
    base = sub_base = None
    for per in periods:
        pairs, sub_pairs = [], []
        for (repo, p), authors in pa.items():
            if p != per:
                continue
            core_a = {login: v for login, v in authors.items()
                      if login in ins_of[(repo, p)]}
            if len(core_a) >= 2:
                wt = w.get(repo, 1.0)
                pairs.append((mid([v[2] for v in core_a.values()])
                              / 1000, wt))
                sub_pairs.append((mid([v[4] for v in core_a.values()])
                                  / 1000, wt))
        est = _est(pairs, f"core|{per}|kloc")
        sub_est = _est(sub_pairs, f"core|{per}|sub_kloc")
        row = {"period": per, "repos": len(pairs), "kloc": est,
               "sub_kloc": sub_est}
        if granularity == "quarter":
            base = base if base is not None else est[0]
            sub_base = sub_base if sub_base is not None else sub_est[0]
            row["mult"] = est[0] / base
            row["sub_mult"] = sub_est[0] / sub_base
        rows.append(row)
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


def core_caption() -> str:
    """Figure 3's method line. The Q2 caveat is DERIVED from the data
    stamp, so regenerating after the finalization re-pull drops it."""
    from pipeline import detect
    q2 = "" if detect.w8_closed(detect.CUTOFF) else " (Q2 provisional)"
    return (f"contributor-weighted repo means, bootstrap 95% CI; merged = "
            f"w8 rule{q2}; core = insider PR authors; repos with "
            f">=2 insider authors")


def core() -> None:
    print("Figure 3: Submitted and merged LOC per core contributor over time")
    print(core_caption())
    print(f"{'period':9}{'repos':>6}{'CW submitted kLOC/author':>28}"
          f"{'x base':>8}{'CW merged kLOC/author':>26}{'x base':>8}")
    for r in core_rows():
        print(f"{r['period']:9}{r['repos']:>6}  "
              f"{_fmt(r['sub_kloc'], pct=False):>26}{r['sub_mult']:>7.2f}x"
              f"  {_fmt(r['kloc'], pct=False):>24}{r['mult']:>7.2f}x")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=["usage", "core"], required=True)
    a = ap.parse_args()
    usage() if a.table == "usage" else core()
