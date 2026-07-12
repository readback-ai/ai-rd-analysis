"""Stage 5 — INTEGRATED AI-involvement decomposition across detection layers.

Since census-v2 (headRefName + mergedBy population-wide), ALL THREE layers
are observed per-PR inside the census, so the layered decomposition is exact
and computed on ONE population (population_repos.txt) — no cross-source
denominators, no sample-based overlap corrections:

  B  agent-authored      detect.pr_agent_author
  A' marker, not B       detect.pr_ai_tools
  C' branch, not A/B     detect.pr_branch_tool
  union = ai_involved    (the primary metric; see studies.slices)

Pooled shares are over census-sampled PRs (uniform-over-time sub-windows;
see census.py) and are reported alongside the contributor-weighted per-repo
series. Cells that name repos outside the population manifest FAIL loudly.

The org-level branch scans and per-prefix PR samples remain as admission
evidence and for per-prefix lane characterization (sample_stats measures the
A∪B overlap DIRECTLY as a union share — never as summed marginals).

Usage:
  python -m pipeline.integrate                      # layered decomposition
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

V2 = Path("data/derived")
PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]


# ------------------------------------------------------------- denominators

def org_totals(periods: list[str] = PERIODS) -> dict[tuple[str, str], int]:
    """(org, period) -> total PRs (for org-level threshold adjustment)."""
    out: dict[tuple[str, str], int] = defaultdict(int)
    for repo in (V2 / "fullorg_repos.txt").read_text().split():
        org = repo.split("/")[0]
        for per in periods:
            try:
                out[(org, per)] += json.load(open(precount_path(repo, per)))["total"]
            except (OSError, ValueError, KeyError):
                continue
    return dict(out)


# ----------------------------------------------------------------- layer C

def branch_counts(*paths: Path) -> dict[tuple[str, str, str], int]:
    """Read branch-scan TSVs (org, period, prefix, n)."""
    counts: dict[tuple[str, str, str], int] = {}
    for path in paths:
        if not path.exists():
            continue
        for ln in path.read_text().splitlines():
            f = ln.split("\t")
            if len(f) == 4 and f[3].isdigit():
                counts[(f[0], f[1], f[2])] = int(f[3])
    return counts


def sample_stats(sample_dir: Path, markers=MARKERS_V2) -> dict[str, dict[str, float]]:
    """Org-weighted per-period stats from one prefix's sample cells:
    ab_overlap (share of sampled PRs already caught by layer A or B — a
    DIRECT union measurement, never summed marginals), human_rev, ai_rev,
    merged (shares of all PRs), and norev_merged / self_merged (shares of
    MERGED PRs). Weights =
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
        d["ab_overlap"] += w * sum(bool(pr_ai_tools(p, markers))
                                   or pr_agent_author(p) is not None
                                   for p in prs) / n
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


# ------------------------------------------------------------------- report

def layered_table() -> None:
    """Exact per-PR layer decomposition over the population manifest."""
    keep = set((V2 / "population_repos.txt").read_text().split())
    grouped = group_by_period(load_cells(), QUARTER_RANGES)
    if not grouped:
        raise SystemExit("no census cells in $AIRD_DATA_DIR — refusing to "
                         "print an empty decomposition")
    agg: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for (repo, per), prs in grouped.items():
        if repo not in keep:
            continue
        d = agg[per]
        for p in prs:
            d["n"] += 1
            c = classify_pr(p, MARKERS_V2)
            if c.agent_author:
                d["b"] += 1
            elif c.marker_tools:
                d["a"] += 1
            elif c.branch_tool:
                d["c"] += 1
    print(f"{'period':9}{'PRs':>8}{'A marker%':>10}{'B agent%':>9}"
          f"{'C branch%':>10}{'union%':>8}")
    for per in PERIODS:
        d = agg.get(per)
        if not d or not d["n"]:
            continue
        n = d["n"]
        print(f"{per:9}{n:>8}{100*d['a']/n:>9.2f}%{100*d['b']/n:>8.2f}%"
              f"{100*d['c']/n:>9.2f}%{100*(d['a']+d['b']+d['c'])/n:>7.2f}%")


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
    counts = branch_counts(V2 / "branch_scan.tsv")
    stats = {pfx: sample_stats(d) for pfx, d in (sample_dirs or {}).items()
             if d.exists()}

    def keep_factor(pfx: str, per: str) -> float:
        st = stats.get(pfx, {}).get(per)
        return max(0.0, 1 - st["ab_overlap"]) if st else 1.0

    ototal = org_totals()
    org_repos: dict[str, list[str]] = defaultdict(list)
    for repo in (V2 / "fullorg_repos.txt").read_text().split():
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
    sample_dirs = {f"{tag}/": V2 / "branch_samples" / tag
                   for tag in ("codex", "copilot", "cursor", "claude")}
    if a.thresholds:
        threshold_table(sample_dirs=sample_dirs)
    else:
        layered_table()


if __name__ == "__main__":
    main()
