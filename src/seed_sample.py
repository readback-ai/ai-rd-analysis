"""Phase 0.2 seed sample: pull one recent month of agent activity and extract the
unique repo list to draw the hand-labeled gold set from.

Two detection paths (per agents.yaml):
  - author_search : /search/issues  author:<bot>          (Devin, Copilot, Cursor, Jules)
  - commit_search : /search/commits committer/author-email (Codex, Claude Code)

Caps each (agent, query) at the Search API's 1000-result ceiling -- this is a
diversity sample for labeling, not exhaustive collection. Writes:
  data/sample/repo_sample.csv   one row per unique repo, with which agents hit it
"""
from __future__ import annotations
import csv
import sys
from collections import defaultdict
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh import search  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
WINDOW = "2026-05-01..2026-05-31"          # last complete month before collection
OUT = ROOT / "data" / "sample" / "repo_sample.csv"


def slug_from_repo_url(url: str) -> str:
    # https://api.github.com/repos/<owner>/<name>  ->  owner/name
    return url.split("/repos/", 1)[1] if "/repos/" in url else ""


def main() -> None:
    agents = yaml.safe_load((ROOT / "agents.yaml").read_text())["agents"]

    # repo full_name -> {"id":..., "owner":..., "agents":set(), "hits":int}
    repos: dict[str, dict] = defaultdict(
        lambda: {"id": "", "owner": "", "agents": set(), "hits": 0}
    )

    for a in agents:
        name = a["name"]
        # ---- author-search agents ----
        for login in a.get("author_logins") or []:
            q = f"is:pr author:{login} created:{WINDOW}"
            n = 0
            for it in search("issues", q, sort="created"):
                slug = slug_from_repo_url(it.get("repository_url", ""))
                if not slug:
                    continue
                r = repos[slug]
                r["owner"] = slug.split("/")[0]
                r["agents"].add(name)
                r["hits"] += 1
                n += 1
            print(f"  {name:16} author:{login:30} hits={n}", file=sys.stderr)

        # ---- commit-search agents (emails + committer logins) ----
        emails = a.get("commit_author_email") or []
        committers = a.get("commit_committer") or []
        for sel in [f"author-email:{e}" for e in emails] + [f"committer:{c}" for c in committers]:
            q = f"{sel} committer-date:{WINDOW}"
            n = 0
            for it in search("commits", q, sort="committer-date"):
                repo = it.get("repository") or {}
                slug = repo.get("full_name", "")
                if not slug:
                    continue
                r = repos[slug]
                r["id"] = repo.get("id", r["id"])
                r["owner"] = (repo.get("owner") or {}).get("login", r["owner"])
                r["agents"].add(name)
                r["hits"] += 1
                n += 1
            print(f"  {name:16} {sel:38} hits={n}", file=sys.stderr)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    with OUT.open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["full_name", "repo_id", "owner_login", "agents", "n_hits"])
        for slug, r in sorted(repos.items(), key=lambda kv: -kv[1]["hits"]):
            w.writerow([slug, r["id"], r["owner"], "|".join(sorted(r["agents"])), r["hits"]])

    print(f"\nUnique repos: {len(repos)}  ->  {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
