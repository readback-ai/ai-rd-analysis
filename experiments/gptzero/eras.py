"""Paired arms for earlier quarters (design eras-v1): the Q2-2026
within-author contrast re-drawn at the same depth in Q4-2025 and
Q1-2026, so detector score trends can be read across eras instead of
from a single quarter.

Each quarter is its own draw: authors with >=1 AI-marked and >=1
unmarked eligible PR in THAT quarter, one slot per arm per author, same
eligibility, LOC window, candidate ranking, and word caps as the v1
paired arm (sampling.eligible_item / sampling._candidates). Seed
streams are namespaced per quarter, so no draw shares randomness with
v1 or with another quarter, and deepening one quarter never disturbs
another.

Manifest: local/manifest_eras.json, same rebuild-don't-trust semantics,
fingerprinted over both quarters' pools.
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

QUARTERS = ("Q4-2025", "Q1-2026")
PARAMS = dict(design="eras-v1", quarters=list(QUARTERS), n_authors=30,
              k_cand=8, word_cap=600, word_floor=100, min_loc=50,
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


def draw(pools_: dict) -> list[dict]:
    """Deterministic slot list: per quarter, a seeded draw of up to
    n_authors mixed authors, one slot per arm per author. Slot ids carry
    the quarter so no id collides with v1's Q2-2026 slots."""
    slots = []
    for q in QUARTERS:
        rng = random.Random(f"{SEED}:gptzero:eras:{q}:paired")
        mixed = sorted(a for a, v in pools_[q].items()
                       if v["ai"] and v["nonai"])
        rng.shuffle(mixed)
        for author in mixed[:PARAMS["n_authors"]]:
            for arm in ("ai", "nonai"):
                crng = random.Random(
                    f"{SEED}:gptzero:eras:cand:{q}:{author}:{arm}")
                slots.append({
                    "slot": f"P:{q}:{author}:{arm}", "arm": "P",
                    "author": author, "period": q, "ai": arm == "ai",
                    "candidates": sampling._candidates(
                        crng, pools_[q][author][arm], PARAMS["k_cand"])})
    return slots


def fingerprint(pools_: dict) -> str:
    items = []
    for q in QUARTERS:
        for a, v in sorted(pools_[q].items()):
            for arm in ("ai", "nonai"):
                items += [[q, a, arm, *t] for t in sorted(v[arm])]
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
