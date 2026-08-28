#!/usr/bin/env bash
# Codex review gate for the PR workflow (CLAUDE.md "PR review loop").
# Reviews the CURRENT branch against a base branch via the Codex CLI and
# exits 0 only on an explicit APPROVE verdict, 1 on REQUEST_CHANGES, 2
# when no verdict line was produced (treat as not approved).
#
# Uses plain `codex exec` rather than `codex exec review`: the review
# subcommand's --base mode does not accept custom instructions, and the
# gate needs both the repo-standards prompt and the verdict protocol.
#
# Usage: scripts/codex_review.sh [base-branch] [findings-file]
set -uo pipefail
BASE="${1:-feat/primary-implementation}"
OUT="${2:-$(mktemp -t codex_review).md}"

codex exec --sandbox workspace-write - >"$OUT" 2>&1 <<EOF
You are the adversarial code reviewer for this repository. Review the
changes on the current branch relative to the base branch:

    git diff ${BASE}...HEAD

Apply the repo's standards from CLAUDE.md, docs/METHODS.md and
docs/CODE_GUIDE.md: every defect fix needs a test that was shown failing
first; comments describe code, not history; collection and completeness
rules must fail loudly rather than accept partial results; any data or
methodology change must state its estimand/bias implications; tests must
not reach the network.

Verify claims empirically where possible — run the test suite
(.venv/bin/python -m pytest -q), inspect the data files a change
touches, and reproduce at least one failure scenario per P1 before
reporting it.

Rank findings [P1] (merge blocker), [P2], [P3], each with file:line
references and a concrete failure scenario. If everything holds, say
what you verified.

End with exactly one line, nothing after it:
VERDICT: APPROVE
or
VERDICT: REQUEST_CHANGES
EOF

echo "--- review written to $OUT" >&2
if grep -q "^VERDICT: APPROVE" "$OUT"; then
    exit 0
elif grep -q "^VERDICT: REQUEST_CHANGES" "$OUT"; then
    exit 1
else
    echo "--- no verdict line found; treating as not approved" >&2
    exit 2
fi
