"""Sampling for the GPTZero code-diff calibration (design v1-50k).

Author-centric, deterministic, versioned. Three arms:
  P  — paired Q2-2026: authors with >=1 AI and >=1 non-AI eligible PR,
       one slot per arm per author (within-author contrast).
  B1 — persistent Q1-2024: Arm-P authors also eligible in Q1-2024
       (same-author-across-eras anchor; same-repo candidates first).
  B2 — independent Q1-2024: authors not in B1, one slot each.

Every slot carries a RANKED CANDIDATE list (<= k_cand PRs): the fetch
stage promotes the first candidate whose assembled document clears the
word floor, so over-drawing spends GitHub calls, never GPTZero words.

Humans only: a paired-author design needs attributable people, so
layer-B bot logins are excluded even though ai_contrast_eligible admits
them (the study's headline A∪B∪C label is therefore sampled A∪C-heavy
here — recorded as a caveat by analyze). Fleet operators excluded per
the study convention for author-level analyses.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from pipeline.detect import AS_OF, CUTOFF, is_bot_login
from pipeline.frame import ai_contrast_eligible, study_frame

SEED = 20260630
PARAMS = dict(design="v1-50k", n_authors=30, n_q1=20, n_b1=10, k_cand=16,
              word_cap=600, word_floor=100, min_loc=50, max_loc=2000)


def _raw_loc(pr: dict) -> int:
    return (pr.get("additions") or 0) + (pr.get("deletions") or 0)


def eligible_item(f, fleet: set) -> tuple | None:
    """(repo, num, raw_loc) when the PR clears the paired-design
    eligibility — human author (no bot login), non-fleet, merged +
    w8-mature, raw additions+deletions inside the [min_loc, max_loc]
    window — else None. Every paired arm (any quarter) uses exactly
    this filter."""
    if not ai_contrast_eligible(f):
        return None
    if f.bot_author or not f.author or is_bot_login(f.author):
        return None
    if f.author in fleet:
        return None
    if not (f.cls.merged and f.cls.w8_mature):
        return None
    loc = _raw_loc(f.pr)
    if not (PARAMS["min_loc"] <= loc <= PARAMS["max_loc"]):
        return None
    return (f.repo, f.pr["number"], loc)


def pools() -> dict:
    """One frame pass over Q1-2024 + Q2-2026, profile 'all'.
    q2: author -> {"ai": [(repo, num, loc)...], "nonai": [...]};
    q1: author -> [(repo, num, loc)...] (unmarked only — the baseline arm
    is unmarked by definition)."""
    from pipeline.studies.productivity import fleet_logins
    fleet = fleet_logins()
    q2: dict = {}
    q1: dict = {}
    for f in study_frame("all", periods=("Q1-2024", "Q2-2026")):
        item = eligible_item(f, fleet)
        if item is None:
            continue
        if f.period == "Q1-2024":
            if not f.cls.ai_involved:
                q1.setdefault(f.author, []).append(item)
        else:
            arm = "ai" if f.cls.ai_involved else "nonai"
            q2.setdefault(f.author, {"ai": [], "nonai": []})[arm]\
                .append(item)
    return {"q2": q2, "q1": q1}


def _candidates(rng: random.Random, prs: list, k: int) -> list[list]:
    """Seeded shuffle of the WHOLE pool, then a k-prefix: the ordering is
    stable under changes to k, so deepening the candidate pool refills
    unfilled slots without disturbing already-fetched ones."""
    order = sorted(prs)
    rng.shuffle(order)
    return [list(p) for p in order[:k]]


def draw(pools_: dict) -> list[dict]:
    """Deterministic slot list for the manifest. Seed streams are
    namespaced per design so v2 draws share nothing with v1."""
    rng = random.Random(f"{SEED}:gptzero:v1:paired")
    mixed = sorted(a for a, v in pools_["q2"].items()
                   if v["ai"] and v["nonai"])
    rng.shuffle(mixed)
    take = mixed[:PARAMS["n_authors"]]
    slots = []
    for author in take:
        for arm in ("ai", "nonai"):
            crng = random.Random(f"{SEED}:gptzero:v1:cand:{author}:{arm}")
            slots.append({
                "slot": f"P:{author}:{arm}", "arm": "P", "author": author,
                "period": "Q2-2026", "ai": arm == "ai",
                "candidates": _candidates(
                    crng, pools_["q2"][author][arm], PARAMS["k_cand"])})
    b1_authors = [a for a in take if pools_["q1"].get(a)][:PARAMS["n_b1"]]
    for author in b1_authors:
        crng = random.Random(f"{SEED}:gptzero:v1:cand:{author}:q1")
        q2_repos = {r for arm in ("ai", "nonai")
                    for r, _n, _l in pools_["q2"][author][arm]}
        order = sorted(pools_["q1"][author])
        crng.shuffle(order)
        # same-repo priority on the FULL ordering, before slicing —
        # sorting a slice would let a deeper k reorder the prefix
        order.sort(key=lambda t: t[0] not in q2_repos)
        cands = [list(p) for p in order[:PARAMS["k_cand"]]]
        slots.append({
            "slot": f"B1:{author}", "arm": "B1", "author": author,
            "period": "Q1-2024", "ai": False,
            "same_repo": bool(cands and cands[0][0] in q2_repos),
            "candidates": cands})
    rng2 = random.Random(f"{SEED}:gptzero:v1:q1")
    # B2 is the INDEPENDENT baseline: exclude every paired author, not
    # just the B1 subset — a paired author past the B1 cap is still not
    # independent of Arm P
    rest = sorted(a for a in pools_["q1"] if a not in set(take))
    n_b2 = max(PARAMS["n_q1"] - len(b1_authors), 0)
    for author in rng2.sample(rest, min(n_b2, len(rest))):
        crng = random.Random(f"{SEED}:gptzero:v1:cand:{author}:q1")
        slots.append({
            "slot": f"B2:{author}", "arm": "B2", "author": author,
            "period": "Q1-2024", "ai": False,
            "candidates": _candidates(
                crng, pools_["q1"][author], PARAMS["k_cand"])})
    return slots


def fingerprint(pools_: dict) -> str:
    items = []
    for a, v in sorted(pools_["q2"].items()):
        for arm in ("ai", "nonai"):
            items += [["q2", a, arm, *t] for t in sorted(v[arm])]
    for a, prs in sorted(pools_["q1"].items()):
        items += [["q1", a, *t] for t in sorted(prs)]
    blob = json.dumps([AS_OF, CUTOFF, PARAMS, SEED, items],
                      sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def ensure_manifest(pools_: dict, path: Path) -> tuple[dict, bool]:
    """Trust nothing: the stored manifest must equal a fresh redraw
    (fingerprint AND payload), else it is rewritten atomically."""
    want = {"design": PARAMS["design"], "fingerprint": fingerprint(pools_),
            "params": PARAMS, "slots": draw(pools_)}
    if path.is_file():
        try:
            if json.loads(path.read_text()) == want:
                return want, False
        except json.JSONDecodeError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(want, indent=1))
    tmp.replace(path)
    return want, True
