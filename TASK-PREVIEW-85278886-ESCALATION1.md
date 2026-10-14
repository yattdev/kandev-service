# Exact V2 preview: escalation 1 review and activation gate

Request `85278886-f97b-4219-b7ba-9182f7059c69` remains **BLOCKED for activation**.
The Human-approved implementation has been extended, tested, built and pushed.
No preview grant, URL, issued time or expiry has been created. No production
recreate, trial lifecycle change, trial HTTP request or evaluation was performed.
This record supersedes the original candidate hashes in
[TASK-PREVIEW-85278886.md](TASK-PREVIEW-85278886.md), whose exact task/target,
credential handoff, revoke commands and rollback procedure still apply.

## What the escalation resolved

Support used reviewed host diagnostics successfully. Both deployment and source
checkouts were inspected; this is not a mistaken restriction on Support's host
authority or an upstream-only classification. Bounded inspection found no
installed authenticated ingress or hot-load path that could supply the new
backend bridge without a production recreate. No caddy/nginx/traefik/cloudflared/
tailscale service or local HTTPS listener was found. `host.env` remains absent.
The unrelated loopback listener on 59433 was not probed or repurposed; the
listener port in the inactive template is a placeholder, not a reservation.

Exporting production cookies, bearer credentials, raw database/socket access or
running a second privileged backend would enlarge the approved boundary. None
was attempted. The broker helper and private state are not installed in the
running production container. The reviewed compiled backend hooks cannot be
activated by changing only this gateway's files.

Native backend acceptance now uses actual user authentication and task/workspace
ACL storage, rather than relying only on a stub authorization callback. It
verifies parked environments, cross-user and cross-workspace denial, disabled
accounts/authentication, mismatched environment/root and unchanged task state.

A new adversarial transport test demonstrated a real race in the first candidate:
ownership could disappear between its request check and upstream connection.
That test initially observed one unauthorized upstream request (HTTP 200). The
repair uses a fresh connection for every request, rechecks authorization after
connection establishment before emitting application bytes, and pins the exact
Docker `StartedAt` value. A stop/restart of even the same container invalidates
an issued grant; it cannot launder a socket accepted by another listener. The
issuer captures the current exact boot and rejects malformed/future timestamps.
The ownership-loss test now observes zero upstream requests. Existing periodic
stream/WebSocket checks remain in place.

## Reviewed source and candidate provenance

Canonical upstream was fetched and pinned before the existing clean worktrees
were created. The deployment-compatible branch retains the documented live
hotfix baseline and unchanged native agentctl pair; it does not replace that
lineage with current upstream main. No source from unrelated dirty/untracked
files was included.

| Artifact | Current revision or SHA-256 |
| --- | --- |
| Canonical native ACL tests | `4de67b57b57532680c40f9d29e94d30f1fa512b1` |
| Canonical implementation head | `1b29c2ff5b86f2b4af08cf1c4bc3be836c46a455` |
| Compatible native ACL tests | `7067010700d605d3bee4a86de555d243f0bdc54c` |
| Compatible superset head | `883439a99d97f8809401f6a83baa8a20279af99d` |
| Static gateway binary | `cb6d21167dc47f9796f02a2c66ead4a0dae899ba0c6106e3c32c10ed5f04d4f6` |
| Scratch gateway image | `sha256:1476f52391b522e43fab380b96059c6b8f8f3c693a77e199fedbcc09e618429b` |
| Compatible FTS5 backend candidate | `dbec5779bcfafc858a41c6240cbebf3557b3613922150e6df4a1f85ed57cacc0` |
| Public-asset manifest | `9795fb290a348d7dc6bdbd6ce6bb4fd563f260e771d93f54f63559e2f1120289` |

Both source branches are pushed to `yattdev/kandev` as
`support/task-preview-85278886` and `support/task-preview-hotfix-85278886`.
Apply the existing baseline and preview patch first, then the new
`patches/kandev-v096-task-preview-authorization-tests.patch`
(SHA-256 `34346d9b6010c53642d6f8a56c3999f9fb80a0e7769a11a5a247965a301ce782`)
and `patches/kandev-v096-task-preview-dial-binding.patch`
(SHA-256 `168bb06a25e27c7cf94c9a7183f887bfa5fc9c205dcdc75de843de2294e3382e`).

The gateway image was built with Go 1.26.0, CGO disabled, trimpath and only the
public CA bundle. It has no data/provider/socket mounts. A disposable no-network,
no-state invocation refused startup before opening a listener. It is not running.
The compatible backend was built with CGO and FTS5, trimpath, stripped symbols
and buildvcs disabled, from the pinned compatible source. It has not been copied
into `.local-hotfix`, an active image or any deployed overlay.

Local candidates are `/tmp/kandev-preview-image-85278886-r1/kandev-task-preview`
and `/tmp/kandev-preview-candidate-85278886/r1/kandev`; verify the recorded hashes
before any later use. The local image ID above, rather than its mutable tag, is
the activation reference. If artifacts have expired, rebuild from the pinned
source and record new hashes; never substitute another binary silently.

The content-free file digest manifest is retained at
`support-evidence/task-preview-85278886-public-assets.json`.
All **362 public frontend file bodies** from the retained generated asset tree
were verified against the captured backend and the new backend, with unchanged
asset paths and matching copied-source hashes. This corrects the original plan's
361 count. Both existing agentctl binaries remain byte-for-byte unchanged.
The prior image `sha256:dee1871874fdf4b091b5b2c52c4b18d85e96cd36d443f338326d3e4f9f88d8d2`
and earlier backend candidate are superseded, unactivated artifacts.

## Bounded acceptance evidence

- Canonical: all preview and auth/httpmw tests passed under the race detector;
  standalone gateway command builds.
- Compatible superset: full preview suite under FTS5 and race detector passed
  (4.126 seconds); native backend preview authorization passed under FTS5 and
  race detector (2.506 seconds). Prior retained hotfix regressions remain green
  as recorded in the initial implementation review.
- Changed preview package lint: **0 issues**. Go formatting, architecture checks,
  commit message validation and whitespace checks passed.
- Python issuer and broker acceptance passed, including exact boot capture,
  malformed/future boot refusal before publication, immutable issuance,
  secret-free login staging, foreign-task denial and idempotent own revocation.
- Scratch image startup without authority fails closed. Existing synthetic
  container isolation and activation-patch/systemd verification remain valid;
  those deployment files were not changed in this pass.

The adversarial socket tests were red before the implementation change, then
green. These are synthetic installation tests, not browser/product evaluation.
No live Human-authenticated positive result is claimed before activation.
The mandatory live `test.sh` gate remains pending the separately approved
recreate; Dockerfile.local and compose changes are still unapplied artifacts.

## Only the remaining decisions and activation steps

1. Approve the existing concrete single production build/recreate plan through
   `scripts/kandev-safe-deploy --build`, including an operator-selected maintenance
   window and its production control-plane interruption. No task park, resume or
   queue replay is included. The existing HTTP-200 gate, automatic verified
   rollback and post-success `bash test.sh` are mandatory. A recovered rollback
   is still BLOCKED. Preserve the captured image and all three original binaries.
2. Supply the existing trusted main HTTPS origin and isolated preview HTTPS
   origin, dedicated preview certificate/key references and an available exact
   private listen address. Prefer distinct registrable sites for cookie isolation;
   verify main's cookie is host-only. The validator enforces distinct hostnames,
   not a public-suffix policy. Do not invent DNS/certificates, use a different port
   on the same host, repurpose another listener or introduce a generic relay.
   If trusted main TLS does not exist, approve only the concrete local main TLS
   bridge plan after its exact bindings are supplied; it is not implicit here.
3. Owner verifies/restores the **exact V2 container** before issuance. Last bounded
   observation at approximately 2026-10-14T03:17:40Z found it stopped, finished
   2026-10-14T02:23:23.421420001Z, exit 0, not OOM. No Support lifecycle change
   occurred. A replacement ID needs exact target review; V1 is never eligible.

Prepare an empty mode-0700 state directory before applying the reviewed compose
mount. Production then starts with preview disabled. After the bridge is healthy,
revalidate the exact target/model/claim and issue the fixed 24-hour grant; the
existing data-directory bind observes those newly created files without another
recreate. The issuer captures the boot time and prints only the non-secret
receipt. Add the image/TLS references to its private generated listener.env, then
start only `kandev-task-preview.service` and verify the deployed binding.

The owner stages only the existing disposable trial login through
`docker kandev preview stage-login 85278886-f97b-4219-b7ba-9182f7059c69 <own-task-login.json>`.
Human retrieves it through the authenticated main `/api/v1/task-preview/credentials`
route, never through chat/logs/URL or a claimed local-file handoff. No provider
credential is sought. Owner then verifies preview origin, unauthenticated denial,
browser login/UI and post-park persistence independently. Evaluation remains
subject to the separate explicit budget/duration decision.

Revocation is the exact owner operation
`docker kandev preview revoke 85278886-f97b-4219-b7ba-9182f7059c69` or the authenticated
preview revoke control. Support can stop only the dedicated preview unit.
Rollback revokes first, stops that unit and uses the captured production image
through the safe deploy procedure if necessary; neither trial or its data is
removed. No current URL or issued/expires timestamp exists.
