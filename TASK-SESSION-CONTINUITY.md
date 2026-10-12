# Exact task source continuity recovery

Version: `d28-source-continuity-recovery-v1`.
Support request: `15388c11-6cc9-456c-846f-b503a17bf177`.
This is a bounded recovery design, not an installed capability or acceptance
receipt. It does not authorize a launch, session restoration, or writer handoff.

## Observed boundary

Read-only Support diagnostics verified the Coordinator and target task belong
to workspace `2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`. The target is
`d28be44c-136f-47af-af5d-faa7e6381818`.

The durable session rows for Source
`d2b0b80c-7716-476f-a4bf-bbcd59988d4f` and steward
`3dc52cfc-d888-41ed-924a-cbe0de77af3b` are absent. Their exact retained
execution bindings are respectively `98fbeabc-5542-40ba-9d87-228ce3ddf370`
and `adea40f6-b704-4579-be95-4856810e7099`. Both execution rows have state
`failed`, `pid=0`, and `local_pid=0`. These are database facts, not physical
revocation receipts.

The task currently has primary `833d9d08-69b8-4855-9ff8-6b05c59a1647`,
`WAITING_FOR_INPUT`, queue incarnation
`6c04347c-e446-4a57-85e6-9da5b8a9ccfc`, and terminal
`8ada5072-e4da-4a74-a2a3-d225da76fa06`. The primary's retained execution
`0995af42-9a9d-4d54-bb30-783d3c1a93a8` is `stopped`, with zero PIDs.
All 34 task execution rows are terminal in this database snapshot. This does
not establish absence of untracked or detached writers.

For each missing session, messages, turns, commit records, attributed Git
snapshots, step history, and queued messages have zero rows. Live schema
defines cascading deletion for messages, turns, commits, and step history;
Git snapshots use `SET NULL` for a removed session. No unattributed snapshots
remain in this task's current environment. Neither deletion actor nor original
queue incarnation can be reconstructed from these facts. A bounded retained
container-log query for 20:24–20:31 UTC returned no exact-session events; it
cannot prove that no lifecycle operation occurred.

The supplied frozen branch/head, local eleven commits, plan and archived gate
evidence were not independently opened or executed by Support. No target
worktree was accessed. They remain caller assertions awaiting guarded
acceptance, rather than newly certified preservation facts.

## Missing supported contract

The installed conversation/session lookup reads durable session rows. It has
no deleted-session restoration or ownership-census operation. The existing
agentctl process-list route requires internal authenticated runtime access and
returns process data; it is not an exact-task, sanitized ownership receipt.
An empty manager index is insufficient to certify detached descendants absent.
The broker's temporary-operator-token mutation path is excluded: this request
does not permit token minting or credential copying. No preissued callable
authenticated ownership surface is available to this Support caller.

Automatic approval review rejected a proposed `/proc` environment census as
broader process inspection than this request permits. It was not executed or
retried indirectly. SQL restoration, new session creation, runtime retirement,
and projecting terminal execution rows as revocation are excluded alternatives.

## Bounded implementation route

Extend the existing backend lifecycle service and authenticated MCP transport;
do not add a standalone helper or expose raw process/host controls. Reuse the
server-owned task/session principal and existing internal runtime clients.
Never manufacture, extract, or export an authentication credential.

The proposed read-only action is `reconcile_task_execution_ownership_kandev`.
Its name is reserved for this design and is **not currently callable**.
Authenticate the current caller and incarnation, validate the canonical
Coordinator repository/backlink, same workspace, exact direct-child task and
registered task environment/repository. A task's own authenticated caller may
inspect only that task. Historical sessions must be bound by retained,
server-authenticated execution/task ownership evidence, never by supplied UUIDs
alone. Wrong scope or missing bindings yields denial or `UNKNOWN`.

For the exact environment, collect an immutable read view from the lifecycle
execution store, durable execution ledger, process manager and managed runtime
closure ledger. Each launch must be bound to session incarnation, execution ID,
environment ownership generation, runtime incarnation, process start time and
descendant ownership. Include provider processes, background commands and
workspace/shell runners with write access. A tombstone must certify the exact
launch and every owned descendant closed or its enforced write authority
revoked. A validated managed runtime-incarnation destruction receipt may provide
closure only for launches positively bound to that destroyed runtime. A missing
row, missing PID, failed state, empty index, API 404, timeout, or inaccessible
runtime is never closure proof.

Retained command/gate records are reported by server identity, state and digest,
without command text, output, DSNs, paths or credentials. Missing historical
records stay explicitly missing. External immutable reports may establish a
gate result after exact identity/digest validation, but cannot establish process
closure. Capture FIFO entry IDs/order and content digests, counters, queue
incarnation, task/source ownership generation and repository binding digests.
Do not reset, dispose, replay or repair them during this read.

Take a bounded consistent snapshot and recheck ownership generation, runtime
incarnation and caller binding before publishing an append-only audit receipt.
On concurrent launch, foreign writer, PID reuse, changing command activity or
unclassified access, return `UNKNOWN` or `CONFLICT`. Return `SOLE_ELIGIBLE`
only with complete, positively bound runtime coverage and one eligible owner.
It is a read observation with an expiry/generation fence, not a write lease.
Subsequent normal writer admission must compare that generation under the
existing lifecycle lock and reject any intervening change.

Deleted Source `d2b0…` cannot be resumed under this design. Restoration would
need an authenticated original session/incarnation snapshot and a supported
transaction preserving transcript, queue and ownership evidence. If absent,
the action must report `RESTORATION_UNAVAILABLE`. It may evaluate existing
`833d…` as a prospective sole owner only after complete closure evidence for
historical and other task executions. It must not promote, launch, or send a
prompt to that session.

## Root acceptance after capability review and installation

This is the inert request body for the proposed authenticated action:

```json
{
  "task_id": "d28be44c-136f-47af-af5d-faa7e6381818",
  "expected_owner_session_id": "833d9d08-69b8-4855-9ff8-6b05c59a1647",
  "historical_bindings": [
    {"session_id":"d2b0b80c-7716-476f-a4bf-bbcd59988d4f","execution_id":"98fbeabc-5542-40ba-9d87-228ce3ddf370"},
    {"session_id":"3dc52cfc-d888-41ed-924a-cbe0de77af3b","execution_id":"adea40f6-b704-4579-be95-4856810e7099"}
  ],
  "expected_plan_id": "d75c71b8-298b-40f9-a5e6-92965465d815",
  "expected_plan_version": "192984",
  "expected_branch": "feature/fence-cancelled-task-9cs",
  "expected_head": "e1f5c3bd38569175c2645906f5200c2d429a4670"
}
```

Caller task/session/incarnation and workspace must be injected from server
authentication, never accepted as caller substitutions. Root runs this read
itself. Root verifies the exact task/repository/environment, frozen branch/head,
immutable archived report digests, eleven local commits, complete process and
command coverage, historical closure bindings, no conflicting writer,
unchanged FIFO/counters, and receipt audit/generation. The current result must
remain `UNKNOWN`; no executable acceptance command is issued because this
action has not been implemented or installed and physical closure is unproved.

Required regression cases for implementation: wrong caller/workspace/task;
deleted session with surviving provider or command; missing incarnation;
PID reuse; untracked descendant; runtime/API error; foreign writer; concurrent
launch; forged tombstone; mutable archive; legitimate own verification turn;
unchanged FIFO/counters; exhaustive positive closure plus existing sole owner;
and idempotent repeat reads without launch, teardown or metadata repair.

## Smallest next operation and preservation guarantee

The reviewed lifecycle owner must provide a preissued, exact-task read surface
with the original incarnation/closure evidence, or authorize implementation of
the bounded backend-owned action above. That action still cannot turn missing
historical closure into proof. If complete evidence is unavailable, a separate
exactly bound recovery/physical-fencing decision is needed; this request does
not grant teardown or creation of another writer. The existing Human approval
for product implementation is preserved and does not need to be repeated.

Support changed only this design and its nonsecret evidence receipt. No task
source, branch, worktree, database row, provider, runtime, helper, question,
candidate authority, FIFO, counter, workflow or deployment was changed.
