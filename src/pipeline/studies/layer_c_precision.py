"""Measured precision of layer-C (branch-prefix) attribution, per prefix.

Layer C rests entirely on naming convention, and 'claude'/'cursor' are words
humans and CI pipelines plausibly put in branch names in 2026 BECAUSE the
products are famous — the zero-hits-in-Q1-2024 check cannot see false
positives that grow with product fame. This study measures provenance
signals on the C-ONLY portion of the org-stratified branch-PR samples
(no commit marker, no agent author — the PRs layer C alone attributes):

- web_flow:    >=1 commit committed by GitHub web-flow (noreply@github.com)
               — the signature of agent cloud flows creating commits via API
- machine_slug: branch matches the product's generated-name pattern
               (cursor/...-[hex4]; claude/ session slugs; codex/ hyphen slugs)
- ci_committed: ALL commits committed by github-actions[bot] — automation
               that merely NAMES branches after the product; counted as a
               FALSE POSITIVE and excluded from layer C by detect.pr_branch_tool
- indeterminate: none of the above — user-pushed commits on a prefix branch;
               consistent with an agent branch taken over locally (true
               positive) or a human-named branch (false positive)

Usage:  python -m pipeline.studies.layer_c_precision
"""
from __future__ import annotations

import json
import re

from pipeline.detect import MARKERS, pr_agent_author, pr_ai_tools
from pipeline.ghx import data_dir
from pipeline.org_set import scoped_repos

SLUG = {
    "codex": re.compile(r"^codex/[a-z0-9][a-z0-9-]*$"),
    "cursor": re.compile(r"^cursor/.+-[0-9a-f]{4}$"),
    "claude": re.compile(r"^claude/(issue-\d+|[a-z]+-[a-z]+-[0-9a-f]{4,})"),
    "copilot": re.compile(r"^copilot/[a-z0-9][a-z0-9-]*$"),
    "droid": re.compile(r"^droid/.+-20\d{6}$"),
}


def committer_emails(pr: dict) -> list[str]:
    out = []
    for c in (pr.get("commits") or {}).get("nodes") or []:
        out.append(((c.get("commit") or {}).get("committer") or {}).get("email") or "")
    return out


def main() -> None:
    store = data_dir() / "raw" / "branch_samples"
    # A repo-scoped org's universe is its in-scope repos only (R5); its
    # sample cells may carry PRs from other repos of the same owner.
    scoped = {o.lower(): set(rs) for o, rs in scoped_repos().items()}
    print(f"{'prefix':9}{'C-only n':>9}{'web_flow%':>10}{'machine_slug%':>14}"
          f"{'ci_committed%':>14}{'indeterminate%':>15}")
    for prefix in ("codex", "copilot", "cursor", "claude", "droid"):
        n = wf = slug = ci = 0
        for f in sorted(store.glob(f"{prefix}/*.json")):
            cell = json.loads(f.read_text())
            keep = scoped.get((cell.get("org") or "").lower())
            for p in cell.get("prs") or []:
                if not p or pr_ai_tools(p, MARKERS) or pr_agent_author(p):
                    continue
                if keep is not None and ((p.get("repository") or {})
                                         .get("nameWithOwner")) not in keep:
                    continue
                n += 1
                emails = committer_emails(p)
                if emails and all(e.endswith("github-actions[bot]@users.noreply.github.com")
                                  for e in emails):
                    ci += 1
                    continue
                is_wf = any(e == "noreply@github.com" for e in emails)
                is_slug = bool(SLUG[prefix].match(p.get("headRefName") or ""))
                if is_wf:
                    wf += 1
                elif is_slug:
                    slug += 1
        if not n:
            continue
        other = n - wf - slug - ci
        print(f"{prefix:9}{n:>9}{100*wf/n:>9.1f}%{100*slug/n:>13.1f}%"
              f"{100*ci/n:>13.1f}%{100*other/n:>14.1f}%")


if __name__ == "__main__":
    main()
