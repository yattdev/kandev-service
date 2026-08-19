#!/usr/bin/env bash
set -euo pipefail

if [[ "$(cat /proc/sys/kernel/unprivileged_userns_clone 2>/dev/null || true)" != "1" ]]; then
    echo "ERROR: Codex sandbox requires kernel.unprivileged_userns_clone=1 on this worker node." >&2
    exit 78
fi

if [[ "$(cat /sys/module/apparmor/parameters/enabled 2>/dev/null || true)" == "Y" ]]; then
    # Modern AppArmor installations restrict the profiles file to root. Let
    # Docker perform an authoritative, unprivileged profile lookup instead.
    if ! docker run --rm \
        --security-opt apparmor=kandev-codex \
        --entrypoint /bin/true \
        kandev-local:latest >/dev/null 2>&1; then
        echo "ERROR: AppArmor is enabled but Docker cannot select the kandev-codex worker profile." >&2
        echo "Run: sudo bash scripts/install-codex-apparmor.sh" >&2
        exit 78
    fi
fi
