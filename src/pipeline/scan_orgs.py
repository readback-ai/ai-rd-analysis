"""Stage 1 — org AI-evidence scan.

For each org, count commits matching each AI tool (EVERY search term per tool;
a tool's count is the max over its terms — terms overlap on the same commits,
so max is an honest floor without double-counting). Idempotent: cells
checkpoint to raw/scan_orgs/, keyed by org + date range + marker-set name, so
changing a quarter definition or the marker set re-pulls instead of silently
serving stale counts.

Usage:
  python -m pipeline.scan_orgs --orgs data/resume_state/v2/v2_active.txt \
      --quarters Q1-2024 Q3-2025 Q4-2025 Q1-2026 Q2-2026 --out scan.tsv
  (omit --quarters for all-time counts)
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
import time
from pathlib import Path

from pipeline.ghx import MARKERS_V1, MARKERS_V2, cell_path, read_cell, rest_count

QUARTER_RANGES = {
    "Q1-2024": "2024-01-01..2024-03-31",
    "Q3-2025": "2025-07-01..2025-09-30",
    "Q4-2025": "2025-10-01..2025-12-31",
    "Q1-2026": "2026-01-01..2026-03-31",
    "Q2-2026": "2026-04-01..2026-06-30",   # full quarter (review gap P2.9)
}
SEARCH_PACE_S = 2.0                         # 30 req/min search budget


def scan_org(org: str, quarter: str | None, markers: dict,
             markers_name: str) -> dict | None:
    """One org x period -> {tool: {"terms": [per-term counts], "count": max}}.
    Checkpointed by (org, date-range, marker-set)."""
    rng = QUARTER_RANGES[quarter] if quarter else "all-time"
    p = cell_path("scan_orgs", org, rng, markers_name)
    cached = read_cell(p, dict)
    if cached is not None:
        return cached
    out: dict[str, dict] = {}
    first = True
    for tool, spec in markers.items():
        counts = []
        for term in spec.search_terms:
            if not first:
                time.sleep(SEARCH_PACE_S)   # pace BEFORE each request after the 1st
            first = False
            q = f"org:{org} {term}"
            if quarter:
                q += f" author-date:{QUARTER_RANGES[quarter]}"
            n = rest_count(q)
            if n is None:                   # gave up -> don't checkpoint a lie
                return None
            counts.append(n)
        out[tool] = {"terms": counts, "count": max(counts)}
    p.write_text(json.dumps(out))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--orgs", required=True, help="file with one org login per line")
    ap.add_argument("--quarters", nargs="*", default=None,
                    choices=list(QUARTER_RANGES), help="omit for all-time")
    ap.add_argument("--markers", choices=["v1", "v2"], default="v1")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    markers = MARKERS_V1 if a.markers == "v1" else MARKERS_V2
    orgs = [ln.strip() for ln in Path(a.orgs).read_text().splitlines() if ln.strip()]
    periods = a.quarters or [None]
    sink = open(a.out, "w", newline="") if a.out else sys.stdout
    w = csv.writer(sink, delimiter="\t")
    w.writerow(["org", "period"] + list(markers))
    for org in orgs:
        for per in periods:
            res = scan_org(org, per, markers, a.markers)
            row = [org, per or "all-time"]
            row += [res[t]["count"] if res and t in res else "ERR" for t in markers]
            w.writerow(row)
            sink.flush()
    if a.out:
        sink.close()


if __name__ == "__main__":
    main()
