#!/usr/bin/env bash
# install-sfl.sh — idempotent kandev setup for sfl-desktop
# Run as the normal user (ayattara):  bash ~/Code/kandev/install-sfl.sh
# Will prompt for sudo password when needed.
set -euo pipefail

USER_HOME="$HOME"
USER_NAME="$(whoami)"

echo "[install-sfl] user=$USER_NAME home=$USER_HOME"

# ── 1. Systemd user unit ────────────────────────────────────────────────────
SYSTEMD_DIR="$USER_HOME/.config/systemd/user"
mkdir -p "$SYSTEMD_DIR"

cat > "$SYSTEMD_DIR/kandev.service" <<'EOF'
[Unit]
Description=Kandev — autonomous agent kanban platform
After=default.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=%h/Code/kandev
ExecStart=/usr/bin/docker compose -p kandev up -d --remove-orphans
ExecStop=/usr/bin/docker compose -p kandev down
ExecReload=/usr/bin/docker compose -p kandev up -d --remove-orphans
TimeoutStartSec=120
TimeoutStopSec=60

[Install]
WantedBy=default.target
EOF
echo "[install-sfl] systemd unit written"

# ── 2. Reload + enable ──────────────────────────────────────────────────────
systemctl --user daemon-reload
systemctl --user enable kandev
echo "[install-sfl] kandev.service enabled"

# ── Kandev allowed-roots mountpoint ─────────────────────────────────────────
# ~/Code is nested-bind-mounted at /data/home/Code in the container. Ensure
# the empty mountpoint dir exists on the host so Docker can apply the nested
# mount on (re)create. Symlinks don't work: kandev discovery doesn't follow them.
KANDEV_DATA="$USER_HOME/.local/share/kandev/home"
mkdir -p "$KANDEV_DATA"
if [[ -L "$KANDEV_DATA/Code" ]]; then
    rm -f "$KANDEV_DATA/Code"
    echo "[install-sfl] removed legacy $KANDEV_DATA/Code symlink"
fi
if [[ ! -d "$KANDEV_DATA/Code" ]]; then
    mkdir -p "$KANDEV_DATA/Code"
    echo "[install-sfl] created $KANDEV_DATA/Code (mountpoint for ~/Code bind)"
fi

# ── 3. Enable lingering (so user services survive logout / start on boot) ──
if ! loginctl show-user "$USER_NAME" 2>/dev/null | grep -q "Linger=yes"; then
    echo "[install-sfl] enabling linger (requires sudo)..."
    sudo loginctl enable-linger "$USER_NAME"
    echo "[install-sfl] linger enabled"
else
    echo "[install-sfl] linger already enabled"
fi

# ── 4. UFW: open 38429 (direct) and 80 (web shortcut) ──────────────────────
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null || true)

    if ! echo "$UFW_STATUS" | grep -q "38429"; then
        sudo ufw allow 38429/tcp comment "kandev"
        echo "[install-sfl] ufw: 38429/tcp opened"
    else
        echo "[install-sfl] ufw: 38429 already open"
    fi

    if ! echo "$UFW_STATUS" | grep -qE ' 80[/ ]'; then
        sudo ufw allow 80/tcp comment "kandev-web"
        echo "[install-sfl] ufw: 80/tcp opened"
    else
        echo "[install-sfl] ufw: 80 already open"
    fi
fi

# ── 5. Port 80 → 38429 redirect (now + persisted in /etc/ufw/before.rules) ─
# PREROUTING: handles traffic from external hosts (LAN, yattara-pc, etc.)
# OUTPUT:     handles traffic from sfl-desktop itself (localhost → board.sfl)
BEFORE_RULES="/etc/ufw/before.rules"

if ! sudo iptables -t nat -C PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429 2>/dev/null; then
    sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429
    echo "[install-sfl] iptables: PREROUTING redirect added (80 → 38429)"
else
    echo "[install-sfl] iptables: PREROUTING redirect already active"
fi

if ! sudo iptables -t nat -C OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429 2>/dev/null; then
    sudo iptables -t nat -A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429
    echo "[install-sfl] iptables: OUTPUT redirect added (80 → 38429, enables local access)"
else
    echo "[install-sfl] iptables: OUTPUT redirect already active"
fi

if ! sudo grep -q "OUTPUT.*REDIRECT.*38429\|REDIRECT.*38429.*OUTPUT" "$BEFORE_RULES" 2>/dev/null; then
    sudo sed -i '/^\*filter/i # kandev: port 80 → 38429 (PREROUTING=external, OUTPUT=local)\n*nat\n:PREROUTING ACCEPT [0:0]\n:OUTPUT ACCEPT [0:0]\n-A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429\n-A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429\nCOMMIT\n' "$BEFORE_RULES"
    sudo ufw reload
    echo "[install-sfl] redirects persisted in before.rules"
else
    echo "[install-sfl] redirects already persisted"
fi

# ── 6. Start kandev if not running ──────────────────────────────────────────
if ! docker ps --filter name=kandev --format '{{.Names}}' | grep -q kandev; then
    echo "[install-sfl] starting kandev..."
    cd "$USER_HOME/Code/kandev" && docker compose -p kandev up -d --remove-orphans
else
    echo "[install-sfl] kandev already running"
fi

# ── 7. Auto-update cron (daily 03:30, user crontab) ─────────────────────────
UPDATE_SCRIPT="$USER_HOME/Code/kandev/update.sh"
CRON_ENTRY="30 3 * * * bash $UPDATE_SCRIPT >> $USER_HOME/logs/kandev-update.log 2>&1"

if ! crontab -l 2>/dev/null | grep -q "kandev/update.sh"; then
    ( crontab -l 2>/dev/null; echo "$CRON_ENTRY" ) | crontab -
    echo "[install-sfl] cron: daily update added (03:30)"
else
    echo "[install-sfl] cron: daily update already present"
fi

echo ""
echo "✅  install-sfl done"
echo "   systemd:  systemctl --user status kandev"
echo "   direct:   http://localhost:38429"
echo "   web:      http://localhost  (LAN: http://board.sfl)"
echo "   update:   runs daily at 03:30 → ~/logs/kandev-update.log"
