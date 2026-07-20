"""Stage 4 — HOW METRICS ARE CREATED from census cells (bootstrap CIs).

Reads raw/census/ cells, classifies each PR once via detect.classify_pr, turns
the classifications into per-repo-period rates, then reports equal-weight and
contributor-weighted averages per period with bootstrap 95% CIs over repos.
Detection semantics (marker sets, reviewer taxonomies, the reviewer!=author
correction) all live in pipeline.detect — nothing here re-defines them.

human_review keeps the LEGACY any-User-reviewer definition so published tables
reproduce exactly; human_review is the reviewer!=author, bot-clean rate
(v2_results §11c). self_merged is only available in cells pulled after
2026-07-08 (mergedBy added to the census query) and reports nan before that.

PRs are DEDUPED by number within each (repo, period): the durable store can
hold overlapping cell generations (full-quarter + sub-window cells, or cells
pulled under an older quarter definition), and summing them double-counted.

Usage:
  python -m pipeline.analyze --contributors data/repo_contributors.csv \
      --bootstrap 2000
"""
from __future__ import annotations

import argparse
import csv
import re
import random
from collections import defaultdict
from pathlib import Path

from pipeline.detect import MARKERS, classify_pr
from pipeline.ghx import decode_cell_stem, raw_dir, read_cell


def load_cells() -> dict[tuple[str, str], list[dict]]:
    """(repo, date-range) -> PR nodes from the census-v2 store (the single
    store since 2026-07-20: the 187 repo-quarters that existed only as
    legacy census cells were re-collected, and the legacy read path was
    removed). Files are visited OLDEST-mtime-first so fresher cells land
    later in the dict — group_by_period's dedup lets the fresher record
    win at equal richness (monthly re-collection vs a stale overlapping
    quarter cell; external review P1)."""
    cells: dict[tuple[str, str], list[dict]] = {}
    for f in sorted(raw_dir("census-v2").glob("*.json"),
                    key=lambda p: p.stat().st_mtime):
        nodes = read_cell(f, list)
        if nodes is None:
            continue
        parts = decode_cell_stem(f.stem)
        if len(parts) != 2:
            continue
        cells[(parts[0], parts[1])] = [n for n in nodes if n]
    return cells


def period_of(rng: str, quarters: dict[str, str]) -> str | None:
    start = rng.split("..")[0]
    for q, qr in quarters.items():
        if qr.split("..")[0] <= start <= qr.split("..")[1]:
            return q
    return None


CENSUSED_QUARTERS = ["Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026"]
INCREMENTAL_REGISTRY = Path("data/derived/incremental_months.txt")


def incremental_months() -> list[str]:
    """Month tokens collected by monthly_update AFTER the frozen quarters —
    persisted in a registry so every later analysis (not just the updating
    invocation) keeps them (external review P1: a September update must not
    silently drop July)."""
    if not INCREMENTAL_REGISTRY.is_file():
        return []
    return sorted({ln.strip() for ln in
                   INCREMENTAL_REGISTRY.read_text().splitlines()
                   if re.fullmatch(r"\d{4}-\d{2}", ln.strip())})


def extended_quarters(extra: list[str] | None = None) -> dict[str, str]:
    """Frozen quarters + registered incremental months (+ any explicit
    extras). Frozen quarters stay first, so they keep period_of priority."""
    from pipeline.scan_orgs import QUARTER_RANGES, resolve_period
    quarters = dict(QUARTER_RANGES)
    for tok in [*incremental_months(), *(extra or [])]:
        quarters.setdefault(tok, resolve_period(tok))
    return quarters


def censused_months(quarters: dict[str, str]) -> set[str]:
    """Months lying inside FULLY censused quarters, plus any explicit
    YYYY-MM keys (incremental months from monthly_update, passed via
    analyze --periods). Stray cells from partially-pulled windows
    (Q3-2025) must not surface as reportable months — ~60-repo coverage
    is not the population."""
    out = set()
    for q in CENSUSED_QUARTERS:
        if q not in quarters:
            continue
        start = quarters[q].split("..")[0]
        y, m = int(start[:4]), int(start[5:7])
        for i in range(3):
            out.add(f"{y}-{m + i:02d}")
    out.update(k for k in quarters if re.fullmatch(r"\d{4}-\d{2}", k))
    return out


def month_of(pr: dict) -> str | None:
    m = (pr.get("createdAt") or "")[:7]
    return m or None


def group_by_period(cells: dict[tuple[str, str], list[dict]],
                    quarters: dict[str, str],
                    granularity: str = "quarter") -> dict[tuple[str, str], list[dict]]:
    """(repo, period) -> PRs, deduped by PR number across cell generations.
    granularity='month' buckets PRs by createdAt month (every PR's createdAt
    lies inside its cell's range, so month buckets are exact re-partitions of
    the sampled quarters — no recollection needed).
    When the same PR appears in overlapping cells (legacy full-quarter +
    census-v2 sub-window), the RICHER record wins: a node carrying
    headRefName (the v2 query marker field) replaces one that lacks it,
    regardless of iteration order — otherwise a stale legacy record silently
    strips branch attribution and mergedBy (external review P1). At EQUAL
    richness the LATER-loaded record wins; load_cells feeds cells in mtime
    order, so a monthly re-collection supersedes a stale overlapping
    quarter cell for the same PR (external review P1, round 2)."""
    grouped: dict[tuple[str, str], list[dict]] = defaultdict(list)
    index: dict[tuple[str, str], dict] = defaultdict(dict)
    for (repo, rng), nodes in cells.items():
        quarter = period_of(rng, quarters)
        if not quarter:
            continue
        ok_months = censused_months(quarters) if granularity == "month" else None
        for pr in nodes:
            per = quarter if granularity == "quarter" else month_of(pr)
            if per is None or (ok_months is not None and per not in ok_months):
                continue
            key = (repo, per)
            num = pr.get("number")
            if num is None:
                grouped[key].append(pr)
                continue
            prev = index[key].get(num)
            if prev is None:
                index[key][num] = pr
                grouped[key].append(pr)
            elif ("headRefName" in pr) >= ("headRefName" in prev):
                # richer wins; at equal richness, fresher (later-loaded) wins
                grouped[key][grouped[key].index(prev)] = pr
                index[key][num] = pr
    return grouped


def pr_metrics(pr: dict, markers: dict) -> dict:
    c = classify_pr(pr, markers)
    return {
        "ai_code": bool(c.marker_tools),
        "ai_involved": c.ai_involved,          # all 3 layers (needs headRefName)
        # FROZEN CENSORING RULE: outcomes at 8 weeks post-creation, defined
        # only on w8-mature PRs (immature -> None -> skipped)
        "merged": c.merged if c.w8_mature else None,
        "rejected_w8": c.rejected if c.w8_mature else None,
        "limbo_w8": (not c.merged and not c.rejected) if c.w8_mature else None,
        "human_review": c.human_reviewed,      # reviewer != author, bot-clean
        "ai_review": c.ai_reviewed,
        "other_bot_review": c.other_bot_reviewed,
        "no_review": not (c.human_reviewed or c.ai_reviewed
                          or c.other_bot_reviewed),
        "insider": c.insider,
        # None (field absent in pre-2026-07-08 cells) -> skipped by rate calc
        "self_merged": c.self_merged,
        # merged-conditioned rates (None on unmerged PRs -> conditioning by
        # skip): unmerged PRs are implicitly reviewed-and-rejected, so
        # reviewer coverage OF WHAT SHIPS is its own question (METRICS §2b)
        "m_hum_rev": c.human_reviewed if c.merged else None,
        "m_ai_rev": c.ai_reviewed if c.merged else None,
        "m_no_rev": (not c.human_reviewed and not c.ai_reviewed
                     and not c.other_bot_reviewed) if c.merged else None,
    }


METRICS = ["ai_code", "ai_involved", "merged", "rejected_w8", "limbo_w8",
           "human_review", "ai_review", "other_bot_review",
           "no_review", "insider", "self_merged",
           "m_hum_rev", "m_ai_rev", "m_no_rev"]


def weighted_mean(pairs: list[tuple[float, float]]) -> float:
    tot = sum(w for _, w in pairs)
    return sum(v * w for v, w in pairs) / tot if tot else float("nan")


_RNG = random.Random(20260630)      # seeded: reruns reproduce identical CIs


def bootstrap_ci(pairs: list[tuple[float, float]], n: int = 2000) -> tuple[float, float]:
    if len(pairs) < 2:
        return (float("nan"), float("nan"))
    stats = sorted(weighted_mean(_RNG.choices(pairs, k=len(pairs))) for _ in range(n))
    return stats[int(0.025 * n)], stats[int(0.975 * n)]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--contributors", default="data/repo_contributors.csv")
    ap.add_argument("--repos", default=None,
                    help="optional repo-list file: restrict metrics to this "
                         "population (e.g. v2.1 rebaseline)")
    ap.add_argument("--granularity", choices=["quarter", "month"],
                    default="quarter")
    ap.add_argument("--min-prs", type=int, default=None,
                    help="repo floor per period; default 5/quarter, 2/month "
                         "(comparable thresholds — METRICS §3)")
    ap.add_argument("--bootstrap", type=int, default=2000)
    ap.add_argument("--periods", nargs="*", default=[],
                    help="extra YYYY-MM tokens beyond the frozen quarters "
                         "(incremental months from monthly_update)")
    a = ap.parse_args()
    markers = MARKERS
    weights: dict[str, float] = {}
    if Path(a.contributors).is_file():
        with open(a.contributors) as fh:
            for row in csv.DictReader(fh):
                val = row.get("core_contributors_window",
                              row.get("core_contributors"))
                try:
                    weights[row["repo"]] = max(float(val), 1.0)
                except (TypeError, ValueError):
                    pass

    if a.min_prs is None:
        a.min_prs = 5 if a.granularity == "quarter" else 2
    quarters = extended_quarters(a.periods)
    grouped = group_by_period(load_cells(), quarters, a.granularity)
    if not grouped:
        raise SystemExit("no census cells found in $AIRD_DATA_DIR — the "
                         "external store is required (docs/METHODS.md §5); "
                         "refusing to print an empty report")
    if a.repos:
        keep = {ln.split("\t")[0].strip() for ln in Path(a.repos).read_text().splitlines()
                if ln.strip() and not ln.startswith("#")}
        grouped = {k: v for k, v in grouped.items() if k[0] in keep}

    extra = sorted(set(incremental_months()) | set(a.periods))
    periods = (CENSUSED_QUARTERS + extra) \
        if a.granularity == "quarter" else sorted({p for (_, p) in grouped})
    print(f"{'period':9}{'weighting':16}{'repos':>6}" +
          "".join(f"{m:>18}" for m in METRICS))
    for per in periods:
        rows = []
        unweighted = set()
        for (repo, p), prs in grouped.items():
            if p != per or len(prs) < a.min_prs:
                continue
            if repo not in weights:
                unweighted.add(repo)
            ms = [pr_metrics(pr, markers) for pr in prs]
            rates = {}
            for m in METRICS:
                vals = [x[m] for x in ms if x[m] is not None]
                rates[m] = sum(vals) / len(vals) if vals else None
            rows.append((repo, rates))
        if not rows:
            continue
        if unweighted:
            print(f"WARN {per}: {len(unweighted)} qualifying repos lack "
                  f"contributor weights (default 1.0) — e.g. "
                  f"{sorted(unweighted)[:3]}", flush=True)
        for label, wfn in (("equal-weight", lambda r: 1.0),
                           ("contrib-weight", lambda r: weights.get(r, 1.0))):
            line = f"{per:9}{label:16}{len(rows):>6}"
            for m in METRICS:
                pairs = [(rates[m], wfn(repo)) for repo, rates in rows
                         if rates[m] is not None]
                if not pairs:
                    line += f"  {'n/a':>17}"
                    continue
                mean = weighted_mean(pairs)
                lo, hi = bootstrap_ci(pairs, a.bootstrap)
                line += f"  {100*mean:5.1f} [{100*lo:4.1f},{100*hi:4.1f}]"
            print(line)


if __name__ == "__main__":
    main()
