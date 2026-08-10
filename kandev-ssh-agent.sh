#!/usr/bin/env bash
# kandev-ssh-agent.sh — (re)start kandev with SSH agent socket forwarding.
#
# Reuses an already-running ssh-agent if SSH_AUTH_SOCK is valid; otherwise
# starts a new one and adds your standard keys.
#
# Usage:
#   bash ~/Code/kandev/kandev-ssh-agent.sh
#   bash ~/Code/kandev/kandev-ssh-agent.sh ~/.ssh/other_key   # add extra key
set -euo pipefail

# ── Machine-specific overrides ───────────────────────────────────────────────
# Load real hosts/users/IPs for THIS machine from a gitignored host.env so this
# public repo stays free of private LAN details. See host.env.example. The
# ${VAR:-default} placeholders below are only used when host.env is absent.
_KANDEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[ -f "$_KANDEV_DIR/host.env" ] && . "$_KANDEV_DIR/host.env"

COMPOSE_DIR="$(cd "$(dirname "$0")" && pwd)"

# ── Ensure an ssh-agent is running ───────────────────────────────────────────
if [[ -z "${SSH_AUTH_SOCK:-}" ]] || ! ssh-add -l &>/dev/null 2>&1; then
    echo "Starting a new ssh-agent..."
    eval "$(ssh-agent -s)"
fi

# ── Load keys ────────────────────────────────────────────────────────────────
# Add keys passed as arguments, or the default set from ~/.ssh/config.
KEYS=("$@")
if [[ ${#KEYS[@]} -eq 0 ]]; then
    KEYS=(
        "$HOME/.ssh/id_ed25519"
        "$HOME/.ssh/github_office"
    )
fi

for key in "${KEYS[@]}"; do
    if [[ -f "$key" ]]; then
        ssh-add "$key" 2>/dev/null && echo "Loaded: $key" || true
    fi
done

# ── Restart kandev with the agent socket ──────────────────────────────────────
echo "Restarting kandev with SSH_AUTH_SOCK=$SSH_AUTH_SOCK ..."
SSH_AUTH_SOCK="$SSH_AUTH_SOCK" docker compose \
    -f "$COMPOSE_DIR/docker-compose.yml" \
    -f "$COMPOSE_DIR/docker-compose.override.yml" \
    -f "$COMPOSE_DIR/docker-compose.ssh-agent.yml" \
    -p kandev up -d --force-recreate

echo "Done. SSH agent is forwarded into the kandev container."
echo "To verify: docker exec -it kandev ssh-add -l"
