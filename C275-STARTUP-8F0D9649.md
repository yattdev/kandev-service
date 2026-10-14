# C275 material incident expansion: exact startup/continuation custody

Request `8f0d9649-2703-4e73-9ef4-682c114b4e12` is BLOCKED for actual command
acceptance. These are two new failures, correlated with the existing no-output
incident without starting another repair worker. Both original intents have
execution disposition **UNKNOWN**: platform prompt dispatch occurred, but
provider acceptance and effects cannot be established from the retained evidence.
Neither intent is classified as executed or safely failed before execution.

## Exact original identities

Caller task/session is `a68df3ae-aaf5-4591-a46d-9d73db62e46d` /
`13d8c011-6e49-40ef-80e9-2f1445296d06`, workspace
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`. Both exact target records were verified in
that workspace. Their Work lane remains `0541923c-2d38-478e-8573-3c5e27e37a31`.

| Field | Visibility owner | 3686 owner |
| --- | --- | --- |
| Task | `9349b6e5-a167-4d88-af14-cb355015e3dd` | `3a64829a-8eff-4162-bb4d-166f8df5b4c6` |
| Source session | `48815ef5-da33-466b-9da8-fb0f2b2b6a82` | `07c8be43-af44-40fb-bcc9-b9581fe131bd` |
| Intent | `C275-VISIBILITY-NEXT-20261014-v1` | `C275-3686-QA-RESUME-20261014-v1` |
| Original message/queue ID | `55c2085b-7109-5921-bcbf-70111923eb73` | `83d75fd7-014c-59a9-8be2-36af5db29fb7` |
| Original turn | `c7a5bafa-f52f-460f-b056-e5892e901f13` | `27592772-791a-498c-997f-aadccf4b6f81` |
| Incarnation | `4ec10277-f335-493c-92bc-da779e3e2a6b` | `32924f2d-8a82-4232-88a4-c1bcdddc5de6` |
| Environment | `63cdf96a-4997-47bd-a097-b3916932d9c6` | `c3b0a164-eab0-44f9-ae30-3e8dc9261e2c` |
| Concrete execution | `aba2823e-198d-4910-8005-c504f396d8f6` | `d1b936fc-e146-4631-ab84-befe5269500c` |
| Prompt generation at teardown | 12 | 14 |
| Execution disposition | UNKNOWN | UNKNOWN |

Original packet SHA-256 values are
`039f5fcd3c965fcd98b589d10a0a42e8a28c1d4d619de872dff4061fc95f5063` and
`dbadc42dc64c55729368785a7a742a8c3b7d3f7d1762162031ad90e9672fc6fa`.
Stored sender/intent/incarnation/lane metadata matches the supplied admissions.
No task packet was relayed or printed.

Caller-supplied preserved source references are
`8f0dbfcef4b25680e5ccc94bdbf6f54f9fd18c18` and
`6129f4f2b1aa7027e99ea64f8265bbfceab15eae`, with local loaders/bootstrap/archive.
Support did not inspect or mutate their source, branches, index, worktrees, local
edits or data, and does not claim independent Git/archive completeness from those
references.

## Exact platform failure sequence

One fixed historical log window, 03:08:00–03:14:00 UTC on 2026-10-14, was filtered
to only the two supplied task/session/concrete-execution tuples. Only lifecycle
event names and ownership/status fields were returned. The sender's MCP handoff,
receipt and conversation reads are not source-owner command output.

| UTC event | Visibility owner | 3686 owner |
| --- | --- | --- |
| Original turn starts | 03:08:04.135588447 | 03:08:43.682150823 |
| Lifecycle `sending prompt to agent` | 03:08:04.234 | 03:08:43.762 |
| Watchdog `never_started:true` | 03:13:04.236 | 03:13:43.764 |
| Session FAILED updated | 03:13:04.297824433 | 03:13:43.839193409 |
| Platform forced-stop begins | 03:13:04.311 | 03:13:43.852 |
| Original turn completed | 03:13:04.315501485 | 03:13:43.856001242 |
| Instance removed from tracking | 03:13:07.143 | 03:13:46.677 |

The stall is exactly 300.002 seconds after the logged prompt preparation/dispatch
boundary in each case. The installed watchdog counts turn-content progress,
not merely live sockets, metadata/catalog updates or sender status queries. It
validates current execution/prompt generation and activity epoch, persists the
no-output failure, claims teardown ownership and stops that execution. Both
conversations contain only their original user packet and exact watchdog error
after admission, with no command/assistant progress recorded.

Error identities are `ff1727df-0171-47ef-b182-a599349f4d48` and
`c8d2c8f0-b0f3-4058-9a92-7bca17c5447e`. Both selected sessions are now FAILED,
nonprimary; both executor records are standalone, failed and resumable. Their
record creation timestamps predate these admissions. A resumable flag is not a
live-execution or no-effect attestation. Platform removal logs do not provide
exhaustive physical descendant/write-capability closure.

No earlier provider/transport failure was visible in this fixed lifecycle window.
The lower-level cause of silent progress remains UNKNOWN; do not replace that
unknown with a guessed provider/account/profile fault. No host credential,
raw control endpoint, provider call or direct CLI resume was used.

## Correlation and controls

- [PORT4476 / 95bf3f3b](https://github.com/yattdev/kandev-service/blob/339d9f5/PORT4476-STARTUP-95BF3F3B.md): same demonstrated failure class—existing execution prompt dispatch,
  five-minute no-progress watchdog, completed original turn and instance removal.
  A common deeper provider/transport cause is not established.
- [531/86 / 811127b4](https://github.com/yattdev/kandev-service/blob/b8a3ca7/BOARD-LOADER-811127B4-ESCALATION2.md): distinct pre-launch missing Git administration metadata/recovery consumer
  refusal, with retained reserved FIFO entries. Do not apply its lease-recovery
  recipe to these completed/absent-queue cases.
- [29 / 390643ab](https://github.com/yattdev/kandev-service/blob/242b89f/HQA-DISPATCH-390643AB-ESCALATION2.md): distinct missing exact executor record and unsafe environment reuse boundary,
  plus failure-release claim mismatch. No duplicate repair/job was started here.
- The successful 03:14–03:15 controls are caller-supplied observations, not newly
  probed resources. They support that this was not a blanket sender-tool outage;
  they do not establish acceptance, profile health or permission to replay these
  two original messages. No partial control ID was expanded or queried.

## Missing reusable operation, not a generic wait for a PR

Both original transcript messages and completed turn IDs remain. Their queue
rows are absent, each selected session has zero queued rows, and no ordinary
dispatch claim exists for either original ID. The native transcript-only receipt
therefore remains `recorded_delivery_unknown`, retry=false, continue=false.
`continue_task_message_kandev` only rechecks an eligible original queued message;
it does not replay a transcript of uncertain acceptance and rejects a FAILED
owner. Normal expired-lease takeover cannot apply when there is no queued row.

There is an existing instance turn-outcome API. Its contract was inspected rather
than bypassing authentication to call the production control server:

- Retention is an in-memory last-terminal-event slot on the live instance.
- Its integer turn counter is local to the control process, not the durable
  UUID of either original Kandev turn.
- Successful `StopInstance` deletes that instance from the manager. Peek then
  distinguishes missing instance from live instance with no retained event; the
  read handler reports 404 for the former.

Thus this API is useful during retained-instance recovery but is not a durable
acceptance/effect ledger for these removed instances. There is no demonstrated
saved outcome/checkpoint bound to these original UUIDs. No production outcome
GET/ack, token read, raw host/broker bypass or fabricated terminal result occurred.

The unavailable primitive is **one authenticated backend operation that resolves
an uncertain original delivery and establishes exact same-task writer custody
before resuming or admitting a successor execution**. It must preserve original
message/turn/FIFO history and deny a new writer on ambiguous custody. Generic
resume, workspace restore, direct CLI resume, primary promotion or duplicate
message admission is not that operation. Other same-task sessions remain WFI
(two per task, including a primary projection); no Review/QA/CI session was woken
or converted into a source writer.

## Concrete custody-preserving recovery prerequisites

The Kandev lifecycle/platform operator owns this recovery boundary. The smallest
next action is an exact incident-scoped custody preflight/decision for these two
original tuples, with these required outputs before any resume:

1. Immutable references to the original packet hashes, completed turns,
   incarnations, lane, environment owner/generation, source head and all unique
   local edits/loaders/bootstrap/archive/data/plans. Preserve the old records;
   never reset turn completion, delete/reinsert the queue or rewrite history.
2. Authenticated old-execution prompt acceptance/outcome evidence, if retained,
   and physical write-capability closure for each exact execution/generation.
   If acceptance is unavailable, record UNKNOWN explicitly and obtain a concrete
   recovery decision that accounts for unknown effects. Silence is insufficient.
3. A backend-enforced sole source-writer claim across every session/attempt of
   each task, with Human/pending-input/WIP/incarnation and unchanged-lane checks.
   Keep other sessions and their read-only rights intact; do not falsify their
   states or infer writer rights from the primary projection.
4. Prefer original-session recovery. If a successor runtime/session is necessary,
   require an explicit predecessor-to-successor custody binding and revocation /
   closure attestation before admission. Pin old/new attempt identities, the
   exact unchanged project resources and original work-order reference. Do not
   relay a fresh copy of the prompt or make a substitute Review/QA/CI owner.
5. Issue an idempotent recovery receipt and require actual same-target assistant
   command output reading local instructions, tied to the original work-order
   identity and that custody chain. Preserve the original completed turn as
   history; a successor turn must not impersonate or overwrite it.

This is a concrete precondition/operation gap, not a recommendation to wait for
an unspecified source PR. The installed primitives do not provide that complete
operation. This request explicitly excludes source changes and broader grants;
none was implemented or activated to bypass the gap. Any necessary platform
change/activation needs a separately scoped decision on this exact contract.
No production restart, profile/model change, direct Codex resume or general
administrator/provider grant is proposed here.

## Verification and preservation

Both named checkouts were inspected. Deployment stays on main; source remains
at `cfd6bdf65ae6f631d7701c105791a099c0325cc3` with unrelated tracked/untracked
files preserved. Source review used clean restored deployed lineage
`80fdc4ce072ced98c6d72996f02e2c578d64dd82`; no new source worktree or source file
was created/edited. This is not an upstream-only classification.

Three additional existing regressions passed under Go 1.26.0, `-race`, `-count=1`:

- `TestGetTurnOutcomeReturns404ForUnknownInstance`.
- `TestGetTurnOutcomeRoundTripsARetainedOutcomeRepeatedly`.
- `TestClearTurnOutcomeRetiresPriorOutcomeAndRejectsOlderLateEvents`.

These use isolated mock servers/instances; no real provider or task execution
was launched. The seven previously green PORT4476 watchdog/teardown/unknown-receipt
tests remain applicable and were not repeated without a new implementation
change. Every yielded test run completed successfully. Reviewed read-only host
diagnostics and isolated mock-socket escalation succeeded.

Only this material-expansion report and content-free receipt were committed /
pushed. Support made no task-state/queue/source/profile/model/lane change,
provider/credential operation, runtime recovery/adoption, deployment, cleanup,
force push or duplicate worker/job/packet. No actual command acceptance is claimed.
