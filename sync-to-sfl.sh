#!/usr/bin/env bash
# Manual push mini-desktop -> sfl-desktop. Run BEFORE working on sfl-desktop.
# Requires SFL VPN up. Must run as root (same reasoning as sync-from-sfl.sh:
# some paths under ~/Code on mini are root-owned, root reader is needed).
# Destination files land owned by SFL_USER on sfl via --chown.
set -euo pipefail

USER_NAME="${USER_NAME:-alassane}"
USER_HOME="${USER_HOME:-/home/$USER_NAME}"
SFL_HOST="${SFL_HOST:-sfl-desktop}"
SFL_USER="${SFL_USER:-ayattara}"
SFL_PING_IP="${SFL_PING_IP:-192.168.50.211}"
SSH_KEY="${SSH_KEY:-$USER_HOME/.ssh/mini-desk}"
CODE_DIR="${CODE_DIR:-$USER_HOME/Code}"
KANDEV_DIR="${KANDEV_DIR:-$USER_HOME/.local/share/kandev}"

if [[ $EUID -ne 0 ]]; then
  echo "ERROR: must run as root (sudo $0)" >&2
  exit 2
fi

if ! ping -c1 -W3 "$SFL_PING_IP" >/dev/null 2>&1; then
  echo "ERROR: sfl-desktop ($SFL_PING_IP) unreachable. Is SFL VPN up?" >&2
  echo "  sudo nmcli connection up 'SFL Montreal VPN'" >&2
  exit 1
fi

SSH_CMD="ssh -F $USER_HOME/.ssh/config -i $SSH_KEY -o User=$SFL_USER -o ConnectTimeout=5 -o StrictHostKeyChecking=accept-new"

echo "About to push (as root, ssh as $SFL_USER, --chown=$SFL_USER:$SFL_USER on dest):"
echo "  $CODE_DIR/        -> $SFL_HOST:Code/                        (with --delete)"
echo "  $KANDEV_DIR/      -> $SFL_HOST:.local/share/kandev/         (no --delete)"
read -r -p "Continue? [y/N] " ans
[[ "$ans" =~ ^[Yy]$ ]] || { echo "aborted"; exit 1; }

echo ">> stopping kandev on sfl-desktop (avoid sqlite write during sync)..."
$SSH_CMD "$SFL_HOST" "cd ~/Code/kandev 2>/dev/null && docker compose stop kandev 2>/dev/null || docker stop kandev 2>/dev/null || true"

RSYNC_EXCLUDES=(
  # ── mini-desktop infra service dirs (systemd-managed, not workspace projects) ──
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
  --chown="$SFL_USER:$SFL_USER" \
  "${RSYNC_EXCLUDES[@]}" \
  "$CODE_DIR/" "$SFL_HOST:Code/"

echo ">> rsync kandev data ..."
rsync -avz \
  -e "$SSH_CMD" \
  --chown="$SFL_USER:$SFL_USER" \
  "$KANDEV_DIR/" "$SFL_HOST:.local/share/kandev/"

echo ">> restarting kandev on sfl-desktop ..."
$SSH_CMD "$SFL_HOST" "cd ~/Code/kandev 2>/dev/null && docker compose up -d kandev 2>/dev/null || docker start kandev 2>/dev/null || true"

echo "Done. sfl-desktop is now in sync with mini-desktop."
