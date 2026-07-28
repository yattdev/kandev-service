#!/usr/bin/env bash
# kandev-build-main.sh — Temporarily build & run kandev from the upstream
# `main` branch (github.com/kdlbs/kandev), for when a fix has landed on main
# but hasn't shipped in a tagged release yet.
#
# Wraps Dockerfile.main-branch: compiles the backend+web from source and
# layers just the binaries on top of the existing kandev-local:latest image
# (release-based). Dockerfile.local / docker-compose.override.yml / update.sh
# are never touched — the next `docker compose build` (manual, or automatic
# via update.sh once the next release ships) rebuilds kandev-local:latest
# cleanly from the release base, discarding this layer.
#
# Usage:
#   bash ~/Code/kandev/kandev-build-main.sh                # build+run main
#   bash ~/Code/kandev/kandev-build-main.sh --ref <branch>  # build a specific branch/tag/commit
#   bash ~/Code/kandev/kandev-build-main.sh --no-test       # skip the test.sh run at the end
#   bash ~/Code/kandev/kandev-build-main.sh --revert        # restore the last release-based backup
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-$HOME/Code/kandev}"
LOG_FILE="${LOG_FILE:-$HOME/logs/kandev-build-main.log}"
KANDEV_REF="${KANDEV_REF:-main}"
RUN_TESTS=1
REVERT=0

while [[ $# -gt 0 ]]; do
    case "$1" in
        --ref)      KANDEV_REF="${2:?--ref requires a branch/tag/commit}"; shift 2 ;;
        --no-test)  RUN_TESTS=0; shift ;;
        --revert)   REVERT=1; shift ;;
        -h|--help)
            sed -n '2,17p' "$0"; exit 0 ;;
        *) echo "Unknown option: $1" >&2; exit 2 ;;
    esac
done

mkdir -p "$(dirname "$LOG_FILE")"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [build-main] $*" | tee -a "$LOG_FILE"; }

cd "$COMPOSE_DIR"

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

# ── Revert path ────────────────────────────────────────────────────────────
if [[ "$REVERT" -eq 1 ]]; then
    if ! docker image inspect kandev-local:pre-main-backup >/dev/null 2>&1; then
        log "No kandev-local:pre-main-backup found — nothing to revert to."
        log "Run 'docker compose build && docker compose up -d --force-recreate' to rebuild from the tracked release instead."
        exit 1
    fi
    log "Reverting to release-based image (kandev-local:pre-main-backup)..."
    docker tag kandev-local:pre-main-backup kandev-local:latest
    docker compose -p kandev up -d --force-recreate
    if wait_for_health; then
        log "Reverted successfully — kandev is back on the release build."
        exit 0
    else
        log "CRITICAL: revert did not become healthy. Check: docker logs kandev --tail 60"
        exit 1
    fi
fi

# ── Build path ─────────────────────────────────────────────────────────────
log "--- kandev main-branch build (ref: ${KANDEV_REF}) ---"

# Make sure a release-based kandev-local:latest exists first — Dockerfile.main-branch
# layers on top of it. If it's missing (first run ever), build it from Dockerfile.local.
if ! docker image inspect kandev-local:latest >/dev/null 2>&1; then
    log "kandev-local:latest not found — building release base first (docker compose build)..."
    docker compose -p kandev build 2>&1 | tee -a "$LOG_FILE"
fi

# Snapshot the current image as the rollback target *before* overwriting the
# tag, so --revert always has something release-based to fall back to (mirrors
# the -previous safety net in update.sh).
log "Backing up current kandev-local:latest as kandev-local:pre-main-backup..."
docker tag kandev-local:latest kandev-local:pre-main-backup

log "Building kandev from ${KANDEV_REF} (this compiles Go backend + web app — a few minutes)..."
if ! docker build --network=host \
        --build-arg KANDEV_REF="$KANDEV_REF" \
        -f Dockerfile.main-branch -t kandev-local:latest . 2>&1 | tee -a "$LOG_FILE"; then
    log "CRITICAL: build failed — kandev-local:latest left untouched (still release-based)."
    exit 1
fi

log "Recreating kandev container..."
docker compose -p kandev up -d --force-recreate

if wait_for_health; then
    log "Done. Kandev is running main branch (ref: ${KANDEV_REF}) and passed health check."
    log "Revert anytime with: bash $0 --revert  (or: docker compose build && docker compose up -d --force-recreate)"
else
    log "CRITICAL: kandev did not become healthy after the main-branch build (no HTTP 200 on ${HEALTH_URL} after 60s)."
    log "--- last container logs ---"
    docker logs kandev --tail 60 >> "$LOG_FILE" 2>&1
    log "--- end container logs ---"

    log "Attempting automatic rollback to kandev-local:pre-main-backup ..."
    docker tag kandev-local:pre-main-backup kandev-local:latest
    docker compose -p kandev up -d --force-recreate
    if wait_for_health; then
        log "Rolled back successfully — kandev is back up on the release image. Investigate the main-branch build before retrying."
    else
        log "CRITICAL: rollback ALSO failed to become healthy — kandev is DOWN. Manual intervention required."
    fi
    exit 1
fi

if [[ "$RUN_TESTS" -eq 1 && -x "$COMPOSE_DIR/test.sh" ]]; then
    log "Running test.sh..."
    if bash "$COMPOSE_DIR/test.sh" 2>&1 | tee -a "$LOG_FILE"; then
        log "test.sh passed."
    else
        log "WARNING: test.sh reported failures — see $LOG_FILE."
    fi
fi
