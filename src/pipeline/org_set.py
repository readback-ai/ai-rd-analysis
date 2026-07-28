"""Stage 0 — HOW THE POPULATION IS DEFINED. Five rules, one override table.

Inputs (data/sources/ — third-party snapshots, transcriptions, declarations):
  lfai_orgs.txt, hf_orgs.tsv, gh_topic_orgs.txt   ecosystem candidate lists
  epoch_org_map.tsv                Epoch notable-models orgs -> GitHub handles
                                   (epoch.ai CC-BY; snapshot in epoch/)
  techcrunch_ai_orgs.tsv           rote transcription of TechCrunch's 2025
                                   $100M+ AI funding round-up
  curated_orgs.tsv                 declared hand-curated remainder (~33 labs
                                   on neither Epoch nor TechCrunch)
  candidates.tsv                   ecosystem-list handle-transcription record
  conglomerates.txt                declared umbrella orgs -> repo-scoped
  org_overrides.tsv                published adjudications (exclude AI-users /
                                   include topic-sparse AI developers)

Derived inputs (data/derived/ — machine-generated scans):
  org_scale.tsv, top5_topics.jsonl (stars + maintainer-topic AI-ness of each
  org's top-5 repos), ai_scan.tsv / recheck_scan.tsv / branch_scan.tsv /
  census_org_evidence.json (AI-evidence layers).

THE RULES (docs/METHODS.md section 1):
  R1 candidates = union of the five lists.
  R2 quality    = flagship repo >=1k stars; AI-developer-list members exempt
                  (those lists already vet significance).
  R3 identity   = AI developer iff on Epoch/TechCrunch/curated list OR >=2 of
                  top-5 repos carry maintainer AI topics (AI_TOPICS dict).
  R4 evidence   = >=5 AI-evidence PRs/commits across the three detection
                  layers, or >=0.1% of PRs, summed over the sampled quarters.
  R5 scope      = developers enter FULL-ORG except declared conglomerates
                  (repo-scoped); non-developers with a >=1k-star AI-topic
                  flagship enter repo-scoped; all else out.
Overrides apply last (exclude beats everything; include-full asserts R3).

Output: data/derived/population.tsv (org, scope, why, top5_ai).
`why` is the ADMISSION reason with priority override > dev-list > top5:N —
it says which rule admitted the org, NOT how AI-concentrated its portfolio
is. `top5_ai` records the measured concentration (count of top-5 starred
repos with AI topics) for every org regardless of admission path; slice
groupings (studies.slices) use top5_ai, not why.

Usage:
  python -m pipeline.org_set            # write population.tsv, print summary
  python -m pipeline.org_set --verify   # source/rule reconciliation report
  python -m pipeline.org_set --explain ORG
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

SRC = Path("data/sources")
DRV = Path("data/derived")

FLAGSHIP_MIN_STARS = 1000
KEEP_MIN_EVIDENCE = 5
KEEP_MIN_PR_RATE = 0.001
TOP5_MIN_AI = 2

# Maintainer-declared AI topics (frozen; anchored to GitHub's curated topic
# vocabulary; generic/gameable terms like "agents" deliberately excluded).
AI_TOPICS = {
    "machine-learning", "deep-learning", "artificial-intelligence", "ai",
    "neural-network", "neural-networks", "llm", "llms", "large-language-models",
    "nlp", "natural-language-processing", "computer-vision",
    "reinforcement-learning", "generative-ai", "transformers",
    "diffusion-models", "ai-agents", "mlops", "speech-recognition",
    "text-to-speech", "llmops", "language-model", "gpt", "chatgpt",
    "stable-diffusion", "rag", "fine-tuning", "model-serving",
}


def _lines(path: Path) -> list[str]:
    return [ln for ln in path.read_text().splitlines()
            if ln.strip() and not ln.startswith("#")]


# ------------------------------------------------------------------ inputs

def candidate_sources() -> dict[str, set[str]]:
    """canonical handle -> source tags. Ecosystem lists come via the
    transcription record; developer lists via their own files."""
    canon: dict[str, str] = {}

    def C(o: str) -> str:
        return canon.setdefault(o.lower(), o)

    tags: dict[str, set[str]] = defaultdict(set)
    for ln in _lines(SRC / "candidates.tsv"):
        o, t = ln.split("\t")
        tags[C(o)].update(t.split("|"))
    for ln in _lines(SRC / "epoch_org_map.tsv"):
        _, h = ln.split("\t")
        if h != "-":
            tags[C(h)].add("epoch")
    for ln in _lines(SRC / "techcrunch_ai_orgs.tsv"):
        tags[C(ln.split("\t")[0])].add("techcrunch")
    for ln in _lines(SRC / "curated_orgs.tsv"):
        tags[C(ln.split("\t")[0])].add("curated")
    return dict(tags)


def top5() -> dict[str, list[dict]]:
    out = {}
    for ln in (DRV / "top5_topics.jsonl").read_text().splitlines():
        d = json.loads(ln)
        out[d["org"].lower()] = d["top5"]
    return out


def evidence() -> tuple[dict[str, int], set[str]]:
    """org(lower) -> evidence count, max across layers so no PR counts
    twice across sources; plus rate-branch set. Within a source the same
    rule holds: R4's threshold is a DISTINCT-AI-evidence-PR count.
    - recheck probes overlap (one PR can match its branch AND its
      markers), so an org's recheck evidence is its max probe count.
    - branch_scan cells are keyed (dedups re-appended checkpoint rows)
      and sum exactly: quarters partition PRs by created date and the
      prefixes are pairwise non-nested. Q1-2024 is the false-positive
      control and never counts toward admission."""
    ev: dict[str, int] = defaultdict(int)
    for ln in _lines(DRV / "ai_scan.tsv"):
        f = ln.split("\t")
        ev[f[0].lower()] = max(ev[f[0].lower()], int(f[1]))
    rc: dict[str, int] = defaultdict(int)
    for ln in _lines(DRV / "recheck_scan.tsv"):
        o, probe, n = ln.split("\t")
        if probe != "total_pr":
            rc[o.lower()] = max(rc[o.lower()], int(n))
    for o, n in rc.items():
        ev[o] = max(ev[o], n)
    br_cells: dict[tuple[str, str, str], int] = {}
    for ln in _lines(DRV / "branch_scan.tsv"):
        f = ln.split("\t")
        if len(f) == 4 and f[1] != "Q1-2024":
            br_cells[(f[0].lower(), f[1], f[2])] = int(f[3])
    br: dict[str, int] = defaultdict(int)
    for (o, _per, _pfx), n in br_cells.items():
        br[o] += n
    for o, n in br.items():
        ev[o] = max(ev[o], n)
    rate_ok = set()
    cens = json.loads((DRV / "census_org_evidence.json").read_text())
    for o, (e, t) in cens.items():
        ev[o] = max(ev[o], e)
        if t and e >= 1 and e / t >= KEEP_MIN_PR_RATE:
            rate_ok.add(o)
    return dict(ev), rate_ok


def stars_ok_set() -> set[str]:
    ok = set()
    for ln in _lines(DRV / "org_scale.tsv")[1:]:
        f = ln.split("\t")
        if len(f) >= 3 and f[2].isdigit() and int(f[2]) >= FLAGSHIP_MIN_STARS:
            ok.add(f[0].lower())
    for o, t5 in top5().items():
        if t5 and t5[0]["stars"] >= FLAGSHIP_MIN_STARS:
            ok.add(o)
    return ok


def overrides() -> dict[str, tuple[str, str]]:
    out = {}
    for ln in _lines(SRC / "org_overrides.tsv"):
        f = ln.split("\t")
        out[f[0].lower()] = (f[1], f[2] if len(f) > 2 else "")
    return out


# ------------------------------------------------------------------ engine

def build() -> dict[str, tuple[str, str, int]]:
    """org -> (scope, why, top5_ai); scope in {full, repo}."""
    cand = candidate_sources()
    dev_lists = {o.lower() for o, tags in cand.items()
                 if tags & {"epoch", "techcrunch", "curated"}}
    t5 = top5()
    ev, rate_ok = evidence()
    stars = stars_ok_set()
    conglomerates = {o.lower() for o in _lines(SRC / "conglomerates.txt")}
    ovr = overrides()

    pop: dict[str, tuple[str, str, int]] = {}
    for org in sorted(cand, key=str.lower):
        lo = org.lower()
        o_action = ovr.get(lo, ("", ""))[0]
        if o_action == "exclude":
            continue
        if lo not in stars and lo not in dev_lists:
            continue                                     # R2
        if ev.get(lo, 0) < KEEP_MIN_EVIDENCE and lo not in rate_ok:
            continue                                     # R4
        n5 = sum(r["ai"] for r in t5.get(lo, []))
        is_dev = (lo in dev_lists or n5 >= TOP5_MIN_AI
                  or o_action == "include-full")         # R3
        if lo in conglomerates:                          # R5
            pop[org] = ("repo", "conglomerate", n5)
        elif is_dev:
            why = ("override" if o_action == "include-full" else
                   "dev-list" if lo in dev_lists else f"top5:{n5}")
            pop[org] = ("full", why, n5)
        elif t5.get(lo) and any(r["ai"] and r["stars"] >= FLAGSHIP_MIN_STARS
                                for r in t5[lo]):
            pop[org] = ("repo", "ai-flagship", n5)
    return pop


def population(scope: str | None = None) -> list[str]:
    """Orgs from data/derived/population.tsv (generated by main())."""
    out = []
    for ln in _lines(DRV / "population.tsv"):
        f = ln.split("\t")
        if scope is None or f[1] == scope:
            out.append(f[0])
    return out


def scoped_repos() -> dict[str, list[str]]:
    """org -> its in-scope repos, for every repo-scoped population org
    (population_repos.txt filtered by owner). Layer-C scans and samples
    take these instead of org-wide queries: a repo-scoped org's universe
    is its AI-topic repos only (R5), matching the census."""
    owners = {o.lower(): o for o in population(scope="repo")}
    out: dict[str, list[str]] = defaultdict(list)
    for r in _lines(DRV / "population_repos.txt"):
        org = owners.get(r.split("/", 1)[0].lower())
        if org:
            out[org].append(r)
    return dict(out)


def verify() -> None:
    """Reconciliation report: source sizes, rule pass counts, scope split."""
    cand = candidate_sources()
    from collections import Counter
    src_counts = Counter(t for tags in cand.values() for t in tags)
    print("source tags:", dict(src_counts))
    print(f"candidates (union): {len(cand)}")
    pop = build()
    scopes = Counter(s for s, *_ in pop.values())
    whys = Counter(w for _, w, *_ in pop.values())
    print(f"population: {len(pop)} = {dict(scopes)}; admission reasons: {dict(whys)}")
    disk = set(population())
    if disk != set(pop):
        print(f"WARN population.tsv is STALE: +{sorted(set(pop) - disk)[:5]} "
              f"-{sorted(disk - set(pop))[:5]} (rerun `python -m pipeline.org_set`)")
    else:
        print("population.tsv matches a fresh build")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--explain", metavar="ORG")
    ap.add_argument("--verify", action="store_true")
    a = ap.parse_args()
    if a.verify:
        verify()
        return
    pop = build()
    if a.explain:
        lo = a.explain.lower()
        hit = {o: v for o, v in pop.items() if o.lower() == lo}
        print(hit or f"{a.explain}: NOT in population")
        return
    with (DRV / "population.tsv").open("w") as f:
        f.write("# GENERATED by pipeline.org_set — do not edit. "
                "org\tscope\twhy(admission)\ttop5_ai(measured)\n")
        for org, (scope, why, n5) in pop.items():
            f.write(f"{org}\t{scope}\t{why}\t{n5}\n")
    full = sum(1 for s, *_ in pop.values() if s == "full")
    print(f"population: {len(pop)} orgs = {full} full + {len(pop) - full} repo-scoped "
          f"-> data/derived/population.tsv")


if __name__ == "__main__":
    main()
