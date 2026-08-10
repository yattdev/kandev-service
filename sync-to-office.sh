#!/usr/bin/env bash
# DEPRECATED — replaced by Litestream live replication.
#
# This script used to manually push home-server → office-desktop before switching
# to the office. It is no longer needed because Litestream continuously replicates
# kandev.db from any active host to home-server. On startup, kandev-start.sh
# restores the latest state automatically — no manual push required.
#
# The sync workflow is now:
#   1. Work on any host → Litestream replicates DB to home-server in seconds
#   2. Switch to another host → kandev-start.sh restores from home on startup
#   3. Continue working with up-to-date data
#
# This file is kept as a reference / emergency manual fallback only.
# To push kandev data manually (emergency, no Litestream):
#   sudo bash ~/Code/kandev/sync-to-office.sh

set -euo pipefail

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

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: must run as root (sudo $0)" >&2
  exit 2
fi

if ! ping -c1 -W3 "$OFFICE_PING_IP" >/dev/null 2>&1; then
  echo "ERROR: office-desktop ($OFFICE_PING_IP) unreachable. Is Corp VPN up?" >&2
  echo "  sudo nmcli connection up 'Corp VPN'" >&2
  exit 1
fi

SSH_CMD="ssh -F $USER_HOME/.ssh/config -i $SSH_KEY -o User=$OFFICE_USER -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new"

echo "About to push (as root, ssh as $OFFICE_USER, --chown=$OFFICE_USER:$OFFICE_USER on dest):"
echo "  $CODE_DIR/        -> $OFFICE_HOST:Code/                        (with --delete)"
echo "  $KANDEV_DIR/      -> $OFFICE_HOST:.local/share/kandev/         (no --delete)"
read -r -p "Continue? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "aborted"; exit 1; }

echo ">> stopping kandev on office-desktop (avoid sqlite write during sync)..."
$SSH_CMD "$OFFICE_HOST" "cd ~/Code/kandev 2>/dev/null && docker compose stop kandev 2>/dev/null || docker stop kandev 2>/dev/null || true"

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

echo ">> rsync Code/ ..."
rsync -avz --delete \
  -e "$SSH_CMD" \
  --chown="$OFFICE_USER:$OFFICE_USER" \
  "${RSYNC_EXCLUDES[@]}" \
  "$CODE_DIR/" "$OFFICE_HOST:Code/"

echo ">> rsync kandev data ..."
rsync -avz \
  -e "$SSH_CMD" \
  --chown="$OFFICE_USER:$OFFICE_USER" \
  "$KANDEV_DIR/" "$OFFICE_HOST:.local/share/kandev/"

echo ">> restarting kandev on office-desktop ..."
$SSH_CMD "$OFFICE_HOST" "cd ~/Code/kandev 2>/dev/null && docker compose up -d kandev 2>/dev/null || docker start kandev 2>/dev/null || true"

echo "Done. office-desktop is now in sync with home-server."
