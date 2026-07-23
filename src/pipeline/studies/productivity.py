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

from pipeline.frame import PERIODS, study_frame
# VOLUME ESTIMAND NOTE (documented provisional treatment, external review
# P1): merged-LOC sums here count every w8 merge OBSERVED so far,
# including merges of not-yet-mature PRs — immature PRs that will merge
# later are missing, so trailing-quarter volume is DEFLATED (conservative
# for all growth claims) and finalizes with the AS_OF re-pulls. This
# differs from rate metrics, which are None-gated on maturity.


def per_author() -> dict:
    """(repo, period) -> login -> [prs, merged, merged_lines, ai_prs,
    submitted_lines]."""
    out: dict = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0, 0]))
    for f in study_frame("author"):
        row = out[(f.repo, f.period)][f.author]
        row[0] += 1
        row[4] += f.loc                          # submitted: no censoring
        if f.cls.ai_involved:
            row[3] += 1
        if f.cls.merged:
            row[1] += 1
            row[2] += f.loc
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
            for n, m, ln, *_ in pa[(r, per)].values():
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
    ins_of = defaultdict(set)
    for f in study_frame("all"):
        if f.author and f.insider:
            ins_of[(f.repo, f.period)].add(f.author)
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
    pooled shares per quarter. Profile 'author', aligned with review_mix
    (issue #2): a user-typed-bot pipeline's LOC is automation, not human
    approval behavior."""
    ch = defaultdict(lambda: defaultdict(int))
    for f in study_frame("author"):
        k = merged_channel(f.cls)
        if k is None:
            continue
        ch[f.period][k] += f.loc
        ch[f.period]["total"] += f.loc
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
    from pipeline.studies.slices import weights
    w = weights()
    # (repo, per) -> login -> [ai_merged_loc, nonai_merged_loc, ai_prs]
    acc: dict = defaultdict(lambda: defaultdict(lambda: [0, 0, 0]))
    ins_of = defaultdict(set)
    for f in study_frame("author"):
        if f.insider:
            ins_of[(f.repo, f.period)].add(f.author)
        row = acc[(f.repo, f.period)][f.author]
        if f.cls.ai_involved:
            row[2] += 1
        if f.cls.merged:
            row[0 if f.cls.ai_involved else 1] += f.loc

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
    acc, per_author_cohort, q_of, _fleet = _author_months_and_cohorts()
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
    q_of = {}
    for m in range(1, 4):
        q_of[f"2024-{m:02d}"] = "Q1-2024"
        q_of[f"2026-{m:02d}"] = "Q1-2026"
        q_of[f"2026-{m + 3:02d}"] = "Q2-2026"
    for m in (10, 11, 12):
        q_of[f"2025-{m}"] = "Q4-2025"
    # login -> month -> [ai_mrg_kloc, nonai_mrg_kloc, ai_prs, prs,
    #                     mrg_prs, submitted_kloc, ai_submitted_kloc]
    acc: dict = defaultdict(
        lambda: defaultdict(lambda: [0.0, 0.0, 0, 0, 0, 0.0, 0.0]))
    insiders = set()
    for f in study_frame("author", periods=q_of, granularity="month"):
        if f.insider:
            insiders.add(f.author)
        row = acc[f.author][f.period]
        row[3] += 1
        kloc = f.loc / 1000
        row[5] += kloc                           # submitted: no censoring
        if f.cls.ai_involved:
            row[2] += 1
            row[6] += kloc                       # AI-involved submitted
        if f.cls.merged:
            row[4] += 1
            row[0 if f.cls.ai_involved else 1] += kloc

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
    fleet_all = set()
    for login, months in acc.items():
        for per in PERIODS:
            mons = [m for m, q in q_of.items() if q == per]
            if sum(months.get(m, [0, 0, 0, 0, 0])[4] for m in mons) \
                    >= FLEET_MIN:
                fleet_all.add(login)
                break
    return acc, per_author_cohort, q_of, fleet_all


def adoption_monthly() -> dict:
    """(month, cohort) -> {n, submitted, sub_ai, sub_nonai, merged,
    mrg_ai, mrg_nonai} — mean kLOC per
    quarter-ACTIVE cohort member per MONTH (the Figure 4 series: submitted
    has no censoring; merged follows the w8 rule and is provisional on
    months not yet mature — see mature-month cap in the caption)."""
    acc, cohort_of_login, q_of, _fleet = _author_months_and_cohorts()
    months = sorted(q_of)
    out = {}
    for mon in months:
        for coh, _d in ADOPTION_COHORTS:
            rows = [acc[login][mon] for login, coh_ in
                    cohort_of_login.items()
                    if coh_ == coh and acc[login].get(mon)
                    and acc[login][mon][3]]
            if not rows:
                continue
            n = len(rows)
            out[(mon, coh)] = {
                "n": n,
                "submitted": sum(r[5] for r in rows) / n,
                "sub_ai": sum(r[6] for r in rows) / n,
                "sub_nonai": sum(r[5] - r[6] for r in rows) / n,
                "merged": sum(r[0] + r[1] for r in rows) / n,
                "mrg_ai": sum(r[0] for r in rows) / n,
                "mrg_nonai": sum(r[1] for r in rows) / n}
    return out


WINDOW_MONTHS = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02",
                 "2026-03", "2026-04", "2026-05", "2026-06"]


def month_w8_mature(mon: str) -> bool:
    """Every PR created in `mon` closed its 56-day window by the AS_OF."""
    from calendar import monthrange
    from datetime import datetime, timedelta
    from pipeline import detect
    as_of = datetime.fromisoformat(detect.AS_OF.replace("Z", "+00:00"))
    y, m = int(mon[:4]), int(mon[5:7])
    end = datetime(y, m, monthrange(y, m)[1], 23, 59, tzinfo=as_of.tzinfo)
    return end + timedelta(days=56) <= as_of


def adoption_event(max_off: int = 2, balanced: bool = True) -> dict:
    """Figure 5: the Figure 4 metrics in EVENT TIME, net of non-adopters,
    as a BALANCED PANEL.

    Each aligned author (cohort member with a first observed AI month t0
    in the window) contributes, at offset e in [-max_off..max_off], their
    month-(t0+e) values MINUS the contemporaneous NON-ADOPTER cohort mean
    for the same calendar month (difference-in-differences: secular and
    seasonal drift cancel; AI metrics are net-zero-baseline by
    construction since non-adopters have none). Inactive months count as
    zero volume, matching the event study. Offsets outside the observed
    window are skipped (unbalanced panel; n reported per offset).

    Returns {(cohort, e): {n, submitted, sub_ai, sub_nonai, merged,
    mrg_ai, mrg_nonai}} for the adopting cohorts + fleet (aligned
    members only)."""
    acc, cohort_of_login, q_of, _fleet = _author_months_and_cohorts()
    zero = [0.0, 0.0, 0, 0, 0, 0.0, 0.0]

    def metrics(row):
        return {"submitted": row[5], "sub_ai": row[6],
                "sub_nonai": row[5] - row[6],
                "merged": row[0] + row[1], "mrg_ai": row[0],
                "mrg_nonai": row[1]}

    # non-adopter mean per calendar month (the subtracted baseline) —
    # ZERO-INCLUSIVE over all non-adopter members, matching the adopter
    # side (inactive month = zero volume on BOTH sides of the difference;
    # an active-only baseline would bias pre-periods negative)
    never = [login for login, c in cohort_of_login.items() if c == "never"]
    base = {}
    for mon in WINDOW_MONTHS:
        ms = [metrics(acc[login].get(mon) or zero) for login in never] \
            or [metrics(zero)]
        base[mon] = {k: sum(m[k] for m in ms) / len(ms) for k in ms[0]}

    out = {}
    for coh in ("fleet", "early", "medium", "late"):
        aligned = {}
        for login, c in cohort_of_login.items():
            if c != coh:
                continue
            t0 = next((i for i, m in enumerate(WINDOW_MONTHS)
                       if acc[login].get(m, zero)[2] > 0), None)
            if t0 is None:
                continue
            if balanced and not (max_off <= t0
                                 < len(WINDOW_MONTHS) - max_off):
                continue                 # full [-2..+2] must be observable
            aligned[login] = t0
        for e in range(-max_off, max_off + 1):
            diffs = []
            immature = 0
            for login, t0 in aligned.items():
                i = t0 + e
                if not 0 <= i < len(WINDOW_MONTHS):
                    continue
                mon = WINDOW_MONTHS[i]
                if not month_w8_mature(mon):
                    immature += 1
                m = metrics(acc[login].get(mon) or zero)
                diffs.append({k: m[k] - base[mon][k] for k in m})
            if diffs:
                out[(coh, e)] = {"n": len(diffs),
                                 "immature_share": immature / len(diffs),
                                 **{k: sum(d[k] for d in diffs) / len(diffs)
                                    for k in diffs[0]}}
    return out


def event_by_adoption_month(max_off: int = 2) -> dict:
    """Figure 4: per-author kLOC (six metrics: submitted/merged x
    total/AI/non-AI) at offsets [-2..+2] around first observed AI use,
    one BALANCED cohort per ADOPTION MONTH (2025-12..2026-04 — exactly
    the months whose full window fits the data). Non-fleet adopters only;
    inactive months count as zero volume. Within a cohort each offset
    maps to ONE calendar month, so w8 maturity per offset is exact.

    Returns {t0_month: {"n": int, "offsets": {e: {six metrics,
    "month": str, "mature": bool}}}}."""
    acc, cohort_of_login, _q_of, _fleet = _author_months_and_cohorts()
    zero = [0.0, 0.0, 0, 0, 0, 0.0, 0.0]

    def metrics(row):
        return {"submitted": row[5], "sub_ai": row[6],
                "sub_nonai": row[5] - row[6],
                "merged": row[0] + row[1], "mrg_ai": row[0],
                "mrg_nonai": row[1]}

    by_t0: dict = defaultdict(list)
    for login, coh in cohort_of_login.items():
        if coh in ("never", "fleet"):    # fleet: 10-100x scale, Figure 5
            continue
        t0 = next((i for i, m in enumerate(WINDOW_MONTHS)
                   if acc[login].get(m, zero)[2] > 0), None)
        if t0 is not None and max_off <= t0 < len(WINDOW_MONTHS) - max_off:
            by_t0[t0].append(login)
    out = {}
    for t0, members in sorted(by_t0.items()):
        offsets = {}
        for e in range(-max_off, max_off + 1):
            mon = WINDOW_MONTHS[t0 + e]
            vals = [metrics(acc[login].get(mon) or zero)
                    for login in members]
            offsets[e] = {"month": mon, "mature": month_w8_mature(mon),
                          **{k: sum(v[k] for v in vals) / len(vals)
                             for k in vals[0]}}
        out[WINDOW_MONTHS[t0]] = {"n": len(members), "offsets": offsets}
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


FLEET_LOGINS_FILE = "data/derived/fleet_logins.txt"


def fleet_logins() -> set[str]:
    """ALL authors (insider or not) with >= FLEET_MIN merged PRs in some
    study quarter — the exclusion set for review-behavior figures 6-8
    (fleet pipelines distort review statistics the way they distort
    per-contributor means). Persisted to data/derived/fleet_logins.txt
    (reproducible from cells; computed and written when absent)."""
    from pathlib import Path
    p = Path(FLEET_LOGINS_FILE)
    if p.is_file():
        return {ln.strip() for ln in p.read_text().splitlines()
                if ln.strip()}
    *_rest, fleet = _author_months_and_cohorts()
    p.write_text("\n".join(sorted(fleet)) + "\n")
    return fleet


def review_mix(by: str = "role", exclude_fleet: bool = True,
               fleet_slice: bool = False) -> dict:
    """Figure 6: review mix of MERGED PRs, insider vs external, per
    quarter — the substitution hypothesis (human review declining, AI/bot
    review rising). For each (period, slice in {ins, ext}): share of
    mature merged PRs (and of their capped LOC) in each approval channel
    (humanRev = reviewer!=author human review; botOnly = AI/CI bot review
    only; selfUnrev / otherUnrev = merged with no review at all).
    Mature-gated like all outcome metrics: Q2-2026 reflects PRs created
    early enough to close their w8 window (finalizes with AS_OF
    re-pulls). Pooled shares (repo-size weighted by construction).

    by="role": slices {ins, ext} (author association), profile 'author' —
    a Bot's NONE association must not pollute the external slice.
    by="ai": slices {ai, nonai} (PR-level AI involvement — the Figure 6
    alternative), profile 'all' per issue #2: agent-authored (layer-B)
    PRs belong in the ai slice; the ai slice is empty at the Q1-2024
    baseline by construction.
    exclude_fleet (default): PRs authored by fleet operators are dropped.
    fleet_slice=True: fleet-authored PRs become their OWN slice ("fleet")
    instead of being dropped (Figure 3 companion).

    Returns {(period, slice): {n, loc, <ch>_pr, <ch>_loc ...}}."""
    fleet = fleet_logins() if (exclude_fleet or fleet_slice) else set()
    agg: dict = defaultdict(lambda: defaultdict(float))
    for f in study_frame("all" if by == "ai" else "author"):
        is_fleet = f.author in fleet
        if is_fleet and not fleet_slice:
            continue
        ch = merged_channel(f.cls)
        if ch is None:
            continue                 # unmerged or w8-immature
        if is_fleet:
            sl = "fleet"
        else:
            sl = ("ai" if f.cls.ai_involved else "nonai") if by == "ai" \
                else ("ins" if f.cls.insider else "ext")
        d = agg[(f.period, sl)]
        d["n"] += 1
        d["loc"] += f.loc
        d[f"{ch}_pr"] += 1
        d[f"{ch}_loc"] += f.loc
    out = {}
    for key, d in agg.items():
        row = {"n": int(d["n"]), "loc": d["loc"]}
        for ch in ("humanRev", "botOnly", "selfUnrev", "otherUnrev"):
            row[f"{ch}_pr"] = d[f"{ch}_pr"] / d["n"] if d["n"] else 0.0
            row[f"{ch}_loc"] = d[f"{ch}_loc"] / d["loc"] if d["loc"] else 0.0
        out[key] = row
    return out


def review_mix_table() -> None:
    print("review mix of MERGED PRs (mature-gated, pooled, FLEET-OPERATOR "
          "authors excluded): PR share / LOC share per approval channel")
    print("humanRev = reviewer!=author human review; botOnly = AI/CI bot "
          "only; selfUnrev/otherUnrev = merged unreviewed")
    for by, slices in (("role", ("ins", "ext")), ("ai", ("ai", "nonai"))):
        rows = review_mix(by)
        print(f"\n--- sliced by {'author role' if by == 'role' else 'PR AI involvement'} ---")
        print(f"{'period':9}{'slice':6}{'merged':>8}{'humanRev':>16}"
              f"{'botOnly':>16}{'selfUnrev':>16}{'otherUnrev':>16}")
        for per in PERIODS:
            for sl in slices:
                r = rows.get((per, sl))
                if not r:
                    continue
                cells = "".join(
                    f"  {100 * r[ch + '_pr']:5.1f}/{100 * r[ch + '_loc']:5.1f}%"
                    for ch in ("humanRev", "botOnly", "selfUnrev",
                               "otherUnrev"))
                print(f"{per:9}{sl:6}{r['n']:>8}{cells}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", choices=["decomposition", "persistent",
                                      "core", "channels", "aisplit",
                                      "adoption", "reviewmix"],
                    default="decomposition")
    a = ap.parse_args()
    {"decomposition": decomposition, "persistent": persistent,
     "core": core_loc, "channels": channels, "aisplit": ai_split,
     "adoption": adoption, "reviewmix": review_mix_table}[a.cut]()


if __name__ == "__main__":
    main()
