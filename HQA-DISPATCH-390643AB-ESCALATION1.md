# Exact HQA dispatch: escalation 1 capability audit

Request `390643ab-baa1-439b-9014-41410352bdf3` remains BLOCKED for a live repair.
This audit found and tested existing recovery primitives, narrowing the original
proposal. It did not invoke a launch, drain, replay, queue edit or runtime change.
[The original bounded failure evidence](HQA-DISPATCH-390643AB.md) remains intact.

## Host authority and checkout audit

Both named checkouts were inspected again. Reviewed Support host diagnostics are
available and were used successfully; this is not confusion with the task-facing
Docker guard. No privilege, credential or socket capability was granted to Root
or another task. Current source and deployment unrelated dirty/untracked files
remain unchanged. No new source worktree, code implementation or deployment was
created. The existing restored live-source worktree remains clean at
`80fdc4ce072ced98c6d72996f02e2c578d64dd82`.

One new read-only query was limited to the three supplied session IDs, their
registered task environment and non-secret executor bindings. It was not a status
poll of the message/turn. All three sessions bind the same environment
`e376dadd-cd2b-4c66-9be2-b110009aa178`. HQA has no executor row. The other supplied
sessions retain these rows:

| Session | Recorded execution | Status/runtime | Last seen |
| --- | --- | --- | --- |
| `8a0d2e01-9a22-44da-bbec-652902957cc8` | `0fae2c0e-89fb-49bc-a00e-300cbc45ab93` | ready / standalone | 2026-10-14T01:17:19.914701017Z |
| `ecadcc45-11d8-49a0-9650-9116435ed5c8` | `e9101bff-1146-4e07-a713-b59fcf8e083b` | ready / standalone | 2026-10-14T01:17:16.637694189Z |

Those durable records do not establish present process liveness or prove an
exclusive writer. No process was stopped or another session's record repurposed.
The original queue/turn/lane snapshot is the earlier 04:11:38Z evidence, not a
fresh claim from this query.

## Existing primitives that were checked

1. **`session.launch`, intent `start_created`:** despite its name, the implementation
   also accepts WAITING_FOR_INPUT for a prepared-session transition. It therefore
   must not be dismissed solely because HQA is WAITING. However, it launches a
   prompt, can use the task-description/workflow fallback, schedules task state,
   and has no public request fields binding the existing reservation/lease and
   accepted original queue ID. `skip_message_record` does not provide those
   ownership fences. Invoking it as a substitute risks a new independent prompt
   while the original durable entry remains eligible for later delivery. It is
   not an exact admitted-entry recovery operation.
2. **`session.launch`, intent `restore_workspace`:** this can create workspace-only
   agentctl infrastructure and persist an executor record without a model prompt.
   Its admission does not categorically require a terminal session. This is a
   potential component of a same-session correction, not automatically a safe
   complete repair. `EnsureWorkspaceExecutionForSession` may return an execution
   already attached to another session in the same task environment. The three
   actual sessions share that environment and the older two retain executor rows.
   Restore success alone is therefore not evidence of an exact HQA runtime or
   task-wide writer ownership. No such restore was called.
3. **`message.queue.drain`:** the identity-bound path validates task, session and
   incarnation, checks promptability and pending clarification, then reserves the
   FIFO head. Its repository can already reclaim an expired durable native-message
   lease by compare-and-swap and rejects a stale owner's acknowledgement. Thus the
   earlier stranded reservation does not necessarily need manual flag clearing or
   deletion. This narrows the first proposal: use the existing retaining-reserve
   mechanism when an exact runtime and writer have been safely established.
   The public drain request does not pin an expected entry/turn or atomically
   establish task-wide sole-writer ownership across the supplied sessions.
4. **Ordinary resume/fresh start:** unchanged findings apply. Resume reaches the
   missing-executor rejection; fresh start/runtime_retry can clear resume identity.
   New-session launch, reparenting, lane moves and forcing terminal state are not
   preservation-safe substitutes. No alternative was invoked experimentally.

The native WS actions exist, but no task-bound recovery operation combining
these exact fences was found in the inspected broker/MCP surfaces. Available
Support connector tools contain no Kandev launch/drain capability. A generic
administrator credential or raw host manipulation would not supply a reviewed
exact-task control; none was minted, read or bypassed into another surface.

## New bounded acceptance evidence

Existing synthetic regressions were run, without implementation edits:

- `TestRepositoryPlanCommentReservationLeaseBlocksConcurrentOwner` and
  `TestRepositoryExpiredPlanCommentLeaseRejectsStaleOwner` passed under `-race`
  (messagequeue package, 1.063s). They cover live-lease exclusion, safe expired
  lease takeover and rejection of the stale owner's acknowledgement. No real
  queue was replayed. PostgreSQL fixtures remain environment-gated.
- `TestEnsureWorkspaceExecutionForSession_ReusesExistingTaskEnvironmentExecution`
  passed under `-race` (lifecycle package, 1.073s). It demonstrates why environment
  reuse is not an exact-session recovery guarantee.

The first lifecycle test run was denied a temporary httptest loopback socket by
sandbox policy. Reviewed host escalation then ran that isolated mock test
successfully. This was a diagnostic permission issue resolved in-scope, not the
live repair blocker. No real agent, provider, runtime or production listener was
used by the test. Every yielded test execution was awaited through completion.

## Refined exact correction and remaining operator decision

The platform owner can build the smallest task-bound recovery control around the
existing primitives instead of inventing a duplicate message/turn or generic
start API. It must:

1. Authenticate caller task/session/workspace and pin target
   `9d5fcce2-e02d-41a5-b8de-d3672254e199`, HQA session
   `6cdaa1ed-57eb-47e8-81b6-6ffe17819caa`, incarnation
   `8bb54e82-41a4-48d4-a315-bdf421f69b9d`, HQA lane
   `814573a3-f2a3-4f42-8706-4f2997401fa6`, queue
   `103fb025-2ad6-5d9f-9e2c-e2d23e41e6f2` and original turn
   `06fa03f6-b9c5-48c1-b4ce-52af04b3612f` at preflight and at admission.
2. Verify no Human/pending-input/WIP/ownership fence, accepted delivery or active /
   orphan competing writer. Preserve older sessions and provider resume identity;
   do not treat a missing executor row or a ready record as proof of safety.
3. Establish the exact HQA execution using existing registered infrastructure only
   if its binding and preservation can be proved. Reject another session's reused
   execution; do not rewrite its owner. If no safe binding can be established,
   return a typed blocker without launching another prompt.
4. Under the same backend-owned admission/writer fences, reserve only the pinned
   original FIFO entry using the existing lease takeover, then let the normal
   dispatch/attempt/ack path handle it. A changed head/turn/incarnation or attempted
   delivery denies recovery. No separate direct `start_created` prompt is sent.
5. Return an idempotent exact receipt. Root's acceptance remains an actual new
   agent command/response in the original HQA session/turn with unchanged lane,
   source/head/index/worktree, packages, plans, counters and original identities.

The separate durable-versus-ordinary FIFO failure-release bug remains a platform
liveness correction to implement and test; it must not be bypassed by SQL edits.
The existing lease takeover primitive may recover this particular retained row
once the missing runtime/writer binding is resolved.

**Smallest missing scope:** authorize implementation/provisioning and activation
of that narrowly bound recovery control. Source implementation and deployment /
production restart remain explicitly excluded here, even though the checkouts are
generally writable Support scope. No broad rights or provider credential grant is
needed or requested. If installing the tested control requires a production
recreate, the approval must cover the concrete hotfix-preserving safe-deploy plan;
only `scripts/kandev-safe-deploy --build`, HTTP-200 gating, required deployment
checks and verified rollback are permitted. A recovered rollback is BLOCKED.

No production recreate or source implementation is claimed or performed. Root
must not resend the original message or clear its receipt. This pushed result
requires no status polling or Human relay.
