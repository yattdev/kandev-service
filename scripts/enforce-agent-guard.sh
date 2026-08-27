#!/usr/bin/env bash
# Persistently force every Kandev agent profile through kandev-agent-guard.
set -euo pipefail

DB="${1:-${KANDEV_DB:-$HOME/.local/share/kandev/data/kandev.db}}"
PREFIX="/usr/local/bin/kandev-agent-guard --"

[[ -f "$DB" ]] || { echo "ERROR: Kandev database not found: $DB" >&2; exit 78; }
command -v sqlite3 >/dev/null 2>&1 || { echo "ERROR: sqlite3 is required" >&2; exit 78; }

sqlite3 "$DB" <<'SQL'
.timeout 30000
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
SQL

unguarded="$(sqlite3 "$DB" "SELECT COUNT(*) FROM agent_profiles WHERE command_prefix != '$PREFIX';")"
[[ "$unguarded" == "0" ]] || { echo "ERROR: $unguarded Kandev profiles remain unguarded" >&2; exit 78; }

echo "Agent guard enforced for $(sqlite3 "$DB" 'SELECT COUNT(*) FROM agent_profiles;') profiles"
