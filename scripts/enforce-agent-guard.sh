#!/usr/bin/env bash
# Persistently force every Kandev agent profile through kandev-agent-guard.
set -euo pipefail

DB="${1:-${KANDEV_DB:-$HOME/.local/share/kandev/data/kandev.db}}"
PREFIX="/usr/local/bin/kandev-agent-guard --"
PYTHON="${PYTHON:-/usr/bin/python3}"

[[ -f "$DB" ]] || { echo "ERROR: Kandev database not found: $DB" >&2; exit 78; }
[[ -x "$PYTHON" ]] || { echo "ERROR: Python 3 is required: $PYTHON" >&2; exit 78; }

# Use Python's standard-library sqlite3 module rather than a host sqlite3 CLI.
# User systemd has a deliberately small PATH, while Python is available at a
# stable system path on every supported Kandev host.
"$PYTHON" - "$DB" "$PREFIX" <<'PY'
import sqlite3
import sys

db, prefix = sys.argv[1:]
try:
    connection = sqlite3.connect(db, timeout=30)
    connection.execute("PRAGMA busy_timeout = 30000")
    connection.executescript(
        """
BEGIN IMMEDIATE;
UPDATE agent_profiles
SET command_prefix = '/usr/local/bin/kandev-agent-guard --',
    updated_at = CURRENT_TIMESTAMP
WHERE command_prefix != '/usr/local/bin/kandev-agent-guard --';

DROP TRIGGER IF EXISTS agent_profiles_require_guard_insert;
DROP TRIGGER IF EXISTS agent_profiles_require_guard_update;

CREATE TRIGGER agent_profiles_require_guard_insert
AFTER INSERT ON agent_profiles
WHEN NEW.command_prefix != '/usr/local/bin/kandev-agent-guard --'
BEGIN
    UPDATE agent_profiles
    SET command_prefix = '/usr/local/bin/kandev-agent-guard --'
    WHERE id = NEW.id;
END;

CREATE TRIGGER agent_profiles_require_guard_update
AFTER UPDATE OF command_prefix ON agent_profiles
WHEN NEW.command_prefix != '/usr/local/bin/kandev-agent-guard --'
BEGIN
    UPDATE agent_profiles
    SET command_prefix = '/usr/local/bin/kandev-agent-guard --'
    WHERE id = NEW.id;
END;
COMMIT;
"""
    )
    unguarded = connection.execute(
        "SELECT COUNT(*) FROM agent_profiles WHERE command_prefix != ?", (prefix,)
    ).fetchone()[0]
    total = connection.execute("SELECT COUNT(*) FROM agent_profiles").fetchone()[0]
except sqlite3.Error as error:
    print(f"ERROR: unable to enforce the Kandev agent guard: {error}", file=sys.stderr)
    sys.exit(78)
finally:
    if "connection" in locals():
        connection.close()

if unguarded:
    print(f"ERROR: {unguarded} Kandev profiles remain unguarded", file=sys.stderr)
    sys.exit(78)
print(f"Agent guard enforced for {total} profiles")
PY
