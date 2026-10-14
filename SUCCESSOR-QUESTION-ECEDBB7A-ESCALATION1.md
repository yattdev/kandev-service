# Original-question continuity: first escalation audit

Request `ecedbb7a-b415-49f2-913f-b8942e70a166` remains BLOCKED on canonical
original-record availability and authenticated continuity. The [original report](https://github.com/yattdev/kandev-service/blob/c82b2de/SUCCESSOR-QUESTION-ECEDBB7A.md)
and supplied question/pending/message identities remain unchanged. No genuine
answer, successor-read capability, adoption grant or recovered lifecycle is
claimed.

## Additional routes checked

Both checkouts were inspected again. The named source checkout remains at
`cfd6bdf65ae6f631d7701c105791a099c0325cc3`; it does not contain the installed
own-question hotfix. The clean restored deployed-lineage worktree at
`80fdc4ce072ced98c6d72996f02e2c578d64dd82` contains the reader being audited.
Unrelated source and deployment edits remain intact. No new source worktree,
application patch, remote base inference or deployment was made.

A reviewed read-only host check completed successfully. It was restricted to
caller task `a68df3ae-aaf5-4591-a46d-9d73db62e46d`, with its workspace verified as
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`. It checked all of that task's own sessions
for exactly the supplied:

- Stable question ID `coordinator_candidate932_boundary_20261012`, in both the
  current metadata key and legacy nested `question.id` key.
- Pending ID `b1606b82-08a3-45cf-9310-0c1fd27c10ba`.
- Message ID `ad22fe2d-4ec1-4293-985b-0add15e2c45d`.

The lookup removed message-type and author assumptions, admitted the legacy
empty-message-task fallback through session ownership, and rejected conflicting
session ownership. It selected identity/status metadata only, with a 17-row
ambiguity bound. **Zero candidates matched.** No question or answer content was
selected; no foreign owner, hidden ID, old database or archive was queried.
This complements the prior exact-message lookup within the authorized workspace;
it does not claim that the historical record is globally nonexistent.

The live schema has no separately named question/continuity table; its matching
sidecar is `clarification_inbox_sidecar`. Source review shows that sidecar holds
only per-user pending-ID dismiss/snooze state. It has no canonical message owner,
recorded answer or predecessor/current authorization. Its user rows were not
read. Inbox dismissal, snooze and restore cannot resolve this incident.

The history reader also derives its bundle identities from
`task_session_messages`; it is a workspace history projection, not an independent
original-answer ledger or successor grant. Paging that broader history would
not recover an absent exact native row or establish the missing continuity.
No history page or foreign content was read.

The broker exposes no own-question continuity/adoption operation. The reader's
principal requires the exact current caller/session. `PreviousSessionID` in a
conversation mutation is expressly a transient UI receipt, not a persisted,
server-authenticated successor-question permission. Spoofing the predecessor
session, broad conversation reads or host policy changes cannot safely supply
that permission. No available reviewed diagnostic escalation was rejected or
left unused where it could resolve the bounded ownership check.

## New bounded validation

A [synthetic same-task predecessor fixture](support-evidence/successor-question-ecedbb7a-scope-test.go.txt)
passed under Go 1.26.0, `-race`, `-count=1`:

```text
TestSupportSuccessorQuestionSameTaskDoesNotImplyContinuity
ok github.com/kandev/kandev/internal/task/repository/sqlite 1.174s
```

It creates an original synthetic question on a predecessor session and a current
session on the same task. The current reader returns no predecessor row. Reading
through the original repository scope returns only that original metadata and
no body; before/after equality verifies preservation of the original synthetic
envelope. The original-scope repository read is not a callable permission grant
to the current caller. The test neither fabricates a real answer nor implements
a successor resolver.

The temporary test was removed after completion; the restored source worktree
is clean. The fixture is retained as review evidence outside application source.
The three prior race-enabled identity/catalog/scope regressions remain valid;
unchanged code did not require repeating them. No live API acceptance is claimed.

## Exact disposition and remaining owner

This is an unavailable identity/provenance input, not an agent-facing host
restriction or an upstream-only platform classification. Source implementation
cannot reconstruct an authenticated original record or answer that the permitted
source does not provide. General workspace authority does not imply own-question
access to an unproved predecessor. This request explicitly excludes a new
source/live adoption grant and deployment.

The smallest next action remains with the **Kandev platform/data owner**: supply
an existing canonical original-record reference and server-authenticated
predecessor/current continuity receipt through an authorized exact-record source.
It must identify predecessor task/session/workspace, original question/pending/
message and envelope digest, source provenance, and any native recorded-answer
binding. Authority must be established before answer content is read. No new
Human answer or generic admin access is needed. If no such retained record can
be supplied, record original identity/answer as unavailable rather than inventing
a lifecycle, recreating the question or inferring candidate approval.

Root's safe current recipe is unchanged:

1. Preserve the exact historical tuple as `UNRESOLVED_ORIGINAL`. Interpret
   `not_created/retry_allowed:true` only within the current reader namespace;
   do not recreate or retry the known historical question.
2. Reconcile the Need-input note to **original identity unresolved**, not a fresh
   Human ask. Candidate bounded-proof/source/history/commit approval remains
   **UNKNOWN**, with its gates held.
3. Continue visible monitoring/board work under the existing direct Human override.
   Do not infer the missing candidate-specific answer from the generic reminder.
4. Keep G1 and request `6cef6efd-df84-40bd-85f0-40577b9f52c0` separate. Consume a
   genuine answer and change candidate approval tags only after authenticated
   original-record retrieval.

Support has not mutated tags, questions, messages, sessions, tasks or runtime;
created/cancelled/answered a question; issued a grant; read foreign question
content or credentials; deployed; or duplicated G1. Only this review, content-free
receipt and isolated fixture are committed and pushed. No Human relay is needed.
