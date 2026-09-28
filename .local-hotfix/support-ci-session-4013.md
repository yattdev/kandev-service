# CI Fixup workflow session recovery overlay (2026-09-28)

Support request `4c7181e8-9c06-49fe-ab3d-fb0fa6a6d7b3` repaired the stuck
CI Fixup route for task `0ae68bd4-7cb1-4b55-9ef0-4f1640b9b7d2` and existing
session `2c8ff1ff-d6c6-4ac3-97c5-4dba58a88f29` without creating a second
session. The backend overlay is SHA-256
`2d8cf7b9747e63bfe241250149c7afa2b526e0280f2387287bd849bae84a38ed`.
It is deployed in image
`sha256:9ad38c2a17e7b4761d302f9d53660f98d386df0c2d281417ea9999b8fc6a6499`.
The paired `agentctl` overlays remain at SHA-256 `93e685d616449911b1b36666563a82a7f17fbfb319b547aa3bc984a8214a270e`
and `eb63600bab383827c4891f1874809d9b8d1ed22c611d3039de3cd9ea80735cda`.

The backend was built from the exact prior v0.96 source tree at synthetic
commit `91787c6e6635bd85b3de2e075cf927b1d2bb1c46`, which contains upstream
tag `v0.96.0` plus the ten local hotfix commits listed in this directory's
`README.md`. The existing generated web assets were copied unchanged into
`apps/backend/internal/webapp/embedded/generated` before linking. The new
patch is the v0.96 compatible port of canonical source commits `33824242c`,
`dbfd1e793`, and `7bd1b88a9` on the published
`yattdev/kandev:support/ci-session-4013` branch, based on verified
`kdlbs/kandev:main` commit `89ff7ff7131d3856eb775cb79e4a960be75a867c`.
It preserves the checkout base when a PR target is resolved, clears
new-checkout PR validation only for attach-only reuse, and conditionally
rearms a prepared session that failed before its first turn. Startup
reconciliation checks the recorded route and reuses the intended session.

The pre-incident backend binary is retained at
`/tmp/kandev-ci-4013-prior-backend` with SHA-256
`f836375117ef94c84b7b051365fbbf590c7dac00bd24fbe2ed19c08dce536fc6`.
The source orchestrator and executor suites passed, as did the v0.96 focused
recovery tests. The safe deployment accepted the candidate after HTTP 200.
Live verification observed route `committed`, intended session `RUNNING`
with the configured profile and a real turn, no added session, and PR #4013
still open/draft at head `827b50b88983f6d121087173f468917f97981f7f`.
The final `test.sh` run passed 124 of 125 checks; the remaining guard fixture
could not create a disposable Docker network because all predefined address
pools were already allocated. No unrelated network was removed.
