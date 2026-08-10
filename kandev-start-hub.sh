#!/usr/bin/env bash
# kandev-start-hub.sh — Start kandev on home-server (hub role).
#
# home-server is the central replica hub — it STORES Litestream WAL segments
# pushed by office-desktop and laptop, each into ITS OWN dedicated subdir
# (never a shared path — see REPLICA_ROOT layout below). home does NOT run
# Litestream as a push sidecar itself.
#
# On startup, this script picks whichever satellite host's replica has the
# MOST RECENT WAL activity (freshest LTX segment mtime) and restores from
# THAT one — this is the authoritative "who edited most recently" signal,
# entirely local to home, no cross-host reachability needed. It then starts
# kandev standalone (no Litestream sidecar).
#
# Replica layout:
#   ~/litestream-replicas/kandev/office/       — pushed by office-desktop
#   ~/litestream-replicas/kandev/laptop/   — pushed by laptop
#   ~/litestream-replicas/kandev/active.lock.d/  — active-writer lock (see kandev-start.sh)
#
# Flow:
#   1. Compare freshness of kandev/office/ltx vs kandev/laptop/ltx
#   2. Restore from the freshest → ~/.local/share/kandev/data/kandev.db
#   3. docker compose -p kandev up -d
#
# Usage:
#   bash ~/Code/kandev/kandev-start-hub.sh
#   bash ~/Code/kandev/kandev-start-hub.sh --no-sync   # skip restore
#   bash ~/Code/kandev/kandev-start-hub.sh --recreate  # force-recreate the container
#
# Note on --recreate: `docker compose up -d` is idempotent — it won't touch an
# already-running container. --recreate adds `--force-recreate` so systemd
# ExecReload (`systemctl --user reload kandev`) actually restarts it.
#
# Called by: systemd kandev.service on home-server.
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-$HOME/Code/kandev}"
KANDEV_DATA="${KANDEV_DATA:-$HOME/.local/share/kandev/data}"
REPLICA_ROOT="${REPLICA_ROOT:-$HOME/litestream-replicas/kandev}"
LOG="${LOG:-$HOME/logs/kandev-sync.log}"
SKIP_SYNC="${1:-}"

# --recreate (may be passed alone or with --no-sync) forces --force-recreate so
# an already-running container is actually restarted (used by systemd ExecReload).
RECREATE=0
for _a in "$@"; do [[ "$_a" == "--recreate" ]] && RECREATE=1; done

mkdir -p "$(dirname "$LOG")" "$KANDEV_DATA"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

log "--- kandev-start-hub ---"

# Return the newest LTX segment mtime (epoch) under a given host's replica dir,
# or 0 if the dir is missing/empty.
newest_mtime() {
  local dir="$1/ltx"
  if [[ -d "$dir" ]]; then
    find "$dir" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1
  fi
}

# ── 1. Pick freshest per-host replica (unless --no-sync) ────────────────────
if [[ "$SKIP_SYNC" != "--no-sync" ]]; then
  BEST_HOST=""
  BEST_MTIME=0
  for host_dir in "$REPLICA_ROOT"/*/; do
    [[ -d "$host_dir" ]] || continue
    host_id="$(basename "$host_dir")"
    [[ "$host_id" == "active.lock.d" ]] && continue
    m="$(newest_mtime "$host_dir")"
    [[ -z "$m" ]] && m=0
    log "Replica '$host_id': newest segment mtime=$m"
    if [[ "$m" -gt "$BEST_MTIME" ]]; then
      BEST_MTIME="$m"
      BEST_HOST="$host_id"
    fi
  done

  if [[ -n "$BEST_HOST" ]] && [[ "$BEST_MTIME" -gt 0 ]]; then
    REPLICA_DIR="$REPLICA_ROOT/$BEST_HOST"
    log "Freshest replica is '$BEST_HOST' (mtime=$BEST_MTIME) — restoring from it"

    # Safety: back up current DB before restore
    if [[ -f "${KANDEV_DATA}/kandev.db" ]]; then
      cp -p "${KANDEV_DATA}/kandev.db" "${KANDEV_DATA}/kandev.db.pre-restore"
      log "Backed up existing DB → kandev.db.pre-restore ($(stat -c%s "${KANDEV_DATA}/kandev.db") bytes)"
    fi

    # Write a temporary litestream config pointing to the chosen replica dir
    LITESTREAM_TMP_CFG="/tmp/litestream-home-$$.yml"
    cat > "$LITESTREAM_TMP_CFG" <<EOF
dbs:
  - path: /data/kandev.db
    replicas:
      - type: file
        path: /replicas/kandev
EOF

    # -config: litestream defaults to /etc/litestream.yml, NOT the mounted
    #   /etc/litestream/litestream.yml path, so this flag is required or the
    #   restore silently no-ops (reports success while restoring nothing).
    # -force: kandev.db always exists already (this runs on every start), and
    #   litestream refuses to restore over an existing output path otherwise.
    # --user: the image's default user is "nonroot", which cannot write to
    #   host-owned (UID 1000) files — match the host user so the restore can
    #   actually write /data/kandev.db.
    if docker run --rm \
        --user "$(id -u):$(id -g)" \
        -v "${KANDEV_DATA}:/data" \
        -v "${REPLICA_DIR}:/replicas/kandev:ro" \
        -v "${LITESTREAM_TMP_CFG}:/etc/litestream/litestream.yml:ro" \
        litestream/litestream:latest \
        restore -config /etc/litestream/litestream.yml -if-replica-exists -force /data/kandev.db >> "$LOG" 2>&1; then
      log "Restore complete — home serving latest synced data (from '$BEST_HOST')"
    else
      log "WARNING: local restore failed — keeping existing kandev.db"
      # Rollback if restore left a smaller (partial) file
      if [[ -f "${KANDEV_DATA}/kandev.db.pre-restore" ]]; then
        PRE=$(stat -c%s "${KANDEV_DATA}/kandev.db.pre-restore" 2>/dev/null || echo 0)
        CUR=$(stat -c%s "${KANDEV_DATA}/kandev.db" 2>/dev/null || echo 0)
        if [[ "$CUR" -lt "$PRE" ]]; then
          cp -p "${KANDEV_DATA}/kandev.db.pre-restore" "${KANDEV_DATA}/kandev.db"
          log "Rolled back (pre-restore ${PRE}B > current ${CUR}B)"
        fi
      fi
    fi

    rm -f "$LITESTREAM_TMP_CFG"
  else
    log "No replica data found under any host dir in $REPLICA_ROOT — skipping restore, using local data"
  fi
else
  log "Sync skipped (--no-sync)"
fi

# ── 2. Start kandev (plain, no Litestream sidecar) ──────────────────────────
log "Starting kandev..."
cd "$COMPOSE_DIR"
RECREATE_ARG=""
[[ "$RECREATE" -eq 1 ]] && RECREATE_ARG="--force-recreate"
docker compose -p kandev up -d --remove-orphans $RECREATE_ARG
log "kandev started"
