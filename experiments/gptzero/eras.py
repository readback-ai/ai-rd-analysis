"""Paired arms beyond the v1 draw (design eras-v1): the within-author
contrast at 90 authors per quarter across Q4-2025, Q1-2026 and
Q2-2026, so detector score trends can be read across eras instead of
from a single quarter.

Each quarter is its own draw: authors with >=1 AI-marked and >=1
unmarked eligible PR in THAT quarter, one slot per arm per author, same
eligibility, LOC window, candidate ranking, and word caps as the v1
paired arm (sampling.eligible_item / sampling._candidates). Seed
streams are namespaced per quarter, so no draw shares randomness with
v1 or with another quarter; raising n_authors deepens a quarter without
disturbing its existing slots (whole-pool shuffle, then a prefix).

Q2-2026 is an EXPANSION of the v1 paired arm, not a redraw: the v1
authors are excluded here (their slots stay in the v1 manifest) and the
quarter's target is reduced by their count, so the pooled quarter is
n_authors distinct authors with every already-scored document retained.

Manifest: local/manifest_eras.json, same rebuild-don't-trust semantics,
fingerprinted over the pools AND the exclusion sets.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from pipeline.detect import AS_OF, CUTOFF
from pipeline.frame import study_frame

import sampling
from sampling import SEED

QUARTERS = ("Q4-2025", "Q1-2026", "Q2-2026")
PARAMS = dict(design="eras-v1", quarters=list(QUARTERS), n_authors=90,
              # per-quarter overrides: Q4-2025 to its pool cap (169
              # mixed authors exist), Q2-2026 to 180 (pool 1293);
              # Q1-2026 stays at the default
              quarter_targets={"Q4-2025": 169, "Q2-2026": 180},
              k_cand=16, word_cap=600, word_floor=100, min_loc=50,
              max_loc=2000)


def pools() -> dict:
    """One frame pass over QUARTERS, profile 'all':
    quarter -> author -> {"ai": [(repo, num, loc)...], "nonai": [...]}."""
    from pipeline.studies.productivity import fleet_logins
    fleet = fleet_logins()
    out: dict = {q: {} for q in QUARTERS}
    for f in study_frame("all", periods=QUARTERS):
        item = sampling.eligible_item(f, fleet)
        if item is None:
            continue
        arm = "ai" if f.cls.ai_involved else "nonai"
        out[f.period].setdefault(
            f.author, {"ai": [], "nonai": []})[arm].append(item)
    return out


def draw(pools_: dict, exclude: dict | None = None) -> list[dict]:
    """Deterministic slot list: per quarter, a seeded draw of mixed
    authors up to n_authors minus the quarter's excluded authors that
    its pool contains (each excluded author is a pair already sampled
    elsewhere — the quarter still totals n_authors). Slot ids carry the
    quarter so no id collides with v1's Q2-2026 slots."""
    exclude = exclude or {}
    slots = []
    for q in QUARTERS:
        excl = set(exclude.get(q, ()))
        rng = random.Random(f"{SEED}:gptzero:eras:{q}:paired")
        mixed = sorted(a for a, v in pools_[q].items()
                       if v["ai"] and v["nonai"])
        goal = PARAMS.get("quarter_targets", {}).get(
            q, PARAMS["n_authors"])
        take_n = goal - sum(1 for a in mixed if a in excl)
        rng.shuffle(mixed)
        # filter AFTER the whole-pool shuffle: the surviving order (and
        # so the drawn prefix) is stable under exclusion-set changes
        mixed = [a for a in mixed if a not in excl]
        for author in mixed[:max(take_n, 0)]:
            for arm in ("ai", "nonai"):
                crng = random.Random(
                    f"{SEED}:gptzero:eras:cand:{q}:{author}:{arm}")
                slots.append({
                    "slot": f"P:{q}:{author}:{arm}", "arm": "P",
                    "author": author, "period": q, "ai": arm == "ai",
                    "candidates": sampling._candidates(
                        crng, pools_[q][author][arm], PARAMS["k_cand"])})
    return slots


def fingerprint(pools_: dict, exclude: dict | None = None) -> str:
    items = []
    for q in QUARTERS:
        for a, v in sorted(pools_[q].items()):
            for arm in ("ai", "nonai"):
                items += [[q, a, arm, *t] for t in sorted(v[arm])]
    excl = {q: sorted(s) for q, s in (exclude or {}).items() if s}
    blob = json.dumps([AS_OF, CUTOFF, PARAMS, SEED, excl, items],
                      sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def ensure_manifest(pools_: dict, path: Path,
                    exclude: dict | None = None) -> tuple[dict, bool]:
    """Trust nothing: the stored manifest must equal a fresh redraw
    (fingerprint AND payload), else it is rewritten atomically."""
    want = {"design": PARAMS["design"],
            "fingerprint": fingerprint(pools_, exclude),
            "params": PARAMS, "slots": draw(pools_, exclude)}
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
