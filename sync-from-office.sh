#!/usr/bin/env bash
# DEPRECATED — replaced by Litestream live replication (kandev-start.sh).
#
# This script used to rsync office-desktop → home-server every 10 minutes via cron.
# The cron (/etc/cron.d/kandev-sync-from-office) has been removed by install-hub.sh.
#
# Current sync: Litestream replicates kandev.db WAL changes in real-time (seconds lag)
# to ~/litestream-replicas/kandev/ on home-server. On startup, kandev-start.sh
# restores from this replica automatically.
#
# This file is kept as a reference / emergency manual fallback only.
# To use as emergency fallback (no Litestream):
#   sudo bash ~/Code/kandev/sync-from-office.sh

set -uo pipefail

# ── Machine-specific overrides ───────────────────────────────────────────────
# Load real hosts/users/IPs for THIS machine from a gitignored host.env so this
# public repo stays free of private LAN details. See host.env.example. The
# ${VAR:-default} placeholders below are only used when host.env is absent.
_KANDEV_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
[ -f "$_KANDEV_DIR/host.env" ] && . "$_KANDEV_DIR/host.env"

USER_NAME="${USER_NAME:-bob}"
USER_HOME="${USER_HOME:-/home/$USER_NAME}"
OFFICE_HOST="${OFFICE_HOST:-office-desktop}"
OFFICE_USER="${OFFICE_USER:-alice}"
OFFICE_PING_IP="${OFFICE_PING_IP:-192.168.1.10}"
SSH_KEY="${SSH_KEY:-$USER_HOME/.ssh/home-key}"
CODE_DIR="${CODE_DIR:-$USER_HOME/Code}"
KANDEV_DIR="${KANDEV_DIR:-$USER_HOME/.local/share/kandev}"
LOG="${LOG:-$USER_HOME/logs/kandev-sync.log}"
LOCK="/run/lock/kandev-sync-from-office.lock"

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: must run as root (use the /etc/cron.d/kandev-sync-from-office entry)" >&2
  exit 2
fi

install -d -o "$USER_NAME" -g "$USER_NAME" -m 755 "$(dirname "$LOG")" "$CODE_DIR" "$KANDEV_DIR"
[[ -f "$LOG" ]] || install -o "$USER_NAME" -g "$USER_NAME" -m 644 /dev/null "$LOG"

exec 9>"$LOCK"
if ! flock -n 9; then
  echo "[$(date -Iseconds)] previous sync still running, skipping" >> "$LOG"
  exit 0
fi

log() { echo "[$(date -Iseconds)] $*" >> "$LOG"; }

if ! ping -c1 -W3 "$OFFICE_PING_IP" >/dev/null 2>&1; then
  log "office-desktop unreachable (VPN down?), skipping"
  exit 0
fi

SSH_CMD="ssh -F $USER_HOME/.ssh/config -i $SSH_KEY -o User=$OFFICE_USER -o ConnectTimeout=5 -o BatchMode=yes -o StrictHostKeyChecking=accept-new"

if ! $SSH_CMD "$OFFICE_HOST" true 2>>"$LOG"; then
  log "ssh to $OFFICE_USER@$OFFICE_HOST failed, skipping"
  exit 0
fi

log "sync start (as root, ssh as $OFFICE_USER, --chown=$USER_NAME:$USER_NAME)"

# Pre-flight diagnostic: surface paths under CODE_DIR not owned by USER_NAME.
# We DO NOT auto-chown -- those files were created by other processes (e.g.
# docker), silently changing ownership could break them. The user decides.
offenders="$(find "$CODE_DIR" -maxdepth 4 -not -user "$USER_NAME" -printf '%u:%g %p\n' 2>/dev/null | head -50)"
if [[ -n "$offenders" ]]; then
  log "non-user-owned paths under $CODE_DIR (top 50, not auto-fixed):"
  echo "$offenders" >> "$LOG"
fi

RSYNC_EXCLUDES=(
  # ── home-server infra service dirs (systemd-managed, not workspace projects) ──
  --exclude '/kandev' --exclude '/vpn' --exclude '/reverse-proxy'
  --exclude '/nextcloud-data' --exclude '/nanoclaw' --exclude '/vaultwarden'
  --exclude '/agent-os' --exclude '/onecli' --exclude '/vibe-kanban'

  # ── git internals ──
  --exclude '.git/objects/pack/tmp_*'

  # ── installed dependencies (each host runs its own install) ──
  --exclude 'node_modules'        # JS/TS (npm, yarn, pnpm)
  --exclude 'vendor'              # PHP Composer, Ruby Bundler, Go vendor
  --exclude '.venv' --exclude 'venv' --exclude 'env'  # Python virtualenvs
  --exclude '.bundle'             # Ruby bundler

  # ── build outputs / compiled artefacts ──
  --exclude 'dist' --exclude 'build' --exclude 'out' --exclude '.output'
  --exclude 'target'              # Rust / Java Maven / Gradle
  --exclude '.next' --exclude '.nuxt' --exclude '.svelte-kit'
  --exclude 'public/build'        # Laravel Mix / Vite
  --exclude '_site'               # Jekyll / static site generators
  --exclude '.turbo'              # Turborepo build cache
  --exclude '.parcel-cache'       # Parcel bundler

  # ── language / tool cache dirs ──
  --exclude '__pycache__' --exclude '*.pyc' --exclude '*.pyo'
  --exclude '.pytest_cache' --exclude '.mypy_cache' --exclude '.ruff_cache'
  --exclude '.phpunit.cache' --exclude '.php-cs-fixer.cache'
  --exclude '.npm' --exclude '.pnpm-store' --exclude '.yarn/cache'
  --exclude '.gradle'             # Gradle build cache
  --exclude '.sass-cache'         # Sass / SCSS

  # ── test coverage reports ──
  --exclude 'coverage' --exclude '.coverage' --exclude 'htmlcov'

  # ── OS / editor noise ──
  --exclude '.DS_Store' --exclude 'Thumbs.db'
)

# Code: mirror office -> home.
rsync -az --delete \
  -e "$SSH_CMD" \
  --chown="$USER_NAME:$USER_NAME" \
  "${RSYNC_EXCLUDES[@]}" \
  "$OFFICE_HOST:Code/" "$CODE_DIR/" >> "$LOG" 2>&1
code_rc=$?

# Kandev data (sqlite, sessions) - no --delete to avoid wiping local kandev state.
rsync -az \
  -e "$SSH_CMD" \
  --chown="$USER_NAME:$USER_NAME" \
  "$OFFICE_HOST:.local/share/kandev/" "$KANDEV_DIR/" >> "$LOG" 2>&1
kd_rc=$?

log "sync done (code rsync rc=$code_rc, kandev rsync rc=$kd_rc)"
