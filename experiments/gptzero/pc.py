"""Positive-control arm (design pc-v1): agent-authored PRs.

Layer-B PRs — authored by a CANONICAL coding agent
(detect.AGENT_PR_AUTHORS via cls.agent_author; Dependabot/CI/release
automation never qualifies, marker or not) — are as close to known
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

from pipeline.detect import AS_OF, CUTOFF
from pipeline.frame import study_frame

from sampling import SEED

QUARTERS = ("Q4-2025", "Q1-2026", "Q2-2026")
PARAMS = dict(design="pc-v2", quarters=list(QUARTERS),
              n_per_agent_quarter=5, per_group=3, k_cand=8,
              extra_cand=4, word_cap=600, word_floor=100, min_loc=50,
              max_loc=2000)


def _raw_loc(pr: dict) -> int:
    return (pr.get("additions") or 0) + (pr.get("deletions") or 0)


def pools() -> dict:
    """quarter -> (agent, repo) -> [(repo, num, loc)...] over PRs whose
    author is a canonical coding agent (cls.agent_author — the study's
    layer-B allowlist), merged + w8-mature, raw LOC inside the
    window."""
    out: dict = {q: {} for q in QUARTERS}
    for f in study_frame("all", periods=QUARTERS):
        if f.cls.agent_author is None:
            continue
        if not (f.cls.merged and f.cls.w8_mature):
            continue
        loc = _raw_loc(f.pr)
        if not (PARAMS["min_loc"] <= loc <= PARAMS["max_loc"]):
            continue
        out[f.period].setdefault((f.cls.agent_author, f.repo), []).append(
            (f.repo, f.pr["number"], loc))
    return out


def _group_shuffle(q: str, login: str, repo: str,
                   prs: list) -> list[list]:
    """The group's full seeded PR shuffle — one stream per group, so
    every slot of the group draws disjoint candidate chunks from the
    same ordering (slot 0's chunk is identical to the pc-v1 list)."""
    crng = random.Random(f"{SEED}:gptzero:pc:cand:{q}:{login}:{repo}")
    order = sorted(prs)
    crng.shuffle(order)
    return [list(p) for p in order]


def _chunk(order: list[list], k: int) -> list[list]:
    """Slot k's candidate chunk: the first k_cand PRs for slot 0
    (pc-v1 compatible), then disjoint extra_cand-sized chunks."""
    kc, ec = PARAMS["k_cand"], PARAMS["extra_cand"]
    if k == 0:
        return order[:kc]
    start = kc + (k - 1) * ec
    return order[start:start + ec]


def draw(pools_: dict) -> list[dict]:
    """Deterministic slot list: per quarter, walk the seeded group
    shuffle giving each agent one slot per group up to
    n_per_agent_quarter documents; agents short on repos (devin's
    concentration, cursor/claude scarcity) then take extra slots on
    already-selected groups — up to per_group per repo, each with a
    disjoint candidate chunk — until the target or the pool runs out.
    Slot 0 of a group keeps the pc-v1 id and candidate list, so
    already-scored documents survive the deepening."""
    slots = []
    for q in QUARTERS:
        rng = random.Random(f"{SEED}:gptzero:pc:{q}")
        keys = sorted(pools_[q])
        rng.shuffle(keys)
        docs: Counter = Counter()
        chosen: list[tuple[str, str, list]] = []
        for login, repo in keys:
            if docs[login] >= PARAMS["n_per_agent_quarter"]:
                continue
            order = _group_shuffle(q, login, repo,
                                   pools_[q][(login, repo)])
            slots.append({
                "slot": f"PC:{q}:{login}:{repo}", "arm": "PC",
                "author": login, "period": q, "ai": True,
                "candidates": _chunk(order, 0)})
            chosen.append((login, repo, order))
            docs[login] += 1
        for k in range(1, PARAMS["per_group"]):
            for login, repo, order in chosen:
                if docs[login] >= PARAMS["n_per_agent_quarter"]:
                    continue
                cands = _chunk(order, k)
                if not cands:
                    continue
                slots.append({
                    "slot": f"PC:{q}:{login}:{repo}:{k}", "arm": "PC",
                    "author": login, "period": q, "ai": True,
                    "candidates": cands})
                docs[login] += 1
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
