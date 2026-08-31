#!/bin/sh
set -eu

if ! command -v bwrap >/dev/null 2>&1; then
    echo "ERROR: Codex sandbox preflight: /usr/bin/bwrap is missing. Rebuild the Kandev worker image with bubblewrap installed." >&2
    exit 78
fi

# The host-loaded AppArmor profile cannot be upgraded by an ordinary image or
# container restart. A private procfs in the inner guard therefore creates a
# deployment-order dependency that presents to every ACP provider as a closed
# stdin/stdout pipe. Keep this invariant fail-fast so Kandev never reports
# itself healthy while all agent sessions are unable to initialize.
guard_bin=/usr/local/bin/kandev-agent-guard
if [ -x "$guard_bin" ] && grep -Eq '^[[:space:]]*--proc[[:space:]]+/proc([[:space:]]|$)' "$guard_bin"; then
    echo "ERROR: agent guard requests a private procfs that image updates cannot authorize in the host AppArmor policy." >&2
    echo "Remove '--proc /proc' from the guard before starting Kandev; otherwise ACP sessions fail with 'file already closed'." >&2
    exit 78
fi

preflight_error="$(mktemp)"
trap 'rm -f "$preflight_error"' EXIT HUP INT TERM

if ! bwrap \
    --unshare-user \
    --unshare-pid \
    --unshare-net \
    --ro-bind / / \
    --dev /dev \
    -- true 2>"$preflight_error"; then
    echo "ERROR: Codex workspace-write sandbox cannot create its bubblewrap namespaces." >&2
    echo "The worker runtime must use seccomp/kandev-bwrap.json and permit nested unprivileged user namespaces; do not use seccomp=unconfined or CAP_SYS_ADMIN." >&2
    echo "Diagnostic: docker run --rm --security-opt seccomp=./seccomp/kandev-bwrap.json --security-opt apparmor=kandev-codex kandev-local:latest /usr/local/bin/codex-sandbox-preflight" >&2
    sed 's/^/bubblewrap: /' "$preflight_error" >&2
    exit 78
fi
