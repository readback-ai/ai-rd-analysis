"""Study: code churn — lines deleted relative to lines added in merged code.

Measures churn trends in THIS population (leading AI organizations) with
metrics similar to an external industry report (Faros, "AI acceleration
whiplash": churn "increased 861% under high AI adoption", ~x9.6,
contrasting each org's lowest- and highest-AI-adoption periods). This is
NOT a replication of that report — the populations differ fundamentally
(prominence-selected AI builders vs a broad-industry sample) — the Faros
figure is quoted only as the external reference point the numbers here
are read against. The headline is the same style of within-org contrast
(`--table adoption`); a calendar view is kept as a labeled sensitivity.

CHURN WINDOWS — identically trimmed per quarter: a PR counts toward a
quarter's churn iff it was CREATED AND MERGED in that same quarter,
REGARDLESS of w8 maturity: an observed merge is terminal, so a same-
quarter merge is fully observable even while the PR's 56-day fate
window is still open (requiring maturity would truncate the trailing
quarter's tail relative to earlier ones — the w8 rule governs fate
metrics, not already-observed merges). The census collects by creation
quarter, so a merge-bucketed quarter would silently miss inbound PRs
created in the preceding (uncensused) window while only out-spill is
observable; same-quarter trimming gives every quarter the same
observability instead. The cross-quarter residual (merges outside the
creation quarter) is dropped and reported.

ADOPTION MEASUREMENT — traceable-adoption share, a floor (METHODS: all
detection is evidence-based). Q1-2024 is EXCLUDED from the adoption
contrast: its zero is by construction (no detectable channel existed),
so a low-endpoint there measures marker availability, not low adoption.
Endpoints come from the adoption-era quarters (Q4-2025..Q2-2026) only.

PILOT design (2026-08-02):

1. `--table adoption` — per org (repo owner), per adoption-era quarter
   with >= ORG_MIN_PRS trimmed merged PRs: traceable-adoption share and
   capped-side deleted:added. Orgs with >= 2 qualifying era quarters and
   a strictly positive adoption spread contribute the churn multiple
   (highest-adoption quarter / lowest); reported as the geometric-mean
   multiple with a bootstrap CI over orgs, the median, and the share of
   orgs whose churn rose — the claim predicts ~x9.6.

2. `--table census` — calendar-trend SENSITIVITY (not the claim's
   contrast), Q1-2024 included under the standard caption: per quarter x
   arm (all / AI / nonAI; non-AI bots dropped via ai_contrast_eligible,
   so all = AI + nonAI), CW mean of per-repo deleted:added (capped
   sides, >= MIN_PRS PRs/repo, per-cell seeded CIs) plus the pooled
   ratio. Per-PR medians are over PRs with nonzero additions (a
   deletion-only PR has no defined ratio; it still counts in del>add).

3. `--draw` / `--pull` / `--table sample` — balanced ~0.1% seeded sample
   of the trimmed frame (equal AI / nonAI per quarter; Q1-2024 backfills
   from nonAI) hydrated with per-FILE additions/deletions so the ratio
   can be recomputed EXCLUDING generated content. The sample file always
   holds EXACTLY the current draw (atomic rewrite; hydration reused only
   for still-selected PRs).

4. `--pull-bugs` / `--table bugs` — bug-report proxy, NOT production
   incidents: GH issues labeled bug (`label:bug` only — repos on other
   taxonomies read zero and are excluded as probable non-users of the
   label) per 100 mature merged PRs over the sample's repos. Exposure is
   CREATION-bucketed on both sides: the denominator is mature merged PRs
   by creation quarter, and the bug window is the same quarter truncated
   at the maturity frontier (AS_OF - 56d) — exactly the last creation
   date an included PR can have. Cells are keyed by (repo, per, range)
   so a frontier move re-pulls them; rows predating the range stamp are
   migrated to the full-quarter range they were queried with.

Not (yet) in the generated report beyond the churn section; pilot numbers
carry no frozen-convention guarantees beyond the frame they share with
every study (w8 maturity, LOC cap, population manifest).
"""
from __future__ import annotations

import argparse
import json
import re
import time
from collections import defaultdict
from datetime import timedelta
from pathlib import Path
from random import Random
from statistics import median

from pipeline.analyze import bootstrap_ci, weighted_mean
from pipeline.detect import AS_OF, _iso
from pipeline.frame import ai_contrast_eligible, study_frame
from pipeline.ghx import graphql_nodes, rest_count
from pipeline.scan_orgs import QUARTER_RANGES

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
ADOPTION_PERIODS = ["Q4-2025", "Q1-2026", "Q2-2026"]   # Q1-2024 excluded
SEED = 20260630
SAMPLE_RATE = 0.001          # ~0.1% of the eligible merged frame
MIN_PRS = 5                  # repo floor per (period, arm), house convention
ORG_MIN_PRS = 20             # org floor per quarter for the adoption contrast
FILES_PAGE = 100             # per-PR file-list cap (one page; no pagination)
CAP = 20_000                 # per-side LOC cap for capped ratios
SAMPLE = Path("data/derived/churn_sample_v1.jsonl")
BUGS = Path("data/derived/churn_incidents_v1.jsonl")
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

def maturity_frontier(as_of: str = AS_OF) -> str:
    """Last creation date (YYYY-MM-DD) a w8-mature PR can have."""
    return (_iso(as_of) - timedelta(days=56)).date().isoformat()


def merge_quarter(merged_at: str | None) -> str | None:
    """The censused quarter containing the merge timestamp, if any."""
    day = (merged_at or "")[:10]
    for per in PERIODS:
        start, end = QUARTER_RANGES[per].split("..")
        if start <= day <= end:
            return per
    return None


def eligible() -> tuple[dict[str, list], dict[str, list], int]:
    """Two frames over merged PRs (profile 'all' + ai_contrast_eligible:
    non-AI bots dropped, all = AI + nonAI), items
    (repo, num, ai, additions, deletions):

    - trimmed (the CHURN frame): created AND merged in the same quarter,
      regardless of w8 maturity — an observed merge is terminal, so
      every quarter is identically observable (module docstring);
    - created (the BUG-PROXY denominator): w8-mature merged (frozen fate
      convention), bucketed by creation quarter — maturity is what
      aligns the denominator's exposure with the frontier-truncated bug
      windows.

    Third value: merged PRs whose merge fell outside their creation
    quarter (the cross-quarter residual the churn trim drops)."""
    trimmed: dict[str, list] = {p: [] for p in PERIODS}
    created: dict[str, list] = {p: [] for p in PERIODS}
    cross = 0
    for f in study_frame("all"):
        if not ai_contrast_eligible(f):
            continue
        c = f.cls
        if not c.merged_ever:
            continue
        item = (f.repo, f.pr["number"], bool(c.ai_involved),
                int(f.pr.get("additions") or 0),
                int(f.pr.get("deletions") or 0))
        if merge_quarter(f.pr.get("mergedAt")) == f.period:
            trimmed[f.period].append(item)
        else:
            cross += 1
        if c.w8_mature and c.merged:
            created[f.period].append(item)
    return trimmed, created, cross


def _ratio(adds: int, dels: int) -> float:
    return dels / adds if adds else float("nan")


# --------------------------------------------- adoption contrast (headline)

def adoption_rows(pool: dict[str, list]) -> dict:
    """Within-org contrast on traceable adoption: per org, churn at
    its highest-adoption era quarter relative to its lowest. Org-quarters
    qualify at >= ORG_MIN_PRS trimmed merged PRs; only ADOPTION_PERIODS
    are eligible endpoints (Q1-2024's zero is by construction). Orgs need
    >= 2 qualifying era quarters, a strictly positive adoption spread,
    and nonzero additions in both endpoint quarters. Returns {orgs,
    dropped_flat, multiples: [(org, low_share, high_share, low_ratio,
    high_ratio, multiple)]}."""
    per_org: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for per in ADOPTION_PERIODS:
        for repo, _num, ai, adds, dels in pool[per]:
            a = per_org[(repo.split("/")[0].lower(), per)]
            a[0] += 1
            a[1] += bool(ai)
            a[2] += min(adds, CAP)
            a[3] += min(dels, CAP)
    quarters: dict[str, dict[str, tuple]] = defaultdict(dict)
    for (org, per), (n, ai, adds, dels) in per_org.items():
        if n >= ORG_MIN_PRS:
            quarters[org][per] = (ai / n, adds, dels)
    multiples, flat = [], 0
    idx = ADOPTION_PERIODS.index
    for org, qs in sorted(quarters.items()):
        if len(qs) < 2:
            continue
        low = min(qs, key=lambda p: (qs[p][0], idx(p)))
        high = max(qs, key=lambda p: (qs[p][0], -idx(p)))
        if qs[high][0] <= qs[low][0]:
            flat += 1                    # no adoption spread to contrast
            continue
        lo_r = _ratio(qs[low][1], qs[low][2])
        hi_r = _ratio(qs[high][1], qs[high][2])
        if not (lo_r > 0 and hi_r == hi_r and qs[high][1] > 0):
            continue
        multiples.append((org, qs[low][0], qs[high][0], lo_r, hi_r,
                          hi_r / lo_r))
    return {"orgs": len(quarters), "dropped_flat": flat,
            "multiples": multiples}


def print_adoption(pool: dict[str, list], cross: int) -> None:
    import math
    r = adoption_rows(pool)
    ms = r["multiples"]
    print("code churn, WITHIN-ORG ADOPTION CONTRAST on TRACEABLE "
          "adoption (an evidence floor): per org, deleted:added at its "
          "highest-adoption quarter vs its lowest, endpoints from "
          f"{ADOPTION_PERIODS[0]}..{ADOPTION_PERIODS[-1]} only "
          "(Q1-2024's zero is by construction — a low endpoint there "
          "would contrast marker availability, not adoption); "
          "same-quarter-trimmed merge windows (capped sides; "
          f"org-quarters qualify at >= {ORG_MIN_PRS} PRs)")
    print("external reference, NOT a replication target (different "
          "population): Faros's broad-industry report has this multiple "
          "at ~x9.6 (+861%)")
    if not ms:
        print("no qualifying orgs")
        return
    logs = [(math.log(m[5]), 1.0) for m in ms]
    gm = math.exp(weighted_mean(logs))
    lo, hi = bootstrap_ci(logs, key="churn|adoption")
    med = median(m[5] for m in ms)
    rose = sum(1 for m in ms if m[5] > 1)
    print(f"orgs contrasted: {len(ms)} (of {r['orgs']} with >= 2 "
          f"qualifying era quarters; {r['dropped_flat']} dropped for "
          f"zero adoption spread); cross-quarter merges trimmed: {cross}")
    print(f"geomean churn multiple (high/low adoption): {gm:.2f} "
          f"[{math.exp(lo):.2f},{math.exp(hi):.2f}]  median {med:.2f}  "
          f"churn rose in {rose}/{len(ms)} orgs "
          f"({100 * rose / len(ms):.0f}%)")
    med_spread = median(m[2] - m[1] for m in ms)
    print(f"median adoption spread low->high: {100 * med_spread:.0f}pp; "
          "multiples pool adds/dels across each org's population repos")


# ------------------------------------------- calendar view (sensitivity)

def census_rows(pool: dict[str, list]) -> dict[tuple[str, str], dict]:
    """(quarter, arm) -> pooled churn. median_pr is over PRs with nonzero
    additions (deletion-only PRs have no defined ratio and are excluded
    from the median; they still count in del_dominant)."""
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
            ratios = [x[4] / x[3] for x in xs if x[3] > 0]
            out[(per, arm)] = {
                "n": len(xs), "adds": adds, "dels": dels,
                "ratio": _ratio(adds, dels),
                "ratio_capped": _ratio(cadds, cdels),
                "median_pr": median(ratios) if ratios else float("nan"),
                "del_dominant": sum(1 for x in xs if x[4] > x[3]) / len(xs),
            }
    return out


def repo_pairs(pool: dict[str, list]) -> dict[tuple[str, str], list]:
    """(quarter, arm) -> [(repo_ratio, repo)] for the CW series: per
    repo, capped-side deletions / capped-side additions over its arm PRs;
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
    print("code churn, CALENDAR-TREND SENSITIVITY (fixed quarters and "
          "PR-level arms — a different cut than the within-org adoption "
          "contrast above, and not comparable to any external figure). "
          "Same-quarter-trimmed merge windows. CW = contributor-weighted "
          f"mean of per-repo deleted:added (capped sides, >= {MIN_PRS} "
          "PRs/repo, 95% CI over repos); pooled = raw ratio of totals")
    print(f"{'quarter':9}{'arm':7}{'repos':>6}{'CW del:add [95% CI]':>22}"
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
    print("Q1-2024 caption: detector-validity baseline and review-practice "
          "control, not an AI-usage estimate; AI arm has no 2024 baseline "
          "by construction (and Q1-2024 is excluded from the adoption "
          "contrast above)")


# ------------------------------------------------------------------ sample

def draw(pool: dict[str, list]) -> list[dict]:
    """Balanced seeded ~0.1% draw over the trimmed churn frame: per
    quarter, target = max(2, round(SAMPLE_RATE * frame)); half from the
    AI arm, half from nonAI (equal arms = AI oversampled at its
    population share); an arm short of its half (Q1-2024 AI is empty)
    backfills from the other."""
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


def reconcile(selected: list[dict], existing: list[dict],
              key_fields: tuple[str, ...], payload_field: str,
              ) -> tuple[dict, list[dict], int]:
    """Selection-vs-store reconciliation: keep existing records only for
    keys in the CURRENT selection (and only if hydrated — carrying
    payload_field); everything else is stale and dropped. Returns
    (kept records by key, still-missing selections, stale_dropped)."""
    cur = {tuple(s[f] for f in key_fields): s for s in selected}
    kept: dict[tuple, dict] = {}
    stale = 0
    for d in existing:
        k = tuple(d.get(f) for f in key_fields)
        if k in cur and payload_field in d:
            kept[k] = d                 # later record supersedes
        elif k not in cur:
            stale += 1
    todo = [s for k, s in cur.items() if k not in kept]
    return kept, todo, stale


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines()]


def _write_jsonl(path: Path, records: list[dict]) -> None:
    tmp = path.with_suffix(".tmp")
    tmp.write_text("".join(json.dumps(r) + "\n" for r in records))
    tmp.replace(path)                   # atomic: complete-or-absent


_FILES_Q = ('a%d: repository(owner:"%s", name:"%s"){ pullRequest(number:%d){'
            ' files(first:%d){ pageInfo{ hasNextPage }'
            ' nodes{ path additions deletions } } } }')


def pull(selected: list[dict], pace: float = 0.8, batch: int = 10) -> None:
    """Hydrate per-file additions/deletions for the CURRENT draw. The
    sample file is atomically rewritten to exactly the current selection:
    prior hydration is reused for still-selected PRs, stale draws are
    dropped, missing ones are pulled (absent results stay missing and are
    retried next run, never faked)."""
    kept, todo, stale = reconcile(selected, _load_jsonl(SAMPLE),
                                  ("repo", "num"), "files")
    print(f"hydrating {len(todo)} of {len(selected)} sampled PRs "
          f"({len(kept)} reused, {stale} stale dropped)")
    for i in range(0, len(todo), batch):
        chunk = todo[i:i + batch]
        parts = [_FILES_Q % (j, s["repo"].split("/")[0],
                             s["repo"].split("/")[1], s["num"], FILES_PAGE)
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
            kept[(s["repo"], s["num"])] = rec
        time.sleep(pace)
    _write_jsonl(SAMPLE, sorted(kept.values(),
                                key=lambda d: (d["per"], d["repo"],
                                               d["num"])))
    missing = len(selected) - len(kept)
    if missing:
        print(f"{missing} selections still unhydrated (re-run --pull)")


def print_sample(pool: dict[str, list]) -> None:
    kept, todo, stale = reconcile(draw(pool), _load_jsonl(SAMPLE),
                                  ("repo", "num"), "files")
    recs = list(kept.values())
    print("code churn, balanced 0.1% sample with per-FILE splits "
          f"({len(recs)} of the current draw hydrated, {len(todo)} "
          f"missing, {stale} stale ignored; equal-arm design — pooled "
          "numbers are per-arm, never blended across arms)")
    print(f"{'quarter':9}{'arm':7}{'PRs':>6}{'trunc':>6}{'del:add':>9}"
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


# ------------------------------------------------------- bug-report proxy

def bug_window(per: str, as_of: str = AS_OF) -> str | None:
    """The quarter's bug-count window, truncated at the maturity frontier
    so numerator exposure matches the creation-bucketed mature-PR
    denominator. None if the whole quarter is past the frontier."""
    start, end = QUARTER_RANGES[per].split("..")
    end = min(end, maturity_frontier(as_of))
    return f"{start}..{end}" if start <= end else None


def migrate_bug_rows(rows: list[dict]) -> list[dict]:
    """Rows written before range-stamping were queried with the FULL
    quarter range — stamp them with it, so reconciliation keeps them
    exactly where that is still the current window and retires them
    (stale) where the frontier has trimmed it."""
    out = []
    for d in rows:
        if "rng" not in d and d.get("per") in QUARTER_RANGES:
            d = {**d, "rng": QUARTER_RANGES[d["per"]]}
        out.append(d)
    return out


def bug_cells(pool: dict[str, list]) -> list[dict]:
    """The current selection of (repo, per, rng) bug-count cells: the
    sample's distinct repos x quarters with a defined window."""
    repos = sorted({d["repo"] for d in draw(pool)})
    return [{"repo": r, "per": per, "rng": bug_window(per)}
            for r in repos for per in PERIODS
            if bug_window(per) is not None]


def pull_bugs(pool: dict[str, list], pace: float = 2.0) -> None:
    """Count bug-labeled issues per cell (label:bug only — a documented
    proxy limitation). The file is atomically rewritten to exactly the
    current cell selection: counts are reused only when the cell's window
    matches (pre-stamp rows are migrated first; a range change, e.g. an
    AS_OF bump moving the frontier, re-pulls the cell); failures stay
    missing, never zeroed. Checkpoints every 25 cells."""
    cells = bug_cells(pool)
    kept, todo, stale = reconcile(cells, migrate_bug_rows(_load_jsonl(BUGS)),
                                  ("repo", "per", "rng"), "bugs")
    print(f"pulling {len(todo)} of {len(cells)} bug cells "
          f"({len(kept)} reused, {stale} stale dropped)")

    def flush() -> None:
        _write_jsonl(BUGS, sorted(kept.values(),
                                  key=lambda d: (d["repo"], d["per"])))

    for i, s in enumerate(todo):
        n = rest_count(f"repo:{s['repo']} is:issue label:{BUG_LABEL} "
                       f"created:{s['rng']}", endpoint="search/issues")
        time.sleep(pace)
        if n is None:
            print(f"WARN {s['repo']} {s['per']}: count failed; "
                  "retry next run")
            continue
        kept[(s["repo"], s["per"], s["rng"])] = {**s, "bugs": n}
        if i % 25 == 24:
            flush()          # checkpoint: an interrupted run keeps its
                             # completed cells (each flush is atomic)
    flush()
    missing = len(cells) - len(kept)
    if missing:
        print(f"{missing} cells still unpulled (re-run --pull-bugs)")


def print_bugs(trimmed: dict[str, list], created: dict[str, list]) -> None:
    kept, todo, stale = reconcile(bug_cells(trimmed),
                                  migrate_bug_rows(_load_jsonl(BUGS)),
                                  ("repo", "per", "rng"), "bugs")
    bugs = {(d["repo"], d["per"]): d["bugs"] for d in kept.values()}
    merged: dict[tuple[str, str], int] = defaultdict(int)
    ai_share: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for per, items in created.items():
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
    print("BUG-REPORT PROXY pilot (bug-labeled GH issues — NOT production "
          "incidents): issues labeled bug created per 100 mature merged "
          "PRs. Exposure is creation-bucketed on BOTH sides: denominator "
          "= mature merged PRs by creation quarter, numerator window = "
          f"the quarter truncated at the maturity frontier "
          f"({maturity_frontier()}). Over the churn sample's repos "
          f"({len(repos)} pulled, {len(todo)} cells missing, {stale} "
          f"stale ignored; {len(repos) - len(with_bugs)} repos with zero "
          "bug-labeled issues in every quarter EXCLUDED as probable "
          "non-users of the label — label:bug only)")
    print(f"{'quarter':9}{'group':9}{'repos':>6}{'bugs':>7}{'merged':>8}"
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
          "share among their created-bucketed merged PRs; pooled group "
          "rates can be dominated by single large repos")


# ------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table",
                    choices=["report", "adoption", "census", "sample",
                             "bugs"])
    ap.add_argument("--draw", action="store_true",
                    help="print the balanced 0.1% selection")
    ap.add_argument("--pull", action="store_true",
                    help="hydrate per-file splits for the current draw")
    ap.add_argument("--pull-bugs", action="store_true",
                    help="pull bug-label counts for the sample's repos")
    a = ap.parse_args()
    if not (a.table or a.draw or a.pull or a.pull_bugs):
        ap.error("pick --table/--draw/--pull/--pull-bugs")
    trimmed, created, cross = eligible()
    if a.draw:
        sel = draw(trimmed)
        by = defaultdict(int)
        for s in sel:
            by[(s["per"], s["ai"])] += 1
        print(f"{len(sel)} PRs selected: " + ", ".join(
            f"{p} AI={by[(p, True)]}/nonAI={by[(p, False)]}"
            for p in PERIODS))
    if a.pull:
        pull(draw(trimmed))
    if a.pull_bugs:
        pull_bugs(trimmed)
    if a.table in ("report", "adoption"):
        print_adoption(trimmed, cross)
    if a.table in ("report", "census"):
        if a.table == "report":
            print()
        print_census(trimmed)
    if a.table == "sample":
        print_sample(trimmed)
    elif a.table == "bugs":
        print_bugs(trimmed, created)


if __name__ == "__main__":
    main()
