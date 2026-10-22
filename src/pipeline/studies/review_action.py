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

Data: census cells lack per-commit dates/LOC, so this study owns SAMPLED
pulls — TWO designs over the same eligibility frame, each with its own
frame-fingerprinted manifest (atomically replaced on any frame change)
and hydrated sample file; the designs share the hydration cache, and the
v1 file is a read-only hydration cache:
- PPS-by-LOC (manifest_v2/sample_v2): 1,200 LOC-proportional draws per
  quarter with replacement, distinct PRs retained.
- EQUAL-PROBABILITY (manifest_eq_v1/sample_eq_v1): min(1,200, N)
  distinct PRs per quarter, uniform without replacement.

ESTIMATION (external review P1 fixes 2026-07-20; two-design split per
the issue #2 estimator review 2026-07-23):
- responded% (per-PR rate) comes from the EQ sample as an UNWEIGHTED
  share — uniform inclusion cancels in the ratio. It previously used HT
  weights over the PPS sample, where pi_i = 1-(1-w_i/W)^k makes tiny-LOC
  PRs dominate small lanes (measured: 39% of one 22-PR lane's weight on
  a single 75-LOC PR; the estimate swung tens of points between draws).
- post-ask LOC share% stays on the PPS sample as the ratio of
  HT-weighted LOC totals — the population LOC estimand that design is
  efficient for. Raw sample counts are printed alongside.
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
from pipeline.frame import CAP, PERIODS, ai_contrast_eligible, study_frame
from pipeline.ghx import graphql_envelope, graphql_nodes
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
# Second design over the SAME frame (issue #2 estimator review): the
# PPS-by-LOC sample is design-efficient for LOC-share estimands but its
# inverse-inclusion weights let tiny-LOC PRs dominate small RATE lanes
# (39% of one lane's weight on a single 75-LOC PR). Per-PR rate
# estimands (responded%) therefore come from this EQUAL-PROBABILITY
# companion sample: uniform pi cancels in the ratio, so rates are
# unweighted sample shares. Both designs share the hydration cache
# (commit data is a PR fact, independent of how the PR was drawn).
SAMPLE_EQ = Path("data/derived/review_action_sample_eq_v1.jsonl")
MANIFEST_EQ = Path("data/derived/review_action_manifest_eq_v1.json")
SEED = 20260630
PER_QUARTER = 1200
# Ceiling on documented unit nonresponse before publication is refused.
# Genuine nonresponse (repos privatized / PRs disabled after the census) has
# run 0.1-0.3%; the 2026-07-25 incident hit 27.9% because transient batch
# failures were tombstoned as permanent. See require_complete_sample.
MAX_NONRESPONSE = 0.02
# ...and at least this many stones, so the RATE is only consulted once it
# means something. A handful of genuine misses in a small selection is not
# a systemic-failure signature; 1,340 of 4,800 is.
MIN_NONRESPONSE_N = 20

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
    The API's totalCount may EXCEED the retrievable nodes, so a clean short
    walk is complete-as-retrievable (round 10). None on any actual failure —
    a failed page or a missing endCursor must never checkpoint as complete
    (round 3).

    WHY the shortfall (corrected 2026-07-26): this was read as force-pushed /
    rebased-away commits being counted but not served. Measured across both
    samples, it is overwhelmingly GitHub's hard **250-commit cap** per PR —
    every record claiming >250 retrieved exactly 250, and no record anywhere
    exceeds 250 (30 of ~8,960 analyzable records). The consequence is a
    TRUNCATION, not an accounting quirk: for those PRs, post-ask LOC sums at
    most 250 commits while the denominator is floored by the census LOC, so
    their post-ask LOC share is biased DOWN. Compare `commits_total` against
    `commits_api_total` to identify them."""
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
        if pi.get("hasNextPage") is False:
            break
        if pi.get("hasNextPage") is not True:
            return None                  # absent pageInfo is a PARTIAL
                                         # response, not the last page
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
    """Sampling frame: mature merged human-reviewed PRs, profile 'all' +
    ai_contrast_eligible (issue #2) — agent-authored PRs are in the frame
    (for them 'responsiveness' means the agent/operator pushes after a human
    ask), but non-AI bots and login-less authors are not: they would land in
    the CLEAN+nonAI lane and contaminate the comparison arm (2026-07-25
    review). MUST stay identical to the lane_rows frame or the manifest
    payload check fails. Fleet handling stays downstream (domain estimation
    in lane_rows)."""
    pool: dict[str, list] = {p: [] for p in PERIODS}
    for f in study_frame("all"):
        if not ai_contrast_eligible(f):
            continue
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
    for path in (OLD_SAMPLE, SAMPLE, SAMPLE_EQ):
        if not path.exists():
            continue
        for ln in path.read_text().splitlines():
            d = json.loads(ln)
            if _complete(d) or d.get("unretrievable") is True:
                cache[(d["repo"], d["num"])] = d
    return cache


def frame_fingerprint(items, design: str = "pps") -> str:
    """Hash of everything that determines the draw: config + the eligible
    (period, repo, num, loc) tuples. Non-PPS designs append their tag so
    the two manifests can never validate each other; the PPS formula is
    unchanged (existing fingerprints stay valid)."""
    import hashlib
    from pipeline.detect import AS_OF, CUTOFF
    parts = [AS_OF, CUTOFF, PER_QUARTER, SEED, sorted(items)]
    if design != "pps":
        parts.append(design)
    blob = json.dumps(parts, separators=(",", ":"))
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


def draw_eq(pool: dict) -> dict[str, list]:
    """Equal-probability draw (canonical, same normalization as draw):
    per period, min(PER_QUARTER, N) distinct PRs uniformly without
    replacement — pi = k/N for every PR, so rate estimands over this
    sample are plain unweighted shares. Seed stream is namespaced so the
    two designs' draws are independent."""
    out = {}
    for per in sorted(pool):
        items = sorted(pool[per], key=lambda x: (x[0], x[1], x[2]))
        if not items:
            continue
        rng = random.Random(f"{SEED}:eq:{per}")
        chosen = rng.sample(items, min(PER_QUARTER, len(items)))
        out[per] = sorted(chosen, key=lambda x: (x[0], x[1], x[2]))
    return out


def _selection_of(pool: dict, draw_fn=draw) -> dict:
    """The deterministic draw, reduced to selection IDENTITY only
    ([repo, num, loc]) — descriptive fields (first_review, ai, ins) are
    never persisted in the manifest; they are rebound from the current
    census at use time (round-7 review P1)."""
    return {per: [[x[0], x[1], x[2]] for x in xs]
            for per, xs in draw_fn(pool).items()}


def ensure_manifest(pool: dict, path: Path | None = None, draw_fn=draw,
                    design: str = "pps") -> tuple[dict, bool]:
    """Load the manifest if its fingerprint matches the CURRENT frame AND
    its payload equals the deterministic draw (a truncated/tampered
    payload with a valid fingerprint must be repaired, never reused
    vacuously — round-7 review P2); otherwise rewrite atomically."""
    path = MANIFEST if path is None else path
    fp = frame_fingerprint(_pool_items(pool), design)
    selected = _selection_of(pool, draw_fn)
    if path.exists():
        m = json.loads(path.read_text())
        if m.get("fingerprint") == fp and m.get("selected") == selected:
            return m, False
        if m.get("fingerprint") != fp:
            print(f"FRAME CHANGED: manifest {m.get('fingerprint')} -> {fp}; "
                  "redrawing selection", flush=True)
        else:
            print("MANIFEST PAYLOAD MISMATCH: repairing from the "
                  "deterministic draw", flush=True)
    m = {"fingerprint": fp, "selected": selected}
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(m))
    tmp.replace(path)
    return m, True


def _selected_keys(manifest: dict) -> dict:
    """(repo, num) -> per over the manifest selection."""
    return {(x[0], x[1]): per
            for per, xs in manifest["selected"].items() for x in xs}


def rebuild_sample(manifest: dict, cache: dict, pool: dict,
                   path: Path | None = None) -> set:
    """Atomically rewrite the sample file to exactly the manifest-selected
    keys with verified-complete records (commits from cache; descriptive
    fields REBOUND from the current pool — stale ai/first_review from an
    earlier census pass must not survive a marker or window revision).
    Returns the covered keys; everything else must be pulled."""
    path = SAMPLE if path is None else path
    current = {(x[0], x[1]): (per, x)
               for per, xs in pool.items() for x in xs}
    tmp = path.with_suffix(".tmp")
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
    tmp.replace(path)
    return done


def require_selection_matches(manifest: dict, pool: dict,
                              draw_fn=draw) -> None:
    """Compute-side guard (round-8 review P1): the manifest payload must
    equal the deterministic draw of the CURRENT pool — a
    fingerprint-matching manifest whose selection was truncated/tampered
    after the last pull would otherwise validate coverage vacuously."""
    if manifest.get("selected") != _selection_of(pool, draw_fn):
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


def _batch_data(query: str, design: str = "pps") -> tuple[dict | None, set]:
    """(data, tainted aliases) for one batch pull, read from the FULL
    envelope so the errors array is neither discarded nor — as after the
    2026-07-25 incident — reconstructed by guesswork (issue #3).

    Every error's type is LOGGED, so a recurrence is diagnosable from the
    pull log instead of inferred by re-running the batch afterwards. Every
    alias touched by a non-NOT_FOUND error is returned as TAINTED and must
    defer: an errored response can null a field anywhere beneath that alias,
    including inside an otherwise well-formed commits connection, and such a
    record would checkpoint `commits_complete: True` — which `_suspect`
    treats as clean, so neither a later pull nor `--repair` would ever
    revisit it. (Measured 2026-07-26: 0 null commit nodes in 92,515, so this
    is a latent hazard, not an observed loss.) An error with no usable path
    taints the whole batch. NOT_FOUND is exempt — it is the legitimate
    definitive signal, and `_confirm_gone` adjudicates it."""
    env = graphql_envelope(query)
    if env is None:
        return None, set()
    errs = env.get("errors") or []
    if errs:
        types = sorted({e.get("type") or "UNKNOWN" for e in errs})
        print(f"BATCH ERRORS ({design}): {len(errs)} {types}; paths="
              f"{[e.get('path') for e in errs][:4]}", flush=True)
    tainted = set()
    for e in errs:
        if (e.get("type") or "UNKNOWN") == "NOT_FOUND":
            continue
        path = e.get("path")
        tainted.add(path[0] if isinstance(path, list) and path else "*")
    data = env.get("data")
    return (data if isinstance(data, dict) else None), tainted


def _confirm_gone(repo: str, num: int) -> bool:
    """Single-PR verification, REQUIRED before writing a tombstone
    (2026-07-25 incident). A null alias in an 8-PR batch is not evidence of
    absence: a timed-out or rate-limited batch comes back with null aliases
    plus an errors array, and `graphql_nodes` discards errors — so 1,345
    live PRs (59 in vllm-project/vllm alone) were checkpointed as permanent
    nonresponse, 27.9% of the EQ selection, zeroing the Q2-2026 AI lane.

    True only when a dedicated query says the PR does not resolve AND every
    error is NOT_FOUND (the openai/plugins 'PRs disabled' case). Anything
    else — alive, RATE_LIMITED, a timeout, an unparseable response — is
    False, which DEFERS the PR to the next pull. Deferring costs one refetch;
    a false tombstone silently corrupts the sample."""
    o, n = repo.split("/", 1)
    env = graphql_envelope('query{ repository(owner:"%s", name:"%s"){ '
                           'pullRequest(number:%d){ number } } }'
                           % (o, n, num))
    if env is None:
        return False                     # no response: transient
    errs = env.get("errors") or []
    if any(e.get("type") != "NOT_FOUND" for e in errs):
        return False                     # rate limit / timeout / 502
    repo_node = (env.get("data") or {}).get("repository")
    if repo_node is None:
        return bool(errs)                # repo unresolvable: only w/ NOT_FOUND
    return repo_node.get("pullRequest") is None


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


def require_complete_sample(manifest: dict, records: dict,
                            design: str = "pps",
                            path: Path | None = None) -> None:
    """Fail-hard on coverage gaps. The design and its sample file are named
    because BOTH designs call this (2026-07-25 review): a hardcoded "PPS"
    sent the operator to the wrong file on an EQ-side gap."""
    gaps = coverage_gaps(manifest, records)
    if gaps:
        raise SystemExit(
            f"{design} sample incomplete ({path or SAMPLE}): {len(gaps)} "
            "selected PRs lack verified-complete records (e.g. "
            f"{gaps[:3]}) — rerun --pull/--repair; refusing to publish a "
            "non-probability subset (external review round 6)")
    sel = _selected_keys(manifest)
    stones = [k for k in sel
              if (records.get(k) or {}).get("unretrievable") is True]
    if (len(stones) >= MIN_NONRESPONSE_N
            and len(stones) / len(sel) > MAX_NONRESPONSE):
        raise SystemExit(
            f"{design} sample nonresponse too high ({path or SAMPLE}): "
            f"{len(stones)}/{len(sel)} = {100 * len(stones) / len(sel):.1f}%"
            f" tombstoned, ceiling {100 * MAX_NONRESPONSE:.0f}% (e.g. "
            f"{stones[:3]}) — documented nonresponse at this scale is still "
            "a non-probability subset. Genuine nonresponse has run 0.1-0.3%;"
            " this signature means a batch failure was recorded as "
            "permanent (2026-07-25 incident). Rerun --repair, which retries "
            "every tombstone, before publishing.")


def pull() -> None:
    pool = eligible()
    # Build the hydration cache ONCE, before any rebuild_sample prunes a
    # sample file: rebuild truncates SAMPLE to the PPS selection, so a PR
    # hydrated only there and drawn by the LATER design would otherwise be
    # gone from disk and re-fetched (2026-07-25 review). Commit data is a
    # PR-level fact, independent of which design drew it. The per-design
    # refresh is a UNION, so records pulled for an earlier design are
    # reused and nothing already cached is ever dropped.
    cache = _hydration_cache()
    for mpath, spath, draw_fn, design in (
            (MANIFEST, SAMPLE, draw, "pps"),
            (MANIFEST_EQ, SAMPLE_EQ, draw_eq, "eq")):
        print(f"=== design: {design} ===", flush=True)
        if not spath.exists():
            spath.touch()
        manifest, _fresh = ensure_manifest(pool, mpath, draw_fn, design)
        cache.update(_hydration_cache())
        done = rebuild_sample(manifest, cache, pool, spath)  # prunes stale
        _pull_missing(manifest, pool, spath, done, design)
    print("REVIEW-ACTION PULL DONE (coverage verified)", flush=True)


def _pull_missing(manifest: dict, pool: dict, spath: Path,
                  done: set, design: str = "pps") -> None:
    current = {(x[0], x[1]): x for xs in pool.values() for x in xs}
    out = spath.open("a")
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
            query = Q % " ".join(parts)
            data, tainted = _batch_data(query, design)
            if data is None:
                time.sleep(30)           # transient (rate/502): one retry
                data, tainted = _batch_data(query, design)
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
                if f"a{j}" in tainted or "*" in tainted:
                    print(f"DEFER {repo}#{num}: alias touched by a transient "
                          "batch error, not checkpointed", flush=True)
                    continue             # retried on the next pull
                node = data.get(f"a{j}")
                if _definitive_miss(node):
                    # a null alias is only a CANDIDATE miss — confirm with a
                    # single-PR query before making it permanent (2026-07-25)
                    if not _confirm_gone(repo, num):
                        print(f"DEFER {repo}#{num}: null alias unconfirmed "
                              "(transient batch failure), not tombstoned",
                              flush=True)
                        continue
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
    for ln in spath.read_text().splitlines():
        d = json.loads(ln)
        records[(d["repo"], d["num"])] = d
    require_complete_sample(manifest, records, design, spath)  # fail-hard


def _inv_pi(loc: float, W: float, k: int = PER_QUARTER) -> float:
    """Horvitz-Thompson weight under k PPS draws with replacement:
    1 / (1 - (1 - loc/W)^k)."""
    return 1.0 / (1.0 - (1.0 - loc / W) ** k)


def _conn_commits(conn: dict) -> tuple[list[dict], int, int] | None:
    """Validate a commits connection from the BATCH pull. Complete only
    when pageInfo is present with hasNextPage explicitly false and
    totalCount is an integer — a terminal page means everything the API
    serves was retrieved, even when short of totalCount (the 250-commit cap;
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
    """Re-pull suspect records in BOTH samples (old first:60 cap,
    page-boundary lengths without completeness metadata, or
    metadata-flagged short); appended records supersede (compute keeps
    the newest per PR). Failed re-pulls stay suspect and are retried on
    the next run."""
    for spath in (SAMPLE, SAMPLE_EQ):
        if spath.exists():
            _repair_sample(spath)
    print("REVIEW-ACTION REPAIR DONE", flush=True)


def _repair_sample(spath: Path) -> None:
    recs = {}
    for ln in spath.read_text().splitlines():
        d = json.loads(ln)
        recs[(d["repo"], d["num"])] = d
    trunc = [d for d in recs.values() if _suspect(d)]
    print(f"{spath.name}: {len(trunc)} suspect records to repair",
          flush=True)
    out = spath.open("a")
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
    out.close()


def _truncated(d: dict) -> bool:
    """Record whose commit list was cut short by GitHub's 250-commit-per-PR
    cap: the API claims more commits than it will serve. Measured 2026-07-26
    — every record claiming >250 retrieved exactly 250, and nothing anywhere
    exceeds 250 — so this is systematic truncation, not force-pushed commits
    being counted-but-not-served as previously documented."""
    got, api = d.get("commits_total"), d.get("commits_api_total")
    return isinstance(got, int) and isinstance(api, int) and got < api


def _author_edits_after(d: dict, anchor: str) -> tuple[int, int]:
    """(post_anchor_author_loc, total_commit_loc). Commits by bots OTHER
    than the PR author are excluded; the PR's OWN bot counts (issue #2:
    an agent-authored PR responds when the agent pushes). The census
    stores a Bot author without the [bot] suffix while commit-level
    logins carry it, so matching normalizes the suffix away."""
    def same(login: str | None) -> bool:
        return bool(login) and (login.removesuffix("[bot]")
                                == (d["author"] or "").removesuffix("[bot]"))
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
        if ("[bot]" in cl or cl.endswith("-bot")) and not same(cl):
            continue
        author_logins = {((x or {}).get("user") or {}).get("login")
                         for x in (cm.get("authors") or {}).get("nodes") or []}
        if not any(same(al) for al in author_logins):
            continue
        if (cm.get("committedDate") or "") > anchor:
            post += loc
    # Denominator: normally the census PR LOC is a FLOOR (a PR's diff can
    # exceed the summed commit LOC the API reports). But when the record is
    # TRUNCATED by GitHub's 250-commit-per-PR cap, the numerator can only
    # cover those 250 commits, so flooring with the whole-PR LOC would divide
    # a 250-commit numerator by a full-PR denominator and bias the share down
    # (2026-07-26 decision). Truncated records are measured against the LOC
    # of the very commits we have — reported as such in METHODS §5.
    if _truncated(d):
        return min(post, CAP), min(total, CAP)
    return min(post, CAP), min(max(total, d["loc"]), CAP)


def lane_rows() -> tuple[dict, dict, int]:
    """(lanes, lanes_nofleet, nonresponse): the lane accumulation used by
    compute() and Figure 8 — {(period, lane): {n, wn, wacted, n_loc,
    post, total}}. TWO designs over one frame (issue #2 estimator
    review): rate fields (n/wn/wacted) come from the EQ sample with UNIT
    weights (uniform inclusion cancels in the ratio — responded% is an
    unweighted share); LOC-share fields (n_loc/post/total) come from the
    PPS sample with HT weights (the estimand that design is efficient
    for). lanes_nofleet restricts both to PRs NOT authored by fleet
    operators — DOMAIN ESTIMATION over the same draws (inclusion
    probabilities unchanged; no redraw needed). Fail-hard semantics
    identical for both designs."""
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
            first_human_ask(p), c.ai_reviewed)   # anchors: EVERY PR
        frt = first_human_review(p)
        if not ai_contrast_eligible(f):
            continue          # frame members only; must match eligible()
        if c.w8_mature and c.merged and c.human_reviewed and frt and f.loc:
            frame[(f.repo, p["number"])] = (f.period, f.loc, frt, f.author,
                                            bool(c.ai_involved),
                                            bool(c.insider))
            W[f.period] += f.loc

    pool_now: dict = defaultdict(list)
    for (r, n), (per, loc, frt, login, ai, ins) in frame.items():
        pool_now[per].append((r, n, loc, frt, login, ai, ins))

    def load_design(mpath, spath, draw_fn, design):
        """Validate one design end-to-end (fingerprint, payload == draw,
        completeness) and return (analyzable keys, records, nonresponse)."""
        if not mpath.exists():
            raise SystemExit(f"no {design} selection manifest — "
                             "run --pull first")
        manifest = json.loads(mpath.read_text())
        fp = frame_fingerprint([(v[0], r, n, v[1])
                                for (r, n), v in frame.items()], design)
        if manifest.get("fingerprint") != fp:
            raise SystemExit(
                f"sampling frame changed ({design} manifest "
                f"{manifest.get('fingerprint')} != current {fp}) — rerun "
                "--pull to redraw before computing")
        require_selection_matches(manifest, pool_now, draw_fn)
        recs: dict = {}                  # newest record per PR wins (repair)
        for ln in spath.read_text().splitlines():
            d = json.loads(ln)
            recs[(d["repo"], d["num"])] = d
        require_complete_sample(manifest, recs, design, spath)
        selected = analyzable_keys(manifest, recs)
        nonresp = len(_selected_keys(manifest)) - len(selected)
        if nonresp:
            print(f"unit nonresponse ({design}): {nonresp} selected PRs "
                  f"({100 * nonresp / len(_selected_keys(manifest)):.1f}%) "
                  "unretrievable at hydration (repos privatized/PRs "
                  "disabled after the census) — excluded, weights "
                  "unchanged")
        return selected, recs, nonresp

    from pipeline.studies.productivity import fleet_logins
    fleet = fleet_logins()
    lanes = defaultdict(lambda: defaultdict(float))
    lanes_nf = defaultdict(lambda: defaultdict(float))

    def accumulate(selected, recs, rate: bool):
        """Rate fields (n/wn/wacted, unit weights) from the EQ sample;
        LOC-share fields (n_loc/post/total, HT weights) from PPS."""
        for key in selected:
            per, loc, frt, login, ai, _ins = frame[key]
            d = {**recs[key], "per": per, "first_review": frt,
                 "author": login, "ai": ai}   # census-derived, never stale
            ipw = 1.0 if rate else _inv_pi(loc, W[per])
            targets = [lanes] if login in fleet else [lanes, lanes_nf]
            ask, ai_rev = anchors.get(key, (None, None))
            cohorts = [(d["first_review"], "all-cause")]
            if ask:
                lane = "mixed" if ai_rev else "CLEAN"
                cohorts += [(ask, lane),
                            (ask, lane + ("+AI" if d["ai"] else "+nonAI"))]
            for anchor, coh in cohorts:
                post, total = _author_edits_after(d, anchor)
                for tgt in targets:
                    a = tgt[(d["per"], coh)]
                    if rate:
                        a["n"] += 1
                        a["wn"] += ipw
                        a["wacted"] += ipw * (post > 0)
                    else:
                        a["n_loc"] += 1
                        a["post"] += ipw * post
                        a["total"] += ipw * total

    sel_eq, recs_eq, nonresp_eq = load_design(MANIFEST_EQ, SAMPLE_EQ,
                                              draw_eq, "eq")
    accumulate(sel_eq, recs_eq, rate=True)
    sel_pps, recs_pps, nonresp_pps = load_design(MANIFEST, SAMPLE,
                                                 draw, "pps")
    accumulate(sel_pps, recs_pps, rate=False)
    return dict(lanes), dict(lanes_nf), nonresp_eq + nonresp_pps


def compute() -> None:
    lanes, lanes_nf, _nonresp = lane_rows()   # nonresponse printed above
    print("conditional responsiveness to HUMAN ASKS (changes-requested or "
          "inline comments)")
    print("CLEAN lane = no AI-reviewer activity (identified); "
          "mixed = descriptive; all-cause = companion only")
    print("two designs, one frame: responded% is the EQUAL-PROBABILITY "
          "sample share (uniform inclusion — unweighted); post-ask LOC "
          "share% is the HT-weighted ratio over the PPS-by-LOC sample "
          "(the estimand that design is efficient for)")
    for label, src in (("all sampled PRs", lanes),
                       ("FLEET-OPERATOR authors EXCLUDED (domain "
                        "estimation, same weights)", lanes_nf)):
        print(f"\n--- {label} ---")
        print(f"{'lane':22}{'PRs':>6}{'responded%':>11}"
              f"{'PRs':>6}{'post-ask LOC share%':>20}")
        for per in PERIODS:
            for coh in ("CLEAN", "CLEAN+AI", "CLEAN+nonAI", "mixed",
                        "all-cause"):
                a = src.get((per, coh))
                # each column gates on ITS OWN design's count (the two
                # draws are independent); the row prints if either design
                # supports its estimate, so no published figure point is
                # missing a table row (2026-07-25 review)
                rate_ok = a is not None and a.get("n", 0) >= 20
                loc_ok = (a is not None and a.get("n_loc", 0) >= 20
                          and a.get("total", 0) > 0)
                if not (rate_ok or loc_ok):
                    continue
                responded = (f"{100 * a['wacted'] / a['wn']:>10.1f}%"
                             if rate_ok else f"{'n/a':>11}")
                loc_share = (f"{100 * a['post'] / a['total']:>19.1f}%"
                             if loc_ok else f"{'n/a':>20}")
                print(f"{per + ' ' + coh:22}{int(a['n']):>6}{responded}"
                      f"{int(a.get('n_loc', 0)):>6}{loc_share}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pull", action="store_true")
    ap.add_argument("--repair", action="store_true")
    a = ap.parse_args()
    (pull if a.pull else repair if a.repair else compute)()


if __name__ == "__main__":
    main()
