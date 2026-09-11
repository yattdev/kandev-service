#!/usr/bin/env bash
# Ensure automated deployments use the canonical main checkout without
# overwriting tracked work on another branch.
set -euo pipefail

COMPOSE_DIR="${1:-${COMPOSE_DIR:-$HOME/Code/kandev}}"
REQUIRED_BRANCH="${KANDEV_REQUIRED_BRANCH:-main}"

if ! git -C "$COMPOSE_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1; then
    exit 0
fi

BRANCH="$(git -C "$COMPOSE_DIR" branch --show-current 2>/dev/null || true)"
if [[ "$BRANCH" == "$REQUIRED_BRANCH" ]]; then
    exit 0
fi

if [[ "${KANDEV_ALLOW_BRANCH:-0}" == "1" ]]; then
    echo "WARNING: running kandev from branch '${BRANCH:-detached HEAD}' (KANDEV_ALLOW_BRANCH=1)." >&2
    exit 0
fi

if ! git -C "$COMPOSE_DIR" diff --quiet \
   || ! git -C "$COMPOSE_DIR" diff --cached --quiet; then
    echo "ERROR: cannot switch the kandev deployment checkout to '$REQUIRED_BRANCH':" >&2
    echo "       tracked changes exist on '${BRANCH:-detached HEAD}'." >&2
    echo "       Commit or stash them before running the deployment." >&2
    exit 78
fi

if ! git -C "$COMPOSE_DIR" switch "$REQUIRED_BRANCH"; then
    echo "ERROR: failed to switch the kandev deployment checkout to '$REQUIRED_BRANCH'." >&2
    echo "       Resolve any checkout conflict, then retry." >&2
    exit 78
fi

echo "Switched kandev deployment checkout from '${BRANCH:-detached HEAD}' to '$REQUIRED_BRANCH'."
