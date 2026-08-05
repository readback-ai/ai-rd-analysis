"""Positive-control arm (design pc-v1): agent-authored PRs.

Layer-B PRs — authored by coding-agent accounts (GitHub App authors or
user-typed bot logins) with AI involvement — are as close to known
machine-written code as the study can sample. Scoring them through the
SAME document pipeline validates the instrument: if the detector cannot
flag these, "GPTZero misses AI code" explains the paired-arm results;
if it can, the marked/unmarked convergence reads as disclosure
collapse. The arm's score level is also the ceiling against which the
paired arms' mixtures are interpreted.

Draw: per quarter, one slot per (agent login, repo) group — a seeded
whole-pool shuffle of group keys with a per-login cap so no single
agent dominates — and each slot's candidates are a seeded shuffle of
the group's PRs. Same LOC window, word caps, and candidate semantics
as the paired arms; the human/fleet hygiene is deliberately ABSENT
(bots are the point).

Manifest: local/manifest_pc.json, rebuild-don't-trust, fingerprinted
over the pools.
"""
from __future__ import annotations

import hashlib
import json
import random
from collections import Counter
from pathlib import Path

from pipeline.detect import AS_OF, CUTOFF, is_bot_login
from pipeline.frame import study_frame

import sampling
from sampling import SEED

QUARTERS = ("Q1-2026", "Q2-2026")
PARAMS = dict(design="pc-v1", quarters=list(QUARTERS), n_per_quarter=15,
              max_per_login=5, k_cand=8, word_cap=600, word_floor=100,
              min_loc=50, max_loc=2000)


def _raw_loc(pr: dict) -> int:
    return (pr.get("additions") or 0) + (pr.get("deletions") or 0)


def pools() -> dict:
    """quarter -> (login, repo) -> [(repo, num, loc)...] over
    AI-involved agent-authored PRs (App author or bot login), merged +
    w8-mature, raw LOC inside the window."""
    out: dict = {q: {} for q in QUARTERS}
    for f in study_frame("all", periods=QUARTERS):
        if not f.cls.ai_involved:
            continue
        if not (f.bot_author
                or (f.author and is_bot_login(f.author))):
            continue
        if not (f.cls.merged and f.cls.w8_mature):
            continue
        loc = _raw_loc(f.pr)
        if not (PARAMS["min_loc"] <= loc <= PARAMS["max_loc"]):
            continue
        login = f.author or "(app)"
        out[f.period].setdefault((login, f.repo), []).append(
            (f.repo, f.pr["number"], loc))
    return out


def draw(pools_: dict) -> list[dict]:
    """Deterministic slot list: per quarter, up to n_per_quarter
    (login, repo) groups from a seeded whole-pool shuffle, at most
    max_per_login groups per agent login."""
    slots = []
    for q in QUARTERS:
        rng = random.Random(f"{SEED}:gptzero:pc:{q}")
        keys = sorted(pools_[q])
        rng.shuffle(keys)
        per_login: Counter = Counter()
        taken = 0
        for login, repo in keys:
            if taken >= PARAMS["n_per_quarter"]:
                break
            if per_login[login] >= PARAMS["max_per_login"]:
                continue
            crng = random.Random(
                f"{SEED}:gptzero:pc:cand:{q}:{login}:{repo}")
            slots.append({
                "slot": f"PC:{q}:{login}:{repo}", "arm": "PC",
                "author": login, "period": q, "ai": True,
                "candidates": sampling._candidates(
                    crng, pools_[q][(login, repo)], PARAMS["k_cand"])})
            per_login[login] += 1
            taken += 1
    return slots


def fingerprint(pools_: dict) -> str:
    items = []
    for q in QUARTERS:
        for (login, repo), prs in sorted(pools_[q].items()):
            items += [[q, login, repo, *t] for t in sorted(prs)]
    blob = json.dumps([AS_OF, CUTOFF, PARAMS, SEED, items],
                      sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def ensure_manifest(pools_: dict, path: Path) -> tuple[dict, bool]:
    """Trust nothing: the stored manifest must equal a fresh redraw
    (fingerprint AND payload), else it is rewritten atomically."""
    want = {"design": PARAMS["design"],
            "fingerprint": fingerprint(pools_),
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
