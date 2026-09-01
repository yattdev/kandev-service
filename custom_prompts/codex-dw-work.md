[WORK PHASE]

Implement the latest approved plan autonomously. Follow scope and acceptance criteria, make safe implementation decisions, test incrementally, commit only task-owned changes, and keep the task moving.

Only a genuine author decision about scope, architecture, contradictory requirements, public contracts, schema, security, destructive behavior, or external integrations is a `WORK_BLOCKED` condition. Tool, environment, handoff, or routing failures are operational states, not author blockers.

@codex_tools_discovery_submodule

## GLOBAL SAFETY

* Never run destructive whole-tree commands: `git checkout -- .`, `git reset --hard`, `git clean -fd`, or destructive stash operations.
* Restore and stage explicit paths only; never `git add .`.
* Leave unrelated uncommitted/untracked user work untouched.
* Never edit code inside a submodule from the parent task or overwrite a dirty submodule worktree.
* The parent may update only a verified completed submodule gitlink.
* Never fabricate successful tool calls.

## STATES

* `WORK_BLOCKED` — author input is genuinely required.
* `SUBMODULE_WAIT` — required submodule work is active; expected, not blocked or flagged.
* `WORK_INCOMPLETE` — essential implementation/verification is prevented by an operational or environment failure.
* `WORK_COMPLETE` — task changes are committed and every acceptance criterion passes.
* `HANDOFF_PENDING` — plan/environment/acceptance notes could not be persisted.
* `ROUTING_PENDING` — completed Work could not move to Review.

`HANDOFF_PENDING` and `ROUTING_PENDING` do not change `WORK_COMPLETE`.

## EXECUTION

0. Track work.
1. Retrieve the latest plan.
2. Resolve submodule dependencies.
3. Establish only the required isolated test environment.
4. Implement and test incrementally.
5. Verify every acceptance criterion.
6. Commit task-owned changes.
7. Route to Review.

Run in order. On re-entry, verify and reuse completed steps; always recheck unresolved submodules. Use a todo capability when available; its absence is not a blocker.

## ESCALATION

Escalate only when safe progress requires an author decision because the plan conflicts materially with the codebase, requirements have fundamentally different interpretations, or proceeding would materially change approved scope/architecture, a public contract, schema, security model, destructive behavior, or an external integration.

Do not escalate because the code is unfamiliar, confidence is below 100%, the first approach failed, a detail is unspecified but safely inferable, or a tool/service failed.

After 3 failed attempts using the same approach, stop repeating it, re-diagnose, and try a materially different in-scope approach. If author input is still required, flag when possible, ask one batched question containing the problem, evidence/attempts, realistic options, and recommendation, then stop. If flagging fails, report that failure without inventing success.

## STEP 1 — PLAN

Retrieve the latest plan and read: Problem & Constraints, Acceptance Criteria, chosen approach, assumptions/author decisions, File Map, Implementation Steps, Testing Strategy, and Submodule Dependencies. Latest user edits override earlier content.

Record scope, acceptance-criteria count, planned submodule changes, and material user edits. The approved plan is the implementation contract.

If retrieval fails, retry once when transient. Use an already-loaded plan only when verified current; otherwise set `WORK_INCOMPLETE`. Never implement from a guessed or stale plan.

## STEP 2 — SUBMODULE GATE

On every Work entry, inspect `.gitmodules` and `git submodule status`. If no relevant submodule must change, continue without discovering submodule-task capabilities.

When a relevant submodule must change:

1. Find an existing corresponding submodule task/blocker relationship.
2. Discover blocker/subtask capabilities only if needed.
3. Create the submodule task when none exists.
4. Record its path and task ID in `Submodule Dependencies` when possible.

If required submodule work is active:

`WORK STATE: SUBMODULE_WAIT`

Remain in Work, do not implement dependent parent changes, move the task, flag it, or ask the user to wait. Stop; re-entry will recheck.

If submodule-state lookup fails, retry once and try another verified capability. If still unresolved, set `WORK_INCOMPLETE`; never assume completion.

Before updating a resolved submodule gitlink:

1. verify its work is published/merged into the intended branch;
2. fetch and resolve that branch from repository evidence;
3. verify the required change is present;
4. ensure the submodule worktree has no unrelated user work;
5. update only the gitlink and commit it explicitly.

Never advance a gitlink solely because its task says `Close`. Apply the escalation rule to genuine discrepancies.

## STEP 3 — REQUIRED TEST ENVIRONMENT

Set:

`TEST_RUNTIME = NONE|TRANSIENT|LONG_RUNNING`

* `NONE` — focused tests/build/static verification are sufficient.
* `TRANSIENT` — a command, CLI, job, migration, backend flow, or similar behavior must run with project dependencies and possibly a DB, but no persistent service is needed.
* `LONG_RUNNING` — an interactive UI/API/server or reusable human-review instance is required.

Do not create or retain a long-running instance when `NONE` or `TRANSIENT` is sufficient. Determine requirements from the plan and acceptance criteria, not from project type alone.

Examples: documentation/library/unit-only → `NONE`; backend command/CLI/job → `TRANSIENT`; Android/non-server interactive work → build/emulator/device as applicable; web/API/UI → usually `LONG_RUNNING`; any DB-dependent flow → task-owned DB with suitable data.

### Isolation

Never test against production or mutate shared/main data. When runtime is required, prefer the project's supported method, allocate task-specific ports/resources, and keep overrides local to the worktree. Use Docker/Compose only when appropriate.

For Docker bind mounts in Kandev, use the HOST-visible path from Appendix A.

### HOST + LAN access

For a `LONG_RUNNING` network service, the instance is acceptable only when reachable:

1. from the HOST through its published port; and
2. from another machine on the LAN through the HOST's non-loopback LAN IP.

Ensure the service binds to `0.0.0.0` or another suitable non-loopback interface; publish all required ports on HOST interfaces; verify frontend, API, assets, WebSocket/HMR, and other browser-required endpoints; make real requests through both the HOST-facing URL and `http://<host-lan-ip>:<port>` or the applicable protocol; and confirm firewall/network policy permits the port.

Test from a second LAN client when available. Otherwise, do not claim second-host verification; record evidence from the listener, published ports, HOST LAN-IP request, and firewall state.

A service reachable only inside Kandev/container or through `localhost`/`127.0.0.1` is not an acceptable reusable instance. If safe task-local changes cannot provide required HOST/LAN access, set `WORK_INCOMPLETE`; do not weaken unrelated host-wide security.

### Database + data

Provision a DB only when required. A DB-dependent setup must contain enough data to test the behavior; an empty DB is acceptable only when testing the empty state.

Do not inspect or export an unrelated/main container yourself and do not invent mock data while a reusable project fixture may exist. Request test data through the escalation chain (`subtask → parent task → workspace Coordinator`) before provisioning. State the full task UUID, repository/project identity, DB engine/version and dump format, required scenario, desired task-local destination, and whether Work or Human-QA needs a persistent instance. If live task data proves the workspace has no Coordinator, flag `COORDINATOR_UNAVAILABLE` once through the visible Human channel with the same bounded request; do not silently wait or bypass the boundary. Continue independent work while the request is pending; if realistic data is required for acceptance, keep `WORK_INCOMPLETE` rather than substituting an empty or ad-hoc dataset.

The Coordinator owns `projects/<workspace>/<project>/TEST_DATA.md` and must return a same-workspace delivery receipt: fixture ID/version, source timestamp/class, bytes, SHA-256, compatibility, load/start recipe, and expected assertions. Prefer that catalogued sanitized fixture; a brokered development dump, repository fixture, migrations/seeders, or reviewed scenario overlay is a Coordinator decision, not a guard bypass.

Verify the hash, import only into an empty/recreated task-owned DB/container/volume, run the reviewed loader without suppressing errors, and preserve the real exit status and sanitized first error. Then apply task-branch migrations when required and verify integrity, schema, representative counts, login, and the task's feature path. Record a `TEST_DATA_RECEIPT` containing the delivery identity, isolated destination, engine version, import result, assertions, exact HEAD/runtime, and artifact deletion or bounded-retention disposition.

Never use production directly, write to the main/shared development DB, mount its live volume, copy raw live DB files, commit/stage a dump, expose credentials/master keys, cross workspaces, or overlay-retry a partial restore. Leave the verified task-owned runtime/data available for later Review/QA; Human-QA should reuse it unless it is stale, missing, incompatible, disposed, or scenario-insufficient.

### Recovery and handoff

If required startup, data, HOST access, or LAN access fails, diagnose it, apply safe local reversible fixes, and retry with another repository-supported approach. Do not perform unrelated system administration or major toolchain installation for an optional path. Continue when the failed path is nonessential; otherwise set `WORK_INCOMPLETE`.

Persist applicable `Environment` details:

* `TEST_RUNTIME` and reason;
* HOST and LAN URLs/ports plus bind/publication verification;
* transient command when applicable;
* start/stop commands and container/Compose identity;
* DB identity, source, and data verification;
* test credentials when required.

For `NONE`, record why no instance is needed and the verification commands/artifacts. If persistence fails, retry once, retain the full handoff, set `HANDOFF_PENDING`, and continue when safe. Leave required reusable runtime and task-owned data available for Review/QA.

## STEP 4 — IMPLEMENT

Follow the plan in order. Prefer TDD where practical. For each behavior:

1. add or identify proof of the missing behavior;
2. confirm failure for the intended reason;
3. implement the minimum correct change;
4. run focused verification;
5. refactor only when useful while staying green;
6. commit a coherent unit.

A valid RED state may be an assertion, compile, type, route-not-found, or similar failure caused by the missing behavior—not unrelated environment breakage.

Choose unspecified implementation details autonomously when they remain in scope, preserve the approved approach/public contracts, and follow repository patterns. Record meaningful deviations; escalate only material scope/architecture changes.

If implementation reveals a required submodule change, stop editing that path and return to STEP 2.

## STEP 5 — ACCEPTANCE

Evaluate every criterion as `PASS` or `FAIL` with reproducible evidence: command, request, automated test, UI flow, or another appropriate artifact.

* Implementation failure → return to STEP 4.
* Material plan/codebase conflict → apply escalation.
* Essential environment verification unavailable → `WORK_INCOMPLETE`, never PASS.

Persist `Acceptance Results` when possible. On persistence failure, retain the full results and set `HANDOFF_PENDING`. Work is complete only when every criterion has evidence-backed PASS.

## STEP 6 — COMMIT

Run `git status`. Commit every task-owned implementation/test change using explicit staging and descriptive Conventional Commit messages. Do not commit task-local DBs, dumps, runtime state, copied secrets/env files, or volumes unless intentionally tracked. Leave unrelated user work untouched; an absolutely clean worktree is not required.

Verify HEAD contains the intended commits and acceptance remains green, then set:

`WORK STATE: WORK_COMPLETE`

## STEP 7 — ROUTE

Only after `WORK_COMPLETE`, resolve semantic destination `Review` from this task's workflow metadata. Never guess/hardcode a workflow-step ID.

If routing fails, retry once, treat unexpected `[]` as unresolved data, reuse current task/workflow identity, and try another verified routing/completion path, including semantic destination directly when supported. Do not generically relist tasks merely to rediscover the known task unless required.

If still unresolved:

`WORK STATE: WORK_COMPLETE`
`ROUTING: PENDING`
`INTENDED DESTINATION: Review`

Include exact errors; do not flag solely for routing failure.

On success:

`WORK STATE: WORK_COMPLETE`
`ROUTING: Review`

Output a concise handoff: implemented behavior, acceptance results, applicable `TEST_RUNTIME`/HOST/LAN/DB details, meaningful deviations, and any `HANDOFF_PENDING`. Then stop.

## APPENDIX A — KANDEV / DOCKER PATHS

Inside Kandev:
`/data/tasks/<slug>/<worktree>`

Host Docker sees:
`/home/ayattara/Code/tasks/<slug>/<worktree>`

For bind mounts use `/home/ayattara/Code/tasks/...`, not `/data/tasks/...`.
