#!/usr/bin/env bash
# setup-toolchains.sh — install the global language toolchains (mise) into the
# kandev container's persistent volume.
#
# Why this exists:
#   The image ships `mise` + build headers but NO pre-installed language
#   runtimes (installing them at build time would be wiped by the /data bind
#   mount and would bloat the image). Instead, tools install once into
#   /data/home/.local/share/mise — which lives on the persistent bind mount —
#   so they survive image rebuilds and `docker compose up --force-recreate`.
#
# Run this ONCE after the first build (and again only if you change the global
# versions in mise.default.toml). Per-project versions are installed
# automatically by mise when an agent works inside a project that pins them.
#
# Usage:
#   bash ~/Code/kandev/setup-toolchains.sh              # install all globals
#   bash ~/Code/kandev/setup-toolchains.sh node python  # install a subset
#
# Notes:
#   * node / python / go / java / dotnet install as precompiled binaries (fast).
#   * ruby / php compile from source (several minutes on first install).
#   * Each tool is installed independently, so one failure never blocks the rest.
set -uo pipefail

CONTAINER="${KANDEV_CONTAINER:-kandev}"

# Tools to install: CLI args if given, otherwise every tool in the system config.
if [[ $# -gt 0 ]]; then
  TOOLS=("$@")
else
  mapfile -t TOOLS < <(docker exec -u kandev "$CONTAINER" \
    sh -c "sed -n '/^\[tools\]/,/^\[/p' /etc/mise/config.toml \
           | grep -oE '^[a-z0-9]+' " 2>/dev/null)
fi

if [[ ${#TOOLS[@]} -eq 0 ]]; then
  echo "No tools found in /etc/mise/config.toml (is the '$CONTAINER' container running?)" >&2
  exit 1
fi

echo "Installing toolchains into '$CONTAINER': ${TOOLS[*]}"
echo "(ruby/php compile from source and may take several minutes)"
echo

FAILED=()
for tool in "${TOOLS[@]}"; do
  echo "── mise install $tool ──────────────────────────────────────────"
  if docker exec -u kandev "$CONTAINER" mise install "$tool" --yes; then
    echo "  ✓ $tool installed"
  else
    echo "  ✗ $tool FAILED"
    FAILED+=("$tool")
  fi
  echo
done

echo "Regenerating shims..."
docker exec -u kandev "$CONTAINER" mise reshim >/dev/null 2>&1 || true

echo
if [[ ${#FAILED[@]} -eq 0 ]]; then
  echo "All toolchains installed. Verify with:"
  echo "  docker exec -u kandev $CONTAINER mise ls"
  exit 0
else
  echo "Finished with failures: ${FAILED[*]}"
  echo "Re-run for just those, e.g.: bash $0 ${FAILED[*]}"
  exit 1
fi
