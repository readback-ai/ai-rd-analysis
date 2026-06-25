#!/usr/bin/env bash
# Manage git worktrees for parallel Claude Code development.
#
# Each parallel Claude Code session should run in its OWN worktree so sessions
# never clobber each other's working tree. Worktrees live in a common directory
# alongside the repo under ~/devel:
#   ~/devel/ai-rd-analysis-worktrees/<name>
# Each is on its own branch <name>, branched from main by default.
set -euo pipefail

ROOT="$(git rev-parse --show-toplevel)"
WT_DIR="$(dirname "$ROOT")/$(basename "$ROOT")-worktrees"

usage() {
  cat <<'EOF'
Usage: scripts/worktree.sh <command> [args]

Commands:
  new <name> [base]   Create worktree .worktrees/<name> on branch <name>,
                      branched from <base> (default: main).
  list                List all worktrees.
  rm <name>           Remove worktree .worktrees/<name> (branch is kept).
  prune               Prune stale worktree metadata.

Examples:
  scripts/worktree.sh new stage0-seed
  scripts/worktree.sh new stage2-classify phase-0-definition
  scripts/worktree.sh list
  scripts/worktree.sh rm stage0-seed
EOF
}

cmd="${1:-}"; shift || true
case "$cmd" in
  new)
    name="${1:?name required}"; base="${2:-main}"
    git -C "$ROOT" worktree add -b "$name" "$WT_DIR/$name" "$base"
    echo "Worktree ready: $WT_DIR/$name  (branch '$name' from '$base')"
    echo "Open a Claude Code session there:  cd $WT_DIR/$name"
    ;;
  list)  git -C "$ROOT" worktree list ;;
  rm)
    name="${1:?name required}"
    git -C "$ROOT" worktree remove "$WT_DIR/$name"
    echo "Removed worktree $WT_DIR/$name (branch '$name' kept; delete with: git branch -D $name)"
    ;;
  prune) git -C "$ROOT" worktree prune -v ;;
  -h|--help|"") usage; [ -z "$cmd" ] && exit 0 || exit 0 ;;
  *) echo "Unknown command: $cmd" >&2; usage; exit 1 ;;
esac
