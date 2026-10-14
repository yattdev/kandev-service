# C275 Host owner: recovery-route escalation audit

Request `1d730b2e-d812-4dca-b553-bd77badf66c8`, escalation pass 1, remains
**BLOCKED** for actual same-owner command acceptance. This extends root incident
`8f0d9649-2703-4e73-9ef4-682c114b4e12`; no duplicate job or work order was created.
The [original Host evidence](C275-HOST-DISPOSITION-1D730B2E.md) and
[unissued preflight](support-evidence/c275-host-1d730b2e-preflight-draft.json)
remain intact. Original execution/provider acceptance remains **UNKNOWN**.

## Exact original and preserved evidence

Task `b4c55269-b579-4dbd-9227-67061064323c`, session
`1a963e8a-8c5b-471a-b98b-35d612e6406b`, intent
`C275-HOST-DISPOSITION-20261014-v1`, message
`5300a2b6-8008-5621-806e-32ca460e9c9f`, turn
`862cec5b-1e66-47be-9c2a-dd5415c84517` remain the only affected Host identity.
The packet digest and fork17 head remain caller-supplied preservation references,
not newly recomputed claims. No direct database access or task-status poll occurred.

The prior bounded historical logs establish dispatch at 03:19:08.292 UTC,
watchdog failure at 03:24:08.294 and removal at 03:24:11.334 on 2026-10-14,
execution `6abc4180-bde2-4340-b8e2-f9c7538be2f7`, generation 3. The watchdog
records absence of progress, not provider rejection or absence of effects.
No new command receipt is available.

## Supported readiness path and its limits

An existing supported application operation does exist: authenticated WebSocket
action `session.recover`, with this conditional lifecycle-owner payload:

```json
{"task_id":"b4c55269-b579-4dbd-9227-67061064323c","session_id":"1a963e8a-8c5b-471a-b98b-35d612e6406b","action":"resume"}
```

This was not executed and is not attested safe for blind invocation. In restored
deployed source, plain `resume` keeps saved conversation identity and calls
`ResumeTaskSessionWithOptions` without a prompt continuation. It waits for
readiness; it does not itself submit another task prompt or replay the packet.
It uses a session lifecycle lock and registered resume attempt. Those existing
guards should be reused; a blanket claim that all supported resume is absent
or necessarily submits another model prompt would be incorrect.

It can nevertheless prepare/relaunch a runtime, abandon open turns, backfill
missing initial-message history and affect workflow parking/launch metadata.
It is not a metadata-only probe. Its request does not bind an expected original
intent/message/digest/turn outcome to the next execution or produce an original
work-order command receipt. `runtime_retry` may select `fresh_start` and clear
resume identity. Neither it, branch replacement nor shared workspace restore
is an acceptable substitute.

This Host owner needs exclusive custody of its existing **read-only actor**.
Requiring or granting a new source-writer claim would exceed this target's
authority. Other source-owner cases retain their separate writer requirements.

## Authority and reviewed escalation audit

Both checkouts were inspected. Source remains
`cfd6bdf65ae6f631d7701c105791a099c0325cc3`; restored deployed code was read at
`80fdc4ce072ced98c6d72996f02e2c578d64dd82`. No source/feature work was performed.
Reviewed host escalation succeeded: read-only Docker inspection confirmed
production container
`3b95b8dbafb8d29c6956e06467cfff09511ff1592f654aec0fe5fa2f9668d172`, image
`sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`,
started `2026-10-12T22:06:50.719127446Z`. Public local feature metadata returned
HTTP 200 and `auth:true`. These were platform diagnostics, not task polling.

`session.recover` requires existing user task access and `session.prompt`
authority. No callable Kandev connector or native delegated recovery control was
available to Support. Broker inspection found no scoped session-recovery operation.
Its description-update helper creates an administrator PAT through a database
write; that is not this capability and would violate the present direct-database/
credential boundary. No token, cookie or raw control access was substituted.

Native `continue_task_message_kandev` requires an eligible original queue entry
and rejects FAILED owners. It cannot reconstruct uncertain delivery from a
transcript. Host read authority cannot reconstruct the deleted live-instance
outcome slot or turn generic readiness into correlated command acceptance.

## Smallest preserving next action

The lifecycle/platform owner must complete the existing root incident's pinned
Host preflight through an authenticated application-owned context:

1. Validate original identity/digest, saved conversation, current incarnation,
   lane/environment and unchanged read-only profile/model. Preserve source,
   loaders, old schema, data, FIFO and plans. No new Human answer is inferred.
2. Supply original acceptance/effect evidence or explicitly account for UNKNOWN
   effects. Establish old-execution closure and exclusive same-session recovery
   custody, with fresh preservation and current Human-input/WIP fences.
3. If admitted, use existing plain `session.recover`/`resume` on the exact row,
   with no prompt, fresh-start or replacement permission. A readiness receipt
   establishes readiness only.
4. Provide application-owned continuation bound to the original work-order
   reference and recovery attempt, without copying/requeuing original content.
   Require an actual same-target command reading local instructions before
   claiming recovery. No such bound continuation primitive is exposed here.

Existing authenticated user recovery does not itself require a production
restart. If delegated original-bound continuation must be added, that exact
implementation/activation scope needs a separate decision because this request
excludes source changes and production restart. A generic provider/admin grant
or unbound new message is not that operation.

The missing operation is authenticated original-outcome/custody reconciliation
plus bound read-only continuation, with an existing readiness component available.
This is not a generic wait for an unspecified source PR.

Only incident documentation and the
[content-free escalation receipt](support-evidence/c275-host-1d730b2e-escalation1.json)
changed.
JSON, root linkage and whitespace checks passed. Unchanged runtime tests were
not repeated. No database access, raw/application resume, replay, source/feature
work, credentials, profile/model/lane change, cleanup, runtime operation,
production restart or Human schema/preview decision change occurred. No command
acceptance is claimed and no Human relay is required for this pushed result.

## Final conditional-route correction

The [pass-2 audit](C275-HOST-DISPOSITION-1D730B2E-ESCALATION2.md) supersedes
unconditional no-prompt recovery advice: FAILED/tokenless resume can retain the
task description. It also distinguishes the successful separate verifier route
from this request's explicit database/credential exclusions. No Host recovery or
original command receipt is claimed.
