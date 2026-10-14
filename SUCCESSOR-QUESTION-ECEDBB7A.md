# Original question continuity: ecedbb7a

Support request `ecedbb7a-b415-49f2-913f-b8942e70a166` is **BLOCKED on original
record availability and authenticated continuity**, not on another Human ask.
No successor-read capability or genuine candidate answer was recovered. This
receipt does not classify the candidate as approved, rejected or still pending.

## Exact scope and bounded findings

Current caller task/session:
`a68df3ae-aaf5-4591-a46d-9d73db62e46d` /
`13d8c011-6e49-40ef-80e9-2f1445296d06`, workspace
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`.

Preserved supplied original tuple:

- Question `coordinator_candidate932_boundary_20261012`.
- Pending ID `b1606b82-08a3-45cf-9310-0c1fd27c10ba`.
- Message ID `ad22fe2d-4ec1-4293-985b-0add15e2c45d`.

Both named checkouts were inspected. Deployment remains on main. Unrelated
tracked/untracked files in both checkouts were preserved. No source worktree,
application implementation, deployment, runtime change or adoption grant was
created. Reviewed Support host diagnostics completed successfully; no agent was
given host/socket authority.

Read-only diagnostics projected only the supplied identity, ownership/status
metadata where authorized, and caller continuity keys. They found:

1. Current caller is an authenticated-task-bound RUNNING primary in the specified
   workspace. Its live incarnation is `cd9e844f-ead5-49b7-88e5-d284a1df6ad2`.
2. There is no clarification row for this exact stable ID on the current task /
   session, or elsewhere on this same task. The supplied original message ID
   also has no matching native question row on this task.
3. The exact supplied message ID was not located through workspace-restricted
   ownership lookup, either by message task or by the session-owned task fallback
   for legacy empty message task IDs. A final exact-ID ownership lookup removed
   type/author assumptions but retained workspace/session-owner checks; it also
   found no row. No question or answer body was read.
4. The current task is parentless. Its metadata keys are `agent_profile_id`,
   `executor_profile_id`, and `workspace`; no explicit predecessor/successor field
   was present there. No authenticated question-read continuity record/reference
   was supplied or discovered by the inspected route. This is not a global claim
   that no historical record or continuity evidence exists anywhere.

No query searched another workspace or guessed an undisclosed ID. The checks
used only the explicitly supplied original identity and caller task/workspace.
No archive, old database, unrelated question, G1 question or Human answer body
was opened. In particular, absence here does not prove that the original was
never created, deleted, answered, or moved; its historical state remains UNKNOWN.

## Why the current reader says not_created

In the restored deployed lineage, the MCP client injects its own task/session;
callers cannot choose another owner through tool arguments. The backend validates
that principal and active session. `FindOwnClarificationMessages` selects only
matching task, session, native question type/author and requested stable IDs.
The absent result projects `not_created` / `retry_allowed:true` **in that current
namespace**. It is not a global assertion about an older identity or an authority
to recreate a historically known question under a successor.

This implementation has no successor-continuity lookup in that reader. The
`PreviousSessionID` conversation mutation field is a transient UI move receipt,
not an authenticated retained successor-question grant. A normal conversation
read can address an authorized session, but cannot supply the missing original
owner/continuity proof or justify arbitrary historical question access here.
Changing caller/session identity, broad conversation paging or proxy-reading
foreign records is not a supported reconciliation recipe.

Three existing synthetic regressions passed under `-race`:

- `TestOwnQuestionReaderExactScope` (SQLite repository, 1.194s): exact scope and
  body-free projection, mixed task/session denial and absent-ID behavior.
- `TestOwnQuestionRejectsCallerMismatchAndStableIDChanges` (handlers, 1.231s).
- `TestOwnQuestionReadbackDoesNotExpandRestrictedCatalogs` (MCP server, 1.131s).

These verify current safety boundaries, not a successor-read implementation or a
candidate answer. No PostgreSQL environment was configured. No application code
changed, and no deployment acceptance is claimed.

## Exact missing platform evidence and smallest next action

The platform owner must provide a **content-free canonical identity/continuity
receipt** for the existing original record: predecessor task/session/workspace,
original question/pending/message IDs and envelope hash, source provenance, and
server-authenticated continuity to this current caller. If a recorded answer
exists, its native binding/provenance reference must be available through the
same authorized exact-record source. Do not ask Human to recreate the approval
or supply a fresh answer merely to compensate for a namespace mismatch.

The receipt must establish authorization before answer content is read. It must
not grant arbitrary question lookup, infer continuity from a reused repository
path/title, or turn a task mention into a Human answer. If the canonical record
is outside the existing authorized boundary, stop for an exact read-scope decision;
this request prohibits foreign access and source/live adoption grants. If the
record is unavailable, report that fact rather than manufacturing pending or
answered status. No local source change can reconstruct missing authenticated
evidence from the generic reminder.

Once that evidence is available, the platform can review a read-only successor
resolver that pins the exact original tuple and continuity, revalidates current
caller/workspace/session, rejects ambiguous/revoked mappings, preserves the old
record and returns only its native lifecycle/recorded answer. No move, cancellation,
recreation, adoption or runtime change is required by the data contract. Installing
new backend code is separately blocked by the no-deployment constraint; it must
not be bypassed by modifying a running process. Do not create a continuity grant
under this request's explicit prohibition.

## Root's safe consumption recipe now

1. Retain the original tuple above and the native result's current namespace.
   Treat the historical identity as `UNRESOLVED_ORIGINAL`, with no permission to
   recreate, answer, cancel or retry the question, despite current-namespace
   `not_created/retry_allowed:true`.
2. Preserve candidate source/history/commit gates with approval **UNKNOWN**.
   Human message `dd1b09d2-c951-50d4-8df4-56d0c1014807` is not interpreted as the
   candidate's missing specific answer. Do not fabricate a choice or answer hash.
3. Continue visible board/monitoring work under the direct Human override already
   supplied. An unavailable historical question record is not a new Human-input
   request. Root may reconcile its notes/tags only to these proven facts; do not
   mark the candidate answered or globally never-created from this receipt.
4. Keep G1 scope and Support `6cef6efd-df84-40bd-85f0-40577b9f52c0` separate. No G1
   query or duplicate incident was created here.
5. Consume a genuine candidate answer only after an authenticated original-record
   read is available. Verify exact IDs, envelope/binding provenance, lifecycle and
   unchanged original record before changing candidate approval tags/gates.

No question was created, answered, cancelled, copied or mutated. No task/tag/
board proxy change, source/live adoption, runtime/session change, foreign read,
credential access or deployment occurred. Only this evidence and receipt were
committed and pushed for Coordinator consumption.
