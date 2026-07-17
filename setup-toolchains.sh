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
# How it installs:
#   Each toolchain is built in an ISOLATED throwaway container that shares the
#   same /data volume, NOT via `docker exec` into the running kandev container.
#   This matters because compiling Ruby/PHP from source is heavy and long; doing
#   it inside the live kandev container can starve/stop the service (observed:
#   the container received SIGTERM mid-compile). The isolated build writes the
#   finished runtime into the shared volume, so the running kandev picks it up
#   via its shims — with zero disruption. kandev need not even be running.
#
# Run this ONCE after the first build (and again only if you change the global
# versions in mise.default.toml). Per-project versions are installed
# automatically by mise when an agent works inside a project that pins them.
#
# Usage:
#   bash ~/Code/kandev/setup-toolchains.sh              # install all globals
#   bash ~/Code/kandev/setup-toolchains.sh node python  # install a subset
#
# Env overrides:
#   KANDEV_IMAGE     image to build from      (default: kandev-local:latest)
#   KANDEV_DATA_DIR  host path of /data vol    (default: $HOME/.local/share/kandev)
#
# Notes:
#   * node / python / go / java / dotnet install as precompiled binaries (fast).
#   * ruby / php compile from source (several minutes on first install).
#   * Each tool is installed independently, so one failure never blocks the rest.
set -uo pipefail

IMAGE="${KANDEV_IMAGE:-kandev-local:latest}"
DATA_DIR="${KANDEV_DATA_DIR:-$HOME/.local/share/kandev}"

if ! docker image inspect "$IMAGE" >/dev/null 2>&1; then
  echo "Image '$IMAGE' not found — run: docker compose build" >&2
  exit 1
fi
if [[ ! -d "$DATA_DIR" ]]; then
  echo "Data volume dir '$DATA_DIR' not found (set KANDEV_DATA_DIR)" >&2
  exit 1
fi

# Run mise in a disposable container that mounts the shared persistent volume.
# --network host matches the kandev service (works behind the sfl transparent
# proxy); the non-root entrypoint just exec's the command.
mise_run() {
  docker run --rm --network host \
    -u kandev -e HOME=/data/home \
    -v "$DATA_DIR:/data" \
    "$IMAGE" mise "$@"
}

# Tools to install: CLI args if given, otherwise every tool in the system config.
if [[ $# -gt 0 ]]; then
  TOOLS=("$@")
else
  mapfile -t TOOLS < <(docker run --rm "$IMAGE" \
    sh -c "sed -n '/^\[tools\]/,/^\[/p' /etc/mise/config.toml \
           | grep -oE '^[a-z0-9]+'" 2>/dev/null)
fi

if [[ ${#TOOLS[@]} -eq 0 ]]; then
  echo "No tools found in /etc/mise/config.toml" >&2
  exit 1
fi

echo "Installing toolchains from '$IMAGE' into '$DATA_DIR': ${TOOLS[*]}"
echo "(ruby/php compile from source and may take several minutes)"
echo

FAILED=()
for tool in "${TOOLS[@]}"; do
  echo "── mise install $tool ──────────────────────────────────────────"
  if mise_run install "$tool" --yes; then
    echo "  ✓ $tool installed"
  else
    echo "  ✗ $tool FAILED"
    FAILED+=("$tool")
  fi
  echo
done

echo "Regenerating shims..."
mise_run reshim >/dev/null 2>&1 || true

echo
if [[ ${#FAILED[@]} -eq 0 ]]; then
  echo "All toolchains installed. Verify with:"
  echo "  docker exec -u kandev kandev mise ls"
  exit 0
else
  echo "Finished with failures: ${FAILED[*]}"
  echo "Re-run for just those, e.g.: bash $0 ${FAILED[*]}"
  exit 1
fi
