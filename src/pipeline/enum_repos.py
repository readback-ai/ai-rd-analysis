"""Stage 2 — enumerate AI-evidence repos inside AI-active orgs.

Pages the commit-search results for each marker (up to the 1000-result cap) and
tallies hits per repository. This is what scopes big-tech orgs correctly:
`org:microsoft` activity resolves to microsoft/DeepSpeed etc., not 8k repos.

Keep rule (Ron, 2026-06-26): a repo enters the analysis set if it has >=5 AI
commits, OR >=0.1% of its PRs are AI in any period (checked downstream where
PR denominators exist).

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

from pipeline.ghx import MARKERS_V1, MARKERS_V2, cell_path, cell_valid


def _paginate_repos(query: str, retries: int = 3) -> list[str] | None:
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
        time.sleep(25)
    return None


def enum_org(org: str, window: str, markers: dict) -> dict[str, dict[str, int]] | None:
    """org -> {repo: {tool: n_hits}}. Checkpointed per org x window."""
    p = cell_path("enum_repos", org, window)
    if cell_valid(p, dict):
        return json.loads(p.read_text())
    tally: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for tool, needles in markers.items():
        repos = _paginate_repos(f"org:{org} {needles[0]} author-date:{window}")
        if repos is None:
            return None
        for r in repos:
            tally[r][tool] += 1
        time.sleep(2)
    out = {r: dict(t) for r, t in tally.items()}
    p.write_text(json.dumps(out))
    return out


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
    w.writerow(["repo", "ai_commits"] + list(markers))
    for org in orgs:
        res = enum_org(org, a.window, markers)
        if res is None:
            w.writerow([f"{org}/*", "ERR"] + [""] * len(markers))
            continue
        for repo, tools in sorted(res.items(), key=lambda kv: -sum(kv[1].values())):
            total = sum(tools.values())
            if total >= a.min_commits:
                w.writerow([repo, total] + [tools.get(t, 0) for t in markers])
        sink.flush()
    if a.out:
        sink.close()


if __name__ == "__main__":
    main()
