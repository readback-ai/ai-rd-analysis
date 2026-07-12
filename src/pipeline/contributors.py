"""Window-scoped contributor weights.

Contributor weighting should reflect who was actually active during the
study, not all-time history (a long-dead 500-committer project should not
weigh like an active one). Source: REST /repos/{repo}/stats/contributors —
GitHub returns WEEKLY per-contributor commit counts, so we sum the weeks
inside the window and count contributors above the core threshold.

Semantics: weight(repo) = number of human contributors with >= MIN_COMMITS
commits authored inside WINDOW (bots excluded by login suffix). The endpoint
computes stats lazily (HTTP 202 on first hit) — we retry with backoff and
FAIL (skip, no row) rather than record a fake weight.

Usage:
  python -m pipeline.contributors --repos data/derived/population_repos.txt \
      --out data/derived/repo_contributors_window.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path

WINDOW = ("2025-10-01", "2026-06-30")     # Q4-2025..Q2-2026 (study quarters)
MIN_COMMITS = 5                           # core threshold within the window


def _week_in_window(epoch: int) -> bool:
    d = datetime.fromtimestamp(epoch, tz=timezone.utc).date().isoformat()
    return WINDOW[0] <= d <= WINDOW[1]


def window_contributors(repo: str, retries: int = 5) -> int | None:
    """Count of core human contributors in WINDOW, or None on failure."""
    for attempt in range(retries):
        r = subprocess.run(["gh", "api", f"repos/{repo}/stats/contributors"],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            time.sleep(10 * (attempt + 1))
            continue
        body = r.stdout.strip()
        if not body:                       # 202: stats still computing
            time.sleep(10 * (attempt + 1))
            continue
        try:
            data = json.loads(body)
        except json.JSONDecodeError:
            return None
        if not isinstance(data, list):
            return None
        core = 0
        for c in data:
            login = ((c.get("author") or {}).get("login") or "")
            if login.endswith("[bot]") or not login:
                continue
            commits = sum(w.get("c", 0) for w in c.get("weeks", [])
                          if _week_in_window(w.get("w", 0)))
            if commits >= MIN_COMMITS:
                core += 1
        return core
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repos", required=True)
    ap.add_argument("--out", default="data/derived/repo_contributors_window.csv")
    a = ap.parse_args()
    out = Path(a.out)
    have = set()
    if out.exists():
        with out.open() as fh:
            have = {row[0] for row in csv.reader(fh) if row}
    else:
        out.write_text("repo,core_contributors_window\n")
        have = {"repo"}
    repos = [r for r in Path(a.repos).read_text().split() if r not in have]
    failed = 0
    with out.open("a") as fh:
        w = csv.writer(fh)
        for i, repo in enumerate(repos):
            n = window_contributors(repo)
            if n is None:
                failed += 1
                print(f"FAIL {repo}", flush=True)
            else:
                w.writerow([repo, n])
            if i % 50 == 0:
                print(f"{i}/{len(repos)}", flush=True)
            time.sleep(0.8)
    print(f"window contributors done; {failed} failures (rerun to retry)")
    if failed:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
