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
from pipeline.ghx import _gh, graphql_nodes, rest_count
from pipeline.scan_orgs import QUARTER_RANGES, resolve_period

PERIODS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
ADOPTION_PERIODS = ["Q4-2025", "Q1-2026", "Q2-2026"]   # Q1-2024 excluded
ADOPTION_ERA_START = "2025-10"   # first adoption-era month (monthly mode)
SEED = 20260630
SAMPLE_RATE = 0.001          # ~0.1% of the eligible merged frame
MIN_PRS = 5                  # repo floor per (quarter, arm); 2/month —
MIN_PRS_MONTH = 2            #   comparable thresholds per unit time
ORG_MIN_PRS = 20             # org floor per quarter for the adoption
ORG_MIN_PRS_MONTH = 7        #   contrast; 7/month is the same per unit time
FILES_PAGE = 100             # per-PR file-list cap (one page; no pagination)
CAP = 20_000                 # per-side LOC cap for capped ratios
SAMPLE = Path("data/derived/churn_sample_v1.jsonl")
SAMPLE_MANIFEST = Path("data/derived/churn_sample_manifest_v1.json")
BUGS = Path("data/derived/churn_incidents_v1.jsonl")
BUGS_MANIFEST = Path("data/derived/churn_incidents_manifest_v1.json")
BUGS_MONTHLY = Path("data/derived/churn_incidents_monthly_v1.jsonl")
BUGS_MONTHLY_MANIFEST = \
    Path("data/derived/churn_incidents_monthly_manifest_v1.json")
BUG_LABEL = "bug"
# Dated bug issues: the v1 artifacts hold a COUNT per window, so every
# window question costs a re-pull. These hold each issue's number and
# creation day instead, so any window — same-period, lagged, or the
# per-PR risk window below — is a local computation over one freeze.
BUG_DATES = Path("data/derived/churn_bug_dates_v2.jsonl")
BUG_DATES_MANIFEST = Path("data/derived/churn_bug_dates_manifest_v2.json")
BUG_DATES_MONTHLY = Path("data/derived/churn_bug_dates_monthly_v2.jsonl")
BUG_DATES_MONTHLY_MANIFEST = \
    Path("data/derived/churn_bug_dates_monthly_manifest_v2.json")
RISK_DAYS = 28               # per-PR risk window: bugs arrive fast
SEARCH_CAP = 1000            # GitHub search cannot page past this
# The dated collector's version, stamped on every cell it writes. A cell
# is reused only under the collector that produced it: a fix to how
# issues are fetched (completeness, ordering, retries) must reach every
# frozen cell, and reuse by key alone would keep the old payloads
# forever. Bump when the fetch changes in a way that can alter a cell.
COLLECTOR = 2

# Generated-content path patterns (the METHODS 5b hygiene classes:
# lockfiles, vendored trees, minified/compiled outputs, protobuf,
# snapshots, svg, notebooks).
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


def finalized_months() -> list[str]:
    """Reportable months under the w8 FINALIZATION rule: censused months
    (frozen quarters + registered incremental months) whose every PR
    creation window has closed — month_end + 56d <= AS_OF. On
    2026-08-01 the series runs through 2026-05; June finalizes at the
    ~Aug 25 re-pull and July on ~Sep 25 (monthly runbook cadence)."""
    from pipeline.analyze import censused_months, extended_quarters
    from pipeline.studies.productivity import month_w8_mature
    return sorted(m for m in censused_months(extended_quarters())
                  if month_w8_mature(m))


def _period_order(keys) -> list[str]:
    """Chronological order for quarter or month tokens."""
    return sorted(keys, key=lambda t: resolve_period(t).split("..")[0])


def eligible(granularity: str = "quarter",
             ) -> tuple[dict[str, list], dict[str, list], int, list[str]]:
    """Two frames over merged PRs (profile 'all' + ai_contrast_eligible:
    non-AI bots dropped, all = AI + nonAI), items
    (repo, num, ai, additions, deletions):

    - trimmed (the CHURN frame): created AND merged in the same period,
      regardless of w8 maturity — an observed merge is terminal, so
      every period is identically observable (module docstring);
    - created (the BUG-PROXY denominator): w8-mature merged (frozen fate
      convention), bucketed by creation period — maturity is what
      aligns the denominator's exposure with the frontier-truncated bug
      windows.

    Monthly granularity uses only FINALIZED months (finalized_months):
    the w8 finalization rule means a month is reportable once every PR
    created in it closed its 56-day window — June 2026 has no data until
    the post-Aug-25 re-pull. Returns (trimmed, created, cross-period
    merge residual, ordered period list)."""
    if granularity == "month":
        from pipeline.analyze import extended_quarters
        periods = finalized_months()
        frame = study_frame("all", periods=set(periods),
                            ranges=extended_quarters(),
                            granularity="month")

        def merge_per(merged_at):
            tok = (merged_at or "")[:7]
            return tok if tok in pset else None
        pset = set(periods)
    else:
        periods = list(PERIODS)
        frame = study_frame("all")
        merge_per = merge_quarter
    trimmed: dict[str, list] = {p: [] for p in periods}
    created: dict[str, list] = {p: [] for p in periods}
    cross = 0
    for f in frame:
        if not ai_contrast_eligible(f):
            continue
        c = f.cls
        if not c.merged_ever:
            continue
        item = (f.repo, f.pr["number"], bool(c.ai_involved),
                int(f.pr.get("additions") or 0),
                int(f.pr.get("deletions") or 0))
        if merge_per(f.pr.get("mergedAt")) == f.period:
            trimmed[f.period].append(item)
        else:
            cross += 1
        if c.w8_mature and c.merged:
            created[f.period].append(item)
    return trimmed, created, cross, periods


def _ratio(adds: int, dels: int) -> float:
    return dels / adds if adds else float("nan")


# --------------------------------------------- adoption contrast (headline)

def adoption_era(periods: list[str]) -> list[str]:
    """Endpoint-eligible periods: the adoption era only — the 2024
    baseline's zero is by construction (marker availability)."""
    if periods and periods[0].startswith("Q"):
        return [p for p in periods if p in ADOPTION_PERIODS]
    return [p for p in periods if p >= ADOPTION_ERA_START]


def adoption_rows(pool: dict[str, list], era: list[str] | None = None,
                  org_min: int = ORG_MIN_PRS) -> dict:
    """Within-org contrast on traceable adoption: per org, churn at
    its highest-adoption era period relative to its lowest. Org-periods
    qualify at >= org_min trimmed merged PRs; only adoption-era periods
    are eligible endpoints (the 2024 baseline's zero is by
    construction). Orgs need >= 2 qualifying era periods, a strictly
    positive adoption spread, and nonzero additions in both endpoint
    periods. Returns {orgs_any, orgs_ge2, dropped_flat, dropped_ratio,
    multiples: [(org, low_share, high_share, low_ratio, high_ratio,
    multiple)]}."""
    era = era if era is not None else ADOPTION_PERIODS
    per_org: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for per in era:
        for repo, _num, ai, adds, dels in pool.get(per, []):
            a = per_org[(repo.split("/")[0].lower(), per)]
            a[0] += 1
            a[1] += bool(ai)
            a[2] += min(adds, CAP)
            a[3] += min(dels, CAP)
    quarters: dict[str, dict[str, tuple]] = defaultdict(dict)
    for (org, per), (n, ai, adds, dels) in per_org.items():
        if n >= org_min:
            quarters[org][per] = (ai / n, adds, dels)
    multiples, flat, badratio = [], 0, 0
    orgs_ge2 = 0
    idx = era.index
    for org, qs in sorted(quarters.items()):
        if len(qs) < 2:
            continue
        orgs_ge2 += 1
        low = min(qs, key=lambda p: (qs[p][0], idx(p)))
        high = max(qs, key=lambda p: (qs[p][0], -idx(p)))
        if qs[high][0] <= qs[low][0]:
            flat += 1                    # no adoption spread to contrast
            continue
        lo_r = _ratio(qs[low][1], qs[low][2])
        hi_r = _ratio(qs[high][1], qs[high][2])
        if not (lo_r > 0 and hi_r == hi_r and qs[high][1] > 0):
            badratio += 1                # endpoint ratio undefined/zero
            continue
        multiples.append((org, qs[low][0], qs[high][0], lo_r, hi_r,
                          hi_r / lo_r))
    return {"orgs_any": len(quarters), "orgs_ge2": orgs_ge2,
            "dropped_flat": flat, "dropped_ratio": badratio,
            "multiples": multiples}


def print_adoption(pool: dict[str, list], cross: int,
                   periods: list[str] | None = None,
                   org_min: int = ORG_MIN_PRS) -> None:
    import math
    era = adoption_era(periods if periods is not None else PERIODS)
    r = adoption_rows(pool, era, org_min)
    ms = r["multiples"]
    unit = "quarter" if era and era[0].startswith("Q") else "month"
    print("code churn, WITHIN-ORG ADOPTION CONTRAST on TRACEABLE "
          "adoption (an evidence floor): per org, deleted:added at its "
          f"highest-adoption {unit} vs its lowest, endpoints from "
          f"{era[0]}..{era[-1]} only "
          "(the 2024 baseline's zero is by construction — a low "
          "endpoint there would contrast marker availability, not "
          f"adoption); same-{unit}-trimmed merge windows (capped sides; "
          f"org-{unit}s qualify at >= {org_min} PRs)")
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
    print(f"orgs contrasted: {len(ms)} — attrition: {r['orgs_any']} orgs "
          f"with >= 1 qualifying era {unit}, {r['orgs_ge2']} with >= 2, "
          f"minus {r['dropped_flat']} with zero adoption spread and "
          f"{r['dropped_ratio']} with an undefined/zero endpoint ratio; "
          f"cross-{unit} merges trimmed: {cross}")
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


def repo_pairs(pool: dict[str, list],
               min_prs: int = MIN_PRS) -> dict[tuple[str, str], list]:
    """(period, arm) -> [(repo_ratio, repo)] for the CW series: per
    repo, capped-side deletions / capped-side additions over its arm PRs;
    qualifies at >= min_prs PRs and nonzero additions (a repo whose arm
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
        if n >= min_prs and adds > 0:
            out[(per, arm)].append((dels / adds, repo))
    return dict(out)


def baseline_rows(rows: dict, periods: list[str]) -> dict[str, dict]:
    """arm -> pooled 2024-baseline totals for the x-baseline multiple:
    the Q1-2024 row at quarter granularity, the pooled 2024 months at
    month granularity."""
    base_pers = [p for p in periods
                 if p == "Q1-2024" or p.startswith("2024")]
    out: dict[str, dict] = {}
    for arm in ("all", "AI", "nonAI"):
        adds = sum(rows[(p, arm)]["adds"] for p in base_pers
                   if (p, arm) in rows)
        dels = sum(rows[(p, arm)]["dels"] for p in base_pers
                   if (p, arm) in rows)
        if adds:
            out[arm] = {"ratio": dels / adds}
    return out


def print_census(pool: dict[str, list],
                 periods: list[str] | None = None,
                 min_prs: int = MIN_PRS) -> None:
    from pipeline.studies.slices import weights
    periods = periods if periods is not None else list(PERIODS)
    unit = "quarter" if periods and periods[0].startswith("Q") else "month"
    rows = census_rows(pool)
    pairs = repo_pairs(pool, min_prs)
    base = baseline_rows(rows, periods)
    w = weights()
    print(f"code churn, CALENDAR-TREND SENSITIVITY (fixed {unit}s and "
          "PR-level arms — a different cut than the within-org adoption "
          "contrast above, and not comparable to any external figure). "
          f"Same-{unit}-trimmed merge windows. CW = contributor-weighted "
          f"mean of per-repo deleted:added (capped sides, >= {min_prs} "
          "PRs/repo, 95% CI over repos); pooled = raw ratio of totals; "
          "x2024 = pooled ratio vs the same-arm pooled 2024 baseline")
    print(f"{'period':9}{'arm':7}{'repos':>6}{'CW del:add [95% CI]':>22}"
          f"{'PRs':>8}{'pooled':>8}{'capped':>8}{'medPR':>7}"
          f"{'del>add':>9}{'x2024':>8}")
    for per in periods:
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
            b = base.get(arm)
            mult = (r["ratio"] / b["ratio"]
                    if b and b["ratio"] else float("nan"))
            print(f"{per:9}{arm:7}{len(ps):>6}{cw:>22}{r['n']:>8}"
                  f"{r['ratio']:>8.3f}{r['ratio_capped']:>8.3f}"
                  f"{r['median_pr']:>7.3f}{100 * r['del_dominant']:>8.1f}%"
                  f"{mult:>8.2f}")
    print("2024 caption: detector-validity baseline and review-practice "
          "control, not an AI-usage estimate; AI arm has no 2024 baseline "
          "by construction (and the 2024 baseline is excluded from the "
          "adoption contrast above)")


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


def frame_fingerprint(*pools: dict[str, list], extra: str = "") -> str:
    """Identity of the frame(s) a frozen artifact depends on: hash of the
    draw-determining config plus every (period, repo, num, ai) of each
    pool, in order. The AI flag is included because it drives arm
    assignment and group membership; the bug freeze passes BOTH pools
    (trimmed drives the draw, created drives denominators/groups). The
    store is LIVE (monthly updates), so committed artifacts carry this
    stamp; tables report the FROZEN data and flag drift instead of
    silently rebuilding on a moved frame."""
    import hashlib
    h = hashlib.sha256(f"{AS_OF}|{SEED}|{SAMPLE_RATE}".encode())
    for pool in pools:
        for per in _period_order(pool.keys()):
            for repo, num, ai, *_ in sorted(pool[per],
                                            key=lambda x: (x[0], x[1])):
                h.update(f"{per}|{repo}|{num}|{int(ai)}\n".encode())
        h.update(b"--\n")
    if extra:
        h.update(f"extra|{extra}\n".encode())
    return h.hexdigest()[:16]


def bugs_fingerprint(trimmed: dict[str, list], created: dict[str, list],
                     sample_digest: str | None = None) -> str:
    """The bug artifact's frame stamp. The monthly selection's repo
    universe comes from the FROZEN quarterly sample, so the monthly
    stamp also covers that sample's digest — a quarterly sample refresh
    changes the monthly pilot universe and must change the stamp. The
    digest MUST come from the same _verify() call that produced the
    sample rows the caller is using (a manifest re-read here could see a
    concurrent re-freeze and stamp old rows with a new digest).
    Quarterly stamps (sample_digest None) are the plain two-pool
    fingerprint, unchanged."""
    if sample_digest is None:
        return frame_fingerprint(trimmed, created)
    return frame_fingerprint(trimmed, created,
                             extra=f"sample:{sample_digest}")


def _freeze(path: Path, mpath: Path, records: list[dict], fp: str,
            selected: int) -> None:
    """Crash-consistent freeze: write the data atomically, then the
    manifest atomically, with the manifest carrying a digest of the data
    bytes and the row count — a crash between the two writes leaves a
    digest mismatch the print paths refuse on, never a silent
    data/manifest skew."""
    import hashlib
    blob = "".join(json.dumps(r) + "\n" for r in records)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(blob)
    tmp.replace(path)
    m = {"frame": fp, "as_of": AS_OF, "selected": selected,
         "held": len(records),
         "digest": hashlib.sha256(blob.encode()).hexdigest()[:16]}
    mtmp = mpath.with_suffix(".tmp")
    mtmp.write_text(json.dumps(m) + "\n")
    mtmp.replace(mpath)


def _read_manifest(path: Path) -> dict:
    return json.loads(path.read_text()) if path.exists() else {}


def _verify(path: Path, mpath: Path) -> tuple[list[dict], dict]:
    """Load a frozen artifact, refusing on any data/manifest skew: the
    manifest's digest must match the file bytes and its held count the
    row count. A held < selected shortfall is honest (documented
    nonresponse) and left to the caller to report."""
    import hashlib
    manifest = _read_manifest(mpath)
    if not manifest:
        raise SystemExit(f"{mpath} missing — run the pull to freeze a "
                         "selection before printing")
    blob = path.read_text() if path.exists() else ""
    digest = hashlib.sha256(blob.encode()).hexdigest()[:16]
    rows = [json.loads(ln) for ln in blob.splitlines()]
    if digest != manifest.get("digest") or len(rows) != manifest.get("held"):
        raise SystemExit(
            f"{path} does not match its manifest (digest {digest} vs "
            f"{manifest.get('digest')}, rows {len(rows)} vs held "
            f"{manifest.get('held')}) — an interrupted or partial write; "
            "re-run the pull to re-freeze")
    return rows, manifest


def _drift_line(manifest: dict, live_fp: str) -> str:
    if not manifest:
        return "no manifest: selection provenance unknown (re-run pull)"
    if manifest.get("frame") == live_fp:
        return (f"frame {manifest['frame']} (as_of {manifest['as_of']}) "
                "— live store MATCHES the frozen selection")
    return (f"frame {manifest.get('frame')} (as_of "
            f"{manifest.get('as_of')}) — live store has MOVED (now "
            f"{live_fp}); table reports the FROZEN selection; re-run the "
            "pull to re-freeze")


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(ln) for ln in path.read_text().splitlines()]


_FILES_Q = ('a%d: repository(owner:"%s", name:"%s"){ pullRequest(number:%d){'
            ' files(first:%d){ pageInfo{ hasNextPage }'
            ' nodes{ path additions deletions } } } }')


def pull(pool: dict[str, list], pace: float = 0.8, batch: int = 10) -> int:
    """Hydrate per-file additions/deletions for the CURRENT draw and
    freeze it: the sample file is atomically rewritten to exactly the
    current selection (prior hydration reused for still-selected PRs,
    stale draws dropped, missing ones pulled — absent results stay
    missing and are retried next run, never faked) and the manifest
    records the frame fingerprint the selection was drawn from."""
    selected = draw(pool)
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
    _freeze(SAMPLE, SAMPLE_MANIFEST,
            sorted(kept.values(),
                   key=lambda d: (d["per"], d["repo"], d["num"])),
            frame_fingerprint(pool), len(selected))
    missing = len(selected) - len(kept)
    if missing:
        print(f"{missing} selections still unhydrated (re-run --pull)")
    return missing


def print_sample(pool: dict[str, list]) -> None:
    recs, manifest = _verify(SAMPLE, SAMPLE_MANIFEST)
    short = manifest["selected"] - manifest["held"]
    print("code churn, balanced 0.1% sample with per-FILE splits "
          f"({len(recs)} frozen-selection records"
          + (f", {short} of the selection unhydrated at freeze" if short
             else "")
          + "; equal-arm design — pooled numbers are per-arm, never "
            "blended across arms)")
    print(_drift_line(manifest, frame_fingerprint(pool)))
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
    start, end = resolve_period(per).split("..")
    end = min(end, maturity_frontier(as_of))
    return f"{start}..{end}" if start <= end else None


def observable_end(as_of: str = AS_OF) -> str:
    """Last day an issue can be observed in the freeze."""
    return _iso(as_of).date().isoformat()


def bug_date_window(per: str, as_of: str = AS_OF) -> str | None:
    """The dated pull's window for a period: the period itself plus
    RISK_DAYS past its end, bounded by what the freeze can observe. The
    tail makes each cell self-contained for any reader window reaching up
    to RISK_DAYS beyond the period (a lagged calendar design, the last
    period of a censused block); exposure_rows itself rates only the
    period's own days. Windows of adjacent periods OVERLAP by design —
    issues carry their number, so readers dedupe rather than
    double-count."""
    start, end = resolve_period(per).split("..")
    end = min((_iso(f"{end}T00:00:00Z") + timedelta(days=RISK_DAYS))
              .date().isoformat(), observable_end(as_of))
    return f"{start}..{end}" if start <= end else None


def _split_range(rng: str) -> list[str]:
    """Halve a date range — the escape hatch when a cell holds more
    issues than search will page through."""
    start, end = rng.split("..")
    a, b = _iso(f"{start}T00:00:00Z"), _iso(f"{end}T00:00:00Z")
    if a >= b:
        return [rng]
    mid = a + (b - a) / 2
    ms = mid.date().isoformat()
    nxt = (mid + timedelta(days=1)).date().isoformat()
    return [f"{start}..{ms}", f"{nxt}..{end}"]


def search_issue_days(repo: str, rng: str, pace: float = 2.0,
                      ) -> list[list] | None:
    """[[issue_number, 'YYYY-MM-DD'], ...] for bug-labeled issues created
    in `rng`. Search cannot page past SEARCH_CAP results, so an
    over-full range is bisected until each part fits. None = a query gave
    up; the caller must not record that as an empty cell."""
    q = f"repo:{repo} is:issue label:{BUG_LABEL} created:{rng}"
    total = _search_count(q)
    if total is None:          # no count, or a count search that timed out
        return None
    if total > SEARCH_CAP:
        parts = _split_range(rng)
        if len(parts) == 1:                  # single day over the cap
            return None
        out: list[list] = []
        for p in parts:
            time.sleep(pace)
            got = search_issue_days(repo, p, pace)
            if got is None:
                return None
            out += got
        return out
    if total == 0:
        return []
    rows: list[list] = []
    for page in range(1, (total // 100) + 2):
        out = _gh_search_page(q, page)
        if out is None:
            return None
        rows += out
        if len(rows) >= total:
            break
        time.sleep(pace)
    # a page that came back short of the count (search timed out, index
    # moved) would freeze an understated cell that reconcile then reuses
    # forever — refuse it, so the cell stays missing and is re-pulled
    return rows if len(rows) == total else None


def _search_json(args: list[str], retries: int, backoff: float):
    """A search response's jq-shaped JSON, retried like rest_count. A
    search that timed out server-side answers SUCCESSFULLY with partial
    matches and incomplete_results true — that is a failure here, since
    a frozen cell must be the whole count, so it is retried and finally
    refused."""
    for _ in range(retries):
        out = _gh(args)
        if out is not None and out.strip():
            try:
                data = json.loads(out.strip())
            except json.JSONDecodeError:
                data = None
            if data is not None and not data.get("inc"):
                return data
        time.sleep(backoff)
    return None


def _search_count(query: str, retries: int = 4, backoff: float = 25.0,
                  ) -> int | None:
    """A search's total_count, or None — including when the count search
    itself timed out, since a partial count would let a truncated page
    set look complete."""
    data = _search_json(
        ["api", "-X", "GET", "search/issues", "-f", f"q={query}", "-f",
         "per_page=1", "--jq",
         '{inc: .incomplete_results, n: .total_count} | tojson'],
        retries, backoff)
    return None if data is None else int(data["n"])


def _gh_search_page(query: str, page: int, retries: int = 4,
                    backoff: float = 25.0) -> list[list] | None:
    """One page of issue (number, creation day) pairs, in creation order
    so paging is stable across requests (best-match order can reshuffle
    between pages and skip an issue). Retries like rest_count: one
    transient failure must not discard a multi-page cell."""
    data = _search_json(
        ["api", "-X", "GET", "search/issues", "-f", f"q={query}", "-f",
         "sort=created", "-f", "order=asc", "-f", "per_page=100", "-f",
         f"page={page}", "--jq",
         '{inc: .incomplete_results, items: [.items[] | [.number, '
         '(.created_at[0:10])]]} | tojson'],
        retries, backoff)
    return None if data is None else data["items"]


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


def bug_cells(pool: dict[str, list], periods: list[str] | None = None,
              repos: list[str] | None = None) -> list[dict]:
    """The current selection of (repo, per, rng) bug-count cells: the
    pilot repos x periods with a defined window. Quarterly mode draws
    the repo universe live; monthly mode passes the FROZEN quarterly
    sample's repos (one pilot repo set across granularities)."""
    if repos is None:
        repos = sorted({d["repo"] for d in draw(pool)})
    return [{"repo": r, "per": per, "rng": bug_window(per)}
            for r in repos for per in (periods or PERIODS)
            if bug_window(per) is not None]


def bug_date_cells(pool: dict[str, list], periods: list[str] | None = None,
                   ) -> list[dict]:
    """The dated pull's (repo, per, rng) selection: EVERY repo with an
    eligible merged PR in any period, over the risk-extended windows. The
    PR side of the rate is a census, so the bug side surveys the
    population too — the counted pilot's PR-level draw would enter repos
    probability-proportional-to-size and describe the largest ones.
    (Quarterly: ~1.5k repos x 4 periods; monthly is ~11x that.)"""
    repos = sorted({item[0] for items in pool.values() for item in items})
    return [{"repo": r, "per": per, "rng": bug_date_window(per)}
            for r in repos for per in (periods or PERIODS)
            if bug_date_window(per) is not None]


def pull_bug_dates(trimmed: dict[str, list], created: dict[str, list],
                   periods: list[str] | None = None,
                   pace: float = 2.0) -> None:
    """Hydrate each cell with its bug issues' numbers and creation days.
    Same reconciliation and crash-consistent freeze as the counted pull;
    failures stay missing rather than being recorded as empty."""
    monthly = periods is not None and bool(periods) \
        and not periods[0].startswith("Q")
    data, mani = ((BUG_DATES_MONTHLY, BUG_DATES_MONTHLY_MANIFEST) if monthly
                  else (BUG_DATES, BUG_DATES_MANIFEST))
    cells = bug_date_cells(trimmed, periods)
    existing = _load_jsonl(data)
    current = [d for d in existing if d.get("collector") == COLLECTOR]
    kept, todo, stale = reconcile(cells, current,
                                  ("repo", "per", "rng"), "days")
    print(f"pulling {len(todo)} of {len(cells)} dated bug cells "
          f"({len(kept)} reused, {stale} stale dropped, "
          f"{len(existing) - len(current)} from an older collector "
          "re-pulled)", flush=True)
    gp = tuple(group_periods(periods or list(PERIODS)))
    fp = bugs_fingerprint(trimmed, created)

    def flush() -> None:
        # grouping inputs travel with the dated cells, so the low/high-AI
        # halves are read from the same freeze as the rates
        _stamp_denominators(kept, created, gp)
        _freeze(data, mani,
                sorted(kept.values(), key=lambda d: (d["repo"], d["per"])),
                fp, len(cells))

    for i, s in enumerate(todo):
        days = search_issue_days(s["repo"], s["rng"], pace)
        time.sleep(pace)
        if days is None:
            print(f"  MISSING {s['repo']} {s['per']}", flush=True)
            continue
        kept[(s["repo"], s["per"], s["rng"])] = {**s, "days": days,
                                                 "collector": COLLECTOR}
        if (i + 1) % 25 == 0:
            flush()
            print(f"  {i + 1}/{len(todo)}", flush=True)
    flush()
    print(f"froze {len(kept)} dated cells -> {data}", flush=True)
    missing = len(cells) - len(kept)
    if missing:
        print(f"{missing} cells still unpulled (re-run --pull-bug-dates)",
              flush=True)


def bug_days_by_repo(rows: list[dict]) -> dict[str, dict[str, int]]:
    """repo -> {day: issues created that day}, deduped by issue number
    across the deliberately overlapping cell windows."""
    seen: dict[str, dict[int, str]] = defaultdict(dict)
    for d in rows:
        for num, day in d.get("days", []):
            seen[d["repo"]][num] = day
    out: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    for repo, issues in seen.items():
        for day in issues.values():
            out[repo][day] += 1
    return out


def merged_exposure(granularity: str = "quarter",
                    ) -> tuple[dict, list[str]]:
    """(repo, per) -> [(merge_day, capped_added_kloc)] for PRs created AND
    merged in the period — the churn frame's identically-observable
    trimming, carrying merge dates so each PR can open its own risk
    window. Also returns the ordered period list."""
    if granularity == "month":
        from pipeline.analyze import extended_quarters
        periods = finalized_months()
        pset = set(periods)
        frame = study_frame("all", periods=pset,
                            ranges=extended_quarters(),
                            granularity="month")

        def merge_per(merged_at):
            tok = (merged_at or "")[:7]
            return tok if tok in pset else None
    else:
        periods = list(PERIODS)
        frame = study_frame("all")
        merge_per = merge_quarter
    out: dict = defaultdict(list)
    for f in frame:
        if not ai_contrast_eligible(f) or not f.cls.merged_ever:
            continue
        merged_at = f.pr.get("mergedAt")
        if merge_per(merged_at) != f.period:      # same-period trimming
            continue
        out[(f.repo, f.period)].append(
            (merged_at[:10], min(int(f.pr.get("additions") or 0), CAP) / 1000))
    return out, periods


def _days(rng: str) -> list[str]:
    start, end = (_iso(f"{x}T00:00:00Z") for x in rng.split(".."))
    n = (end - start).days
    return [(start + timedelta(days=i)).date().isoformat()
            for i in range(n + 1)]


def _lookback_start(day: str) -> str:
    return (_iso(f"{day}T00:00:00Z")
            - timedelta(days=RISK_DAYS - 1)).date().isoformat()


def exposure_rows(granularity: str = "quarter") -> tuple[list[dict], list]:
    """Per (repo, period) incidence rates over the per-PR risk window.

    Every PR opens a RISK_DAYS window at its merge day; on each day of the
    period the repo is carrying some number of open windows (and some
    volume of recently merged kLOC). Summing bugs filed on those days over
    that exposure gives bugs per PR-risk-window and per kLOC-risk-window —
    the same numerator, two denominators, neither bucketed by month.

    Exposure looks back across period boundaries: a PR merged late in
    one period is still at risk in the next. A day is rated only when its
    whole lookback lies in censused days, so exposure is never understated
    by merges the census did not collect — that burn-in falls at the start
    of each contiguous censused block (Q1-2024; Q4-2025), not on every
    period. Only (repo, period) cells the dated pull froze are rated: an
    unpulled cell has no numerator, not a zero one. A period with merged
    PRs but no added lines keeps its per-PR rate and reports per-kLOC as
    undefined.
    """
    monthly = granularity == "month"
    rows, mani = _verify(*((BUG_DATES_MONTHLY, BUG_DATES_MONTHLY_MANIFEST)
                           if monthly else (BUG_DATES, BUG_DATES_MANIFEST)))
    bugs_by_day = bug_days_by_repo(rows)
    held = {(d["repo"], d["per"]) for d in rows}
    stale_windows = sum(1 for d in rows
                        if d.get("rng") != bug_date_window(d["per"]))
    # label use and grouping inputs are properties of the frozen cells,
    # decided before any day is burnt in or any period dropped
    users = label_users(rows)
    ai_share = {d["repo"]: tuple(d["q2"]) for d in rows if d.get("q2")}
    exposure, periods = merged_exposure(granularity)
    censused: set[str] = set()
    for per in periods:
        censused.update(_days(resolve_period(per)))
    merges_by_repo: dict = defaultdict(lambda: defaultdict(lambda: [0, 0.0]))
    for (repo, _p), merges in exposure.items():
        for day, kloc in merges:
            merges_by_repo[repo][day][0] += 1
            merges_by_repo[repo][day][1] += kloc
    out = []
    for per in periods:
        days = [d for d in _days(resolve_period(per))
                if all(x in censused for x in _days(f"{_lookback_start(d)}..{d}"))]
        for repo in sorted(merges_by_repo):
            if (repo, per) not in held or not days:
                continue
            by_day = merges_by_repo[repo]
            pr_exp = kloc_exp = 0.0
            bugs = 0
            for d in days:
                lo = _lookback_start(d)
                for m, (n, k) in by_day.items():
                    if lo <= m <= d:
                        pr_exp += n
                        kloc_exp += k
                bugs += bugs_by_day.get(repo, {}).get(d, 0)
            if pr_exp <= 0:
                continue
            out.append({"repo": repo, "per": per, "bugs": bugs,
                        "pr_windows": pr_exp / RISK_DAYS,
                        "kloc_windows": kloc_exp / RISK_DAYS,
                        "per_pr": bugs / (pr_exp / RISK_DAYS),
                        "per_kloc": (bugs / (kloc_exp / RISK_DAYS)
                                     if kloc_exp > 0 else None)})
    return out, (periods, {**mani, "stale_windows": stale_windows,
                           "label_users": users, "ai_share": ai_share})


def label_users(cells: list[dict]) -> set[str]:
    """Repos that use the bug label at all, judged on their frozen dated
    cells: a repo with no labeled issue in any window is a probable
    non-user of the taxonomy, not a repo without defects (the counted
    table's exclusion). An issue counts wherever it falls — in burn-in,
    in a period with no exposure — because label use is a property of
    the repo, not of the days the rate happens to cover."""
    return {d["repo"] for d in cells if d.get("days")}


def print_exposure(granularity: str = "quarter",
                   live_fp: str | None = None) -> None:
    """`live_fp` is the fingerprint of the frame the denominators are read
    from; the numerator is frozen, so the table says when the two have
    parted (the counted table's drift line)."""
    rows, (periods, mani) = exposure_rows(granularity)
    users = mani["label_users"]
    rated = {r["repo"] for r in rows}
    excluded = len(rated - users)
    rows = [r for r in rows if r["repo"] in users]
    unit = "month" if granularity == "month" else "quarter"
    print("BUG-REPORT PROXY, PER-PR RISK WINDOW (bug-labeled GH issues — "
          "NOT production incidents). Every merged PR opens a "
          f"{RISK_DAYS}-day window at its MERGE day; a {unit}'s rate is the "
          "issues filed on its days over the exposure carried on those "
          f"days, so no issue is double counted and no window is a "
          f"function of the calendar {unit}. Both denominators are "
          "reported: PR-risk-windows and kLOC-risk-windows (capped "
          f"{CAP:,}/PR). Exposure looks back across contiguous {unit}s; "
          f"the first {RISK_DAYS - 1} days of each censused block are "
          "burn-in (their lookback reaches merges the census did not "
          "collect). Rates are INCIDENCE over overlapping risk sets, not "
          "attribution of an issue to a PR.")
    print(f"frozen dated cells: {mani['held']}/{mani['selected']} "
          f"(as_of {mani['as_of']}); {excluded} repos with zero "
          "bug-labeled issues in every period EXCLUDED as probable "
          "non-users of the label"
          + (f"; {mani['selected'] - mani['held']} cells UNPULLED "
             "(their repo-periods are not rated)"
             if mani["held"] < mani["selected"] else "")
          + (f"; {mani['stale_windows']} cells pulled under a DIFFERENT "
             "window than the current RISK_DAYS — re-pull"
             if mani.get("stale_windows") else ""))
    if live_fp is not None:
        print(_drift_line(mani, live_fp))

    # cuts: every label-using repo; the balanced panel (rated in every
    # period, so a trend cannot be composition); and the counted table's
    # low/high-AI repo halves
    repos = {r["repo"] for r in rows}
    balanced = {r for r in repos
                if all(any(x["repo"] == r and x["per"] == p for x in rows)
                       for p in periods)}
    lo, hi, _unranked = rank_groups(repos, mani["ai_share"])
    groups = (("all", repos), ("balanced", balanced), ("low-AI", lo),
              ("high-AI", hi))
    print(f"{'period':9}{'group':10}{'repos':>6}{'bugs':>7}{'PRwin':>10}"
          f"{'kLOCwin':>10}{'pooled/PR':>11}{'med/PR':>9}"
          f"{'pooled/kLOC':>13}{'med/kLOC':>10}")
    for per in periods:
        for label, grp in groups:
            rs = [r for r in rows if r["per"] == per and r["repo"] in grp]
            if not rs:
                continue
            b = sum(r["bugs"] for r in rs)
            pw = sum(r["pr_windows"] for r in rs)
            kw = sum(r["kloc_windows"] for r in rs)
            per_kloc = [r["per_kloc"] for r in rs
                        if r["per_kloc"] is not None]
            print(f"{per:9}{label:10}{len(rs):>6}{b:>7}{pw:>10.0f}"
                  f"{kw:>10.0f}{b / pw:>11.3f}"
                  f"{median([r['per_pr'] for r in rs]):>9.3f}"
                  + (f"{b / kw:>13.3f}{median(per_kloc):>10.3f}" if kw > 0
                     else f"{'n/a':>13}{'n/a':>10}"))
    print(f"balanced = rated in every {unit}; low/high-AI = halves of the "
          "label-using repos by the counted table's grouping-window "
          "AI-involvement share; pooled rates can be dominated by single "
          "large repos — the pilot is a PR-level draw, so repos enter "
          "probability-proportional-to-size")


def group_periods(periods: list[str]) -> list[str]:
    """The grouping window for low/high-AI membership: the latest
    adoption-era quarter (Q2-2026), or its monthly analog — the last
    three finalized era months."""
    era = adoption_era(periods)
    if era and era[0].startswith("Q"):
        return [era[-1]]
    return era[-3:]


def _stamp_denominators(records: dict, created: dict[str, list],
                        group_pers: tuple[str, ...] = ("Q2-2026",)) -> None:
    """Freeze the table's OTHER inputs into the records: each cell gets
    its creation-bucketed mature-merged denominator, and EVERY row gets
    the repo's grouping-window inputs `q2: [ai_numerator,
    merged_denominator]`, summed over group_pers (the latest era
    quarter, or the last three finalized era months) and stamped on
    EVERY row — a repo whose grouping-window cell is missing from an
    honest partial freeze must still carry its group membership.
    Stamped on every freeze — reused bug counts stay valid (they depend
    only on repo+window) while denominators/groups always reflect the
    frozen frame."""
    merged: dict[tuple[str, str], int] = defaultdict(int)
    ai_num: dict[str, int] = defaultdict(int)
    gset = set(group_pers)
    for per, items in created.items():
        for repo, _num, ai, _a, _d in items:
            merged[(repo, per)] += 1
            if per in gset and ai:
                ai_num[repo] += 1
    for rec in records.values():
        rec["merged"] = merged.get((rec["repo"], rec["per"]), 0)
        rec["q2"] = [ai_num.get(rec["repo"], 0),
                     sum(merged.get((rec["repo"], g), 0)
                         for g in group_pers)]
        rec.pop("ai_num", None)         # superseded Q2-only stamp


def pull_bugs(trimmed: dict[str, list], created: dict[str, list],
              periods: list[str] | None = None,
              pace: float = 2.0) -> None:
    """Count bug-labeled issues per cell (label:bug only — a documented
    proxy limitation). The file is atomically rewritten to exactly the
    current cell selection: counts are reused only when the cell's window
    matches (pre-stamp rows are migrated first; a range change, e.g. an
    AS_OF bump moving the frontier, re-pulls the cell); failures stay
    missing, never zeroed. Denominators and Q2 AI group counts are
    frozen into the records (_stamp_denominators) so the table needs no
    live frame. Checkpoints every 25 cells, each writing data + manifest
    crash-consistently (_freeze)."""
    monthly = periods is not None and bool(periods) \
        and not periods[0].startswith("Q")
    sample_digest = None
    if monthly:
        data, mani = BUGS_MONTHLY, BUGS_MONTHLY_MANIFEST
        sample_rows, sm = _verify(SAMPLE, SAMPLE_MANIFEST)
        sample_digest = sm["digest"]    # same snapshot as sample_rows
        repos = sorted({d["repo"] for d in sample_rows})
        cells = bug_cells(trimmed, periods, repos)
    else:
        data, mani = BUGS, BUGS_MANIFEST
        cells = bug_cells(trimmed, periods)
    gp = tuple(group_periods(periods or list(PERIODS)))
    kept, todo, stale = reconcile(cells, migrate_bug_rows(_load_jsonl(data)),
                                  ("repo", "per", "rng"), "bugs")
    print(f"pulling {len(todo)} of {len(cells)} bug cells "
          f"({len(kept)} reused, {stale} stale dropped)")
    fp = bugs_fingerprint(trimmed, created, sample_digest)

    def flush() -> None:
        _stamp_denominators(kept, created, gp)
        _freeze(data, mani,
                sorted(kept.values(), key=lambda d: (d["repo"], d["per"])),
                fp, len(cells))

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
                             # completed cells, data+manifest in step
    flush()
    missing = len(cells) - len(kept)
    if missing:
        print(f"{missing} cells still unpulled (re-run --pull-bugs)")


def bug_stats(rows: list[dict]) -> tuple[dict, dict, dict]:
    """(bugs, merged, ai_share) built ONLY from frozen records — the
    denominators and Q2 group inputs were stamped at freeze time (on
    every row), so a moved live store cannot shift this table."""
    bugs = {(d["repo"], d["per"]): d["bugs"] for d in rows if "bugs" in d}
    merged = {(d["repo"], d["per"]): d.get("merged", 0) for d in rows}
    ai_share = {d["repo"]: tuple(d["q2"]) for d in rows if d.get("q2")}
    return bugs, merged, ai_share


def rank_groups(with_bugs: set, ai_share: dict,
                ) -> tuple[set, set, set]:
    """(low-AI half, high-AI half, unranked). A repo with a ZERO Q2
    denominator has an UNDEFINED adoption share and belongs to neither
    half (treating undefined as 0.0 silently filed such repos under
    low-AI); it still counts in the 'all' row."""
    rankable = [r for r in with_bugs if ai_share.get(r, (0, 0))[1] > 0]
    ranked = sorted(rankable,
                    key=lambda r: ai_share[r][0] / ai_share[r][1])
    lo = set(ranked[:len(ranked) // 2])
    return lo, set(ranked) - lo, with_bugs - set(ranked)


def print_bugs(trimmed: dict[str, list], created: dict[str, list],
               periods: list[str] | None = None) -> None:
    periods = periods if periods is not None else list(PERIODS)
    monthly = bool(periods) and not periods[0].startswith("Q")
    rows, manifest = _verify(*((BUGS_MONTHLY, BUGS_MONTHLY_MANIFEST)
                               if monthly else (BUGS, BUGS_MANIFEST)))
    bugs, merged, ai_share = bug_stats(rows)
    repos = sorted({r for (r, _p) in bugs})
    with_bugs = {r for r in repos
                 if any(bugs.get((r, p)) for p in periods)}
    lo, hi, unranked = rank_groups(with_bugs, ai_share)
    short = manifest["selected"] - manifest["held"]
    frontier = maturity_frontier(manifest.get("as_of", AS_OF))
    unit = "month" if monthly else "quarter"
    gp = group_periods(periods)
    gp_label = f"{gp[0]}..{gp[-1]}" if len(gp) > 1 else gp[0]
    print("BUG-REPORT PROXY pilot (bug-labeled GH issues — NOT production "
          "incidents): issues labeled bug created per 100 mature merged "
          "PRs. Exposure is creation-bucketed on BOTH sides: denominator "
          f"= mature merged PRs by creation {unit}, numerator window = "
          f"the {unit} truncated at the FROZEN maturity frontier "
          f"({frontier}). Fully FROZEN table — counts, denominators and "
          "grouping inputs all from the frozen records "
          f"({len(repos)} repos"
          + (f", {short} cells unpulled at freeze" if short else "")
          + f"; {len(repos) - len(with_bugs)} with zero bug-labeled "
            f"issues in every {unit} EXCLUDED as probable non-users of "
            f"the label — label:bug only; {len(unranked)} with an "
            "UNDEFINED adoption share (zero merged in the grouping "
            "window) in 'all' but neither AI half)")
    sample_digest = None
    if monthly:
        _srows, sm = _verify(SAMPLE, SAMPLE_MANIFEST)
        sample_digest = sm["digest"]    # verified at THIS read
    print(_drift_line(manifest, bugs_fingerprint(trimmed, created,
                                                 sample_digest)))
    print(f"{'period':9}{'group':9}{'repos':>6}{'bugs':>7}{'merged':>8}"
          f"{'per100':>8}")
    for per in periods:
        for label, grp in (("low-AI", lo), ("high-AI", hi),
                           ("all", with_bugs)):
            rs = [r for r in grp
                  if (r, per) in bugs and merged.get((r, per))]
            b = sum(bugs[(r, per)] for r in rs)
            m = sum(merged[(r, per)] for r in rs)
            if not m:
                continue
            print(f"{per:9}{label:9}{len(rs):>6}{b:>7}{m:>8}"
                  f"{100 * b / m:>8.2f}")
    print(f"groups = halves of the pilot repos by {gp_label} "
          "AI-involvement share among their created-bucketed merged PRs; "
          "pooled group rates can be dominated by single large repos")


# ------------------------------------------------------------------- main

def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--table",
                    choices=["report", "adoption", "census", "sample",
                             "bugs", "exposure"])
    ap.add_argument("--draw", action="store_true",
                    help="print the balanced 0.1% selection")
    ap.add_argument("--pull", action="store_true",
                    help="hydrate per-file splits for the current draw")
    ap.add_argument("--pull-bugs", action="store_true",
                    help="pull bug-label counts for the pilot's repos")
    ap.add_argument("--pull-bug-dates", action="store_true",
                    help="pull bug issues WITH creation days, so any "
                         "window is computable without another pull")
    ap.add_argument("--granularity", choices=["quarter", "month"],
                    default="quarter",
                    help="month = w8-FINALIZED months only (a month "
                         "reports once month_end + 56d <= AS_OF)")
    a = ap.parse_args()
    if not (a.table or a.draw or a.pull or a.pull_bugs
            or a.pull_bug_dates):
        ap.error("pick --table/--draw/--pull/--pull-bugs/--pull-bug-dates")
    if a.granularity == "month" and (a.pull or a.table == "sample"
                                     or a.draw):
        ap.error("the 0.1% file-level sample is quarterly-only "
                 "(--draw/--pull/--table sample)")
    trimmed, created, cross, periods = eligible(a.granularity)
    month = a.granularity == "month"
    if a.draw:
        sel = draw(trimmed)
        by = defaultdict(int)
        for s in sel:
            by[(s["per"], s["ai"])] += 1
        print(f"{len(sel)} PRs selected: " + ", ".join(
            f"{p} AI={by[(p, True)]}/nonAI={by[(p, False)]}"
            for p in periods))
    if a.pull:
        pull(trimmed)
    if a.pull_bugs:
        pull_bugs(trimmed, created, periods)
    if a.pull_bug_dates:
        pull_bug_dates(trimmed, created, periods)
    org_min = ORG_MIN_PRS_MONTH if month else ORG_MIN_PRS
    min_prs = MIN_PRS_MONTH if month else MIN_PRS
    if a.table in ("report", "adoption"):
        print_adoption(trimmed, cross, periods, org_min)
    if a.table in ("report", "census"):
        if a.table == "report":
            print()
        print_census(trimmed, periods, min_prs)
    if a.table == "sample":
        print_sample(trimmed)
    elif a.table == "bugs":
        print_bugs(trimmed, created, periods)
    elif a.table == "exposure":
        print_exposure(a.granularity,
                       live_fp=bugs_fingerprint(trimmed, created))


if __name__ == "__main__":
    main()
