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
# Export HOME so `docker compose` (invoked below) resolves ${HOME} in
# docker-compose.override.yml to the correct user's home directory. This
# matters on mini-desktop, where cron runs this script as root: without this
# export, ${HOME} would resolve to /root, silently remounting the container
# onto root's ~/.ssh, ~/.gitconfig, and ~/.local/share/kandev instead of the
# intended user's — a real incident that caused the running container to
# drift onto /root paths for days until caught manually.
export HOME="$USER_HOME"
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

# Snapshot the tag the *currently running* container uses (e.g. kandev-local:latest,
# or ghcr.io/kdlbs/kandev:latest when SKIP_LOCAL_BUILD=1) as "-previous" *before*
# pulling/rebuilding. This is a rollback safety net: a rebuild with the same tag
# (`docker compose build`) overwrites that tag on the new image, so without this
# extra tag the last known-good image would become untagged/dangling and could be
# garbage-collected, leaving no fast way back after a bad upstream release.
RUNNING_IMAGE_TAG=$(docker inspect kandev --format '{{.Config.Image}}' 2>/dev/null || echo "")
if [[ -n "$RUNNING_IMAGE_TAG" ]] && docker image inspect "$RUNNING_IMAGE_TAG" >/dev/null 2>&1; then
    docker tag "$RUNNING_IMAGE_TAG" "${RUNNING_IMAGE_TAG}-previous"
    log "Tagged current image as ${RUNNING_IMAGE_TAG}-previous (rollback safety net)."
fi

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

# Health-gate the update: a successful `docker compose up` only means the
# container process started, not that the backend came up (e.g. a broken
# DB migration crash-loops the container forever while `up -d` still exits 0).
# A prior incident silently left kandev unreachable for hours after an
# unattended update because nothing checked this. Poll the health endpoint for
# up to ~60s; on failure, roll back to the pre-update image automatically so
# the service self-heals, and fail loudly (nonzero exit) so cron surfaces it.
HEALTH_URL="http://localhost:38429/"
wait_for_health() {
    local i
    for ((i = 0; i < 30; i++)); do
        if [[ "$(curl -s -o /dev/null -w '%{http_code}' "$HEALTH_URL" 2>/dev/null)" == "200" ]]; then
            return 0
        fi
        sleep 2
    done
    return 1
}

if wait_for_health; then
    log "Done. Kandev restarted with latest image and passed health check."
else
    log "CRITICAL: kandev did not become healthy after update (no HTTP 200 on ${HEALTH_URL} after 60s)."
    log "--- last container logs ---"
    docker logs kandev --tail 60 >> "$LOG_FILE" 2>&1
    log "--- end container logs ---"

    if [[ -n "$RUNNING_IMAGE_TAG" ]] && docker image inspect "${RUNNING_IMAGE_TAG}-previous" >/dev/null 2>&1; then
        log "Attempting automatic rollback to ${RUNNING_IMAGE_TAG}-previous ..."
        docker tag "${RUNNING_IMAGE_TAG}-previous" "$RUNNING_IMAGE_TAG"
        docker compose -p kandev up -d --force-recreate
        if wait_for_health; then
            log "Rolled back successfully — kandev is back up on the previous image. Investigate the new image/DB migration before updating again."
        else
            log "CRITICAL: rollback ALSO failed to become healthy — kandev is DOWN. Manual intervention required."
        fi
    else
        log "CRITICAL: no previous image tag available for rollback — kandev may be DOWN. Manual intervention required."
    fi
    exit 1
fi

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
