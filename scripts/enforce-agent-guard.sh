#!/usr/bin/env bash
# Persistently force every Kandev agent profile through kandev-agent-guard.
#
# Provider-level permission prompts and filesystem sandboxes are deliberately
# disabled *inside* that guard. The outer Bubblewrap guard is the authoritative
# boundary: it exposes only the task root and the backlink-verified common .git
# directory read-write, while sibling tasks and unrelated Code repositories
# remain read-only. In particular, Codex's workspace-write sandbox otherwise
# reclassifies a linked worktree's common .git directory as read-only and makes
# every git add/commit fail with a read-only index.lock.
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
    auto_approve = 1,
    dangerously_skip_permissions = 1,
    mode = CASE
        WHEN agent_id IN (SELECT id FROM agents WHERE name = 'codex-acp')
        THEN 'agent-full-access'
        WHEN agent_id IN (SELECT id FROM agents WHERE name = 'claude-acp')
        THEN 'bypassPermissions'
        ELSE mode
    END,
    cli_flags = CASE
        WHEN agent_id IN (SELECT id FROM agents WHERE name = 'copilot-acp')
        THEN (
            SELECT json_group_array(json(
                CASE
                    WHEN json_extract(value, '$.flag') IN (
                        '--allow-all-paths', '--allow-all-tools', '--allow-all-urls'
                    )
                    THEN json_set(value, '$.enabled', json('true'))
                    ELSE value
                END
            ))
            FROM json_each(agent_profiles.cli_flags)
        )
        ELSE cli_flags
    END,
    updated_at = CURRENT_TIMESTAMP
WHERE command_prefix != '/usr/local/bin/kandev-agent-guard --'
   OR auto_approve != 1
   OR dangerously_skip_permissions != 1
   OR (
       agent_id IN (SELECT id FROM agents WHERE name = 'codex-acp')
       AND mode != 'agent-full-access'
   )
   OR (
       agent_id IN (SELECT id FROM agents WHERE name = 'claude-acp')
       AND mode != 'bypassPermissions'
   )
   OR (
       agent_id IN (SELECT id FROM agents WHERE name = 'copilot-acp')
       AND EXISTS (
           SELECT 1 FROM json_each(agent_profiles.cli_flags)
           WHERE json_extract(value, '$.flag') IN (
               '--allow-all-paths', '--allow-all-tools', '--allow-all-urls'
           )
             AND json_extract(value, '$.enabled') != 1
       )
   );

DROP TRIGGER IF EXISTS agent_profiles_require_guard_insert;
DROP TRIGGER IF EXISTS agent_profiles_require_guard_update;
DROP TRIGGER IF EXISTS task_sessions_require_guard_insert;
DROP TRIGGER IF EXISTS task_sessions_require_guard_update;

CREATE TRIGGER agent_profiles_require_guard_insert
AFTER INSERT ON agent_profiles
BEGIN
    UPDATE agent_profiles
    SET command_prefix = '/usr/local/bin/kandev-agent-guard --',
        auto_approve = 1,
        dangerously_skip_permissions = 1,
        mode = CASE
            WHEN NEW.agent_id IN (SELECT id FROM agents WHERE name = 'codex-acp')
            THEN 'agent-full-access'
            WHEN NEW.agent_id IN (SELECT id FROM agents WHERE name = 'claude-acp')
            THEN 'bypassPermissions'
            ELSE NEW.mode
        END,
        cli_flags = CASE
            WHEN NEW.agent_id IN (SELECT id FROM agents WHERE name = 'copilot-acp')
            THEN (
                SELECT json_group_array(json(
                    CASE
                        WHEN json_extract(value, '$.flag') IN (
                            '--allow-all-paths', '--allow-all-tools', '--allow-all-urls'
                        )
                        THEN json_set(value, '$.enabled', json('true'))
                        ELSE value
                    END
                ))
                FROM json_each(NEW.cli_flags)
            )
            ELSE NEW.cli_flags
        END
    WHERE id = NEW.id;
END;

CREATE TRIGGER agent_profiles_require_guard_update
AFTER UPDATE OF command_prefix, mode, agent_id, auto_approve,
    dangerously_skip_permissions, cli_flags ON agent_profiles
BEGIN
    UPDATE agent_profiles
    SET command_prefix = '/usr/local/bin/kandev-agent-guard --',
        auto_approve = 1,
        dangerously_skip_permissions = 1,
        mode = CASE
            WHEN NEW.agent_id IN (SELECT id FROM agents WHERE name = 'codex-acp')
            THEN 'agent-full-access'
            WHEN NEW.agent_id IN (SELECT id FROM agents WHERE name = 'claude-acp')
            THEN 'bypassPermissions'
            ELSE NEW.mode
        END,
        cli_flags = CASE
            WHEN NEW.agent_id IN (SELECT id FROM agents WHERE name = 'copilot-acp')
            THEN (
                SELECT json_group_array(json(
                    CASE
                        WHEN json_extract(value, '$.flag') IN (
                            '--allow-all-paths', '--allow-all-tools', '--allow-all-urls'
                        )
                        THEN json_set(value, '$.enabled', json('true'))
                        ELSE value
                    END
                ))
                FROM json_each(NEW.cli_flags)
            )
            ELSE NEW.cli_flags
        END
    WHERE id = NEW.id;
END;

-- Existing long-lived sessions resume from this immutable launch snapshot,
-- not from agent_profiles. Migrate those snapshots too, otherwise an old
-- provider filesystem sandbox can be resurrected inside the outer guard.
UPDATE task_sessions AS ts
SET agent_profile_snapshot = json_set(
        CASE
            WHEN json_valid(ts.agent_profile_snapshot)
             AND json_type(ts.agent_profile_snapshot) = 'object'
            THEN ts.agent_profile_snapshot
            ELSE '{}'
        END,
        '$.command_prefix', '/usr/local/bin/kandev-agent-guard --',
        '$.auto_approve', json('true'),
        '$.dangerously_skip_permissions', json('true'),
        '$.mode', CASE
            WHEN (SELECT a.name FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
                  WHERE ap.id = ts.agent_profile_id) = 'codex-acp'
            THEN 'agent-full-access'
            WHEN (SELECT a.name FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
                  WHERE ap.id = ts.agent_profile_id) = 'claude-acp'
            THEN 'bypassPermissions'
            ELSE COALESCE(json_extract(ts.agent_profile_snapshot, '$.mode'), '')
        END
    )
WHERE EXISTS (SELECT 1 FROM agent_profiles ap WHERE ap.id = ts.agent_profile_id);

UPDATE task_sessions AS ts
SET agent_profile_snapshot = json_set(
        ts.agent_profile_snapshot,
        '$.cli_flags', json(COALESCE(
            (SELECT ap.cli_flags FROM agent_profiles ap WHERE ap.id = ts.agent_profile_id),
            '[]'
        ))
    )
WHERE EXISTS (
    SELECT 1 FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
    WHERE ap.id = ts.agent_profile_id AND a.name = 'copilot-acp'
);

CREATE TRIGGER task_sessions_require_guard_insert
AFTER INSERT ON task_sessions
WHEN EXISTS (SELECT 1 FROM agent_profiles ap WHERE ap.id = NEW.agent_profile_id)
BEGIN
    UPDATE task_sessions
    SET agent_profile_snapshot = json_set(
            CASE
                WHEN json_valid(NEW.agent_profile_snapshot)
                 AND json_type(NEW.agent_profile_snapshot) = 'object'
                THEN NEW.agent_profile_snapshot ELSE '{}'
            END,
            '$.command_prefix', '/usr/local/bin/kandev-agent-guard --',
            '$.auto_approve', json('true'),
            '$.dangerously_skip_permissions', json('true'),
            '$.mode', CASE
                WHEN (SELECT a.name FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
                      WHERE ap.id = NEW.agent_profile_id) = 'codex-acp'
                THEN 'agent-full-access'
                WHEN (SELECT a.name FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
                      WHERE ap.id = NEW.agent_profile_id) = 'claude-acp'
                THEN 'bypassPermissions'
                ELSE COALESCE(json_extract(NEW.agent_profile_snapshot, '$.mode'), '')
            END
        )
    WHERE id = NEW.id;
    UPDATE task_sessions
    SET agent_profile_snapshot = json_set(
            agent_profile_snapshot, '$.cli_flags',
            json(COALESCE((SELECT ap.cli_flags FROM agent_profiles ap
                           WHERE ap.id = NEW.agent_profile_id), '[]'))
        )
    WHERE id = NEW.id
      AND EXISTS (SELECT 1 FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
                  WHERE ap.id = NEW.agent_profile_id AND a.name = 'copilot-acp');
END;

CREATE TRIGGER task_sessions_require_guard_update
AFTER UPDATE OF agent_profile_id, agent_profile_snapshot ON task_sessions
WHEN EXISTS (SELECT 1 FROM agent_profiles ap WHERE ap.id = NEW.agent_profile_id)
BEGIN
    UPDATE task_sessions
    SET agent_profile_snapshot = json_set(
            CASE
                WHEN json_valid(NEW.agent_profile_snapshot)
                 AND json_type(NEW.agent_profile_snapshot) = 'object'
                THEN NEW.agent_profile_snapshot ELSE '{}'
            END,
            '$.command_prefix', '/usr/local/bin/kandev-agent-guard --',
            '$.auto_approve', json('true'),
            '$.dangerously_skip_permissions', json('true'),
            '$.mode', CASE
                WHEN (SELECT a.name FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
                      WHERE ap.id = NEW.agent_profile_id) = 'codex-acp'
                THEN 'agent-full-access'
                WHEN (SELECT a.name FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
                      WHERE ap.id = NEW.agent_profile_id) = 'claude-acp'
                THEN 'bypassPermissions'
                ELSE COALESCE(json_extract(NEW.agent_profile_snapshot, '$.mode'), '')
            END
        )
    WHERE id = NEW.id;
    UPDATE task_sessions
    SET agent_profile_snapshot = json_set(
            agent_profile_snapshot, '$.cli_flags',
            json(COALESCE((SELECT ap.cli_flags FROM agent_profiles ap
                           WHERE ap.id = NEW.agent_profile_id), '[]'))
        )
    WHERE id = NEW.id
      AND EXISTS (SELECT 1 FROM agent_profiles ap JOIN agents a ON a.id = ap.agent_id
                  WHERE ap.id = NEW.agent_profile_id AND a.name = 'copilot-acp');
END;
COMMIT;
"""
    )
    unguarded = connection.execute(
        "SELECT COUNT(*) FROM agent_profiles WHERE command_prefix != ?", (prefix,)
    ).fetchone()[0]
    restricted_profiles = connection.execute(
        """
        SELECT COUNT(*)
        FROM agent_profiles ap
        JOIN agents a ON a.id = ap.agent_id
        WHERE ap.auto_approve != 1
           OR ap.dangerously_skip_permissions != 1
           OR (a.name = 'codex-acp' AND ap.mode != 'agent-full-access')
           OR (a.name = 'claude-acp' AND ap.mode != 'bypassPermissions')
           OR (
               a.name = 'copilot-acp'
               AND EXISTS (
                   SELECT 1 FROM json_each(ap.cli_flags)
                   WHERE json_extract(value, '$.flag') IN (
                       '--allow-all-paths', '--allow-all-tools', '--allow-all-urls'
                   )
                     AND json_extract(value, '$.enabled') != 1
               )
           )
        """
    ).fetchone()[0]
    total = connection.execute("SELECT COUNT(*) FROM agent_profiles").fetchone()[0]
    restricted_sessions = connection.execute(
        """
        SELECT COUNT(*)
        FROM task_sessions ts
        JOIN agent_profiles ap ON ap.id = ts.agent_profile_id
        JOIN agents a ON a.id = ap.agent_id
        WHERE NOT json_valid(ts.agent_profile_snapshot)
           OR COALESCE(json_extract(ts.agent_profile_snapshot, '$.command_prefix'), '') != ?
           OR COALESCE(json_extract(ts.agent_profile_snapshot, '$.auto_approve'), 0) != 1
           OR COALESCE(json_extract(ts.agent_profile_snapshot, '$.dangerously_skip_permissions'), 0) != 1
           OR (a.name = 'codex-acp' AND json_extract(ts.agent_profile_snapshot, '$.mode') != 'agent-full-access')
           OR (a.name = 'claude-acp' AND json_extract(ts.agent_profile_snapshot, '$.mode') != 'bypassPermissions')
        """,
        (prefix,),
    ).fetchone()[0]
    total_sessions = connection.execute(
        "SELECT COUNT(*) FROM task_sessions WHERE agent_profile_id IN (SELECT id FROM agent_profiles)"
    ).fetchone()[0]
except sqlite3.Error as error:
    print(f"ERROR: unable to enforce the Kandev agent guard: {error}", file=sys.stderr)
    sys.exit(78)
finally:
    if "connection" in locals():
        connection.close()

if unguarded:
    print(f"ERROR: {unguarded} Kandev profiles remain unguarded", file=sys.stderr)
    sys.exit(78)
if restricted_profiles:
    print(
        f"ERROR: {restricted_profiles} profiles retain inner permission restrictions",
        file=sys.stderr,
    )
    sys.exit(78)
if restricted_sessions:
    print(
        f"ERROR: {restricted_sessions} session snapshots retain inner permission restrictions",
        file=sys.stderr,
    )
    sys.exit(78)
print(
    f"Agent guard enforced for {total} profiles and {total_sessions} session snapshots; "
    "all providers run full-access inside the guard"
)
PY
