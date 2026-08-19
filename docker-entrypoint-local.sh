#!/bin/sh
set -e

preflight_worker() {
    if [ "${1:-}" = "kandev" ] && [ "${2:-}" = "start" ]; then
        /usr/local/bin/codex-sandbox-preflight
    fi
}

if [ "$(id -u)" = '0' ]; then
    # HOME for the kandev user lives on the PV so agent CLI auth state
    # (gh, claude, codex, auggie, copilot, amp, ...) survives pod restarts
    # and image upgrades. Make sure it exists before dropping privileges.
    mkdir -p /data/home
    # Patched: || true so that chown failures on read-only bind mounts
    # (e.g. ~/.ssh:ro, ~/.gitconfig:ro in docker-compose.override.yml) do not
    # abort startup under `set -e`. All writable paths under /data are still
    # chowned to kandev:kandev correctly; only the :ro mounts are skipped.
    chown -R kandev:kandev /data 2>/dev/null || true
    # Fail before the Kandev server accepts agent work when the enclosing
    # container runtime prevents Codex's bubblewrap sandbox from starting.
    if [ "${1:-}" = "kandev" ] && [ "${2:-}" = "start" ]; then
        gosu kandev /usr/local/bin/codex-sandbox-preflight
    fi
    exec gosu kandev "$@"
fi

# Direct non-root image invocations should receive the same preflight.
preflight_worker "$@"
exec "$@"
