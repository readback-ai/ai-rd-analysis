"""Study: did review produce ACTION? Post-review edits, pinned definition.

The measurement triangle for review effectiveness:
  comments/kLOC        -> did review produce talk        (studies.attention)
  comment length       -> how much talk                  (needs body pull)
  POST-REVIEW EDITS    -> did review produce action      (this study)

PINNED DEFINITION (do not vary): lines changed (additions+deletions) in
commits whose committedDate is AFTER the PR's FIRST human review event
(first review by a User, reviewer != author, bot logins excluded,
submittedAt <= cutoff), where the commit's AUTHOR is the PR author (matched
by author email set / login), excluding commits committed by bots. Reported
as (a) action rate: share of reviewed-merged PRs with >=1 qualifying
post-review commit; (b) post-review LOC share of the PR's total LOC.

Known proxy caveats (documented, not corrected): committedDate is rewritten
by rebase/amend (drifts toward push time — direction inflates post-review
attribution); squash-merged branches retain original branch-commit dates.

Data: census cells lack per-commit dates/LOC, so this study owns a SAMPLED
pull (LOC-weighted, ~1,200 reviewed-merged PRs/quarter, checkpointed to
data/derived/review_action_sample.jsonl).

Usage:
  python -m pipeline.studies.review_action --pull    # collect sample
  python -m pipeline.studies.review_action           # compute tables
"""
from __future__ import annotations

import argparse
import json
import random
import time
from pathlib import Path

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import CUTOFF, MARKERS_V2, classify_pr, split_reviews
from pipeline.ghx import graphql_nodes
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.slices import population_repos

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
CAP = 20_000
SAMPLE = Path("data/derived/review_action_sample.jsonl")
PER_QUARTER = 1200

Q = """
query{ %s }
"""
FIELDS = ("{ pullRequest(number:%d){ commits(first:60){ nodes{ commit{ "
          "committedDate additions deletions "
          "authors(first:3){ nodes{ email user{ login } } } "
          "committer{ email user{ login } } } } } } }")


def first_human_review(pr: dict) -> str | None:
    human_other, _, _ = split_reviews(pr)
    times = [r.get("submittedAt") for r in human_other
             if r.get("submittedAt") and r["submittedAt"] <= CUTOFF]
    return min(times) if times else None


def eligible() -> dict[str, list]:
    keep = population_repos()
    pool: dict[str, list] = {p: [] for p in PERIODS}
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        for p in prs:
            a = p.get("author") or {}
            if a.get("__typename") == "Bot":
                continue
            c = classify_pr(p, MARKERS_V2)
            frt = first_human_review(p)
            loc = min((p.get("additions") or 0) + (p.get("deletions") or 0), CAP)
            if c.merged and c.human_reviewed and frt and loc:
                pool[per].append((repo, p["number"], loc, frt, a.get("login"),
                                  bool(c.ai_involved), bool(c.insider)))
    return pool


def pull() -> None:
    random.seed(20260630)
    pool = eligible()
    done = set()
    if SAMPLE.exists():
        for ln in SAMPLE.read_text().splitlines():
            d = json.loads(ln)
            done.add((d["repo"], d["num"]))
    out = SAMPLE.open("a")
    for per, items in pool.items():
        weights = [x[2] for x in items]
        chosen = {items[i] for i in
                  random.choices(range(len(items)), weights=weights,
                                 k=PER_QUARTER)}
        todo = [x for x in chosen if (x[0], x[1]) not in done]
        print(f"{per}: {len(todo)} to pull", flush=True)
        for i in range(0, len(todo), 8):
            chunk = todo[i:i + 8]
            parts = []
            for j, (repo, num, *_rest) in enumerate(chunk):
                o, n = repo.split("/", 1)
                parts.append(f'a{j}: repository(owner:"{o}", name:"{n}")'
                             + FIELDS % num)
            data = graphql_nodes(Q % " ".join(parts), {}, ".data", expect=dict)
            if data is None:
                continue
            for j, (repo, num, loc, frt, login, ai, ins) in enumerate(chunk):
                node = data.get(f"a{j}") or {}
                prq = node.get("pullRequest") if isinstance(node, dict) else None
                if prq:
                    out.write(json.dumps({
                        "per": per, "repo": repo, "num": num, "loc": loc,
                        "first_review": frt, "author": login, "ai": ai,
                        "ins": ins,
                        "commits": (prq.get("commits") or {}).get("nodes") or [],
                    }) + "\n")
            time.sleep(1)
    print("REVIEW-ACTION PULL DONE", flush=True)


def compute() -> None:
    from collections import defaultdict
    agg = defaultdict(lambda: defaultdict(float))
    for ln in SAMPLE.read_text().splitlines():
        d = json.loads(ln)
        post = total = 0
        for c in d["commits"]:
            cm = c.get("commit") or {}
            loc = (cm.get("additions") or 0) + (cm.get("deletions") or 0)
            total += loc
            committer = (cm.get("committer") or {})
            cl = ((committer.get("user") or {}).get("login")
                  or committer.get("email") or "")
            if "[bot]" in cl or cl.endswith("-bot"):
                continue
            author_logins = {((x or {}).get("user") or {}).get("login")
                             for x in (cm.get("authors") or {}).get("nodes") or []}
            if d["author"] not in author_logins:
                continue
            if (cm.get("committedDate") or "") > d["first_review"]:
                post += loc
        for coh in ("all", "AI" if d["ai"] else "nonAI",
                    "ins" if d["ins"] else "ext"):
            a = agg[(d["per"], coh)]
            a["n"] += 1
            a["acted"] += post > 0
            a["post"] += min(post, CAP)
            a["total"] += min(max(total, d["loc"]), CAP)
    print("post-review action — merged, human-reviewed PRs (LOC-weighted sample)")
    print(f"{'cohort':14}{'PRs':>6}{'action rate%':>13}{'post-review LOC share%':>23}")
    for per in PERIODS:
        for coh in ("all", "AI", "nonAI", "ins", "ext"):
            a = agg[(per, coh)]
            if not a["n"]:
                continue
            print(f"{per + ' ' + coh:14}{int(a['n']):>6}"
                  f"{100*a['acted']/a['n']:>12.1f}%"
                  f"{100*a['post']/a['total']:>22.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    a = ap.parse_args()
    (pull if a.pull else compute)()


if __name__ == "__main__":
    main()
