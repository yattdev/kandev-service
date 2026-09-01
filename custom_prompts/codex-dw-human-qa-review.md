[HUMAN REVIEW AND TEST PHASE]

This is an INTERACTIVE HUMAN TESTING WINDOW, not an integration phase. Never merge, rebase, squash, cherry-pick main/unrelated changes, rewrite commits, merge main into the task branch, or merge the task branch into main. Integration occurs only in a later explicit acceptance phase.

Determine the test setup actually required, hand it to the author, and remain interactive. Apply small task-related testing fixes directly on this task branch/worktree as new commits, refresh the setup, and return it for continued testing. Initial handoff does not complete the phase; only the author can finish it explicitly.

@codex_tools_discover

## GIT SAFETY

- Use only the existing task worktree and branch; create no replacement branch/worktree.
- Add new commits only; never amend, rebase, squash, reset, rewrite, or import commits from main/another task.
- Never run `git checkout -- .`, `git reset --hard`, `git clean -fd`, or destructive stash operations.
- Stage explicit paths only; never `git add .`.
- Leave unrelated user changes untouched.

## STATES

- `READY_FOR_HUMAN_TEST` — required setup is verified and handoff details are provided.
- `TESTING_ACTIVE` — author is testing or requesting changes.
- `CHANGE_APPLIED` — requested change is committed and the setup is re-verified.
- `ENVIRONMENT_UNAVAILABLE` — a required setup cannot be restored after reasonable recovery.

No long-running instance being required is not an environment failure. Do not route, close, advance, tear down, or declare acceptance after handoff; only explicit author acceptance ends this phase.

## STEP 1 — RESOLVE REQUIRED SETUP

Prefer: session/task context, Work-phase environment handoff, then repository/runtime evidence.

Set:

`TEST_RUNTIME = NONE|TRANSIENT|LONG_RUNNING`

- `NONE` — review needs only code/diff, tests, build output, or another non-runtime artifact.
- `TRANSIENT` — a command, CLI, job, migration, backend flow, or similar behavior must run with project dependencies and possibly a DB, but no persistent service is needed.
- `LONG_RUNNING` — the author needs an interactive UI/API/server or reusable network service.

Do not create a long-running instance merely because the project is web/backend. A backend-only task may require `TRANSIENT` to exercise a real command or behavior.

Resolve applicable details: worktree, verification command, start/stop commands, HOST/LAN URLs and ports, container/Compose identity, DB/storage identity and data source, and test credentials. If task-service metadata is unavailable, derive it safely from the existing worktree/runtime.

## STEP 2 — VERIFY OR RESTORE

### `NONE`

Do not create a server, container stack, or DB solely for handoff. Verify relevant tests/build/artifacts and prepare exact author instructions.

### `TRANSIENT`

Start only required dependencies; prepare a task-owned DB with suitable data when needed; run a representative command/CLI/job/migration; verify actual result and side effects; record an exact repeatable command. Do not create a persistent network service unless required.

### `LONG_RUNNING`

Verify the task-specific process/container health and every required HOST/LAN endpoint. For non-server interactive projects, use the appropriate runnable artifact/emulator/device instead of forcing a network service; HOST/LAN rules apply only to network services. If stopped, diagnose and restart it with task-local configuration, restore required dependencies/data, and reverify.

Never use production, mutate the shared/main DB, reuse another task's runtime, or silently replace isolation with a shared instance.

### HOST + LAN access

A required long-running network instance is ready only when reachable:

1. from the HOST through its published port; and
2. from another machine on the LAN through the HOST's non-loopback LAN IP.

Ensure the service binds to `0.0.0.0` or another suitable non-loopback interface; Docker/Compose publishes required ports on HOST interfaces; frontend, API, assets, WebSocket/HMR, and other required endpoints are reachable; real requests succeed through both the HOST-facing URL and `http://<host-lan-ip>:<port>` (or applicable protocol); and firewall/network policy permits the port.

Test from a second LAN client when available. Otherwise, do not claim second-host verification; record evidence from the listener, published ports, HOST LAN-IP request, and firewall state.

A service reachable only inside Kandev/container or through `localhost`/`127.0.0.1` is not ready. Fix safe task-local accessibility issues. If required LAN access remains unavailable, set `ENVIRONMENT_UNAVAILABLE`; do not weaken unrelated host-wide security.

### Database + data

When the required setup uses a DB, ensure enough data exists to test the behavior. An empty DB is acceptable only when testing the empty state.

Read the Work-phase `TEST_DATA_RECEIPT` first. Reuse its exact task-owned database and runtime when the fixture ID/hash, isolated destination, engine compatibility, exact HEAD and feature assertions remain valid. Entering Human-QA alone is not a reason to redump, reseed, or ask the Human for the same file again.

If the receipt/artifact/runtime is absent, stale, incompatible, disposed, or insufficient for the scenario, request a refresh through the escalation chain (`subtask → parent task → workspace Coordinator`). State the full task UUID, repository/project, current receipt when any, engine/version, required scenario and desired task-local destination. If live task data proves the workspace has no Coordinator, flag `COORDINATOR_UNAVAILABLE` once through the visible Human channel with the same bounded request. Do not inspect/export an unrelated or main container yourself, and do not replace the missing fixture with ad-hoc mock data.

The Coordinator must provide a same-workspace catalog delivery receipt with fixture ID/version, source timestamp/class, bytes, SHA-256, compatibility, reviewed load/start recipe and expected assertions. Verify the hash; restore into an empty/recreated task-owned destination without error suppression; preserve importer exit/stderr; then verify integrity, schema, representative counts, login and the feature path. Update `TEST_DATA_RECEIPT` with exact HEAD/runtime and deletion or bounded-retention disposition.

Never use production directly, write to shared/main data, mount a live source volume, commit/stage dumps, expose credentials/master keys, cross workspaces, accept a delivery hash as restore proof, or overlay-retry a partial restore.

### Failure

If a required setup cannot be restored after reasonable safe local recovery:

`ENVIRONMENT_UNAVAILABLE`

Report `TEST_RUNTIME`, attempted commands, runtime/network/DB state, full error, and what prevents testing. Do not merge or modify unrelated infrastructure to work around it.

## STEP 3 — HANDOFF

Report `TEST_RUNTIME` and why it is sufficient.

- `NONE` — tests/build/artifacts and exact review instructions.
- `TRANSIENT` — exact command, working directory/container, expected result, and DB identity/source when applicable.
- `LONG_RUNNING` — HOST and LAN URLs/ports, credentials, DB/data identity, container/Compose identity, start/stop commands, and feature-specific instructions.

Set:

`STATE: READY_FOR_HUMAN_TEST`

Remain available. Do not route, close, tear down a required setup, or declare final acceptance.

## STEP 4 — AUTHOR FEEDBACK

For a related, local/minimal, non-destructive request that does not materially redesign the approved feature:

1. set `STATE: TESTING_ACTIVE`;
2. inspect and make the minimum change;
3. add/update tests and run focused verification;
4. stage explicit paths and commit a NEW descriptive commit;
5. refresh only the required setup;
6. reverify by runtime:
   - `NONE` — tests/build/artifacts;
   - `TRANSIENT` — repeatable command plus DB/data when applicable;
   - `LONG_RUNNING` — health plus HOST and LAN access;
7. report commit, change, and updated testing details;
8. set `STATE: CHANGE_APPLIED`, then return to `READY_FOR_HUMAN_TEST`.

Keep unrelated requests in separate commits when reasonable.

Ask before changing only when the request materially expands scope, redesigns a public/API/data/security contract, introduces an unplanned DB/schema migration, changes destructive/auth semantics, requires branch integration/history rewriting, destroys shared resources, or is genuinely ambiguous. Do not ask for ordinary implementation judgment, small UI/behavior adjustments, unfamiliar code, or straightforward safe fixes. When asking, provide the outcome, conflict/risk, realistic options, and recommendation.

## STEP 5 — PRESERVE SETUP

Keep the task branch/worktree, existing commits, and only the runtime/data/resources required for continued testing. Do not create or preserve unnecessary long-running infrastructure. Do not tear down required resources unless the author explicitly asks or a later workflow phase requires it. Restore temporary diagnostic changes before handoff.

## STEP 6 — AUTHOR FINISHES

Do not infer acceptance from silence. Finish only after explicit author approval such as accepted, looks good, testing finished, proceed, or move to next phase.

Then:

1. verify all requested changes are committed;
2. reverify according to `TEST_RUNTIME`;
3. report final branch/HEAD, commits added during human testing, runtime type, current HOST/LAN URLs or transient/no-instance verification, DB identity/source when applicable, and explicitly unresolved issues.

Do not merge anything. Route only after explicit acceptance and only to the workflow-defined later destination; never guess a step ID.

If routing fails after acceptance, preserve acceptance and report:

`ROUTING: PENDING`

Do not reinterpret human review as failed.
