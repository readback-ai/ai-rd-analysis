"""Study: where could the author's own review of AI code show up? (§11d–e)

Formal review objects miss author self-review, which can happen (1) in the
tool session before committing, (2) on the branch before opening the PR,
(3) on the open PR before merging. Each mode leaves a measurable residue:

- mode1_interleaving: population-scale, census-only. Merged human-authored
  AI-code PRs: all-AI-commit vs mixed human+AI commit sequences, and human
  fix-up commits after AI commits (evidence the human read and corrected).
- session_residue: within multi-commit ALL-AI-commit PRs, classify follow-up
  commit messages: external-review response / author in-session redirect /
  mechanical self-heal / plain progression (§11e taxonomy).
- timing (modes 2+3): hydrates per-commit committedDate via pull_prs to
  measure the last-commit->PR-open pause and the open->merge window per lane.
  Caveat: rebase/amend resets committedDate toward push time — compare across
  cohorts, not absolute levels.

Usage:
  python -m pipeline.studies.review_modes --mode interleaving
  python -m pipeline.studies.review_modes --mode residue
"""
from __future__ import annotations

import argparse
import re

from pipeline.analyze import group_by_period, load_cells
from pipeline.detect import MARKERS_V1, ToolSpec
from pipeline.scan_orgs import QUARTER_RANGES

FIXWORDS = ("fix", "clean", "tweak", "address", "correct", "adjust",
            "polish", "revert", "typo", "review")
# §11e classifier: external-review response beats author redirect beats
# mechanical self-heal (first match wins, most-specific first).
EXT_REV = re.compile(
    r"(address (pr|the |review|copilot|cursor|coderabbit|codex|greptile)"
    r"|pr #?\d+ review|review feedback|reviewer feedback|per @"
    r"|code review feedback|cr feedback|review nits|review findings"
    r"|review comments)", re.I)
AUTHOR_DIR = re.compile(
    r"(\brevert\b|instead of|switch(ed)? to|rework|redesign|rethink"
    r"|drop the|simplif|per (the )?(user|request|discussion)"
    r"|as (suggested|requested)|round-\d|restore original)", re.I)
MECH = re.compile(
    r"(fix (lint|test|tests|build|ci|type|typo|format|compile|import"
    r"|clippy|mypy|prettier)|\blint\b|\bformat\b|pre-commit|ruff|gofmt"
    r"|clang-format|failing (test|check)|cargo fmt|update golden"
    r"|regenerate|bump|dedupe)", re.I)


def commit_ai(c: dict, markers: dict[str, ToolSpec] = MARKERS_V1) -> bool:
    commit = c.get("commit") or {}
    hay = commit.get("message") or ""
    for a in (commit.get("authors") or {}).get("nodes") or []:
        hay += "\n" + ((a or {}).get("email") or "")
    return any(n in hay for spec in markers.values() for n in spec.needles)


def _merged_ai_pr_commits(periods: list[str]):
    grouped = group_by_period(load_cells(), QUARTER_RANGES)
    for (repo, per), prs in grouped.items():
        if per not in periods:
            continue
        for pr in prs:
            if (pr.get("author") or {}).get("__typename") == "Bot":
                continue
            if not pr.get("mergedAt"):
                continue
            commits = (pr.get("commits") or {}).get("nodes") or []
            if not commits:
                continue
            flags = [commit_ai(c) for c in commits]
            if any(flags):
                yield per, repo, pr, commits, flags


def mode1_interleaving(periods: list[str]) -> None:
    """§11d mode 1: human-touch residue inside merged AI-code PRs."""
    agg: dict[str, list[int]] = {p: [0, 0, 0, 0] for p in periods}  # n, allai, mixed, fixup
    for per, _, _, commits, flags in _merged_ai_pr_commits(periods):
        d = agg[per]
        d[0] += 1
        if all(flags):
            d[1] += 1
            continue
        d[2] += 1
        seen_ai = False
        for c, f in zip(commits, flags):
            if f:
                seen_ai = True
            elif seen_ai:
                msg = ((c.get("commit") or {}).get("message") or "").lower()
                if any(w in msg for w in FIXWORDS):
                    d[3] += 1
                    break
    print(f"{'period':9}{'N':>7}{'all-AI':>8}{'mixed':>7}{'humanFixupAfterAI':>19}")
    for per, (n, allai, mixed, fixup) in agg.items():
        if n:
            print(f"{per:9}{n:>7}{100*allai/n:>7.0f}%{100*mixed/n:>6.0f}%"
                  f"{100*fixup/n:>18.0f}%")


def session_residue(periods: list[str]) -> None:
    """§11e: follow-up commit-message classes in multi-commit all-AI PRs."""
    agg: dict[str, list[int]] = {p: [0, 0, 0, 0, 0] for p in periods}
    for per, _, _, commits, flags in _merged_ai_pr_commits(periods):
        if not all(flags) or len(commits) < 2:
            continue
        d = agg[per]
        d[0] += 1
        tail = "\n".join(((c.get("commit") or {}).get("message") or "")
                         for c in commits[1:])
        if EXT_REV.search(tail):
            d[1] += 1
        elif AUTHOR_DIR.search(tail):
            d[2] += 1
        elif MECH.search(tail):
            d[3] += 1
        else:
            d[4] += 1
    print(f"{'period':9}{'multi-commit all-AI':>20}{'ext-review%':>12}"
          f"{'author-redirect%':>17}{'mech-only%':>11}{'plain%':>8}")
    for per, (n, ext, auth, mech, plain) in agg.items():
        if n:
            print(f"{per:9}{n:>20}{100*ext/n:>11.0f}%{100*auth/n:>16.0f}%"
                  f"{100*mech/n:>10.0f}%{100*plain/n:>7.0f}%")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["interleaving", "residue"],
                    default="interleaving")
    ap.add_argument("--periods", nargs="+",
                    default=["Q4-2025", "Q1-2026", "Q2-2026"])
    a = ap.parse_args()
    (mode1_interleaving if a.mode == "interleaving" else session_residue)(a.periods)


if __name__ == "__main__":
    main()
