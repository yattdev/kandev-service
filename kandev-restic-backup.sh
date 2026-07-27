#!/usr/bin/env bash
# kandev-restic-backup.sh — Daily restic snapshot of kandev data.
#
# Creates a named, deduplicated snapshot in mini-desktop's restic repo.
# Snapshots are browsable with `restic snapshots` — like `git log` for your data.
# Retention: 7 daily + 4 weekly + 3 monthly (pruned automatically).
#
# Repo location (on mini-desktop): ~/restic-repos/kandev-backup
# Password file: ~/.config/restic/kandev-backup-password (same on all hosts)
#
# Usage:
#   bash ~/Code/kandev/kandev-restic-backup.sh
#
# Cron (all hosts, 01:30 daily):
#   30 1 * * * bash ~/Code/kandev/kandev-restic-backup.sh >> ~/logs/kandev-backup.log 2>&1
#
# On mini-desktop the cron runs as root via /etc/cron.d/kandev-backup;
# on sfl-desktop and yattara-pc it runs as the normal user via crontab.
set -euo pipefail

USER_HOME="${USER_HOME:-$HOME}"
USER_NAME="${USER_NAME:-$(whoami)}"
MINI_HOST="${MINI_HOST:-10.0.0.182}"
MINI_USER="${MINI_USER:-alassane}"
RESTIC="${RESTIC:-$(command -v restic 2>/dev/null || echo "$USER_HOME/bin/restic")}"
RESTIC_REPO="${RESTIC_REPO:-sftp:${MINI_USER}@${MINI_HOST}:restic-repos/kandev-backup}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-$USER_HOME/.config/restic/kandev-backup-password}"
KANDEV_DATA="${KANDEV_DATA:-$USER_HOME/.local/share/kandev}"
COMPOSE_DIR="${COMPOSE_DIR:-$USER_HOME/Code/kandev}"
LOG="${LOG:-$USER_HOME/logs/kandev-backup.log}"
LOCK="/run/lock/kandev-restic-backup.lock"

mkdir -p "$(dirname "$LOG")"

log() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

exec 9>"$LOCK"
if ! flock -n 9; then
  log "Another backup is running, skipping"
  exit 0
fi

log "--- kandev restic backup start (host: $(hostname)) ---"

# ── Preflight: mini-desktop reachable? ──────────────────────────────────────
if ! ping -c1 -W3 "$MINI_HOST" >/dev/null 2>&1; then
  log "mini-desktop ($MINI_HOST) unreachable — skipping backup"
  exit 0
fi

# ── Init repo if first run ───────────────────────────────────────────────────
if ! RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" "$RESTIC" -r "$RESTIC_REPO" snapshots \
     --no-lock >/dev/null 2>&1; then
  log "Repo not found or not initialized — running restic init"
  RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" "$RESTIC" -r "$RESTIC_REPO" init
  log "Repo initialized: $RESTIC_REPO"
fi

# ── Stop kandev briefly for a consistent SQLite snapshot ────────────────────
KANDEV_WAS_RUNNING=false
if docker ps --filter name=kandev --filter status=running --format '{{.Names}}' \
   | grep -q '^kandev$'; then
  KANDEV_WAS_RUNNING=true
  log "Stopping kandev for consistent snapshot..."
  cd "$COMPOSE_DIR"
  docker compose -p kandev stop kandev
fi

# ── Backup ───────────────────────────────────────────────────────────────────
log "Running restic backup: $KANDEV_DATA → $RESTIC_REPO"
RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" "$RESTIC" -r "$RESTIC_REPO" backup \
  --tag "kandev" \
  --tag "$(hostname)" \
  --hostname "$(hostname)" \
  "$KANDEV_DATA" >> "$LOG" 2>&1
backup_rc=$?

# ── Restart kandev ───────────────────────────────────────────────────────────
if $KANDEV_WAS_RUNNING; then
  log "Restarting kandev..."
  cd "$COMPOSE_DIR"
  docker compose -p kandev start kandev
fi

if [[ $backup_rc -ne 0 ]]; then
  log "ERROR: restic backup exited rc=$backup_rc"
  exit $backup_rc
fi
log "Backup complete"

# ── Prune old snapshots ───────────────────────────────────────────────────────
log "Pruning old snapshots..."
RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" "$RESTIC" -r "$RESTIC_REPO" forget \
  --keep-daily 7 \
  --keep-weekly 4 \
  --keep-monthly 3 \
  --prune \
  --tag kandev >> "$LOG" 2>&1
log "Prune complete"

log "--- backup done ---"
