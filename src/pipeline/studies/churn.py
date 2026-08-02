"""Study: code churn — lines deleted relative to lines added in merged code.

External claim under test (industry report, quoted 2026-08-02): "Code
churn, the ratio of lines deleted to lines added for merged code in a
given quarter, has increased 861% under high AI adoption. At nearly 10
times the prior rate, significantly more code is being removed relative
to what is being added." Replication question: does deleted:added over
merged code move anything like 861% (x9.6) in this population between the
Q1-2024 baseline and the high-AI-adoption quarters?

PILOT design (2026-08-02, pre-commitment to a full study):

1. `--table census` — the claim's own metric needs no collection at all:
   census cells already carry per-PR additions/deletions, so the
   deleted:added ratio over mature merged PRs is computed on the COMPLETE
   census (pooled; capped companion guards mega-PR domination). Arms:
   all / AI-involved / non-AI, non-AI bots dropped (ai_contrast_eligible),
   so all = AI + nonAI exactly.

2. `--draw` / `--pull` / `--table sample` — a balanced ~0.1% seeded
   sample of the same frame (equal AI / nonAI per period = deliberate
   AI oversampling; Q1-2024 backfills from nonAI since no AI PRs exist)
   hydrated with per-FILE additions/deletions, so the ratio can be
   recomputed EXCLUDING generated content (lockfiles/vendored/minified/
   protobuf/snapshots/svg/notebooks — the METHODS 5b objection: deleted
   lockfiles could manufacture churn). Files are capped at first
   FILES_PAGE per PR; truncated records are flagged, kept, and reported.

3. `--pull-incidents` / `--table incidents` — incidents per merged PR,
   piloted on the sample's repos: GH issues labeled bug (`label:bug` only
   — the dominant convention; repos using other label taxonomies read as
   zero, a documented pilot limitation) CREATED in the quarter, divided
   by the repo's mature merged PRs that quarter. Repos split into
   high-AI / low-AI halves by their Q2-2026 AI-involvement share.

Not (yet) in the generated report; pilot numbers carry no frozen-
convention guarantees beyond the frame they share with every study
(w8 maturity, LOC cap, population manifest).
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from pathlib import Path
from random import Random

from pipeline.analyze import bootstrap_ci, weighted_mean
from pipeline.frame import ai_contrast_eligible, study_frame
from pipeline.ghx import graphql_nodes, rest_count
from pipeline.scan_orgs import QUARTER_RANGES

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
SEED = 20260630
SAMPLE_RATE = 0.001          # ~0.1% of the eligible merged frame
MIN_PRS = 5                  # repo floor per (period, arm), house convention
FILES_PAGE = 100             # per-PR file-list cap (one page; no pagination)
CAP = 20_000                 # per-side LOC cap for the capped companion
SAMPLE = Path("data/derived/churn_sample_v1.jsonl")
INCIDENTS = Path("data/derived/churn_incidents_v1.jsonl")
BUG_LABEL = "bug"

# Generated-content path patterns (mirrors the METHODS 5b hygiene classes;
# the loc-hygiene sample's generator predates the repo, so the list lives
# here for this study).
_GEN = re.compile(
    r"(^|/)(package-lock\.json|yarn\.lock|pnpm-lock\.yaml|poetry\.lock|"
    r"uv\.lock|cargo\.lock|composer\.lock|gemfile\.lock|go\.sum|"
    r"flake\.lock|packages\.lock\.json)$"
    r"|(^|/)(vendor|vendors|third_party|thirdparty|node_modules|dist|"
    r"build|out)/"
    r"|\.(min\.js|min\.css|pb\.go|pb\.cc|pb\.h|snap|svg|ipynb|lock)$"
    r"|_pb2(_grpc)?\.pyi?$|\.generated\.|(^|/)generated/",
    re.IGNORECASE)


def is_generated(path: str) -> bool:
    return bool(_GEN.search(path or ""))


# ------------------------------------------------------------------ frame

def eligible() -> dict[str, list]:
    """period -> [(repo, num, ai, additions, deletions)] over mature merged
    PRs, profile 'all' + ai_contrast_eligible (non-AI bots dropped, so the
    nonAI arm is human-authored and all = AI + nonAI)."""
    pool: dict[str, list] = {p: [] for p in PERIODS}
    for f in study_frame("all"):
        if not ai_contrast_eligible(f):
            continue
        c = f.cls
        if not (c.w8_mature and c.merged):
            continue
        pool[f.period].append(
            (f.repo, f.pr["number"], bool(c.ai_involved),
             int(f.pr.get("additions") or 0),
             int(f.pr.get("deletions") or 0)))
    return pool


# ------------------------------------------------------------ census table

def _ratio(adds: int, dels: int) -> float:
    return dels / adds if adds else float("nan")


def census_rows(pool: dict[str, list]) -> dict[tuple[str, str], dict]:
    """(period, arm) -> pooled churn: n, madds/mdels (raw + capped),
    deleted:added ratio, median per-PR ratio, share of PRs deleting more
    than they add."""
    out: dict[tuple[str, str], dict] = {}
    for per, items in pool.items():
        arms = {"all": items,
                "AI": [x for x in items if x[2]],
                "nonAI": [x for x in items if not x[2]]}
        for arm, xs in arms.items():
            if not xs:
                continue
            adds = sum(x[3] for x in xs)
            dels = sum(x[4] for x in xs)
            cadds = sum(min(x[3], CAP) for x in xs)
            cdels = sum(min(x[4], CAP) for x in xs)
            per_pr = sorted(x[4] / max(x[3], 1) for x in xs)
            out[(per, arm)] = {
                "n": len(xs), "adds": adds, "dels": dels,
                "ratio": _ratio(adds, dels),
                "ratio_capped": _ratio(cadds, cdels),
                "median_pr": per_pr[len(per_pr) // 2],
                "del_dominant": sum(1 for x in xs if x[4] > x[3]) / len(xs),
            }
    return out


def repo_pairs(pool: dict[str, list]) -> dict[tuple[str, str], list]:
    """(period, arm) -> [(repo_ratio, repo)] for the CW series: per repo,
    capped-side deletions / capped-side additions over its arm PRs;
    qualifies at >= MIN_PRS PRs and nonzero additions (a repo whose arm
    added nothing has no defined ratio — skipped, never zeroed)."""
    acc: dict[tuple[str, str, str], list[int]] = defaultdict(lambda: [0, 0, 0])
    for per, items in pool.items():
        for repo, _num, ai, adds, dels in items:
            for arm in ("all", "AI" if ai else "nonAI"):
                a = acc[(per, arm, repo)]
                a[0] += min(adds, CAP)
                a[1] += min(dels, CAP)
                a[2] += 1
    out: dict[tuple[str, str], list] = defaultdict(list)
    for (per, arm, repo), (adds, dels, n) in sorted(acc.items()):
        if n >= MIN_PRS and adds > 0:
            out[(per, arm)].append((dels / adds, repo))
    return dict(out)


def print_census(pool: dict[str, list]) -> None:
    from pipeline.studies.slices import weights
    rows = census_rows(pool)
    pairs = repo_pairs(pool)
    w = weights()
    print("code churn: deleted:added over mature merged PRs. CW = "
          "contributor-weighted mean of per-repo ratios (capped sides, "
          f">= {MIN_PRS} PRs/repo, 95% CI over repos); pooled = the "
          "external claim's literal metric (raw; capped companion)")
    print("claim under test: deleted:added rose 861% (x9.6) under high AI "
          "adoption; xQ1-24 is the pooled ratio vs the same-arm baseline")
    print(f"{'period':9}{'arm':7}{'repos':>6}{'CW del:add [95% CI]':>22}"
          f"{'PRs':>8}{'pooled':>8}{'capped':>8}{'medPR':>7}"
          f"{'del>add':>9}{'xQ1-24':>8}")
    for per in PERIODS:
        for arm in ("all", "AI", "nonAI"):
            r = rows.get((per, arm))
            if not r:
                continue
            ps = [(ratio, w.get(repo, 1.0))
                  for ratio, repo in pairs.get((per, arm), [])]
            if ps:
                m = weighted_mean(ps)
                lo, hi = bootstrap_ci(ps, key=f"churn|{per}|{arm}")
                cw = f"{m:6.3f} [{lo:5.3f},{hi:5.3f}]"
            else:
                cw = "n/a"
            base = rows.get(("Q1-2024", arm))
            mult = (r["ratio"] / base["ratio"]
                    if base and base["ratio"] else float("nan"))
            print(f"{per:9}{arm:7}{len(ps):>6}{cw:>22}{r['n']:>8}"
                  f"{r['ratio']:>8.3f}{r['ratio_capped']:>8.3f}"
                  f"{r['median_pr']:>7.3f}{100 * r['del_dominant']:>8.1f}%"
                  f"{mult:>8.2f}")
    print("Q1-2024 caption: detector-validity baseline, not an AI-usage "
          "estimate; AI arm has no 2024 baseline by construction")


# ------------------------------------------------------------------ sample

def draw(pool: dict[str, list]) -> list[dict]:
    """Balanced seeded ~0.1% draw: per period, target = max(2,
    round(SAMPLE_RATE * frame)); half from the AI arm, half from nonAI
    (equal arms = AI oversampled at its population share); an arm short
    of its half (Q1-2024 AI is empty) backfills from the other."""
    out = []
    for per in PERIODS:
        items = sorted(pool[per], key=lambda x: (x[0], x[1]))
        if not items:
            continue
        target = max(2, round(SAMPLE_RATE * len(items)))
        arms = {"AI": [x for x in items if x[2]],
                "nonAI": [x for x in items if not x[2]]}
        half = -(-target // 2)
        k = {"AI": min(half, len(arms["AI"]))}
        k["nonAI"] = min(target - k["AI"], len(arms["nonAI"]))
        k["AI"] = min(target - k["nonAI"], len(arms["AI"]))
        for arm, xs in arms.items():
            rng = Random(f"{SEED}:churn:{per}:{arm}")
            for repo, num, ai, adds, dels in (
                    rng.sample(xs, k[arm]) if k[arm] else []):
                out.append({"repo": repo, "num": num, "per": per,
                            "ai": ai, "adds": adds, "dels": dels})
    return sorted(out, key=lambda d: (d["per"], d["repo"], d["num"]))


_FILES_Q = ('a%d: repository(owner:"%s", name:"%s"){ pullRequest(number:%d){'
            ' files(first:%d){ pageInfo{ hasNextPage }'
            ' nodes{ path additions deletions } } } }')


def pull(selected: list[dict], pace: float = 0.8, batch: int = 10) -> None:
    """Hydrate per-file additions/deletions for the drawn PRs (append-
    resume on (repo, num); absent results are retried next run, never
    faked). files capped at FILES_PAGE — truncated records keep their
    first page and are flagged files_complete=false (reported, kept)."""
    done = set()
    if SAMPLE.exists():
        for ln in SAMPLE.read_text().splitlines():
            d = json.loads(ln)
            done.add((d["repo"], d["num"]))
    todo = [s for s in selected if (s["repo"], s["num"]) not in done]
    print(f"hydrating {len(todo)} of {len(selected)} sampled PRs")
    with SAMPLE.open("a") as out:
        for i in range(0, len(todo), batch):
            chunk = todo[i:i + batch]
            parts = [_FILES_Q % (j, s["repo"].split("/")[0],
                                 s["repo"].split("/")[1], s["num"],
                                 FILES_PAGE)
                     for j, s in enumerate(chunk)]
            data = graphql_nodes("query{ " + " ".join(parts) + " }", {},
                                 ".data", expect=dict)
            if data is None:
                print(f"WARN batch {i // batch} failed; retry next run")
                time.sleep(pace)
                continue
            for j, s in enumerate(chunk):
                node = (data.get(f"a{j}") or {}).get("pullRequest") or {}
                files = node.get("files")
                if not isinstance(files, dict) or files.get("nodes") is None:
                    continue                    # absent: retried next run
                rec = dict(s)
                rec["files"] = [
                    {"path": f.get("path") or "",
                     "adds": int(f.get("additions") or 0),
                     "dels": int(f.get("deletions") or 0)}
                    for f in files["nodes"] or [] if f]
                rec["files_complete"] = \
                    (files.get("pageInfo") or {}).get("hasNextPage") is False
                out.write(json.dumps(rec) + "\n")
                out.flush()
            time.sleep(pace)


def print_sample() -> None:
    recs = [json.loads(ln) for ln in SAMPLE.read_text().splitlines()]
    seen: dict[tuple, dict] = {}
    for r in recs:                       # later re-pull supersedes
        seen[(r["repo"], r["num"])] = r
    recs = list(seen.values())
    print("code churn, balanced 0.1% sample with per-FILE splits "
          f"({len(recs)} PRs hydrated; equal-arm design — pooled numbers "
          "are per-arm, never blended across arms)")
    print(f"{'period':9}{'arm':7}{'PRs':>6}{'trunc':>6}{'del:add':>9}"
          f"{'noGen':>9}{'gen%dels':>9}{'gen%adds':>9}")
    for per in PERIODS:
        for arm, want in (("AI", True), ("nonAI", False)):
            xs = [r for r in recs if r["per"] == per and r["ai"] == want]
            if not xs:
                continue
            adds = sum(f["adds"] for r in xs for f in r["files"])
            dels = sum(f["dels"] for r in xs for f in r["files"])
            gadds = sum(f["adds"] for r in xs for f in r["files"]
                        if is_generated(f["path"]))
            gdels = sum(f["dels"] for r in xs for f in r["files"]
                        if is_generated(f["path"]))
            trunc = sum(1 for r in xs if not r.get("files_complete"))
            print(f"{per:9}{arm:7}{len(xs):>6}{trunc:>6}"
                  f"{_ratio(adds, dels):>9.3f}"
                  f"{_ratio(adds - gadds, dels - gdels):>9.3f}"
                  f"{100 * gdels / dels if dels else 0:>8.1f}%"
                  f"{100 * gadds / adds if adds else 0:>8.1f}%")


# --------------------------------------------------------------- incidents

def incident_repos(pool: dict[str, list]) -> list[str]:
    """The sample's distinct repos — the pilot's repo universe."""
    return sorted({d["repo"] for d in draw(pool)})


def pull_incidents(repos: list[str], pace: float = 2.0) -> None:
    """Per (repo, quarter): count of GH issues labeled `bug` CREATED in
    the quarter (label:bug only — repos with other taxonomies read 0;
    pilot limitation). Append-resume; failures skipped, never zeroed."""
    done = set()
    if INCIDENTS.exists():
        for ln in INCIDENTS.read_text().splitlines():
            d = json.loads(ln)
            done.add((d["repo"], d["per"]))
    todo = [(r, per) for r in repos for per in PERIODS
            if (r, per) not in done]
    print(f"pulling bug counts for {len(todo)} repo-quarters")
    with INCIDENTS.open("a") as out:
        for r, per in todo:
            rng = QUARTER_RANGES[per]
            n = rest_count(f"repo:{r} is:issue label:{BUG_LABEL} "
                           f"created:{rng}", endpoint="search/issues")
            time.sleep(pace)
            if n is None:
                print(f"WARN {r} {per}: count failed; retry next run")
                continue
            out.write(json.dumps({"repo": r, "per": per, "bugs": n}) + "\n")
            out.flush()


def print_incidents(pool: dict[str, list]) -> None:
    bugs: dict[tuple[str, str], int] = {}
    for ln in INCIDENTS.read_text().splitlines():
        d = json.loads(ln)
        bugs[(d["repo"], d["per"])] = d["bugs"]
    merged: dict[tuple[str, str], int] = defaultdict(int)
    ai_share: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for per, items in pool.items():
        for repo, _num, ai, _a, _d in items:
            merged[(repo, per)] += 1
            if per == "Q2-2026":
                ai_share[repo][0] += bool(ai)
                ai_share[repo][1] += 1
    repos = sorted({r for (r, _p) in bugs})
    with_bugs = {r for r in repos
                 if any(bugs.get((r, p)) for p in PERIODS)}
    ranked = sorted(with_bugs,
                    key=lambda r: (ai_share[r][0] / ai_share[r][1])
                    if ai_share[r][1] else 0.0)
    lo = set(ranked[:len(ranked) // 2])
    print("incidents pilot: bug-labeled issues created per 100 mature "
          f"merged PRs, over the churn sample's repos ({len(repos)} "
          f"pulled; {len(repos) - len(with_bugs)} with zero bug-labeled "
          "issues in every quarter EXCLUDED as probable non-users of the "
          "label — label:bug only, a pilot limitation)")
    print(f"{'period':9}{'group':9}{'repos':>6}{'bugs':>7}{'merged':>8}"
          f"{'per100':>8}")
    for per in PERIODS:
        for label, grp in (("low-AI", lo), ("high-AI", with_bugs - lo),
                           ("all", with_bugs)):
            rs = [r for r in grp
                  if (r, per) in bugs and merged.get((r, per))]
            b = sum(bugs[(r, per)] for r in rs)
            m = sum(merged[(r, per)] for r in rs)
            if not m:
                continue
            print(f"{per:9}{label:9}{len(rs):>6}{b:>7}{m:>8}"
                  f"{100 * b / m:>8.2f}")
    print("groups = halves of the sample repos by Q2-2026 AI-involvement "
          "share among their sampled-frame merged PRs")


# ------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table", choices=["census", "sample", "incidents"])
    ap.add_argument("--draw", action="store_true",
                    help="print the balanced 0.1% selection")
    ap.add_argument("--pull", action="store_true",
                    help="hydrate per-file splits for the drawn sample")
    ap.add_argument("--pull-incidents", action="store_true",
                    help="pull bug-label counts for the sample's repos")
    a = ap.parse_args()
    if a.table in ("census", "sample", "incidents") or a.draw or a.pull \
            or a.pull_incidents:
        pool = eligible()
    else:
        ap.error("pick --table/--draw/--pull/--pull-incidents")
    if a.draw:
        sel = draw(pool)
        by = defaultdict(int)
        for s in sel:
            by[(s["per"], s["ai"])] += 1
        print(f"{len(sel)} PRs selected: " + ", ".join(
            f"{p} AI={by[(p, True)]}/nonAI={by[(p, False)]}"
            for p in PERIODS))
    if a.pull:
        pull(draw(pool))
    if a.pull_incidents:
        pull_incidents(incident_repos(pool))
    if a.table == "census":
        print_census(pool)
    elif a.table == "sample":
        print_sample()
    elif a.table == "incidents":
        print_incidents(pool)


if __name__ == "__main__":
    main()
