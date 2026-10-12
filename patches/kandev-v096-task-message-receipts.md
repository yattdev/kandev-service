# Authenticated task-message admission and sender receipts

Support request `0c0acd13-dd1d-4372-90dc-b5d27dd6d169`.

## Failure and reusable contract

Legacy `message_task_kandev` transitioned REVIEW before recording the prompt,
then synchronously waited for prompt/resume/startup. A lock failure before
publication and a transport timeout after publication had no stable sender
intent to correlate. Blind retries could duplicate prompts. The REVIEW write
now uses an archive-aware compare-and-set and bounded transient lock retries;
a superseding transition is rejected rather than overwritten.

For reliable admission, `message_task_kandev` adds optional `intent_id`:
8–128 ASCII letters, digits, hyphens, underscores, or periods. This mode requires
an exact target `task_id` and `session_id`, queued delivery (omitted or `queued`),
a nonempty prompt of at most 64 KiB, and no parent-question reply. Legacy and
parent interrupt/reply behavior remain separate. No profile/model selector or
new interruption permission is added.

The trusted MCP server injects its own sender task/session. The backend requires
that exact authenticated pair, an active nonautomation caller, and platform
records proving target session ownership in the caller's workspace. It never
accepts a caller-selected sender/workspace or a foreign target. The caller's
stable identity maps deterministically to one namespaced message UUID, and a
fingerprint binds the unchanged original prompt and exact identities.

The transcript, its turn when needed, and its exact durable FIFO receipt commit
as one transaction under existing task-before-session writer fences. The
transaction rechecks archive status, target state, workflow step, and immutable
session incarnation. It does not move the workflow step or allocate another
worker/routine. Queue failure rolls back the message and successor turn.
Existing turns and pending Human input are preserved. A pending clarification
or permission rejects new peer admission with `admission_error: human_input_pending`;
only legitimate resolution permits a later identical-intent attempt. No turn
or message is created by that rejection. Queue delivery uses the
existing reserve/attempt/ack mechanism and normal clarification/WIP/lifecycle
checks. No direct SQL API or data workaround is exposed to agents.

Admission uses a 20-second deadline and at most three whole-transaction attempts
for classified transient lock/serialization failures, with bounded backoff.
After failure it correlates the original receipt using a fresh bounded read.
If readback itself cannot confirm identity, it rejects and requires correlation
before retry. It never reports a missing intent from a failed read. Readiness
notification is bounded and happens after persistence; the tool does not wait
for executor startup or the recipient's answer.

## Status and continuation operations

`get_task_message_status_kandev` accepts either:

- `task_id`, `session_id`, and `intent_id`; or
- exact legacy `message_id`, optionally narrowed by a paired task/session.

Only exact sender-owned records in the caller's workspace are projected. Legacy
correlation uses the exact marker on that sender's exact target; multiple
candidate identities or partial legacy marker matches reject rather than guessing.
UUID lookup derives the
legacy target from trusted records. No prompt, Human-message body, peer message,
queue inventory, or credential is returned. Output contains identity fields,
nonsecret content digest, status, `retry_allowed`, `continue_allowed`, and
`continuation`.

| Status | Meaning | Safe action |
| --- | --- | --- |
| `not_created` | No current sender-owned message/queue record matches the exact stable intent. | An identical stable-ID publication is dedup-safe; all lifecycle fences still apply. Do not infer that an earlier transport was never attempted. |
| `not_found` | Exact legacy UUID has no visible sender-owned record. | No resend permission or assertion that it was never created. |
| `queued` | Original FIFO entry is durable. | Never republish. Recheck readiness only if `continue_allowed` is true. |
| `dispatching` | Original durable entry is reserved in flight. | Observe the existing turn; no replay. |
| `delivery_attempted` | External delivery may have occurred. | No automatic replay or inferred provider acceptance. |
| `recorded_delivery_unknown` | Transcript exists, but this record cannot prove provider acceptance. | Preserve its identity and observe the existing turn; no blind resend. |

`continue_task_message_kandev` takes the same identity fields. It only rechecks
normal readiness of an existing queued receipt. It revalidates task/session,
archive/terminal state, step, and incarnation, preserves FIFO and all input/WIP
fences, and never inserts a prompt, reapplies a move, takes a FIFO entry by force,
interrupts a turn, or reconstructs a legacy send. A false `continue_allowed`
returns the existing receipt without attempting delivery. A queued result is
an admission receipt, not a recipient/agent answer.

A replay of `message_task_kandev` with the same stable ID and identical prompt
returns the original identities without republishing or repeating readiness
side effects. Changed content under that identity rejects. A legacy transcript
without a provider acceptance marker cannot be converted into proof that it
was never delivered; its retry permission remains false.

## Exact Coordinator acceptance, after deployment

Refresh MCP discovery on caller task
`a68df3ae-aaf5-4591-a46d-9d73db62e46d`, session
`76a8a9e8-8562-4d27-826e-66f040d980b2`. Do not manufacture another live QA message.

First correlate the failed HQA intent:

```json
{"task_id":"7056a702-a3c3-4fe8-8535-c6b8d340ef6a","session_id":"2ac1abf6-2208-4d4e-9621-19b67ef4ba4c","intent_id":"HQA-INTEGRATION-OVERRIDE-20261012-v2"}
```

Use `get_task_message_status_kandev`. An existing identity forbids republishing.
If it is queued and continuation is allowed, call `continue_task_message_kandev`
with those same arguments. If it is `not_created`, the original reported
failure occurred at the pre-publication REVIEW transition; the Coordinator may
retry its retained exact original instruction once through
`message_task_kandev`, using those identity fields, `delivery_mode: queued`,
and the unchanged original `prompt`. Support does not relay that prompt.
The deterministic new-admission UUID for this tuple is
`6280f37b-d35f-5d51-b363-989a5fd6f0c6`; this is a candidate identity, not a claim
that Support created a record. A successfully admitted new intent must return
that same message and queue identity on repeat reads/replays. Retain any
preexisting legacy identity instead; never substitute the candidate for it.

Then correlate the plugin's proven existing user message:

```json
{"message_id":"cd046f80-317d-4793-baf3-7ee8a35204d8"}
```

Use `get_task_message_status_kandev`. Require the exact message identity when
present; derive its full task/session UUIDs from the authenticated receipt.
If a matching original queue exists and continuation is allowed, recheck only
that receipt. If it is `recorded_delivery_unknown`, `delivery_attempted`, or
`dispatching`, preserve the original and inspect its existing turn through the
already supported conversation capability. Do not resend `PLUGIN-WAKE-20261012T0536Z`
or infer acceptance from the absence of an agent response. A `not_found` result
also forbids resend. This is sender-owned supported acceptance, not a recurring
Support queue/status relay.

## Synthetic verification and source ownership

Fixtures exercise atomic transcript/turn/FIFO persistence, queue failure
rollback without orphan turns, REVIEW lane preservation, exact replay and
concurrent deduplication, timeout/cancel followed by readback, changed content,
legacy UUID/marker correlation and ambiguity, exact case, missing legacy UUID,
caller/session/workspace denial, changed target step/incarnation and terminal
owner fences, and bounded lock retry. Human answer/question fixtures use only
synthetic task-owned data. No live ordinary work is executed by Support.

```sh
cd apps/backend
go test -race -tags fts5 ./internal/mcp/handlers ./internal/mcp/server \
  ./internal/task/repository/sqlite -run 'TestTaskMessage(Receipt|Write)|TestOwnQuestion' -count=1
```

Owners are `internal/mcp/handlers/task_message_receipt.go` (authentication,
receipt and continuation), `internal/task/service/task_message_receipt.go`
(admission bridge), `internal/task/repository/sqlite/task_message_receipt.go`
(atomic writer and bounded sender projection), and
`internal/mcp/server/task_message_receipt.go` (paired agentctl tools/schema).
Existing queue and provider lifecycle owners still control actual delivery.
No schema migration, custom prompt, target task source/test/PR edit, or new
standing authority is introduced.

Canonical `upstream/main` was fetched and verified at
`bc0d3b90477078bb5e002e1a18d5e7fbe9c91f71`. The source repair starts at exact
deployed `52408015b184cb045a04e0d937e8dfc846a7d61b`, retaining all preceding fixes
in the [mixed-batch record](kandev-v096-own-question-mixed-batch.md) and its
provenance chain. The unchanged workspace-adoption overlay has SHA-256
`79b787b189b8df3742d5bd67d838974232f2517c14e3bdd4ce64bab0e9274e2a`.
All 361 unchanged frontend asset hashes were verified before embedding.

Pre-replacement image:
`sha256:683f7b34cde19182763e278cb821d583203f020541e4c00e4a5d708447f439ee`.
Its live trio matched the preceding record exactly:

- Backend: `2b679eedab31511137207ad05ce16a7e5592e055ba4cfdd39f55aa6fc4412a94`
- Native agentctl: `739fd743ac7b4cf68200c48033d34dbe137b8cdc1a920345f1de34c20ed0ec9a`
- Remote agentctl: `b48ddb3a531158a9adc8cbbb5f765414b995485cce977c45ae9569dcae71cf78`

Source commits: `f16b49f2f00ac1bc468871a075307f292f550bb3` and final
`02bb5d05944141c9e03ad746dde120668f98e46f`. The adjacent patch is their exact
combined diff from the deployed base, containing only this request's source
and tests; the adoption overlay is retained separately.

Full MCP handlers/server, task service, SQLite repository, message queue,
orchestrator, worktree, backendapp, and system-prompt regressions passed across
the scoped runs. The affected service/handler suites passed again after atomic
turn admission. Final own-question/task-message receipt race tests, SQL guard,
and persistence conformance passed; full backend lint reported zero issues
and both source commit hooks passed. PostgreSQL fixtures are present but skipped
without a configured DSN; the live deployment uses SQLite.

Build flags: backend `CGO_ENABLED=1`, `fts5`, `-buildvcs=false`, and
`-ldflags='-s -w'`. Agentctl retains native CGO=1 and remote linux/amd64 CGO=0,
with version `v0.96.0-support-0c0acd13`, the final source commit above, and build
time `2026-10-12T06:36:09Z`.

Candidate SHA-256 values:

- Backend: `5d803423d161ba4ebb77e53dc71bc100117199c487d0d2aa101346eada2a3753`
- Native agentctl: `7b48366861f4a878c6c70e3922651c9ebcb2e0b3dda37cffd2eef40ed8c2030e`
- Remote agentctl: `a4c382a005e621d9629edd03e780b77178c7284a7d0e7cc124dcb69e71c1a88a`

The previous trio is retained privately in the host Kandev data directory under
`hotfix-backups/task-message-receipts-0c0acd13/`.

## Verified deployment receipt (2026-10-12)

`scripts/kandev-safe-deploy --build` exited zero and accepted HTTP 200 at
06:42:58 UTC on image
`sha256:809f83037b659b60820b194ba24094434f88d9ff14d15f00566195dbf4fb1aaa`.
No rollback occurred. The live backend and both agentctl hashes match the
candidates above. Restart count is zero; seccomp and `apparmor=kandev-codex`
remain active. `bash test.sh` passed all 129 deployment checks.

Support did not send, replay, relay, or execute either ordinary instruction,
operate the Coordinator's MCP connection, perform a live question acceptance
fixture, read live prompt bodies, directly edit linkage/data rows, change
profiles/models, modify target task source/tests/PRs, clear queues/FIFO, or
dispose of unread Human input. The Coordinator owns the exact authenticated
readback and any eligible continuation using the recipe above. Provider
acceptance for a legacy transcript is never inferred or fabricated.
