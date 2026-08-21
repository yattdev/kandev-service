#!/usr/bin/env bash
# require-main-branch.sh — refuse to build/start/restart kandev from a non-main checkout.
#
# Why: kandev-start.sh, update.sh and kandev-pull.sh read the compose files from
# the CURRENT WORKING TREE. The *-workflow branches exist only to edit
# workflows/ and are stale forks of main that still carry an old
# docker-compose.override.yml / Dockerfile.local. Starting from one silently
# builds a container missing whatever main added since the branch was cut.
#
# On 2026-08-21 this took the service down: kandev-start.sh ran while
# codex-copilotDI-workflow was checked out, whose override.yml predates the
# Codex sandbox fix and has no `security_opt:` block. The container came up
# under docker-default AppArmor + default seccomp, bubblewrap could not create
# its user namespace, the entrypoint preflight exited 78, and Docker restarted
# it 43 times. Nothing in the compose output hinted at the cause.
#
# Usage:  bash scripts/require-main-branch.sh [compose_dir]
# Exit:   0 = safe to proceed, 78 = wrong branch (matches the other preflights)
#
# Escape hatch (deliberate, e.g. testing a compose change on a branch):
#   KANDEV_ALLOW_BRANCH=1 bash kandev-start.sh
set -euo pipefail

COMPOSE_DIR="${1:-${COMPOSE_DIR:-$HOME/Code/kandev}}"
REQUIRED_BRANCH="${KANDEV_REQUIRED_BRANCH:-main}"

# Not a git work tree (e.g. a deployment copied without .git) — nothing to check.
if ! git -C "$COMPOSE_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    exit 0
fi

BRANCH="$(git -C "$COMPOSE_DIR" rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"

if [[ "$BRANCH" == "$REQUIRED_BRANCH" ]]; then
    exit 0
fi

if [[ "${KANDEV_ALLOW_BRANCH:-0}" == "1" ]]; then
    echo "WARNING: starting kandev from branch '$BRANCH' (KANDEV_ALLOW_BRANCH=1)." >&2
    echo "         Compose files may be stale; verify the container afterwards with:" >&2
    echo "         docker inspect kandev --format '{{.AppArmorProfile}} {{json .HostConfig.SecurityOpt}}'" >&2
    exit 0
fi

echo "ERROR: refusing to run the kandev deployment from branch '$BRANCH'." >&2
echo "       $COMPOSE_DIR is not on '$REQUIRED_BRANCH', so the compose files here may be" >&2
echo "       stale — the container can come up without its security_opt profiles and" >&2
echo "       crash-loop (see CLAUDE.md, 'infrastructure changes live on main')." >&2
echo "" >&2
echo "       Fix:      cd $COMPOSE_DIR && git switch $REQUIRED_BRANCH" >&2
echo "       Then:     docker compose -p kandev up -d --force-recreate" >&2
echo "       Override: KANDEV_ALLOW_BRANCH=1 $0   (not recommended)" >&2
exit 78
