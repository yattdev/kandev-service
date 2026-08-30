#!/bin/sh
set -e

preflight_worker() {
    if [ "${1:-}" = "kandev" ] && [ "${2:-}" = "start" ]; then
        /usr/local/bin/codex-sandbox-preflight
    fi
}

start_agent_docker_broker() {
    if [ "${1:-}" != "kandev" ] || [ "${2:-}" != "start" ]; then
        return 0
    fi
    install -d -m 0700 -o kandev -g kandev /run/kandev-agent-docker
    gosu kandev sh -c '
        while :; do
            /usr/local/bin/kandev-agent-docker-broker
            status=$?
            echo "kandev-agent-docker-broker exited with status $status; restarting" >&2
            sleep 1
        done
    ' &
    attempts=0
    while [ ! -S /run/kandev-agent-docker/broker.sock ]; do
        attempts=$((attempts + 1))
        if [ "$attempts" -ge 50 ]; then
            echo "ERROR: task-scoped Docker broker did not start" >&2
            exit 78
        fi
        sleep 0.1
    done
}

if [ "$(id -u)" = '0' ]; then
    # HOME for the kandev user lives on the PV so agent CLI auth state
    # (gh, claude, codex, auggie, copilot, amp, ...) survives pod restarts
    # and image upgrades. Make sure it exists before dropping privileges.
    # The host and container user intentionally share UID 1000, so bind-mounted
    # data is already writable by kandev. Never recursively chown /data here:
    # it contains the database plus Code/task bind mounts, and walking those on
    # every restart can take minutes and cross into host project trees.
    # Initialize only the runtime directories that this entrypoint may create.
    mkdir -p /data/home
    chown kandev:kandev /data /data/home 2>/dev/null || true
    install -d -m 0700 -o kandev -g kandev /data/home/.android
    [ ! -f /data/home/.android/adbkey ] || chmod 0600 /data/home/.android/adbkey
    for runtime_dir in /data/data /data/plugins /data/supervisor; do
        [ ! -d "$runtime_dir" ] || chown kandev:kandev "$runtime_dir" 2>/dev/null || true
    done
    # Fail before the Kandev server accepts agent work when the enclosing
    # container runtime prevents Codex's bubblewrap sandbox from starting.
    if [ "${1:-}" = "kandev" ] && [ "${2:-}" = "start" ]; then
        gosu kandev /usr/local/bin/codex-sandbox-preflight
    fi
    start_agent_docker_broker "$@"
    exec gosu kandev "$@"
fi

# Direct non-root image invocations should receive the same preflight.
preflight_worker "$@"
exec "$@"
