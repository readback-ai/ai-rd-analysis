"""Arm B3 — Q3-2022 era baseline (last full quarter before ChatGPT).

No census exists for 2022, so this arm has its own draw path: a seeded
PPS-by-precount draw of repos (one document per repo, for author
diversity), one search page per drawn repo, and node-side eligibility
(merged, human author, LOC window — the frame's helpers need census
cells, so the same hygiene applies directly to pulled nodes). Everything
downstream — candidate ranking, fetch, documents, scoring — is the
shared pipeline. Scores here are near-pure false-positive calibration:
Q3-2022 code cannot be LLM-written in any meaningful volume.

Determinism: repo draw and candidate ranking are seeded; search pages
are cached forever (the era is immutable), so the draw is reproducible
given the page cache. Manifest: local/manifest_b3.json, same
rebuild-don't-trust semantics, fingerprinted over the precount pool.
"""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

from pipeline.detect import is_bot_login
from pipeline.ghx import graphql_nodes
from pipeline.precount import get_precount

from sampling import SEED

RANGE = "2022-07-01..2022-09-30"
PERIOD = "Q3-2022"
B3_PARAMS = dict(design="v1-50k-b3", n_docs=26, k_cand=8, spare=15,
                 min_repo_prs=20, min_loc=50, max_loc=2000)

PAGE_QUERY = ("query($q:String!){ search(query:$q, type:ISSUE, "
              "first:50){ nodes{ ... on PullRequest{ number createdAt "
              "mergedAt additions deletions "
              "author{login __typename} } } } }")


def repo_pool(population_repos_path: Path) -> dict[str, int]:
    """repo -> Q3-2022 precount, over population repos at or above the
    activity floor (a page of a near-empty repo wastes a draw)."""
    pool = {}
    for ln in population_repos_path.read_text().splitlines():
        repo = ln.strip()
        if not repo:
            continue
        n = get_precount(repo, PERIOD)
        if n is not None and n >= B3_PARAMS["min_repo_prs"]:
            pool[repo] = n
    return pool


def draw_repos(pool: dict[str, int]) -> list[str]:
    """Seeded PPS-without-replacement ranked list, n_docs + spare long —
    spares stand in when a repo's page yields no eligible candidate."""
    rng = random.Random(f"{SEED}:gptzero:v1:b3")
    remaining = dict(sorted(pool.items()))
    picked: list[str] = []
    want = B3_PARAMS["n_docs"] + B3_PARAMS["spare"]
    while remaining and len(picked) < want:
        total = sum(remaining.values())
        shot = rng.uniform(0, total)
        acc = 0.0
        for repo, n in remaining.items():
            acc += n
            if shot <= acc:
                picked.append(repo)
                del remaining[repo]
                break
    return picked


def fetch_page(repo: str, cache_dir: Path) -> list[dict] | None:
    """One 50-PR page (created-desc) for the quarter, cached forever."""
    p = cache_dir / f"{repo.replace('/', '~')}.json"
    if p.is_file():
        return json.loads(p.read_text())
    nodes = graphql_nodes(
        PAGE_QUERY,
        {"q": f"repo:{repo} is:pr created:{RANGE} sort:created-desc"},
        ".data.search.nodes", expect=list)
    if nodes is None:
        return None
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(nodes))
    tmp.replace(p)
    return nodes


def eligible_nodes(nodes: list[dict]) -> list[tuple[str, int, int]]:
    """Node-side hygiene mirroring the frame's rules: merged, human
    author with a real non-bot login, raw LOC inside the window.
    Returns (author, num, loc) tuples."""
    out = []
    for n in nodes:
        if not isinstance(n, dict) or not n.get("mergedAt"):
            continue
        a = n.get("author") or {}
        login = a.get("login")
        if a.get("__typename") != "User" or not login \
                or is_bot_login(login):
            continue
        loc = (n.get("additions") or 0) + (n.get("deletions") or 0)
        if not (B3_PARAMS["min_loc"] <= loc <= B3_PARAMS["max_loc"]):
            continue
        out.append((login, int(n["number"]), loc))
    return out


def slots_for(ranked_repos: list[str], pages: dict[str, list[dict]]) \
        -> list[dict]:
    """One slot per repo, first n_docs repos with any eligible node;
    one document per author across the whole arm (diversity). The
    slot's author is drawn FIRST (seeded shuffle) and its candidates
    are that author's PRs only, so a floor miss during fetch can only
    promote another PR by the same author — the recorded author is the
    document's author by construction."""
    slots: list[dict] = []
    used_authors: set[str] = set()
    for repo in ranked_repos:
        if len(slots) >= B3_PARAMS["n_docs"]:
            break
        nodes = pages.get(repo)
        if not nodes:
            continue
        elig = [(a, num, loc) for a, num, loc in eligible_nodes(nodes)
                if a not in used_authors]
        if not elig:
            continue
        crng = random.Random(f"{SEED}:gptzero:v1:cand:{repo}:b3")
        order = sorted(elig)
        crng.shuffle(order)
        author = order[0][0]
        cands = [t for t in order
                 if t[0] == author][:B3_PARAMS["k_cand"]]
        used_authors.add(author)
        slots.append({
            "slot": f"B3:{repo}", "arm": "B3", "author": author,
            "period": PERIOD, "ai": False,
            "candidates": [[repo, num, loc] for _a, num, loc in cands]})
    return slots


def fingerprint(pool: dict[str, int]) -> str:
    blob = json.dumps([RANGE, B3_PARAMS, SEED, sorted(pool.items())],
                      sort_keys=True)
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


def ensure_manifest(pool: dict[str, int],
                    pages: dict[str, list[dict]],
                    path: Path) -> tuple[dict, bool]:
    want = {"design": B3_PARAMS["design"], "fingerprint": fingerprint(pool),
            "params": {**B3_PARAMS, "word_cap": 600, "word_floor": 100},
            "slots": slots_for(draw_repos(pool), pages)}
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
