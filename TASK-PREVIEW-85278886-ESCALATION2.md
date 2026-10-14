# Exact V2 preview: final escalation audit

Request `85278886-f97b-4219-b7ba-9182f7059c69`: implementation and synthetic
acceptance are complete; live activation remains BLOCKED. The approved new
ingress implementation is not being reopened for permission. The reviewed source,
container boot binding, native ACL tests, candidate provenance and activation /
rollback steps remain those in
[TASK-PREVIEW-85278886-ESCALATION1.md](TASK-PREVIEW-85278886-ESCALATION1.md).

## Bounded audit evidence

Both named checkouts were inspected. Deployment remains on main; unrelated dirty
and untracked files in both repositories remain intact. The existing compatible
source worktree is clean at `883439a99d97f8809401f6a83baa8a20279af99d`.
Remote branch verification independently confirmed that revision and canonical
feature head `1b29c2ff5b86f2b4af08cf1c4bc3be836c46a455`. Both supplemental patches
reverse-apply against the compatible committed tree.

The retained local binaries were hashed again, with exact matches:

| Artifact | SHA-256 |
| --- | --- |
| Compatible backend | `dbec5779bcfafc858a41c6240cbebf3557b3613922150e6df4a1f85ed57cacc0` |
| Static gateway | `cb6d21167dc47f9796f02a2c66ead4a0dae899ba0c6106e3c32c10ed5f04d4f6` |
| Retained public-asset manifest | `9795fb290a348d7dc6bdbd6ce6bb4fd563f260e771d93f54f63559e2f1120289` |

The previously built, unactivated scratch image remains the recorded candidate
`sha256:1476f52391b522e43fab380b96059c6b8f8f3c693a77e199fedbcc09e618429b`.
This audit does not claim a fresh live image/container inspection. No source or
runtime implementation changed, so the recorded green race/FTS5/auth tests,
issuer/broker acceptance, zero-issue lint and synthetic isolation checks were not
rerun. Live browser acceptance and the post-recreate deployment suite remain
pending; synthetic success is not represented as deployed acceptance.

Source review again confirmed:

- Existing real browser identity, active account and native task/workspace ACL
  are required. The signed check endpoint has no caller-selected target or user.
- The exact environment/root, container/image/project/service/loopback port,
  immutable ownership/model and container boot are rechecked. Each request uses
  a fresh socket with a post-connect check before application bytes.
- Parking does not require an active executor or extend the fixed 24-hour window.
  Expiry, revocation, changed ownership and a restarted/replaced target deny access.
- Main authorization is handed off by a short one-time POST-body ticket. Preview
  uses its own host-only Secure/HttpOnly cookie; outer credentials are stripped.
  The documented deployment review must verify actual cookie-site/TLS bindings.
- Task-owned login staging remains guarded and immutable. Human delivery is the
  authenticated main credentials endpoint, not a claim that a private file was
  delivered. No actual login was staged or read in this audit.

## Authority audit and remaining action

Earlier reviewed host diagnostics succeeded. Neither a denied task-facing Docker
operation nor inability to inspect a host path is the remaining blocker. No
additional reviewed diagnostic escalation can supply missing deployment consent
or trusted TLS bindings. The prior host/service inspection is retained rather
than repeating an exhaustive audit or polling trial/task status.

The candidate's normal-auth backend hooks and broker helper are absent from the
captured running deployment. An independent gateway alone cannot provide that
exact user/task authorization bridge. Exporting main cookies/PATs, opening the raw
socket/database to a second service, or inventing an unauthenticated relay would
expand the reviewed boundary. None was attempted. Live binary replacement or
process patching would be deployment under another name, expressly excluded here.

The smallest remaining activation package is:

1. **Separate production-recreate approval** for the already documented single
   `scripts/kandev-safe-deploy --build` operation in an operator-selected window,
   preserving captured hotfix lineage and native binaries, HTTP-200 acceptance,
   automatic rollback and mandatory post-success `bash test.sh`.
2. **Concrete trusted HTTPS bindings:** main origin, cookie-isolated preview
   origin, dedicated certificate/key references and an available exact private
   listen address. Do not guess hostnames, trust anchors or listener ownership.
   If main TLS is absent, its exact local bridge bindings require a concrete
   additional decision; this audit installs no generic proxy.
3. **Owner verification/restoration of the exact approved V2 container before
   issuance.** The last retained observation (approximately 2026-10-14T03:17:40Z)
   found V2 stopped, finished 2026-10-14T02:23:23.421420001Z, exit 0, not OOM.
   This audit makes no fresh live-state claim. Support has not changed lifecycle.
   V1 is excluded. Replacement with a different ID requires exact target review.

Prepare the empty private state mount before the approved recreate. Issue only
once the bridge and exact V2 target are ready, then start the dedicated gateway
and perform the documented positive/negative installation checks. No grant has
been issued; `issued_at`, `expires_at` and usable URL remain null. The 24-hour
window has not started. Owner performs browser/product and post-park acceptance;
provider configuration and evaluation remain outside Support's execution scope.

The existing exact owner revoke command is
`docker kandev preview revoke 85278886-f97b-4219-b7ba-9182f7059c69`.
Only the dedicated preview service is stopped for preview shutdown; neither
trial nor production is implicitly restarted. The prior review retains the
rollback procedure and the authenticated Human credential handoff instructions.

Only this audit and content-free receipt updates were committed and pushed.
No production/source deployment, board/database mutation, credential access,
model call, trial request, task lifecycle change, publication/firewall change,
new grant or provider configuration occurred.
