#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
HELPER="$ROOT/scripts/ensure-main-checkout.sh"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

fail() {
    echo "ERROR: $*" >&2
    exit 1
}

REPO="$TMP/repo"
git init -q -b main "$REPO"
git -C "$REPO" config user.name test
git -C "$REPO" config user.email test@example.com
echo main > "$REPO/tracked"
git -C "$REPO" add tracked
git -C "$REPO" commit -qm main
git -C "$REPO" switch -qc workflow

bash "$HELPER" "$REPO"
[[ "$(git -C "$REPO" branch --show-current)" == "main" ]] \
    || fail "clean workflow branch was not switched to main"

git -C "$REPO" switch -q workflow
echo dirty >> "$REPO/tracked"
rc=0
bash "$HELPER" "$REPO" >/dev/null 2>&1 || rc=$?
[[ "$rc" -eq 78 ]] || fail "dirty checkout returned $rc instead of 78"
[[ "$(git -C "$REPO" branch --show-current)" == "workflow" ]] \
    || fail "dirty checkout changed branches"

git -C "$REPO" restore tracked
KANDEV_ALLOW_BRANCH=1 bash "$HELPER" "$REPO" >/dev/null
[[ "$(git -C "$REPO" branch --show-current)" == "workflow" ]] \
    || fail "branch override unexpectedly switched branches"

bash "$HELPER" "$TMP"

echo "ensure-main-checkout: all tests passed"
