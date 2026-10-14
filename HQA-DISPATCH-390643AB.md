# Exact HQA dispatch failure: preservation-safe correction proposal

Support request `390643ab-baa1-439b-9014-41410352bdf3` is **BLOCKED for repair
activation**, with two concrete platform failures identified. No successful
start is claimed. Task/source/CI work was not performed. This is the pushed
Support result; no polling or Human relay is required.

## Exact evidence

Read-only diagnostics completed at approximately 2026-10-14T04:11:38Z. They used
the reviewed Support host authority, not an agent-facing raw Docker/socket grant.
Both named checkouts were inspected; unrelated dirty/untracked files remain
unchanged. No source, worktree, index, branch, package, plan or CI object on the
reported task was opened or modified.

| Binding | Observed value |
| --- | --- |
| Target task | `9d5fcce2-e02d-41a5-b8de-d3672254e199` |
| Workspace | `2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd` |
| Sole primary session | `6cdaa1ed-57eb-47e8-81b6-6ffe17819caa` |
| Session incarnation | `8bb54e82-41a4-48d4-a315-bdf421f69b9d` |
| HQA lane | `814573a3-f2a3-4f42-8706-4f2997401fa6` (`Human-QA`) |
| Task/session state | `REVIEW` / `WAITING_FOR_INPUT` |
| Original message/queue ID | `103fb025-2ad6-5d9f-9e2c-e2d23e41e6f2` |
| Bound original turn | `06fa03f6-b9c5-48c1-b4ce-52af04b3612f` |
| Intent | `C274-29-HQA-CONFLICT-OWNER-v1` |
| Queue position | `1`, sole queued row for this task |
| Queue content SHA-256 | `3607c923afa8d078fbc35815e7de8d6cd7b157682a41cefb03e179a904515c84` |

The task is WIP-admitted, not archived and not waiting for a WIP slot. The HQA
step is `custom`, uses profile session policy `reuse`, and its on-enter action is
`auto_start_agent`. There are no pending input-request rows on the exact HQA
session. This does not waive any independent Human approval/CI gate.

The session has **zero executors_running records**. Its last update remains
2026-10-14T01:16:41.180479852Z. The original turn opened at that time and remains
uncompleted. The session contains only the two inbound messages; the Root
message was recorded at 01:24:27.190350234Z against that original turn. No new
agent command/response or execution was observed in this session.

The original durable transcript receipt is still the same queue/message ID.
The queue row is retained with `lifecycle_reserved_in_flight:true`, matching
incarnation, `user_message_recorded:true` and no delivery-attempt marker. Its
lease expired at 01:24:57.217860536Z. There is **no ordinary
queue_dispatch_claims row** for that exact entry/session. Lease expiry alone
is not permission to replay an ambiguous dispatch. No reservation token or
message body was printed or retained in the Support receipt.

Production container/image identity was read-only captured as
`3b95b8dbafb8d29c6956e06467cfff09511ff1592f654aec0fe5fa2f9668d172` /
`sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`.
No binary or image was replaced. Live state was read for diagnosis, not polled.
The first query encountered the installed `metadata_json` queue-column naming;
the dependent query was corrected and completed read-only.

## Cause and supported-path audit

One fixed historical log window, 01:16:20–01:26:00Z, was filtered to the exact
task/session/message. Only static event text and selected dispatch fields were
projected; no prompt bodies, agent output or credentials were emitted.

1. At **01:16:41.199Z**, HQA auto-start failed with:
   `session runtime unavailable: failed to ensure session is running: session is not resumable: no executor record (state: WAITING_FOR_INPUT)`.
2. At **01:24:27.221Z**, execution of the exact Root queue entry failed with the
   same runtime error, before a provider prompt could be accepted.
3. At **01:24:27.222Z**, the handler attempted to requeue that original entry.
   At **01:24:27.223Z**, it failed with `queue dispatch claim changed`.

The restored live-source lineage explains both failures. In
`orchestrator/task_operations.go`, resume rejects a nonterminal WAITING session
without its executor row; old-session reuse alone does not reconstruct that
record. This is a missing-runtime failure, not a reported Human approval block.

In `messagequeue/repository_sqlite.go`, the FIFO requeue path checks ordinary
pending-dispatch ownership when generation metadata was captured and the entry
is not `IsDurableLifecycle()`. A native durable transcript-backed message is
instead `IsDurablePlanComment()` / `IsDurableDelivery()`. Its retaining-reserve
path does not create that ordinary claim. Thus the ordinary-claim check can fail
before the exact durable reservation release branch is reached. The actual
absence of that claim and the logged refusal support this explanation; no
synthetic reproduction or new implementation is claimed in this request.

The sender receipt intentionally reports reserved entries as `dispatching` with
`continue_allowed:false` and `retry_allowed:false`. That projection is not proof
of an active execution. It correctly prevents the caller from duplicating the
already recorded intent, but cannot recover this stranded reservation.

Existing alternatives were reviewed in source, not invoked:

- `session.recover` with `resume` reaches the same missing-executor guard.
- `fresh_start` clears the stored resume token before launch; `runtime_retry`
  can select that path. Neither is a preservation-safe substitute here.
- `resume_new_branch`, creating another session, lane moves and forcing a terminal
  state would change the requested preservation boundary.
- Queue drain/continuation cannot safely be treated as a release of an already
  reserved entry. Direct SQL deletion/flag clearing would bypass its ownership
  fences. Support performed none of these actions.

## Smallest correction proposal, before mutation

This request explicitly excludes source implementation and deployment. The
source checkout's general Support writability does not authorize overriding that
specific constraint. The necessary next operator decision is a narrow exception
for **this platform repair and its tested activation**, while task source, CI,
lane/history, credentials and broad rights remain excluded.

The platform owner should implement and review these two coupled corrections:

1. Distinguish retained durable deliveries from destructive ordinary dispatch
   claims in FIFO failure recovery. Require the original reservation token,
   unchanged incarnation/generations/entry and no delivery-attempt marker, then
   release only that exact retained row through the normal repository operation.
   Preserve ID, content, transcript binding, turn, timestamp and FIFO position.
   A missing or changed token/claim must continue to fail closed. Do not weaken
   ordinary claim ownership or release merely because a lease expired.
2. Provide a guarded same-session missing-runtime recovery for this exact reused
   primary and original admitted queue/turn, without clearing resume identity or
   creating a new task/session/turn. Preflight must validate task/workspace/lane,
   profile, incarnation, original turn and receipt, pending Human input, WIP and
   task-wide writer/execution ownership. A missing executor row alone is not
   proof that an orphan/other writer cannot exist. If preserved provider identity
   cannot be reconstructed, return an explicit blocker instead of fresh-starting.
   Serialize recovery and release under backend-owned lifecycle/admission fences;
   do not expose raw mutation or caller-supplied phase/authority overrides.

Expose a non-mutating preflight receipt and an exact, idempotent supported
recovery operation. Bind the latter to the preflight identities and revalidate
all fences at execution time; allow at most one runtime and one acceptance of
the original queue item. Do not use an agent-side replay loop or a generic host
broker escape hatch. Publish a failure disposition when recovery cannot run,
rather than leaving an unexplained apparent dispatch.

Required acceptance before activation:

- A reused WAITING primary with no executor row, a pre-existing original turn and
  a durable transcript-backed FIFO head recovers on the same identities; source,
  head/index/worktree, lane, packages, plans and prior sessions/counters survive.
- Pre-provider launch failure safely releases the exact reservation; unchanged
  sender continuation becomes available without another message or turn.
- Delivery attempted/accepted, existing/orphan writer, Human question/permission,
  WIP block, different primary/profile/lane/incarnation, stale lease token,
  changed generations, foreign workspace and duplicate recovery all deny or
  return the original idempotent result. Ordinary-dispatch fences remain intact.
- Exercise real persistent repository recovery and controlled provider/runtime
  fixtures, including concurrent attempts and failures between transaction phases.
  Run race tests and retained hotfix regressions; do not use actual CI/provider
  operations as test fixtures.

Only after separate deployment approval may the tested hotfix-preserving backend
and agentctl superset be activated through `scripts/kandev-safe-deploy --build`.
Inventory the then-live overlay provenance first; retain the captured image and
binaries, require HTTP 200 and deployment tests, and use verified automatic
rollback on readiness failure. A recovered rollback is BLOCKED. No restart is
approved by this proposal.

Root's final acceptance must be an actual new command/response in `6cdaa1ed...`
from the original admitted turn and unchanged HQA lane, not merely a successful
recovery API response. Root must not resend or manually continue while the
original receipt remains reserved/dispatching. No live repair was performed.
