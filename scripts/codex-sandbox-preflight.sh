#!/bin/sh
set -eu

if ! command -v bwrap >/dev/null 2>&1; then
    echo "ERROR: Codex sandbox preflight: /usr/bin/bwrap is missing. Rebuild the Kandev worker image with bubblewrap installed." >&2
    exit 78
fi

# PID isolation requires a namespace-local procfs. The host-loaded AppArmor
# profile is independent of the image, so require the matching guard argument
# and exercise the exact mount before a deployment can replace Kandev.
guard_bin=/usr/local/bin/kandev-agent-guard
if ! [ -x "$guard_bin" ] || ! grep -Eq '^[[:space:]]*--proc[[:space:]]+/proc([[:space:]]|$)' "$guard_bin"; then
    echo "ERROR: Codex sandbox preflight: agent guard is missing required private procfs." >&2
    exit 78
fi

preflight_error="$(mktemp)"
trap 'rm -f "$preflight_error"' EXIT HUP INT TERM

if ! bwrap \
    --unshare-user \
    --unshare-pid \
    --unshare-net \
    --ro-bind / / \
    --proc /proc \
    --dev /dev \
    -- sh -ceu 'test -r /proc/$$/status; bwrap --unshare-user --dev-bind / / true' \
    2>"$preflight_error"; then
    echo "ERROR: Codex workspace-write sandbox cannot create its bubblewrap namespaces." >&2
    echo "The worker runtime must use seccomp/kandev-bwrap.json and permit nested unprivileged user namespaces; do not use seccomp=unconfined or CAP_SYS_ADMIN." >&2
    echo "Diagnostic: docker run --rm --security-opt seccomp=./seccomp/kandev-bwrap.json --security-opt apparmor=kandev-codex kandev-local:latest /usr/local/bin/codex-sandbox-preflight" >&2
    sed 's/^/bubblewrap: /' "$preflight_error" >&2
    exit 78
fi
