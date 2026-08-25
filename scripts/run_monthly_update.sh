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
# Usage:
#   scripts/run_monthly_update.sh [--at YYYY-MM-DDTHH:MM:SSZ] <monthly_update args>
#
# June-2026 finalization (August stays uncollected — it is still partial):
#   scripts/run_monthly_update.sh --at 2026-08-26T00:00:00Z 2026-08 --revise-only
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO"

PY=.venv/bin/python
[ -x "$PY" ] || { echo "no venv at $REPO/$PY — run 'uv sync' first" >&2; exit 3; }

AT=""
if [ "${1:-}" = "--at" ]; then
    AT="${2:?--at needs an ISO-8601 UTC instant, e.g. 2026-08-26T00:00:00Z}"
    shift 2
fi
[ "$#" -gt 0 ] || { sed -n '2,16p' "$0"; exit 2; }

# data/derived/*.log is gitignored; one log per run, named for its start.
LOG="data/derived/monthly_update_$(date -u +%Y%m%dT%H%M%SZ).log"
mkdir -p data/derived

if [ -n "$AT" ]; then
    # Computed in Python: `date` parses ISO-8601 differently on BSD and GNU.
    SECS=$("$PY" - "$AT" <<'EOF'
import sys
from datetime import datetime, timezone
t = datetime.strptime(sys.argv[1], "%Y-%m-%dT%H:%M:%SZ").replace(
    tzinfo=timezone.utc)
print(int(max(0, (t - datetime.now(timezone.utc)).total_seconds())))
EOF
)
    echo "waiting ${SECS}s until ${AT}" | tee -a "$LOG"
    sleep "$SECS"
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
exit "$status"
