"""Stage 2 — enumerate AI-evidence repos inside AI-active orgs.

Pages the commit-search results for EVERY search term of every tool (up to the
1000-result cap per query) and tallies hits per repository; a repo's per-tool
count is the max over that tool's terms (terms overlap on the same commits).
Saturating the 1000-cap is DETECTED (result count vs total_count) and warned —
silent truncation biased repo tallies for the largest orgs once.

Keep rule (Ron, 2026-06-26), BOTH branches implemented here:
  keep a repo if AI commits >= --min-commits (absolute branch),
  OR AI commits >= 0.1% of the repo's PRs in the window (rate branch —
  checked via one PR-count lookup for each sub-threshold repo with >=1 hit).

Usage:
  python -m pipeline.enum_repos --orgs v2_active.txt \
      --window 2025-07-01..2026-06-30 --min-commits 5 --out repos.tsv
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import sys
import time
from collections import defaultdict
from pathlib import Path

from pipeline.detect import MARKERS_V1, MARKERS_V2
from pipeline.ghx import cell_path, read_cell, rest_count

RATE_KEEP = 0.001                       # 0.1% of PRs (keep-rule OR-branch)
SEARCH_CAP = 1000                       # GitHub search hard cap per query


def _paginate_repos(query: str, retries: int = 6) -> list[str] | None:
    """repository.full_name for every commit-search hit (<=1000/query)."""
    for _ in range(retries):
        try:
            r = subprocess.run(
                ["gh", "api", "--paginate", "-X", "GET", "search/commits",
                 "-f", f"q={query}", "-f", "per_page=100",
                 "--jq", ".items[].repository.full_name"],
                capture_output=True, text=True, timeout=300)
            if r.returncode == 0:
                return [ln for ln in r.stdout.splitlines() if ln.strip()]
        except subprocess.TimeoutExpired:
            pass
        time.sleep(45)
    return None


def enum_org(org: str, window: str, markers: dict,
             markers_name: str) -> dict[str, dict[str, int]] | None:
    """org -> {repo: {tool: max-hits-over-terms}}. Checkpointed by
    (org, window, marker-set). Warns on 1000-cap saturation."""
    p = cell_path("enum_repos", org, window, markers_name)
    cached = read_cell(p, dict)
    if cached is not None:
        return cached
    tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for tool, spec in markers.items():
        for term in spec.search_terms:
            q = f"org:{org} {term} author-date:{window}"
            repos = _paginate_repos(q)
            if repos is None:
                return None
            if len(repos) >= SEARCH_CAP:
                total = rest_count(q)
                print(f"WARN {org}/{tool}: search cap hit "
                      f"({len(repos)} returned, {total} total) — repo tallies "
                      f"truncated; narrow the window to recover the tail",
                      file=sys.stderr, flush=True)
            per_term: dict[str, int] = defaultdict(int)
            for r in repos:
                per_term[r] += 1
            for r, n in per_term.items():
                tally[r][tool] = max(tally[r][tool], n)
            time.sleep(2)
    out = {r: dict(t) for r, t in tally.items()}
    p.write_text(json.dumps(out))
    return out


def keep_reason(repo: str, total_hits: int, window: str,
                min_commits: int) -> str | None:
    """Apply BOTH keep-rule branches. Returns 'abs', 'rate', or None."""
    if total_hits >= min_commits:
        return "abs"
    if total_hits < 1:
        return None
    prs = rest_count(f"repo:{repo} is:pr created:{window}", endpoint="search/issues")
    time.sleep(2)
    if prs and prs > 0 and total_hits / prs >= RATE_KEEP:
        return "rate"
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orgs", required=True)
    ap.add_argument("--window", default="2025-07-01..2026-06-30")
    ap.add_argument("--markers", choices=["v1", "v2"], default="v1")
    ap.add_argument("--min-commits", type=int, default=5)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    markers = MARKERS_V1 if a.markers == "v1" else MARKERS_V2
    orgs = [ln.strip() for ln in Path(a.orgs).read_text().splitlines() if ln.strip()]
    sink = open(a.out, "w", newline="") if a.out else sys.stdout
    w = csv.writer(sink, delimiter="\t")
    w.writerow(["repo", "ai_commits", "keep_rule"] + list(markers))
    for org in orgs:
        res = enum_org(org, a.window, markers, a.markers)
        if res is None:
            print(f"WARN {org}: enumeration failed — re-run to retry",
                  file=sys.stderr, flush=True)
            continue
        for repo, tools in sorted(res.items(), key=lambda kv: -sum(kv[1].values())):
            total = sum(tools.values())
            rule = keep_reason(repo, total, a.window, a.min_commits)
            if rule:
                w.writerow([repo, total, rule] + [tools.get(t, 0) for t in markers])
        sink.flush()
    if a.out:
        sink.close()


if __name__ == "__main__":
    main()
