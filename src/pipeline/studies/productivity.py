"""Study: is contributor output changing, or just contributor counts?

Three nested cuts, each killing one confound (results discussed in
results.md; PR counts and LOC are OUTPUT VOLUME PROXIES, not value):

1. decomposition: PRs = authors x PRs/author, on the balanced repo panel
   (same repos in all quarters) — separates team growth from per-person
   output. Author = distinct human PR author in the repo-quarter.
2. cohorts: incumbent (active in Q1-2024) vs newcomer per-author output —
   NOTE the incumbent series is survivor-selected; use cut 3 for
   same-person claims.
3. persistent: same person, same repo, active at both endpoints
   (Q1-2024 and Q2-2026); their own then-vs-now output, split by whether
   they authored any AI-involved PR in 2026. Selection caveat: adopters
   were already ~2x heavier contributors in 2024 — the split is
   descriptive, not causal.

Usage:  python -m pipeline.studies.productivity --cut {decomposition,persistent}
"""
from __future__ import annotations

import argparse
import statistics
from collections import defaultdict

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import MARKERS, classify_pr, is_bot_login
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.slices import population_repos

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
LINE_CAP = 20_000        # per-PR cap so one vendored monster can't dominate
# VOLUME ESTIMAND NOTE (documented provisional treatment, external review
# P1): merged-LOC sums here count every w8 merge OBSERVED so far,
# including merges of not-yet-mature PRs — immature PRs that will merge
# later are missing, so trailing-quarter volume is DEFLATED (conservative
# for all growth claims) and finalizes with the AS_OF re-pulls. This
# differs from rate metrics, which are None-gated on maturity.


def per_author() -> dict:
    """(repo, period) -> login -> [prs, merged, merged_lines, ai_prs]."""
    keep = population_repos()
    out: dict = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot" or not a.get("login") \
                    or is_bot_login(a["login"]):
                continue
            c = classify_pr(p, MARKERS)
            row = out[(repo, per)][a["login"]]
            row[0] += 1
            if c.ai_involved:
                row[3] += 1
            if c.merged:
                row[1] += 1
                row[2] += min((p.get("additions") or 0)
                              + (p.get("deletions") or 0), LINE_CAP)
    return out


def decomposition() -> None:
    pa = per_author()
    panel = {r for r in {r for (r, _) in pa}
             if all((r, p) in pa for p in PERIODS)}
    print(f"balanced repo panel: {len(panel)} repos (pooled)")
    print(f"{'period':9}{'PRs':>8}{'authors':>9}{'PRs/auth':>9}"
          f"{'merged/auth':>12}{'klines/auth':>12}")
    for per in PERIODS:
        N = A = M = L = 0
        for r in panel:
            for n, m, ln, _ in pa[(r, per)].values():
                A += 1
                N += n
                M += m
                L += ln
        print(f"{per:9}{N:>8}{A:>9}{N/A:>9.2f}{M/A:>12.2f}{L/A/1000:>12.2f}")


def persistent() -> None:
    pa = per_author()
    pairs = []
    for (repo, per) in list(pa):
        if per != "Q1-2024" or (repo, "Q2-2026") not in pa:
            continue
        for login, v24 in pa[(repo, "Q1-2024")].items():
            v26 = pa[(repo, "Q2-2026")].get(login)
            if v26:
                pairs.append((v24, v26))
    print(f"persistent same-repo authors (active Q1-2024 AND Q2-2026): {len(pairs)}")
    for label, idx in (("PRs/quarter", 0), ("merged/quarter", 1)):
        a24 = [p[0][idx] for p in pairs]
        a26 = [p[1][idx] for p in pairs]
        print(f"  {label:22} 2024 mean {statistics.mean(a24):6.2f} "
              f"median {statistics.median(a24):4.1f} | 2026 mean "
              f"{statistics.mean(a26):6.2f} median {statistics.median(a26):4.1f}")
    for label, grp in (("AI-using in 2026", [p for p in pairs if p[1][3] > 0]),
                       ("non-AI in 2026", [p for p in pairs if p[1][3] == 0])):
        if not grp:
            continue
        m24 = statistics.mean(p[0][1] for p in grp)
        m26 = statistics.mean(p[1][1] for p in grp)
        l24 = statistics.mean(p[0][2] for p in grp) / 1000
        l26 = statistics.mean(p[1][2] for p in grp) / 1000
        print(f"  {label:22} n={len(grp):5}  merged/q {m24:.2f}->{m26:.2f} "
              f"({m26 / m24:.2f}x)  klines/q {l24:.2f}->{l26:.2f} "
              f"({l26 / l24:.2f}x)")
    print("  (adopter selection caveat: AI-users were already ~2x heavier "
          "contributors in 2024; descriptive, not causal)")


def core_loc() -> None:
    """Paper point 1: merged LOC per CORE (insider) contributor, per-repo
    contributor-weighted; externals excluded from both numerator and
    denominator (their influx dilutes pooled averages)."""
    from pipeline.analyze import weighted_mean
    from pipeline.studies.slices import weights
    pa = per_author()
    w = weights()
    from pipeline.analyze import group_by_period, load_cells
    from pipeline.scan_orgs import QUARTER_RANGES
    ins_of = defaultdict(set)
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        for p in prs:
            a = p.get("author") or {}
            if a.get("login") and p.get("authorAssociation") in                     ("MEMBER", "OWNER", "COLLABORATOR"):
                ins_of[(repo, per)].add(a["login"])
    print(f"{'period':9}{'repos':>6}{'CW merged kLOC / core author':>30}")
    for per in PERIODS:
        pairs = []
        for (repo, p), authors in pa.items():
            if p != per:
                continue
            core = {login: v for login, v in authors.items()
                    if login in ins_of[(repo, p)]}
            if len(core) >= 2:
                mrg = sum(v[2] for v in core.values())
                pairs.append((mrg / len(core), w.get(repo, 1.0)))
        if pairs:
            print(f"{per:9}{len(pairs):>6}{weighted_mean(pairs)/1000:>30.2f}")


def merged_channel(c) -> str | None:
    """Approval channel of a merged PR, or None when not merged OR not yet
    w8-mature — channel shares depend on review/self-merge flags that are
    provisional until maturity and can move in EITHER direction (round-5
    review P1), unlike the one-sided volume deflation documented above."""
    if not (c.merged and c.w8_mature):
        return None
    if c.human_reviewed:
        return "humanRev"
    if c.ai_reviewed or c.other_bot_reviewed:
        return "botOnly"
    if c.self_merged is True:
        return "selfUnrev"
    if c.self_merged is False:
        return "otherUnrev"
    return "unknown"


def channels() -> None:
    """Paper points 2 & 5: merged LOC by approval channel (human-reviewed /
    bot-only-reviewed / self-merged unreviewed / other-merged unreviewed),
    pooled shares per quarter."""
    from pipeline.analyze import group_by_period, load_cells
    from pipeline.scan_orgs import QUARTER_RANGES
    from pipeline.studies.slices import population_repos
    keep = population_repos()
    ch = defaultdict(lambda: defaultdict(int))
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        for p in prs:
            if (p.get("author") or {}).get("__typename") == "Bot":
                continue
            c = classify_pr(p, MARKERS)
            k = merged_channel(c)
            if k is None:
                continue
            loc = min((p.get("additions") or 0) + (p.get("deletions") or 0),
                      LINE_CAP)
            ch[per][k] += loc
            ch[per]["total"] += loc
    print(f"{'period':9}{'merged MLOC':>12}{'humanRev%':>10}{'botOnly%':>9}"
          f"{'selfUnrev%':>11}{'otherUnrev%':>12}")
    for per in PERIODS:
        d = ch[per]
        t = d["total"] or 1
        print(f"{per:9}{t/1e6:>12.1f}{100*d['humanRev']/t:>9.1f}%"
              f"{100*d['botOnly']/t:>8.1f}%{100*d['selfUnrev']/t:>10.1f}%"
              f"{100*d['otherUnrev']/t:>11.1f}%")


def ai_split() -> None:
    """Core-contributor merged (w8) LOC split by AI involvement, CW with
    bootstrap 95% CIs. Three columns per quarter, core (insider) authors
    only, repos with >=2 core authors (same rule as --cut core):

    - noAI-author kLOC: merged kLOC per core author, restricted to authors
      with ZERO AI-tracked PRs (submitted or merged) in the repo-quarter —
      the non-adopter output level.
    - AI-user AI-PR kLOC: merged LOC arriving in AI-tracked PRs, per
      AI-USING core author (authors with >=1 AI-tracked PR in the
      repo-quarter).
    - AI-user nonAI-PR kLOC: merged LOC in the AI users' NON-AI-tracked
      PRs, per AI-using author. The last two sum to total merged kLOC per
      AI-using author; non-adopters' LOC never enters either.

    Repos need >=2 core authors; the AI-user columns additionally need >=1
    AI-using core author in the repo-quarter. Detection is a floor, so the
    split is conservative: undetected AI LOC lands in the nonAI columns."""
    from pipeline.analyze import bootstrap_ci, weighted_mean
    from pipeline.studies.slices import population_repos, weights
    keep = population_repos()
    w = weights()
    # (repo, per) -> login -> [ai_merged_loc, nonai_merged_loc, ai_prs]
    acc: dict = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    ins_of = defaultdict(set)
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot" or not a.get("login") \
                    or is_bot_login(a["login"]):
                continue
            if p.get("authorAssociation") in ("MEMBER", "OWNER",
                                              "COLLABORATOR"):
                ins_of[(repo, per)].add(a["login"])
            c = classify_pr(p, MARKERS)
            row = acc[(repo, per)][a["login"]]
            if c.ai_involved:
                row[2] += 1
            if c.merged:
                loc = min((p.get("additions") or 0)
                          + (p.get("deletions") or 0), LINE_CAP)
                row[0 if c.ai_involved else 1] += loc

    def fmt(pairs):
        if not pairs:
            return "     (no AI users)"
        m = weighted_mean(pairs)
        lo, hi = bootstrap_ci(pairs)
        return f"{m:6.2f} [{lo:5.2f},{hi:5.2f}]"

    print("core-contributor merged (w8) kLOC split by AI involvement "
          "(CW, bootstrap 95% CI; floors: undetected AI counts as nonAI)")
    print("AI-user columns are per AI-USING core author and sum to their "
          "total; noAI-author LOC never enters them")
    print(f"{'period':9}{'repos':>6}{'AI-user repos':>14}"
          f"{'noAI-author kLOC':>22}{'AI-user AI-PR kLOC':>22}"
          f"{'AI-user nonAI-PR kLOC':>23}")
    for per in PERIODS:
        pa_, pb, pc = [], [], []
        for (repo, p), authors in acc.items():
            if p != per:
                continue
            core = {login: v for login, v in authors.items()
                    if login in ins_of[(repo, p)]}
            if len(core) < 2:
                continue
            wt = w.get(repo, 1.0)
            noai = [v for v in core.values() if v[2] == 0]
            if noai:
                pa_.append((sum(v[0] + v[1] for v in noai)
                            / len(noai) / 1000, wt))
            ai_users = [v for v in core.values() if v[2] > 0]
            if ai_users:
                n = len(ai_users)
                pb.append((sum(v[0] for v in ai_users) / n / 1000, wt))
                pc.append((sum(v[1] for v in ai_users) / n / 1000, wt))
        print(f"{per:9}{len(pa_):>6}{len(pb):>14}  {fmt(pa_):>20}"
              f"  {fmt(pb):>20}  {fmt(pc):>21}")


ADOPTION_COHORTS = [
    ("fleet", "fleet operators: >=300 merged PRs in some quarter "
              "(assigned before the AI-timing cohorts)"),
    ("early", "early adopters: first PR with AI evidence by end of "
              "2026-02"),
    ("medium", "middle adopters: first AI evidence 2026-03..2026-04"),
    ("late", "late adopters: first AI evidence 2026-05 or later"),
    ("never", "non-adopters: no PR with AI evidence in the study period"),
]
FLEET_MIN = 300   # merged PRs in a single quarter; ~0.3% of core authors


def adoption_rows() -> dict:
    """Fixed adoption cohorts of CORE authors, tracked in calendar time.

    Cohort = author's FIRST month with an AI-tracked PR (submitted, any
    repo): early (<= 2026-02), medium (2026-03..04), late (>= 2026-05),
    never — EXCEPT authors with >= FLEET_MIN merged PRs in any single
    quarter, who form the separate FLEET cohort regardless of AI timing
    (agent-fleet / automation operators: a 45%-of-cell-LOC whale audit,
    then a population sweep, found ~43 such accounts merging 300-4,400
    PRs/quarter, roughly half with no AI markers — isolating them replaces
    top-1% trimming). Core = insider association on >=1 censused PR in any
    period.
    Per quarter x cohort, over cohort members ACTIVE that quarter (>=1 PR):
    author-level (pooled, unweighted) mean merged (w8) kLOC in AI-tracked
    PRs, in non-AI PRs, and their sum, with a seeded bootstrap 95% CI,
    MEDIAN, and top-1%-trimmed mean of the sum. Means are whale-sensitive:
    a top-5 author audit of the medium/Q2-2026 cell found 45% of cohort
    LOC from five agent-fleet accounts (thousands of merged PRs/quarter
    each, partly unmarked) — quote medians or trimmed means for
    typical-contributor claims. Caveats: Q2-2026 merged LOC is
    w8-deflated for May/June PRs
    (hits late adopters hardest); late adopters' pre-Q2 rows are clean
    pre-adoption output; detection floors put undetected AI in nonAI.

    Returns {(period, cohort): {n, ai, nonai, total, lo, hi}}."""
    from pipeline.analyze import bootstrap_ci, weighted_mean
    acc, per_author_cohort, q_of = _author_months_and_cohorts()
    out = {}
    for per in PERIODS:
        mons = [m for m, q in q_of.items() if q == per]
        for coh, _desc in ADOPTION_COHORTS:
            ai_v, nonai_v = [], []
            for login, coh_ in per_author_cohort.items():
                if coh_ != coh:
                    continue
                rows = [acc[login][m] for m in mons if m in acc[login]]
                if not any(r[3] for r in rows):
                    continue                       # inactive this quarter
                ai_v.append(sum(r[0] for r in rows))
                nonai_v.append(sum(r[1] for r in rows))
            tot = [(a + b, 1.0) for a, b in zip(ai_v, nonai_v)]
            if not tot:
                out[(per, coh)] = None
                continue
            lo, hi = bootstrap_ci(tot)
            out[(per, coh)] = {
                "n": len(tot),
                "ai": sum(ai_v) / len(ai_v),
                "nonai": sum(nonai_v) / len(nonai_v),
                "total": weighted_mean(tot), "lo": lo, "hi": hi,
                "median": statistics.median(t for t, _ in tot)}
    return out


def _author_months_and_cohorts():
    """Shared builder: per-author monthly activity, cohort assignment, and
    the month->quarter map. Used by adoption_rows (quarterly table) and
    adoption_monthly (Figure 4 series)."""
    keep = population_repos()
    q_of = {}
    for m in range(1, 4):
        q_of[f"2024-{m:02d}"] = "Q1-2024"
        q_of[f"2026-{m:02d}"] = "Q1-2026"
        q_of[f"2026-{m + 3:02d}"] = "Q2-2026"
    for m in (10, 11, 12):
        q_of[f"2025-{m}"] = "Q4-2025"
    # login -> month -> [ai_kloc, nonai_kloc, ai_prs, prs, mrg_prs,
    #                     submitted_kloc]
    acc: dict = defaultdict(
        lambda: defaultdict(lambda: [0.0, 0.0, 0, 0, 0, 0.0]))
    insiders = set()
    for (repo, mon), prs in group_by_period(load_cells(), QUARTER_RANGES,
                                            "month").items():
        if repo not in keep or mon not in q_of:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot" or not a.get("login") \
                    or is_bot_login(a["login"]):
                continue
            login = a["login"]
            if p.get("authorAssociation") in ("MEMBER", "OWNER",
                                              "COLLABORATOR"):
                insiders.add(login)
            c = classify_pr(p, MARKERS)
            row = acc[login][mon]
            row[3] += 1
            kloc = min((p.get("additions") or 0)
                       + (p.get("deletions") or 0), LINE_CAP) / 1000
            row[5] += kloc                       # submitted: no censoring
            if c.ai_involved:
                row[2] += 1
            if c.merged:
                row[4] += 1
                row[0 if c.ai_involved else 1] += kloc

    def cohort_of(months: dict) -> str:
        for per in PERIODS:
            mons = [m for m, q in q_of.items() if q == per]
            if sum(months.get(m, [0, 0, 0, 0, 0])[4] for m in mons) \
                    >= FLEET_MIN:
                return "fleet"
        first = min((m for m, v in months.items() if v[2] > 0),
                    default=None)
        if first is None:
            return "never"
        if first <= "2026-02":
            return "early"
        return "medium" if first <= "2026-04" else "late"

    per_author_cohort = {login: cohort_of(m) for login, m in acc.items()
                         if login in insiders}
    return acc, per_author_cohort, q_of


def adoption_monthly() -> dict:
    """(month, cohort) -> {n, submitted, merged} — mean kLOC per
    quarter-ACTIVE cohort member per MONTH (the Figure 4 series: submitted
    has no censoring; merged follows the w8 rule and is provisional on
    months not yet mature — see mature-month cap in the caption)."""
    acc, cohort_of_login, q_of = _author_months_and_cohorts()
    months = sorted(q_of)
    out = {}
    for mon in months:
        for coh, _d in ADOPTION_COHORTS:
            sub, mrg = [], []
            for login, coh_ in cohort_of_login.items():
                if coh_ != coh:
                    continue
                row = acc[login].get(mon)
                if not row or not row[3]:
                    continue                     # inactive this month
                sub.append(row[5])
                mrg.append(row[0] + row[1])
            if sub:
                out[(mon, coh)] = {
                    "n": len(sub),
                    "submitted": sum(sub) / len(sub),
                    "merged": sum(mrg) / len(mrg)}
    return out


def adoption() -> None:
    rows = adoption_rows()
    print("merged (w8) kLOC per CORE author by fixed adoption cohort "
          "(pooled author-level means over quarter-active members; "
          "bootstrap 95% CI on total)")
    for coh, desc in ADOPTION_COHORTS:
        print(f"  {coh}: {desc}")
    print("Q2-2026 w8-deflated for May/June PRs; undetected AI counts "
          "as nonAI (floors)")
    print(f"\n{'period':9}{'cohort':8}{'authors':>8}{'AI kLOC':>9}"
          f"{'nonAI kLOC':>11}{'total kLOC':>11}{'95% CI':>16}"
          f"{'median':>8}")
    for per in PERIODS:
        for coh, _ in ADOPTION_COHORTS:
            r = rows[(per, coh)]
            if r is None:
                print(f"{per:9}{coh:8}{'—':>8}")
                continue
            print(f"{per:9}{coh:8}{r['n']:>8}{r['ai']:>9.2f}"
                  f"{r['nonai']:>11.2f}{r['total']:>11.2f}"
                  f"   [{r['lo']:5.2f},{r['hi']:6.2f}]"
                  f"{r['median']:>8.2f}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", choices=["decomposition", "persistent",
                                      "core", "channels", "aisplit",
                                      "adoption"],
                    default="decomposition")
    a = ap.parse_args()
    {"decomposition": decomposition, "persistent": persistent,
     "core": core_loc, "channels": channels, "aisplit": ai_split,
     "adoption": adoption}[a.cut]()


if __name__ == "__main__":
    main()
