#!/usr/bin/env bash
# kandev-pull.sh — Manually check for newer kandev data and pull it if behind.
#
# What it does:
#   1. Asks mini-desktop which host's Litestream replica is freshest, and how
#      fresh THIS host's own replica is (all mtimes come from mini's filesystem,
#      so they're directly comparable — no local-vs-hub clock skew).
#   2. Reads who currently holds the active-writer lock.
#   3. Decides:
#        • This host IS the active writer  → nothing to pull (you're the source
#          of truth). Just make sure kandev is up. Use --force to pull anyway.
#        • A peer replica is newer than ours → we're BEHIND → stop kandev, then
#          run kandev-start.sh (freshest-wins restore + lock + start).
#        • Already current                 → just make sure kandev is up.
#
# The heavy lifting (guarded restore, lock, sidecar) lives in kandev-start.sh —
# this script only decides whether a restore-restart is worth doing.
#
# Usage:
#   bash ~/Code/kandev/kandev-pull.sh            # check + pull if behind + start
#   bash ~/Code/kandev/kandev-pull.sh --force    # pull even if we look current/writer
#   bash ~/Code/kandev/kandev-pull.sh --dry-run  # report only, change nothing
#
# Safe to run on a cron schedule (e.g. 06:00 / 13:00 / 18:00) — it no-ops when
# this host is the active writer or already current, so it won't disturb work.
set -euo pipefail

COMPOSE_DIR="${COMPOSE_DIR:-$HOME/Code/kandev}"
MINI_HOST="${MINI_HOST:-10.0.0.182}"
MINI_USER="${MINI_USER:-alassane}"
REPLICA_ROOT="${REPLICA_ROOT:-/home/${MINI_USER}/litestream-replicas/kandev}"
HOST_ID_FILE="${HOST_ID_FILE:-$HOME/.kandev-host-id}"
START_SCRIPT="${START_SCRIPT:-$COMPOSE_DIR/kandev-start.sh}"
LOG="${LOG:-$HOME/logs/kandev-sync.log}"
# A peer replica must beat our own replica by at least this many seconds before
# we treat ourselves as "behind" (avoids churn on tiny timestamp differences).
PULL_MARGIN_SECS="${PULL_MARGIN_SECS:-60}"
ARG="${1:-}"

mkdir -p "$(dirname "$LOG")"
log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] [pull] $*" | tee -a "$LOG"; }

if [[ -f "$HOST_ID_FILE" ]]; then
  HOST_ID="$(tr -d '[:space:]' < "$HOST_ID_FILE")"
else
  HOST_ID="$(hostname -s)"
  log "WARNING: $HOST_ID_FILE missing — falling back to hostname '$HOST_ID' as host-id"
fi

FORCE=0; DRY=0
case "$ARG" in
  --force)   FORCE=1 ;;
  --dry-run) DRY=1 ;;
  "" )       ;;
  * ) echo "usage: $0 [--force|--dry-run]" >&2; exit 2 ;;
esac

start_kandev() {
  # "Ensure up" — never disturb an already-running instance (which may be an
  # active writer with a live sidecar). Only start when kandev is actually down.
  if docker ps --filter 'name=^kandev$' --filter 'status=running' --format '{{.Names}}' 2>/dev/null | grep -qx kandev; then
    log "kandev already running — leaving it untouched."
    return 0
  fi
  if [[ "$DRY" -eq 1 ]]; then log "[dry-run] kandev is down; would run: $START_SCRIPT"; return 0; fi
  log "kandev is down — starting it..."
  bash "$START_SCRIPT"
}

restart_and_pull() {
  if [[ "$DRY" -eq 1 ]]; then
    log "[dry-run] would: docker compose -p kandev down && $START_SCRIPT"
    return 0
  fi
  log "Stopping kandev to restore freshest data cleanly..."
  ( cd "$COMPOSE_DIR" && docker compose -p kandev down ) >> "$LOG" 2>&1 || true
  # kandev-start.sh performs the guarded freshest-wins restore, lock, and start.
  bash "$START_SCRIPT"
}

# ── Reachability ─────────────────────────────────────────────────────────────
if ! ping -c1 -W3 "$MINI_HOST" >/dev/null 2>&1; then
  log "mini-desktop ($MINI_HOST) unreachable — cannot check for newer data."
  log "Ensuring kandev is running with local data..."
  start_kandev
  exit 0
fi

# ── Query mini: freshest replica + own freshness + lock owner ────────────────
REMOTE_OUT="$(ssh -o ConnectTimeout=8 -o BatchMode=yes "${MINI_USER}@${MINI_HOST}" \
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
lock_owner=""
of="$REPLICA_ROOT/active.lock.d/owner"
[[ -f "$of" ]] && lock_owner="$(awk '{print $1}' "$of" 2>/dev/null)"
echo "$best_host $best_m $own_m ${lock_owner:-none}"
REMOTE
)"

BEST_HOST="$(awk '{print $1}' <<<"$REMOTE_OUT")"
BEST_MTIME="$(awk '{print $2}' <<<"$REMOTE_OUT")"; [[ -z "$BEST_MTIME" ]] && BEST_MTIME=0
OWN_MTIME="$(awk '{print $3}' <<<"$REMOTE_OUT")"; [[ -z "$OWN_MTIME" ]] && OWN_MTIME=0
LOCK_OWNER="$(awk '{print $4}' <<<"$REMOTE_OUT")"; [[ -z "$LOCK_OWNER" ]] && LOCK_OWNER="none"

fmt() { [[ "$1" -gt 0 ]] && date -d "@$1" '+%Y-%m-%d %H:%M:%S' || echo "none"; }
log "host-id=$HOST_ID  writer=$LOCK_OWNER"
log "freshest replica : '${BEST_HOST:-none}'  ($(fmt "$BEST_MTIME"))"
log "our own replica  : $(fmt "$OWN_MTIME")"

# ── Decide ───────────────────────────────────────────────────────────────────
if [[ -z "$BEST_HOST" ]] || [[ "$BEST_MTIME" -eq 0 ]]; then
  log "No replica data on hub yet — nothing to pull. Ensuring kandev is up."
  start_kandev
  exit 0
fi

if [[ "$FORCE" -eq 1 ]]; then
  log "--force given → pulling freshest ('$BEST_HOST') regardless of state."
  restart_and_pull
  exit 0
fi

if [[ "$LOCK_OWNER" == "$HOST_ID" ]]; then
  log "This host is the ACTIVE WRITER — your data is authoritative. Not pulling."
  log "(Use --force to override.) Ensuring kandev is up."
  start_kandev
  exit 0
fi

if [[ "$BEST_HOST" == "$HOST_ID" ]]; then
  log "Freshest replica is our own push — already current. Ensuring kandev is up."
  start_kandev
  exit 0
fi

if [[ "$BEST_MTIME" -gt $(( OWN_MTIME + PULL_MARGIN_SECS )) ]]; then
  BEHIND=$(( BEST_MTIME - OWN_MTIME ))
  log "BEHIND by ~${BEHIND}s vs peer '$BEST_HOST' — pulling freshest data."
  restart_and_pull
  exit 0
fi

log "Already current (within ${PULL_MARGIN_SECS}s of freshest). Ensuring kandev is up."
start_kandev
exit 0
