# Merged canonical PR URL linking repair

Support request: `7effc837-ea2e-4e6c-98a7-21bfaff702e8`.

The verified-source URL association reused `validateGitHubContributionPR`, whose
lifecycle predicate requires `State == open`. This rejected a merged deliverable
before association, despite the correct attached fork repository and canonical
upstream URL. The MCP adapter intentionally returned a generic validation error.
A separate GitHub REST quota exhaustion was also observed during diagnosis;
provider availability must recover before the caller retries.

Source fix: `5c564dbd4ed9d3f3b1cd30e15587300ec8141df0`, a direct child of the
previous backend source `37b8f8a744ea57fe212e8a72d7ea879b37809615`.
The adjacent patch is the exact source commit diff. URL linking accepts open or
merged provider state; contribution creation still requires an open, editable
PR. Identity and safe-ref validation remain shared. Existing URL collisions and
stale active head hashes still fail closed. The collision checks were extracted
without behavioral changes to satisfy the repository's complexity limit.

No MCP catalog, parent/child/workspace/session authorization, task attachment,
provider access, task state, database schema, agentctl, or frontend changes.
No real PR was linked by Support; the Coordinator owns the single retry and
verification that its task/board projection contains exactly one active link.

## Build provenance

Canonical `upstream/main` was fetched and verified at
`e8c1761cb5b7006b905c0aa995925372ce8664e1`; it does not contain the local
URL-link capability. The deployment repair therefore retains the exact deployed
v0.96 overlay lineage rather than replacing it with current upstream.

Build the source fix with the unchanged
`kandev-v096-workspace-adoption.patch` (SHA-256
`79b787b189b8df3742d5bd67d838974232f2517c14e3bdd4ce64bab0e9274e2a`).
This preserves terminal retention, live-session URL authorization, stale/collision
protection, scoped queue readers, source recloning, durable folder reconciliation,
prepared-route recovery, canonical PR workspace reuse, spawn-session separation,
and operator-attested independent checkout adoption.

Preserve the frontend archive documented in `kandev-v096-workspace-adoption.md`:
archive SHA-256 `a5368248abd87c9e8efad35b179617d2c325e78c05fd4d55aab546131a5b3453`.
All 361 listed static asset hashes were verified before embedding it. Build with
`go build -tags fts5 -buildvcs=false -ldflags='-s -w' ./cmd/kandev`.

Retain the deployed agentctl pair byte for byte:

- native: `93e685d616449911b1b36666563a82a7f17fbfb319b547aa3bc984a8214a270e`
- linux-amd64: `eb63600bab383827c4891f1874809d9b8d1ed22c611d3039de3cd9ea80735cda`

The preceding backend hash was
`68eaa38d6027240935f0c80c6190df137184730ff0c81a33ae71bd6e8dbc4a2d`.
Its source and agentctl provenance were checked against the actual live binaries
before replacement. The previous backend is retained privately under
`hotfix-backups/merged-pr-url-link-20261011/` in the host Kandev data directory.

## Validation

Synthetic tests cover merged linking, exact hash and merge timestamp, idempotent
retry leaving one active association, no new watch, open linking, unmerged-closed
and unknown-state denial, unsafe/mismatched identity/ref/source/URL rejection,
active and detached canonical collisions, stale heads, and continued rejection
of merged contribution editing. The full GitHub, worktree, MCP handlers, and
backendapp test packages passed with `-tags fts5`. The backend linter and source
commit hooks passed. Deployment acceptance is recorded below after completion.

## Coordinator retry contract

Retry `link_task_pr_by_url_kandev` once from the live direct-parent session with:

- `task_id`: `1dc4067e-00de-4459-8289-56ac6ec4ec5b`
- `repository_id`: `b86ec283-13cd-4cee-baec-1b88457ec06b`
- `pr_url`: `https://github.com/kdlbs/kandev/pull/3988`

The supplied UUID is correct: it is the child's attached `yattdev/kandev` source
repository in workspace `2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`. Do not substitute
the upstream repository UUID or use number-only linking. Verify one active
canonical #3988 association with head
`f380a2532168c3ea0fde19e5cb10b02382f72263` and merged state on task/board readback.

## Deployment acceptance (2026-10-11)

`scripts/kandev-safe-deploy --build` exited zero and accepted HTTP 200 at
21:35:43 UTC on image
`sha256:964a939c4c37e7a5d3a94f2a63f913032a7ee2743ece74650ed1755f261f1945`.
No rollback occurred. Live backend SHA-256:
`d2b36653e6403a76ffbb87a4a5c50f0c46b31f89a6c30fc8f3c856a258232cb5`.
Both agentctl hashes matched the preserved pair, restart count was zero, and
seccomp plus `apparmor=kandev-codex` remained installed. `bash test.sh` passed
all 129 deployment checks. Read-only child verification after deployment showed
`REVIEW` / `Human-QA` and zero PR-link rows, as before deployment.

The rate-limited REST response reported `X-Ratelimit-Remaining: 0` and
`X-Ratelimit-Reset: 1791754962` (2026-10-11 21:42:42 UTC). The `/rate_limit`
endpoint gave inconsistent quota information; use the actual repository/PR
response when checking recovery. Do not bypass workspace/provider access checks
to work around rate exhaustion.
