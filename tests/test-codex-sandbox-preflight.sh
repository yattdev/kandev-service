#!/usr/bin/env bash
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PREFLIGHT="$REPO_DIR/scripts/codex-sandbox-preflight.sh"
TMP_DIR="$(mktemp -d)"
trap 'rm -rf "$TMP_DIR"' EXIT

mkdir -p "$TMP_DIR/bin"
cat >"$TMP_DIR/bin/bwrap" <<'EOF'
#!/bin/sh
case " $* " in
    *" --proc /proc "*)
        [ "${BWRAP_PRIVATE_PROC_SUPPORTED:-0}" = 1 ]
        ;;
    *)
        case " $* " in
            *" --unshare-pid "*) exit 1 ;;
            *" --bind /proc /proc "*) exit 0 ;;
            *) exit 1 ;;
        esac
        ;;
esac
EOF
chmod +x "$TMP_DIR/bin/bwrap"

cat >"$TMP_DIR/guard" <<'EOF'
#!/bin/sh
printf '%s\n' --proc /proc
EOF
chmod +x "$TMP_DIR/guard"

marker="$TMP_DIR/private-proc-supported"
stderr="$TMP_DIR/stderr"

PATH="$TMP_DIR/bin:$PATH" \
KANDEV_GUARD_BIN="$TMP_DIR/guard" \
KANDEV_PRIVATE_PROC_MARKER="$marker" \
BWRAP_PRIVATE_PROC_SUPPORTED=0 \
    "$PREFLIGHT" 2>"$stderr"

[[ ! -e "$marker" ]]
grep -q "continuing without private procfs" "$stderr"

PATH="$TMP_DIR/bin:$PATH" \
KANDEV_GUARD_BIN="$TMP_DIR/guard" \
KANDEV_PRIVATE_PROC_MARKER="$marker" \
BWRAP_PRIVATE_PROC_SUPPORTED=1 \
    "$PREFLIGHT" 2>"$stderr"

[[ -f "$marker" ]]
