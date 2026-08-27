# Kandev live custom prompts: operator runbook

This document is for a trusted host/operator agent responding to an explicit
request from the Kandev instance owner. It explains how to keep the live prompt
and its required Git mirror synchronized without replacing or corrupting the
live database.

It is not an authorization grant for ordinary task agents. A guarded task that
cannot reach the host database must report the requirement through its parent
and workspace Coordinator. It must not request broader mounts, the host Docker
socket, `sudo`, copied credentials, or a guard bypass.

## Data model

Saved prompts live in the `custom_prompts` table of Kandev's persistent SQLite
database:

| Column | Meaning |
|---|---|
| `id` | Stable prompt UUID; discover it, never assume or hardcode a UUID from another instance |
| `name` | Reference name without `@`, such as `workstep-prompt` |
| `content` | Full prompt text |
| `builtin` | Whether Kandev originally seeded the prompt |
| `created_at`, `updated_at` | Persistence timestamps |

Workflow-level instructions are stored in `workflows.prompt`; step-level
instructions are stored in `workflow_steps.prompt`. Either may contain a saved
prompt reference such as `@workstep-prompt`. The backend resolves references by
reading `custom_prompts` when it composes the effective prompt. A service restart
is normally unnecessary after a successful update, but an already-running model
turn cannot be rewritten retroactively.

Every owner-managed saved prompt also has a versioned Markdown mirror:

```text
custom_prompts/<prompt-name>.md
```

For example, `@workstep-prompt` maps to
`custom_prompts/workstep-prompt.md`. The Markdown body is the prompt content;
do not add front matter or explanatory text to that file. Put documentation in
`custom_prompts/README.md` instead. The live SQLite row is the value Kandev runs,
while `main` is the durable, reviewed desired copy. An add/update is incomplete
until both match and the mirror commit has been pushed.

## Authorization rule

Inspecting prompt metadata is read-only diagnosis. Changing prompt content is a
live configuration mutation and requires an explicit request from the instance
owner. Before changing it:

1. Identify the prompt by both name and ID.
2. Identify every workflow/step that references it so the blast radius is known.
3. Confirm the repository worktree is on `main` and is safe to edit.
4. Create or update `custom_prompts/<prompt-name>.md` and review it for secrets.
5. Show or preserve the previous content and make a consistent backup outside
   the repository.
6. Change only the identified row, preferably through the authenticated API.
7. Read the row back, verify it matches the trimmed Markdown file, validate
   references and SQLite integrity, and check Kandev health.
8. Commit the mirror and related documentation on `main`, then push `main`.

Do not silently change a shared prompt while implementing unrelated application
code. Do not edit built-in prompts, workflow prompts, or multiple rows merely
because their wording looks similar. If requested prompt text contains a secret
or private payload that cannot safely be pushed, stop and flag the conflict
instead of committing it or quietly violating the mirror rule.

## Start from `main`

Prompt mirrors are deployment documentation, so they always live on `main`, not
on a `*-workflow` branch. Use a clean main worktree and inspect existing changes
before editing:

```bash
git rev-parse --abbrev-ref HEAD
git status --short --branch
```

The branch must be `main`. Do not move or overwrite unrelated user changes to
get there; use the repository's existing dedicated main worktree when another
checkout has a workflow branch active. Before pushing, inspect the commits that
are ahead of `origin/main` so the push scope is understood.

## Find the actual live database

On the standard host deployment the data root is usually
`${HOME}/.local/share/kandev`, making the database path:

```text
${HOME}/.local/share/kandev/data/kandev.db
```

Inside the trusted outer Kandev container the same file is normally:

```text
/data/data/kandev.db
```

Do not rely on either path without checking the running container. A cron job
run under the wrong user has previously mounted a different home directory and
created a second, stale data tree. Resolve the source mounted at `/data`:

```bash
docker inspect kandev \
  --format '{{range .Mounts}}{{if eq .Destination "/data"}}{{.Source}}{{end}}{{end}}'
```

Append `/data/kandev.db` to that source and confirm that its modification time,
WAL file, and application activity match the live instance. Do not operate on a
similarly named `pre-restore`, test, backup, or stale database.

## Inspect before updating

Set a task-specific shell variable to the verified absolute database path; do
not repurpose `HOME`:

```bash
KANDEV_LIVE_DB=/absolute/data/root/data/kandev.db

sqlite3 -readonly "$KANDEV_LIVE_DB" \
  "SELECT id, name, builtin, length(content) AS chars, updated_at
   FROM custom_prompts ORDER BY name;"
```

After choosing the prompt, resolve its workflow blast radius:

```bash
sqlite3 -readonly "$KANDEV_LIVE_DB" \
  "SELECT ws.name AS workspace, w.name AS workflow, w.prompt
   FROM workflows w
   LEFT JOIN workspaces ws ON ws.id = w.workspace_id
   WHERE instr(w.prompt, '@workstep-prompt') > 0
   ORDER BY ws.name, w.name;

   SELECT ws.name AS workspace, w.name AS workflow, s.name AS step
   FROM workflow_steps s
   JOIN workflows w ON w.id = s.workflow_id
   LEFT JOIN workspaces ws ON ws.id = w.workspace_id
   WHERE instr(s.prompt, '@workstep-prompt') > 0
   ORDER BY ws.name, w.name, s.position;"
```

Replace `workstep-prompt` with the discovered name. Export the current content
to a private backup path for review. The reviewed desired text belongs in its
required `custom_prompts/` mirror; transient exports and backups do not:

```bash
sqlite3 -noheader -readonly "$KANDEV_LIVE_DB" \
  "SELECT content FROM custom_prompts WHERE id = '<discovered-prompt-id>';" \
  > /private/backup/location/prompt.before.md
chmod 600 /private/backup/location/prompt.before.md
```

## Preferred update: authenticated API

Kandev exposes:

```text
GET   /api/v1/prompts
PATCH /api/v1/prompts/<prompt-id>
```

The PATCH JSON accepts `name` and/or `content`. Prefer this path when an
authenticated operator session or appropriately scoped API token is already
available because it uses Kandev's validation and persistence service. Do not
extract browser cookies, print tokens, or create a broader credential merely to
avoid the SQLite fallback.

Conceptual request body:

```json
{
  "content": "complete replacement prompt text"
}
```

Read the prompt back through the API and compare it with the requested text.
An unauthenticated `401` means credentials are required; it does not mean the
service or prompt is missing.

## Allowed fallback: direct SQLite update

Use this only after the owner explicitly requested the live prompt change and
the authenticated API is unavailable or impractical.

### 1. Create a hot backup

SQLite is in WAL mode while Kandev is running. Do not use a plain `cp` of only
`kandev.db`, and never manipulate `-wal` or `-shm` files. Use SQLite's online
backup command and a new, explicit destination outside the repository:

```bash
sqlite3 "$KANDEV_LIVE_DB" \
  ".backup '/private/backup/location/kandev.db.before-prompt-update'"

sqlite3 -readonly /private/backup/location/kandev.db.before-prompt-update \
  "PRAGMA integrity_check;"
```

The backup can be large and may take several minutes. Wait for the command to
finish and for any destination journal to disappear before treating it as
valid. A full disaster-recovery copy also needs the matching `master.key`, which
must remain secret and must never be committed. For a prompt-only rollback,
retain the private Markdown export as well.

### 2. Put the requested replacement in its mirror file

Review exact Unicode characters, Markdown, blank lines, and the final newline.
Write the prompt body to `custom_prompts/<prompt-name>.md` in the `main`
worktree. Using this file avoids breaking SQL on apostrophes or shell
interpolation and makes the deployed text reviewable. Resolve it to a trusted
absolute path before passing it to SQLite.

### 3. Apply one transactional row update

Create a private SQL file with the discovered prompt ID and the absolute prompt
file path:

```sql
.bail on
BEGIN IMMEDIATE;

UPDATE custom_prompts
SET content = trim(
        CAST(readfile('/absolute/main-worktree/custom_prompts/workstep-prompt.md') AS TEXT),
        char(9) || char(10) || char(13) || ' '
    ),
    updated_at = CURRENT_TIMESTAMP
WHERE id = '<discovered-prompt-id>';

SELECT 'rows_updated=' || changes();
COMMIT;
```

Then run it against the verified live database:

```bash
sqlite3 "$KANDEV_LIVE_DB" ".read /absolute/private/path/update-prompt.sql"
```

The result must be `rows_updated=1`. Zero means the target was not found or an
idempotence condition declined the change; more than one means the SQL was not
properly scoped. Stop and investigate either result instead of broadening the
UPDATE.

Do not interpolate a multi-line prompt directly into a shell command. Do not
use `UPDATE custom_prompts SET content=...` without an exact `WHERE id=...`.

## Verify and hand off

Read metadata and content back from the live database, confirm the reference
scope again, and validate the database:

```bash
sqlite3 -readonly "$KANDEV_LIVE_DB" \
  "SELECT id, name, length(content) AS chars, updated_at
   FROM custom_prompts WHERE id = '<discovered-prompt-id>';
   PRAGMA integrity_check;"

sqlite3 -noheader -readonly "$KANDEV_LIVE_DB" \
  "SELECT content FROM custom_prompts WHERE id = '<discovered-prompt-id>';"
```

Verify semantic byte equality with the mirror after trimming the Markdown
file's conventional final newline:

```bash
sqlite3 -noheader -readonly "$KANDEV_LIVE_DB" \
  "SELECT content = trim(
       CAST(readfile('/absolute/main-worktree/custom_prompts/workstep-prompt.md') AS TEXT),
       char(9) || char(10) || char(13) || ' '
   )
   FROM custom_prompts WHERE id = '<discovered-prompt-id>';"
```

The result must be `1`.

Check the running container and HTTP endpoint without restarting solely for the
prompt update. Report:

- prompt name and discovered ID;
- workflows/steps affected;
- backup and private export locations;
- exact verification result, including `integrity_check=ok`;
- Kandev health; and
- the timing limitation that future composed turns receive the change while a
  turn already in progress does not.

Finally, review the diff, commit the mirror and runbook changes on `main`, and
push them:

```bash
git diff --check
git diff -- custom_prompts/
git add custom_prompts/ CUSTOM-PROMPTS.md AGENTS.md CLAUDE.md
git commit -m "Document and mirror Kandev custom prompts"
git push origin main
```

Adjust the staged documentation paths to what actually changed, but never use a
broad staging command that sweeps in unrelated work. Confirm the pushed commit
is reachable from `origin/main` before reporting completion.

## Rollback principle

For a prompt-only error, restore the previous content in the mirror and to the
same prompt row through the API or another one-row transaction, then repeat
verification, commit the rollback, and push `main`. Do not replace the entire
live database merely to undo prompt wording: a full-file restore would also
roll back unrelated tasks, comments, sessions, and settings created since the
backup.

Only perform a full database restore under an explicit incident-recovery plan
with Kandev stopped, a verified backup, the matching `master.key`, and clear
acceptance of the broader data rollback.
