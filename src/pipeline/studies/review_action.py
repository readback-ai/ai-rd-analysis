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
PRs retained). The selection lives in review_action_manifest_v2.json
(frame-fingerprinted, atomically replaced on any frame change); hydrated
records in review_action_sample_v2.jsonl; the v1 file is a read-only
hydration cache.

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

from pipeline.detect import split_reviews
from pipeline.frame import CAP, PERIODS, study_frame
from pipeline.ghx import graphql_nodes
# v2: redrawn under the MATURE-GATED eligibility frame (2026-07-24) — HT
# inclusion probabilities are only valid for records drawn from the frame
# they are computed on. The v1 file remains solely as a hydration cache
# (commit data is frame-independent PR fact; selection is not).
SAMPLE = Path("data/derived/review_action_sample_v2.jsonl")
OLD_SAMPLE = Path("data/derived/review_action_sample.jsonl")
# Selection manifest: binds the drawn keys to a FRAME FINGERPRINT so a
# frame change (AS_OF bump, eligibility, weights, population) atomically
# REPLACES the selection instead of unioning two draws, and coverage can
# be verified fail-hard (external review round 6).
MANIFEST = Path("data/derived/review_action_manifest_v2.json")
SEED = 20260630
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


def _all_commits(repo: str, num: int) -> tuple[list[dict], int, int] | None:
    """Paginated fetch of ALL commits for one PR (saturation follow-up).
    Returns (nodes, retrieved, api_total) after a CLEAN TERMINAL WALK —
    every page succeeded and the last page reported hasNextPage=false.
    The API's totalCount may EXCEED the retrievable nodes (force-pushed /
    rebased-away commits are counted but never served; measured:
    NVIDIA-NeMo/Speech#8622 serves 250 of a claimed 281), so a clean
    short walk is complete-as-retrievable (round 10). None on any actual
    failure — a failed page or a missing endCursor must never checkpoint
    as complete (round 3)."""
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
            time.sleep(30)               # transient (rate/502): one retry
            conn = graphql_nodes(q, {},
                                 ".data.repository.pullRequest.commits",
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
    if not isinstance(total, int):
        return None                      # partial response: no API claim
    return nodes, len(nodes), total


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
    """Sampling frame: mature merged human-reviewed PRs, profile 'all'
    (issue #2) — agent-authored PRs are in the frame; for them
    'responsiveness' means the agent/operator pushes after a human ask.
    Fleet handling stays downstream (domain estimation in lane_rows)."""
    pool: dict[str, list] = {p: [] for p in PERIODS}
    for f in study_frame("all"):
        c = f.cls
        frt = first_human_review(f.pr)
        if c.w8_mature and c.merged and c.human_reviewed and frt and f.loc:
            pool[f.period].append((f.repo, f.pr["number"], f.loc, frt,
                                   f.author, bool(c.ai_involved),
                                   bool(c.insider)))
    return pool


def _complete(d: dict) -> bool:
    """STRICT completeness: explicit metadata only. Legacy records without
    it are never reusable — a pre-metadata partial response has no
    page-boundary signature (external review round 6)."""
    total = d.get("commits_total")
    return (d.get("commits_complete") is True and isinstance(total, int)
            and len(d.get("commits") or []) == total)


def _hydration_cache() -> dict:
    """(repo, num) -> verified-COMPLETE commit records from any prior
    sample file — reusable because commit data is a PR-level fact
    independent of the sampling frame; only the DRAW must come from the
    current frame."""
    cache = {}
    for path in (OLD_SAMPLE, SAMPLE):
        if not path.exists():
            continue
        for ln in path.read_text().splitlines():
            d = json.loads(ln)
            if _complete(d) or d.get("unretrievable") is True:
                cache[(d["repo"], d["num"])] = d
    return cache


def frame_fingerprint(items) -> str:
    """Hash of everything that determines the draw: config + the eligible
    (period, repo, num, loc) tuples."""
    import hashlib
    from pipeline.detect import AS_OF, CUTOFF
    blob = json.dumps([AS_OF, CUTOFF, PER_QUARTER, SEED,
                       sorted(items)], separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def _pool_items(pool: dict) -> list:
    return [(per, x[0], x[1], x[2]) for per, xs in pool.items() for x in xs]


def draw(pool: dict) -> dict[str, list]:
    """Deterministic PPS draw (seeded, LOC-proportional, distinct),
    CANONICAL under encounter order (round-9 review P1): periods iterate
    sorted, items sort by (repo, num, loc) before weights are assigned,
    each period gets its own derived RNG stream, and empty periods are
    normalized away — pull (PERIODS dict order) and compute (census
    encounter order) reconstruct identical selections from identical
    frames."""
    out = {}
    for per in sorted(pool):
        items = sorted(pool[per], key=lambda x: (x[0], x[1], x[2]))
        if not items:
            continue
        rng = random.Random(f"{SEED}:{per}")
        weights = [x[2] for x in items]
        chosen = {items[i] for i in
                  rng.choices(range(len(items)), weights=weights,
                              k=PER_QUARTER)}
        out[per] = sorted(chosen, key=lambda x: (x[0], x[1], x[2]))
    return out


def _selection_of(pool: dict) -> dict:
    """The deterministic draw, reduced to selection IDENTITY only
    ([repo, num, loc]) — descriptive fields (first_review, ai, ins) are
    never persisted in the manifest; they are rebound from the current
    census at use time (round-7 review P1)."""
    return {per: [[x[0], x[1], x[2]] for x in xs]
            for per, xs in draw(pool).items()}


def ensure_manifest(pool: dict) -> tuple[dict, bool]:
    """Load the manifest if its fingerprint matches the CURRENT frame AND
    its payload equals the deterministic draw (a truncated/tampered
    payload with a valid fingerprint must be repaired, never reused
    vacuously — round-7 review P2); otherwise rewrite atomically."""
    fp = frame_fingerprint(_pool_items(pool))
    selected = _selection_of(pool)
    if MANIFEST.exists():
        m = json.loads(MANIFEST.read_text())
        if m.get("fingerprint") == fp and m.get("selected") == selected:
            return m, False
        if m.get("fingerprint") != fp:
            print(f"FRAME CHANGED: manifest {m.get('fingerprint')} -> {fp}; "
                  "redrawing selection", flush=True)
        else:
            print("MANIFEST PAYLOAD MISMATCH: repairing from the "
                  "deterministic draw", flush=True)
    m = {"fingerprint": fp, "selected": selected}
    tmp = MANIFEST.with_suffix(".tmp")
    tmp.write_text(json.dumps(m))
    tmp.replace(MANIFEST)
    return m, True


def _selected_keys(manifest: dict) -> dict:
    """(repo, num) -> per over the manifest selection."""
    return {(x[0], x[1]): per
            for per, xs in manifest["selected"].items() for x in xs}


def rebuild_sample(manifest: dict, cache: dict, pool: dict) -> set:
    """Atomically rewrite SAMPLE to exactly the manifest-selected keys
    with verified-complete records (commits from cache; descriptive
    fields REBOUND from the current pool — stale ai/first_review from an
    earlier census pass must not survive a marker or window revision).
    Returns the covered keys; everything else must be pulled."""
    current = {(x[0], x[1]): (per, x)
               for per, xs in pool.items() for x in xs}
    tmp = SAMPLE.with_suffix(".tmp")
    done = set()
    with tmp.open("w") as out:
        for key in _selected_keys(manifest):
            d = cache.get(key)
            cur = current.get(key)
            if d is None or cur is None or not (
                    _complete(d) or d.get("unretrievable") is True):
                continue
            per, (repo, num, loc, frt, login, ai, ins) = cur
            out.write(json.dumps({**d, "per": per, "loc": loc,
                                  "first_review": frt, "author": login,
                                  "ai": ai, "ins": ins}) + "\n")
            done.add(key)
    tmp.replace(SAMPLE)
    return done


def require_selection_matches(manifest: dict, pool: dict) -> None:
    """Compute-side guard (round-8 review P1): the manifest payload must
    equal the deterministic draw of the CURRENT pool — a
    fingerprint-matching manifest whose selection was truncated/tampered
    after the last pull would otherwise validate coverage vacuously."""
    if manifest.get("selected") != _selection_of(pool):
        raise SystemExit(
            "manifest selection does not match the deterministic draw of "
            "the current frame — rerun --pull before computing")


def _definitive_miss(node) -> bool:
    """A SUCCESSFUL batch response carrying an explicit null repository or
    null pullRequest: the entity is gone from the live API (repo
    privatized/deleted, or PRs disabled after the census — measured:
    openai/plugins disabled PRs 2026-07-14). Definitive nonresponse, as
    opposed to a transient failure (whole-response None), which defers."""
    if node is None:
        return True
    return isinstance(node, dict) and node.get("pullRequest") is None


def _tombstone(per: str, x) -> dict:
    """Record of DEFINITIVE nonresponse for a selected PR: resolves
    coverage as documented unit nonresponse (~0.5% of the selection),
    never analyzed as data, retried by --repair in case retrievability
    returns."""
    repo, num, loc, frt, login, ai, ins = x
    return {"per": per, "repo": repo, "num": num, "loc": loc,
            "first_review": frt, "author": login, "ai": ai, "ins": ins,
            "commits": [], "unretrievable": True,
            "commits_complete": False}


def coverage_gaps(manifest: dict, records: dict) -> list:
    """Selected keys without a verified-complete record OR a documented
    nonresponse tombstone."""
    return [k for k in _selected_keys(manifest)
            if k not in records
            or not (_complete(records[k])
                    or records[k].get("unretrievable") is True)]


def analyzable_keys(manifest: dict, records: dict) -> list:
    """Selected keys with actual data (tombstoned nonresponse excluded)."""
    return [k for k in _selected_keys(manifest)
            if _complete(records.get(k) or {})]


def require_complete_sample(manifest: dict, records: dict) -> None:
    gaps = coverage_gaps(manifest, records)
    if gaps:
        raise SystemExit(
            f"PPS sample incomplete: {len(gaps)} selected PRs lack "
            f"verified-complete records (e.g. {gaps[:3]}) — rerun "
            "--pull/--repair; refusing to publish a non-probability "
            "subset (external review round 6)")


def pull() -> None:
    pool = eligible()
    manifest, fresh = ensure_manifest(pool)
    cache = _hydration_cache()
    done = rebuild_sample(manifest, cache, pool)  # idempotent, prunes stale
    current = {(x[0], x[1]): x for xs in pool.values() for x in xs}
    out = SAMPLE.open("a")
    for per, xs in manifest["selected"].items():
        todo = [current[(x[0], x[1])] for x in xs
                if (x[0], x[1]) not in done and (x[0], x[1]) in current]
        print(f"{per}: {sum(1 for x in xs if (x[0], x[1]) in done)} "
              f"covered, {len(todo)} to pull", flush=True)
        for i in range(0, len(todo), 8):
            chunk = todo[i:i + 8]
            parts = []
            for j, (repo, num, *_rest) in enumerate(chunk):
                o, n = repo.split("/", 1)
                parts.append(f'a{j}: repository(owner:"{o}", name:"{n}")'
                             + FIELDS % num)
            data = graphql_nodes(Q % " ".join(parts), {}, ".data", expect=dict)
            if data is None:
                time.sleep(30)           # transient (rate/502): one retry
                data = graphql_nodes(Q % " ".join(parts), {}, ".data",
                                     expect=dict)
            if data is None:
                # a chunk of HEAVY PRs can 502 as a batch while each PR
                # serves fine alone (census small-page lesson): fall back
                # to per-PR paginated pulls before deferring
                print(f"CHUNK FAILED after retry: {len(chunk)} PRs — "
                      "falling back to per-PR pulls", flush=True)
                for repo, num, loc, frt, login, ai, ins in chunk:
                    full = _all_commits(repo, num)
                    if full is None:
                        print(f"DEFER {repo}#{num}: per-PR pull failed",
                              flush=True)
                        continue
                    commits, retrieved, api_total = full
                    out.write(json.dumps({
                        "per": per, "repo": repo, "num": num, "loc": loc,
                        "first_review": frt, "author": login, "ai": ai,
                        "ins": ins, "commits": commits,
                        "commits_total": retrieved,
                        "commits_api_total": api_total,
                        "commits_complete": True,
                    }) + "\n")
                    time.sleep(1)
                continue
            for j, (repo, num, loc, frt, login, ai, ins) in enumerate(chunk):
                node = data.get(f"a{j}")
                if _definitive_miss(node):
                    print(f"NONRESPONSE {repo}#{num}: gone from the live "
                          "API (tombstoned)", flush=True)
                    out.write(json.dumps(_tombstone(
                        per, (repo, num, loc, frt, login, ai, ins))) + "\n")
                    continue
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
                    commits, retrieved, api_total = res
                    out.write(json.dumps({
                        "per": per, "repo": repo, "num": num, "loc": loc,
                        "first_review": frt, "author": login, "ai": ai,
                        "ins": ins, "commits": commits,
                        "commits_total": retrieved,
                        "commits_api_total": api_total,
                        "commits_complete": True,
                    }) + "\n")
            time.sleep(1)
    out.close()
    records = {}
    for ln in SAMPLE.read_text().splitlines():
        d = json.loads(ln)
        records[(d["repo"], d["num"])] = d
    require_complete_sample(manifest, records)   # fail-hard, nonzero
    print("REVIEW-ACTION PULL DONE (coverage verified)", flush=True)


def _inv_pi(loc: float, W: float, k: int = PER_QUARTER) -> float:
    """Horvitz-Thompson weight under k PPS draws with replacement:
    1 / (1 - (1 - loc/W)^k)."""
    return 1.0 / (1.0 - (1.0 - loc / W) ** k)


def _conn_commits(conn: dict) -> tuple[list[dict], int, int] | None:
    """Validate a commits connection from the BATCH pull. Complete only
    when pageInfo is present with hasNextPage explicitly false and
    totalCount is an integer — a terminal page means everything the API
    serves was retrieved, even when short of totalCount (ghost commits;
    see _all_commits). Partial responses (missing pageInfo/totalCount)
    defer instead of checkpointing (rounds 3/10)."""
    total = conn.get("totalCount")
    pi = conn.get("pageInfo")
    if not isinstance(total, int) or not isinstance(pi, dict) \
            or pi.get("hasNextPage") is not False:
        return None
    nodes = conn.get("nodes") or []
    return nodes, len(nodes), total


def _suspect(d: dict) -> bool:
    """Record possibly truncated. Metadata-bearing records: suspect
    whenever commits_complete is not True, commits_total is missing, or
    len(commits) < commits_total — REGARDLESS of length (external review
    P1, round 3). Legacy records (no metadata): the old first:60 cap and
    exact page-boundary lengths."""
    if d.get("unretrievable") is True:
        return True                       # nonresponse: retried by repair
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
            if d.get("unretrievable") is True:
                out.write(json.dumps(d) + "\n")   # still gone: keep stone
            else:
                print(f"SKIP {d['repo']}#{d['num']}: pull failed/incomplete",
                      flush=True)
            continue
        d.pop("unretrievable", None)
        d["commits"], d["commits_total"], d["commits_api_total"] = full
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


def lane_rows() -> tuple[dict, dict, int]:
    """(lanes, lanes_nofleet, nonresponse): the lane accumulation used by
    compute() and Figure 8 — {(period, lane): {n, wn, wacted, post,
    total}} with HT weights applied. lanes_nofleet restricts to PRs NOT
    authored by fleet operators — DOMAIN ESTIMATION over the same PPS
    draw (inclusion probabilities unchanged; no redraw needed). Fail-hard
    semantics identical to compute()."""
    from collections import defaultdict
    # one census pass: ask anchors + lane flags + the PPS sampling frame
    # (per-PR LOC weights and quarter LOC totals for inclusion probs).
    # Profile "all" throughout (issue #2): anchors from EVERY PR, and
    # agent-authored PRs are frame members like eligible().
    anchors: dict = {}
    # (repo, num) -> (per, loc, frt, login, ai, ins): every descriptive
    # field derives from THIS census pass — sampled records supply only
    # commit data, so a marker/window revision can never leave stale
    # ai/first_review values in the analysis (round-7 review P1)
    frame: dict = {}
    W: dict = defaultdict(float)         # per -> total eligible LOC
    for f in study_frame("all"):
        p, c = f.pr, f.cls
        anchors[(f.repo, p.get("number"))] = (
            first_human_ask(p), c.ai_reviewed)
        frt = first_human_review(p)
        if c.w8_mature and c.merged and c.human_reviewed and frt and f.loc:
            frame[(f.repo, p["number"])] = (f.period, f.loc, frt, f.author,
                                            bool(c.ai_involved),
                                            bool(c.insider))
            W[f.period] += f.loc

    def inv_pi(key) -> float:
        per, loc = frame[key][:2]
        return _inv_pi(loc, W[per])

    # BIND to the selection manifest: the sample is only a valid PPS draw
    # of THIS frame if the fingerprints match, and only publishable if
    # every selected key has a verified-complete record (round 6).
    if not MANIFEST.exists():
        raise SystemExit("no selection manifest — run --pull first")
    manifest = json.loads(MANIFEST.read_text())
    fp = frame_fingerprint([(v[0], r, n, v[1])
                            for (r, n), v in frame.items()])
    if manifest.get("fingerprint") != fp:
        raise SystemExit(
            f"sampling frame changed (manifest {manifest.get('fingerprint')}"
            f" != current {fp}) — rerun --pull to redraw before computing")
    pool_now: dict = defaultdict(list)
    for (r, n), (per, loc, frt, login, ai, ins) in frame.items():
        pool_now[per].append((r, n, loc, frt, login, ai, ins))
    require_selection_matches(manifest, pool_now)
    recs: dict = {}                      # newest record per PR wins (repair)
    for ln in SAMPLE.read_text().splitlines():
        d = json.loads(ln)
        recs[(d["repo"], d["num"])] = d
    require_complete_sample(manifest, recs)
    selected = analyzable_keys(manifest, recs)
    nonresp = len(_selected_keys(manifest)) - len(selected)
    if nonresp:
        print(f"unit nonresponse: {nonresp} selected PRs "
              f"({100 * nonresp / len(_selected_keys(manifest)):.1f}%) "
              "unretrievable at hydration (repos privatized/PRs disabled "
              "after the census) — excluded, HT weights unchanged")
    from pipeline.studies.productivity import fleet_logins
    fleet = fleet_logins()
    lanes = defaultdict(lambda: defaultdict(float))
    lanes_nf = defaultdict(lambda: defaultdict(float))
    for key in selected:
        d = recs[key]
        per, _loc, frt, login, ai, _ins = frame[key]
        d = {**d, "per": per, "first_review": frt, "author": login,
             "ai": ai}                    # census-derived, never stale
        ipw = inv_pi(key)
        targets = [lanes] if login in fleet else [lanes, lanes_nf]
        ask, ai_rev = anchors.get(key, (None, None))
        # descriptive companion: all-cause (any-review anchor)
        post, total = _author_edits_after(d, d["first_review"])
        for tgt in targets:
            a = tgt[(d["per"], "all-cause")]
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
            for tgt in targets:
                a = tgt[(d["per"], coh)]
                a["n"] += 1
                a["wn"] += ipw
                a["wacted"] += ipw * (post > 0)
                a["post"] += ipw * post
                a["total"] += ipw * total
    return dict(lanes), dict(lanes_nf), nonresp


def compute() -> None:
    lanes, lanes_nf, _nonresp = lane_rows()   # nonresponse printed above
    print("conditional responsiveness to HUMAN ASKS (changes-requested or "
          "inline comments)")
    print("CLEAN lane = no AI-reviewer activity (identified); "
          "mixed = descriptive; all-cause = companion only")
    print("HT inclusion-probability weighted (PPS sample -> population "
          "estimands): responded% is PR-weighted; LOC share% is the "
          "population post-ask LOC ratio")
    for label, src in (("all sampled PRs", lanes),
                       ("FLEET-OPERATOR authors EXCLUDED (domain "
                        "estimation, same HT weights)", lanes_nf)):
        print(f"\n--- {label} ---")
        print(f"{'lane':22}{'PRs':>6}{'responded%':>11}"
              f"{'post-ask LOC share%':>20}")
        for per in PERIODS:
            for coh in ("CLEAN", "CLEAN+AI", "CLEAN+nonAI", "mixed",
                        "all-cause"):
                a = src.get((per, coh))
                if not a or a["n"] < 20:
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
