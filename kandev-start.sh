#!/usr/bin/env bash
# kandev-start.sh — Start kandev with Litestream live sync.
#
# Flow:
#   1. Restore kandev.db from the FRESHEST Litestream replica across ALL hosts
#      on home-server (mirrors kandev-start-hub.sh's freshest-wins logic, but
#      queried over SSH). This is what lets you leave one host and continue on
#      another with the same board state. A data-loss GUARD skips the restore
#      when the local DB is newer than the freshest peer replica (i.e. this host
#      has unpushed local edits) — never silently revert real local work.
#   2. Acquire the single-active-writer lock on home-server. Only the lock
#      holder is allowed to run the Litestream push sidecar. If another host
#      is still actively pushing (checked via freshness of ITS replica, not
#      ICMP/SSH reachability — avoids VPN/routing false negatives), this host
#      starts kandev WITHOUT the sidecar and warns that local edits will not
#      replicate until it can acquire the lock.
#   3. Start kandev (+ Litestream sidecar, if lock acquired) via docker compose.
#
# Why a lock at all: Litestream is single-leader replication. Two hosts
# pushing while both being treated as "the current truth" causes exactly the
# data-loss bugs seen 2026-07-07/08 (stale host silently overwrote real data
# on restore). The lock enforces "only one host edits at a time" — which
# matches how kandev is actually used (one physical location at a time).
#
# Usage:
#   bash ~/Code/kandev/kandev-start.sh              # normal (with Litestream)
#   bash ~/Code/kandev/kandev-start.sh --no-sync    # skip restore + lock (offline / debug)
#   bash ~/Code/kandev/kandev-start.sh --release-lock  # release this host's lock, then exit
#   bash ~/Code/kandev/kandev-start.sh --recreate    # force-recreate the container(s)
#
# Note on --recreate: `docker compose up -d` is idempotent — it will NOT touch a
# container that is already running with unchanged config. So a plain start/reload
# is a no-op for an already-running container. --recreate adds `--force-recreate`
# so `systemctl --user reload kandev` (ExecReload) actually restarts the container.
#
# Called by: systemd kandev.service ExecStart (normal), ExecStop (--release-lock),
#            ExecReload (--recreate).
set -euo pipefail

# ── Machine-specific overrides ───────────────────────────────────────────────
# Load real hosts/users/IPs for THIS machine from a gitignored host.env so this
# public repo stays free of private LAN details. See host.env.example. The
# ${VAR:-default} placeholders below are only used when host.env is absent.
_KANDEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[ -f "$_KANDEV_DIR/host.env" ] && . "$_KANDEV_DIR/host.env"

COMPOSE_DIR="${COMPOSE_DIR:-$HOME/Code/kandev}"
KANDEV_DATA="${KANDEV_DATA:-$HOME/.local/share/kandev/data}"
MINI_HOST="${MINI_HOST:-10.0.0.20}"
MINI_USER="${MINI_USER:-bob}"
REPLICA_ROOT="${REPLICA_ROOT:-/home/${MINI_USER}/litestream-replicas/kandev}"
HOST_ID_FILE="${HOST_ID_FILE:-$HOME/.kandev-host-id}"
LITESTREAM_CONFIG="${LITESTREAM_CONFIG:-$HOME/.config/litestream/litestream.yml}"
LOG="${LOG:-$HOME/logs/kandev-sync.log}"
LOCK_STALE_SECS="${LOCK_STALE_SECS:-120}"
# Margin (seconds) the freshest peer replica must beat the local DB's mtime by
# before we overwrite local data on restore. Guards against reverting unpushed
# local edits (the exact failure that stranded office's work during the VPN outage).
RESTORE_MARGIN_SECS="${RESTORE_MARGIN_SECS:-60}"
ARG="${1:-}"

# --recreate (may be passed alone or alongside another mode) forces
# `docker compose up` to add --force-recreate so an already-running container
# is actually restarted (used by systemd ExecReload).
RECREATE=0
for _a in "$@"; do [[ "$_a" == "--recreate" ]] && RECREATE=1; done

mkdir -p "$(dirname "$LOG")" "$KANDEV_DATA"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

if [[ -f "$HOST_ID_FILE" ]]; then
  HOST_ID="$(tr -d '[:space:]' < "$HOST_ID_FILE")"
else
  HOST_ID="$(hostname -s)"
  log "WARNING: $HOST_ID_FILE missing — falling back to hostname '$HOST_ID' as host-id"
fi

# SFTP private key used to reach home for restore. Auto-detect the first that
# exists (carol uses ~/.config/litestream/litestream-key, office uses
# ~/.ssh/id_ed25519). Override with LITESTREAM_KEY=/path.
LITESTREAM_KEY="${LITESTREAM_KEY:-}"
if [[ -z "$LITESTREAM_KEY" ]]; then
  for _k in "$HOME/.config/litestream/litestream-key" "$HOME/.ssh/id_ed25519" \
            "$HOME/.ssh/id_ed25519" "$HOME/.ssh/id_rsa"; do
    [[ -f "$_k" ]] && { LITESTREAM_KEY="$_k"; break; }
  done
fi

# Ask home (over SSH) which host's replica is freshest across ALL host dirs, and
# how fresh THIS host's own replica is. Echoes: "<best_host> <best_mtime> <own_mtime>"
# (mtimes are epoch seconds; 0 when absent). Empty best_host = no replicas yet.
pick_freshest_replica() {
  ssh -o ConnectTimeout=8 -o BatchMode=yes "${MINI_USER}@${MINI_HOST}" \
    bash -s -- "$REPLICA_ROOT" "$HOST_ID" 2>>"$LOG" <<'REMOTE'
set -u
REPLICA_ROOT="$1"; SELF="$2"
newest() {
  local d="$1/ltx"
  [[ -d "$d" ]] && find "$d" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1
}
best_host=""; best_m=0; own_m=0
for hd in "$REPLICA_ROOT"/*/; do
  [[ -d "$hd" ]] || continue
  hid="$(basename "$hd")"
  [[ "$hid" == "active.lock.d" ]] && continue
  m="$(newest "$hd")"; [[ -z "$m" ]] && m=0
  [[ "$hid" == "$SELF" ]] && own_m="$m"
  if [[ "$m" -gt "$best_m" ]]; then best_m="$m"; best_host="$hid"; fi
done
echo "$best_host $best_m $own_m"
REMOTE
}

# ── lock helpers ─────────────────────────────────────────────────────────────
# The lock lives on home-server as a directory (mkdir is atomic) containing an
# "owner" file: "<host-id> <iso-timestamp>". Staleness is judged NOT by ping
# but by how recently the claimed owner's OWN replica dir received a push —
# this sidesteps all VPN/routing ambiguity, since it's answered entirely by
# home (which both hosts already reach reliably for restore/push).
release_lock() {
  ssh -o ConnectTimeout=8 -o BatchMode=yes "${MINI_USER}@${MINI_HOST}" \
    bash -s -- "$HOST_ID" "$REPLICA_ROOT" <<'REMOTE' 2>>"$LOG" || true
set -u
HOST_ID="$1"; REPLICA_ROOT="$2"
LOCK_DIR="$REPLICA_ROOT/active.lock.d"
OWNER_FILE="$LOCK_DIR/owner"
if [[ -f "$OWNER_FILE" ]]; then
  owner_id="$(awk '{print $1}' "$OWNER_FILE" 2>/dev/null)"
  if [[ "$owner_id" == "$HOST_ID" ]]; then
    rm -rf "$LOCK_DIR"
    echo "RELEASED"
  fi
fi
REMOTE
}

acquire_lock() {
  ssh -o ConnectTimeout=8 -o BatchMode=yes "${MINI_USER}@${MINI_HOST}" \
    bash -s -- "$HOST_ID" "$REPLICA_ROOT" "$LOCK_STALE_SECS" <<'REMOTE' 2>>"$LOG"
set -u
HOST_ID="$1"; REPLICA_ROOT="$2"; STALE_SECS="$3"
LOCK_DIR="$REPLICA_ROOT/active.lock.d"
OWNER_FILE="$LOCK_DIR/owner"
mkdir -p "$REPLICA_ROOT"

claim() {
  echo "$HOST_ID $(date -Iseconds)" > "$OWNER_FILE"
}

if mkdir "$LOCK_DIR" 2>/dev/null; then
  claim
  echo "ACQUIRED"
  exit 0
fi

owner_id="$(awk '{print $1}' "$OWNER_FILE" 2>/dev/null || true)"
if [[ "$owner_id" == "$HOST_ID" ]]; then
  claim
  echo "ACQUIRED"
  exit 0
fi

owner_ltx_dir="$REPLICA_ROOT/$owner_id/ltx"
newest=0
if [[ -n "$owner_id" ]] && [[ -d "$owner_ltx_dir" ]]; then
  newest="$(find "$owner_ltx_dir" -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1 | cut -d. -f1)"
  [[ -z "$newest" ]] && newest=0
fi
now="$(date +%s)"
age=$(( now - newest ))

if [[ -z "$owner_id" ]] || [[ "$newest" -eq 0 ]] || [[ "$age" -gt "$STALE_SECS" ]]; then
  rm -rf "$LOCK_DIR"
  mkdir "$LOCK_DIR"
  claim
  echo "STOLEN previous_owner=${owner_id:-none} age=${age}s"
  exit 0
fi

echo "HELD_BY=$owner_id age=${age}s"
exit 1
REMOTE
}

if [[ "$ARG" == "--release-lock" ]]; then
  log "Releasing active-writer lock for host-id '$HOST_ID'..."
  RESULT="$(release_lock)"
  log "release_lock: ${RESULT:-no-op (lock not held by this host)}"
  exit 0
fi

WRITER_MODE=1  # 1 = we may run the litestream sidecar, 0 = read-only (no sidecar)

# ── 1. Restore from the FRESHEST replica across all hosts (freshest-wins) ─────
#     Guarded: never overwrite local data that is newer than the freshest peer
#     replica (i.e. this host has unpushed edits). --no-sync skips entirely.
if [[ "$ARG" != "--no-sync" ]]; then
  if ping -c1 -W3 "$MINI_HOST" >/dev/null 2>&1; then
    log "Querying home for freshest replica (host-id: $HOST_ID)..."
    FRESHEST="$(pick_freshest_replica || true)"
    BEST_HOST="$(awk '{print $1}' <<<"$FRESHEST")"
    BEST_MTIME="$(awk '{print $2}' <<<"$FRESHEST")"; [[ -z "$BEST_MTIME" ]] && BEST_MTIME=0
    OWN_MTIME="$(awk '{print $3}' <<<"$FRESHEST")"; [[ -z "$OWN_MTIME" ]] && OWN_MTIME=0
    log "Freshest replica: host='${BEST_HOST:-none}' mtime=$BEST_MTIME (own replica mtime=$OWN_MTIME)"

    # Data-loss guard: if THIS host's own replica is at least as fresh as the
    # best (i.e. we are — or tie with — the most recent writer), don't restore
    # over our own data. Also skip if there's no replica yet.
    if [[ -z "$BEST_HOST" ]] || [[ "$BEST_MTIME" -eq 0 ]]; then
      log "No replica data on hub yet — starting with existing local data"
    elif [[ "$BEST_HOST" == "$HOST_ID" ]] || [[ "$OWN_MTIME" -ge $(( BEST_MTIME - RESTORE_MARGIN_SECS )) ]]; then
      log "Local data is freshest (own=$OWN_MTIME ≥ best=$BEST_MTIME−${RESTORE_MARGIN_SECS}s) — skipping restore to avoid reverting local edits"
    else
      REPLICA_PATH_BEST="${REPLICA_ROOT}/${BEST_HOST}"
      log "Restoring from freshest peer '$BEST_HOST': sftp://${MINI_USER}@${MINI_HOST}${REPLICA_PATH_BEST}"

      if [[ -z "$LITESTREAM_KEY" ]]; then
        log "WARNING: no SFTP key found (looked for litestream-key / id_ed25519 / id_*) — skipping restore"
      else
        # Safety: back up current DB before any restore attempt
        if [[ -f "${KANDEV_DATA}/kandev.db" ]]; then
          cp -p "${KANDEV_DATA}/kandev.db" "${KANDEV_DATA}/kandev.db.pre-restore"
          log "Backed up existing DB → kandev.db.pre-restore ($(stat -c%s "${KANDEV_DATA}/kandev.db") bytes)"
        fi

        # Build a throwaway config pointing at the FRESHEST PEER's replica path,
        # with the auto-detected key mounted at a fixed container path. This
        # sidesteps the per-host key-path/known-hosts differences baked into each
        # host's own litestream.yml (which only knows its OWN replica path).
        LITESTREAM_TMP_CFG="$(mktemp /tmp/litestream-restore-XXXXXX.yml)"
        cat > "$LITESTREAM_TMP_CFG" <<EOF
dbs:
  - path: /data/kandev.db
    replicas:
      - type: sftp
        host: "${MINI_HOST}"
        user: "${MINI_USER}"
        key-path: /keys/restore-key
        path: ${REPLICA_PATH_BEST}
EOF

        # -config: without it litestream reads the default /etc/litestream.yml
        #   (not our mount) and silently no-ops — see Bug #3.
        # -force: kandev.db always pre-exists (runs on every start); litestream
        #   refuses to overwrite an existing output path otherwise.
        # --user matches the host UID so the restored db stays host-owned (kandev
        #   reads it) and the host-owned key file is readable.
        if docker run --rm \
            --user "$(id -u):$(id -g)" \
            -v "${KANDEV_DATA}:/data" \
            -v "${LITESTREAM_KEY}:/keys/restore-key:ro" \
            -v "${LITESTREAM_TMP_CFG}:/etc/litestream/litestream.yml:ro" \
            litestream/litestream:latest \
            restore -config /etc/litestream/litestream.yml -if-replica-exists -force /data/kandev.db >> "$LOG" 2>&1; then
          log "Restore complete — now serving freshest data (from '$BEST_HOST')"
        else
          log "WARNING: restore failed — rolling back to pre-restore backup"
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
      fi
    fi

    # ── 2. Active-writer lock ──────────────────────────────────────────────
    log "Requesting active-writer lock (host-id: $HOST_ID)..."
    if LOCK_RESULT="$(acquire_lock)"; then
      log "Lock: $LOCK_RESULT"
      WRITER_MODE=1
    else
      log "Lock: $LOCK_RESULT"
      WRITER_MODE=0
      log "⚠ Another host is actively syncing kandev right now. Starting in READ-ONLY sync mode:"
      log "⚠   this host will NOT run the Litestream push sidecar, so any edits made here"
      log "⚠   will NOT be replicated until the other host goes offline or its lock expires."
    fi
  else
    log "home-server ($MINI_HOST) unreachable — skipping restore and lock, using local data"
    log "⚠ Litestream sidecar will NOT start this run (no reachable hub) — edits won't sync until reconnected."
    WRITER_MODE=0
  fi
else
  log "Sync skipped (--no-sync)"
  WRITER_MODE=0
fi

# ── 3. Start kandev (+ Litestream sidecar, only if we hold the writer lock) ──
cd "$COMPOSE_DIR"

# Docker cannot load named AppArmor profiles from Compose. Refuse to create a
# worker that would fail every Codex sandbox command; the fix command is
# printed by the check.
bash "$COMPOSE_DIR/scripts/check-codex-runtime.sh"

RECREATE_ARG=""
[[ "$RECREATE" -eq 1 ]] && RECREATE_ARG="--force-recreate"

if [[ "$WRITER_MODE" -eq 1 ]] && [[ -f "$LITESTREAM_CONFIG" ]] && [[ "$ARG" != "--no-sync" ]]; then
  log "Starting kandev + Litestream sidecar (active writer)..."
  # Explicitly include override.yml so SSH keys, identity mounts, and .env are preserved.
  # docker-compose.override.yml is only auto-merged when no -f flags are used.
  OVERRIDE=""
  [[ -f "$COMPOSE_DIR/docker-compose.override.yml" ]] && OVERRIDE="-f docker-compose.override.yml"
  docker compose -f docker-compose.yml $OVERRIDE -f docker-compose.litestream.yml -p kandev up -d --remove-orphans $RECREATE_ARG
else
  log "Starting kandev WITHOUT Litestream sidecar (read-only sync mode or --no-sync)..."
  docker compose -p kandev up -d --remove-orphans $RECREATE_ARG
fi

log "kandev started"
