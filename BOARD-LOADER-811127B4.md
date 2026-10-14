# Board-loader startup failure: exact preservation receipt

Support request `811127b4-88c1-4758-ba6f-f175ee0e6153` is BLOCKED for live
continuation. Diagnosis is complete; no successful start, restored owner or new
agent output is claimed. The [content-free receipt](support-evidence/board-loader-811127b4.json)
pins both original admissions and their preservation checks.

## Exact failure

| Task / selected session | Original message = FIFO entry | Original open turn |
| --- | --- | --- |
| `531a41cd-57ef-495a-8dfa-614d2a4d0d52` / `5e0de349-8eaf-404f-9ae9-e5d102f70686` | `bb3ea0bb-a5e0-565e-bf4a-0a13311870c1` | `8dfa19fe-6df1-4725-b5cc-08bd51bdb3b5` |
| `86c8b47e-e7a5-4693-8e11-dce08899a0bf` / `2376d3fe-6818-4486-a1fb-7dc99c3bf433` | `31ac0085-0723-56ae-82de-f09187ea3795` | `ccaef80f-bca0-4467-8288-ee353a51fbaa` |

A fixed historical log window, 2026-10-14 02:01:06–02:01:12 UTC, records both
resume attempts failing with the same backend-redacted error:

```text
failed to resume session: worktree directory is corrupted: task "***" checkout "": task environment recovery is busy: environment *** has a live session or runtime
```

The persisted checkouts still exist. Read-only inspection of their regular
`.git` pointer files and `lstat` of the resolved targets confirmed:

- First task: registered worktree `e8821e3b-c3b0-45a5-8923-c2157eaf6a77`,
  `/data/tasks/allow-coordinator-de_au1g7cb7/kandev-source`, has a missing linked
  Git administration target.
- Second task: registered worktree `046e49a9-fa4f-433d-a263-a84ca28aa2aa`,
  `/data/tasks/preserve-unread-queu_ofb2j8xg/kandev-source-feature-add-guarded-queue-cl-sls`,
  also has a missing administration target. Its other registered checkout
  `e7e57de8-3405-454a-9108-407dc934a64f` has an existing nonsymlink administration
  directory; this limited check does not attest its complete Git integrity.

No task source files, Git objects, index, credential stores or pointer-target
contents were opened. Pointer hashes are preserved in the receipt. The cause of
historical administration-directory loss is not established by this bounded
check. Do not reconstruct it by guessing HEAD, index or branch state.

In the restored deployed-lineage source, `worktree/recovery_admission.go` first
inspects the selected checkout. Its `needsRecovery` path applies specifically
after missing-admin classification and repository/branch validation. Only then
does it request a task-environment recovery claim. The claim refusal is wrapped
as the error above before recovery changes or agent launch.

`task/recoveryclaim/claim.go:environmentHasConsumers` refuses a claim if either
another nonterminal session is attached or **any** `executors_running` row is
attached. The executor query has no status filter and includes the requesting
session's own stopped record. For these exact environments:

| Target | Other waiting sessions | Current primary, also waiting | Registered executor rows |
| --- | --- | --- | --- |
| `531a41cd...` | 2 | `403b66a8-5153-4fb8-9df1-922db6f9c29e` | 9, all `stopped`, resumable |
| `86c8b47e...` | 1 | `02b48c70-3ad9-461d-a5ca-7fe3c01dfe50` | 3, all `stopped`, resumable |

Neither selected failed session is currently primary. Neither environment has a
recovery claim row. The selected executor records exist, are stopped and are
resumable. The logs record discovery of saved resume state; no value was read.
This incident therefore differs from the separate HQA missing-executor incident.
Database `stopped` status does not independently establish process quiescence,
and another waiting primary does not independently prove a running writer.
Neither condition may be falsified or deleted to bypass recovery admission.

## Why sender status still says dispatching

The first execution failure is logged at 02:01:08.023 UTC, the second at
02:01:09.608 UTC. Each failure handler then logs a failed post-claim mutation,
operation `requeue message at head`, error `queue dispatch claim changed`.

Both original entries remain at FIFO position 1, durable-reserved, with their
original transcript messages and incarnations. No delivery-attempt marker is
present; neither original turn has a completion timestamp. There are zero
ordinary dispatch claim rows for these two entries. The lease deadlines were
02:01:37.201964445 and 02:01:38.542145847 UTC respectively. Expiry is not a license
to resend: normal identity-checked lease takeover exists, but it does not repair
Git metadata or establish exact execution ownership.

The retained-versus-ordinary failure-release mismatch is a separate platform
liveness defect. `dispatching` is a reservation projection, not proof that an
agent accepted a prompt. No agent/tool output after these admissions was found
in the scoped snapshot. Do not duplicate either original receipt, send a direct
start prompt, retarget a different primary, or manually release queue flags.

## Bounded acceptance checks

Both named checkouts were inspected. Their unrelated changes remain untouched.
No source implementation, new source worktree or upstream-only classification
was made. The clean restored deployed-lineage worktree at
`80fdc4ce072ced98c6d72996f02e2c578d64dd82` was used for seven existing tests,
all passing under `-race`, `-count=1`, Go 1.26.0:

- SQLite: `TestTaskEnvironmentRecoveryClaimSerializesMutationsAndConsumers`,
  `TestTaskEnvironmentRecoveryClaimRejectsStaleOwnership`.
- Executor: `TestResumeSession_BlocksWorktreeRecoveryBeforeStateChangeOrLaunch`.
- Message queue: `TestRepositoryPlanCommentReservationLeaseBlocksConcurrentOwner`,
  `TestRepositoryExpiredPlanCommentLeaseRejectsStaleOwner`.
- Worktree: `TestManager_AdmitTaskRecoveryRejectsMissingAdminOutsideRepositoryCommonWorktrees`,
  `TestManager_AdmitTaskRecoveryRefusesBacklinkMismatchWithoutMutation`.

These isolated fixtures validate pre-launch refusal, ownership/consumer fences,
lease takeover and stale-owner rejection, and refusal of unsafe Git repair.
They do not constitute live restoration or coverage of a new recovery control.
All yielded test runs completed successfully before subsequent dependent work.
Reviewed read-only host diagnostics succeeded; no diagnostic denial remains.

## Precise prerequisite and preservation-safe continuation

The remaining owner is the Kandev platform/storage operator, with Root retaining
ownership of the instruction packet and correction. The smallest next action is
to establish a trusted recovery source for the two missing Git administration
directories and approve a narrowly scoped preservation-first recovery plan.
The current request forbids the worktree mutation/rematerialization needed to
repair that prerequisite. Wider credentials or generic Coordinator rights are
unnecessary.

A reviewable plan must cover:

1. Pin each exact caller/workspace/task/session/incarnation/entry/turn and the
   unchanged lane `89985050-d740-4421-bbbe-4aa018d8c7ab`. Record complete Git,
   source, index, plan, pending-message and resource preservation evidence before
   any repair. Preserve both older primary and historical sessions.
2. Establish actual process quiescence and sole-writer ownership using supported
   backend admission. A stopped database record is insufficient. Do not make
   other sessions terminal, delete resumable records or impersonate a parent.
3. Prefer restoring the exact original Git administration metadata from a
   trusted matching source, retaining its original HEAD/index/history/backlink.
   If this cannot be proved, stop with a concrete blocker. Existing automatic
   worktree recovery snapshots and rematerializes beside the original and
   publishes a new checkout pointer; that is a material resource change and is
   not authorized here. Merely removing the consumer check is unsafe.
4. Revalidate healthy checkout and normal exact-session admission. If recovery
   still needs a claim, its conservative stopped-record/consumer policy must be
   addressed through a separately reviewed backend-owned control preserving
   historical rows and writer fences, not SQL or filesystem bypass. Any necessary
   source implementation/activation remains outside this request.
5. Only after those preconditions, use the normal identity-bound dispatcher and
   existing expired-lease takeover on the pinned original FIFO head. It must
   reject changed head/incarnation/turn, attempted or accepted delivery, Human /
   pending-input / WIP gates and competing writers. Do not call a generic start
   or insert another copy of the packet to work around the retained reservation.

Root's live acceptance is an actual agent command reading the local instructions
or response in each **original selected session**, correlated to the original
open turn and packet, with unchanged lane and all source/runtime/provider holds.
An API success, `drained:true` or a session state change alone is insufficient.
After that evidence, Root can supply its compact `BOARD-LOADER-FIT-20261014-v2`
correction. Support has not sent that correction or another instruction packet.

Only this report and content-free receipt are committed/pushed. No recovery,
Git repair, task mutation, queue replay, runtime start, provider work, credential
access, source implementation, cleanup, lane move, deployment or restart occurred.
The original checkouts, session history, open turns and pending packets remain
preserved. Delivery is the pushed Support result; no Human relay or status
polling is required.
