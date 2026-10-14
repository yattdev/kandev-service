# Exact-target retained retirement: 05d2f692

Support request `05d2f692-811d-4856-8586-b0cdf06ea3cf` remains BLOCKED for capability
provisioning. No task was mutated, moved, archived, deleted, cleaned or restarted.
No source implementation or generic API/database write was performed. The Human
retirement directive is not being reopened for identical approval.

## Bounded live evidence and authorization cause

Both named checkouts were inspected. Deployment remains on main, unrelated
tracked/untracked user files are unchanged, and the current source checkout was
not edited. Read-only exact-target/workspace queries and source inspection used
reviewed Support host diagnostics, without granting raw host/socket access to an
agent. This is a local platform authorization gap, not an upstream-only diagnosis.

- Caller task/session: `a68df3ae-aaf5-4591-a46d-9d73db62e46d` /
  `13d8c011-6e49-40ef-80e9-2f1445296d06`.
- Exact target: `96e27238-8b7d-476a-8c70-b8da0abae935`, workspace
  `2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`.
- Target parent is empty. State is `SCHEDULING`, lane is Human-QA
  `814573a3-f2a3-4f42-8706-4f2997401fa6`; it is not archived.
- Target metadata has no `terminal_retention` key. No pending-action keys were
  present in that metadata. Sessions are four COMPLETED and one FAILED.
- Workflow is `90f322ed-2159-424d-96e7-c2ad05668b8e`; Done is
  `30ae45bd-e99e-455a-8eb7-10e7a038200f`. Done auto-archives after 72 hours and has
  an `auto_start_agent` on-enter action.

The deployed-lineage MCP `handleUpdateTask` checks the server-derived caller and
requires `target.ParentID == principal.CallerTaskID` plus matching workspace for
any `terminal_retention` update. A parentless target cannot pass this check.
The check does not consult a Coordinator role, native Human instruction or an
operator-installed exact-target grant. It therefore refuses even though task
reach and a retirement instruction are supplied. The refusal itself is fail-closed.

The existing broker dispatch and workspace-registration mechanisms contain no
terminal-retention delegation operation. Filesystem/workspace write authority
cannot override that compiled backend parent check. Generic metadata updates
preserve the server-owned hold instead of allowing one to be injected; ordinary
creation strips it. Parent impersonation, reparenting, direct SQL and privileged
proxy mutation are neither needed nor authorized and were not attempted.

The cited capability source `924f3f41-ea93-4708-b394-c6ca3e929298` was unavailable
in a task metadata lookup restricted to this workspace. No foreign row or plan
body was accessed. This does not establish whether it exists elsewhere or
identify the root cause of its reported INTERNAL_ERROR; it is not an available
authorization route within this request's boundary.

## Existing Human evidence, preserved

Exact native message `dd1b09d2-c951-50d4-8df4-56d0c1014807` was found on the
specified caller task/session, author `user`, created
2026-10-14T01:43:09.978833976Z. Its content SHA-256 is
`bd755825d1aa9af1a8ec39a1d98f3b9a5b6c57af52a74897b02a5ded3c43e721`;
it names the exact target UUID. No message body was printed or copied.

Its single recorded admission resolves to a native user admission for the same
task/session and current incarnation, but the admitted content differs from the
stored transcript content. This check alone cannot establish byte-exact native
provenance for an executable grant. It is not evidence that Human intent is
invalid. A trusted implementation must classify the existing native envelope /
transcript transformation and authenticate that same instruction before issuing
an exact grant; it must not infer permission from author labels or task mentions.
Both original records remain intact. No new or fabricated instruction is proposed.

## Retention visibility and no-cleanup semantics

The normal task DTO projects `metadata.terminal_retention` through
`PublicTaskMetadata`; that key is not redacted. A successful supported setter can
therefore be read back by Root through its normal task read capability.

Existing guards enforce an actual true hold at several cleanup boundaries:

- Auto-archive skips held tasks.
- Direct archive rejects a held task before gathering/stopping/cleaning resources.
- Archive cascade rejects a held root.
- Generic metadata replacement cannot remove the hold.

A hold is not proof of Git/archive completeness and does not suppress all workflow
actions. The supplied archive remains reported as 102522880 bytes with SHA-256
`0d1329c66f3a250588982d972b9782e101694ddf11ff9a04654bdceb67f78466`.
Support did not open it or inspect Git/worktree contents. Its .git-pointer and
consumer-completeness limitation remains **UNKNOWN**, exactly as supplied.
No cleanup can be justified from that archive claim.

Done's auto-start is avoidable through the already supported one-shot move
options: `skip_step_prompt:true`, no instructions, `reset_context:false`.
`workflow/move.OverlayStep` drops the auto-start without changing durable workflow
configuration. For a COMPLETED task with retention held and an empty effective
on-enter/prompt, `silentRetainedTerminalEntry` bypasses profile-session preparation.
This is the supported retained/silent entry path; a plain Done move is not the
acceptance recipe for this workflow. Support has not invoked either move.

## Smallest platform correction and remaining scope decision

No existing exact-target grant hook was found. The request forbids source edits
and runtime restart, so implementation/installation of that missing hook is not
a safe in-scope action. General Support checkout writability does not override
those specific constraints. Do not weaken the direct-parent rule for every
same-workspace agent or give a generic Coordinator override.

The smallest operator decision is a narrowly scoped exception to implement and
activate an authenticated **enable-retention-only** grant for this caller,
workspace and target, bound to the preserved Human message and an authenticated
provenance disposition. Leave task movement and clearing retention outside the
grant. Keep the existing direct-parent path intact. The grant must be backend /
operator owned, immutable to task agents, auditable and revocable, with normal
live caller/session/workspace checks on each call and explicit idempotent readback.
Revoking setter authority must not itself clear an already established hold.

Required acceptance for that implementation:

1. The exact validated caller enables true on this target, and a repeat returns
   the same provenance/held state without other mutations.
2. Different caller/session/workspace/target, unproven Human envelope, stale or
   revoked grant and `terminal_retention:false` fail closed. No grant allows task
   movement, archive/cleanup, provider execution or generic metadata writes.
3. Root can read `metadata.terminal_retention:true`; tests prove direct/automatic/
   cascade archive denial and metadata-protection behavior on the same hold.
4. Synthetic retained/silent Done entry preserves worktree/resources and session
   count/identities without any agent launch or source/Git cleanup.

Any installation requiring a production recreate needs a separate concrete
approval and a hotfix-preserving backend/agentctl superset. Inventory the then-live
provenance before replacement. Use only `scripts/kandev-safe-deploy --build`,
HTTP-200 acceptance, required deployment tests and verified automatic rollback.
No deployment/restart or new broad authority is authorized by this proposal.

## Root acceptance recipe, gated on a real capability receipt

This is a future acceptance recipe, not a claim that capability provisioning
succeeded. Root must remain out of Done until the first two checks succeed.

1. Receive a non-secret exact grant receipt identifying caller/session/workspace,
   target, Human evidence hash, enable-only scope, authorization disposition and
   supported set/read/revoke operations. No secret or impersonated parent identity
   belongs in the receipt.
2. Root invokes the supported exact-target enable operation. Read the original
   task back and require `metadata.terminal_retention:true`, unchanged parent,
   lane/state, existing five terminal sessions and no pending actions. An error,
   missing field or unrelated task response is not success.
3. Root alone may then use the existing `move_task` with this task ID, workflow
   `90f322ed-2159-424d-96e7-c2ad05668b8e`, step
   `30ae45bd-e99e-455a-8eb7-10e7a038200f`, and
   `entry_options:{"skip_step_prompt":true,"reset_context":false}`. Omit prompt
   and instructions. Require actual applied/readback disposition, COMPLETED/Done,
   the retained true hold, unchanged session identities/count and no new execution.
4. Verify the existing resource/worktree/ref/artifact inventory is retained. Do
   not test archive denial by invoking a live destructive operation or waiting
   72 hours; use bounded trusted guard evidence and synthetic acceptance instead.
   Record Git/consumer completeness UNKNOWN until independently established.

The following existing synthetic regressions passed under the race detector on
restored live-source lineage (source worktree `80fdc4ce072ced98c6d72996f02e2c578d64dd82`):

- `TestUpdateTaskTerminalRetentionRequiresDirectParent` (handlers, 1.245s).
- `TestTerminalRetentionPreventsArchiveCleanupUntilCleared` (service, 1.306s).
- `TestSilentRetainedTerminalMoveDoesNotCreateSessionOrReopenTask`
  (orchestrator, 1.229s).

These checks validate existing guards and the conditional silent-entry path.
They do not establish that an exact-target grant is installed or that this live
target has a hold. No new implementation or deployment test success is claimed.

Support ran only those isolated existing regression checks;
no live setter or move was called. No usable grant was issued. No source edit,
proxy task mutation, database write, archive/cleanup, parent change, broad trust
change, credential access or runtime restart occurred.
