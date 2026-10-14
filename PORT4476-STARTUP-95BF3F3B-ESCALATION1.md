# PORT4476 same-owner startup: escalation audit

Request `95bf3f3b-8edd-4995-8209-0e652981df39` remains BLOCKED for actual MAIN
command acceptance. The [original exact timeline/receipt](https://github.com/yattdev/kandev-service/blob/339d9f5/PORT4476-STARTUP-95BF3F3B.md)
is preserved. Original intent disposition is **UNKNOWN**. It is neither classified as executed
nor as safely failed before execution. No replay or new owner is claimed.

## Authority and source audit

Both named checkouts were inspected again. Deployment is on main; source remains
`cfd6bdf65ae6f631d7701c105791a099c0325cc3` with unrelated edits preserved. The
restored deployed-lineage worktree at
`80fdc4ce072ced98c6d72996f02e2c578d64dd82` is clean and contains the audited
receipt, outcome and replay guards. No new source worktree, implementation,
overlay replacement, deployment or live adoption was created.

Earlier reviewed host diagnostics succeeded and are retained, including exact
execution logs and the fixed diagnostic-log absence. An agent-facing ban on raw
host/socket access was not used as a restriction on reviewed Support diagnostics.
No useful reviewed read escalation was left unrequested. Conversely, the request's
explicit no-credentials/no-restart/no-live-adoption/no-source-implementation
constraints are not authority to launch through a raw host route.

Even treating safe same-session continuation as authorized by the goal, the
installed controls do not safely continue this transcript-only unknown receipt.
This is a concrete custody/operation gap, not only a blanket permission argument
or an upstream-only classification.

## Additional supported paths checked

The preserved concrete execution `69a2d004-3360-4591-ac36-be5c2b8d09f8`, prompt
generation 11, was removed after the watchdog failed original turn
`174386fb-bca5-4731-b260-8fb9c44f3662`. The turn completed and the original queue
row is absent. `continue_task_message_kandev` can recheck an eligible queued
message; it rejects FAILED owners and cannot replay a transcript whose provider
acceptance is unknown. Expired-lease takeover has no original queue row here.

The existing instance outcome API retains an in-memory last-terminal-event slot,
with a control-process-local integer turn ID. It is not a durable ledger keyed
by the original Kandev turn UUID. Successful instance removal deletes that slot;
the read handler reports a missing instance rather than a retained result. It
therefore cannot recover PORT4476 acceptance/effects after the recorded teardown.
No production raw-control GET/ack or credential was used to bypass this boundary.

Automatic transient retry is another real existing path, but it requires both
matching safe prompt-attempt evidence (known, no output/effects, exact execution /
generation) and a classified short transient failure. The original watchdog
notice is not such an attestation. A transport disconnect caused by the later
platform stop must not be relabelled as an earlier provider failure to activate
replay. No retained pre-result-safe receipt for this attempt was supplied.

Generic `resume`, workspace restore and `start_created` do not atomically settle
the original unknown-delivery receipt and prove sole MAIN writer custody. Resume
can perform runtime cleanup; workspace restore can create/reuse an execution from
another session. The reviewed host exact-stop helper only preflights/stops a
bound process; it is not a start or unknown-delivery reconciliation capability.
It was not invoked. CI's primary projection is not source ownership and cannot
be used as a recovery writer.

## Validation and correlation

Three additional existing tests passed under Go 1.26.0, `-race`, `-count=1`:

- `TestHandleTransientFailure_ReplayRequiresPromptAttemptEvidence`.
- `TestHandleTransientFailure_ReplayRejectsOutputOrToolEvidence`.
- `TestPromptAttemptEvidence_RejectsReplacedAttempt`.

They use isolated mocks, not the live task/provider. The run completed before
dependent work. The original seven watchdog/receipt tests and the three instance
outcome/generation tests recorded in [C275](https://github.com/yattdev/kandev-service/blob/bb9ff871880bddb70a8dd24c7eb9a4ea442f6a4e/C275-STARTUP-8F0D9649.md)
remain applicable and were not repeated. No new source change was made.

The two C275 admissions establish the same demonstrated dispatch → five-minute
watchdog → completed-turn/instance-removal class as PORT4476. They do not prove a
common lower-level provider/transport cause. The 531/86 missing-Git and 29
missing-executor admissions remain distinct pre-launch failures. No duplicate
repair worker or job was created for any of those targets. No live status search
was repeated in this pass.

## Exact remaining operation and custody prerequisites

The missing operation is backend-owned reconciliation of an uncertain original
handoff plus exact same-task writer custody before admitting the next execution.
The Kandev lifecycle/platform operator owns that boundary. Its smallest next
action is an exact PORT4476 custody preflight/decision pinned to:

- Caller `a68df3ae-aaf5-4591-a46d-9d73db62e46d` /
  `13d8c011-6e49-40ef-80e9-2f1445296d06`, workspace
  `2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`.
- Target task `6a9c10e2-7f7c-4d78-8b5c-579e945ab297`, MAIN session
  `2ea0f20a-0e7e-4264-ac6e-4474c58a8c88`, incarnation
  `656088c8-aeae-438f-a4eb-9780e1d69ead`, original intent
  `PORT4476-CONTRACT-INTEGRATE-20261014-v1`, message
  `f7177d3f-3e4b-568c-a6b7-ac435b40acd0`, original turn and execution above,
  environment `3f2c19b9-dd87-40e5-a41a-446d81b049b9`, generation 1 and unchanged
  Human-QA lane `814573a3-f2a3-4f42-8706-4f2997401fa6`.

Before any resume, that decision must provide retained acceptance/outcome evidence
or explicitly account for UNKNOWN effects; verify old execution/write-capability
closure; preserve original packet hash, completed turn, FIFO, saved-conversation
identity and all unique source/worktree/loader/PG/Human artifacts; and establish
one backend-enforced MAIN writer claim with Human/pending-input/WIP/incarnation
fences. Keep CI/Review/QA state and read-only rights intact. Do not reset turn
completion or manufacture another original queue row.

Prefer original-session recovery. Any successor execution must have an explicit
custody binding to the old execution/turn before admission, with no competing
writer and no copied work order. The original packet remains the sole instruction
source. Require an idempotent recovery receipt and actual assistant command
reading local task instructions in MAIN, correlated to that original intent.
A STARTING state, API success or another recorded packet is not acceptance.

The current primitives cannot produce that complete recovery receipt. If adding
or activating one is necessary, a separately scoped decision must cover this
exact operation; source implementation and runtime restart/adoption remain
excluded here. No generic provider/account grant or unbounded host authority
is needed or requested.

Only this audit and content-free receipt were committed/pushed. No live recovery,
stop, replay, queue/task/lane mutation, PR/source/provider work, credential access,
restart, adoption or deployment occurred. MAIN's original work order and all
preservation evidence remain intact. No Human relay is required.
