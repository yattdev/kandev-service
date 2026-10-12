# D28 physical recovery review package

Contract `D28-PHYSICAL-RECOVERY-PROPOSAL-v1`, Support request
`b4c9bebe-74f0-4756-ba75-a68c2ce2a8e1`. Preparation only. The canonical
sanitized proposal is `support-evidence/d28-physical-b4c9bebe-proposal.json`.
It is not a deployed API, approval, writer grant or executable recovery command.
This preparation reuses retained audited evidence and static existing lifecycle
code. No live diagnostic, runtime request or recovery operation was performed.

## Existing authority and missing proof

The Kandev backend lifecycle manager owns the execution store, recovery guard,
task/environment association and its existing authenticated runtime clients.
The standalone agentctl control server owns `instance.Manager`; each instance's
`process.Manager` owns provider and command handles. The launcher/OS supervisor
owns any actual process containment domain. These are the evidence owners;
Coordinator/task callers do not gain their raw interfaces or credentials.

An attestation must originate from an authenticated existing owner, bind its
actual server/backend/runtime incarnation, and refer to immutable audit evidence.
A caller's JSON `complete=true`, synthesized test generation, task plan, process
name, CWD, zero PID, empty session lookup or missing control ledger is not proof.
The registered repository/environment/worktree IDs and physical handles remain
unbound in this proposal. No placeholder ID is treated as a real resource.

Current shared-ledger absence prevents this Support caller from obtaining an
existing authenticated runtime binding. Even a newly exposed read projection
cannot recover an erased original incarnation or prove escaped descendants
absent. The retained final audit remains authoritative about that UNKNOWN.

## Supported seams and their limits

Existing internal `ControlClient.GetInstance(executionID)` and the instance's
process-manager read surface can supply **currently managed** identity and
command facts through an authenticated backend owner. They are not complete
closure certificates and must not trigger launch, adoption, credential rotation,
teardown or queue replay merely to answer a read.

Existing `Manager.StopAgentWithReason`/`StandaloneExecutor.StopInstance` and
agentctl instance teardown close admission and stop a process manager. Static
review shows process shutdown may escalate to process-group SIGKILL even when
the outer call requests graceful behavior. A shared task-environment execution
may also be reused by multiple sessions. Therefore those calls are **ineligible
as-is** for the proposed preservation and TERM-only recovery contract.

The prior exact-stop Support utility performs a global `/proc` environment
enumeration. It must not be reused or invoked for D28: that scan was rejected.
The recovery guard alone is in-memory launch bookkeeping and cannot revoke an
existing process's filesystem authority or survive restart as a physical fence.
No currently installed freeze-only or preservation-safe exact D28 retirement
primitive was established by the retained evidence/static review.

## Two evidence routes before a physical decision

**Original binding route.** The existing lifecycle/supervisor owner supplies an
authenticated original launch record for each old Source/steward: exact task,
workspace, session incarnation, execution ID, server/runtime incarnation, kernel
handle birth identity, source/data capabilities and full descendant coverage.
Closure must cover background commands, detached children and further admission
paths. Any gaps remain UNKNOWN. A complete retained closure receipt could settle
the historical question without a new physical operation.

**Prospective containment route when original incarnation is unrecoverable.**
The existing supervisor supplies an independently authenticated, pre-existing
physical write-domain binding covering every remaining old task source writer,
including unindexed descendants. Its membership generation and containment
guarantee must be kernel/supervisor enforced, with no agent delegation allowing
escape. The owner must prove this domain is disjoint from current833, private PG,
helper processes, shared control/backend services and every other task. Creating
a new scope around the processes currently visible in a registry does not prove
that old escaped processes were captured. No process scan is authorized here.

This second route establishes a new prospective physical boundary; it never
certifies the missing historical interval, restores deleted sessions or claims
historical transcript/counter recovery. Human must explicitly accept that
distinction after seeing actual finite scope/resource bindings. A general
engineering approval cannot authorize it.

## Exact future resource allowlist

Only task `d28be44c-136f-47af-af5d-faa7e6381818` in workspace
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd` is eligible. The candidate old identities
are Source `d2b0b80c-7716-476f-a4bf-bbcd59988d4f` / execution
`98fbeabc-5542-40ba-9d87-228ce3ddf370`, and steward
`3dc52cfc-d888-41ed-924a-cbe0de77af3b` / execution
`adea40f6-b704-4579-be95-4856810e7099`. These UUID pairs are retained database
associations, not an OS signal target list. Later approval must name a finite
owner-issued manifest of actual opaque physical scope/handle IDs and generations.
No wildcard, PID-only target, supplied host path or newly discovered foreign
resource is permitted.

Exclude session `833d9d08-69b8-4855-9ff8-6b05c59a1647` and all its current
executions, whether read-only or later assigned Source; no primary/model/role
change is implicit. Exclude private native PG processes, their data/DSNs,
commands containing unique state, helpers, current and historical gate archives,
F3, other sessions unless positively bound as old-provider descendants, every
other task, shared services, Root and protected question/candidate authorities.
Whole-task, whole-instance or shared-control shutdown is not an acceptable
substitute. Any protected member inside a candidate domain makes it ineligible.

The source branch stays `feature/fence-cancelled-task-9cs`, frozen checkpoint
`e1f5c3bd38569175c2645906f5200c2d429a4670`, fork
`5d13d9110972d60274c0b504d0c1bb6abca4be02`, eleven local commits. These are
caller-supplied preserved facts, not new filesystem observations in this turn.
The owner must pin actual registered repository/environment/worktree identity,
tracked/untracked/ignored unique-state manifests, native PG identity, archived
report digests, FIFO order/content digests and counters without exposing DSNs,
command output, credentials or raw process environments.

## Future operation schema and guards

The schema in the canonical packet describes a **proposed**, not callable,
backend `prepareExactTaskPhysicalRecovery` read action and separate
`applyExactTaskPhysicalRecovery` operator action. Reuse the existing lifecycle
manager, runtime client and per-instance/process ownership locks. No parallel
engine, standalone helper, credential endpoint or raw host control is proposed.
Caller identity comes from existing authenticated provenance; task/workspace and
canonical Coordinator authorization are rechecked server-side. Resolve every
opaque resource reference from the owner's immutable attestation, never caller
path strings. Original-incarnation fields must remain null/UNKNOWN if lost.

Prepare only after owner evidence is available. Capture a bounded consistent
manifest and explicit completeness/exclusion evidence. Record a stable operation
ID, selected mode, exact scope generations, expiry, preservation snapshot and
proposed rollback boundary. Missing binding, stale owner/epoch, unclassified
child, protected member, unverifiable capability holder, new Human input,
unpreserved FIFO or changed source checkpoint returns HELD with no mutation.

Apply requires a separate authenticated Human physical authorization receipt
pinned to **that exact prepared manifest and mode**, not a boolean or the
earlier additive-cutoff engineering approval. Acquire the existing owner's
per-resource lock and admission gate, CAS every scope/generation, and prevent
new old-provider admission/escape before any physical step. Never clear a queue,
session or budget to acquire the lock. Freeze/retirement must be an existing or
separately reviewed owner primitive whose documented boundary excludes protected
resources. A schema alone does not establish that such a primitive exists.

Preferred prospective mode is a supervisor-enforced freeze of an already proved
disjoint complete old-provider domain, coupled with durable denial of new
old-domain admission. This preserves memory while preventing old source writes.
It is **conditional and unavailable under the presently proved controls**.
Kernel freeze without complete containment/admission proof is insufficient.
A lease marker, read-only remount of a different namespace, chmod, guard-row
edit or semantic pause cannot revoke old open writable handles.

Alternative retirement is permitted only after an exact quiescent checkpoint
proves there is no unique provider/command memory or pending input to lose, and
the reviewed primitive is graceful/TERM-only with bounded grace and positively
bound handles. It must have no implicit SIGKILL or widening fallback. A timeout
holds the fence and returns PARTIAL/HELD; it does not kill another group, recycle
the environment, deploy, or assert success. Private PG/helper preservation is
mandatory even if an old instance happens to own those resources.

## Recovery, rollback and post-acceptance

Append content-free PREPARED/APPLYING/HELD/FENCED receipts with owner, manifest,
generation and preservation digests. Idempotency keys resolve retries to the
same finite resources; they do not admit newly found targets. A stale retry is
rejected. Existing original audits remain immutable.

Before a new Source is admitted, a reversible freeze may be rolled back only
by the same authenticated owner, after proving no successor writer has been
admitted and checking exact scope generation/preservation. Thaw restores old
write authority and invalidates exclusivity immediately. If a successor was
admitted, rollback needs a separately authorized exact successor revocation;
it must not automatically thaw into two writers. Retirement has no process
resurrection rollback; keep history/data/FIFO and acknowledge lost volatile
state if separately approved. Never recreate old UUIDs or replay commands.

Post-acceptance must prove complete source-write containment and persistent
old-admission denial, no protected changes, unchanged source/refs/untracked
unique state/PG/data/DSN/archives/FIFO/counters, and the exact owner/runtime epoch.
Supervisor restart or loss of enforcement invalidates the fence and blocks new
writer admission. Current833 stays read-only. Root must perform a separate
guarded own-caller acceptance and Source admission under the lifecycle lock and
generation fence; this proposal neither starts it nor repairs missing history.

## Smallest concrete next operation

The existing backend/agentctl/supervisor owner must provide one authenticated
task-filtered resource attestation from its retained launch/containment records,
not a global scan: actual registered task identity, original launch closure if
available, or a complete existing prospective domain and protected-resource
partition. Current833 can supply its ordinary authenticated metadata/artifact
preservation receipt while remaining read-only. Neither receipt authorizes a
physical action. No Human should be asked to approve unknown scope handles.

If that finite containment proof cannot be produced, no task-contained physical
operation meeting these exclusions is available. The only honest next decision
would be whether to relax a specifically identified preservation/exclusion
boundary; a shared shutdown, destructive reset or new writer is not an option
inside this request. Report the exact overlap/missing resource to Root first.
This is an evidence/capability prerequisite, not another request for generic
engineering approval.
