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
from pipeline.detect import MARKERS_V2, classify_pr
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.slices import population_repos

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
LINE_CAP = 20_000        # per-PR cap so one vendored monster can't dominate


def per_author() -> dict:
    """(repo, period) -> login -> [prs, merged, merged_lines, ai_prs]."""
    keep = population_repos()
    out: dict = defaultdict(lambda: defaultdict(lambda: [0, 0, 0, 0]))
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot" or not a.get("login"):
                continue
            c = classify_pr(p, MARKERS_V2)
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
            c = classify_pr(p, MARKERS_V2)
            if not c.merged:
                continue
            loc = min((p.get("additions") or 0) + (p.get("deletions") or 0),
                      LINE_CAP)
            if c.human_reviewed:
                k = "humanRev"
            elif c.ai_reviewed or c.other_bot_reviewed:
                k = "botOnly"
            elif c.self_merged is True:
                k = "selfUnrev"
            elif c.self_merged is False:
                k = "otherUnrev"
            else:
                k = "unknown"
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


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cut", choices=["decomposition", "persistent",
                                      "core", "channels"],
                    default="decomposition")
    a = ap.parse_args()
    {"decomposition": decomposition, "persistent": persistent,
     "core": core_loc, "channels": channels}[a.cut]()


if __name__ == "__main__":
    main()
