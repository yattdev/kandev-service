#!/bin/sh
set -eu

if ! command -v bwrap >/dev/null 2>&1; then
    echo "ERROR: Codex sandbox preflight: /usr/bin/bwrap is missing. Rebuild the Kandev worker image with bubblewrap installed." >&2
    exit 78
fi

# Prefer a namespace-local procfs for correct PID visibility, but retain the
# existing container procfs when the host runtime cannot authorize that mount.
guard_bin="${KANDEV_GUARD_BIN:-/usr/local/bin/kandev-agent-guard}"
private_proc_marker="${KANDEV_PRIVATE_PROC_MARKER:-/run/kandev-private-proc-supported}"
if ! [ -x "$guard_bin" ] || ! grep -Eq -- '--proc[[:space:]]+/proc([[:space:])]|$)' "$guard_bin"; then
    echo "ERROR: Codex sandbox preflight: agent guard is missing required private procfs." >&2
    exit 78
fi

preflight_error="$(mktemp)"
trap 'rm -f "$preflight_error"' EXIT HUP INT TERM

if bwrap \
    --unshare-user \
    --unshare-pid \
    --unshare-net \
    --ro-bind / / \
    --proc /proc \
    --dev /dev \
    -- sh -ceu 'test -r /proc/$$/status; bwrap --unshare-user --dev-bind / / true' \
    2>"$preflight_error"; then
    : >"$private_proc_marker"
    exit 0
fi

rm -f "$private_proc_marker"
if ! bwrap \
    --unshare-user \
    --unshare-net \
    --ro-bind / / \
    --dev /dev \
    -- true \
    2>>"$preflight_error"; then
    echo "ERROR: Codex workspace-write sandbox cannot create its bubblewrap namespaces." >&2
    echo "The worker runtime must use seccomp/kandev-bwrap.json and permit nested unprivileged user namespaces; do not use seccomp=unconfined or CAP_SYS_ADMIN." >&2
    echo "Diagnostic: docker run --rm --security-opt seccomp=./seccomp/kandev-bwrap.json --security-opt apparmor=kandev-codex kandev-local:latest /usr/local/bin/codex-sandbox-preflight" >&2
    sed 's/^/bubblewrap: /' "$preflight_error" >&2
    exit 78
fi

echo "WARNING: private procfs is unavailable; continuing without private procfs." >&2
