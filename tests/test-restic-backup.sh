#!/usr/bin/env bash
# Regression tests for remote-first Restic backup with local fallback.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

mkdir -p "$TMP/bin" "$TMP/data-one" "$TMP/data-two" "$TMP/data-three"
printf payload > "$TMP/data-one/state"
printf payload > "$TMP/data-two/state"
printf payload > "$TMP/data-three/state"
printf password > "$TMP/password"

cat > "$TMP/bin/ping-down" <<'SH'
#!/bin/sh
exit 1
SH
cat > "$TMP/bin/ping-up" <<'SH'
#!/bin/sh
exit 0
SH
cat > "$TMP/bin/restic" <<'SH'
#!/bin/sh
set -u
repo="$2"
command="$3"
printf '%s %s\n' "$repo" "$command" >> "$RESTIC_TEST_CALLS"
case "$command" in
  snapshots)
    if [ "$repo" = "$RESTIC_TEST_REMOTE" ]; then
      exit 0
    fi
    test -f "$repo/.initialized"
    ;;
  init)
    case "$repo" in sftp:*) exit 1;; esac
    mkdir -p "$repo"
    : > "$repo/.initialized"
    ;;
  backup)
    if [ "$repo" = "$RESTIC_TEST_REMOTE" ] && [ "${RESTIC_TEST_FAIL_REMOTE:-0}" = 1 ]; then
      exit 1
    fi
    : > "$repo/.backup-ran"
    ;;
  forget)
    :
    ;;
  *)
    exit 2
    ;;
esac
SH
chmod +x "$TMP/bin/ping-down" "$TMP/bin/ping-up" "$TMP/bin/restic"

REMOTE="sftp:test@offline:repo"
export RESTIC_TEST_REMOTE="$REMOTE"

# VPN/host unavailable: do not skip; initialize and back up locally.
export RESTIC_TEST_CALLS="$TMP/calls-one"
PING="$TMP/bin/ping-down" \
RESTIC="$TMP/bin/restic" \
RESTIC_REPO="$REMOTE" \
LOCAL_RESTIC_REPO="$TMP/local-one" \
RESTIC_PASSWORD_FILE="$TMP/password" \
KANDEV_DATA="$TMP/data-one" \
LOG="$TMP/one.log" \
LOCK="$TMP/one.lock" \
bash "$ROOT/kandev-restic-backup.sh" >/dev/null
test -f "$TMP/local-one/.backup-ran"
grep -Fq "$TMP/local-one backup" "$TMP/calls-one"
if grep -Fq "$REMOTE backup" "$TMP/calls-one"; then
  echo "ERROR: unreachable remote was used for backup" >&2
  exit 1
fi

# Ping succeeds but SFTP backup fails: retry the same run locally.
export RESTIC_TEST_CALLS="$TMP/calls-two"
export RESTIC_TEST_FAIL_REMOTE=1
PING="$TMP/bin/ping-up" \
RESTIC="$TMP/bin/restic" \
RESTIC_REPO="$REMOTE" \
LOCAL_RESTIC_REPO="$TMP/local-two" \
RESTIC_PASSWORD_FILE="$TMP/password" \
KANDEV_DATA="$TMP/data-two" \
LOG="$TMP/two.log" \
LOCK="$TMP/two.lock" \
bash "$ROOT/kandev-restic-backup.sh" >/dev/null
test -f "$TMP/local-two/.backup-ran"
grep -Fq "$REMOTE backup" "$TMP/calls-two"
grep -Fq "$TMP/local-two backup" "$TMP/calls-two"

# Recursive placement is rejected before Restic runs.
recursive_rc=0
PING="$TMP/bin/ping-down" \
RESTIC="$TMP/bin/restic" \
RESTIC_REPO="$REMOTE" \
LOCAL_RESTIC_REPO="$TMP/data-two/repository" \
RESTIC_PASSWORD_FILE="$TMP/password" \
KANDEV_DATA="$TMP/data-two" \
LOG="$TMP/recursive.log" \
LOCK="$TMP/recursive.lock" \
bash "$ROOT/kandev-restic-backup.sh" >/dev/null || recursive_rc=$?
test "$recursive_rc" -eq 78

# The former visible default is atomically migrated to the documented hidden
# location when no explicit LOCAL_RESTIC_REPO override is configured.
mkdir -p "$TMP/home/Backups/restic/kandev-backup"
: > "$TMP/home/Backups/restic/kandev-backup/.initialized"
export RESTIC_TEST_CALLS="$TMP/calls-three"
unset RESTIC_TEST_FAIL_REMOTE
PING="$TMP/bin/ping-down" \
RESTIC="$TMP/bin/restic" \
RESTIC_REPO="$REMOTE" \
RESTIC_PASSWORD_FILE="$TMP/password" \
USER_HOME="$TMP/home" \
KANDEV_DATA="$TMP/data-three" \
LOG="$TMP/three.log" \
LOCK="$TMP/three.lock" \
bash "$ROOT/kandev-restic-backup.sh" >/dev/null
test -f "$TMP/home/.Backups/restic/kandev-backup/.backup-ran"
test ! -e "$TMP/home/Backups/restic/kandev-backup"

echo "PASS: restic uses a non-recursive local fallback when remote access is unavailable or fails"
