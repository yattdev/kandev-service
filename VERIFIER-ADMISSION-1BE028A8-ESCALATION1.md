# Verifier admission: resolved through reviewed host recovery

Request `1be028a8-6818-4ef8-bbf0-2111b868c73f`, escalation pass 1.
**RESOLVED for guarded admission/protocol readiness.** Both original independent
side sessions are WAITING_FOR_INPUT with ready executions. No verification
handoff, provider inference, evaluation or Review/QA verdict was issued by Support.

The first pass treated the absence of a task-facing recovery tool as a terminal
Support limitation. Reviewed host execution of the existing authenticated
application control was available and succeeded. No new task-facing host access
or production deployment was needed.

## Exact positive acceptance

Task `afdb2ef3-06ca-4cd5-a074-c4e691679da9`, workspace
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`, step
`0541923c-2d38-478e-8573-3c5e27e37a31`, state REVIEW and sole MAIN
`fafba895-b769-40d5-a840-f6b90b98fcb4` were preserved.

| Owner | Original session, now WAITING_FOR_INPUT | Ready execution | ACP initialized UTC |
| --- | --- | --- | --- |
| Review | `ce9a2b21-226c-41b1-be4c-828c7ef1dfef` | `aa9bbbe7-aa54-42fd-bd02-8a1ff2d66056` | 2026-10-14 06:18:25.499 |
| QA | `9610084b-03e4-442c-ba8a-3109e06a4123` | `f7c21c67-906f-45cd-b13e-933d8b9326d3` | 2026-10-14 06:18:28.584 |

The supported recovery calls returned these exact executions after protocol
readiness. Independent post-checks found executor status `ready`, configured and
effective model `gpt-6.1-sol`, unchanged profile
`c06ad00e-0da1-429a-8174-54f97164a289`, and original incarnations. Profile policy
remained auto_fallback=false and require_exact_model=false; Support changed no
Human model/profile setting. No model substitution or conversation replacement
occurred: the adapter compared saved-conversation fingerprints before and after
without returning their values.

The adapter confirmed unchanged original user-message hashes and failed-turn
completion values, unchanged user-message/work-turn counts, and empty queue,
open-work-turn and pending-or-unknown Human-input counts. Lifecycle-only boot
history may be appended normally. Both original watchdog error envelopes were
also independently checked against their original content hash. No failed
transcript or work turn was rewritten.

A single fixed historical log window, 06:12:22.420755–06:20:22.420755 UTC, showed
both new subprocess starts and ACP initialization, with **zero prompt dispatches**
for either new execution. No application/trial requests or evaluation were run.

Original activation outcomes remain UNKNOWN. Their original identities are:

- Review: intent `activation-review-c9-59433-v1`, message
  `24ea3a33-b106-5b56-bb88-9ced18e9e558`, failed turn
  `04436262-9a3d-4ef3-ad65-2c21801f7a99`.
- QA: intent `activation-qa-c9-59433-v1`, message
  `22d8f471-e8a5-58ca-b51a-0f3539dab9bd`, failed turn
  `be347b62-9f02-401e-be9c-bace319759be`.

Neither original packet was replayed. Restored readiness is not a verdict about
those prompts or about the trial's activation behavior.

## Cause, supported operation and reviewed authority

The failed prompts reached dispatch, then the five-minute no-progress watchdog
failed and removed their executions. The lower-level cause of silence is still
UNKNOWN. The subsequent admission failure is explained: native durable message
admission rejects FAILED owners; it is not a session-recovery operation. The
[reporting repair](https://github.com/yattdev/kandev/commit/e8f963523d9d10f85af7c0d0d2c45ae0d1fdff91)
corrects misleading retry advice but remains undeployed.

This escalation restored the exact owners through the existing authenticated
WebSocket action `session.recover`, payload `{task_id, session_id, action:"resume"}`.
There was no fresh-start, replacement session, substitute source owner, copied
prompt, direct Codex resume, raw agent-control call or manual task-state SQL write.
Normal backend lifecycle, resume-attempt and readiness guards stayed in force.

Reviewed host execution used a five-minute, host-contained operator PAT following
the existing broker's temporary-operator pattern. It selected an existing active
administrator; no user role, provider credential or task grant was added. The
credential existed only inside the host process and in the normal Authorization
header, never in a URL, argument, chat, plan or log. No existing credential values
were discovered or copied. The lease was revoked in a deferred cleanup and an
independent read confirmed **zero remaining lease rows**. The only direct database
writes were that temporary authentication lease's INSERT/DELETE. All session
recovery/state changes went through the supported authenticated application API.
No credential or raw host capability was returned to the Coordinator/task.

## Guarded reusable route and owner handoff

The [host-only operator adapter source](support-evidence/verifier-admission-1be028a8-readiness.go)
is a bounded review artifact, not an agent command or installed service. It pins
this request's task/workspace/step/MAIN, two original sessions/incarnations,
profile/model, prior executions and original message hashes. It has no arbitrary
target or prompt parameter. Default execution is read-only preflight; `--apply`
requires reviewed host operator authority and invokes only the normal recovery
control. It refuses another attempt once these original failed executions have
changed, or whenever a guard no longer matches. It must not be relaxed to replay
UNKNOWN work or routed around a backend refusal.

Before recovery it verifies original completed turns and hashes, compatible
saved resume identity, prior effective/configured model, empty FIFO/Human gates,
and ownership. It requires unchanged conversation/history and actual same-model
protocol readiness afterward. On ambiguous delivery/result it reports UNKNOWN
and does not retry. Generic tokenless FAILED recovery can auto-prompt, and generic
model selection can fall back; those paths were not taken here and are not an
unconditional future permission. New failure identities require new correlation,
not rerunning this pinned old recovery.

The Coordinator/MAIN may now send each actual independent verification handoff
through existing `message_task_kandev`, naming the exact original Review/QA
session and using a new stable intent. Do not resend the original UNKNOWN
activation intents. Existing native queued admission and Human/WIP/incarnation
fences remain authoritative. Support will not supply the verification prompt or
verdict. If a new handoff fails, preserve its own receipt rather than replaying it.

## Code, tests and preservation provenance

Operator source SHA-256:
`f67fcd49963951124019fedaf98317d6a6a785db622d081cfdbe87c878f26ff4`.
Built host adapter SHA-256:
`91a87cadf8c28bc584de7415fa4c20fefeddf6bab61a852a00d5a281a6b5dc06`.
The adapter was built with Go 1.26.0 and the already pinned backend module's
Gorilla WebSocket/SQLite dependencies. Its self-test passed 14 negative guard
cases, its read-only preflight passed, Go vet passed, and both guarded live
protocol receipts passed. No new application binary/image was built or installed.

Additional race-enabled isolated tests passed for FAILED tokenless auto-prompt
semantics, executor-authoritative model policy and mock-protocol fallback. The
first sandbox mock-listener run was restricted; the reviewed host retry passed.
Those tests used mocks only. The earlier source reporting candidate's tests,
commit hooks and offline build remain unchanged and are not claimed deployed.

Both user checkouts and their unrelated dirty/untracked files were preserved.
Production container
`3b95b8dbafb8d29c6956e06467cfff09511ff1592f654aec0fe5fa2f9668d172`, image
`sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`
and started-at `2026-10-12T22:06:50.719127446Z` stayed unchanged. No overlay,
production restart/deployment, trial container/image/data/port, board step or
completion state, provider account/model configuration, or MAIN ownership changed.

The [content-free resolution receipt](support-evidence/verifier-admission-1be028a8-escalation1.json)
records the exact before/after identities, preserved evidence and zero-prompt
acceptance. No new recovery job or task session was created. The existing owners
retain responsibility for the actual independent activation verification.
