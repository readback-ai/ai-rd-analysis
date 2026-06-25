"""Phase 0.2: batch-fetch lightweight repo metadata for the seed sample, so we can
stratify before drawing the gold set. Uses GraphQL aliases (~40 repos/query) to
stay well under rate limits. README/manifests are fetched later, only for the
selected gold repos.

Writes data/sample/repo_meta.csv.
"""
from __future__ import annotations
import csv
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gh import gql  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
IN = ROOT / "data" / "sample" / "repo_sample.csv"
OUT = ROOT / "data" / "sample" / "repo_meta.csv"
BATCH = 40

FIELDS = """
  nameWithOwner description isFork isArchived stargazerCount forkCount
  primaryLanguage { name }
  pushedAt createdAt
  repositoryTopics(first: 25) { nodes { topic { name } } }
"""


def esc(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def build_query(batch: list[tuple[str, str]]) -> str:
    parts = []
    for i, (owner, name) in enumerate(batch):
        parts.append(
            f'r{i}: repository(owner: "{esc(owner)}", name: "{esc(name)}") {{{FIELDS}}}'
        )
    return "query {\n" + "\n".join(parts) + "\n}"


def main() -> None:
    rows = list(csv.DictReader(IN.open()))
    pairs = []
    for r in rows:
        slug = r["full_name"]
        if "/" in slug:
            owner, name = slug.split("/", 1)
            pairs.append((owner, name))

    out_rows = []
    missing = 0
    for start in range(0, len(pairs), BATCH):
        batch = pairs[start:start + BATCH]
        data = gql(build_query(batch))
        for i in range(len(batch)):
            node = data.get(f"r{i}")
            if not node:                     # deleted / renamed / private
                missing += 1
                continue
            topics = "|".join(
                t["topic"]["name"] for t in node["repositoryTopics"]["nodes"]
            )
            out_rows.append({
                "full_name": node["nameWithOwner"],
                "description": (node.get("description") or "").replace("\n", " ").strip(),
                "topics": topics,
                "language": (node.get("primaryLanguage") or {}).get("name", ""),
                "stars": node["stargazerCount"],
                "forks": node["forkCount"],
                "is_fork": node["isFork"],
                "archived": node["isArchived"],
                "pushed_at": node["pushedAt"],
                "created_at": node["createdAt"],
            })
        print(f"  {start + len(batch)}/{len(pairs)} fetched "
              f"({len(out_rows)} ok, {missing} missing)", file=sys.stderr)
        time.sleep(1.0)

    with OUT.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out_rows[0].keys()))
        w.writeheader()
        w.writerows(out_rows)
    print(f"\nWrote {len(out_rows)} repos ({missing} unreachable) -> {OUT}", file=sys.stderr)


if __name__ == "__main__":
    main()
