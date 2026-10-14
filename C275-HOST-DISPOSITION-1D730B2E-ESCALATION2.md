# C275 Host startup: final boundary and conditional recovery

Request `1d730b2e-d812-4dca-b553-bd77badf66c8`, escalation pass 2.
Status **BLOCKED**: original execution/outcome remains **UNKNOWN**; no recovery
or same-target command acceptance is claimed. This extends root incident
`8f0d9649-2703-4e73-9ef4-682c114b4e12`; no duplicate repair job was created.

## Exact preserved identity and diagnosis

- Read-only Host task: `b4c55269-b579-4dbd-9227-67061064323c`.
- Original session: `1a963e8a-8c5b-471a-b98b-35d612e6406b`.
- Intent: `C275-HOST-DISPOSITION-20261014-v1`.
- Message: `5300a2b6-8008-5621-806e-32ca460e9c9f`.
- Turn: `862cec5b-1e66-47be-9c2a-dd5415c84517`.
- Caller packet digest: `24f398694a8b58ff623f6f0e53a5e1c9ef98a514bd4980b1983430881742013f`.
- Caller preservation head: `d7b24e163f4adfb6290f824fdc8f3bff2afa7a58`.

The [prior fixed-window evidence](C275-HOST-DISPOSITION-1D730B2E.md) remains
valid: execution `6abc4180-bde2-4340-b8e2-f9c7538be2f7`, prompt generation 3,
reached dispatch at 03:19:08.292 UTC, hit the no-progress watchdog 300.002 seconds
later, emitted error `91e37223-8bf1-4ce9-9e17-f9a99528baa9` and was removed from
platform tracking. The lower-level reason for silence and provider acceptance
remain UNKNOWN. Watchdog `never_started` is not a no-effects certificate.
No new live task-state assertion or physical writer-closure claim is made.

This matches the demonstrated C275/PORT4476 watchdog class. It does not establish
a common provider cause, nor merge the distinct missing-Git/missing-executor
incidents. Original instructions, FIFO and histories have not been replayed or
rewritten by Support. Supplied source head/digest remain caller evidence; no
foreign worktree or live database was opened to recompute them.

## Escalation audit: Support authority and the available control

Both named checkouts were inspected. Deployment remains on main, with unrelated
tracked/untracked files preserved; the source checkout remains at
`cfd6bdf65ae6f631d7701c105791a099c0325cc3` with its unrelated files preserved.
No upstream-only classification or inability to perform reviewed host reads is
asserted. Reviewed host diagnostics succeeded: the application features endpoint
returned HTTP 200, while `/ws` without an identity returned HTTP 401.
There is no callable Kandev connector/browser control in this Support tool set,
and the reviewed broker has no exact-session recovery delegate.

The existing authenticated application action is real:

```json
{"action":"session.recover","payload":{"task_id":"b4c55269-b579-4dbd-9227-67061064323c","session_id":"1a963e8a-8c5b-471a-b98b-35d612e6406b","action":"resume"}}
```

This is a review-only action envelope, not an executed command or a grant. The
normal transport request also needs its own correlation ID and existing user
identity with task access and `session.prompt`; no credential belongs in this
artifact. Backend task/session/archival/recovery fences must remain enabled.
No fresh-start, branch replacement, runtime_retry or profile/model override is
permitted by this proposal.

The [separate verifier recovery](https://github.com/yattdev/kandev-service/blob/ea05fe8/VERIFIER-ADMISSION-1BE028A8-ESCALATION1.md)
demonstrated that reviewed Support can use this control to restore protocol
readiness. That operation used exact read-only database preflight and a new
host-contained five-minute operator PAT, inserted and revoked in the auth token
table. This Host request explicitly excludes **direct database access and
credential changes**. Reusing that adapter/helper would violate those boundaries;
using the broker's existing token helper does not remove its database/token side
effects. No such helper, token creation, credential discovery/copy, existing
credential reuse or database access occurred for this request. No reviewer denial
is claimed: the permitted read-only host escalation was approved and completed.

There is a second correction to earlier route descriptions: a `resume` payload
with no prompt is **not unconditionally prompt-free**. In the inspected restored
lineage, `applyRunningRecordToResumeRequest` clears the task description when a
compatible executor resume token is present; FAILED/tokenless recovery can retain
the description and start work automatically. A FAILED session's metadata-only
conversation identity does not establish that compatible executor-token branch.
The previous receipt's unconditional `submits_task_prompt_itself:false` must be
read as a conditional proposal and is superseded here. This target's current
executor/token/profile binding has not been authenticated under the present
constraints. No blind launch or no-prompt safety claim was substituted for that
missing preflight. Generic model fallback policy must also be checked without
changing Human settings or permitting a substituted model.

## Precise remaining prerequisite and supported preserving sequence

Owner: **Kandev authenticated lifecycle/platform operator**. The smallest next
step is to supply the exact application-owned custody/preflight receipt using an
already authenticated operator context, covering the existing
[unissued Host draft](support-evidence/c275-host-1d730b2e-preflight-draft.json).
Do not ask Human to relay a password/token or repeat the original instruction.
This requires no production restart and no new provider/model/profile grant.

The preflight must bind original identity/digest/incarnation, unchanged read-only
profile/model/lane/environment, saved conversation and compatible executor token,
empty or accounted-for FIFO/Human/WIP gates, preservation, old actor closure and
exclusive same-owner custody. It must explicitly account for UNKNOWN prior effects
rather than infer that the original failed before execution. Missing/ambiguous
proofs must stop recovery. The original packet remains the only work order.

If those proofs admit recovery, the operator can use the existing normal `resume`
control above and demand same-session, same-model protocol readiness without a
work prompt, replacement conversation or new worker. Readiness alone is not
original-delivery reconciliation and does not satisfy the command receipt.
The next continuation must be reference-bound to the preserved original work
order and custody decision, must not copy/requeue the original packet or rewrite
its completed turn, and must produce an actual same-target instruction-reading
command before claiming full recovery. A plain new message or unbound generic
resume is not certified as this operation here. No such authenticated
original-bound continuation/custody receipt is currently available to Support.

If no existing authenticated operator context can provide this, the exact
remaining scope decision is permission for a task-bound recovery delegate or
reviewed host-only authentication/preflight exception for this identity, together
with the UNKNOWN-effects/custody decision. Any implementation/activation must be
separately scoped because source changes remain prohibited. Broad credentials,
raw agent resume, source-owner substitution or production restart are not
prerequisites to be silently added. The earlier preflight draft remains unissued;
this report does not authorize its launch or fill its missing proofs.

## Bounded acceptance and preservation

A focused isolated race regression passed on the existing clean source review
lineage `e8f963523d9d10f85af7c0d0d2c45ae0d1fdff91`:
`TestApplyRunningRecordToResumeRequest_FailedSessionKeepsTaskDescription` in
`internal/orchestrator/executor`. It uses mock repository/manager objects and no
provider calls, proving the tokenless safety concern rather than testing a live
resume. No source implementation or production artifact was changed.

The host diagnostic observed the unchanged production container
`3b95b8dbafb8d29c6956e06467cfff09511ff1592f654aec0fe5fa2f9668d172`, image
`sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`,
started `2026-10-12T22:06:50.719127446Z`. No task-status polling, direct database
access, credential change, raw/application resume, queue mutation/replay,
source/feature work, profile/model/lane change, cleanup, provider call or production
restart occurred. Human schema/preview decisions remain separate and unchanged.

Only this final audit, root/history links and the
[content-free final receipt](support-evidence/c275-host-1d730b2e-escalation2.json)
are published. Root should preserve the original UNKNOWN receipt; no new command
acceptance or safe retry is claimed. The result returns through the existing
Support broker without a duplicate worker or Human relay.
