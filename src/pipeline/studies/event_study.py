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

Censoring rule (outcome A, merged): only w8-MATURE calendar months
contribute observations — mature_max() derives the last month whose PRs
all closed their 8-week windows by the data AS_OF; later observations are
EXCLUDED from every cell rather than reported deflated. Outcome B
(SUBMITTED kLOC — all PRs created in the month, merged or not) needs no
maturity gate and runs on the full window.

Composition control: alongside the all-observations table, a BALANCED cohort
(authors observed at every offset in [-2..+2]) removes entry/exit drift; its
FULLY-MATURE variant further requires t0 <= mature_max()-2 so every
offset in [-2..+2] falls in a mature month (no censoring in the panel).
Adoptions in the first observed month (2025-10) are excluded — no
pre-period; left-censored adopters (active in 2024 with AI already in
2025-10) cannot be aligned.

Usage:  python -m pipeline.studies.event_study
"""
from __future__ import annotations

from collections import defaultdict
from statistics import mean, median

from pipeline.analyze import group_by_period, load_cells
from pipeline import detect
from pipeline.detect import MARKERS, classify_pr, is_bot_login
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.slices import population_repos

WINDOW = ["2025-10", "2025-11", "2025-12", "2026-01", "2026-02", "2026-03",
          "2026-04", "2026-05", "2026-06"]
BASELINE = ["2024-01", "2024-02", "2024-03"]
CAP = 20_000
def mature_max() -> int:
    """Index of the last WINDOW month whose PRs ALL reached w8 maturity by
    the data AS_OF (month_end + 56d <= AS_OF) — derived, not hard-coded,
    so bumping AS_OF after a re-pull extends the mature range
    (external review P1). Later months are excluded, not deflated."""
    from calendar import monthrange
    from datetime import datetime, timedelta
    as_of = datetime.fromisoformat(detect.AS_OF.replace("Z", "+00:00"))
    last = -1
    for i, tok in enumerate(WINDOW):
        y, m = int(tok[:4]), int(tok[5:7])
        end = datetime(y, m, monthrange(y, m)[1], 23, 59,
                       tzinfo=as_of.tzinfo)
        if end + timedelta(days=56) <= as_of:
            last = i
    return last


def author_months():
    """login -> month -> [merged_kloc, ai_pr_count, insider_any,
    submitted_kloc]."""
    keep = population_repos()
    out = defaultdict(lambda: defaultdict(lambda: [0.0, 0, False, 0.0]))
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES,
                                            "month").items():
        if repo not in keep:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot" or not a.get("login") \
                    or is_bot_login(a["login"]):
                continue
            c = classify_pr(p, MARKERS)
            row = out[a["login"]][per]
            kloc = min((p.get("additions") or 0)
                       + (p.get("deletions") or 0), CAP) / 1000
            row[3] += kloc
            if c.merged:
                row[0] += kloc
            if c.ai_involved:
                row[1] += 1
            if p.get("authorAssociation") in ("MEMBER", "OWNER",
                                              "COLLABORATOR"):
                row[2] = True
    return out


def mature_month_label() -> str:
    return WINDOW[mature_max()]


def mature_cap_label() -> str:
    return "t0 <= " + WINDOW[mature_cap()]


def balanced_cap() -> int:
    """Calendar balance is a property of the FIXED window: an adopter needs
    t0+2 inside WINDOW regardless of maturity (round-5 review P1)."""
    return len(WINDOW) - 3


def mature_cap() -> int:
    """Fully mature outcome panel: every offset in [-2..+2] must be a
    mature month, i.e. t0 <= mature_max() - 2."""
    return mature_max() - 2


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
    print(f"outcome A = MERGED kLOC (w8); months after "
          f"{WINDOW[mature_max()]} (w8-immature at AS_OF) excluded. "
          "outcome B = SUBMITTED kLOC; full window.")

    def table(cohort, label, field=0, max_idx=None):
        max_idx = mature_max() if max_idx is None else max_idx
        print(f"\n{label}")
        print(f"{'event month':12}{'authors':>8}{'mean kLOC/mo':>13}{'median':>8}")
        for e in range(-4, 5):
            vals = []
            for login, t0 in cohort.items():
                idx = t0 + e
                if 0 <= idx <= max_idx:
                    vals.append(am[login].get(
                        WINDOW[idx], [0.0, 0, False, 0.0])[field])
            if len(vals) >= 30:
                print(f"{('t' + format(e, '+d')):12}{len(vals):>8}"
                      f"{mean(vals):>13.2f}{median(vals):>8.2f}")

    balanced = {login: t0 for login, t0 in events.items()
                if 2 <= t0 <= min(balanced_cap(), mature_max())}
    mature = {login: t0 for login, t0 in events.items()
              if 2 <= t0 <= min(balanced_cap(), mature_cap())}

    print("\n=== outcome A: MERGED kLOC (w8) ===")
    table(events, "ALL alignable adopters (unbalanced event panel)")
    table(balanced, "BALANCED cohort (observed at every offset in [-2..+2]; "
                    f"post-t0 offsets past {mature_month_label()} excluded)")
    table(mature, f"FULLY-MATURE balanced cohort ({mature_cap_label()}: "
                  "every offset in [-2..+2] w8-mature)")

    print("\n=== outcome B: SUBMITTED kLOC (all PRs created in the month; "
          "no censoring, full window through 2026-06) ===")
    last = len(WINDOW) - 1
    table(events, "ALL alignable adopters (unbalanced event panel)",
          field=3, max_idx=last)
    table(balanced, "BALANCED cohort (observed at every offset in [-2..+2])",
          field=3, max_idx=last)
    table(mature, f"{mature_cap_label()} cohort (same authors as "
                  "fully-mature merged panel)", field=3, max_idx=last)


if __name__ == "__main__":
    main()
