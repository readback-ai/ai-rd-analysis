"""Regenerate the study on the clean population (pipeline.org_set).

Staged, resumable driver — every stage is checkpointed by the underlying
modules, so rerunning after interruption is safe and cheap.

  A. enum_strata      AI-topic repos of repo-scoped orgs -> strata_repos.tsv
  B. population repos full-org members' censused repos + strata repos
                      -> data/derived/population_repos.txt
  C. precount+census  fill cells for repos never censused (4 quarters)
  D. contributors     core-contributor weights for new repos
  E. convergence      recompute census-based evidence; re-run org_set; warn
                      if the population changed (uniform-evidence check)
  F. report           analyze (contributor-weighted) on population_repos

Run:  PYTHONPATH=src python scripts/regenerate.py
"""
import csv
import json
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, "src")
from pipeline.org_set import DRV, population  # noqa: E402

ENV = None  # inherit


def run(mod: str, *args: str) -> None:
    r = subprocess.run([sys.executable, "-m", mod, *args])
    if r.returncode != 0:
        raise SystemExit(f"{mod} failed")


def stage_a() -> None:
    print("=== A: strata repo enumeration ===", flush=True)
    run("pipeline.enum_strata")


def stage_b() -> Path:
    print("=== B: population repo list ===", flush=True)
    full = set(population(scope="full"))
    censused = (DRV / "census_repos_frozen.txt").read_text().split()
    repos = {r for r in censused if r.split("/")[0] in full}
    n_full = len(repos)
    for ln in (DRV / "strata_repos.tsv").read_text().splitlines():
        f = ln.split("\t")
        if len(f) == 3 and f[1] != "DONE":
            repos.add(f[1])
    out = DRV / "population_repos.txt"
    out.write_text("\n".join(sorted(repos)) + "\n")
    print(f"population repos: {len(repos)} ({n_full} full-org + "
          f"{len(repos) - n_full} strata-only)", flush=True)
    return out


def stage_c(repos_file: Path) -> None:
    print("=== C: precount + census gap fill ===", flush=True)
    run("pipeline.precount", "--repos", str(repos_file),
        "--periods", "Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026")
    run("pipeline.census", "--repos", str(repos_file),
        "--periods", "Q1-2024", "Q4-2025", "Q1-2026", "Q2-2026")


def stage_d(repos_file: Path) -> None:
    print("=== D: contributor weights ===", flush=True)
    weights = DRV / "repo_contributors_v2.csv"
    have = {row[0] for row in csv.reader(weights.open()) if row}
    todo = [r for r in repos_file.read_text().split() if r not in have]
    print(f"pulling contributors for {len(todo)} repos", flush=True)
    with weights.open("a") as out:
        w = csv.writer(out)
        for repo in todo:
            r = subprocess.run(
                ["gh", "api", f"repos/{repo}/contributors?per_page=100",
                 "--paginate", "--jq",
                 '[.[] | select((.type != "Bot") and (.contributions >= 10))] | length'],
                capture_output=True, text=True)
            counts = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
            w.writerow([repo, sum(counts) if r.returncode == 0 and counts else 1])
            time.sleep(0.4)


def stage_e() -> None:
    print("=== E: evidence convergence check ===", flush=True)
    from pipeline.analyze import group_by_period, load_cells
    from pipeline.detect import (MARKERS_V2, pr_agent_author, pr_ai_tools,
                                 pr_branch_tool)
    from pipeline.scan_orgs import QUARTER_RANGES
    ev: dict[str, list[int]] = {}
    for (repo, _), prs in group_by_period(load_cells(), QUARTER_RANGES).items():
        org = repo.split("/")[0].lower()
        e, t = ev.setdefault(org, [0, 0])
        for p in prs:
            t += 1
            if pr_ai_tools(p, MARKERS_V2) or pr_agent_author(p) or pr_branch_tool(p):
                e += 1
        ev[org] = [e, t]
    json.dump(ev, (DRV / "census_org_evidence.json").open("w"))
    before = set(population())
    run("pipeline.org_set")
    after = set(population())
    if before != after:
        print(f"WARN population changed on uniform evidence: "
              f"+{sorted(after - before)} -{sorted(before - after)}", flush=True)
    else:
        print("population stable under uniform census evidence", flush=True)


def stage_f(repos_file: Path) -> None:
    print("=== F: contributor-weighted report ===", flush=True)
    run("pipeline.analyze", "--contributors", str(DRV / "repo_contributors_v2.csv"),
        "--repos", str(repos_file), "--bootstrap", "1000")


if __name__ == "__main__":
    stage_a()
    repos = stage_b()
    stage_c(repos)
    stage_d(repos)
    stage_e()
    repos = stage_b()          # strata may have grown if org_set changed
    stage_f(repos)
    print("=== REGENERATION COMPLETE ===", flush=True)
