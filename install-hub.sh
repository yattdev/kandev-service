#!/usr/bin/env bash
# install-hub.sh — Idempotent kandev setup for home-server (hub role).
#
# home-server is the central hub:
#   - Stores Litestream SFTP replica (~/litestream-replicas/kandev/)
#   - Stores restic snapshot repo (~/restic-repos/kandev-backup)
#   - Does NOT run Litestream itself (satellites replicate TO home)
#
# Must run as root: sudo bash ~/Code/kandev/install-hub.sh
set -euo pipefail

# ── Machine-specific overrides ───────────────────────────────────────────────
# Load real hosts/users/IPs for THIS machine from a gitignored host.env so this
# public repo stays free of private LAN details. See host.env.example. The
# ${VAR:-default} placeholders below are only used when host.env is absent.
_KANDEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[ -f "$_KANDEV_DIR/host.env" ] && . "$_KANDEV_DIR/host.env"

USER_NAME="${USER_NAME:-bob}"
USER_HOME="${USER_HOME:-/home/$USER_NAME}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UPDATE_SCRIPT_SRC="$SCRIPT_DIR/update.sh"
UPDATE_SCRIPT_DST="/usr/local/sbin/kandev-update.sh"
UPDATE_CRON_FILE="/etc/cron.d/kandev-update"
BACKUP_SCRIPT_SRC="$SCRIPT_DIR/kandev-restic-backup.sh"
BACKUP_SCRIPT_DST="/usr/local/sbin/kandev-restic-backup.sh"
BACKUP_CRON_FILE="/etc/cron.d/kandev-backup"
RESTIC="${RESTIC:-$USER_HOME/bin/restic}"
RESTIC_REPO="${RESTIC_REPO:-sftp:localhost:restic-repos/kandev-backup}"
RESTIC_PASSWORD_FILE="${RESTIC_PASSWORD_FILE:-$USER_HOME/.config/restic/kandev-backup-password}"

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: must run as root (sudo $0)" >&2
  exit 2
fi

install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$USER_HOME/logs"

# ── Systemd user unit (ExecStart → kandev-start-hub.sh) ────────────────────
SYSTEMD_DIR="$USER_HOME/.config/systemd/user"
install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$SYSTEMD_DIR"

cat > "$SYSTEMD_DIR/kandev.service" <<'EOF'
[Unit]
Description=Kandev — autonomous agent kanban platform (home-server hub)
After=default.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=%h/Code/kandev
ExecStart=/bin/bash %h/Code/kandev/kandev-start-hub.sh
ExecStop=/usr/bin/docker compose -p kandev down
ExecReload=/bin/bash %h/Code/kandev/kandev-start-hub.sh --recreate
TimeoutStartSec=180
TimeoutStopSec=60

[Install]
WantedBy=default.target
EOF
chown "$USER_NAME:$USER_NAME" "$SYSTEMD_DIR/kandev.service"
echo "Systemd unit written (ExecStart → kandev-start-hub.sh)"

# Reload systemd for the user
sudo -u "$USER_NAME" XDG_RUNTIME_DIR="/run/user/$(id -u "$USER_NAME")" \
  systemctl --user daemon-reload 2>/dev/null || true
sudo -u "$USER_NAME" XDG_RUNTIME_DIR="/run/user/$(id -u "$USER_NAME")" \
  systemctl --user enable kandev 2>/dev/null || true
echo "kandev.service enabled"

# ── Kandev allowed-roots mountpoint ─────────────────────────────────────────
KANDEV_DATA="$USER_HOME/.local/share/kandev/home"
mkdir -p "$KANDEV_DATA"
if [[ -L "$KANDEV_DATA/Code" ]]; then
  rm -f "$KANDEV_DATA/Code"
  echo "Removed legacy $KANDEV_DATA/Code symlink"
fi
if [[ ! -d "$KANDEV_DATA/Code" ]]; then
  install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$KANDEV_DATA/Code"
  echo "Created $KANDEV_DATA/Code (mountpoint for ~/Code bind)"
fi

# ── Litestream replica dir (hub storage) ────────────────────────────────────
# Each satellite host pushes to its OWN dedicated subdir (office/, carol/) —
# never a shared path. This is required for safe single-leader replication:
# see kandev-start.sh / kandev-start-hub.sh for the active-writer lock and
# freshest-replica restore logic that depend on this per-host layout.
REPLICA_DIR="$USER_HOME/litestream-replicas/kandev"
if [[ ! -d "$REPLICA_DIR" ]]; then
  install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$REPLICA_DIR"
  echo "Created Litestream replica dir: $REPLICA_DIR"
else
  echo "Litestream replica dir already exists: $REPLICA_DIR"
fi
for host_id in office carol; do
  install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$REPLICA_DIR/$host_id"
done
echo "Per-host replica subdirs ready: $REPLICA_DIR/{office,carol}"

# ── Restic backup repo ────────────────────────────────────────────────────────
RESTIC_REPO_DIR="$USER_HOME/restic-repos"
install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$RESTIC_REPO_DIR"

# Generate password file if missing
if [[ ! -f "$RESTIC_PASSWORD_FILE" ]]; then
  install -d -o "$USER_NAME" -g "$USER_NAME" -m 700 "$(dirname "$RESTIC_PASSWORD_FILE")"
  # Generate a random 32-char password
  openssl rand -base64 24 | tr -d '\n' > "$RESTIC_PASSWORD_FILE"
  chown "$USER_NAME:$USER_NAME" "$RESTIC_PASSWORD_FILE"
  chmod 600 "$RESTIC_PASSWORD_FILE"
  echo "Generated restic password: $RESTIC_PASSWORD_FILE"
  echo "⚠️  IMPORTANT: copy this password to office-desktop and laptop:"
  echo "   cat $RESTIC_PASSWORD_FILE"
else
  echo "Restic password file already exists: $RESTIC_PASSWORD_FILE"
fi

# Init restic repo if not yet initialized
if ! sudo -u "$USER_NAME" RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" \
     "$RESTIC" -r "$RESTIC_REPO" snapshots --no-lock >/dev/null 2>&1; then
  echo "Initializing restic repo: $RESTIC_REPO"
  sudo -u "$USER_NAME" RESTIC_PASSWORD_FILE="$RESTIC_PASSWORD_FILE" \
    "$RESTIC" -r "$RESTIC_REPO" init
  echo "Restic repo initialized"
else
  echo "Restic repo already initialized: $RESTIC_REPO"
fi

# ── Remove legacy sync-from-office cron ────────────────────────────────────────
if [[ -f /etc/cron.d/kandev-sync-from-office ]]; then
  rm -f /etc/cron.d/kandev-sync-from-office
  echo "Removed legacy cron: /etc/cron.d/kandev-sync-from-office"
fi

# ── Auto-update cron (daily 03:30) ───────────────────────────────────────────
install -m 755 -o root -g root "$UPDATE_SCRIPT_SRC" "$UPDATE_SCRIPT_DST"

cat > "$UPDATE_CRON_FILE" <<EOF
# kandev daily image update — pulls latest, restarts only if image changed
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
30 3 * * * root USER_NAME=$USER_NAME USER_HOME=$USER_HOME $UPDATE_SCRIPT_DST
EOF
chmod 644 "$UPDATE_CRON_FILE"
chown root:root "$UPDATE_CRON_FILE"
echo "Installed update cron: $UPDATE_CRON_FILE (daily 03:30)"

# ── Restic backup cron (daily 03:00) ─────────────────────────────────────────
install -m 755 -o root -g root "$BACKUP_SCRIPT_SRC" "$BACKUP_SCRIPT_DST"

cat > "$BACKUP_CRON_FILE" <<EOF
# kandev daily restic backup — snapshot history for kandev data
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
# MINI_HOST=127.0.0.1: on the hub the "hub" reachability preflight is just localhost
# (the static /usr/local/sbin copy of the backup script can't read the repo's host.env).
0 3 * * * root USER_NAME=$USER_NAME USER_HOME=$USER_HOME MINI_HOST=127.0.0.1 RESTIC=$RESTIC RESTIC_REPO=$RESTIC_REPO RESTIC_PASSWORD_FILE=$RESTIC_PASSWORD_FILE $BACKUP_SCRIPT_DST
EOF
chmod 644 "$BACKUP_CRON_FILE"
chown root:root "$BACKUP_CRON_FILE"
echo "Installed backup cron: $BACKUP_CRON_FILE (daily 03:00)"

# Reload cron
if command -v systemctl >/dev/null; then
  systemctl reload cron 2>/dev/null || systemctl reload crond 2>/dev/null || true
fi

# ── Immediate: upgrade kandev image (v0.65.0 → latest) ─────────────────────
echo ""
echo "Upgrading kandev image (currently stale — running update now)..."
USER_NAME="$USER_NAME" USER_HOME="$USER_HOME" bash "$UPDATE_SCRIPT_DST"

echo ""
echo "✅  install-home done"
echo "   litestream hub : $REPLICA_DIR"
echo "   restic repo    : $RESTIC_REPO"
echo "   restic password: $RESTIC_PASSWORD_FILE"
echo "   update cron    : daily 03:30 → $USER_HOME/logs/kandev-update.log"
echo "   backup cron    : daily 03:00 → $USER_HOME/logs/kandev-backup.log"
echo ""
echo "Next steps:"
echo "  1. Copy restic password to office-desktop + laptop:"
echo "     cat $RESTIC_PASSWORD_FILE"
echo "  2. Run install-office.sh on office-desktop"
echo "  3. Run install-laptop.sh on laptop"
