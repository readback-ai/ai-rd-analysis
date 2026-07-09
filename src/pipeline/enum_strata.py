"""Stage 2b — repo enumeration for REPO-SCOPED population members.

A repo-scoped org (population.tsv scope=repo) contributes only its AI-topic
repos (rule R5). This stage enumerates them by full pagination over the org's
repositories, keeping any repo whose maintainer topics intersect AI_TOPICS.
No star floor here: the org already passed admission; small AI repos of an
admitted org are in-scope (the census evidence rule still applies at the
metrics layer).

Checkpointed per org into data/derived/strata_repos.tsv (org, repo, stars);
reruns skip enumerated orgs.

Usage:
  python -m pipeline.enum_strata
"""
from __future__ import annotations

import argparse
import time
from pathlib import Path

from pipeline.ghx import graphql_nodes
from pipeline.org_set import AI_TOPICS, DRV, population

Q = """
query($org:String!, $cur:String){ organization(login:$org){
  repositories(first:100, orderBy:{field:STARGAZERS, direction:DESC},
               privacy:PUBLIC, isFork:false, after:$cur){
    pageInfo{ hasNextPage endCursor }
    nodes{ name stargazerCount
      repositoryTopics(first:20){ nodes{ topic{ name } } } } } } }
"""


def enum_org(org: str, max_pages: int = 40) -> list[tuple[str, int]] | None:
    """AI-topic repos of one org, or None on API failure."""
    cur, out, pages = None, [], 0
    while pages < max_pages:
        data = graphql_nodes(Q, {"org": org, **({"cur": cur} if cur else {})},
                             ".data.organization.repositories", expect=dict)
        if data is None:
            return None
        for r in data.get("nodes") or []:
            topics = {t["topic"]["name"]
                      for t in (r.get("repositoryTopics") or {}).get("nodes") or []}
            if topics & AI_TOPICS:
                out.append((f"{org}/{r['name']}", r["stargazerCount"]))
        pages += 1
        pi = data.get("pageInfo") or {}
        if not pi.get("hasNextPage"):
            break
        cur = pi.get("endCursor")
        time.sleep(1)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(DRV / "strata_repos.tsv"))
    a = ap.parse_args()
    out_path = Path(a.out)
    done = {ln.split("\t")[0] for ln in out_path.read_text().splitlines()
            if "\t" in ln} if out_path.exists() else set()
    with out_path.open("a") as f:
        for org in population(scope="repo"):
            if org in done:
                continue
            repos = enum_org(org)
            if repos is None:
                print(f"FAIL {org}", flush=True)
                continue
            for repo, stars in repos:
                f.write(f"{org}\t{repo}\t{stars}\n")
            f.write(f"{org}\tDONE\t0\n")
            f.flush()
            print(f"ok {org}: {len(repos)} AI-topic repos", flush=True)
    print("strata enumeration complete")


if __name__ == "__main__":
    main()
