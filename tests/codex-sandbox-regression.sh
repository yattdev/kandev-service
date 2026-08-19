#!/usr/bin/env bash
set -euo pipefail

# Run this from a fresh exec-worktree agent task. Codex injects apply_patch for
# the task; copying it into the fixture keeps the real helper executable inside
# the workspace-write root used by the nested sandbox invocation.
APPLY_PATCH_SOURCE="${APPLY_PATCH_BIN:-$(command -v apply_patch || true)}"
if [[ -z "$APPLY_PATCH_SOURCE" || ! -x "$APPLY_PATCH_SOURCE" ]]; then
    echo "SKIP: apply_patch is injected only inside an active Codex task. Re-run this test from a fresh exec-worktree task." >&2
    exit 77
fi

CODEX_BIN="${CODEX_BIN:-$(command -v codex || true)}"
if [[ -z "$CODEX_BIN" || ! -x "$CODEX_BIN" ]]; then
    echo "ERROR: codex CLI not found" >&2
    exit 1
fi

FIXTURE="$(mktemp -d "${HOME}/.codex-regression-workspace.XXXXXX")"
BOUNDARY_DIR="$(mktemp -d "${HOME}/.codex-regression-outside.XXXXXX")"
trap 'rm -rf "$FIXTURE" "$BOUNDARY_DIR"' EXIT HUP INT TERM
mkdir -p "$FIXTURE/.test-bin"
cp --dereference "$APPLY_PATCH_SOURCE" "$FIXTURE/.test-bin/apply_patch"
chmod 0755 "$FIXTURE/.test-bin/apply_patch"

git -C "$FIXTURE" init -q
git -C "$FIXTURE" config user.name sandbox-test
git -C "$FIXTURE" config user.email sandbox-test@example.invalid
printf 'tracked-before\n' > "$FIXTURE/tracked.txt"
git -C "$FIXTURE" add tracked.txt
git -C "$FIXTURE" commit -qm fixture

run_patch() {
    "$CODEX_BIN" sandbox -P :workspace --sandbox-state-disable-network -C "$FIXTURE" -- \
        "$FIXTURE/.test-bin/apply_patch"
}

run_patch <<'PATCH'
*** Begin Patch
*** Add File: created.txt
+created-once
*** End Patch
PATCH

run_patch <<'PATCH'
*** Begin Patch
*** Update File: created.txt
@@
-created-once
+created-twice
*** End Patch
PATCH

run_patch <<'PATCH'
*** Begin Patch
*** Update File: tracked.txt
@@
-tracked-before
+tracked-after
*** End Patch
PATCH

[[ "$(<"$FIXTURE/created.txt")" == "created-twice" ]]
[[ "$(<"$FIXTURE/tracked.txt")" == "tracked-after" ]]

printf 'outside-before\n' > "$BOUNDARY_DIR/sentinel.txt"
if "$CODEX_BIN" sandbox -P :workspace --sandbox-state-disable-network -C "$FIXTURE" -- \
    sh -c 'printf "escaped\n" > "$1"' sh "$BOUNDARY_DIR/sentinel.txt" 2>/dev/null; then
    echo "ERROR: workspace-write sandbox allowed a write outside the fixture" >&2
    exit 1
fi
[[ "$(<"$BOUNDARY_DIR/sentinel.txt")" == "outside-before" ]]

if "$CODEX_BIN" sandbox -P :workspace --sandbox-state-disable-network -C "$FIXTURE" -- \
    python3 -c 'import socket; socket.socket()' 2>/dev/null; then
    echo "ERROR: network-disabled sandbox allowed socket creation" >&2
    exit 1
fi

echo "PASS: apply_patch mutations plus workspace and network boundaries"
