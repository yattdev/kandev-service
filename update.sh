#!/usr/bin/env bash
# update.sh — pull latest kandev image and restart only if it changed
# Safe to run as root (home-server) or as normal user (office-desktop).
#
# Reconciles the deployed image back to a clean release build: it rebuilds
# kandev-local:latest not only when a new upstream :latest is pulled, but also
# whenever the currently-deployed image is not a clean release build (e.g. a
# temporary main-branch build left by kandev-build-main.sh) or was built on a
# now-stale upstream base. This is driven by the com.kandev.flavor /
# com.kandev.base-id labels stamped by Dockerfile.local.
#
# After a local rebuild, also syncs mise language toolchains (node, python, go,
# java, ruby, php, dotnet) into the persistent /data volume via
# setup-toolchains.sh — so the toolset stays in sync automatically without a
# separate manual step. Set SYNC_TOOLCHAINS=0 to disable.
#
# Usage:
#   bash ~/Code/kandev/update.sh
#
# Cron (home-server, /etc/cron.d/kandev-update):
#   30 3 * * * root USER_NAME=bob USER_HOME=/home/bob /usr/local/sbin/kandev-update.sh
#
# Cron (office-desktop, user crontab):
#   30 3 * * * bash ~/Code/kandev/update.sh
set -euo pipefail

USER_HOME="${USER_HOME:-$HOME}"
# Export HOME so `docker compose` (invoked below) resolves ${HOME} in
# docker-compose.override.yml to the correct user's home directory. This
# matters on home-server, where cron runs this script as root: without this
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
#
# Keep exactly one updater-owned rollback image. Merely overwriting the tag leaves
# the older rollback dangling in the containerd image store; repeated failed runs
# accumulated several ~2.7 GB local layers and eventually made the disk preflight
# reject every later update. Removing this one known tag is deliberately narrower
# than `docker image prune`: unrelated task/QA images are never touched.
RUNNING_IMAGE_TAG=$(docker inspect kandev --format '{{.Config.Image}}' 2>/dev/null || echo "")
if [[ -n "$RUNNING_IMAGE_TAG" ]] && docker image inspect "$RUNNING_IMAGE_TAG" >/dev/null 2>&1; then
    ROLLBACK_TAG="${RUNNING_IMAGE_TAG}-previous"
    STALE_ROLLBACK_ID=$(docker image inspect "$ROLLBACK_TAG" --format '{{.Id}}' 2>/dev/null || echo "")
    if [[ -n "$STALE_ROLLBACK_ID" && "$STALE_ROLLBACK_ID" != "$OLD_DIGEST" ]]; then
        if docker image rm "$ROLLBACK_TAG" >>"$LOG_FILE" 2>&1; then
            log "Removed stale updater rollback image $ROLLBACK_TAG ($STALE_ROLLBACK_ID)."
        else
            log "WARNING: could not remove stale updater rollback tag $ROLLBACK_TAG; continuing safely."
        fi
    fi
    docker tag "$RUNNING_IMAGE_TAG" "$ROLLBACK_TAG"
    log "Tagged current image as $ROLLBACK_TAG (rollback safety net)."
fi

# Pull latest upstream image
log "Pulling $IMAGE ..."
PULL_OUT=$(docker pull "$IMAGE" 2>&1)
echo "$PULL_OUT" >> "$LOG_FILE"

PULLED_NEW=1
if echo "$PULL_OUT" | grep -q "Image is up to date"; then
    PULLED_NEW=0
fi

# Resolved ID of the upstream :latest we now have locally. Stamped into the
# rebuilt local image (com.kandev.base-id) so we can later tell whether the
# deployed image is still built on the current upstream.
UPSTREAM_ID=$(docker image inspect "$IMAGE" --format '{{.Id}}' 2>/dev/null || echo "unknown")

cd "$COMPOSE_DIR"

# Validate node-level prerequisites before a rebuild/recreate (or an
# "already up to date" early exit) can leave agents on a broken runtime.
# Refuse to run the deployment from a non-main checkout. The compose files are
# read from the current working tree, so a stale *-workflow branch silently
# produces a misconfigured container (2026-08-21 crash-loop outage).
# Override deliberately with KANDEV_ALLOW_BRANCH=1.
bash "$COMPOSE_DIR/scripts/require-main-branch.sh" "$COMPOSE_DIR"
bash "$COMPOSE_DIR/scripts/check-codex-runtime.sh"

# ── Decide whether the local image must be (re)built ─────────────────────────
# The old logic only rebuilt when THIS pull downloaded a new upstream base, so
# it never reconciled a kandev-local:latest that had drifted for any OTHER
# reason — most importantly a temporary main-branch build from
# kandev-build-main.sh (which overwrites kandev-local:latest). Result: after a
# branch build, `update.sh` reported "Already up to date" forever and the
# container kept running the branch build. We now also rebuild when the
# deployed image is not a clean release build, or was built on a stale base.
REBUILD=0
REBUILD_REASON=""
if [[ "$SKIP_LOCAL_BUILD" -eq 0 && -f "$COMPOSE_DIR/Dockerfile.local" ]]; then
    TARGET_IMAGE="kandev-local:latest"
    if [[ "$PULLED_NEW" -eq 1 ]]; then
        REBUILD=1; REBUILD_REASON="new upstream base pulled ($OLD_DIGEST → $UPSTREAM_ID)"
    elif ! docker image inspect "$TARGET_IMAGE" >/dev/null 2>&1; then
        REBUILD=1; REBUILD_REASON="local image $TARGET_IMAGE missing"
    else
        FLAVOR=$(docker image inspect "$TARGET_IMAGE" --format '{{index .Config.Labels "com.kandev.flavor"}}' 2>/dev/null || echo "")
        BASE_ID=$(docker image inspect "$TARGET_IMAGE" --format '{{index .Config.Labels "com.kandev.base-id"}}' 2>/dev/null || echo "")
        if [[ "$FLAVOR" != "release" ]]; then
            REBUILD=1; REBUILD_REASON="deployed image flavor='${FLAVOR:-none}' is not a clean release build — reconciling to release"
        # Images built before base provenance was introduced (or built manually
        # without BASE_IMAGE_ID) cannot prove that they track the current
        # upstream image. Treat empty/unknown as stale. This also closes an
        # important retry gap: if one update run pulls a release but aborts at
        # the disk-space preflight, the next pull says "up to date"; previously
        # an unknown BASE_ID then caused the still-old local image to be accepted
        # forever.
        elif [[ -z "$BASE_ID" || "$BASE_ID" == "unknown" ]]; then
            REBUILD=1; REBUILD_REASON="local image has no usable upstream base provenance (base-id='${BASE_ID:-missing}')"
        elif [[ "$UPSTREAM_ID" != "unknown" && "$BASE_ID" != "$UPSTREAM_ID" ]]; then
            REBUILD=1; REBUILD_REASON="local image built on stale base ($BASE_ID → $UPSTREAM_ID)"
        fi
    fi
else
    TARGET_IMAGE="$IMAGE"
fi

if [[ "$REBUILD" -eq 1 ]]; then
    # ── Preflight: free disk space ───────────────────────────────────────────
    # A full disk does NOT fail the build with an obvious "out of space" error.
    # apt inside `docker build` writes truncated repository index files and then
    # rejects them with
    #     "At least one invalid signature was encountered"
    #     "E: The repository '...' is not signed"
    # which reads like a GPG/keyring or transparent-proxy problem and sends
    # debugging in completely the wrong direction. Real incident: / filled up
    # with containerd image layers (89G) and every nightly rebuild failed this
    # way, looking like repo corruption.
    #
    # Both filesystems matter and they are often NOT the same one: this daemon
    # uses the containerd image store, so layers land in /var/lib/containerd
    # (on /) while the docker data root may be a separate partition.
    # The local layer adds about 2.7 GB to the shared upstream base and BuildKit
    # needs temporary unpacking room. Eight GiB is a measured conservative floor
    # after rotating the stale rollback above. The former 15 GiB floor rejected
    # valid updates on this dedicated Docker partition even when the build had
    # enough room. Operators can still raise/lower it explicitly.
    MIN_FREE_GB="${MIN_FREE_GB:-8}"
    free_gb() {
        df -BG --output=avail "$1" 2>/dev/null | tail -1 | tr -dc '0-9'
    }
    SPACE_OK=1
    DOCKER_ROOT=$(docker info --format '{{.DockerRootDir}}' 2>/dev/null || echo "/var/lib/docker")
    for path in "/" "$DOCKER_ROOT"; do
        avail=$(free_gb "$path")
        if [[ -z "$avail" ]]; then
            log "WARNING: could not determine free space for $path — continuing anyway."
            continue
        fi
        log "Free space on $path: ${avail}G"
        if (( avail < MIN_FREE_GB )); then
            log "CRITICAL: only ${avail}G free on $path; need >= ${MIN_FREE_GB}G to rebuild."
            SPACE_OK=0
        fi
    done
    if [[ "$SPACE_OK" -eq 0 ]]; then
        log "Aborting BEFORE the build: a full disk makes 'docker build' fail with"
        log "misleading apt GPG/'not signed' errors rather than a disk-space error."
        log "Reclaim space, e.g.:"
        log "    docker system prune            # unused images/containers/build cache"
        log "    sudo journalctl --vacuum-size=200M"
        log "    sudo du -xh --max-depth=1 /var/lib | sort -rh | head"
        log "Override the threshold with MIN_FREE_GB=<n> if you know better."
        exit 1
    fi

    log "Rebuilding local image (Dockerfile.local): $REBUILD_REASON"

    # Retry transient build failures. Reuse BuildKit's completed layers between
    # attempts: a changed upstream base already invalidates dependent layers, so
    # `--no-cache` added no freshness but made every retry re-download everything.
    # A single bad CDN node or momentary proxy hiccup could therefore waste both
    # time and several GiB before starting from zero again. Observed in practice:
    # deb.debian.org served a 5.7 kB HTML error page instead of the .deb,
    # yielding "Hash Sum mismatch" / "Unable to fetch some archives"; the exact
    # same build succeeded minutes later with no changes at all. Without a retry
    # the cron run just dies and kandev silently stays on the old image.
    #
    # KANDEV_BASE_IMAGE_ID feeds docker-compose.override.yml's BASE_IMAGE_ID
    # build arg (and thus the com.kandev.base-id label on the built image).
    BUILD_RETRIES="${BUILD_RETRIES:-3}"
    BUILD_RETRY_DELAY="${BUILD_RETRY_DELAY:-30}"
    BUILD_ATTEMPT_TIMEOUT_SECS="${BUILD_ATTEMPT_TIMEOUT_SECS:-900}"
    build_ok=0
    for attempt in $(seq 1 "$BUILD_RETRIES"); do
        log "Build attempt ${attempt}/${BUILD_RETRIES} ..."
        # `set +e` + PIPESTATUS: the exit status of the pipeline is tee's, not
        # docker's, so the build result must be read from PIPESTATUS[0].
        set +e
        KANDEV_BASE_IMAGE_ID="$UPSTREAM_ID" \
            timeout --signal=TERM --kill-after=30s "$BUILD_ATTEMPT_TIMEOUT_SECS" \
            docker compose -p kandev build \
            --build-arg BASE_IMAGE_ID="$UPSTREAM_ID" 2>&1 | tee -a "$LOG_FILE"
        rc=${PIPESTATUS[0]}
        set -e
        if [[ "$rc" -eq 0 ]]; then
            build_ok=1
            break
        fi
        if [[ "$rc" -eq 124 || "$rc" -eq 137 ]]; then
            log "Build attempt ${attempt} timed out after ${BUILD_ATTEMPT_TIMEOUT_SECS}s (exit $rc)."
        else
            log "Build attempt ${attempt} failed (exit $rc)."
        fi
        if [[ "$attempt" -lt "$BUILD_RETRIES" ]]; then
            log "Retrying in ${BUILD_RETRY_DELAY}s — transient mirror/proxy failures are common here."
            sleep "$BUILD_RETRY_DELAY"
        fi
    done
    if [[ "$build_ok" -ne 1 ]]; then
        log "CRITICAL: local image build failed after ${BUILD_RETRIES} attempts — aborting update."
        log "The running container is left untouched on its current image."
        exit 1
    fi
    log "Local image rebuilt."
fi

# ── Recreate only if the running container isn't already the target image ────
RUNNING_ID=$(docker inspect kandev --format '{{.Image}}' 2>/dev/null || echo "none")
TARGET_ID=$(docker image inspect "$TARGET_IMAGE" --format '{{.Id}}' 2>/dev/null || echo "unknown")

# Validate the exact candidate image under the host's currently loaded
# security policy before replacing a working container. This catches the
# image/AppArmor drift that otherwise presents as an endless exit-78 restart
# loop and takes the board offline. The probe is disposable and cannot mutate
# Kandev data because no deployment volumes are mounted.
if [[ "$TARGET_ID" == "unknown" ]] || ! docker run --rm \
    --security-opt seccomp="$COMPOSE_DIR/seccomp/kandev-bwrap.json" \
    --security-opt apparmor=kandev-codex \
    "$TARGET_IMAGE" /usr/local/bin/codex-sandbox-preflight >>"$LOG_FILE" 2>&1; then
    log "CRITICAL: candidate image failed the guarded ACP runtime preflight; refusing to deploy it."
    log "The existing container/image is preserved. Inspect the end of $LOG_FILE for the exact Bubblewrap/AppArmor error."
    exit 1
fi
log "Candidate image passed guarded ACP runtime preflight."

if [[ "$REBUILD" -eq 0 && "$RUNNING_ID" != "none" && "$RUNNING_ID" == "$TARGET_ID" ]]; then
    log "Already up to date — container already running $TARGET_IMAGE ($TARGET_ID). No restart needed."
    exit 0
fi

# Recreate container with the (possibly rebuilt) target image
log "Recreating kandev container (target: $TARGET_IMAGE)..."
docker compose -p kandev up -d --force-recreate

# Health-gate the update: a successful `docker compose up` only means the
# container process started, not that the backend came up (e.g. a broken
# DB migration crash-loops the container forever while `up -d` still exits 0).
# A prior incident silently left kandev unreachable for hours after an
# unattended update because nothing checked this. Poll the health endpoint;
# on failure, roll back to the pre-update image automatically so the service
# self-heals, and fail loudly (nonzero exit) so cron surfaces it.
#
# Timeout must be generous: the FIRST boot after a version jump runs DB
# migrations before the HTTP server binds, which was observed to take ~55s on
# a minor-version upgrade. A too-tight 60s gate caused a spurious rollback of a
# perfectly healthy new image. Restored boards with hundreds of sessions have
# subsequently needed more than 180 seconds for startup reconciliation, so the
# A live 2026-09-01 startup lifecycle recovery consumed the full 15-minute
# AgentLaunchTimeout before the board returned HTTP 200. Keep this external
# transaction gate just above that bound until the upstream listener-order
# defect is fixed; otherwise update and rollback can both be rejected too early.
# Override with HEALTH_TIMEOUT_SECS.
HEALTH_URL="http://localhost:38429/"
HEALTH_TIMEOUT_SECS="${HEALTH_TIMEOUT_SECS:-960}"
wait_for_health() {
    local i deadline
    deadline=$(( SECONDS + HEALTH_TIMEOUT_SECS ))
    while (( SECONDS < deadline )); do
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
    log "CRITICAL: kandev did not become healthy after update (no HTTP 200 on ${HEALTH_URL} after ${HEALTH_TIMEOUT_SECS}s)."
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
