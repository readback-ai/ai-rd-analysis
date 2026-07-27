"""Population slices for detailed reporting (results.md sections 5-6).

Six slices from two published cuts, derived entirely from data files:
- Adoption groups, from population.tsv's scope+reason:
    AI-majority  full-org via dev-list/override, or >=3 of top-5 AI-topic
    AI-heavy     full-org via exactly 2 of top-5
    repo-scoped  scope=repo (AI-topic repos of conglomerates/single-product)
- Org types, from data/sources/org_type.tsv: public / private / community.

PRIMARY METRIC: ai_involved = union of the three detection layers per PR
(commit markers OR agent author OR agent branch prefix) — a lower bound on
true AI involvement. Requires census-v2 cells (headRefName); the metric is
undefined (skipped) on legacy cells.

Usage:
  python -m pipeline.studies.slices --table involvement
  python -m pipeline.studies.slices --table selfmerge
  python -m pipeline.studies.slices --table botcheck
"""
from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path

from pipeline.analyze import (bootstrap_ci, extended_quarters,
                              weighted_mean)
from pipeline.detect import (MARKERS, pr_agent_author, pr_ai_tools,
                             pr_branch_tool)
from pipeline.frame import PERIODS, study_groups

SRC = Path("data/sources")
DRV = Path("data/derived")
MIN_PRS = 5            # per quarter; month floor is 2 (comparable threshold)
GRANULARITY = "quarter"  # set by main() --granularity


def _floor() -> int:
    return MIN_PRS if GRANULARITY == "quarter" else 2


def _lines(p: Path) -> list[str]:
    return [ln for ln in p.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


def adoption_group(scope: str, why: str, top5_ai: int) -> str:
    """Grouping uses the MEASURED concentration (top5_ai), not the admission
    reason: AI-majority = >=3 of top-5 AI-topic'd OR dev-list/override
    identity (topic-sparse labs are AI companies by list scope); AI-heavy =
    full-org with measured 0-2 and no list identity."""
    if scope == "repo":
        return "repo-scoped"
    if top5_ai >= 3 or why in ("dev-list", "override"):
        return "AI-majority"
    return "AI-heavy"


def slices() -> dict[str, set[str]]:
    """slice name -> set of orgs (lower)."""
    out: dict[str, set[str]] = defaultdict(set)
    for ln in _lines(DRV / "population.tsv"):
        org, scope, why, n5 = ln.split("\t")
        out[adoption_group(scope, why, int(n5))].add(org.lower())
    pop = {o for s in out.values() for o in s}
    for ln in _lines(SRC / "org_type.tsv"):
        o, t = ln.split("\t")
        if o.lower() in pop:
            out[t].add(o.lower())
    return dict(out)


def weights() -> dict[str, float]:
    """Window-scoped contributor weights (pipeline.contributors); falls back
    to the all-time file with a warning until the window pull completes."""
    src = DRV / "repo_contributors_window.csv"
    if not src.exists():
        src = DRV / "repo_contributors_v2.csv"
        print(f"WARN: using ALL-TIME contributor weights ({src.name}); "
              f"run pipeline.contributors for window weights", flush=True)
    out = {}
    with open(src) as fh:
        for row in csv.reader(fh):
            if row and row[0] != "repo":
                out[row[0]] = max(1.0, float(row[1] or 1))
    return out


def repo_rates() -> dict[tuple[str, str], dict[str, float | None]]:
    """(repo, period) -> per-repo rates of the slice metrics. None where the
    metric's denominator is under MIN_PRS or the field is unavailable."""
    out: dict[tuple[str, str], dict[str, float | None]] = {}
    for (repo, per), facts in study_groups(
            "all", periods=None, ranges=extended_quarters(),
            granularity=GRANULARITY):
        if len(facts) < _floor():
            continue
        cls = [f.cls for f in facts]
        n = len(cls)
        # outcome metrics (merge/review/self-merge) are defined only on
        # w8-MATURE PRs — immature state is provisional (frozen rule
        # 1d.1; external review P1: studies must gate like analyze does)
        mat = [c for c in cls if c.w8_mature]
        merged = [c for c in mat if c.merged]
        sm = [c for c in merged if c.self_merged]        # needs mergedBy
        sm_known = [c for c in merged if c.self_merged is not None]
        ai = [c for c in cls if c.ai_involved]           # intrinsic: all PRs
        sm_ai = [c for c in sm if c.ai_involved]
        sm_non = [c for c in sm if not c.ai_involved]

        def rate(hits: int, base: int) -> float | None:
            return hits / base if base >= _floor() else None
        rev2x2 = {}
        if len(merged) >= _floor():
            m = len(merged)
            rev2x2 = {
                "m_hum_only": sum(c.human_reviewed and not c.ai_reviewed
                                  for c in merged) / m,
                "m_ai_only": sum(c.ai_reviewed and not c.human_reviewed
                                 for c in merged) / m,
                "m_both": sum(c.human_reviewed and c.ai_reviewed
                              for c in merged) / m,
                "m_neither": sum(not c.human_reviewed and not c.ai_reviewed
                                 for c in merged) / m,
            }
        out[(repo, per)] = {
            "m_hum_only": rev2x2.get("m_hum_only"),
            "m_ai_only": rev2x2.get("m_ai_only"),
            "m_both": rev2x2.get("m_both"),
            "m_neither": rev2x2.get("m_neither"),
            "ai_involved": len(ai) / n,
            "hum_rev": rate(sum(c.human_reviewed for c in mat), len(mat)),
            "ai_rev": rate(sum(c.ai_reviewed for c in mat), len(mat)),
            "merged": rate(len(merged), len(mat)),
            "self_merged": rate(len(sm), len(sm_known)),
            "ai_of_selfm": rate(sum(c.ai_involved for c in sm), len(sm)),
            "ai_of_otherm": rate(sum(c.ai_involved for c in sm_known if not c.self_merged),
                                 len(sm_known) - len(sm)),
            "humrev_selfm_ai": rate(sum(c.human_reviewed for c in sm_ai), len(sm_ai)),
            "humrev_selfm_non": rate(sum(c.human_reviewed for c in sm_non), len(sm_non)),
        }
    return out


def bot_sensitivity() -> None:
    """How much of the headline involvement rate is bot-mix (PR #1 review
    item 3)?

    The published `ai_involved` series runs on profile "all", so App-bot PRs
    (dependabot/renovate/CI — never AI-involved) sit in its DENOMINATOR. That
    is a defensible floor, but if bot volume grew across the window a rising
    bot share would mechanically depress the AI share, making part of the
    0.0 -> 16.9 slope a change in bot mix rather than in practice.

    MEASURED 2026-07-27: it does not. The bot share is roughly flat (7.3% ->
    9.4% of PRs), and the no-dilution series tracks the published one within
    its CI (Q2-2026 17.9 vs 16.9, CI width ~+-1.9pp) — so the trend is not a
    bot-mix artifact. Kept as a standing check, since the answer depends on
    data that changes every update.

    Two counterfactuals, because they differ in SIGN:
    - no-dilution drops bot PRs that are NOT AI-involved and keeps layer-B
      coding agents. This isolates denominator dilution and is the column to
      read.
    - no-bots is profile "pr", which drops every bot author — including the
      coding agents that ARE the AI signal. In Q4-2025 that removes more
      numerator than denominator (2.5 vs a published 3.0), which is why a
      single "bots excluded" column would invite the wrong conclusion.

    One census pass: both populations are subsets of "all".
    Changes no published number — it is a companion diagnostic."""
    w = weights()
    rows: dict[str, list] = defaultdict(list)
    for (repo, per), facts in study_groups(
            "all", periods=None, ranges=extended_quarters(),
            granularity=GRANULARITY):
        if len(facts) < _floor():
            continue
        # THE clean counterfactual: drop bot PRs that are not AI-involved
        # (dependabot/renovate/CI dilution) while KEEPING layer-B coding
        # agents, which are bot-authored AND the AI signal. Profile "pr"
        # drops both, so it answers a different question — reported beside
        # it because the two differ in sign (see the docstring).
        dilute = [f for f in facts
                  if not (f.bot_author and not f.cls.ai_involved)]
        hum = [f for f in facts if not f.bot_author]
        rows[per].append((
            w.get(repo, 1.0),
            sum(f.cls.ai_involved for f in facts) / len(facts),
            (sum(f.cls.ai_involved for f in dilute) / len(dilute)
             if len(dilute) >= _floor() else None),
            (sum(f.cls.ai_involved for f in hum) / len(hum)
             if len(hum) >= _floor() else None),
            len(facts), len(hum)))
    print("involvement sensitivity to BOT-AUTHORED PRs in the denominator")
    print("published   = profile 'all', as reported (every bot PR in the "
          "denominator)")
    print("no-dilution = non-AI bot PRs dropped, layer-B coding agents KEPT "
          "— the clean counterfactual for denominator dilution")
    print("no-bots     = profile 'pr' (ALL bot authors dropped, agents "
          "included): removes AI signal too, so it can move the OTHER way")
    print(f"{'period':9}{'repos':>6}{'published':>20}{'no-dilution':>20}"
          f"{'no-bots':>20}{'bot%':>7}")
    for per in (PERIODS if GRANULARITY == "quarter" else sorted(rows)):
        rs = rows.get(per)
        if not rs:
            continue
        n_all = sum(r[4] for r in rs) or 1
        bot_share = 100 * (n_all - sum(r[5] for r in rs)) / n_all
        line = f"{per:9}{len(rs):>6}"
        for col, key in ((1, "published"), (2, "no-dilution"), (3, "no-bots")):
            pairs = [(r[col], r[0]) for r in rs if r[col] is not None]
            if not pairs:
                line += f"{'n/a':>20}"
                continue
            m = weighted_mean(pairs)
            lo, hi = bootstrap_ci(pairs, 1000)
            line += f"  {100*m:5.1f} [{100*lo:4.1f},{100*hi:4.1f}]"
        print(line + f"{bot_share:>6.1f}%")


def table(metrics: list[str], header: str) -> None:
    rates = repo_rates()
    w = weights()
    for name, orgs in slices().items():
        print(f"\n=== {name} ===")
        print(f"{'period':9}{'repos':>6}" + "".join(f"{m:>22}" for m in metrics))
        periods = PERIODS if GRANULARITY == "quarter" else \
            sorted({p for (_, p) in rates})
        for per in periods:
            rows = [(repo, r) for (repo, p), r in rates.items()
                    if p == per and repo.split("/")[0].lower() in orgs]
            if not rows:
                continue
            line = f"{per:9}{len(rows):>6}"
            for m in metrics:
                pairs = [(r[m], w.get(repo, 1.0)) for repo, r in rows
                         if r[m] is not None]
                if not pairs:
                    line += f"{'n/a':>22}"
                    continue
                mean = weighted_mean(pairs)
                lo, hi = bootstrap_ci(pairs, 500)
                line += f"  {100*mean:5.1f} [{100*lo:4.1f},{100*hi:4.1f}]"
            print(line)


def bounds() -> None:
    """The study's single two-sided bound (METHODS §2): headline CW
    ai_involved WITH the weak-prefix (cursor/, claude/) indeterminate C-only
    PRs (upper arm, the reported headline) and WITHOUT them (lower arm —
    weak prefixes count only with positive provenance). Everything else in
    the study is a one-sided floor."""
    w = weights()
    per_repo: dict[str, dict[tuple, list]] = {"hi": defaultdict(list), "lo": defaultdict(list)}
    for (repo, per), facts in study_groups(
            "all", periods=None, ranges=extended_quarters(),
            granularity=GRANULARITY):
        if len(facts) < _floor():
            continue
        n = len(facts)
        def involved(p, strict):
            return bool(pr_ai_tools(p, MARKERS)
                        or pr_agent_author(p)
                        or pr_branch_tool(p, strict=strict))
        per_repo["hi"][per].append((sum(involved(f.pr, False)
                                        for f in facts) / n,
                                    w.get(repo, 1.0)))
        per_repo["lo"][per].append((sum(involved(f.pr, True)
                                        for f in facts) / n,
                                    w.get(repo, 1.0)))
    periods = PERIODS if GRANULARITY == "quarter" else \
        sorted({p for p in per_repo["hi"]})
    print("headline ai_involved: two-sided bound (CW)")
    print(f"{'period':9}{'upper (reported)':>20}{'lower (strict C)':>20}{'delta pp':>10}")
    for per in periods:
        hi, lo = per_repo["hi"][per], per_repo["lo"][per]
        if not hi:
            continue
        mh, ml = weighted_mean(hi), weighted_mean(lo)
        print(f"{per:9}{100*mh:>19.2f}%{100*ml:>19.2f}%{100*(mh-ml):>9.2f}")


def balanced_panel() -> None:
    """Sensitivity check promised in METHODS §1: the headline series on the
    BALANCED panel — only repos that qualify (>= MIN_PRS PRs) in every
    censused quarter — versus the repeated cross-section reported elsewhere.
    Separates the adoption trend from cohort-composition change."""
    rates = repo_rates()
    w = weights()
    periods = PERIODS if GRANULARITY == "quarter" else \
        sorted({p for (_, p) in rates})
    by_repo: dict[str, set[str]] = defaultdict(set)
    for (repo, per) in rates:
        by_repo[repo].add(per)
    # sorted: bootstrap pairs must be order-deterministic — iterating the
    # bare set made the seeded CIs PYTHONHASHSEED-dependent (gate finding,
    # test_balanced_panel_ci_reproducible_across_hash_seeds)
    panel = sorted({r for r, pers in by_repo.items() if set(periods) <= pers})
    print(f"balanced panel: {len(panel)} repos qualify in all "
          f"{len(periods)} {GRANULARITY}s")
    print(f"{'period':9}{'panel ai_involved':>22}{'cross-section':>22}")
    for per in periods:
        rows_p = [(rates[(r, per)]["ai_involved"], w.get(r, 1.0)) for r in panel]
        rows_x = [(v["ai_involved"], w.get(repo, 1.0))
                  for (repo, p), v in rates.items() if p == per]
        mp, (lp, hp) = weighted_mean(rows_p), bootstrap_ci(rows_p, 1000)
        mx, (lx, hx) = weighted_mean(rows_x), bootstrap_ci(rows_x, 1000)
        print(f"{per:9}  {100*mp:5.1f} [{100*lp:4.1f},{100*hp:4.1f}]"
              f"  {100*mx:5.1f} [{100*lx:4.1f},{100*hx:4.1f}]")


def main() -> None:
    global GRANULARITY
    ap = argparse.ArgumentParser()
    ap.add_argument("--table",
                    choices=["involvement", "selfmerge", "panel", "bounds",
                             "reviewers", "botcheck"],
                    default="involvement")
    ap.add_argument("--granularity", choices=["quarter", "month"],
                    default="quarter")
    a = ap.parse_args()
    GRANULARITY = a.granularity
    if a.table == "involvement":
        table(["ai_involved", "hum_rev", "ai_rev", "merged"],
              "AI involvement (A∪B∪C) by slice")
    elif a.table == "panel":
        balanced_panel()
    elif a.table == "bounds":
        bounds()
    elif a.table == "botcheck":
        bot_sensitivity()
    elif a.table == "reviewers":
        table(["m_hum_only", "m_ai_only", "m_both", "m_neither"],
              "reviewer profile of MERGED PRs by slice")
    else:
        table(["self_merged", "ai_of_selfm", "ai_of_otherm",
               "humrev_selfm_ai", "humrev_selfm_non"],
              "self-merge behavior by slice")


if __name__ == "__main__":
    main()
