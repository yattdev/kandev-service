#!/usr/bin/env bash
set -euo pipefail

PROFILE_NAME="kandev-codex"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROFILE_FILE="$SCRIPT_DIR/../apparmor/$PROFILE_NAME"
INSTALLED_FILE="/etc/apparmor.d/$PROFILE_NAME"

if [[ "$(cat /sys/module/apparmor/parameters/enabled 2>/dev/null || true)" != "Y" ]]; then
    exit 0
fi

if [[ ! -x /usr/sbin/apparmor_parser ]]; then
    echo "ERROR: AppArmor is enabled but apparmor_parser is unavailable. Install the host 'apparmor' package, then run: sudo $0" >&2
    exit 78
fi

if [[ "${EUID}" -ne 0 ]]; then
    echo "ERROR: the Codex worker AppArmor profile must be loaded by root. Run: sudo $0" >&2
    exit 78
fi

install -m 0644 "$PROFILE_FILE" "$INSTALLED_FILE"
/usr/sbin/apparmor_parser -r -W "$INSTALLED_FILE"
echo "Installed and loaded AppArmor profile: $INSTALLED_FILE"
