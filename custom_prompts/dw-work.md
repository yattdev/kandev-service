[WORK PHASE]
Implement the task following the approved plan.

@tools_discovery_submodule
Required for this phase (locate via tool search before STEP 0; do not guess names or signatures):
- The task-plan tools (e.g. `get_task_plan_kandev`, `update_task_plan_kandev`)
- The workflow-steps listing tool (e.g. `list_workflow_steps_kandev`)
- The task-movement tool (e.g. `move_task_kandev`)
- The task-flagging tool (e.g. `flag_task_kandev`) and the question tool (e.g. `ask_user_question_kandev`) — for STOP CONDITIONS
The submodule-specific tools (blocker queries, sibling-repo subtask creation) are discovered inside STEP 2 only when needed.

────────────────────────────────────────────────────────────────────────
EXECUTION CHECKLIST (restate this list as your task list before acting)
────────────────────────────────────────────────────────────────────────
0. Create the task list (this list).
1. Retrieve and acknowledge the plan.
2. Submodule dependency gate — if blocked, STOP here.
3. Decide whether this task needs a test instance; if yes, provision and
   start this task's isolated environment (record either outcome in the plan).
4. Implement via TDD, one behavior at a time.
5. Acceptance check — verify every acceptance criterion from the plan.
6. Commit only YOUR task changes.
7. Advance to Review.

Do each step in order — each step feeds the next. Do not skip ahead. Each
step lists a "Done when:" gate you must satisfy before advancing. The GIT
SAFETY rules and STOP CONDITIONS below apply throughout every step.

RE-ENTRY: this phase can be re-entered (e.g. after a submodule blocker
resolves). On re-entry, retrieve the plan and your prior task list state
first; steps whose "Done when" gate already holds (e.g. a provisioned,
healthy environment from a previous run — verify health, don't assume)
are verified and reused, not redone. STEP 2 is the exception: it runs in
full on EVERY entry.
────────────────────────────────────────────────────────────────────────

GIT SAFETY (read before running any git command)
- NEVER run `git checkout -- .`, `git checkout .`, `git reset --hard`, `git clean -fd`, or `git stash --include-untracked`. These wipe uncommitted work.
- When reverting files touched by formatters/linters, ALWAYS pass explicit paths (e.g. `git checkout -- path/to/file path/to/dir/`). Never use `.` or unscoped globs.
- Treat any uncommitted changes you did not make as intentional user work — leave them in place. Do not revert, stash, or overwrite them.
- SUBMODULE RULE: NEVER edit files inside a submodule's own directory as part of this task. Any change required inside a submodule MUST go through the subtask flow in STEP 2. This task may only ever bump the submodule's pointer (the commit it is checked out to) after that subtask's blocker is resolved. STEP 2 and STEP 4 reference this as "the SUBMODULE RULE".

STOP CONDITIONS (apply throughout — check at every step, not only at the end)
Stop implementing when any of these occurs:
- A blocker: missing dependency, unclear requirement, or a contradiction between the plan and the codebase.
- A fix requiring an architectural change not in the plan (new DB table, new service layer, switching libraries) — the plan is the contract; renegotiating it is the author's call.
- The isolated environment is REQUIRED (per STEP 3-PRE) but cannot be provisioned, started, or made reachable from the HOST and the LAN (STEP 3).
- 3 failed fix attempts on the same issue — stop and question the approach rather than attempt a 4th variation.
- A submodule bump that cannot be verified (STEP 2e).
When stopping, NEVER stop silently, and follow the flag-then-ask ordering: FIRST call the task-flagging tool (e.g. `flag_task_kandev`) so the board reflects the pause, THEN call the question tool (e.g. `ask_user_question_kandev`) with your question — in that order, because asking ends your turn. Include: which step you were in, what you tried (commands/tool calls), and the full error output. On resume, follow the RE-ENTRY note above.
Exception: the STEP 2e submodule wait is NOT a stop condition — it is an expected, self-resolving pause with its own no-flag rule.

STEP 0: CREATE A TASK LIST
Create a task list mirroring the EXECUTION CHECKLIST above (use your todo/task tracking tool), including the STEP 2 submodule gate. Mark each item in_progress when you begin it and completed when you finish.
Done when: the task list exists with all 8 items (0–7) tracked.

STEP 1: RETRIEVE THE PLAN
- Retrieve the task plan using the task-plan tool (e.g. `get_task_plan_kandev`) with the task_id from the session context.
- Review it in full: Acceptance Criteria, File Map (with submodule annotations), Implementation Steps, Testing Strategy, Submodule Dependencies — including any edits the user made after the Spec phase saved it. User edits override the original plan.
- Acknowledge the plan and any user modifications before proceeding.
Done when: you have restated the plan's scope, its acceptance criteria count, and noted any user edits.

STEP 2: SUBMODULE DEPENDENCY GATE (MANDATORY — run on EVERY entry to this phase, before STEP 3 or any code)

Why every entry: this phase can be re-entered after a submodule subtask closes (it messages this task directly). Re-verifying blocker state on every entry self-heals even if a notification is missed.

2a. EARLY EXIT — check for a `.gitmodules` file at the repo root.
    - If it does NOT exist: this project has no submodules. Skip 2b–2e entirely and go to STEP 3.
    - If it exists: continue to TOOL DISCOVERY, then 2b–2e.

TOOL DISCOVERY (only reached if `.gitmodules` exists): the tools to (i) query this task's blocker/blocked-by relationships and (ii) create a sibling-repo subtask with a blocker relationship may not be pre-loaded. Before calling either, use your tool-search capability to find them — search by capability (e.g. "task blocker relationship", "related tasks blocked by", "create subtask sibling repository"), NOT by the placeholder names below. `get_related_tasks_kandev` and `create_task_kandev` describe the capability needed, not guaranteed literal tool names — resolve them via tool search first. If the search turns up nothing plausible, that is a STOP CONDITION (flag, then ask) — do not improvise a workaround.

2b. Query this task's current blocker relationships (via the resolved tool), with this task's task_id, filtered to blocker/blocked-by tasks.
    - Any blocker task not yet at its Close step is UNRESOLVED.
    - If the query fails unexpectedly (tool error): that is a STOP CONDITION — do not guess at blocker state.

2c. Compare the planned scope (STEP 1's File Map) against the paths in `.gitmodules`. Find any submodule path that needs changes but has NO corresponding blocker task recorded in the plan's "Submodule Dependencies" section.
    - For each such newly identified path, create a blocker subtask per 2d.

2d. Creating a subtask for an affected submodule:
    - Gather the specific context from the parent plan: what needs to change in that submodule, and why.
    - Create the subtask via the resolved tool, targeting ONLY that submodule's own repository as a sibling-repo subtask — not the superproject. It follows the full standard workflow (Backlog → ... → Close) for that repository as an independent task, with this task as its parent (parent_id: "self", workspace_mode: "new_workspace", per the resolved tool's schema).
    - Establish this task as blocked by that subtask (native blocker relationship — same call or a follow-up, whichever the resolved tool exposes).
    - Record the submodule path and new subtask_id in this task's plan via the plan-update tool (e.g. `update_task_plan_kandev`), appended under "Submodule Dependencies". This note is for human visibility and Review-phase verification only — the real gate in 2e always comes from the live blocker query in 2b, never from this note (the note can go stale; the relationship cannot).

2e. Pause or proceed:
    - If ANY blocker is UNRESOLVED (per 2b): stay at this Work step. Do NOT provision an environment (STEP 3) and do NOT implement (STEP 4). End this phase run here — do NOT call the task-movement tool.
      · Do NOT call the task-flagging tool. An unresolved submodule blocker is an expected, self-resolving wait, not a decision needing a human — flagging it creates false-alarm noise.
    - If ALL blockers are resolved (Close), or there were none: for each resolved submodule dependency, bump its reference in the superproject:
      1. Resolve the submodule's default branch LOCALLY from inside the submodule: `git symbolic-ref refs/remotes/origin/HEAD` (fallback: `git remote show origin | grep 'HEAD branch'`). Do not assume `main`.
      2. `cd <submodule_path> && git fetch origin && git checkout <submodule_default_branch> && git pull origin <submodule_default_branch> && cd -`
      3. VERIFY the bump actually contains the subtask's work before committing it: read the subtask (via the task-reading tool) for its recorded branch/PR; confirm that branch is merged into the submodule's default (`git -C <submodule_path> branch -r --merged origin/<default_branch> | grep <subtask_branch>`), or that the change it was created for is demonstrably present. A subtask at Close whose work is NOT on the submodule's remote default branch means the pointer would advance without the needed change — that is a STOP CONDITION (flag, then ask); do not bump blindly.
      4. `git add <submodule_path>` (the gitlink only — never files inside the path)
      5. `git commit -m "chore: bump <submodule_path> for task <task_id> (subtask <subtask_id>)"`
Done when: `.gitmodules` is absent, OR all blockers are resolved and every submodule pointer bump is verified and committed. If blocked, this phase run ends here.

STEP 3: DECIDE INSTANCE REQUIREMENT, THEN PROVISION THIS TASK'S ISOLATED ENVIRONMENT

3-PRE. INSTANCE REQUIREMENT DECISION (mechanical — do this FIRST, before provisioning anything):
Not every task needs a running test instance, and provisioning one that nothing will use wastes ports, containers, DB copies, and Close-phase teardown work. But the bar for "not needed" is HIGH — decide from the plan's Acceptance Criteria, not from convenience:
- REQUIRED if ANY of the following holds:
  · any Acceptance Criterion involves exercising the running application — an HTTP request, a UI flow, an authenticated session, a rendered page, a websocket, a webhook;
  · the change touches runtime server behavior: routes/endpoints, middleware, UI components, templates, background jobs, queue workers, schedulers, or migrations that must be exercised against realistic data;
  · verification needs a command executed against a LIVE service or seeded DB (e.g. an artisan/manage.py/rake/console command, a worker run, a data backfill). "Backend-only" does NOT mean "no instance": a command that boots the framework or reads/writes the app's DB needs the isolated environment just as much as a UI change does;
  · the author will plausibly want to manually test the behavior in the Human-QA phase.
- NOT REQUIRED only if the task fits one of these categories AND every Acceptance Criterion is verifiable by tests/static checks alone, with no live service and no seeded DB: documentation-only; CI/pipeline config; pure library/refactor changes fully covered by unit tests; standalone scripts/tooling testable directly with no app runtime.
- Borderline or unsure → REQUIRED. A wasted instance costs a teardown; a missing instance stalls QA and the author's testing window.
RECORD the decision in the task plan via the plan-update tool under "Environment":
- If NOT REQUIRED: write `Environment: NOT REQUIRED — <reason> — verify via: <exact test command(s)>`, skip items 1–5 below entirely, and go to STEP 4. The QA and Human-QA phases read this line — an undocumented absence of an instance looks like a broken WORK phase, so this line is mandatory, not optional.
- If REQUIRED: continue with items 1–5.

Goal (when REQUIRED): stand up a task-specific run environment INSIDE this worktree so (a) you can run real end-to-end tests against the task's changes, and (b) the author and the QA phase can later test this task in isolation. It must never collide with the main environment or any other task's environment, it must be reproducible, and it MUST be reachable from the HOST machine AND from other machines on the same LAN — the author tests from the host or, just as often, from ANOTHER host on the same LAN (another workstation, a phone, a tablet). An instance reachable only from inside your container, or only via `localhost` on the host, is NOT acceptable and does not satisfy this step. See APPENDIX A for kandev/Docker path mapping.
Checklist:
[ ] 1. Detect stack and run method. Do NOT assume web (Django/Laravel) — may be Android/Kotlin, other, containerized (Docker/Compose) or bare host. Determine:
       - the build/run command(s),
       - whether it exposes a long-running server/service or produces a runnable app/artifact,
       - Docker/Compose vs. bare host.
       PREFER running the instance as a Docker/Compose container over a bare process: containers started via the Docker daemon publish ports on the HOST, whereas a bare process started inside your own container is only reachable from inside it and is invisible to the author. Only fall back to a bare process if the stack genuinely cannot be containerized, and then confirm host AND LAN reachability explicitly in item 4 — if it cannot be made reachable from both, that is a STOP CONDITION.
[ ] 2. Allocate non-conflicting resources:
       - unique ports (web/app/debug/etc.) — verify each chosen port is actually free ON THE HOST (`ss -tlnp | grep <port>`) before binding,
       - publish ports explicitly (`-p <host_port>:<container_port>` / Compose `ports:`) and bind services to `0.0.0.0` inside the container, not `127.0.0.1`, or the published port will be unreachable. The HOST-side binding must also be `0.0.0.0` (the default for `-p <port>:<port>`) — NEVER publish as `-p 127.0.0.1:<port>:<port>`, which makes the instance invisible to the LAN,
       - APPLICATION-LEVEL LAN GUARDS: if the framework restricts hosts (e.g. Django `ALLOWED_HOSTS`, Rails host authorization, Laravel trusted hosts, Vite/webpack dev-server `--host`/`allowedHosts`), add the host's LAN IP (and `0.0.0.0`/wildcard where applicable) to THIS worktree's override config so a request from another machine is not rejected with a 400/403 that localhost never sees,
       - unique Compose project name, container names, network, volumes (if containerized) — include the task slug/ID in every name so the Close phase can match ownership by task ID,
       - isolated config/env scoped to this worktree — copy the project's env/config, then override ONLY what's needed (ports, hostnames, DB name, cache/queue/storage paths). Use HOST paths (per APPENDIX A) in any bind mounts, since the containers run on the host's Docker daemon.
       Never edit the main environment's config; keep all overrides inside the worktree.
[ ] 3. REQUEST AND RESTORE THE COORDINATOR'S REALISTIC PROJECT TEST DATA (if the project uses a DB). This task gets its OWN dedicated DB/container/volume. An empty database is acceptable only when the acceptance scenario is explicitly the empty state; otherwise it fails provisioning.
       3a. Before creating data, message the parent task or workspace Coordinator through the task-service escalation chain. Include: full task UUID; repository/project identity; DB engine/version and dump format; required scenario; desired task-local inbox path; and whether Work/Human-QA needs a persistent instance. If live task data proves the workspace has no Coordinator, flag `COORDINATOR_UNAVAILABLE` once through the visible Human channel with the same bounded request. Continue independent implementation while waiting. If the realistic-data gate is required, record `Environment: DATA REQUESTED` and do not fabricate mock data to claim completion.
       3b. The Coordinator owns `projects/<workspace>/<project>/TEST_DATA.md` and must deliver only within this workspace. Require fixture ID/version, source timestamp/class, bytes, SHA-256, engine/format compatibility, reviewed `how-to-load.sh`/`how-to-start.sh` or exact commands, and expected schema/count/login/feature assertions. A catalogued sanitized fixture is preferred; brokered development dump, repository fixture, migrations/seeders, or a reviewed scenario overlay are Coordinator-controlled fallbacks.
       3c. Verify SHA-256 before use. Recreate an empty task-owned destination, import with the supplied recipe without `--force` or error suppression, preserve the real client exit status and sanitized first error, then apply task-branch migrations if needed. Never overlay-retry a partial restore: recreate only the task destination first.
       3d. Verify mechanically: destination isolation; DB integrity; expected schema; representative table counts; a working test login; and the task-specific feature path. Record `TEST_DATA_RECEIPT` with full task/project identity, fixture ID/hash/source time, destination/container/volume and engine, clean-destination proof, import exit/stderr, assertions, exact HEAD/runtime, and artifact deletion or bounded-retention disposition.
       Never inspect/export unrelated or main containers with raw Docker, write/restart/reconfigure shared data, mount live source volumes, copy raw live DB files, cross workspaces, expose credentials/master keys, or stage/commit dumps. Leave the verified task-owned runtime/data available for later QA; a workflow-step change alone never requires a new dump.
[ ] 4. Start this task's own instance from the worktree and verify it is up AND reachable from the HOST and the LAN:
       - Resolve the host's LAN IP mechanically: `ip -4 addr show` / `hostname -I` — pick the LAN interface address (e.g. 192.168.x.x / 10.x.x.x), NOT the Docker bridge (172.17.x.x) and NOT 127.0.0.1.
       - HOST check: a successful request against `http://127.0.0.1:<host_port>` (or the host-mapped address). A check that only passes from inside a container does not count.
       - LAN check: a successful request against `http://<host_lan_ip>:<host_port>` — this exercises the same interface another machine on the LAN will hit, and is the closest verification you can run without a second machine. Also confirm the listener mechanically: `ss -tlnp | grep <port>` must show `0.0.0.0:<port>` or `*:<port>`, NOT `127.0.0.1:<port>`.
       - If the LAN check fails while localhost passes, diagnose in this order: (i) port published as `127.0.0.1:` (fix the `-p`/`ports:` mapping), (ii) service bound to 127.0.0.1 inside the container (fix the bind address), (iii) application host guard rejecting the LAN hostname (fix per item 2's LAN GUARDS), (iv) host firewall blocking the port — changing host firewall rules is the author's call: that is a STOP CONDITION, reported with the exact rule/output that blocks.
       - non-server (e.g. Android/Kotlin): build and verify the runnable artifact (successful build + run on emulator/device, or the instrumented/integration test target); host+LAN reachability applies to any debug/dev server it exposes.
       If it does not come up cleanly or is not reachable from BOTH host and LAN, that is a STOP CONDITION — resolve or escalate before implementing.
[ ] 5. RECORD the environment in the task plan via the plan-update tool (e.g. `update_task_plan_kandev`), under an "Environment" section: the LAN URL (`http://<host_lan_ip>:<port>` — the address the author opens from another machine) AND the localhost URL, DB name/connection, WHICH data source was used (3a/3b/3c/3d) with the spot-checked row counts and the test login credentials, container/compose project names, PIDs where applicable, and the exact start/stop commands. This recorded section is the source of truth that the QA phase (to pick the right instance) and the Close phase (to know what to tear down) read later — an unrecorded resource is an orphaned resource.
Leave this environment RUNNING. Do NOT tear it down at the end of this phase — it is how the author and later phases test the task.
Done when: EITHER the plan records `Environment: NOT REQUIRED` with its reason and verification commands, OR the instance is verified up, reachable from HOST AND LAN, seeded with data (row counts spot-checked, login verified), AND the Environment section is saved in the task plan.

STEP 4: IMPLEMENT (TDD)
Work through the plan's Implementation Steps in their stated order, applying the plan's Testing Strategy. For each behavior:
1. Write a failing test asserting the expected behavior.
2. Run it — confirm it fails with the expected assertion error (not a compile error).
3. Write the minimum code to make it pass.
4. Run it — confirm it passes.
5. Refactor while keeping tests green.
6. Commit the change (explicit paths, descriptive Conventional Commit message, e.g. `feat: reject empty carts with 422`).

- Run all tests and end-to-end checks against THIS task's isolated environment (STEP 3), never the main environment or shared DB. If STEP 3-PRE recorded NOT REQUIRED but implementation reveals you DO need a live instance or seeded DB to verify a behavior, the 3-PRE decision was wrong: return to STEP 3, provision per items 1–5, and REPLACE the plan's `Environment: NOT REQUIRED` line with the full Environment section — never test against the main environment as a shortcut.
- Build incrementally — one behavior at a time, tests passing at every step.
- Follow existing codebase conventions (naming, patterns, file organization).
- You may update the plan mid-implementation via the plan-update tool; material deviations from the plan (different files than the File Map, changed approach) must be recorded there, not just made silently — Review compares against the plan.
- If you discover a need to modify a file inside a submodule path NOT already covered by a STEP 2 blocker subtask: STOP immediately and return to STEP 2 to create the subtask before continuing (the SUBMODULE RULE). If its blocker is unresolved, this phase run ends per 2e.
Done when: all planned behaviors are implemented with tests green.

STEP 5: ACCEPTANCE CHECK
Walk the plan's Acceptance Criteria one by one. For EACH criterion:
- Execute it literally against the isolated environment (the exact request, input, or flow the criterion states) and record PASS/FAIL with the command used. When the plan records `Environment: NOT REQUIRED`, execute each criterion via its recorded verification command(s) instead — the literal-execution rule still applies.
- A failing criterion means STEP 4 is not done — return there. Do not reinterpret or weaken a criterion to make it pass; if a criterion turns out to be wrong or unachievable as written, that is a STOP CONDITION (flag, then ask).
Record the completed pass/fail list in the task plan via the plan-update tool (an "Acceptance Results" note) — QA re-verifies against the same criteria and should see what you claim passed.
Done when: every acceptance criterion is recorded PASS.

STEP 6: COMMIT YOUR OWN CHANGES
This step is unconditional:
- Run `git status` to see what changed.
- Stage and commit every file YOU created or modified for this task, using explicit paths (see GIT SAFETY) — never `git add .`. Use descriptive messages.
- Do NOT commit environment-local artifacts (copied env files, DB dumps/clones, container volumes) unless the project tracks them. Keep the isolated environment out of the task branch's history.
- Any uncommitted/untracked changes you did not make are intentional user work — leave them as-is. Aim not for an absolutely clean tree, but for none of YOUR task edits being left uncommitted.
Done when: all of your task edits are committed; the environment (when one was provisioned) is still running.

STEP 7: ADVANCE TO REVIEW
- Call the workflow-steps listing tool (e.g. `list_workflow_steps_kandev`) to retrieve the steps for THIS task's workflow, and identify the ID of its "Review" step from the results. Do NOT hardcode or guess IDs, and do NOT reuse a step ID from a different workflow.
- With the isolated environment still running (when one was provisioned), call the task-movement tool (e.g. `move_task_kandev`) with:
  - task_id: the task_id from the session context
  - workflow_step_id: the resolved Review step ID
- Confirm the move succeeded, then output a short handoff summary: behaviors implemented, acceptance results, the environment's LAN and localhost URLs with test credentials (or the `Environment: NOT REQUIRED` line with its verification commands), and any plan deviations recorded.
Done when: the move has succeeded and the handoff summary is output.

────────────────────────────────────────────────────────────────────────
APPENDIX A — kandev / Docker path mapping (reference for STEP 3)
────────────────────────────────────────────────────────────────────────
kandev (inside container)          | Host filesystem (Docker sees)
/data/tasks/<slug>/<worktree>      | /home/ayattara/Code/tasks/<slug>/<worktree>
/data/home/Code/<repo>             | /home/ayattara/Code/<repo>

Why: kandev mounts /home/ayattara/.local/share/kandev → /data, and a host
symlink exists: ~/Code/tasks → ~/.local/share/kandev/tasks.
Docker consequence: always use /home/ayattara/Code/tasks/... (NOT
/data/tasks/...) as the bind-mount path in docker-compose volumes.
This session's task workspace:
  /home/ayattara/Code/tasks/<current-task-slug>/<worktree-name>
which is the same directory as
  /data/tasks/<current-task-slug>/<worktree-name>
inside kandev.
