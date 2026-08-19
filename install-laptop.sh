#!/usr/bin/env bash
# install-laptop.sh — Idempotent kandev setup for laptop.
#
# Sets up a full kandev instance identical to office-desktop:
#   - Systemd user unit (autostart on login/boot via linger)
#   - iptables NAT: port 80 → 38429 (persisted across reboots)
#   - DNS: 127.0.0.1 board.local in /etc/hosts
#   - Litestream: restore from home-server replica on start
#   - Restic: daily backup snapshot to home-server repo
#
# Run as the normal user (carol):  bash ~/Code/kandev/install-laptop.sh
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
SSH_KEY="${SSH_KEY:-$USER_HOME/.ssh/laptop}"
RESTIC_REPO="${RESTIC_REPO:-sftp:${MINI_USER}@${MINI_HOST}:restic-repos/kandev-backup}"

echo "[install-laptop] user=$USER_NAME home=$USER_HOME"

# Persist the worker-only AppArmor policy and load it into the current kernel.
sudo bash "$SCRIPT_DIR/scripts/install-codex-apparmor.sh"

# ── 0. Host identity for Litestream replica path + active-writer lock ───────
# Each satellite host gets its OWN replica subdir on home (never shared —
# sharing one path across multiple writers is what caused the 2026-07-07/08
# data-loss incidents). kandev-start.sh reads this file to pick its path.
HOST_ID="${KANDEV_HOST_ID:-laptop}"
echo "$HOST_ID" > "$USER_HOME/.kandev-host-id"
echo "[install-laptop] host-id set to '$HOST_ID' ($USER_HOME/.kandev-host-id)"

# ── 1. Required directories ──────────────────────────────────────────────────
mkdir -p "$USER_HOME/logs" \
         "$USER_HOME/.local/share/kandev/data" \
         "$USER_HOME/.config/litestream" \
         "$USER_HOME/.config/restic"

KANDEV_DATA="$USER_HOME/.local/share/kandev/home"
mkdir -p "$KANDEV_DATA"
if [[ -L "$KANDEV_DATA/Code" ]]; then
    rm -f "$KANDEV_DATA/Code"
fi
if [[ ! -d "$KANDEV_DATA/Code" ]]; then
    mkdir -p "$KANDEV_DATA/Code"
    echo "[install-laptop] created $KANDEV_DATA/Code (mountpoint for ~/Code bind)"
fi

# ── 2. Litestream config ─────────────────────────────────────────────────────
LITESTREAM_CFG="$USER_HOME/.config/litestream/litestream.yml"

# Verify SSH key reaches home-server
if [[ -f "$SSH_KEY" ]]; then
    if ! ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new \
         "${MINI_USER}@${MINI_HOST}" true 2>/dev/null; then
        echo "[install-laptop] WARNING: $SSH_KEY cannot reach ${MINI_USER}@${MINI_HOST}"
        echo "  Ensure your public key is in home-server's authorized_keys:"
        echo "  ssh-copy-id -i ${SSH_KEY}.pub ${MINI_USER}@${MINI_HOST}"
    else
        echo "[install-laptop] SSH to home-server OK (key: $SSH_KEY)"
        # Ensure public key is in home's authorized_keys (needed for Litestream container)
        PUBKEY_CONTENT=$(ssh-keygen -y -f "$SSH_KEY" 2>/dev/null || cat "${SSH_KEY}.pub" 2>/dev/null || true)
        if [[ -n "$PUBKEY_CONTENT" ]]; then
            if ! ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5 \
                 "${MINI_USER}@${MINI_HOST}" "grep -qF '$(echo $PUBKEY_CONTENT | awk '{print $2}')' ~/.ssh/authorized_keys" 2>/dev/null; then
                ssh -i "$SSH_KEY" -o BatchMode=yes -o ConnectTimeout=5 \
                    "${MINI_USER}@${MINI_HOST}" "echo '$PUBKEY_CONTENT' >> ~/.ssh/authorized_keys"
                echo "[install-laptop] Public key added to home-server authorized_keys"
            else
                echo "[install-laptop] Public key already in home-server authorized_keys"
            fi
        fi
    fi
else
    echo "[install-laptop] WARNING: SSH key not found: $SSH_KEY"
fi

# Copy SSH key and known_hosts into litestream config dir (world-readable for container)
LITESTREAM_KEY="$USER_HOME/.config/litestream/litestream-key"
LITESTREAM_KNOWN_HOSTS="$USER_HOME/.config/litestream/known_hosts"
cp "$SSH_KEY" "$LITESTREAM_KEY" 2>/dev/null || true
chmod 644 "$LITESTREAM_KEY" 2>/dev/null || true
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
echo "[install-laptop] Litestream config written: $LITESTREAM_CFG (replica path: kandev/${HOST_ID} — dedicated, not shared)"

# ── 3. Restic password ───────────────────────────────────────────────────────
RESTIC_PASSWORD_FILE="$USER_HOME/.config/restic/kandev-backup-password"
if [[ ! -f "$RESTIC_PASSWORD_FILE" ]]; then
    echo "[install-laptop] ⚠️  Restic password file missing: $RESTIC_PASSWORD_FILE"
    echo "  Copy it from home-server:"
    echo "  scp ${MINI_USER}@${MINI_HOST}:.config/restic/kandev-backup-password $RESTIC_PASSWORD_FILE"
    echo "  chmod 600 $RESTIC_PASSWORD_FILE"
    echo ""
    echo "  Then re-run this script."
    echo "  (Continuing without restic backup...)"
else
    echo "[install-laptop] Restic password file found: $RESTIC_PASSWORD_FILE"
fi

# ── 4. Systemd user unit ─────────────────────────────────────────────────────
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

systemctl --user daemon-reload
systemctl --user enable kandev
echo "[install-laptop] systemd unit written + enabled"

# ── 5. Enable lingering ───────────────────────────────────────────────────────
if ! loginctl show-user "$USER_NAME" 2>/dev/null | grep -q "Linger=yes"; then
    echo "[install-laptop] enabling linger (requires sudo)..."
    sudo loginctl enable-linger "$USER_NAME"
    echo "[install-laptop] linger enabled"
else
    echo "[install-laptop] linger already enabled"
fi

# ── 6. UFW: open ports ───────────────────────────────────────────────────────
if command -v ufw &>/dev/null; then
    UFW_STATUS=$(sudo ufw status 2>/dev/null || true)
    if ! echo "$UFW_STATUS" | grep -q "38429"; then
        sudo ufw allow 38429/tcp comment "kandev"
        echo "[install-laptop] ufw: 38429/tcp opened"
    fi
    if ! echo "$UFW_STATUS" | grep -qE ' 80[/ ]'; then
        sudo ufw allow 80/tcp comment "kandev-web"
        echo "[install-laptop] ufw: 80/tcp opened"
    fi
fi

# ── 7. Port 80 → 38429 NAT redirect ──────────────────────────────────────────
# PREROUTING: external traffic (other LAN devices)
# OUTPUT:     localhost traffic (browser on laptop itself → board.local)

if ! sudo iptables -t nat -C PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429 2>/dev/null; then
    sudo iptables -t nat -A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429
    echo "[install-laptop] iptables: PREROUTING redirect added (80 → 38429)"
fi

# IMPORTANT: scope to -d 127.0.0.1/32 only. An unscoped OUTPUT rule matches
# ANY destination on port 80 (board.office, board.home, even unrelated websites),
# silently redirecting them all to this host's own local kandev instead of the
# real remote host. This caused board.office/board.home to appear to load but
# show local/stale data when browsed from laptop.
if ! sudo iptables -t nat -C OUTPUT -d 127.0.0.1/32 -p tcp --dport 80 -j REDIRECT --to-port 38429 2>/dev/null; then
    sudo iptables -t nat -A OUTPUT -d 127.0.0.1/32 -p tcp --dport 80 -j REDIRECT --to-port 38429
    echo "[install-laptop] iptables: OUTPUT redirect added (80 → 38429, scoped to 127.0.0.1 only)"
fi

# Remove any pre-existing unscoped OUTPUT rule from a previous (buggy) run
if sudo iptables -t nat -C OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429 2>/dev/null; then
    sudo iptables -t nat -D OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429
    echo "[install-laptop] iptables: removed unscoped OUTPUT redirect (security/correctness fix)"
fi

# Persist: prefer UFW before.rules if present, else iptables-persistent
BEFORE_RULES="/etc/ufw/before.rules"
IPTABLES_RULES="/etc/iptables/rules.v4"

if [[ -f "$BEFORE_RULES" ]]; then
    # Remove any previously-persisted unscoped OUTPUT rule (buggy — matches all destinations)
    if sudo grep -q '^-A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429$' "$BEFORE_RULES" 2>/dev/null; then
        sudo sed -i '/^-A OUTPUT -p tcp --dport 80 -j REDIRECT --to-port 38429$/d' "$BEFORE_RULES"
        echo "[install-laptop] removed unscoped OUTPUT redirect from before.rules"
    fi
    if ! sudo grep -q "REDIRECT.*38429" "$BEFORE_RULES" 2>/dev/null; then
        sudo sed -i '/^\*filter/i # kandev: port 80 → 38429\n*nat\n:PREROUTING ACCEPT [0:0]\n:OUTPUT ACCEPT [0:0]\n-A PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 38429\n-A OUTPUT -d 127.0.0.1/32 -p tcp --dport 80 -j REDIRECT --to-port 38429\nCOMMIT\n' "$BEFORE_RULES"
        sudo ufw reload
        echo "[install-laptop] redirects persisted in ufw/before.rules"
    fi
elif command -v iptables-save &>/dev/null; then
    sudo iptables-save | sudo tee "$IPTABLES_RULES" > /dev/null
    echo "[install-laptop] redirects persisted via iptables-save"
fi

# ── 8. DNS: board.local → localhost ──────────────────────────────────────────
if ! grep -q "board.local" /etc/hosts 2>/dev/null; then
    echo "127.0.0.1 board.local" | sudo tee -a /etc/hosts > /dev/null
    echo "[install-laptop] Added 127.0.0.1 board.local to /etc/hosts"
else
    echo "[install-laptop] board.local already in /etc/hosts"
fi

# ── 9. Initial restore + start ───────────────────────────────────────────────
echo "[install-laptop] Starting kandev (restoring from home-server replica)..."
bash "$SCRIPT_DIR/kandev-start.sh"

# ── 10. Crons ────────────────────────────────────────────────────────────────
UPDATE_ENTRY="30 3 * * * bash $USER_HOME/Code/kandev/update.sh >> $USER_HOME/logs/kandev-update.log 2>&1"
if ! crontab -l 2>/dev/null | grep -q "kandev/update.sh"; then
    ( crontab -l 2>/dev/null; echo "$UPDATE_ENTRY" ) | crontab -
    echo "[install-laptop] cron: daily update added (03:30)"
fi

if [[ -f "$RESTIC_PASSWORD_FILE" ]]; then
    BACKUP_ENTRY="0 3 * * * RESTIC_REPO=$RESTIC_REPO bash $USER_HOME/Code/kandev/kandev-restic-backup.sh >> $USER_HOME/logs/kandev-backup.log 2>&1"
    if ! crontab -l 2>/dev/null | grep -q "kandev-restic-backup.sh"; then
        ( crontab -l 2>/dev/null; echo "$BACKUP_ENTRY" ) | crontab -
        echo "[install-laptop] cron: daily restic backup added (03:00)"
    fi
fi

# Periodic pull: if this host isn't the active writer and a peer is newer,
# pull the freshest data + restart kandev (no-ops otherwise). 06:00/13:00/18:00.
PULL_ENTRY="0 6,13,18 * * * bash $USER_HOME/Code/kandev/kandev-pull.sh >> $USER_HOME/logs/kandev-sync.log 2>&1"
if ! crontab -l 2>/dev/null | grep -q "kandev-pull.sh"; then
    ( crontab -l 2>/dev/null; echo "$PULL_ENTRY" ) | crontab -
    echo "[install-laptop] cron: periodic pull added (06:00/13:00/18:00)"
fi

echo ""
echo "✅  install-laptop done"
echo "   direct:    http://localhost:38429"
echo "   web:       http://board.local  (127.0.0.1 via /etc/hosts)"
echo "   systemd:   systemctl --user status kandev"
echo "   litestream: replicating kandev.db → ${MINI_USER}@${MINI_HOST}:litestream-replicas/kandev/${HOST_ID}/"
echo "   backup:    daily 03:00 → ~/logs/kandev-backup.log"
echo "   update:    daily 03:30 → ~/logs/kandev-update.log"
