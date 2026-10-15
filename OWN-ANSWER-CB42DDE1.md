# Exact preview approval reconciliation: cb42dde1

Status: **BLOCKED**. The existing supported reconciler cannot safely bind this
historical envelope. No live reconciliation, delivery, rejection, preview check,
application build, runtime change or deployment was performed. Do not retry the
unchanged call or ask for another Human approval. This is a different question,
answer and session from Support `6cef6efd`; that case's rejection disposition
does not apply.

## Verified evidence

Both named checkouts were inspected, including their unrelated dirty/untracked
files. The deployment checkout remains on `main`. Canonical
`https://github.com/kdlbs/kandev.git` upstream/main was fetched and verified at
`8c6f4b800b123d5f074cc006a88893c807c584b9` before the isolated source checkout.
The reconciliation source is the existing review branch at
`80fdc4ce072ced98c6d72996f02e2c578d64dd82`, not a duplicate implementation.
Its format-reporting change is not installed in the live preview source lineage.

The content-free machine receipt is
[support-evidence/own-answer-cb42dde1.json](support-evidence/own-answer-cb42dde1.json).
Read-only host inspection identified container
`2d2b866221ecad48a67383db0dcae20a15128b38ad477ca41b406e451a5dcdbe`, image
`sha256:7cd0c17fd24fd6c7e84ae29a3a0d4c374942aaf3def54a4716e26dd149e3422f`,
started `2026-10-15T00:05:57.269376664Z`, and the actual `/data` mount. No
environment, model, claim, configuration or credential contents were inspected.
The deployment checkout's `host.env` is absent; no placeholder hostname was used.

The two exact messages were read through a read-only SQLite connection scoped to
task `a68df3ae-aaf5-4591-a46d-9d73db62e46d` and session
`1a1e64ab-926b-4c9a-a862-967d815b8779`. This session is RUNNING with incarnation
`21de8c87-3d6f-4c1f-a01f-50cbab3c6c68`; the earlier session is CANCELLED.

The original question remains pending/disconnected, is the sole message in its
bundle, and has no binding receipt. Both supplied hashes match. The Human
message is unedited. Its metadata contains **only** the native client request
fingerprint, with no `queue_admission_ids`. Its body has two selected-response
and feedback pairs. It matches zero complete question/option envelopes.

The original local receipt remains 9063 bytes with SHA-256
`d9e80f497a3405a3d0e1934c50b9c4c64fc5fe877351eee9c18fb36343f083f5`.
Neither it nor either live message was edited. The reported NOT_CREATED handoff
and C300 outcomes are retained as caller evidence, not claimed as newly queried
or retried by Support. The separate Ubuntu fact grants no reconciliation scope.

## Why the existing operation refuses

The failure occurs before option parsing:

1. `internal/task/ownanswer/binding.go:nativeHumanIngress` requires a native
   request fingerprint **and** exactly one queue-admission ID. Direct native
   `message.add` can persist a legitimate user message with only the fingerprint;
   see `internal/task/handlers/message_handlers.go`. That fingerprint is an
   idempotency digest, not the retained current-incarnation admission proof
   required by this reconciler.
2. Independently, `exactHumanOption` accepts the complete recorded context,
   question title/prompt, and one exact recorded option label. This comment
   envelope quotes a recommendation and feedback; it does not contain that
   structured answer. Even supplying authentic queue admission would leave it
   unsupported.

`apps/web/lib/state/slices/comments/format.ts` serializes selected response text
and feedback into Markdown and drops their selected-message IDs. The persisted
Human message has no typed question/pending/option linkage. Matching a quoted
recommendation semantically and assigning an option would add authority that
the existing closed matcher deliberately does not possess. Accepting any native
text under caller-supplied question IDs would also let an unrelated fact settle
a pending approval. Neither relaxation is a safe repair.

The previous reporting patch returns `ANSWER_FORMAT_UNSUPPORTED` only after
native admission and the other guards pass. It therefore cannot classify this
fingerprint-only message as a provenance-confirmed format disposition. Installing
that patch alone would not unblock this case.

The normal authenticated clarification `/respond` route is not a replacement:
an affirmative response to a disconnected question invokes detached resume.
It would resubmit an answer and dispatch work. Rejection would alter the Human
decision. Generic SQL edits, impersonating Root, manufacturing admission rows,
copying credentials, memory patching and forced runtime refresh are excluded.

## Missing capability and smallest escalation

The precise missing capability is a **trusted historical evidence-binding path
for a direct native comment**, extending the existing reconciliation owner. It
must establish protected direct-ingress provenance and an authoritative link
from the complete existing Human body to the exact original question. It must
retain that body verbatim, audit the complete tuple and original receipt, and
perform no choice inference, new answer admission, dispatch or queue operation.
The current records lack the typed link; a source patch cannot recover an
immutable link that was never persisted. Coordinator assertions and an
agent-writable local receipt cannot manufacture one.

Route this evidence to the trusted reconciliation maintainer/operator through
the existing Support escalation chain for an authorized exact-evidence binding
mechanism using the existing approval. This requests no repeated Human decision.
Any mechanism requiring new installed code has a separate activation dependency:
runtime/deployment/build are expressly excluded by this request. No broader
token, database or caller authority has been requested or granted.

## Bounded caller acceptance, only after that capability exists

Preserve this exact input identity for the existing own-session operation:

```json
{
  "question_id": "preview_trusted_model_validation_20261015",
  "pending_id": "ecadc06d-bd52-456a-96bc-09e75493e4df",
  "question_message_id": "89e5496c-cf37-4746-9253-52dbc0d8e991",
  "question_sha256": "d02f816db3fd1ceb85e1a18da6b272c10dd15bd9883ea54798a45ed8ca25f44d",
  "answer_message_id": "8ef1ea88-3d79-44ca-a84c-6da258063195",
  "answer_sha256": "8f9dc25bb64576d42515886702df42fa76de83bd73aafe4edbf0bd28355b0f1e"
}
```

This is a preserved tuple, **not an instruction to retry today's tool**. Root
owns future acceptance in its existing session. Require proof for this tuple,
original receipt hash, workspace/session incarnation, and complete original
Human body; reject changed hashes, foreign/inactive callers, duplicate question
matches, absent provenance, already-bound conflicting evidence and live waiters.
Require one immutable receipt, durable own-status readback, and an identical
retry returning the same receipt with `changed:false`. Every independent
question, queue entry/order and task/runtime identity must remain unchanged.
No selected option may be fabricated from feedback. Failure must remain a
non-retryable refusal, never approval.

Only after accepted own-status readback should Root perform its original
same-intent delivery with the original receipt/candidate identity and normal
delivery readback. A remaining independent Human-input barrier stays enforced.
Support sends or replays neither that delivery nor C300.

## Verification and persisted source coverage

Test-only coverage was added beside the existing repository reconciler in the
isolated branch `support/own-answer-comment-boundary-cb42dde1`. No production
code or trust guard changed. The synthetic two-comment producer shape proves:
direct comments and direct exact-choice text both fail admission proof; queued
comments independently fail format matching. Snapshots assert preservation of
all fixture messages, an independent question and Human fact, every task/session
field, queue-admission receipt and two ordered FIFO entries.

The following race-enabled run passed all four packages, including existing
exact-choice success/idempotency and own-question/clarification contracts:

```sh
go test -trimpath -p=2 -race ./internal/task/repository/sqlite \
  ./internal/mcp/handlers ./internal/mcp/server ./internal/clarification \
  -run 'Test(OwnAnswer|OwnQuestion|ResolverOwnAnswerDisposition|HttpRespond)' -count=1
```

The new tests cover existing behavior, so no production RED/GREEN change is
claimed. PostgreSQL acceptance remains environment-gated; this incident uses
SQLite. Application binaries were not built. Deployment tests/recreate were not
triggered because no deployment/runtime file changed and deployment is excluded.
The adjacent patch contains only the new source regression test; final commit
and lint evidence are recorded in the machine receipt.

Source test commit: `bb985c2baba703df7b20564d9336f3f256e8544f`, parent
`80fdc4ce072ced98c6d72996f02e2c578d64dd82`. Changed-package golangci-lint:
**0 issues**. Formatting and diff whitespace checks pass. The isolated clone
has no active commit hooks; those checks ran directly without a hook bypass.
[Exact regression patch](patches/kandev-v096-own-answer-comment-boundary.patch),
SHA-256 `159c5f3cb26345b67ee14dbeed53b9b639d488ad55621e6e1025a1f026032482`.

## Final escalation audit

Both automatic escalation passes are complete. The
[pass 1 interface/provenance audit](OWN-ANSWER-CB42DDE1-ESCALATION1.md) and
[final machine audit](support-evidence/own-answer-cb42dde1-escalation2.json)
retain BLOCKED. Reviewed host access succeeded; another host privilege grant
would not supply the missing authenticated no-dispatch operation.

Final source review also checked the internal per-question update interface:
it is a cancel-path helper, not a caller operation for binding an already
delivered affirmative answer. Direct use of internal writers would bypass the
reconciliation guards. Inbox sidecars alter visibility, not answer linkage.
The broker has no independent own-answer repair route. No live polling or
mutation was performed during the final static audit, and no unchanged test
suite was rerun.

The terminal dependency is the reviewed historical direct-native binding
capability described above. Changed backend code also requires activation
authority, explicitly excluded here. The smallest next action remains trusted
reconciliation-maintainer review using the existing approval and exact pins;
no new Human approval, rejection, unchanged retry or handoff replay is proposed.
The source commit is test-only and must not be reported as a deployed repair.
