"""Stage 4 — weighted metrics from census cells, with bootstrap CIs.

Reads raw/census/ cells, classifies each PR (AI-code via marker set; reviewer
types), computes per-repo-period rates, then reports equal-weight and
contributor-weighted averages per period with bootstrap 95% CIs over repos.

Bot-review is DECOMPOSED (review gap P1.4): reviewers whose login is in
AI_REVIEWERS count as ai_review; other Bot-typed reviewers as other_bot_review.

Usage:
  python -m pipeline.analyze --contributors data/repo_contributors.csv \
      --markers v1 --bootstrap 2000
"""
from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
from collections import defaultdict
from pathlib import Path

from pipeline.ghx import MARKERS_V1, MARKERS_V2, pr_ai_tools, raw_dir

AI_REVIEWERS = {  # dedicated AI code-review bots seen in the data (extend as found)
    "gemini-code-assist", "copilot-pull-request-reviewer", "coderabbitai",
    "greptile-apps", "qodo-merge-pro", "cursor", "chatgpt-codex-connector",
    "copilot-swe-agent", "claude",
}
INSIDER = {"MEMBER", "OWNER", "COLLABORATOR"}


def load_cells() -> dict[tuple[str, str], list[dict]]:
    """(repo, period-or-range) -> PR nodes. Cell name: repo~name@range.json"""
    cells: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for f in raw_dir("census").glob("*.json"):
        try:
            nodes = json.loads(f.read_text())
        except json.JSONDecodeError:
            continue
        if not isinstance(nodes, list):
            continue
        stem = f.stem
        repo_part, _, rng = stem.partition("@")
        repo = repo_part.replace("~", "/")
        cells[(repo, rng)].extend(n for n in nodes if n)
    return cells


def period_of(rng: str, quarters: dict[str, str]) -> str | None:
    start = rng.split("..")[0]
    for q, qr in quarters.items():
        if qr.split("..")[0] <= start <= qr.split("..")[1]:
            return q
    return None


def pr_metrics(pr: dict, markers: dict) -> dict:
    revs = [r for r in (pr.get("reviews") or {}).get("nodes") or [] if r.get("author")]
    human = [r for r in revs if r["author"]["__typename"] == "User"]
    bots = [r for r in revs if r["author"]["__typename"] == "Bot"]
    ai_rev = [r for r in bots
              if (r["author"].get("login") or "").removesuffix("[bot]") in AI_REVIEWERS]
    return {
        "ai_code": bool(pr_ai_tools(pr, markers)),
        "merged": bool(pr.get("mergedAt")),
        "human_review": bool(human),
        "ai_review": bool(ai_rev),
        "other_bot_review": bool(len(ai_rev) < len(bots)),
        "no_review": not revs,
        "insider": pr.get("authorAssociation") in INSIDER,
        "size": (pr.get("additions") or 0) + (pr.get("deletions") or 0),
    }


METRICS = ["ai_code", "merged", "human_review", "ai_review", "other_bot_review", "no_review"]


def weighted_mean(pairs: list[tuple[float, float]]) -> float:
    tot = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / tot if tot else float("nan")


def bootstrap_ci(pairs: list[tuple[float, float]], n: int = 2000) -> tuple[float, float]:
    if len(pairs) < 2:
        return (float("nan"), float("nan"))
    stats = sorted(weighted_mean(random.choices(pairs, k=len(pairs))) for _ in range(n))
    return stats[int(0.025 * n)], stats[int(0.975 * n)]


def main() -> None:
    from pipeline.scan_orgs import QUARTER_RANGES
    ap = argparse.ArgumentParser()
    ap.add_argument("--contributors", default="data/repo_contributors.csv")
    ap.add_argument("--markers", choices=["v1", "v2"], default="v1")
    ap.add_argument("--min-prs", type=int, default=10)
    ap.add_argument("--bootstrap", type=int, default=2000)
    a = ap.parse_args()
    markers = MARKERS_V1 if a.markers == "v1" else MARKERS_V2
    weights: dict[str, float] = {}
    if Path(a.contributors).is_file():
        for row in csv.DictReader(open(a.contributors)):
            try:
                weights[row["repo"]] = max(float(row["core_contributors"]), 1.0)
            except (KeyError, ValueError):
                pass

    # aggregate cells -> (repo, period) PR lists
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    for (repo, rng), nodes in load_cells().items():
        per = period_of(rng, QUARTER_RANGES)
        if per:
            grouped[(repo, per)].extend(nodes)

    print(f"{'period':9}{'weighting':16}{'repos':>6}" +
          "".join(f"{m:>18}" for m in METRICS))
    for per in QUARTER_RANGES:
        rows = []
        for (repo, p), prs in grouped.items():
            if p != per or len(prs) < a.min_prs:
                continue
            ms = [pr_metrics(pr, markers) for pr in prs]
            rates = {m: sum(x[m] for x in ms) / len(ms) for m in METRICS}
            rows.append((repo, rates))
        if not rows:
            continue
        for label, wfn in (("equal-weight", lambda r: 1.0),
                           ("contrib-weight", lambda r: weights.get(r, 1.0))):
            line = f"{per:9}{label:16}{len(rows):>6}"
            for m in METRICS:
                pairs = [(rates[m], wfn(repo)) for repo, rates in rows]
                mean = weighted_mean(pairs)
                lo, hi = bootstrap_ci(pairs, a.bootstrap)
                line += f"  {100*mean:5.1f} [{100*lo:4.1f},{100*hi:4.1f}]"
            print(line)


if __name__ == "__main__":
    main()
