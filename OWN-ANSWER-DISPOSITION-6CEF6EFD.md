# Native own-question answer disposition: 6cef6efd

Support escalation pass 1 repaired the reusable reporting failure in source.
It did not settle a live question or deploy. Live reconciliation remains the
previous exact-single-choice implementation. Do not retry the unchanged tuple.

## Exact verified evidence

Task `a68df3ae-aaf5-4591-a46d-9d73db62e46d`, session
`13d8c011-6e49-40ef-80e9-2f1445296d06`:

- Question `g1_partial_monitoring_four_20261013`, pending
  `efe029a8-7cc2-4e83-9e05-e8dcc12f69de`, message
  `cfdfb77a-5bd7-4968-b377-1965a16400d4`.
- Question SHA-256:
  `0de6f42d94edf5ce32e2f86928c3995c7a161f94fb21bd5038002161da7d0a4e`.
- Native Human message `d1f8f603-de6b-51b4-8c92-04f78f74ff4c`, SHA-256:
  `c6d8058c88d585c61ddd04480288b3abda475c2baedf70b27a42249a011355ba`.
- One scoped read-only host diagnostic confirmed both hashes, matching native
  admission in the current session incarnation, Agent Message Comments format,
  zero exact option matches, pending/disconnected state and no binding receipt.
  No raw message, prompt, option or credential contents were printed or copied.

The closed reconciler requires the stored complete single-question envelope
followed by exactly one recorded option label. Native Agent Message Comments
serialize selected response text and qualified feedback; that is not an exact
single-choice envelope. Human provenance alone cannot justify inventing a choice
or treating arbitrary feedback as this question's structured answer.
The repository refusal was correct. The generic handler/MCP error hid the format
classification and retry safety; that reporting defect was locally repairable.

## Guarded source repair

Canonical upstream was fetched and verified at
`82928ecc4c29431f60c1ef449dbb1672568e91f0` before the isolated checkout.
The repair targets restored live-source baseline
`56d742982b8c2daf0a13cb72c453aecd3471b6a7`, preserving deployed source
`79b0e8a39b7a3ff74cf15fa611202ab558dfaa64`, its prior lineage and the unchanged
workspace-adoption patch. It includes no preview implementation.

Fix commit: `80fdc4ce072ced98c6d72996f02e2c578d64dd82`, pushed to
`yattdev/kandev`, branch `support/own-answer-disposition-6cef6efd`.
Its separately pushed review base is `support/own-answer-baseline-6cef6efd`.
The adjacent `patches/kandev-v096-own-answer-disposition.patch` contains only this
fix; SHA-256 `bf60942533cedd53d17d44744db2185b542809e9adbc62e070bdebcb3214856c`.
[Review the exact delta](https://github.com/yattdev/kandev/compare/support/own-answer-baseline-6cef6efd...support/own-answer-disposition-6cef6efd).
Draft PR creation was denied by the GitHub integration (403, resource inaccessible
by integration). No broader credential grant was requested or bypass attempted.

The new typed `ANSWER_FORMAT_UNSUPPORTED` disposition is returned only after
existing caller/session/workspace, evidence hashes, native current-incarnation
admission, disconnected/unclaimed state and ambiguity guards pass. It reports
`status:not_reconciled`, `question_status:pending`, `retry_allowed:false`,
`changed:false`, exact evidence identifiers/hashes, and a separate Human decision
path. Both original envelopes remain untouched. Unproven, ambiguous, claimed,
foreign or otherwise invalid evidence continues to fail closed without this
provenance-confirmed disposition. Unexpected errors stay redacted.

The MCP client injects `result_mode:explicit_disposition_v1`; tool callers cannot
supply an answer/choice or broaden scope. The updated client marks the refusal
as an MCP error while retaining structured content. Old clients receive the old
error rather than misreading the structured refusal as success. A new client
against the old strict backend also fails closed. A small receipt-projection
helper extraction preserves behavior and satisfies package complexity limits.

## Supported disposition now, without deployment

If Human explicitly decides to retire this exact stale question, use its
original authenticated clarification response control:

```text
POST /api/v1/clarification/efe029a8-7cc2-4e83-9e05-e8dcc12f69de/respond
```

```json
{"answers":[],"rejected":true}
```

This is rejection, not an inferred affirmative answer. The existing backend
validates owning-task access and the original bundle. For a disconnected
request, rejection does not invoke detached resume. It preserves original
message bodies and leaves independent questions untouched. Inbox sidecar
dismissal merely hides an entry and is not a substitute. An affirmative late
custom-text response takes the detached-resume path and is outside this grant.

Support has not performed rejection. The monitoring instruction does not imply
permission to retire a pending question. Visible monitoring remains independently
authorized. No unchanged reconciliation retry is recommended before or after
installing this reporting fix: the format still cannot encode an exact option.

## Bounded acceptance and persistence

TDD reproduced repository, handler and MCP failures before implementation;
additional red tests reproduced the mixed-version risk. Final checks passed:

```text
go test -trimpath -p=2 -race ./internal/task/repository/sqlite \
  ./internal/mcp/handlers ./internal/mcp/server ./internal/clarification \
  -run 'Test(OwnAnswer|OwnQuestion|ResolverOwnAnswerDisposition|HttpRespond)' -count=1
```

Tests cover successful exact-choice reconciliation and idempotent replay;
unsupported comments/qualified text; missing admission, changed hashes, foreign
workspace, claimed and ambiguous questions; unchanged complete Human/question
records, task/session and an independent question; legacy client failure;
structured MCP error and redacted unexpected errors. A synthetic contract test
verified original-only Human rejection, idempotent rejection readback, no
PrimaryAnswered event and zero detached-resume requests. Prior adoption/worktree
regressions also passed. PostgreSQL fixtures are environment-gated; no configured
DSN was used. No query/schema/dialect logic changed.

Changed-package golangci: 0 issues. Go formatting, code whitespace, architecture,
public-copy and commitlint checks passed. The pre-commit executable was absent,
so hooks were inactive and these checks ran directly; no hook bypass was used.
The content-free receipt records the exact parent/commit and clean worktree.
Patch applicability was checked in reverse against the committed tree.

## Runtime boundary and smallest remaining decision

No deployment, binary replacement, queue replay, task resume, live database
settlement, question dismissal, provider call or board operation occurred.
Container `3b95b8dbafb8d29c6956e06467cfff09511ff1592f654aec0fe5fa2f9668d172`
and image `sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`
remain running and unchanged. Deployed binary SHA-256 values still match:

- backend: `75128d854c9f5ddcdebe85fd9e3c057897f460ae1d10535a67805ed9053bf57b`
- native agentctl: `4181384550bbe0d1c1f2f1f5157a4a819482417ed8789a8903155779292da8ec`
- remote agentctl: `bc7f9d9494ff117bf2bd884fa10f6f4e0e92104fa8c75cd0063edcc81cfa7869`

The smallest decision to retire the pending question is explicit Human
confirmation of that original-only rejection through the existing control.
No new platform permission or deployment is needed for that path.

Installing the reusable reporting repair is a separate future deployment
decision, expressly excluded here. An operator-approved installation must build
the exact source superset for backend and both agentctl targets, retain all
existing frontend asset hashes and hotfix provenance, and activate only through
`scripts/kandev-safe-deploy --build` with the HTTP-200 gate, deployment tests and
verified rollback on failure. The caller then owns a normal MCP refresh; Support
must not replay queues or resume a runtime to refresh tooling. Retain the captured
image and trio for rollback; a rolled-back candidate is BLOCKED. This source
receipt claims no live installation or caller acceptance.
