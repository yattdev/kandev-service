# Exact V2 task preview: implementation and activation review

Support request `85278886-f97b-4219-b7ba-9182f7059c69`. Implementation is staged;
no production deployment, preview issuance, listener, or credential delivery has
occurred. The separate production-restart decision remains pending. Final
read-only inspection found V2 externally stopped at 2026-10-14T02:23:23.421420001Z
(exit 0, not OOM); Support did not change its lifecycle. The owner must restore
the same approved container before issuance. A replacement needs an exact new
target review; V1 remains excluded.

Escalation 1 adds native authorization acceptance and a tested connection-race
repair. The current candidates, commits and revised activation sequence are in
[TASK-PREVIEW-85278886-ESCALATION1.md](TASK-PREVIEW-85278886-ESCALATION1.md).
That record supersedes the original candidate hashes below.

## Approved scope and captured target

Human's answered question `core_trial_preview_20261014`, message
`46686621-8ba9-42b9-b3cd-c8f3972c4899`, bundle
`5047d7b6-8074-4e24-a025-7912eb4223d8`, selected `q1_opt1`. The approved question
SHA-256 is `1d810c4065a9129ec6cbd3a7a0c66241c943a336bab926a42fffddc372d4f07a`.
The existing approved workspace owner is `default-user`; the issuer also requires
a live real browser session and rechecks normal user/task authorization.

Only task `afdb2ef3-06ca-4cd5-a074-c4e691679da9`, workspace
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`, current owner session
`fafba895-b769-40d5-a840-f6b90b98fcb4`, and the following V2 target are covered:

| Binding | Value |
| --- | --- |
| Container | `fed730dc124fb13a704c4ec9c39b973e697f06f4062cc34472eadd84efd8f0c6` |
| Project/service | `kd_2d20a7e4bdd453f1d4654dab` / `core` |
| Image | `sha256:f6f56d17673a91782f021acc9f0b9c5c556795163494025e19aef207eb1ca88d` |
| Publication | host `127.0.0.1:59432` to container `59430/tcp` |
| Task root | `/data/tasks/provision-isolated-c_lhtgd60a` |
| Clone | task-root child `ct-afdb2ef3` |
| Saved model SHA-256 | `50899d4ca216ed1d6ad5be614e1e5bb26e7706133396fc3465ad9ad0161c238a` |

Both saved-model and immutable project-claim ownership were read-only verified.
V1 (`0f6657...`, port 59430) is excluded and remains untouched. No trial rebuild,
restart, account change, data mutation, evaluation, or provider call is included.
Q2 permits Human to configure provider/account/model later; Support provisions
no provider credentials. Evaluation still requires explicit budget/duration.

## Code and trust boundary

Canonical `https://github.com/kdlbs/kandev.git` upstream/main was fetched and
verified at `2f501583ff55b9f64047ae29c99b39c33ee5d2cb` before creating the
isolated source checkout. Source branch: `support/task-preview-85278886`. The deployment-compatible
superset is `support/task-preview-hotfix-85278886`, based on the captured
`02bb5d...` parent with the exact documented deployed reconciliation and adoption
patches restored before the new preview changes.

The source adds `internal/taskpreview`, the standalone `cmd/kandev-task-preview`
TLS service, and narrowly wired production control endpoints. The registry is a
single operator-installed manifest and private signing key; absent/invalid state
fails closed. It is never registered through HTTP or agent-controlled inputs.

1. Human uses an existing production browser session at the exact trusted main
   HTTPS origin. `GET /api/v1/task-preview/authorize` requires a real session,
   the registered user, active account and normal task/workspace access.
2. A one-minute, exact-grant/user/binding ticket is POSTed in a form body to the
   separate preview hostname. No ticket, password or main cookie appears in a
   URL. Redemption is one-time and persists across gateway process restarts.
3. The preview sets a host-only Secure/HttpOnly/SameSite=Strict authorization
   cookie. The trial cannot set or receive this cookie. Different ports on one
   hostname are explicitly insufficient for cookie isolation.
4. Every proxied request rechecks live user/task authorization through an
   exact-purpose signed control proof, exact Docker ID/image/project/service/boot timestamp,
   loopback publication, retained task-environment ID/root, original model digest
   and ownership claim. The latter files are re-read through the existing data
   bind so atomic registry replacements are observed. There is no
   caller-selected target, Docker command, workspace, filesystem path or user.
5. The gateway validates browser Origin, normalizes only the inner HTTP hop for
   the unchanged trial's CSRF/WS checks, and proxies only the fixed loopback
   port. Native trial cookies remain confined to the preview hostname. HTTP
   streaming and WebSocket connections close after expiry/revocation or a
   failed periodic authorization/ownership recheck.
6. Issuance fixes `expires_at = issued_at + 86400`; reauthentication and parking
   cannot extend it. No executor/session liveness is required. Account/task
   authorization and the original running container must remain valid.

The sole cookie-free production endpoint is POST
`/api/v1/task-preview/check`. It accepts only a 15-second purpose-separated HMAC
proof for this registered binding and user, then performs the normal active-user
and task/workspace authorization plus target validation. Adjacent paths and GET
are not allowlisted. Missing state/key, bad proof, stale binding or disabled auth
denies access. No production database grant/token rows are created.

The gateway has no Docker socket or production data access and no access logger.
Its manifest, key, login payload and irreversible revocation marker are read-only
in its namespace; only the nonce ledger child is writable. Browser revocation is
signed back to the existing backend. The gateway uses a dedicated scratch container, its own PID/filesystem namespaces,
a read-only root, zero capabilities and NoNewPrivileges, a non-root UID, bounded
CPU/memory/PIDs, and no ambient provider environment. It mounts no Docker socket,
process tree, task/source/data directory or provider credential. Host networking
is necessary for the fixed loopback trial and the existing HTTPS authorization
bridge; the reviewed listener binds one exact private IP/port. It passes no caller Authorization header
or preview credential to the trial, disables response caching, and uses a
dedicated empty Docker client configuration rather than registry credentials.

## Task-owned disposable login delivery

The task owner prepares an existing disposable trial login as a private JSON
file **inside that exact owner task root**, with only `email` and `password`.
Support has not read or copied that login. Once activation is approved and the
new broker helper is installed, the owner's existing guarded CLI can run:

```text
docker kandev preview stage-login 85278886-f97b-4219-b7ba-9182f7059c69 <own-task-login.json>
```

The broker requires its existing verified task-root token, the exact registered
task root/grant, bounded private regular input, descriptor-anchored no-symlink path traversal,
nonblocking rejection of FIFOs, active lifetime and an immutable
private destination. It returns only `login_delivery_ready`; values and secret
hashes are never printed. Coordinators/other tasks cannot substitute themselves.

Human obtains the existing disposable login by directly opening the trusted main
origin's `/api/v1/task-preview/credentials` in the already-authenticated production
browser. It requires the same real owner session and live task authorization,
checks the target, rejects foreign origins, and returns no-store JSON. This is
authenticated Human delivery, not an assertion that a local 0600 file was handed
to Human. The password is never put in chat, plans, logs, query strings or URLs.
The original task-owned file and the trial database are not modified.

## Guarded revocation and stop

The owner may revoke only its exact grant with:

```text
docker kandev preview revoke 85278886-f97b-4219-b7ba-9182f7059c69
```

This atomically creates an irreversible private marker and is idempotent. It
does not stop/restart the trial, enqueue a turn, or mutate production data.
Existing preview sessions, handoff tickets and login retrieval then fail closed;
active streams are terminated by the gateway. The authenticated preview user
can also POST `/__preview/revoke` from its own preview origin; this signs an
exact-purpose revocation request to the backend. The gateway cannot remove or
rewrite the backend-owned marker. Trusted host
Support can stop only `kandev-task-preview.service`. None of these operations
touches the Kandev production service or V1/V2 trial lifecycle.

## Concrete activation plan (not executed)

The required decision is approval of this bounded production recreate and the
two concrete trusted HTTPS origins/certificate bindings. New preview access is
already approved; that approval is not being requested again. No hostname/TLS
trust reference was supplied, and `host.env` is absent. The template deliberately
contains invalid origin placeholders and zero issuance/expiry so it cannot run.

1. Resolve an existing trusted production HTTPS origin and a **different
   hostname** for this preview, a dedicated trusted preview certificate/key and
   one exact LAN IP/listen port. Preserve the existing production auth cookie
   host. Select distinct registrable sites for main and preview to avoid parent-
   domain cookie interference; the manifest validator itself checks distinct hosts.
   The production TLS terminator must be local, preserve Host and set
   X-Forwarded-Proto=https; remote cleartext assertions are rejected. If no main
   TLS origin exists, its exact authentication-bridge TLS exposure is an
   additional scope decision, not an implied generic production proxy grant.
2. Owner restores the exact V2 container without rebuilding/replacing it.
   Revalidate the live target/model/claim and all approval metadata. Fill only
   the reviewed origin fields in the template. Run the host-only
   `scripts/kandev-task-preview-issue` later, after step 6 has passed. Before
   the compose build, prepare only an empty private mode-0700
   `%h/.config/kandev/task-preview-85278886` directory, outside all production
   data/Code identity mounts. An empty mount fails closed. Do not issue the grant
   while awaiting restart approval. Issuance after a healthy bridge creates the
   key, exact boot pin and fixed 24-hour window without another recreate. The
   key never enters Git, task roots or chat. A restart of the same trial after
   issuance invalidates the grant; parking its outer task does not.
3. Build the static standalone gateway (`CGO_ENABLED=0 go build -trimpath`) and
   a scratch image using `Dockerfile.task-preview`. Its isolated build context
   contains only that binary and the public system CA bundle. Record the source
   commit, binary digest and immutable image ID; use that image ID with
   `--pull=never`. Install the reviewed user service and add only its three
   non-secret image/certificate/key references to the private listener.env.
   The service passes private authority read-only, its nonce child read-write,
   and only the dedicated TLS certificate/key read-only. Keep all other host
   paths inaccessible. Verify the documented UID 1000 matches the state/key
   owner before activation. A synthetic test proved these Docker mount/capability
   restrictions; the host user service manager could not enforce read-only bind
   namespaces, so that weaker host-process design was rejected. The backend re-reads the original current model/claim paths
   through its existing data identity bind; the gateway mounts no model/data
   directory. The agent guard's fresh `/run` hides the only container mount of
   private preview state.
4. Prepare a **superset** backend overlay from deployed source
   `79b0e8a39b7a3ff74cf15fa611202ab558dfaa64` (parent
   `02bb5d05944141c9e03ad746dde120668f98e46f`) plus the unchanged workspace
   adoption patch and this reviewed preview patch. Do not substitute the
   canonical development branch's backend binary for the deployed hotfix
   lineage. Preserve all 362 retained public frontend file bodies and their asset paths and both existing
   agentctl binaries. The prepared `support/task-preview-hotfix-85278886` branch contains this
   restored baseline plus the preview overlay; run the prior hotfix acceptance
   and new preview tests on that superset before producing any replacement
   backend binary. The escalation record pins the already built superset
   candidate and its public-asset preservation evidence.
5. Prepare the compose delta: bind only this exact private state at
   `/run/kandev-task-preview`. No metadata/data parent or inode-pinned model file
   is newly mounted. Add the helper COPY described
   in `support-evidence/task-preview-85278886-activation.patch`. Do not mount
   provider credentials, task/source/data parents or TLS keys into agents.
6. On approved `main`, use **only** `scripts/kandev-safe-deploy --build` for
   the production build/recreate. Its captured-image HTTP-200 gate and verified
   automatic rollback remain mandatory. A recovered rollback is BLOCKED.
   Run `bash test.sh` after successful activation; no assertion may be weakened.
7. With the production bridge healthy and the exact V2 target running, invoke
   the issuer using the reviewed template and exact model root. Capture the
   content-free receipt. Add the reviewed image/TLS references to the generated
   private listener.env (issuance creates its LISTEN entry); never overwrite the
   manifest or key. Then start only the dedicated TLS gateway.
   If a host firewall rule is necessary, scope it to the exact approved LAN
   listener/source boundary; do not add broad port ranges or public listeners.
   Hand off the issued/expires timestamps and a token-free HTTPS URL only after
   verifying deployed code, model/claim/target pins and unauthenticated denial.

No production recreate, unit installation/start, grant issuance, firewall change,
TLS trust change, secret staging or listener has been executed by this request.

## Existing deployment provenance and rollback

Captured production container: `3b95b8dbafb8d29c6956e06467cfff09511ff1592f654aec0fe5fa2f9668d172`.
Captured image: `sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`.
Its exact unchanged trio is documented by `patches/kandev-v096-own-answer-reconciliation.md`:

| Artifact | Preserved SHA-256 |
| --- | --- |
| backend | `75128d854c9f5ddcdebe85fd9e3c057897f460ae1d10535a67805ed9053bf57b` |
| native agentctl | `4181384550bbe0d1c1f2f1f5157a4a819482417ed8789a8903155779292da8ec` |
| remote agentctl | `bc7f9d9494ff117bf2bd884fa10f6f4e0e92104fa8c75cd0063edcc81cfa7869` |

That lineage includes the queue/wake/terminal recovery, guarded inference and
liveness, attachment/worktree adoption, strict exact-profile and Coordinator
handoff/global-profile scope, plan CAS, own-question lifecycle/mixed batches,
sender-owned message receipts and native delivered-answer reconciliation fixes.
The adoption patch SHA remains
`79b787b189b8df3742d5bd67d838974232f2517c14e3bdd4ce64bab0e9274e2a`.
No deployed binary, image or overlay file has been replaced.

Rollback first revokes the private preview grant and stops only its user service.
Leave both trials and their data intact. A failed candidate production recreate
must be rolled back and HTTP-200 verified by `kandev-safe-deploy`; report BLOCKED
even after availability is restored. Restore prior compose/broker/backend files
from their exact captured revisions only through the same gated procedure.
Keep non-secret provenance; remove only this preview's private runtime state and
dedicated TLS bindings after revocation. Never remove trial source/data/evidence.

## Acceptance and owner handoff

Synthetic Go tests cover real HTTP/TLS/WS transport, authorized access, no active
executor dependency, fixed 24-hour expiry, cross-user/workspace/target/origin
denials, stopped/replaced container and changed model ownership, private-file
guards, durable one-time handoff, browser cookie isolation, live authorization
revocation, active stream/WS expiry/revocation and authenticated login delivery.
The normal auth middleware suite and backend wiring are also checked. Synthetic
Python tests cover exact task/grant ownership, bounded immutable login staging,
secret-free receipts, idempotent own-grant revocation and foreign-task denials.
Verification outputs and final source/deployment commits are appended after the
checks complete. These are installation tests, not the product evaluation.

After activation, owner independently verifies the canonical preview origin,
unauthenticated denial, browser login/UI and post-park persistence. Human uses
the existing production browser session for the handoff and credential retrieval;
then the disposable trial login. Owner receives no main cookie, host key, Docker
socket or additional provider grant. Provider configuration and model evaluation
remain separate Human-controlled actions with explicit budget/duration.

### Bounded review findings

The implementation deliberately does not use the existing unauthenticated port
runners or the session-lifetime proxy. Main bearer tokens/synthetic identities
cannot issue handoffs; ticket, session, check and revoke signatures have separate
purposes and bind the entire immutable manifest. Both browser hosts require TLS;
shared-host/different-port origins fail validation. The gateway's authority mount
is read-only, so gateway restarts or a writable nonce ledger cannot extend the
lifetime or undo revocation. Service-worker registration is denied to protect the
handoff document. No dynamic upstream or HTTP registration API exists.

A private user-service bind namespace was experimentally unavailable on this
host (`226/NAMESPACE`). The accepted container sandbox was then exercised with
synthetic files and no network: read-only authority, writable nonce child,
UID 1000, zero permitted/effective capabilities, NoNewPrivileges, and absent
socket/data were verified. The running production image was used only as the
local interpreter for that disposable synthetic isolation test; no service,
trial request or production volume was involved. The final gateway image is
scratch with only its static binary and public CA bundle.

### Verified checks

- Canonical source: all `internal/taskpreview` and auth/httpmw tests passed
  under `-race`; command package builds. Full backendapp suite passed before the
  final request-owned watcher drain addition; the exact environment ownership
  wiring test also passed on the deployed-lineage superset.
- Restored deployed source superset: all preview tests passed under `-race`,
  including goleak verification; own-answer/own-question handler, server and
  SQLite regressions plus operator adoption tests passed. PostgreSQL integration
  was not configured; no database schema/query logic is changed by preview.
- Changed-package golangci lint: 0 issues. Harness, architecture and public-copy
  checks passed. Go formatting and diff whitespace checks passed.
- Python issuer and broker acceptance passed; existing Docker broker policy and
  project-artifact suite passed (16 artifact tests). Python compilation passed.
- Activation patch applies cleanly; systemd unit syntax verifies. Disposable
  container sandbox passed the read-only authority/write-only-ledger boundary.
- Final metadata inspection: production and V1 identities/images/running state
  unchanged. V2 retains its exact approved ID/image but was externally stopped;
  the issuer and per-request checks deny stopped targets. No live trial HTTP
  requests were made by Support.

No usable URL, issued_at, expires_at, installed gateway or deployed preview
provenance is claimed. Those fields remain null until the separately approved
activation succeeds. `test.sh` is reserved for the approved production recreate;
Dockerfile.local and compose remain unapplied patch artifacts here.

### Original source and candidate provenance (superseded by escalation 1)

- Canonical development feature commit: `eb6935d8ef65673dda22fa74a774a75e3194c0af`,
  pushed to `yattdev/kandev`, branch `support/task-preview-85278886`.
- Restored deployed baseline: `56d742982b8c2daf0a13cb72c453aecd3471b6a7`.
- Tested compatible preview superset: `f38b3ac9740c16ed9d63962ff1f68aff3ab3860a`,
  pushed to `yattdev/kandev`, branch `support/task-preview-hotfix-85278886`.
  `patches/kandev-v096-task-preview.patch` is that feature-only commit, applied
  after the restored baseline (not directly to canonical current main).
  Patch SHA-256: `2ce887aa8bab5153f1a5e9d7622e0fe6f47327505a19576ba6b1148b15a5da8f`.
- Static gateway binary SHA-256:
  `a89284c165c739b6d39a5243775620a64d0fb75bb306dd95373b1a24dc1c6be8`.
  Go build metadata pins clean feature commit `eb6935d8...`, Go 1.26.0,
  linux/amd64, CGO disabled and trimpath enabled.
- Local scratch gateway candidate image ID (built, **not activated**):
  `sha256:dee1871874fdf4b091b5b2c52c4b18d85e96cd36d443f338326d3e4f9f88d8d2`.
  Image metadata: user `1000:1000`, fixed gateway entrypoint, no volumes.
  A no-network/no-mount invocation verified absent grant fails closed before
  opening a listener. Never use the mutable convenience tag for activation.

Deployment main had unrelated unpublished historical commits before this request.
They and unrelated dirty/untracked files remain intact. Only this request's delta
is exported to a deployment review branch based on the fetched remote main;
remote main is not advanced with that unrelated pending history.
