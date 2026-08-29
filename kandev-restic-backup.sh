#!/usr/bin/env bash
# kandev-restic-backup.sh — Daily restic snapshot of kandev data.
#
# Creates a named, deduplicated snapshot in home-server's restic repo, falling
# back to a local repository outside ~/Code when the VPN/remote is unavailable.
# Snapshots are browsable with `restic snapshots` — like `git log` for your data.
# Retention: 7 daily + 4 weekly + 3 monthly (pruned automatically).
#
# NO DOWNTIME: kandev is an AI-agent orchestrator — stopping it kills every
# in-flight agent session/task. This script therefore NEVER stops kandev. It
# takes a transactionally-consistent hot copy of the SQLite database via
# SQLite's online-backup API (`sqlite3 .backup`, safe against a live WAL-mode
# DB), then lets restic back up that snapshot instead of the live DB file.
#
# Repo location (on home-server): ~/restic-repos/kandev-backup
# Password file: ~/.config/restic/kandev-backup-password (same on all hosts)
#
# Usage:
#   bash ~/Code/kandev/kandev-restic-backup.sh
#
# Cron (all hosts, 03:00 daily):
#   0 3 * * * bash ~/Code/kandev/kandev-restic-backup.sh >> ~/logs/kandev-backup.log 2>&1
#
# On home-server the cron runs as root via /etc/cron.d/kandev-backup;
# on office-desktop and laptop it runs as the normal user via crontab.
#
# Error handling: we deliberately do NOT use `set -e`. The previous version did,
# which meant a non-zero `restic backup` (e.g. rc=3 unreadable files, or rc=1
# "no space left on device" on the hub) aborted the script *before* it restarted
# kandev — stranding the container stopped until a human noticed. This version
# never stops kandev at all, and also handles restic's exit code explicitly.
set -uo pipefail

# ── Machine-specific overrides ───────────────────────────────────────────────
# Load real hosts/users/IPs for THIS machine from a gitignored host.env so this
# public repo stays free of private LAN details. See host.env.example. The
# ${VAR:-default} placeholders below are only used when host.env is absent.
_KANDEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[ -f "$_KANDEV_DIR/host.env" ] && . "$_KANDEV_DIR/host.env"

USER_HOME="${USER_HOME:-$HOME}"
USER_NAME="${USER_NAME:-$(whoami)}"
MINI_HOST="${MINI_HOST:-10.0.0.20}"
MINI_USER="${MINI_USER:-bob}"
RESTIC="${RESTIC:-$(command -v restic 2>/dev/null || echo "$USER_HOME/bin/restic")}"
REMOTE_RESTIC_REPO="${RESTIC_REPO:-sftp:${MINI_USER}@${MINI_HOST}:restic-repos/kandev-backup}"
LOCAL_RESTIC_REPO="${LOCAL_RESTIC_REPO:-$USER_HOME/Backups/restic/kandev-backup}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-$USER_HOME/.config/restic/kandev-backup-password}"
KANDEV_DATA="${KANDEV_DATA:-$USER_HOME/.local/share/kandev}"
COMPOSE_DIR="${COMPOSE_DIR:-$USER_HOME/Code/kandev}"
LOG="${LOG:-$USER_HOME/logs/kandev-backup.log}"
LOCK="${LOCK:-/run/lock/kandev-restic-backup.lock}"
PING="${PING:-$(command -v ping 2>/dev/null || echo /usr/bin/ping)}"

mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

exec 9>"$LOCK"
if ! flock -n 9; then
  log "Another backup is running, skipping"
  exit 0
fi

log "--- kandev restic backup start (host: $(hostname)) ---"

# Never place the fallback repository inside the tree being backed up (which
# would recurse forever). The default is ~/Backups/restic/kandev-backup.
case "$LOCAL_RESTIC_REPO" in
  "$KANDEV_DATA"|"$KANDEV_DATA"/*)
    log "ERROR: LOCAL_RESTIC_REPO must be outside KANDEV_DATA: $LOCAL_RESTIC_REPO"
    exit 78
    ;;
esac

restic_repo() {
  local repo="$1"
  shift
  RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" "$RESTIC" -r "$repo" "$@"
}

ensure_repo() {
  local repo="$1"
  if restic_repo "$repo" snapshots --no-lock >/dev/null 2>&1; then
    return 0
  fi
  if [[ "$repo" != sftp:* ]]; then
    mkdir -p "$repo"
  fi
  log "Repo not found or unavailable — attempting restic init: $repo"
  if restic_repo "$repo" init >>"$LOG" 2>&1; then
    log "Repo initialized: $repo"
    return 0
  fi
  return 1
}

# Prefer the remote repository. Loss of VPN/ICMP/SFTP availability selects a
# local repository, so every scheduled run still creates a recoverable copy.
BACKUP_REPO="$REMOTE_RESTIC_REPO"
if ! "$PING" -c1 -W3 "$MINI_HOST" >/dev/null 2>&1; then
  log "home-server ($MINI_HOST) unreachable — using local fallback: $LOCAL_RESTIC_REPO"
  BACKUP_REPO="$LOCAL_RESTIC_REPO"
elif ! ensure_repo "$REMOTE_RESTIC_REPO"; then
  log "Remote restic repo unavailable — using local fallback: $LOCAL_RESTIC_REPO"
  BACKUP_REPO="$LOCAL_RESTIC_REPO"
fi

if [[ "$BACKUP_REPO" == "$LOCAL_RESTIC_REPO" ]] && ! ensure_repo "$LOCAL_RESTIC_REPO"; then
  log "ERROR: local fallback repo could not be initialized: $LOCAL_RESTIC_REPO"
  exit 1
fi

# ── Consistent SQLite snapshot WITHOUT stopping kandev ──────────────────────
# kandev is an AI-agent orchestrator: stopping it kills every in-flight agent
# session/task, forcing a manual re-run of everything. So we NEVER stop it for
# a backup. Instead we take a consistent hot copy of the SQLite database using
# SQLite's online-backup API (`sqlite3 .backup`), which is safe to run against a
# live WAL-mode database from a separate process — it coordinates via SQLite's
# own locking and retries around concurrent writes, producing a
# transactionally-consistent file. The copy is made by a throwaway container
# built from the kandev image (which ships sqlite3), so it works on every host
# and even when the kandev container itself happens to be down. restic then
# backs up the whole data tree but EXCLUDES the live db/-wal/-shm (torn if
# copied mid-write) and INCLUDES the consistent snapshot in their place.
KANDEV_IMAGE="${KANDEV_IMAGE:-kandev-local:latest}"
DB_DIR="$KANDEV_DATA/data"
DB_FILE="$DB_DIR/kandev.db"
SNAP_NAME="kandev.db.backup-snapshot"
SNAP_FILE="$DB_DIR/$SNAP_NAME"

# Always remove the (~0.6 GB) snapshot on any exit so a stale copy never lingers.
cleanup_snapshot() {
  rm -f "$SNAP_FILE" "$SNAP_FILE-journal" "$SNAP_FILE-wal" "$SNAP_FILE-shm" 2>/dev/null || true
}
trap cleanup_snapshot EXIT

DB_EXCLUDES=()
if [[ -f "$DB_FILE" ]]; then
  cleanup_snapshot
  log "Creating consistent kandev.db snapshot (hot — kandev stays running)..."
  if docker run --rm -u "$(id -u)":"$(id -g)" -v "$DB_DIR:/db" "$KANDEV_IMAGE" \
        sqlite3 "/db/kandev.db" ".backup '/db/$SNAP_NAME'" >>"$LOG" 2>&1 \
     && [[ -s "$SNAP_FILE" ]]; then
    log "Snapshot OK ($(du -h "$SNAP_FILE" 2>/dev/null | cut -f1)) — backing up snapshot, excluding live DB."
    DB_EXCLUDES=(
      --exclude "$DB_FILE"
      --exclude "$DB_FILE-wal"
      --exclude "$DB_FILE-shm"
      --exclude "$DB_DIR/kandev.db.pre-restore"
    )
  else
    log "WARNING: hot sqlite snapshot failed — restic will fall back to a raw (best-effort) copy of the live DB."
    cleanup_snapshot
  fi
fi

# ── Backup (kandev keeps running throughout) ────────────────────────────────
run_backup() {
  local repo="$1"
  log "Running restic backup: $KANDEV_DATA → $repo"
  restic_repo "$repo" backup \
    --tag "kandev" \
    --tag "$(hostname)" \
    --host "$(hostname)" \
    "${DB_EXCLUDES[@]}" \
    "$KANDEV_DATA" >> "$LOG" 2>&1
}

run_backup "$BACKUP_REPO"
backup_rc=$?

# Ping can succeed while SFTP fails, and connectivity can disappear after the
# preflight. Retry the same hot snapshot locally before declaring this run lost.
if [[ $backup_rc -ne 0 && $backup_rc -ne 3 && "$BACKUP_REPO" != "$LOCAL_RESTIC_REPO" ]]; then
  log "Remote backup failed rc=$backup_rc — retrying local fallback: $LOCAL_RESTIC_REPO"
  if ensure_repo "$LOCAL_RESTIC_REPO"; then
    BACKUP_REPO="$LOCAL_RESTIC_REPO"
    run_backup "$BACKUP_REPO"
    backup_rc=$?
  else
    log "ERROR: local fallback repo could not be initialized: $LOCAL_RESTIC_REPO"
  fi
fi

cleanup_snapshot

# restic exit codes: 0 = ok, 3 = some source files were unreadable (benign here
# — e.g. a couple of 0600 glab-cli config files; the DB snapshot still made it),
# anything else = a real failure (e.g. rc=1 "no space left on device" on the hub
# repo). Crucially, because we no longer stop kandev, NONE of these can leave the
# service down — kandev ran throughout regardless of the outcome.
if [[ $backup_rc -eq 0 ]]; then
  log "Backup complete"
elif [[ $backup_rc -eq 3 ]]; then
  log "Backup completed WITH WARNINGS (rc=3: some source files unreadable) — continuing to prune."
else
  log "ERROR: restic backup failed rc=$backup_rc (kandev was NOT stopped and is unaffected)."
  exit $backup_rc
fi

# ── Prune old snapshots ───────────────────────────────────────────────────────
log "Pruning old snapshots..."
restic_repo "$BACKUP_REPO" forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 3 \
  --prune \
  --tag kandev >> "$LOG" 2>&1
log "Prune complete"

log "--- backup done ---"
