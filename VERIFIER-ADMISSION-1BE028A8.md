# Core trial verifier admission: 1be028a8

Support request `1be028a8-6818-4ef8-bbf0-2111b868c73f`.
Execution restoration remains **BLOCKED**. A reporting repair is implemented,
tested and preserved separately from live recovery. No Review/QA verdict or
execution acceptance is claimed.

## Exact scope and observed failure

Workspace `2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`, task
`afdb2ef3-06ca-4cd5-a074-c4e691679da9`, step
`0541923c-2d38-478e-8573-3c5e27e37a31`. MAIN remains
`fafba895-b769-40d5-a840-f6b90b98fcb4`; it is not a substitute verifier.

| Owner | Session | Original turn | Prompt dispatch UTC | Watchdog failure UTC | Instance removal UTC |
| --- | --- | --- | --- | --- | --- |
| Review | `ce9a2b21-226c-41b1-be4c-828c7ef1dfef` | `04436262-9a3d-4ef3-ad65-2c21801f7a99` | 03:35:33.753 | 03:40:33.754 | 03:40:36.656 |
| QA | `9610084b-03e4-442c-ba8a-3109e06a4123` | `be347b62-9f02-401e-be9c-bace319759be` | 03:35:33.826 | 03:40:33.827 | 03:40:36.702 |

All times are 2026-10-14. Execution IDs were respectively
`a44318b3-a799-4ca4-84b0-7a231e6ba531` and
`37bdbcdb-ef37-464e-91df-db30186835c6`; prompt generations were 8 and 7.
Each session has its original user message and watchdog error on the failed
turn, no recorded command/assistant verdict, and a completed original turn.
Each had zero remaining queue entries, open turns and pending clarification
inputs at the scoped read. The executor records are failed/resumable.

Original provider acceptance and effects remain **UNKNOWN**. The watchdog's
`never_started` flag means no qualifying progress was observed; it does not
prove that the provider rejected the prompt. Removal also removed the live
outcome slot. These are post-dispatch stalls, unlike the pre-launch Git failures
in incident 811127b4. They match the observed no-output class in incident
8f0d9649, without establishing the underlying provider cause or opening another
repair job for those targets.

The original intents are `activation-review-c9-59433-v1` and
`activation-qa-c9-59433-v1`. Their message IDs, content hashes and exact
incarnations are in the content-free receipt. Do not resend either intent.

## Separate admission defect and implemented repair

The reported recovery attempt used task-message admission against FAILED
sessions. `CreateTaskMessageAndQueue` calls
`plancommenttx.ValidateTargetSession` under its task/session transaction and
rejects terminal states before message, turn or queue insertion. The MCP layer
then collapses `ErrTaskSessionUnavailable` into `admission_unavailable`.
Its absence reader also advertises `not_created/retry_allowed:true` without
checking whether the owner can accept anything. That misleading retry advice
was reproduced in isolated tests for FAILED, CANCELLED and COMPLETED.

The repair changes the existing authenticated sender-receipt path:

- An absent exact intent rechecks its exact authorized task/session and returns
  `session_terminal`, `retry_allowed:false`, `continue_allowed:false`, and
  `continuation:exact_session_recovery_required` for terminal owners.
- A wrapped atomic state-race rejection returns `session_unavailable`, disables
  retry and requires `correlate_session_state`.
- Existing transcripts with UNKNOWN delivery and existing FIFO entries retain
  their original identities, hashes, statuses and replay prohibition.
- Receipt reads never arm a session, notify a terminal queue or launch a process.
  No terminal admission guard was relaxed and no recovery authority was granted.

`exact_session_recovery_required` is a disposition, not a new tool or permission.
This fixes reporting, not the underlying five-minute silence.

## Existing supported recovery and the exhausted boundary

There IS an existing browser/user operation: authenticated WebSocket action
`session.recover`, with payload:

```json
{"task_id":"afdb2ef3-06ca-4cd5-a074-c4e691679da9","session_id":"<one exact verifier above>","action":"resume"}
```

This is a conditional operator recipe, **not executed or attested safe for a
blind retry**. It requires the existing user's task access and `session.prompt`
authority. Plain `resume` preserves the saved resume identity and calls
`ResumeTaskSessionWithOptions` without a prompt continuation. It waits for
readiness; it does not itself submit a verification prompt. It can nevertheless
prepare/relaunch a runtime, refresh launch configuration and act on workflow
parking. It is not a metadata-only probe. `runtime_retry` can choose
`fresh_start`, which clears resume identity; neither is an acceptable substitute.

The public local feature response confirms authentication is enabled. No
authenticated user recovery handle or task-bound delegate is exposed to this
Support request or the Coordinator receipt tools. The broker's temporary broad
operator token mechanism is not a scoped verifier-recovery operation. Support
did not mint one, read a cookie, impersonate a user, invoke raw control endpoints,
or change FAILED to WFI through database writes. Legacy message dispatch also
rejects FAILED targets; omitting the intent is not a recovery route.

**Smallest next action:** the lifecycle/platform owner uses its existing
authenticated recovery control for these two exact sessions after the preflight
below, or provides a backend-owned, exact-task delegated equivalent. No new
profile/model, source owner or provider credential grant is needed. An existing
authenticated user operation does not itself require a production restart.
Exposing a new delegated operation or installing the reporting candidate would
require the separately authorized production change described below.

## Guarded recovery and owner acceptance

1. Bind the authenticated actor to this workspace/task, existing MAIN and the
   exact side-session identity. Pin current step, profile
   `c06ad00e-0da1-429a-8174-54f97164a289`, configured model `gpt-6.1-sol`,
   incarnation and failed turn from the receipt. Reject any mismatch.
2. Under backend lifecycle/writer admission, establish that each old execution
   is closed, no competing recovery owns the session, original turns are closed,
   no new queue/Human input has appeared, and current WIP/incarnation/ownership
   fences permit readiness. Preserve MAIN and all independent verifier roles.
   Account explicitly for UNKNOWN original delivery; never replay it or claim
   that watchdog silence proved non-execution.
3. Prefer the existing authenticated `session.recover` action `resume` on the
   same row, with no prompt and no replacement/fresh-start permission. Stop on
   missing continuity, unresolved writer ownership, branch/environment repair,
   profile/model drift, deferred admission or Human gate. Do not waive a guard.
4. Acceptance requires an exact task/session protocol-readiness receipt, same
   profile/model/incarnation and step, retained failed transcript/turn/hash, and
   no new task execution prompt or application/container change. A success
   envelope or database state alone is insufficient.
5. Only after that receipt may the Coordinator send a new verification handoff
   to each restored original owner. The original UNKNOWN intents stay preserved.
   Independent owners, not Support, produce any actual command/verdict. No
   acceptance command or verdict was generated during this request.

## Source, tests and candidate installation plan

Both checkouts were inspected. Canonical `upstream/main` was fetched and pinned
at `0b208ce00a0ae00955696381006364dbc3b7424a`. The custom native receipt extension
is absent there; this maintenance patch uses the explicitly verified restored
deployed hotfix baseline `56d742982b8c2daf0a13cb72c453aecd3471b6a7`, fetched from
the named personal-fork support ref. It does not treat `origin/main` as canonical
or replace deployed fixes with upstream. The isolated source branch is
`support/verifier-admission-1be028a8`; its exact commit is in the receipt.
Unrelated dirty/untracked files in both user checkouts were preserved.

The source commit is
[`e8f963523d9d10f85af7c0d0d2c45ae0d1fdff91`](https://github.com/yattdev/kandev/commit/e8f963523d9d10f85af7c0d0d2c45ae0d1fdff91).
The exported patch is `patches/kandev-verifier-admission-1be028a8.patch`, SHA-256
`1094e080a5f61cb2b629939a480d4a3bcbc1e5f010f73aa32f96b713f16d40ad`.

New tests cover terminal absence, read/send/continue without launch, unchanged
failed evidence, FIFO identity, UNKNOWN delivery, foreign caller rejection,
state rechecks and wrapped atomic state-race disposition. Race-enabled native
handler/server/repository regressions passed. PostgreSQL coverage was not run;
no SQL/schema logic changed. Changed-package golangci reports zero issues.
The regression failed on the old misleading retry flag before the fix.
Additional race-enabled recovery checks passed for wrong-task rejection,
Office scheduler ownership and FAILED-session resume-token preservation.
Repository hooks, including architecture, public-copy and commitlint checks,
passed after restoring the missing hook executable in a temporary environment.

The compatible backend candidate was built offline with Go 1.26.0, CGO/FTS5,
trimpath, buildvcs disabled and stripped symbols:
`/tmp/kandev-verifier-admission-1be028a8-candidate`, SHA-256
`745d82d47003d5fe1d5a8caa11e9ecaf54ebd46eac075299b278227faf1d158f`.
It is not installed. The source commit and exported patch are review artifacts,
not an issued execution capability.

Before any separately approved candidate installation, revalidate deployment
identity and every still-required hotfix against the documented provenance in
`OWN-ANSWER-DISPOSITION-6CEF6EFD.md`. Preserve the existing native/remote agentctl
pair, frontend assets and unrelated reviewed fixes. Integrate the pinned patch
into that exact superset, rebuild/test it and record all candidate hashes.
Snapshot the current image/overlays; activation must use
`scripts/kandev-safe-deploy --build` from deployment main, followed by required
HTTP-200/security/deployment tests. On readiness failure use its verified
rollback; a rolled-back candidate remains BLOCKED. No runtime/queue replay is
an implicit MCP refresh or rollback step. Revoke no task data and clean up no
historical resources. No installation or production restart was attempted.

Production container `3b95b8dbafb8d29c6956e06467cfff09511ff1592f654aec0fe5fa2f9668d172`
and image `sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`
were observed with the documented backend/native-agentctl hashes. Support made
no lifecycle, profile/model, credential, board, trial or provider change.
