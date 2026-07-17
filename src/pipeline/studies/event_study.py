"""Study: adoption event-study — volume in event time around first AI marker.

Each CORE author (insider in >=1 population repo in the month) is aligned to
their FIRST observed AI-marker month t0 (first censused month with an
AI-involved PR they authored, no earlier observed AI activity including the
2024 baseline months). MERGED kLOC/author/month (w8 rule: LOC of PRs created
in the month that merged within 8 weeks) is then read in EVENT TIME (months
relative to t0) over the continuous observation window (2025-10..2026-06).

Identification logic: if volume JUMPS at t0 rather than trending up before
it, trend-selection (heavier contributors were on steeper trajectories
anyway) is dead as an explanation for the adopter/non-adopter divergence.

Censoring rule: only w8-MATURE calendar months contribute observations —
2026-04 is the last month whose PRs all had a full 8-week window before the
cutoff (Apr 30 + 56d = Jun 25), so observations landing in 2026-05/06 are
EXCLUDED from every cell rather than reported deflated.

Composition control: alongside the all-observations table, a BALANCED cohort
(authors observed at every offset in [-2..+2]) removes entry/exit drift; its
FULLY-MATURE variant further requires t0 <= 2026-02 so every offset in
[-2..+2] falls in a mature month (no censoring anywhere in the panel).
Adoptions in the first observed month (2025-10) are excluded — no
pre-period; left-censored adopters (active in 2024 with AI already in
2025-10) cannot be aligned.

Usage:  python -m pipeline.studies.event_study
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean, median

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import MARKERS_V2, classify_pr
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.slices import population_repos

WINDOW = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
          "2026-04", "2026-05", "2026-06"]
BASELINE = ["2024-01", "2024-02", "2024-03"]
CAP = 20_000
# Last calendar month whose PRs all reached w8 maturity by the cutoff
# (2026-04-30 + 56d = 2026-06-25 <= 2026-06-30). Later months are excluded
# from the tables, not reported deflated.
MATURE_MAX = WINDOW.index("2026-04")


def author_months():
    """login -> month -> [merged_kloc, ai_pr_count, insider_any]."""
    keep = population_repos()
    out = defaultdict(lambda: defaultdict(lambda: [0.0, 0, False]))
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES,
                                            "month").items():
        if repo not in keep:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot" or not a.get("login"):
                continue
            c = classify_pr(p, MARKERS_V2)
            row = out[a["login"]][per]
            if c.merged:
                row[0] += min((p.get("additions") or 0)
                              + (p.get("deletions") or 0), CAP) / 1000
            if c.ai_involved:
                row[1] += 1
            if p.get("authorAssociation") in ("MEMBER", "OWNER",
                                              "COLLABORATOR"):
                row[2] = True
    return out


def main() -> None:
    am = author_months()
    events = {}
    for login, months in am.items():
        if not any(m[2] for m in months.values()):
            continue                                   # never core
        if any(months.get(b, [0, 0, 0])[1] for b in BASELINE):
            continue                                   # pre-window AI: cannot align
        first = next((i for i, m in enumerate(WINDOW)
                      if months.get(m, [0, 0, 0])[1] > 0), None)
        if first is not None and first > 0:            # need a pre-period
            events[login] = first
    print(f"alignable adopters (core, clean pre-period): {len(events)}")
    print("outcome = MERGED kLOC (w8) of PRs created in the month; "
          "months after 2026-04 (w8-immature) excluded from all cells")

    def table(cohort, label):
        print(f"\n{label}")
        print(f"{'event month':12}{'authors':>8}{'mean kLOC/mo':>13}{'median':>8}")
        for e in range(-4, 5):
            vals = []
            for login, t0 in cohort.items():
                idx = t0 + e
                if 0 <= idx <= MATURE_MAX:
                    vals.append(am[login].get(WINDOW[idx], [0, 0, 0])[0])
            if len(vals) >= 30:
                print(f"{('t' + format(e, '+d')):12}{len(vals):>8}"
                      f"{mean(vals):>13.2f}{median(vals):>8.2f}")

    table(events, "ALL alignable adopters (unbalanced event panel)")
    balanced = {login: t0 for login, t0 in events.items()
                if 2 <= t0 <= MATURE_MAX}
    table(balanced, "BALANCED cohort (observed at every offset in [-2..+2]; "
                    "post-t0 offsets past 2026-04 excluded)")
    mature = {login: t0 for login, t0 in events.items()
              if 2 <= t0 <= WINDOW.index("2026-02")}
    table(mature, "FULLY-MATURE balanced cohort (t0 <= 2026-02: every offset "
                  "in [-2..+2] w8-mature)")


if __name__ == "__main__":
    main()
