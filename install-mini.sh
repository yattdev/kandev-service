#!/usr/bin/env bash
# Install sync-from-sfl as a system cron (/etc/cron.d) running as root.
# Idempotent. Must run as root.
#
# Root cron is needed because some paths under ~USER/Code on mini are
# root-owned (docker leftovers) -- a user-cron rsync cannot write into them.
# The script itself uses --chown to keep new files owned by the normal user.
set -euo pipefail

USER_NAME="${USER_NAME:-alassane}"
USER_HOME="${USER_HOME:-/home/$USER_NAME}"
SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/sync-from-sfl.sh"
SCRIPT_DST="/usr/local/sbin/kandev-sync-from-sfl.sh"
CRON_FILE="/etc/cron.d/kandev-sync-from-sfl"
UPDATE_SCRIPT_SRC="$(cd "$(dirname "$0")" && pwd)/update.sh"
UPDATE_SCRIPT_DST="/usr/local/sbin/kandev-update.sh"
UPDATE_CRON_FILE="/etc/cron.d/kandev-update"

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: must run as root (sudo $0)" >&2
  exit 2
fi

install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$USER_HOME/logs"
install -m 755 -o root -g root "$SCRIPT_SRC" "$SCRIPT_DST"

# ── Kandev allowed-roots mountpoint ─────────────────────────────────────────
# ~/Code is nested-bind-mounted at /data/home/Code in the container (see
# docker-compose.yml). Ensure the empty mountpoint dir exists on the host
# inside the /data bind so Docker can apply the nested mount on (re)create.
# We do NOT use a symlink: kandev's repository discovery scanner does not
# follow symlinks, so the workspace must be a real directory in-container.
KANDEV_DATA="$USER_HOME/.local/share/kandev/home"
mkdir -p "$KANDEV_DATA"
if [[ -L "$KANDEV_DATA/Code" ]]; then
  rm -f "$KANDEV_DATA/Code"
  echo "Removed legacy $KANDEV_DATA/Code symlink"
fi
if [[ ! -d "$KANDEV_DATA/Code" ]]; then
  install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$KANDEV_DATA/Code"
  echo "Created $KANDEV_DATA/Code (empty mountpoint for ~/Code bind)"
fi

cat > "$CRON_FILE" <<EOF
# kandev sfl -> mini auto-sync (runs as root; --chown keeps files user-owned)
SHELL=/bin/bash
PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
*/10 * * * * root USER_NAME=$USER_NAME USER_HOME=$USER_HOME $SCRIPT_DST
EOF
chmod 644 "$CRON_FILE"
chown root:root "$CRON_FILE"

# Remove any legacy entry from the user's crontab (from the old user-cron install).
if sudo -u "$USER_NAME" crontab -l 2>/dev/null | grep -qE 'kandev-sync-from-sfl|sync-from-sfl\.sh'; then
  sudo -u "$USER_NAME" bash -c "crontab -l 2>/dev/null | grep -vE 'kandev-sync-from-sfl|sync-from-sfl\.sh' | crontab -"
  echo "Removed legacy user-crontab entry for $USER_NAME."
fi

# Reload cron so the new /etc/cron.d file is picked up immediately.
if command -v systemctl >/dev/null; then
  systemctl reload cron 2>/dev/null || systemctl reload crond 2>/dev/null || true
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

if command -v systemctl >/dev/null; then
  systemctl reload cron 2>/dev/null || systemctl reload crond 2>/dev/null || true
fi

echo "Installed:"
echo "  script: $SCRIPT_DST"
echo "  cron  : $CRON_FILE  (*/10 * * * * as root)"
echo "  update: $UPDATE_SCRIPT_DST  ($UPDATE_CRON_FILE, daily 03:30 as root)"
echo "  log   : $USER_HOME/logs/kandev-sync.log"
echo "  log   : $USER_HOME/logs/kandev-update.log"
echo
cat "$CRON_FILE"
echo
cat "$UPDATE_CRON_FILE"
