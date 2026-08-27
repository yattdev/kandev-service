# Versioned Kandev custom prompts

Each Markdown file in this directory mirrors one live Kandev saved prompt:

```text
<saved-prompt-name>.md
```

The file body must contain only the prompt text so it can be synchronized to
the `custom_prompts.content` database field without stripping metadata.

An owner-requested add/update must always be performed from `main` and include
all of these outcomes:

1. Create or update this Markdown mirror and review it for secrets.
2. Discover the live prompt row and every workflow/step reference.
3. Back up the live value/database outside the repository.
4. Synchronize the identified live row through the authenticated API or the
   tightly scoped SQLite fallback in `CUSTOM-PROMPTS.md`.
5. Verify the live content equals the trimmed Markdown file and run the health
   checks.
6. Commit and push the mirror on `main`.

Never commit databases, `master.key`, transient exports, credentials, or
backups here. Read the repository-root `CUSTOM-PROMPTS.md` before any live
change.
