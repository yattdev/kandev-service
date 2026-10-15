# Historical native-comment binding: bounded contract review

Publication/review request: `f7a1c1da-89a5-4741-a905-6756fb4b13c5`.
Original reconciliation request: `cb42dde1-ee10-4dfe-99ce-dfd9868ad46c`.

**Maintainer verdict: UNRESOLVED.** This document is Support's static contract
assessment and a request for the local reconciliation maintainer's decision.
It is not maintainer approval, an implementation, a newly authenticated Human
answer, or activation authority. No live state was queried in this request.

## Classification and existing owner

This is a **local Kandev customization**, not an upstream-only defect.
At verified canonical upstream/main
`8c6f4b800b123d5f074cc006a88893c807c584b9`, neither
`apps/backend/internal/task/ownanswer` nor
`apps/backend/internal/mcp/handlers/own_answer.go` exists. The source checkout
and deployment checkout were both inspected; unrelated files were preserved.

The existing implementation owner is the local own-answer reconciliation module:

| Boundary | Existing owner |
| --- | --- |
| Evidence validation and answer representation | `apps/backend/internal/task/ownanswer/binding.go` |
| Task/session transaction, native admission, ambiguity and CAS | `apps/backend/internal/task/repository/sqlite/message_own_answer.go` |
| Trusted MCP caller authorization and publication | `apps/backend/internal/mcp/handlers/own_answer.go` |
| Six-pin caller schema and forwarding | `apps/backend/internal/mcp/server/own_answer.go` |
| Status/receipt readback | `apps/backend/internal/mcp/handlers/own_question.go` |
| Current comment producer; not a trusted binding store | `apps/web/lib/state/slices/comments/format.ts` |

The supported operation is `reconcile_own_question_answer_kandev`; readback is
`get_own_question_status_kandev`. There is no separate historical-direct-comment
operation in the supplied caller catalog. The earlier reporting repair is
`80fdc4ce072ced98c6d72996f02e2c578d64dd82`. Test-only coverage is
`bb985c2baba703df7b20564d9336f3f256e8544f`, its direct child. Neither commit
implements this requested historical binding. The local commits identify
`ayattara` as author; GitHub identifies `yattdev` as custodian of the personal
source fork. No CODEOWNERS entry or existing review thread naming a separate
reconciliation reviewer was found. Repository custody is not an independent
maintainer verdict.

## Exact case under review

The immutable evidence manifest preserves all six original pins. The historical
Human message contains two comment pairs, including a quoted restricted
validation recommendation followed by `ok go`; its complete body must remain
intact. It has the protected native request fingerprint but no queue-admission
reference. The original question is in the original caller session. The later
Ubuntu fact is unrelated and must never settle this or any other question.

The present parser's inability to correlate this envelope does not revoke or
dispute the Human's recorded approval. Conversely, hashes and a `user` label
alone cannot prove interactive Human authorship, bind a comment to a question,
or establish affirmative meaning. These are separate proof requirements.

## Minimum proof contract for maintainer decision

1. **Genuine Human ingress.** The server must verify a protected admission/audit
   record tying the persisted answer ID, complete content hash, creation time,
   task/session/incarnation and authenticated interactive Human actor or trusted
   Human-ingress origin together. Exclude task-to-task, broker Support,
   automation and provider-authored messages even when rendered as `user`.
   A client request fingerprint is replay evidence, not an actor attestation.
   Do not reconstruct request fingerprints by reading model/configuration or
   credentials. Existing queue-admission proof remains valid for its supported
   path; do not invent a queue receipt for direct ingress.
2. **Own caller and historical question.** Keep server-injected task/session
   identity and the existing live workspace/ownership/nonterminal checks.
   Bind the exact pending/question/message IDs, original requesting turn,
   creation identity, complete question/context/ordered option-set digest and
   the current verified session incarnation. A disconnected question may belong
   to an older turn; do not silently move it to a new turn or session. Reject a
   recycled incarnation or any changed question/context after review.
3. **Quoted recommendation linkage.** Verify a protected reference to the
   agent-authored recommendation, its exact source body digest, selected span
   and question association. A future producer can persist validated typed
   references; the current Markdown text drops those identities. For this
   historical envelope, any recovery must cite an already protected audit or an
   explicitly authorized maintainer/operator historical attestation of this
   exact full tuple. An agent-writable receipt, caller-nominated question ID,
   quote substring search or semantic similarity cannot supply that authority.
4. **Affirmative meaning and scope.** The maintainer must explicitly decide
   whether this exact complete envelope unambiguously affirms the quoted,
   restricted recommendation and the original question. Review both comment
   pairs and all residual text. Pin the complete answer body and the relevant
   quote/feedback spans; never discard the first pair to simplify interpretation.
   No generic `ok go` allowlist may settle arbitrary questions. Contradictory,
   qualified, duplicated, changed or multiply linked envelopes fail closed.
   This review must not broaden the issuer/backend validation scope or execute
   any validation. If the meaning/link cannot be established from authorized
   evidence, the verdict is unresolved or rejected; do not manufacture proof.
5. **No caller-invented option.** Retain the six-pin task caller interface;
   do not accept a choice, replacement body, actor, target session or permissive
   provenance flag. If the existing approval is accepted as custom text, retain
   the exact complete native body as the recorded answer, with a typed binding
   audit. Do not synthesize `q1_opt1` from a natural-language recommendation.
   Any historical attestation must be server-owned, separately authorized,
   bounded to this tuple and unavailable for task self-attestation.
6. **One-time/idempotent commit.** Retain task-before-session admission locks,
   same-transaction scope revalidation, exact evidence comparisons and row CAS.
   Preserve any prior genuine answer. One tuple yields one immutable receipt;
   an identical retry returns that receipt with `changed:false`. A conflicting
   tuple or previously claimed Human message must never replace a binding.
   Bind the provenance proof and reviewed interpretation in the audit along
   with the original receipt hash; do not regenerate the source approval.
7. **No automatic dispatch.** Commit only the original question's answer/link
   metadata and the original Human message's binding linkage, following the
   existing reconciliation owner. Preserve original bodies, turns and creation
   times. Use normal metadata publication and durable own-status readback only.
   No `/respond`, PrimaryAnswered/resume event, prompt admission, task startup,
   provider call, FIFO operation, source activation or preview action occurs.
   A publication failure must not create another binding on retry.

For this exact historical case, the unresolved decision is whether sufficient
protected Human-origin and recommendation/question evidence already exists, or
whether a narrowly authorized historical attestation can supply those claims.
A source change alone cannot retroactively create the original admission facts.
Support has not asserted an actor identity, recommendation message ID, signed
link, selected option or approved interpretation that the evidence does not prove.

## Isolated implementation/review/test criteria, if later authorized

Implement in the existing module and operation above; do not add a parallel
generic database writer or second answer resolver. Before creating a source
worktree, fetch/verify canonical `upstream/main` and the explicitly named local
review baseline. Preserve the exact deployed source superset: the reporting
branch alone is not the full current preview/hotfix lineage. This request creates
no source worktree or implementation and requires no new source fetch.

First obtain the maintainer's written verdict on the seven proof requirements,
including the exact historical provenance source and interpretation policy.
Define the server-owned historical attestation boundary, if needed, before
writing code. Ordinary task callers must never issue or approve such attestations.
Resolve original context digests and selected-source canonicalization explicitly;
do not treat the existing question-object hash as a full context hash.

Future tests must drive real producer/handler/repository seams with synthetic
data and demonstrate an initial failure before changed production behavior:

- Accepted authenticated direct-native proof plus the exact approved envelope;
  ordinary exact queued-choice behavior and every restricted MCP catalog remain
  intact. A positive fixture must supply the chosen real proof mechanism, not
  merely seed a `user` label or caller-created metadata.
- Changed question/context, message IDs/hashes, quote/span/body, actor/origin,
  incarnation, original receipt or target; missing proof; task/broker/automation
  impersonation; foreign/inactive caller; attached waiter; multiple matching
  questions or recommendations; contradictory/qualified feedback; and the
  unrelated Ubuntu fact all refuse without writes.
- Concurrent exactly-once binding, restart/readback, identical retry,
  conflicting already-bound evidence, changed evidence between validation and
  commit, and publication failure followed by safe receipt correlation.
- Byte-equivalent preservation of all other questions and Human messages,
  original bodies/turns/creation times, task/session identity, and queued entries,
  FIFO order, admissions and counters. No dispatch, resume, PrimaryAnswered,
  inference, credentials, model/configuration access or task start is observed.
- Normal same-intent handoff remains a separate caller action after accepted
  status readback; it retains the original candidate/receipt identity. An
  independent unanswered question continues to enforce its ordinary barrier.

Run only affected tests after implementation, including race coverage for the
transaction/handler boundary and dialect parity where query behavior changes.
No unchanged suite was rerun for this static review; existing test evidence
remains evidence of the current refusal boundary, not future acceptance.

## Separate activation scope

This publication and review authorizes no implementation, binary build,
installation, runtime refresh, queue replay or preview validation. Root retains
any later implementation/activation authorization. If changed backend/MCP code
must be installed, that is a separate reviewed deployment preserving all current
hotfixes, using `scripts/kandev-safe-deploy` with the required health/rollback
gate and deployment checks. No additional preview production build is authorized
or consumed here. The original approval is not being requested again.
