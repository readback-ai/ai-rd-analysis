"""Regenerate the study on the clean population (pipeline.org_set).

Staged, resumable driver — every stage is checkpointed by the underlying
modules, so rerunning after interruption is safe and cheap.

  A. enum_strata      AI-topic repos of repo-scoped orgs -> strata_repos.tsv
  B. population repos full-org members' censused repos + strata repos
                      -> data/derived/population_repos.txt
  C. precount+census  fill cells for repos never censused (4 quarters)
  D. contributors     core-contributor weights for new repos
  E. convergence      recompute census-based evidence; re-run org_set; if
                      the population changed, LOOP back to A (bounded) so new
                      members are collected before reporting
  F. report           analyze + integrate + slices written to
                      artifacts/report_generated.md, plus a census manifest

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


REPO_RE = __import__("re").compile(r"[\w.-]+/[\w.-]+")


def stage_b() -> Path:
    """Assemble the canonical repo manifest with validation: every entry is
    owner/repo-shaped, every org traces to population.tsv, and classification
    coverage (org_type) is complete (external review finding 5)."""
    print("=== B: population repo list ===", flush=True)
    full = set(population(scope="full"))
    scoped = set(population(scope="repo"))
    censused = (DRV / "fullorg_repos.txt").read_text().split()
    repos = {r for r in censused if r.split("/")[0] in full}
    n_full = len(repos)
    for ln in (DRV / "strata_repos.tsv").read_text().splitlines():
        f = ln.split("\t")
        if len(f) == 3 and f[1] != "DONE" and f[0] in scoped:
            repos.add(f[1])
    bad = [r for r in repos if not REPO_RE.fullmatch(r)]
    if bad:
        raise SystemExit(f"malformed repo entries: {bad[:5]}")
    orphans = {r.split("/")[0] for r in repos} - full - scoped
    if orphans:
        raise SystemExit(f"repos from orgs outside population.tsv: {sorted(orphans)[:5]}")
    types = {ln.split("\t")[0].lower()
             for ln in (Path("data/sources/org_type.tsv").read_text().splitlines())
             if ln.strip() and not ln.startswith("#")}
    untyped = {o for o in full | scoped if o.lower() not in types}
    if untyped:
        raise SystemExit(f"population orgs missing org_type rows: {sorted(untyped)[:5]}")
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
        failed = 0
        for repo in todo:
            r = subprocess.run(
                ["gh", "api", f"repos/{repo}/contributors?per_page=100",
                 "--paginate", "--jq",
                 '[.[] | select((.type != "Bot") and (.contributions >= 10))] | length'],
                capture_output=True, text=True)
            counts = [int(x) for x in r.stdout.split() if x.strip().isdigit()]
            if r.returncode == 0 and counts:
                w.writerow([repo, sum(counts)])
            else:
                failed += 1          # do NOT record: a permanent weight=1 is
            time.sleep(0.4)          # worse than a retry on the next run
        if failed:
            print(f"WARN: {failed} contributor pulls failed; rerun stage D "
                  f"to retry (weights default to 1.0 until then)", flush=True)


def stage_e() -> bool:
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
        print(f"population changed on uniform evidence: "
              f"+{sorted(after - before)} -{sorted(before - after)} — "
              f"looping to collect new members", flush=True)
        return False
    print("population stable under uniform census evidence", flush=True)
    return True


def stage_f(repos_file: Path) -> None:
    """Write the generated report artifact + census manifest (the numbers
    behind artifacts/results.md come from THIS file, not ad-hoc runs)."""
    print("=== F: report artifact ===", flush=True)
    import hashlib
    out = Path("artifacts/report_generated.md")
    with out.open("w") as fh:
        fh.write("# GENERATED report — scripts/regenerate.py\n\n")
        for title, args in (
            ("Contributor-weighted metrics",
             ["pipeline.analyze", "--contributors",
              str(DRV / "repo_contributors_v2.csv"),
              "--repos", str(repos_file), "--bootstrap", "2000"]),
            ("Layered decomposition (pooled)", ["pipeline.integrate"]),
            ("Slices: involvement", ["pipeline.studies.slices",
                                     "--table", "involvement"]),
            ("Slices: self-merge", ["pipeline.studies.slices",
                                    "--table", "selfmerge"]),
        ):
            r = subprocess.run([sys.executable, "-m", *args],
                               capture_output=True, text=True)
            if r.returncode != 0:
                raise SystemExit(f"{args[0]} failed:\n{r.stderr[-800:]}")
            fh.write(f"## {title}\n```\n{r.stdout}\n```\n\n")
    manifest = {
        "population_repos": hashlib.sha256(
            repos_file.read_bytes()).hexdigest()[:16],
        "population": hashlib.sha256(
            (DRV / "population.tsv").read_bytes()).hexdigest()[:16],
        "repos": len(repos_file.read_text().split()),
    }
    (DRV / "census_manifest.json").write_text(json.dumps(manifest, indent=1))
    print(f"wrote {out} + census_manifest.json", flush=True)


if __name__ == "__main__":
    for _round in range(3):            # fixed-point loop on the population
        stage_a()
        repos = stage_b()
        stage_c(repos)
        stage_d(repos)
        if stage_e():
            break
    else:
        raise SystemExit("population did not converge in 3 rounds")
    repos = stage_b()
    stage_f(repos)
    print("=== REGENERATION COMPLETE ===", flush=True)
