#!/usr/bin/env bash
# install-office.sh — idempotent kandev setup for office-desktop
# Run as the normal user (alice):  bash ~/Code/kandev/install-office.sh
# Will prompt for sudo password when needed.
set -euo pipefail

# ── Machine-specific overrides ───────────────────────────────────────────────
# Load real hosts/users/IPs for THIS machine from a gitignored host.env so this
# public repo stays free of private LAN details. See host.env.example. The
# ${VAR:-default} placeholders below are only used when host.env is absent.
_KANDEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[ -f "$_KANDEV_DIR/host.env" ] && . "$_KANDEV_DIR/host.env"

USER_HOME="$HOME"
USER_NAME="$(whoami)"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MINI_HOST="${MINI_HOST:-10.0.0.20}"
MINI_USER="${MINI_USER:-bob}"
RESTIC_REPO="${RESTIC_REPO:-sftp:${MINI_USER}@${MINI_HOST}:restic-repos/kandev-backup}"

echo "[install-office] user=$USER_NAME home=$USER_HOME"

# ── 0. Host identity for Litestream replica path + active-writer lock ───────
# Each satellite host gets its OWN replica subdir on home (never shared —
# sharing one path across multiple writers is what caused the 2026-07-07/08
# data-loss incidents). kandev-start.sh reads this file to pick its path.
HOST_ID="${KANDEV_HOST_ID:-office}"
echo "$HOST_ID" > "$USER_HOME/.kandev-host-id"
echo "[install-office] host-id set to '$HOST_ID' ($USER_HOME/.kandev-host-id)"

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
ExecStart=/bin/bash %h/Code/kandev/kandev-start.sh
ExecStop=/bin/bash %h/Code/kandev/kandev-start.sh --release-lock
ExecStop=/usr/bin/docker compose -p kandev down
ExecReload=/bin/bash %h/Code/kandev/kandev-start.sh --recreate
TimeoutStartSec=180
TimeoutStopSec=60

[Install]
WantedBy=default.target
EOF
echo "[install-office] systemd unit written (ExecStart → kandev-start.sh)"

# ── 2. Reload + enable ──────────────────────────────────────────────────────
systemctl --user daemon-reload
systemctl --user enable kandev
echo "[install-office] kandev.service enabled"

# ── Kandev allowed-roots mountpoint ─────────────────────────────────────────
KANDEV_DATA="$USER_HOME/.local/share/kandev/home"
mkdir -p "$KANDEV_DATA"
if [[ -L "$KANDEV_DATA/Code" ]]; then
    rm -f "$KANDEV_DATA/Code"
    echo "[install-office] removed legacy $KANDEV_DATA/Code symlink"
fi
if [[ ! -d "$KANDEV_DATA/Code" ]]; then
    mkdir -p "$KANDEV_DATA/Code"
    echo "[install-office] created $KANDEV_DATA/Code (mountpoint for ~/Code bind)"
fi

# ── 3. Litestream config ─────────────────────────────────────────────────────
# Detects the SSH key that can reach bob@home-server.
LITESTREAM_CFG_DIR="$USER_HOME/.config/litestream"
LITESTREAM_CFG="$LITESTREAM_CFG_DIR/litestream.yml"
mkdir -p "$LITESTREAM_CFG_DIR"

# Find the SSH key that works for home-server
SSH_KEY=""
for candidate in "$USER_HOME/.ssh/home-key" "$USER_HOME/.ssh/id_ed25519" "$USER_HOME/.ssh/id_rsa" "$USER_HOME/.ssh/id_ed25519"; do
    if [[ -f "$candidate" ]]; then
        if ssh -i "$candidate" -o BatchMode=yes -o ConnectTimeout=3 -o StrictHostKeyChecking=accept-new \
           "${MINI_USER}@${MINI_HOST}" true 2>/dev/null; then
            SSH_KEY="$candidate"
            break
        fi
    fi
done

if [[ -z "$SSH_KEY" ]]; then
    echo "[install-office] WARNING: no SSH key found that reaches ${MINI_USER}@${MINI_HOST}"
    echo "  Add your public key to home-server's authorized_keys:"
    echo "  ssh-copy-id -i ~/.ssh/YOUR_KEY.pub ${MINI_USER}@${MINI_HOST}"
    SSH_KEY="$USER_HOME/.ssh/REPLACE_WITH_KEY"
fi
echo "[install-office] Litestream SSH key: $SSH_KEY"

# Copy SSH key and known_hosts into litestream config dir (world-readable for container)
LITESTREAM_KEY="$USER_HOME/.config/litestream/litestream-key"
LITESTREAM_KNOWN_HOSTS="$USER_HOME/.config/litestream/known_hosts"
if [[ -f "$SSH_KEY" ]]; then
    cp "$SSH_KEY" "$LITESTREAM_KEY"
    chmod 644 "$LITESTREAM_KEY"
fi
ssh-keyscan -t ed25519,ecdsa "$MINI_HOST" 2>/dev/null > "$LITESTREAM_KNOWN_HOSTS" || true
chmod 644 "$LITESTREAM_KNOWN_HOSTS" 2>/dev/null || true

cat > "$LITESTREAM_CFG" <<EOF
dbs:
  - path: /data/kandev.db
    replicas:
      - type: sftp
        host: "${MINI_HOST}"
        user: "${MINI_USER}"
        key-path: /etc/litestream/litestream-key
        known-hosts-path: /etc/litestream/known_hosts
        path: /home/${MINI_USER}/litestream-replicas/kandev/${HOST_ID}
EOF
echo "[install-office] Litestream config written: $LITESTREAM_CFG (replica path: kandev/${HOST_ID} — dedicated, not shared)"

# ── 4. Enable lingering ──────────────────────────────────────────────────────
if ! loginctl show-user "$USER_NAME" 2>/dev/null | grep -q "Linger=yes"; then
    echo "[install-office] enabling linger (requires sudo)..."
    sudo loginctl enable-linger "$USER_NAME"
    echo "[install-office] linger enabled"
else
    echo "[install-office] linger already enabled"
fi

# ── 5. UFW: open 38429 and 80 ────────────────────────────────────────────────
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null || true)
    if ! echo "$UFW_STATUS" | grep -q "38429"; then
        sudo ufw allow 38429/tcp comment "kandev"
        echo "[install-office] ufw: 38429/tcp opened"
    fi
    if ! echo "$UFW_STATUS" | grep -qE ' 80[/ ]'; then
        sudo ufw allow 80/tcp comment "kandev-web"
        echo "[install-office] ufw: 80/tcp opened"
    fi
fi

# ── 6. Port 80 → 38429 redirect ──────────────────────────────────────────────
BEFORE_RULES="/etc/ufw/before.rules"

if ! sudo iptables -t nat -C PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429 2>/dev/null; then
    sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429
    echo "[install-office] iptables: PREROUTING redirect added (80 → 38429)"
fi

if ! sudo iptables -t nat -C OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429 2>/dev/null; then
    sudo iptables -t nat -A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429
    echo "[install-office] iptables: OUTPUT redirect added"
fi

if ! sudo grep -q "OUTPUT.*REDIRECT.*38429\|REDIRECT.*38429.*OUTPUT" "$BEFORE_RULES" 2>/dev/null; then
    sudo sed -i '/^\*filter/i # kandev: port 80 → 38429 (PREROUTING=external, OUTPUT=local)\n*nat\n:PREROUTING ACCEPT [0:0]\n:OUTPUT ACCEPT [0:0]\n-A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429\n-A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429\nCOMMIT\n' "$BEFORE_RULES"
    sudo ufw reload
    echo "[install-office] redirects persisted in before.rules"
fi

# ── 7. Start kandev (with Litestream restore) ─────────────────────────────────
if ! docker ps --filter name=kandev --format '{{.Names}}' | grep -q kandev; then
    echo "[install-office] starting kandev via kandev-start.sh..."
    bash "$SCRIPT_DIR/kandev-start.sh"
else
    echo "[install-office] kandev already running"
fi

# ── 8. Crons ─────────────────────────────────────────────────────────────────
mkdir -p "$USER_HOME/logs"

UPDATE_ENTRY="30 3 * * * bash $USER_HOME/Code/kandev/update.sh >> $USER_HOME/logs/kandev-update.log 2>&1"
if ! crontab -l 2>/dev/null | grep -q "kandev/update.sh"; then
    ( crontab -l 2>/dev/null; echo "$UPDATE_ENTRY" ) | crontab -
    echo "[install-office] cron: daily update added (03:30)"
fi

BACKUP_ENTRY="0 3 * * * RESTIC_REPO=$RESTIC_REPO bash $USER_HOME/Code/kandev/kandev-restic-backup.sh >> $USER_HOME/logs/kandev-backup.log 2>&1"
if ! crontab -l 2>/dev/null | grep -q "kandev-restic-backup.sh"; then
    ( crontab -l 2>/dev/null; echo "$BACKUP_ENTRY" ) | crontab -
    echo "[install-office] cron: daily restic backup added (03:00)"
fi

# Periodic pull: if this host isn't the active writer and a peer is newer,
# pull the freshest data + restart kandev (no-ops otherwise). 06:00/13:00/18:00.
PULL_ENTRY="0 6,13,18 * * * bash $USER_HOME/Code/kandev/kandev-pull.sh >> $USER_HOME/logs/kandev-sync.log 2>&1"
if ! crontab -l 2>/dev/null | grep -q "kandev-pull.sh"; then
    ( crontab -l 2>/dev/null; echo "$PULL_ENTRY" ) | crontab -
    echo "[install-office] cron: periodic pull added (06:00/13:00/18:00)"
fi

echo ""
echo "✅  install-office done"
echo "   systemd:  systemctl --user status kandev"
echo "   direct:   http://localhost:38429"
echo "   web:      http://localhost  (LAN: http://board.office)"
echo "   litestream: replicating kandev.db → ${MINI_USER}@${MINI_HOST}:litestream-replicas/kandev/${HOST_ID}/"
echo "   backup:   daily 03:00 → ~/logs/kandev-backup.log"
echo "   update:   daily 03:30 → ~/logs/kandev-update.log"
if [[ "$SSH_KEY" == *"REPLACE"* ]]; then
    echo ""
    echo "⚠️  ACTION REQUIRED: Set up SSH key to home-server, then re-run this script."
fi
