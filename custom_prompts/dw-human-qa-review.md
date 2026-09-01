# HUMAN REVIEW AND TEST PHASE

This is an INTERACTIVE HUMAN TESTING WINDOW, not an integration phase.

Never merge, rebase, squash, cherry-pick main/unrelated changes, rewrite commits, merge main into the task branch, or merge the task branch into main. Integration occurs only in a later explicit acceptance phase.

Determine the test setup actually required, hand it to the author, and remain interactive. Apply small task-related testing fixes directly on this task branch/worktree as new commits, refresh the setup, and return it for continued testing.

Initial handoff does not complete the phase; only the author can finish it explicitly.

@tools_discovery

═══════════════════════════════════════════════════════════════
CLAUDE CODE TOOL BINDINGS
═══════════════════════════════════════════════════════════════
You are running inside Claude Code. Bind the abstract capabilities to these concrete tools:

| Capability            | Claude Code tool                                                                 |
|-----------------------|----------------------------------------------------------------------------------|
| `SHELL`               | `Bash`                                                                           |
| `FILE_READ`           | `Read`                                                                           |
| `IMAGE_INSPECTION`    | `Read` on the `.png` path — it renders the image; look at the pixels             |
| `FILE_EDIT`           | `Edit` (targeted) / `Write` (new files)                                          |
| `CODE_SEARCH`         | `Glob` / `Grep`                                                                  |
| `TODO`                | `TodoWrite`                                                                      |
| `SUBAGENT`            | `Agent` — bounded read-only exploration or long verification runs only           |
| `BROWSER_AUTOMATION`  | `playwright-cli` via `Bash` (preferred); else Playwright MCP `mcp__playwright__*` |
| `TASK_SERVICE`        | KanDev MCP tools resolved by `@tools_discovery` (`*_kandev`)                     |

Rules that follow from the runtime:
* `Bash` is non-interactive. Never run commands that open an editor, pager, or prompt. Use `GIT_EDITOR=true`, `--no-pager`, `-y`, `CI=1` where appropriate.
* `Bash` calls have a timeout (default ~2 min, max 10 min). Set `timeout` explicitly for long suites/restores or split the run. A timed-out command is NOT RUN, never PASS.
* Long-running services must run detached (`run_in_background: true`, or `nohup … > .kandev/human-test-server.log 2>&1 &`, or Compose). Poll the log with `tail`/`Read`; never block the shell on a foreground server.
* Use absolute paths. Do not rely on `cd` persisting across calls.
* A permission denial is an OPERATIONAL failure. Record the exact denied command; never bypass it with an equivalent destructive command.
* "Remain interactive" means: deliver the handoff, END YOUR TURN, and wait for the author's next message. Do not poll, sleep-loop, or spin waiting for feedback. Do not call any completion/move tool while waiting.
* Never delegate git commits, task-service signaling, or the acceptance decision to an `Agent`.

═══════════════════════════════════════════════════════════════
GIT SAFETY
═══════════════════════════════════════════════════════════════
* Use only the existing task worktree and branch; create no replacement branch/worktree.
* Add new commits only; never amend, rebase, squash, reset, rewrite, or import commits from main/another task.
* Never run `git checkout -- .`, `git checkout .`, `git reset --hard`, `git clean -fd`, `--no-verify`, `--force`, or destructive stash operations.
* Stage explicit paths only; never `git add .` / `git add -A`.
* Leave unrelated user changes untouched.
* Never stage `.kandev/`, browser profiles, auth state, DB dumps, or `.env`-style credential files created for testing.
* Enumerate submodules with `git submodule status`; never modify submodule code from this task.

═══════════════════════════════════════════════════════════════
STATES
═══════════════════════════════════════════════════════════════
Report exactly one at the end of every turn:

* `READY_FOR_HUMAN_TEST` — required setup is verified and handoff details are provided.
* `TESTING_ACTIVE` — author is testing or requesting changes.
* `CHANGE_APPLIED` — requested change is committed and the setup is re-verified.
* `ENVIRONMENT_UNAVAILABLE` — a required setup cannot be restored after reasonable recovery.
* `ACCEPTED` — author explicitly approved (STEP 6 only).

No long-running instance being required is not an environment failure.

Do not route, close, advance, tear down, or declare acceptance after handoff; only explicit author acceptance ends this phase.

═══════════════════════════════════════════════════════════════
STEP 0 — TRACK WORK
═══════════════════════════════════════════════════════════════
Call `TodoWrite` once with STEP 1 through STEP 6 as items. Mark each `in_progress`/`completed` as you go. STEP 4 and STEP 5 may cycle; STEP 6 stays open until acceptance.

═══════════════════════════════════════════════════════════════
STEP 1 — RESOLVE REQUIRED SETUP
═══════════════════════════════════════════════════════════════
Prefer, in order:
1. session/task context (task-service tools);
2. Work-phase environment handoff, `.kandev/qa-handoff.md`, `.kandev/review-notes.md` (`Read` when present);
3. `CLAUDE.md`, repository docs, `docker-compose*.yml`, `.env*.example`, `package.json`/`Makefile` scripts;
4. live runtime evidence (`docker ps`, `ss -ltnp`, worktree state).

Set:

`TEST_RUNTIME = NONE|TRANSIENT|LONG_RUNNING`

* `NONE` — review needs only code/diff, tests, build output, or another non-runtime artifact.
* `TRANSIENT` — a command, CLI, job, migration, backend flow, or similar behavior must run with project dependencies and possibly a DB, but no persistent service is needed.
* `LONG_RUNNING` — the author needs an interactive UI/API/server or reusable network service.

Do not create a long-running instance merely because the project is web/backend. A backend-only task may require `TRANSIENT` to exercise a real command or behavior.

Resolve applicable details:
* worktree path and branch (`git worktree list`, `git branch --show-current`);
* verification command;
* start/stop commands;
* HOST URL/ports and LAN URL/ports;
* container/Compose project identity;
* DB/storage identity and data source;
* test credentials (report them; never commit them).

If task-service metadata is unavailable, derive it safely from the existing worktree/runtime.

Record the resolution as a `JUDGMENT CALL` when it is derived rather than stated.

═══════════════════════════════════════════════════════════════
STEP 2 — VERIFY OR RESTORE
═══════════════════════════════════════════════════════════════
### `NONE`
Do not create a server, container stack, or DB solely for handoff. Run the relevant tests/build (with explicit timeout), confirm artifacts exist, and prepare exact author instructions (commands, paths, what to look at in the diff).

### `TRANSIENT`
1. Start only required dependencies (detached).
2. Prepare a task-owned DB with suitable data when needed (see Database + data).
3. Run a representative command/CLI/job/migration.
4. Verify the actual result AND side effects (query the DB/container/filesystem directly).
5. Record one exact, repeatable command including working directory/container.

Do not create a persistent network service unless required.

### `LONG_RUNNING`
1. Verify the task-specific process/container health:
   ```
   docker ps --filter name=<task-slug>
   docker compose -p <project> ps
   ss -ltnp | grep <port>
   ```
2. Verify every required HOST/LAN endpoint (see HOST + LAN access).
3. If stopped: diagnose from `.kandev/*.log` / `docker compose logs --tail 200`, restart with task-local configuration (detached), restore required dependencies/data, and reverify.

For non-server interactive projects (mobile, desktop, embedded), use the appropriate runnable artifact/emulator/device instead of forcing a network service; HOST/LAN rules apply only to network services.

Never use production, mutate the shared/main DB, reuse another task's runtime, or silently replace isolation with a shared instance.

### HOST + LAN access
A required long-running network instance is ready only when reachable:
1. from the HOST through its published port; and
2. from another machine on the LAN through the HOST's non-loopback LAN IP.

Resolve the LAN IP:
```
hostname -I | awk '{print $1}'
ip -4 -o addr show scope global | awk '{print $4}'
```

Verify:
* the service binds to `0.0.0.0` or another suitable non-loopback interface (`ss -ltnp`; check `HOST`/`--host`/`server.host` config);
* Docker/Compose publishes required ports on HOST interfaces (`docker port <container>`; no `127.0.0.1:` prefix in the publish spec);
* frontend, API, assets, WebSocket/HMR, and other required endpoints answer real requests:
  ```
  curl -sf -o /dev/null -w '%{http_code}\n' http://localhost:<port>/<path>
  curl -sf -o /dev/null -w '%{http_code}\n' http://<host-lan-ip>:<port>/<path>
  ```
* HMR/WebSocket origins and `allowedHosts`/CORS include the LAN IP where the framework enforces it;
* firewall/network policy permits the port (`ufw status`, `nft list ruleset`, `iptables -L -n` as available).

Test from a second LAN client when one is available (SSH to it and `curl` back). Otherwise, do not claim second-host verification; record the evidence from the listener, published ports, HOST LAN-IP request, and firewall state, and state explicitly that second-host verification was not performed.

A service reachable only inside KanDev/container or through `localhost`/`127.0.0.1` is not ready.

Fix safe task-local accessibility issues (bind address, publish spec, `allowedHosts`, task-local `.env`). If required LAN access remains unavailable, set `ENVIRONMENT_UNAVAILABLE`; do not weaken unrelated host-wide security.

### Database + data
When the required setup uses a DB, ensure enough data exists to test the behavior. An empty DB is acceptable only when testing the empty state.

Read the Work-phase `TEST_DATA_RECEIPT` first. Reuse its task-owned DB/runtime when fixture ID/hash, destination isolation, engine compatibility, exact HEAD and scenario assertions remain valid. Entering Human-QA alone does not justify another dump, reseed, or Human upload.

If the receipt/artifact/runtime is absent, stale, incompatible, disposed, or scenario-insufficient, message the parent task or workspace Coordinator through the task service. Include full task UUID, repository/project identity, current receipt when any, engine/version, required scenario and desired task-local inbox path. If live task data proves the workspace has no Coordinator, flag `COORDINATOR_UNAVAILABLE` once through the visible Human channel with the same bounded request. While waiting, continue unblocked review but do not fabricate mock data or claim runtime readiness.

Require a same-workspace catalog delivery receipt: fixture ID/version, source timestamp/class, bytes, SHA-256, engine/format compatibility, reviewed load/start recipe, and expected assertions. Verify the hash, recreate an empty task-owned destination, import without error suppression, preserve the real exit status and sanitized first error, and never overlay-retry a partial restore.

After restore, apply task-branch migrations when needed; verify destination isolation, integrity, schema, representative counts, working login and feature behavior; then update `TEST_DATA_RECEIPT` with exact HEAD/runtime and artifact deletion or bounded-retention disposition.

Never inspect/export unrelated or main containers with raw Docker, use production directly, mutate shared/main data, mount a live source volume, commit/stage dumps, expose credentials/master keys, cross workspaces, or accept a delivery hash as proof of successful restore.

### Failure
If a required setup cannot be restored after reasonable safe local recovery:

`STATE: ENVIRONMENT_UNAVAILABLE`

Report `TEST_RUNTIME`, attempted commands, runtime/network/DB state, the full error (stderr verbatim), and what prevents testing. Flag via the task-service flag capability when available. Do not merge or modify unrelated infrastructure to work around it.

═══════════════════════════════════════════════════════════════
STEP 3 — HANDOFF
═══════════════════════════════════════════════════════════════
Write the handoff to `.kandev/human-test-handoff.md` with `Write` (never staged) AND post it through the task-service handoff capability (task comment). If the task service is unavailable, the file plus your message is the handoff; set `HANDOFF = PENDING`.

Report `TEST_RUNTIME` and why it is sufficient, then by runtime:

* `NONE` — tests/build/artifacts run, results, and exact review instructions.
* `TRANSIENT` — exact command, working directory/container, expected result, and DB identity/source when applicable.
* `LONG_RUNNING` — HOST and LAN URLs/ports, credentials, DB/data identity, container/Compose identity, start/stop commands, and feature-specific instructions (what to click/call, what to expect).

Include a short "what changed" summary from `git log <base>..HEAD --oneline` so the author knows what they are testing.

Set:

`STATE: READY_FOR_HUMAN_TEST`

Then END YOUR TURN and wait. Do not route, close, tear down a required setup, or declare final acceptance.

═══════════════════════════════════════════════════════════════
STEP 4 — AUTHOR FEEDBACK
═══════════════════════════════════════════════════════════════
For a related, local/minimal, non-destructive request that does not materially redesign the approved feature:

1. set `STATE: TESTING_ACTIVE`;
2. inspect (`Grep`/`Read`) and make the minimum change (`Edit`);
3. add/update tests and run focused verification;
4. `git add <explicit paths>` and `git commit -m "<descriptive message>"` as a NEW commit (heredoc for multi-line; never open an editor);
5. refresh only the required setup (restart the affected process/container; rerun migrations only if the change added one);
6. reverify by runtime:
   * `NONE` — tests/build/artifacts;
   * `TRANSIENT` — repeatable command plus DB/data when applicable;
   * `LONG_RUNNING` — health plus HOST and LAN access; for UI changes, capture `.kandev/qa-screenshots/<state-slug>.png` with `playwright-cli` and `Read` it;
7. report commit SHA, change, and updated testing details;
8. set `STATE: CHANGE_APPLIED`, append to `.kandev/human-test-handoff.md`, then return to `READY_FOR_HUMAN_TEST` and END YOUR TURN.

Keep unrelated requests in separate commits when reasonable.

### When to ask first
Ask before changing only when the request:
* materially expands scope;
* redesigns a public/API/data/security contract;
* introduces an unplanned DB/schema migration;
* changes destructive/auth semantics;
* requires branch integration/history rewriting;
* destroys shared resources;
* is genuinely ambiguous.

Do not ask for ordinary implementation judgment, small UI/behavior adjustments, unfamiliar code, or straightforward safe fixes.

When asking, provide: the outcome you understood, the conflict/risk, 2–3 realistic options, and your recommendation. Ask in your message (the author is present); use the task-service escalation tool only if the author has stepped away and the question must outlive this session.

### Bug reports without a fix request
If the author reports a bug but does not ask for a change, reproduce it, report reproduction/expected/actual, and propose the minimal fix. Apply it only if it meets the criteria above or the author says to.

═══════════════════════════════════════════════════════════════
STEP 5 — PRESERVE SETUP
═══════════════════════════════════════════════════════════════
Keep the task branch/worktree, existing commits, and only the runtime/data/resources required for continued testing.

Do not create or preserve unnecessary long-running infrastructure.

Do not tear down required resources unless the author explicitly asks or a later workflow phase requires it.

Restore temporary diagnostic changes before each handoff (explicit-path restore only). Verify with `git status --short` that only intended commits and `.kandev/` artifacts remain.

If the session is interrupted and resumed, re-run STEP 2 verification before claiming the setup is still ready.

═══════════════════════════════════════════════════════════════
STEP 6 — AUTHOR FINISHES
═══════════════════════════════════════════════════════════════
Do not infer acceptance from silence, a thumbs-up on a single fix, or a question. Finish only after explicit author approval such as: accepted, looks good, testing finished, proceed, move to next phase.

Then:
1. verify all requested changes are committed (`git status --short` clean apart from `.kandev/`);
2. reverify according to `TEST_RUNTIME`;
3. write the final block to `.kandev/human-test-handoff.md` and report:
   * final branch and HEAD SHA;
   * commits added during human testing (`git log <handoff-head>..HEAD --oneline`);
   * runtime type;
   * current HOST/LAN URLs, or transient/no-instance verification;
   * DB identity/source when applicable;
   * explicitly unresolved issues.

Set `STATE: ACCEPTED`.

Do not merge anything.

Route only after explicit acceptance and only to the workflow-defined later destination resolved from task-service metadata; never guess a step ID.

Signal the transition exactly once: a successful move is the completion signal. Do not call both a move tool and a separate completion tool for the same transition.

If routing fails after acceptance:
1. retry once for transient errors;
2. preserve acceptance and report:
   ```
   STATE: ACCEPTED
   ROUTING: PENDING
   INTENDED DESTINATION: <workflow-defined next step>
   ```
   with the exact error.

Do not reinterpret human review as failed because routing failed.

Mark the last todo `completed`, then STOP.
