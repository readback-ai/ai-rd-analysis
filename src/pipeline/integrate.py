"""Stage 5 — INTEGRATED AI-involvement metrics across all detection layers.

Combines, per quarter, with layers kept disjoint (v2_results §12/§13):

  A. marker-attributed PRs   — census cells, detect.pr_ai_tools (pooled rate)
  B. agent-authored PRs      — census cells, detect.pr_agent_author
  C. branch-attributed PRs   — branch_scan counts / precount denominators,
                               with per-prefix overlap corrections measured on
                               the org-stratified samples (pull_prs):
                               - marker overlap (would double-count layer A)
                               - bot-author overlap (would double-count B;
                                 ~100% of copilot/ PRs are Copilot-authored)

  total AI involvement = A + B + C_only

Also blends branch-sample review metrics into the census-based review-of-AI
trends, weighting each component by its population PR count. Prefixes without
a pulled sample get their raw count share reported with overlap marked
unknown — never silently assumed.

Usage:
  python -m pipeline.integrate                      # layered table
  python -m pipeline.integrate --thresholds         # org adoption thresholds
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import defaultdict
from pathlib import Path

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import (MARKERS_V2, classify_pr, pr_agent_author,
                             pr_ai_tools)
from pipeline.precount import precount_path
from pipeline.scan_orgs import QUARTER_RANGES

V2 = Path("data/resume_state/v2")
PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]


# ------------------------------------------------------------- denominators

def population_totals(repos_file: Path = V2 / "census_repos.txt",
                      periods: list[str] = PERIODS) -> dict[str, int]:
    """period -> total PRs in the population (precount sums)."""
    totals: dict[str, int] = defaultdict(int)
    for repo in repos_file.read_text().split():
        for per in periods:
            try:
                totals[per] += json.load(open(precount_path(repo, per)))["total"]
            except (OSError, ValueError, KeyError):
                continue
    return dict(totals)


def org_totals(periods: list[str] = PERIODS) -> dict[tuple[str, str], int]:
    """(org, period) -> total PRs (for org-level threshold adjustment)."""
    out: dict[tuple[str, str], int] = defaultdict(int)
    for repo in (V2 / "census_repos.txt").read_text().split():
        org = repo.split("/")[0]
        for per in periods:
            try:
                out[(org, per)] += json.load(open(precount_path(repo, per)))["total"]
            except (OSError, ValueError, KeyError):
                continue
    return dict(out)


# ----------------------------------------------------------------- layer C

def branch_counts(*paths: Path) -> dict[tuple[str, str, str], int]:
    """Merge branch-scan TSVs. Accepts both the 4-col format
    (org, period, prefix, n) and the original 3-col codex scan
    (org, period, n -> prefix codex/)."""
    counts: dict[tuple[str, str, str], int] = {}
    for path in paths:
        if not path.exists():
            continue
        for ln in path.read_text().splitlines():
            f = ln.split("\t")
            if len(f) == 4 and f[3].isdigit():
                counts[(f[0], f[1], f[2])] = int(f[3])
            elif len(f) == 3 and f[2].isdigit():
                counts.setdefault((f[0], f[1], "codex/"), int(f[2]))
    return counts


def sample_stats(sample_dir: Path, markers=MARKERS_V2) -> dict[str, dict[str, float]]:
    """Org-weighted per-period stats from one prefix's sample cells:
    marker_overlap, bot_author_share, human_rev, ai_rev, merged (shares of all
    PRs), and norev_merged / self_merged (shares of MERGED PRs). Weights =
    pop_count. Conditional metrics use POPULATION-RATIO semantics (weighted
    merged mass in the denominator), i.e. "of merged <prefix> PRs population-
    wide, X% were self-merged" — matching v2_results §12b — not a mean of
    per-org conditional rates (orgs' merge rates differ too much for those to
    coincide)."""
    acc: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for f in sorted(sample_dir.glob("*.json")):
        try:
            cell = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        prs = [p for p in cell.get("prs") or [] if p]
        if not prs:
            continue
        w, n = cell["pop_count"], len(prs)
        d = acc[cell["period"]]
        cls = [classify_pr(p, markers) for p in prs]
        merged = [c for c in cls if c.merged]
        d["w"] += w
        d["marker_overlap"] += w * sum(bool(pr_ai_tools(p, markers)) for p in prs) / n
        d["bot_author"] += w * sum(pr_agent_author(p) is not None for p in prs) / n
        d["human_rev"] += w * sum(c.human_reviewed for c in cls) / n
        d["ai_rev"] += w * sum(c.ai_reviewed for c in cls) / n
        d["merged"] += w * len(merged) / n
        d["norev_merged_mass"] += w * sum(not c.human_reviewed for c in merged) / n
        d["self_merged_mass"] += w * sum(bool(c.self_merged) for c in merged) / n
    out: dict[str, dict[str, float]] = {}
    for per, d in acc.items():
        w = d["w"]
        row = {k: v / w for k, v in d.items() if k != "w"}
        row["w"] = w
        m = row.pop("norev_merged_mass"), row.pop("self_merged_mass")
        row["norev_merged"] = m[0] / row["merged"] if row["merged"] else 0.0
        row["self_merged"] = m[1] / row["merged"] if row["merged"] else 0.0
        out[per] = row
    return out


# ----------------------------------------------------------------- layers A+B

def census_layers(markers=MARKERS_V2) -> dict[str, dict[str, float]]:
    """period -> pooled census shares: marker rate (layer A) and
    agent-authored rate (layer B) over ALL census PRs."""
    grouped = group_by_period(load_cells(), QUARTER_RANGES)
    agg: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for (_, per), prs in grouped.items():
        d = agg[per]
        for p in prs:
            d["n"] += 1
            if pr_agent_author(p):
                d["agent"] += 1
            elif pr_ai_tools(p, markers):
                d["marker"] += 1
    return {per: {"marker": d["marker"] / d["n"], "agent": d["agent"] / d["n"]}
            for per, d in agg.items() if d["n"]}


# ------------------------------------------------------------------- report

def layered_table(sample_dirs: dict[str, Path]) -> None:
    pop = population_totals()
    counts = branch_counts(V2 / "branch_scan.tsv", V2 / "codex_branch_scan.tsv")
    census = census_layers()
    stats = {pfx: sample_stats(d) for pfx, d in sample_dirs.items() if d.exists()}
    print(f"{'period':9}{'markerA%':>9}{'agentB%':>9}"
          f"{'branch raw%':>12}{'branch-only C%':>15}{'total AI%':>10}")
    for per in PERIODS:
        if per not in census or not pop.get(per):
            continue
        a, b = census[per]["marker"], census[per]["agent"]
        raw = c_only = 0.0
        unknown = []
        for pfx in {p for (_, q, p) in counts if q == per}:
            n = sum(v for (o, q, p), v in counts.items() if q == per and p == pfx)
            share = n / pop[per]
            raw += share
            st = stats.get(pfx, {}).get(per)
            if st:
                c_only += share * max(0.0, 1 - st["marker_overlap"] - st["bot_author"])
            else:
                unknown.append(pfx)
                c_only += share          # uncorrected; flagged below
        note = f"  (no sample for {','.join(sorted(unknown))}: overlap uncorrected)" \
            if unknown else ""
        print(f"{per:9}{100*a:>8.2f}%{100*b:>8.2f}%{100*raw:>11.2f}%"
              f"{100*c_only:>14.2f}%{100*(a+b+c_only):>9.2f}%{note}")


def threshold_table(contrib_csv: Path = V2 / "repo_contributors_v2.csv",
                    sample_dirs: dict[str, Path] | None = None) -> None:
    """Org adoption thresholds: CW marker rate + org branch share with the
    measured per-prefix overlap corrections applied (period-global factors —
    per-org overlap is not identified from one sample page)."""
    weights: dict[str, float] = {}
    with open(contrib_csv) as fh:
        for row in csv.reader(fh):
            if row and row[0] != "repo":
                weights[row[0]] = max(1.0, float(row[1] or 1))
    grouped = group_by_period(load_cells(), QUARTER_RANGES)
    rate: dict[tuple[str, str], float] = {}
    for (repo, per), prs in grouped.items():
        human = [p for p in prs if (p.get("author") or {}).get("__typename") != "Bot"]
        if human:
            rate[(repo, per)] = sum(bool(pr_ai_tools(p, MARKERS_V2)) for p in human) / len(human)
    counts = branch_counts(V2 / "branch_scan.tsv", V2 / "codex_branch_scan.tsv")
    stats = {pfx: sample_stats(d) for pfx, d in (sample_dirs or {}).items()
             if d.exists()}

    def keep_factor(pfx: str, per: str) -> float:
        st = stats.get(pfx, {}).get(per)
        return max(0.0, 1 - st["marker_overlap"] - st["bot_author"]) if st else 1.0

    ototal = org_totals()
    org_repos: dict[str, list[str]] = defaultdict(list)
    for repo in (V2 / "census_repos.txt").read_text().split():
        org_repos[repo.split("/")[0]].append(repo)
    for per in ("Q1-2026", "Q2-2026"):
        base, adj = [], []
        for org, repos in org_repos.items():
            num = den = 0.0
            for r in repos:
                if (r, per) in rate:
                    w = weights.get(r, 1.0)
                    num += w * rate[(r, per)]
                    den += w
            if not den:
                continue
            cw = num / den
            branch = sum(v * keep_factor(p, q) for (o, q, p), v in counts.items()
                         if o == org and q == per)
            share = branch / ototal[(org, per)] if ototal.get((org, per)) else 0.0
            base.append(cw)
            adj.append(min(1.0, cw + share))
        n = len(base)
        print(f"\n{per} (n={n} orgs) — share of orgs with AI rate >= threshold:")
        for t in (0.10, 0.25, 0.50, 0.75):
            print(f"  >={int(t*100):>3}%: markers {100*sum(x >= t for x in base)/n:5.1f}%"
                  f"   +branch {100*sum(x >= t for x in adj)/n:5.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--thresholds", action="store_true")
    a = ap.parse_args()
    sample_dirs = {f"{tag}/": V2 / f"{tag}_prs"
                   for tag in ("codex", "copilot", "cursor", "claude")}
    if a.thresholds:
        threshold_table(sample_dirs=sample_dirs)
    else:
        layered_table(sample_dirs)


if __name__ == "__main__":
    main()
