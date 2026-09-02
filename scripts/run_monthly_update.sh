#!/usr/bin/env bash
# Scheduled runner for the incremental monthly update (METHODS §1c).
#
# A w8 finalization can only start once the month's last 8-week window has
# closed, which is an instant, not a date — so this waits for it rather
# than asking the operator to be awake. The correctness checks themselves
# live in monthly_update.check_finalizable (the data stamp must cover the
# month being finalized and must not lead the run); this script only
# handles the waiting and keeps a durable log, and reports whatever exit
# code the update produced.
#
# --bump-as-of advances detect.AS_OF to this run's start instant, right
# before collection. The stamp records a pull that happened and every
# analysis entry point reads it, so it is never committed ahead of the
# pull; commit the one-line diff with the regenerated artifacts after.
#
# Usage:
#   scripts/run_monthly_update.sh [--at YYYY-MM-DDTHH:MM:SSZ] [--bump-as-of] \
#       <monthly_update args>
#
# June-2026 finalization (August stays uncollected — it is still partial):
#   scripts/run_monthly_update.sh --at 2026-08-26T00:00:00Z --bump-as-of \
#       2026-08 --revise-only
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PY=.venv/bin/python
[ -x "$PY" ] || { echo "no venv at $REPO/$PY — run 'uv sync' first" >&2; exit 3; }

AT=""
BUMP=""
while : ; do
    case "${1:-}" in
        --at) AT="${2:?--at needs an ISO-8601 UTC instant, e.g. 2026-08-26T00:00:00Z}"; shift 2 ;;
        --bump-as-of) BUMP=1; shift ;;
        *) break ;;
    esac
done
[ "$#" -gt 0 ] || { sed -n '2,21p' "$0"; exit 2; }

# data/derived/*.log is gitignored; one log per run, named for its start.
LOG="data/derived/monthly_update_$(date -u +%Y%m%dT%H%M%SZ).log"
mkdir -p data/derived

if [ -n "$AT" ]; then
    # Computed in Python: `date` parses ISO-8601 differently on BSD and GNU.
    SECS=$("$PY" - "$AT" <<'EOF'
import math
import sys
from datetime import datetime, timezone
t = datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ").replace(
    tzinfo=timezone.utc)
# Round UP: flooring can wake within the second before --at, which stamps
# AS_OF a second early and trips the gate on an unattended run.
print(max(0, math.ceil((t - datetime.now(timezone.utc)).total_seconds())))
EOF
)
    echo "waiting ${SECS}s until ${AT}" | tee -a "$LOG"
    sleep "$SECS"
fi

DETECT=src/pipeline/detect.py
BACKUP=""

# The stamp is rolled back by a TRAP, not by the success path: a census
# runs for hours and is far more likely to end on Ctrl-C or SIGTERM than
# to return a bad status. Any exit that is not a completed, successful
# run must leave detect.AS_OF exactly as it was found, or the tree keeps
# a stamp claiming a census that never finished.
rollback_as_of() {
    [ -n "$BACKUP" ] && [ -f "$BACKUP" ] || return 0
    cp "$BACKUP" "$DETECT"
    rm -f "$BACKUP"
    BACKUP=""
    echo "run did not complete — rolled detect.AS_OF back" | tee -a "$LOG"
}
trap rollback_as_of EXIT
trap 'exit 130' INT
trap 'exit 143' TERM

if [ -n "$BUMP" ]; then
    # AS_OF stamps a collection that HAPPENED, so it is advanced here —
    # at the moment this run starts pulling — never committed ahead of
    # the pull. Commit the resulting one-line diff with the regenerated
    # artifacts once the run succeeds.
    BACKUP="$(mktemp -t detect_as_of)"
    cp "$DETECT" "$BACKUP"
    "$PY" - "$(date -u +%Y-%m-%dT%H:%M:%SZ)" <<'EOF' | tee -a "$LOG"
import pathlib
import re
import sys
p = pathlib.Path("src/pipeline/detect.py")
src = p.read_text()
new, n = re.subn(r'^AS_OF = "[^"]*"$', f'AS_OF = "{sys.argv[1]}"', src,
                 count=1, flags=re.M)
if n != 1:
    sys.exit("could not find the AS_OF assignment in detect.py")
old = re.search(r'^AS_OF = "([^"]*)"$', src, re.M).group(1)
p.write_text(new)
print(f"bumped detect.AS_OF: {old} -> {sys.argv[1]}")
EOF
fi

# errexit off across the pipeline: a failed update must still reach the
# reporting below instead of killing the script at the pipe.
set +e
{
    echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) monthly_update.py $* ==="
    PYTHONPATH=src "$PY" scripts/monthly_update.py "$@"
} 2>&1 | tee -a "$LOG"
# tee sits at the end of the pipe, so read the update's own status.
status=${PIPESTATUS[0]}
set -e
echo "=== $(date -u +%Y-%m-%dT%H:%M:%SZ) exit=${status} ===" | tee -a "$LOG"
echo "log: $REPO/$LOG"

if [ "$status" -eq 0 ]; then
    # Success is the only path that KEEPS the bumped stamp: discard the
    # backup so the EXIT trap becomes a no-op.
    rm -f "$BACKUP"
    BACKUP=""
fi

if [ "$status" -eq 0 ]; then
    # New cells and a new stamp change published numbers, so the run is
    # not finished until the artifacts are rebuilt from them.
    cat <<'NEXT'

next: the finalized cells are in the store, but published artifacts still
reflect the previous stamp. Regenerate and commit them together with the
detect.AS_OF bump:
    uv run python scripts/regenerate.py
    PYTHONPATH=src uv run python scripts/report.py --granularity month
    PYTHONPATH=src uv run python scripts/plot_all.py
NEXT
fi
exit "$status"
