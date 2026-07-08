"""Study: readable PR corpora for qualitative analysis (§9–§10, §11e).

Dumps a human-readable corpus of sampled PRs — title line with flags, top
changed files, and commit-message sequence — for close reading. Two draws:

- unreviewed-substantial: merged, >100 changed lines, no human review
  (reviewer!=author), human-authored. Backs the §10 thematic read.
- session: multi-commit all-AI-commit merged PRs. Backs the §11e read.

Usage:
  python -m pipeline.studies.corpus --draw unreviewed --period Q2-2026 \
      --n 130 --out corpus_Q2-2026.txt
"""
from __future__ import annotations

import argparse
import random

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import MARKERS_V1, classify_pr
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.review_modes import commit_ai


def _flags(pr: dict, n_authors: int) -> str:
    c = classify_pr(pr, MARKERS_V1)
    lines = (pr.get("additions") or 0) + (pr.get("deletions") or 0)
    bits = ["INS" if c.insider else "ext",
            "solo" if n_authors == 1 else f"{n_authors}auth",
            f"{lines}ln"]
    if c.marker_tools:
        bits.append("AIcode")
    if c.ai_reviewed:
        bits.append("AIrev")
    return "|".join(bits)


def dump(prs: list[tuple[str, dict, int]], out: str) -> None:
    with open(out, "w") as f:
        for repo, pr, n_auth in prs:
            title = (pr.get("title") or "").strip() or "(no title)"
            f.write(f"### {repo}#{pr.get('number')} [{_flags(pr, n_auth)}] {title}\n")
            for c in (pr.get("commits") or {}).get("nodes") or []:
                msg = ((c.get("commit") or {}).get("message") or "").split("\n")[0]
                f.write(f"    c: {msg[:110]}\n")
    print(f"wrote {len(prs)} PRs -> {out}")


def draw_unreviewed(period: str, n: int, seed: int) -> list[tuple[str, dict, int]]:
    random.seed(seed)
    grouped = group_by_period(load_cells(), QUARTER_RANGES)
    authors: dict[str, set] = {}
    pool = []
    for (repo, per), prs in grouped.items():
        if per != period:
            continue
        authors[repo] = {(p.get("author") or {}).get("login")
                         for p in prs if (p.get("author") or {}).get("__typename") == "User"}
        for p in prs:
            c = classify_pr(p, MARKERS_V1)
            if (p.get("author") or {}).get("__typename") == "Bot":
                continue
            lines = (p.get("additions") or 0) + (p.get("deletions") or 0)
            if c.merged and lines > 100 and not c.human_reviewed:
                pool.append((repo, p))
    return [(repo, p, len(authors.get(repo) or [1]))
            for repo, p in random.sample(pool, min(n, len(pool)))]


def draw_session(period: str, n: int, seed: int) -> list[tuple[str, dict, int]]:
    random.seed(seed)
    grouped = group_by_period(load_cells(), QUARTER_RANGES)
    pool = []
    for (repo, per), prs in grouped.items():
        if per != period:
            continue
        for p in prs:
            if (p.get("author") or {}).get("__typename") == "Bot" or not p.get("mergedAt"):
                continue
            commits = (p.get("commits") or {}).get("nodes") or []
            if len(commits) >= 2 and all(commit_ai(c) for c in commits):
                pool.append((repo, p))
    return [(repo, p, 0) for repo, p in random.sample(pool, min(n, len(pool)))]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--draw", choices=["unreviewed", "session"], required=True)
    ap.add_argument("--period", default="Q2-2026", choices=list(QUARTER_RANGES))
    ap.add_argument("--n", type=int, default=130)
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    fn = draw_unreviewed if a.draw == "unreviewed" else draw_session
    dump(fn(a.period, a.n, a.seed), a.out)


if __name__ == "__main__":
    main()
