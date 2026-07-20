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
from pipeline.detect import MARKERS, classify_pr, split_reviews
from pipeline.ghx import graphql_nodes
from pipeline.scan_orgs import QUARTER_RANGES
from pipeline.studies.slices import population_repos

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
CAP = 20_000
# v2: redrawn under the MATURE-GATED eligibility frame (2026-07-24) — HT
# inclusion probabilities are only valid for records drawn from the frame
# they are computed on. The v1 file remains solely as a hydration cache
# (commit data is frame-independent PR fact; selection is not).
SAMPLE = Path("data/derived/review_action_sample_v2.jsonl")
OLD_SAMPLE = Path("data/derived/review_action_sample.jsonl")
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


def _all_commits(repo: str, num: int) -> tuple[list[dict], int] | None:
    """Paginated fetch of ALL commits for one PR (saturation follow-up).
    Returns (nodes, totalCount) only when COMPLETE (len >= totalCount);
    None on any failure — a missing endCursor, a failed page, or a short
    result must never checkpoint as a complete record (external review
    P1: silent fallback created permanently truncated records)."""
    o, n = repo.split("/", 1)
    nodes: list[dict] = []
    cursor = ""
    total = None
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
        total = conn.get("totalCount")
        pi = conn.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        cursor = pi.get("endCursor")
        if not cursor:
            return None                  # would loop on the first page
        time.sleep(1)
    if total is None or len(nodes) < total:
        return None                      # short result is not complete
    return nodes, total


def first_human_review(pr: dict) -> str | None:
    """split_reviews already applies the w8 event window — no extra bound."""
    human_other, _, _ = split_reviews(pr)
    times = [r.get("submittedAt") for r in human_other if r.get("submittedAt")]
    return min(times) if times else None


def first_human_ask(pr: dict) -> str | None:
    """First explicit human ask: reviewer!=author review that requested
    changes or carried inline comments (an APPROVED with zero comments is
    not an ask)."""
    human_other, _, _ = split_reviews(pr)
    times = [r.get("submittedAt") for r in human_other
             if r.get("submittedAt")
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
            c = classify_pr(p, MARKERS)
            frt = first_human_review(p)
            loc = min((p.get("additions") or 0) + (p.get("deletions") or 0), CAP)
            if c.w8_mature and c.merged and c.human_reviewed and frt and loc:
                pool[per].append((repo, p["number"], loc, frt, a.get("login"),
                                  bool(c.ai_involved), bool(c.insider)))
    return pool


def _hydration_cache() -> dict:
    """(repo, num) -> COMPLETE commit records from any prior sample file —
    reusable because commit data is a PR-level fact independent of the
    sampling frame; only the DRAW must come from the current frame."""
    cache = {}
    for path in (OLD_SAMPLE, SAMPLE):
        if not path.exists():
            continue
        for ln in path.read_text().splitlines():
            d = json.loads(ln)
            if not _suspect(d):
                cache[(d["repo"], d["num"])] = d
    return cache


def pull() -> None:
    random.seed(20260630)
    pool = eligible()
    done = set()
    if SAMPLE.exists():
        for ln in SAMPLE.read_text().splitlines():
            d = json.loads(ln)
            done.add((d["repo"], d["num"]))
    reuse = _hydration_cache()
    out = SAMPLE.open("a")
    for per, items in pool.items():
        weights = [x[2] for x in items]
        chosen = {items[i] for i in
                  random.choices(range(len(items)), weights=weights,
                                 k=PER_QUARTER)}
        fresh = [x for x in chosen if (x[0], x[1]) not in done]
        todo = []
        reused = 0
        for x in fresh:
            repo, num, loc, frt, login, ai, ins = x
            d = reuse.get((repo, num))
            if d is not None:
                out.write(json.dumps({**d, "per": per, "loc": loc,
                                      "first_review": frt, "author": login,
                                      "ai": ai, "ins": ins}) + "\n")
                reused += 1
            else:
                todo.append(x)
        print(f"{per}: {reused} reused from hydration cache, "
              f"{len(todo)} to pull", flush=True)
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
                    res = _conn_commits(conn)
                    if res is None and (conn.get("pageInfo") or {}).get(
                            "hasNextPage") is True:
                        res = _all_commits(repo, num)
                    if res is None:
                        print(f"DEFER {repo}#{num}: incomplete commit "
                              "connection, not checkpointed", flush=True)
                        continue         # left out of `done`: retried later
                    commits, total = res
                    out.write(json.dumps({
                        "per": per, "repo": repo, "num": num, "loc": loc,
                        "first_review": frt, "author": login, "ai": ai,
                        "ins": ins, "commits": commits,
                        "commits_total": total, "commits_complete": True,
                    }) + "\n")
            time.sleep(1)
    print("REVIEW-ACTION PULL DONE", flush=True)


def _inv_pi(loc: float, W: float, k: int = PER_QUARTER) -> float:
    """Horvitz-Thompson weight under k PPS draws with replacement:
    1 / (1 - (1 - loc/W)^k)."""
    return 1.0 / (1.0 - (1.0 - loc / W) ** k)


def _conn_commits(conn: dict) -> tuple[list[dict], int] | None:
    """Validate a commits connection from the BATCH pull. Complete only
    when pageInfo is present with hasNextPage false, totalCount is an
    integer, and len(nodes) == totalCount — partial GraphQL responses
    (missing pageInfo/totalCount, short node lists) defer instead of
    checkpointing (external review P1, round 3)."""
    total = conn.get("totalCount")
    pi = conn.get("pageInfo")
    if not isinstance(total, int) or not isinstance(pi, dict) \
            or pi.get("hasNextPage") is not False:
        return None
    nodes = conn.get("nodes") or []
    return (nodes, total) if len(nodes) == total else None


def _suspect(d: dict) -> bool:
    """Record possibly truncated. Metadata-bearing records: suspect
    whenever commits_complete is not True, commits_total is missing, or
    len(commits) < commits_total — REGARDLESS of length (external review
    P1, round 3). Legacy records (no metadata): the old first:60 cap and
    exact page-boundary lengths."""
    if "commits_complete" in d or "commits_total" in d:
        total = d.get("commits_total")
        return (d.get("commits_complete") is not True
                or not isinstance(total, int)
                or len(d["commits"]) < total)
    n = len(d["commits"])
    return n >= 60 and (n == 60 or n % 100 == 0)


def repair() -> None:
    """Re-pull suspect records (old first:60 cap, page-boundary lengths
    without completeness metadata, or metadata-flagged short); appended
    records supersede (compute keeps the newest per PR). Failed re-pulls
    stay suspect and are retried on the next run."""
    recs = {}
    for ln in SAMPLE.read_text().splitlines():
        d = json.loads(ln)
        recs[(d["repo"], d["num"])] = d
    trunc = [d for d in recs.values() if _suspect(d)]
    print(f"{len(trunc)} suspect records to repair", flush=True)
    out = SAMPLE.open("a")
    for i, d in enumerate(trunc):
        full = _all_commits(d["repo"], d["num"])
        if full is None:
            print(f"SKIP {d['repo']}#{d['num']}: pull failed/incomplete",
                  flush=True)
            continue
        d["commits"], d["commits_total"] = full
        d["commits_complete"] = True
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
            c = classify_pr(p, MARKERS)
            anchors[(repo, p.get("number"))] = (
                first_human_ask(p), c.ai_reviewed)
            a = p.get("author") or {}
            if a.get("__typename") == "Bot":
                continue
            frt = first_human_review(p)
            loc = min((p.get("additions") or 0) + (p.get("deletions") or 0), CAP)
            if c.w8_mature and c.merged and c.human_reviewed and frt and loc:
                frame[(repo, p["number"])] = (per, loc)
                W[per] += loc

    def inv_pi(key) -> float:
        per, loc = frame[key]
        return _inv_pi(loc, W[per])

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
