# Exact own-question mixed-batch readback

Support request `8bd69fe8-3ee2-4dc9-a037-1a4b4111a8b4` follows
`292e71d2-00d0-49fc-bb37-c9cb95de1785`.

## Cause and contract

The reader incorrectly required every requested ID to exist, applying an
ask-retry completeness predicate to a read operation. A mixed existing/missing
batch therefore failed even though each individual lookup was valid.

`get_own_question_status_kandev` still accepts only `question_ids`: 1–4 unique,
nonempty exact IDs, at most 128 bytes each. Trusted MCP task/session provenance,
active caller, workspace ownership, and agent-authored clarification scope are
unchanged. The metadata-only storage query and its bounds are unchanged. No
additional authority, SQL operation, or target selector is introduced.

The response now has exactly one `questions` entry per requested ID, in request
order. Each entry declares `question_id`, `status`, and `retry_allowed`.
Existing entries additionally retain their own `pending_id`, `message_id`,
requesting turn, timestamps, question digest, disconnected-waiter metadata,
and recorded answer where applicable. Missing entries have only the three
required fields, `status: not_created`, and `retry_allowed: true`.

Per-ID statuses are `not_created`, `pending`, `answered`, `rejected`, `expired`,
`cancelled`, or `unknown`. Only `not_created` permits a new publication using
that same ID. An existing identity never permits recreation or implies approval.
Unknown lifecycle strings normalize to `unknown`; malformed/ambiguous identities
still fail closed. Duplicate records for one ID are never guessed away.

Batch `status` is the common status when all entries agree, otherwise `mixed`.
Batch `retry_allowed` is true only when every requested ID is absent. The
optional batch `pending_id` identifies the single existing bundle, if exactly
one is represented; for multiple bundles it is omitted. Each existing entry's
`pending_id` remains authoritative. A missing entry beside a pending original
never permits retrying the combined batch or recreating the original.

Readback permits distinct exact own bundles. Ask retry still requires all
requested IDs to exist in a single original bundle, with identical question
content/context. Partial identity matches and attempts to merge separate
requests reject without publishing, cancelling, or replacing anything.

## Coordinator acceptance without a live ask

Refresh MCP discovery to obtain the updated output schema. On the exact
Coordinator task/session, perform read-only calls:

```json
{"question_ids":["coordinator_visibility_scope_20261012_1"]}
{"question_ids":["coordinator_own_question_acceptance_missing_20261012"]}
{"question_ids":["coordinator_visibility_scope_20261012_1","coordinator_own_question_acceptance_missing_20261012"]}
```

Repeat the mixed call and reverse its ID order. Require one entry per ID in
request order, preserved original pending identity
`188875c4-ccd4-46f5-b40f-e37fee1c7f02` and message identity
`b6ac51cb-f66c-4d0a-b5e5-7c995095b39d`, and no retry permission for that original.
The missing entry must remain `not_created` with per-ID retry permission and no
invented message/bundle identity. Batch retry permission must be false.
For pending original plus absent ID, batch status is `mixed`. A legitimate
Human answer/rejection may change the original status; retain the same identity
and consume only its actual recorded result. These read calls do not publish
an ask, mutate pending input, or grant policy scope. Do not retry the original.

Answer/rejection acceptance uses synthetic task-owned fixtures only:

```sh
cd apps/backend
go test -tags fts5 ./internal/mcp/handlers ./internal/mcp/server \
  ./internal/task/repository/sqlite -run TestOwnQuestion -count=1
go test -race -tags fts5 ./internal/mcp/handlers ./internal/mcp/server \
  ./internal/task/repository/sqlite -run TestOwnQuestion -count=1
```

The added batch fixtures cover missing-only, existing-only, both mixed orders,
four IDs, deterministic repeated reads, answered and rejected records, retained
identities/answers, separate bundles, and partial/combined ask retry denial.
Existing fixtures cover caller/session/workspace mismatch, inactive caller,
publication failure, restart/concurrent retry deduplication, duplicate identity
rejection, and exclusion of Human/peer message bodies. Support performs no live
question relay or manufactured Human-input acceptance.

## Source ownership and preserved deployment

Backend owner: `apps/backend/internal/mcp/handlers/own_question.go`.
Agentctl MCP schema/forwarding owner:
`apps/backend/internal/mcp/server/own_question.go`.
The storage, publication, and Human-answer owners are unchanged from the
[original lifecycle record](kandev-v096-own-question-lifecycle.md).

Canonical `upstream/main` was fetched and verified at
`56461e6a7f780b83b1f831dd6972fe169c67aa72`. This repair starts at exact deployed
source `6d75fff4da2969f9bcf040433beb56a9b05c5934`, retaining all fixes documented
in the original lifecycle record. It reapplies the unchanged adoption overlay
with SHA-256 `79b787b189b8df3742d5bd67d838974232f2517c14e3bdd4ce64bab0e9274e2a`.
All 361 unchanged frontend asset hashes were verified before embedding.

Before replacement, the live image was
`sha256:42e28e828ee939174085280ca71f80ec5ca52878bf9b8d6537128253719094c3`.
Its binaries matched the original record exactly:

- Backend: `026517571508c1d66e2f3ce4a111fc5c27c66e8048270bb70c2db5e9e3945171`
- Native agentctl: `b821f6e8c4a6af56d583542d2362026980940371c9d8634f4dd8a1db7eb8f0f1`
- Remote agentctl: `fd270d88efab05d0cf1ec2c198e19765c25bd7212bbf583c6d62785e8691d0d1`

Source repair commit: `52408015b184cb045a04e0d937e8dfc846a7d61b`.
The adjacent patch is its exact diff and contains only this request's four
source/test files; the adoption patch is retained separately.
Full handlers, MCP server, SQLite repository, clarification, worktree,
backendapp, and system-prompt suites passed across the final scoped runs.
Own-question race tests passed in handlers, server, and repository. Backend
lint reported zero issues; source commit hooks passed. PostgreSQL fixture
parity remains environment-gated; no DSN was configured and storage is unchanged.

Candidate builds use `-buildvcs=false -ldflags='-s -w'`, with `fts5` for the
backend. Agentctl retains native CGO=1 and remote linux/amd64 CGO=0, embedding
version `v0.96.0-support-8bd69fe8`, the source commit above, and build time
`2026-10-12T05:13:41Z`.

Candidate SHA-256 values:

- Backend: `2b679eedab31511137207ad05ce16a7e5592e055ba4cfdd39f55aa6fc4412a94`
- Native agentctl: `739fd743ac7b4cf68200c48033d34dbe137b8cdc1a920345f1de34c20ed0ec9a`
- Remote agentctl: `b48ddb3a531158a9adc8cbbb5f765414b995485cce977c45ae9569dcae71cf78`

The previous trio is backed up privately in the host Kandev data directory
under `hotfix-backups/own-question-mixed-8bd69fe8/`.

## Verified deployment receipt (2026-10-12)

`scripts/kandev-safe-deploy --build` exited zero and accepted HTTP 200 at
05:18:33 UTC on image
`sha256:683f7b34cde19182763e278cb821d583203f020541e4c00e4a5d708447f439ee`.
No rollback occurred. All three live binary hashes match the candidates above.
Restart count is zero; seccomp and `apparmor=kandev-codex` remain active.
`bash test.sh` passed all 129 deployment checks.

Support did not create, retry, answer, reject, cancel, or recreate any live
question, read live question bodies or answers, use the Coordinator's MCP
connection, mutate Human input/routines/FIFO, or expand registration/guard
policy. The original pending question remains owned by the existing durable
clarification path. Its supported-call acceptance belongs to the Coordinator
using the read-only recipe above; Support does not operate a status relay.
