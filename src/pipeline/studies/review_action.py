"""Study: did review produce ACTION? Post-review edits, pinned definition.

The measurement triangle for review effectiveness:
  comments/kLOC        -> did review produce talk        (studies.attention)
  comment length       -> how much talk                  (needs body pull)
  POST-REVIEW EDITS    -> did review produce action      (this study)

IDENTIFIED DESIGN (2026-07-16): an edit after both a human comment and an
AI-reviewer comment is causally ambiguous, and that interleaving is the
2025-26 norm — so the estimand anchors on EXPLICIT HUMAN ASKS and the clean
lane:

1. CONDITIONAL RESPONSIVENESS (primary): among PRs with a human ASK — a
   reviewer!=author human review with state CHANGES_REQUESTED or >=1 inline
   comment — the share with subsequent author edits (commits
   committedDate-after the FIRST ask, authored by the PR author, bot
   committers excluded) and the lines involved.
2. CLEAN LANE (the identified estimate): responsiveness restricted to PRs
   with human review activity and NO AI-reviewer activity (ai_reviewed
   False). The MIXED lane (human + AI reviewers) is reported descriptively
   only.
3. ALL-CAUSE post-review edits (any-review anchor) survives as a
   descriptive companion (comparable to merged-without-modification
   metrics), never as evidence about human review specifically.

Paired with the changes-requested share (how often humans ask), this
decomposes the action channel: how often review asks, and whether asking
still works.

Known proxy caveats (documented, not corrected): committedDate is rewritten
by rebase/amend (drifts toward push time — direction inflates post-review
attribution); squash-merged branches retain original branch-commit dates.

Data: census cells lack per-commit dates/LOC, so this study owns a SAMPLED
pull (PPS: 1,200 LOC-proportional draws/quarter with replacement, distinct
PRs retained, checkpointed to data/derived/review_action_sample.jsonl).

ESTIMATION (external review P1 fixes, 2026-07-20):
- PR-WEIGHTED PRIMARY via Horvitz-Thompson: each sampled PR i with LOC
  weight w_i in a quarter of total eligible LOC W has inclusion
  probability pi_i = 1-(1-w_i/W)^k (k=1200 PPS draws); rates weight each
  PR by 1/pi_i, so responded% estimates the population per-ask
  probability, not a size-biased sample rate. post-ask LOC share% is the
  ratio of HT-weighted LOC totals (population LOC estimand). Raw sample
  counts are printed alongside.
- COMMIT PAGINATION: commits are fetched 100/page with totalCount;
  saturated PRs get follow-up paginated pulls (the previous first:60
  cap chronologically truncated exactly the post-ask commits on
  high-commit PRs, biasing responsiveness DOWN). `--repair` re-pulls
  previously-truncated records; compute() keeps the newest record per PR.

Usage:
  python -m pipeline.studies.review_action --pull    # collect sample
  python -m pipeline.studies.review_action --repair  # re-pull truncated
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
COMMIT_FIELDS = ("nodes{ commit{ committedDate additions deletions "
                 "authors(first:3){ nodes{ email user{ login } } } "
                 "committer{ email user{ login } } } } "
                 "pageInfo{ hasNextPage endCursor } totalCount")
FIELDS = ("{ pullRequest(number:%d){ commits(first:100){ "
          + COMMIT_FIELDS + " } } }")


def _all_commits(repo: str, num: int) -> list[dict] | None:
    """Paginated fetch of ALL commits for one PR (saturation follow-up)."""
    o, n = repo.split("/", 1)
    nodes: list[dict] = []
    cursor = ""
    while True:
        after = ', after:"%s"' % cursor if cursor else ""
        q = ('query{ repository(owner:"%s", name:"%s"){ '
             'pullRequest(number:%d){ commits(first:100%s){ %s } } } }'
             % (o, n, num, after, COMMIT_FIELDS))
        conn = graphql_nodes(q, {}, ".data.repository.pullRequest.commits",
                             expect=dict)
        if conn is None:
            return None
        nodes.extend(conn.get("nodes") or [])
        pi = conn.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            return nodes
        cursor = pi.get("endCursor") or ""
        time.sleep(1)


def first_human_review(pr: dict) -> str | None:
    human_other, _, _ = split_reviews(pr)
    times = [r.get("submittedAt") for r in human_other
             if r.get("submittedAt") and r["submittedAt"] <= CUTOFF]
    return min(times) if times else None


def first_human_ask(pr: dict) -> str | None:
    """First explicit human ask: reviewer!=author review that requested
    changes or carried inline comments (an APPROVED with zero comments is
    not an ask)."""
    human_other, _, _ = split_reviews(pr)
    times = [r.get("submittedAt") for r in human_other
             if r.get("submittedAt") and r["submittedAt"] <= CUTOFF
             and (r.get("state") == "CHANGES_REQUESTED"
                  or (r.get("comments") or {}).get("totalCount", 0) > 0)]
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
                    conn = prq.get("commits") or {}
                    commits = conn.get("nodes") or []
                    if (conn.get("pageInfo") or {}).get("hasNextPage"):
                        commits = _all_commits(repo, num) or commits
                    out.write(json.dumps({
                        "per": per, "repo": repo, "num": num, "loc": loc,
                        "first_review": frt, "author": login, "ai": ai,
                        "ins": ins, "commits": commits,
                    }) + "\n")
            time.sleep(1)
    print("REVIEW-ACTION PULL DONE", flush=True)


def repair() -> None:
    """Re-pull records truncated by the old commits(first:60) cap; appended
    records supersede (compute keeps the newest per PR)."""
    recs = {}
    for ln in SAMPLE.read_text().splitlines():
        d = json.loads(ln)
        recs[(d["repo"], d["num"])] = d
    trunc = [d for d in recs.values() if len(d["commits"]) == 60]
    print(f"{len(trunc)} truncated records to repair", flush=True)
    out = SAMPLE.open("a")
    for i, d in enumerate(trunc):
        commits = _all_commits(d["repo"], d["num"])
        if commits is None:
            print(f"SKIP {d['repo']}#{d['num']}: pull failed", flush=True)
            continue
        d["commits"] = commits
        out.write(json.dumps(d) + "\n")
        if i % 25 == 0:
            print(f"  {i}/{len(trunc)}", flush=True)
        time.sleep(1)
    print("REVIEW-ACTION REPAIR DONE", flush=True)


def _author_edits_after(d: dict, anchor: str) -> tuple[int, int]:
    """(post_anchor_author_loc, total_commit_loc), bot committers excluded."""
    post = total = 0
    for c in d["commits"]:
        if not c:
            continue                       # ghost-commit nodes arrive as null
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
        if (cm.get("committedDate") or "") > anchor:
            post += loc
    return min(post, CAP), min(max(total, d["loc"]), CAP)


def compute() -> None:
    from collections import defaultdict
    # one census pass: ask anchors + lane flags + the PPS sampling frame
    # (per-PR LOC weights and quarter LOC totals for inclusion probs)
    keep = population_repos()
    anchors: dict = {}
    frame: dict = {}                     # (repo, num) -> (per, loc)
    W: dict = defaultdict(float)         # per -> total eligible LOC
    for (repo, per), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        if repo not in keep or per not in PERIODS:
            continue
        for p in prs:
            c = classify_pr(p, MARKERS_V2)
            anchors[(repo, p.get("number"))] = (
                first_human_ask(p), c.ai_reviewed)
            a = p.get("author") or {}
            if a.get("__typename") == "Bot":
                continue
            frt = first_human_review(p)
            loc = min((p.get("additions") or 0) + (p.get("deletions") or 0), CAP)
            if c.merged and c.human_reviewed and frt and loc:
                frame[(repo, p["number"])] = (per, loc)
                W[per] += loc

    def inv_pi(key) -> float:
        """Horvitz-Thompson weight under k PPS draws with replacement."""
        per, loc = frame[key]
        pi = 1.0 - (1.0 - loc / W[per]) ** PER_QUARTER
        return 1.0 / pi

    recs: dict = {}                      # newest record per PR wins (repair)
    for ln in SAMPLE.read_text().splitlines():
        d = json.loads(ln)
        recs[(d["repo"], d["num"])] = d
    lanes = defaultdict(lambda: defaultdict(float))
    dropped = 0
    for key, d in recs.items():
        if key not in frame:
            dropped += 1                 # frame drift (re-classification)
            continue
        ipw = inv_pi(key)
        ask, ai_rev = anchors.get(key, (None, None))
        # descriptive companion: all-cause (any-review anchor)
        post, total = _author_edits_after(d, d["first_review"])
        a = lanes[(d["per"], "all-cause")]
        a["n"] += 1
        a["wn"] += ipw
        a["wacted"] += ipw * (post > 0)
        a["post"] += ipw * post
        a["total"] += ipw * total
        if not ask:
            continue                      # no explicit human ask on this PR
        post, total = _author_edits_after(d, ask)
        lane = "mixed" if ai_rev else "CLEAN"
        for coh in (lane, lane + ("+AI" if d["ai"] else "+nonAI")):
            a = lanes[(d["per"], coh)]
            a["n"] += 1
            a["wn"] += ipw
            a["wacted"] += ipw * (post > 0)
            a["post"] += ipw * post
            a["total"] += ipw * total
    if dropped:
        print(f"note: {dropped} sampled PRs no longer in the eligible frame "
              "(reclassified since pull); excluded")
    print("conditional responsiveness to HUMAN ASKS (changes-requested or "
          "inline comments)")
    print("CLEAN lane = no AI-reviewer activity (identified); "
          "mixed = descriptive; all-cause = companion only")
    print("HT inclusion-probability weighted (PPS sample -> population "
          "estimands): responded% is PR-weighted; LOC share% is the "
          "population post-ask LOC ratio")
    print(f"{'lane':22}{'PRs':>6}{'responded%':>11}{'post-ask LOC share%':>20}")
    for per in PERIODS:
        for coh in ("CLEAN", "CLEAN+AI", "CLEAN+nonAI", "mixed", "all-cause"):
            a = lanes[(per, coh)]
            if a["n"] < 20:
                continue
            print(f"{per + ' ' + coh:22}{int(a['n']):>6}"
                  f"{100*a['wacted']/a['wn']:>10.1f}%"
                  f"{100*a['post']/a['total']:>19.1f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--repair", action="store_true")
    a = ap.parse_args()
    (pull if a.pull else repair if a.repair else compute)()


if __name__ == "__main__":
    main()
