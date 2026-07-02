"""Stage 1 — org AI-evidence scan.

For each org, count commits matching each AI marker (bare-term commit search),
optionally per quarter. Idempotent: results checkpoint to raw/scan_orgs/ cells;
re-runs skip valid cells. Output table -> stdout TSV or --out.

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

from pipeline.ghx import MARKERS_V1, MARKERS_V2, cell_path, cell_valid, rest_count

QUARTER_RANGES = {
    "Q1-2024": "2024-01-01..2024-03-31",
    "Q3-2025": "2025-07-01..2025-09-30",
    "Q4-2025": "2025-10-01..2025-12-31",
    "Q1-2026": "2026-01-01..2026-03-31",
    "Q2-2026": "2026-04-01..2026-06-30",   # full quarter (review gap P2.9)
}


def scan_org(org: str, quarter: str | None, markers: dict) -> dict | None:
    """One org x period -> {tool: count}. Checkpointed."""
    key = (org, quarter or "all-time")
    p = cell_path("scan_orgs", *key)
    if cell_valid(p, dict):
        return json.loads(p.read_text())
    out: dict[str, int] = {}
    for tool, needles in markers.items():
        q = f"org:{org} {needles[0]}"          # primary needle = the email/committer term
        if quarter:
            q += f" author-date:{QUARTER_RANGES[quarter]}"
        n = rest_count(q)
        if n is None:                            # gave up -> don't checkpoint a lie
            return None
        out[tool] = n
        time.sleep(2)                            # 30 req/min search budget
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
            res = scan_org(org, per, markers)
            row = [org, per or "all-time"] + [res.get(t, "ERR") if res else "ERR"
                                              for t in markers]
            w.writerow(row)
            sink.flush()
    if a.out:
        sink.close()


if __name__ == "__main__":
    main()
