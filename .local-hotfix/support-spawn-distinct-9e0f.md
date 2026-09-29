# Distinct MCP spawn session overlay (2026-09-29)

Support request `9e0f6eb1-26e3-4809-8478-05c2db639895` repaired the
`spawn_session_kandev` route for task `8693b33e-f348-4039-8846-b2439a082010`.
At 13:48 UTC, a spawn requesting Work profile
`c06ad00e-0da1-429a-8174-54f97164a289` returned the existing session
`b98d2b09-cf64-4ead-b783-d5494c4c16e0`. The task's Blocked workflow step
had a `reuse` session target aimed at Work. The MCP handler called
`LaunchSession(IntentStart)` without `ProfileExplicit`; workflow routing then
selected the old session, and startup failed while configuring its agent.

The handler now marks its resolved profile explicit. This bypasses workflow
session-target reuse for an additional-session request and leaves the
workflow/profile records unchanged. Canonical source commit
`627b39b3dc942689365fe4e95a31aa0c92e63661` is based on verified
`upstream/main` commit `d7280234aff7a5b6dd170850dc09e66f24dc0305`.

The deployed backend was built from upstream `v0.96.0` commit
`f099a46dc7aab16f6ff5806cd29b2b480296303f`, the ten local fixes listed
in `.local-hotfix/README.md`, the three CI recovery fixes documented in
`support-ci-session-4013.md`, and overlay commit
`37b8f8a744ea57fe212e8a72d7ea879b37809615`. That overlay commit also
ports the CI recovery prompt call to the v0.96 API. The pinned v0.96 frontend
was rebuilt and embedded before linking. The `agentctl` pair was not changed.

- Backend SHA-256: `2464623cf870f2615c60ede9c8172c95d0347dbae51dc1483bfa628ad7690e2d`.
- Agentctl SHA-256: `93e685d616449911b1b36666563a82a7f17fbfb319b547aa3bc984a8214a270e`.
- Remote agentctl SHA-256: `eb63600bab383827c4891f1874809d9b8d1ed22c611d3039de3cd9ea80735cda`.
- Accepted image: `sha256:e11fa232a0e03828fb07e3be01ac5070d9a5e65920c71f48e86315fa3dbae103`.
- Rollback image: `sha256:00f8c7acb4de411b27f8f930333e55f49aef0239359223fb66567ae9518379db`.
- Previous backend backup: `/tmp/kandev-support-spawn-9e0f-prior-backend`.

Focused MCP and orchestrator tests passed. The five-package backend run passed
MCP handlers, orchestrator, executor, and SQLite repository suites. The task
service suite's repository creation cases were blocked by this test runner's
UID mapping: `/` and `/home` appear owned by UID 65534, while those tests
require trusted root or process ownership for every parent. Repeating them
under a private temporary directory did not alter that parent ownership.
The deployed `bash test.sh` suite passed all 125 checks. Safe deploy accepted
HTTP 200 on the candidate; the active image and binary hashes matched, with
`kandev-codex` AppArmor and the configured seccomp profile.

Support did not start or mutate the affected task or either task worktree.
The Coordinator must retry one distinct Work session and accept only a new
session ID that enters a running guarded turn. The prior failed session stays
for audit.
