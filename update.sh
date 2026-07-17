#!/usr/bin/env bash
# update.sh — pull latest kandev image and restart only if it changed
# Safe to run as root (mini-desktop) or as normal user (sfl-desktop).
#
# After a local rebuild, also syncs mise language toolchains (node, python, go,
# java, ruby, php, dotnet) into the persistent /data volume via
# setup-toolchains.sh — so the toolset stays in sync automatically without a
# separate manual step. Set SYNC_TOOLCHAINS=0 to disable.
#
# Usage:
#   bash ~/Code/kandev/update.sh
#
# Cron (mini-desktop, /etc/cron.d/kandev-update):
#   30 3 * * * root USER_NAME=alassane USER_HOME=/home/alassane /usr/local/sbin/kandev-update.sh
#
# Cron (sfl-desktop, user crontab):
#   30 3 * * * bash ~/Code/kandev/update.sh
set -euo pipefail

USER_HOME="${USER_HOME:-$HOME}"
COMPOSE_DIR="$USER_HOME/Code/kandev"
LOG_FILE="$USER_HOME/logs/kandev-update.log"
IMAGE="ghcr.io/kdlbs/kandev:latest"
# Set to 1 to skip local rebuild and use upstream image directly (bypass Dockerfile.local).
SKIP_LOCAL_BUILD="${SKIP_LOCAL_BUILD:-0}"
# Set to 0 to skip syncing mise language toolchains after a local rebuild.
SYNC_TOOLCHAINS="${SYNC_TOOLCHAINS:-1}"

mkdir -p "$(dirname "$LOG_FILE")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG_FILE"; }

log "--- kandev update check ---"

# Get digest of currently running image
OLD_DIGEST=$(docker inspect kandev --format '{{.Image}}' 2>/dev/null || echo "none")

# Pull latest upstream image
log "Pulling $IMAGE ..."
PULL_OUT=$(docker pull "$IMAGE" 2>&1)
echo "$PULL_OUT" >> "$LOG_FILE"

if echo "$PULL_OUT" | grep -q "Image is up to date"; then
    log "Already up to date — no restart needed."
    exit 0
fi

# New upstream image pulled — rebuild local image if Dockerfile.local exists
NEW_DIGEST=$(docker inspect "$IMAGE" --format '{{.Id}}' 2>/dev/null || echo "unknown")
log "Upstream image updated: $OLD_DIGEST → $NEW_DIGEST"

cd "$COMPOSE_DIR"

if [[ "$SKIP_LOCAL_BUILD" -eq 0 && -f "$COMPOSE_DIR/Dockerfile.local" ]]; then
    log "Rebuilding local image (Dockerfile.local) on top of new upstream..."
    docker compose -p kandev build --no-cache 2>&1 | tee -a "$LOG_FILE"
    log "Local image rebuilt."
fi

# Recreate container with updated image
log "Recreating kandev container..."
docker compose -p kandev up -d --force-recreate

log "Done. Kandev restarted with latest image."

# Sync mise language toolchains (node/python/go/java/ruby/php/dotnet) into the
# persistent /data volume. Only relevant for the local image (kandev-local:latest),
# which is the one that ships mise — the bare upstream image (SKIP_LOCAL_BUILD=1)
# has no mise/build toolchain at all. mise install is idempotent (skips versions
# already present), so this is cheap on every run and only does real work when
# mise.default.toml has changed or a toolchain is missing from the volume.
# Runs in an isolated throwaway container (see setup-toolchains.sh) so a slow
# Ruby/PHP source build can never starve or stop the just-restarted kandev
# container. Failures are logged but never abort the update — kandev itself is
# already up and unaffected either way.
if [[ "$SYNC_TOOLCHAINS" -eq 1 && "$SKIP_LOCAL_BUILD" -eq 0 && -x "$COMPOSE_DIR/setup-toolchains.sh" ]]; then
    log "Syncing language toolchains (mise) into persistent volume..."
    if KANDEV_DATA_DIR="$USER_HOME/.local/share/kandev" \
        bash "$COMPOSE_DIR/setup-toolchains.sh" >>"$LOG_FILE" 2>&1; then
        log "Toolchains synced."
    else
        log "WARNING: toolchain sync had failures — see $LOG_FILE (kandev itself is unaffected)."
    fi
fi
