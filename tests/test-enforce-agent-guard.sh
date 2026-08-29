#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
DB="$TMP/kandev.db"

python3 - "$DB" <<'PY'
import sqlite3
import sys

db = sys.argv[1]
connection = sqlite3.connect(db)
connection.executescript(
    """
    CREATE TABLE agents (id TEXT PRIMARY KEY, name TEXT NOT NULL);
    CREATE TABLE agent_profiles (
        id TEXT PRIMARY KEY,
        agent_id TEXT NOT NULL,
        mode TEXT,
        auto_approve INTEGER NOT NULL DEFAULT 0,
        dangerously_skip_permissions INTEGER NOT NULL DEFAULT 0,
        cli_flags TEXT NOT NULL DEFAULT '[]',
        command_prefix TEXT NOT NULL DEFAULT '',
        updated_at TIMESTAMP
    );
    INSERT INTO agents(id, name) VALUES
        ('codex', 'codex-acp'),
        ('claude', 'claude-acp'),
        ('copilot', 'copilot-acp');
    INSERT INTO agent_profiles(id, agent_id, mode, cli_flags, command_prefix) VALUES
        ('codex-existing', 'codex', 'agent', '[]', ''),
        ('claude-existing', 'claude', 'plan', '[]', ''),
        ('copilot-existing', 'copilot', 'agent', '[
            {"flag":"--allow-all-paths","enabled":false},
            {"flag":"--allow-all-tools","enabled":false},
            {"flag":"--allow-all-urls","enabled":false},
            {"flag":"--no-ask-user","enabled":false}
        ]', '');
    """
)
connection.commit()
connection.close()
PY

"$ROOT/scripts/enforce-agent-guard.sh" "$DB" >/dev/null

python3 - "$DB" <<'PY'
import sqlite3
import sys

db = sys.argv[1]
connection = sqlite3.connect(db)
guard = "/usr/local/bin/kandev-agent-guard --"

assert connection.execute(
    "SELECT mode, auto_approve, dangerously_skip_permissions, command_prefix "
    "FROM agent_profiles WHERE id='codex-existing'"
).fetchone() == ("agent-full-access", 1, 1, guard)
assert connection.execute(
    "SELECT mode, auto_approve, dangerously_skip_permissions, command_prefix "
    "FROM agent_profiles WHERE id='claude-existing'"
).fetchone() == ("bypassPermissions", 1, 1, guard)
copilot = connection.execute(
    "SELECT auto_approve, dangerously_skip_permissions, cli_flags, command_prefix "
    "FROM agent_profiles WHERE id='copilot-existing'"
).fetchone()
assert copilot[:2] == (1, 1) and copilot[3] == guard
flags = {item["flag"]: item["enabled"] for item in __import__("json").loads(copilot[2])}
assert flags["--allow-all-paths"] is True
assert flags["--allow-all-tools"] is True
assert flags["--allow-all-urls"] is True
assert flags["--no-ask-user"] is False

# Inserts and later UI edits cannot silently restore Codex's incompatible
# nested workspace-write sandbox or remove the outer guard.
connection.execute(
    "INSERT INTO agent_profiles(id, agent_id, mode, cli_flags, command_prefix) VALUES (?, ?, ?, ?, ?)",
    ("codex-new", "codex", "agent", "[]", ""),
)
assert connection.execute(
    "SELECT mode, command_prefix FROM agent_profiles WHERE id='codex-new'"
).fetchone() == ("agent-full-access", guard)
connection.execute(
    "UPDATE agent_profiles SET mode='agent', command_prefix='' WHERE id='codex-new'"
)
assert connection.execute(
    "SELECT mode, command_prefix FROM agent_profiles WHERE id='codex-new'"
).fetchone() == ("agent-full-access", guard)
connection.close()
PY

echo "PASS: all agent providers are full-access only inside the persistent outer guard"
