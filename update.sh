#!/usr/bin/env bash
# update.sh — pull latest kandev image and restart only if it changed
# Safe to run as root (mini-desktop) or as normal user (sfl-desktop).
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
