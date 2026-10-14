# Successor preview: completed plan-only activation review

Request `c4819364-2566-4876-848f-84c559f8d328` is **RESOLVED for the requested
read-only/plan package**. Live activation remains unapproved and unperformed.
Original implementation request `85278886-f97b-4219-b7ba-9182f7059c69` stays
closed; its accepted implementation/tests are reused, not reimplemented.
Main Coordinator retains production execution ownership. No usable URL, grant,
issuance/expiry time, certificate, login delivery or production deployment is
claimed. Every address/configuration below is an **uninstalled, untrusted proposal**.

## Exact successor review

| Binding | Successor reviewed here |
| --- | --- |
| Task / workspace | `afdb2ef3-06ca-4cd5-a074-c4e691679da9` / `2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd` |
| Owner MAIN | `fafba895-b769-40d5-a840-f6b90b98fcb4` |
| Container | `c9b3a34c34cac4c346e5f3728fad74794664f208a12dec78a59beea45f4cb253` |
| Observed boot | `2026-10-14T02:34:57.681270133Z` |
| Image | `sha256:4c48f445367095556ad2b4fbd80746997d3daea11076c8320f6181485f0ff9ae` |
| Project / service | `kd_35edab1ae47e8cae45d91975` / `core` |
| Publication | **only** `127.0.0.1:59433` → `59430/tcp` |
| Core revision, owner supplied | `8d163e959a62a5766a0e6922473bef99f0157c82` |
| Owner binding artifact SHA-256 | `62178733965d31da53656ae1352cc33a4a99b1a7614f66706c315d7c9759641e` |
| Owner runtime receipt SHA-256 | `b445c8b63934dc76a36ed282ed713c5051ed9f472228cef61541ec9b8960b2d1` |

Curated Docker metadata independently matched container/image/project/service,
running state, exact loopback publication and boot. Source revision, artifact
hashes, authenticated UI/401 checks, asset/board counts and screenshots remain
owner evidence; Support made **no trial HTTP requests** or product assertions.

The existing issuer and inspector are target-parameterized: this project's
24-hex suffix, fixed service, ports and immutable image/boot fit their checks.
Provider-capable trial contents do not require a gateway code change. This is
**structural compatibility**, not approval to bind or proof that native ACL,
model/claim or current UI acceptance has passed. Current independent activation
verdicts remain the existing Review/QA owners' responsibility; their separate
admission repair is not duplicated here.

The old V2 `fed730dc124fb13a704c4ec9c39b973e697f06f4062cc34472eadd84efd8f0c6`
was independently observed stopped, with its `59432` publication preserved.
V1 `0f6657…`/59430 is also excluded. Do not restore either, alias/reuse 59432,
edit its old manifest/template into a successor, or treat the earlier Human
approval as an exact new-container grant.

Automatic approval review rejected reading/hashing the complete retained broker
model because it may contain configuration or credentials; hashing still reads
those values. The rejected action did not execute and no workaround was used.
The finished plan instead requires the owner's **nonsecret model digest and
ownership attestation**. The two supplied artifact hashes are not silently used
as `model_sha256`. No secret/key value was read or copied. This remaining input
does not prevent an inert plan from being completed.

## One recommended operator-local HTTPS binding

Bounded host evidence: host `ayattara-MS-7C35`, interface `enp39s0`, private
address `192.168.50.131/22` (dynamic). TCP 59443 and 59444 were unoccupied;
59433 belongs to the successor's loopback publication. No reservation was made.
The inspected conventional TLS reference paths, old preview listener.env,
Caddy/nginx/stunnel executables and local Caddy image were absent. No reusable
trusted main/preview certificate binding was confirmed; this is not a global
credential or certificate-store search. `host.env` remains absent.

| Purpose | Proposed origin | Exact listener / upstream |
| --- | --- | --- |
| Main authentication/UI TLS bridge | `https://kandev-main.test:59443` | `192.168.50.131:59443` → **only** `127.0.0.1:38429` |
| Exact trial preview | `https://trial-afdb2ef3.test:59444` | `192.168.50.131:59444` → reviewed gateway → **only** `127.0.0.1:59433` |

`.test` is reserved for local testing ([RFC 6761](https://www.rfc-editor.org/rfc/rfc6761.html)).
These are distinct sites, not ports on a shared cookie hostname. Neither name
currently has an approved DNS/trust binding. Before approval, these are proposed
addresses, **not usable access URLs**. Recheck IP ownership, both TCP/UDP port
conflicts and client reachability just before activation. Dynamic-IP drift
invalidates the proposal; do not silently substitute another address.

Recommend an operator-pinned official **Caddy 2** instance for the main TLS bridge,
with no admin API, ACME, HTTP redirect listener, HTTP/3/UDP or access log. Its
binary/image is not currently installed or downloaded; freeze its supported
version, source provenance and immutable digest, and validate its config before
any production operation. This is a separate, explicit main-control-plane TLS
exposure decision, not an implied addition to original preview approval.

The following Caddyfile is an **inert configuration proposal**, not installed or
syntax-validated here (Caddy is absent). The selected version must accept it in
an offline `caddy adapt`/`caddy validate` check before activation:

```caddyfile
{
    admin off
    auto_https off
    persist_config off
    servers {
        protocols h1 h2
    }
}
https://kandev-main.test:59443 {
    bind 192.168.50.131
    tls /run/main/fullchain.pem /run/main/key.pem
    reverse_proxy 127.0.0.1:38429 {
        header_up Host kandev-main.test:59443
        header_up X-Forwarded-Proto https
        header_up -Forwarded
        header_up -X-Forwarded-Host
    }
}
```

The bridge must preserve the exact public Host, overwrite the asserted scheme,
and connect from loopback so `secureMainRequest` accepts it; no caller-selected
upstream or wildcard virtual host is added. Caddy's documented
[bind](https://caddyserver.com/docs/caddyfile/directives/bind),
[proxy headers/WebSockets](https://caddyserver.com/docs/caddyfile/directives/reverse_proxy)
and [global options](https://caddyserver.com/docs/caddyfile/options) support this
proposal. No `tls_insecure_skip_verify` is allowed. Use the existing ordinary
backend authentication, not a second backend or an auth bypass.

Run the bridge as a dedicated non-root, read-only, capability-free container,
host networking only for the fixed loopback upstream; mount only its inert
config and dedicated main leaf certificate/key. No Docker socket, task/source,
production DB, provider credentials or CA signing key is mounted. No access logs
or credential/header/body dumps. A separate bounded user unit
`kandev-main-tls-c4819364.service` owns only this bridge. Its stop leaves the
existing production service and trial intact.

### Certificate provisioning and Human onboarding, after approval only

Use one dedicated short-lived operator-local CA with critical name constraints
for `kandev-main.test` and `trial-afdb2ef3.test`, pathlen 0; two separate server
leaf certificates, each with only its exact DNS SAN, CA:false, serverAuth and
appropriate key usage. Proposed CA lifetime: 7 days; leaf lifetime: 48 hours;
access grant: a separate fixed 24 hours. No automatic certificate/authority
renewal extends the grant. Check SAN, constraints, chain and expiry using
[OpenSSL's extension rules](https://docs.openssl.org/3.0/man5/x509v3_config/).

All paths below are **proposed references**, not files created or inspected:

```text
/home/ayattara/.config/kandev/preview-c4819364-tls/
  ca/root.pem                  public CA certificate/fingerprint
  ca/root.key                  operator-encrypted/offline; NEVER container-mounted
  main/fullchain.pem           main leaf + issuer chain
  main/key.pem                 dedicated main TLS key, mode 0600
  preview/fullchain.pem        preview leaf + issuer chain
  preview/key.pem              dedicated preview TLS key, mode 0600
  gateway/ca-bundle.pem         existing public roots plus this public CA only
  main/Caddyfile               approved exact fixed-route configuration
```

Operator creates a private 0700 directory and keys locally after approval;
passwords/passphrases are entered interactively, never arguments, env, chat or
logs. Support is not asking to receive private material. Record public
fingerprints and key references only. Validate the constraints against both
intended names and an unrelated name in isolated verification. Certificate and
trust-store changes have their own rollback inventory.

On the host and Human workstation, approve exact local hosts-file entries:

```text
192.168.50.131 kandev-main.test trial-afdb2ef3.test
```

Use a dedicated Human browser profile for this temporary CA. Verify its public
fingerprint through the operator-controlled channel, import only root.pem into
that profile's website-authority trust store, then confirm both name-valid TLS
chains without bypassing warnings. Do not install the root system-wide or use
`curl -k`. Client OS/browser and its exact import/remove procedure must be recorded
before making trust changes. Main login at this new hostname requires ordinary
Human sign-in to the **existing account**, because cookies from the old HTTP
hostname are not copied. Verify host-only Secure main auth cookies; Domain-wide
cookies, third-party-cookie workarounds and exported sessions are disallowed.

The scratch gateway also needs **two explicit runtime configuration additions**:
read-only mount of `gateway/ca-bundle.pem` at
`/etc/ssl/certs/ca-certificates.crt`, and Docker
`--add-host kandev-main.test:192.168.50.131`. Host `/etc/hosts` entries alone do
not populate the container's hosts file. The unchanged static Go client otherwise
has only public CA roots. Keep the gateway image/binary digest unchanged by
mounting the dedicated *public* bundle rather than rebuilding it or copying any
CA private key. TLS verification stays enabled. These unit/mount changes are part
of the proposal requiring review/activation consent, not already tested deployment.

No firewall change is assumed. If existing policy prevents the Human client's
path, stop and review only that exact client-source/IP/interface/TCP-port tuple;
no public listener, broad allowlist, port range, NAT or wildcard bind is included.

## New target, old scope and secret-free disposable-login sequence

Proposed new grant identity: `c4819364-2566-4876-848f-84c559f8d328`, **unissued**.
Fresh state directory:
`/home/ayattara/.config/kandev/task-preview-c4819364`, mounted in the backend at
its existing fixed `/run/kandev-task-preview` path. Proposed gateway unit:
`kandev-task-preview-c4819364.service`; its container name/label and environment
file must use this identity/state, not claim the obsolete grant. Only one preview
gateway may run. The existing implementation supports an operator-selected UUID;
no code or agent capability extension is required for the identifier.

1. Recheck old issuance metadata without exposing key/login values. None of
   manifest/key/revoked/login/listener.env existed at the known old state path in
   this bounded audit. If a grant appeared since then, revoke its **exact ID**
   through its owner control before retiring its mount, stop its gateway and
   preserve its private state as revoked evidence. Never remove a revocation
   marker to reuse a store. If still unissued, record that fact; do not fabricate
   a successful old revoke. Preserve old containers, 59432 and original evidence.
2. Record the new Human approval/binding receipt for the exact successor and
   chosen TLS/main exposure. The old bundle `5047d7b6…` proves implementation
   approval only; do not fabricate a new approval UUID/hash from it. Validate the
   real browser account, native task/workspace ACL, current task environment/root
   and owner MAIN. Do not blindly copy the old template's default-user or model
   digest. Owner supplies nonsecret model/claim references/digest; privileged
   verification, if required, must be separately permitted without secret reads.
3. Prepare the fresh empty private state mount before production recreate.
   The attached JSON is nested, `review_only:true`, has null approvals/digests/
   issuance and is **not an issuer input**. Do not flatten or fill it until those
   decisions and attestations exist. No change to the original V2 template occurs.
4. After the production bridge/ACL hooks are healthy, operator revalidates the
   exact successor's current boot/model/claim/publication. A restart or digest
   change requires fresh review; do not restore the old boot or follow a tag.
   Use the existing issuer once with a separately approved complete template,
   fresh state path and exact model-registry root. Capture the content-free
   receipt; `expires_at=issued_at+86400`. Parking does not renew it.
5. Use the existing gateway binary/image and reviewed sandbox, with the fresh
   state/nonce mounts, leaf key/cert, public bundle and exact add-host mapping.
   Do not mount the model registry, source/data, provider files or raw socket.
   Start only the dedicated bridge/gateway units after their reviewed pins match.
6. Owner stages the **existing disposable successor login**, not old V2 login
   and never a provider credential, using its private exact-task JSON and the
   supported post-activation command:

   `docker kandev preview stage-login c4819364-2566-4876-848f-84c559f8d328 <own-task-login.json>`

   Human retrieves it in the authenticated main browser at
   `https://kandev-main.test:59443/api/v1/task-preview/credentials`, then enters it
   in the isolated trial login. No password in chat/plan/log/URL, screenshot of
   the secret endpoint or claimed local-0600-file delivery. Endpoint responses
   must be no-store and foreign/unauthenticated origins must fail. Do not read or
   rotate trial login data on the owner's behalf; immutable staging means wrong
   credentials require revocation and a reviewed fresh grant, not overwrite.
7. Human obtains the main authorize handoff via
   `/api/v1/task-preview/authorize`; the ticket stays in a one-time POST body.
   Only after installed positive/negative checks pass does the Coordinator
   publish the token-free preview URL and actual issued/expires receipt.
   Human self-configures providers later. Support runs no evaluation/model calls.

Supported future owner revocation is
`docker kandev preview revoke c4819364-2566-4876-848f-84c559f8d328`, or the
reviewed authenticated preview revoke control. Stop only its gateway for access
shutdown; keep the irreversible marker and trial/source/data intact.

## Hotfix-preserving production activation and rollback package

Carry forward the accepted [implementation](TASK-PREVIEW-85278886.md),
[compatible source/test review](TASK-PREVIEW-85278886-ESCALATION1.md) and
[terminal audit](TASK-PREVIEW-85278886-ESCALATION2.md). Both checkouts were inspected;
unrelated dirty/untracked files remain untouched. Existing tests are retained
rather than repeated for documentation-only work.

| Artifact reverified | Revision / SHA-256 |
| --- | --- |
| Compatible preview superset, clean | `883439a99d97f8809401f6a83baa8a20279af99d` |
| Canonical feature, recorded | `1b29c2ff5b86f2b4af08cf1c4bc3be836c46a455` |
| Compatible backend candidate | `dbec5779bcfafc858a41c6240cbebf3557b3613922150e6df4a1f85ed57cacc0` |
| Gateway binary | `cb6d21167dc47f9796f02a2c66ead4a0dae899ba0c6106e3c32c10ed5f04d4f6` |
| Gateway scratch image present | `sha256:1476f52391b522e43fab380b96059c6b8f8f3c693a77e199fedbcc09e618429b` |
| 362-file public-assets manifest | `9795fb290a348d7dc6bdbd6ce6bb4fd563f260e771d93f54f63559e2f1120289` |

Retained candidate paths are `/tmp/kandev-preview-candidate-85278886/r1/kandev`
and `/tmp/kandev-preview-image-85278886-r1/kandev-task-preview`. If expired,
rebuild from those pinned sources and record new hashes before activation.
Do not replace production overlays now. The superset is based on restored live
lineage `56d742982b8c2daf0a13cb72c453aecd3471b6a7`, retaining backend
`79b0e8a…` over `02bb5d…` plus unchanged adoption patch. Its full provenance covers
queue/wake/terminal recovery, guarded inference/liveness, attachment/worktree
adoption, exact-profile and Coordinator handoff/global-profile scope, plan CAS,
own-question/mixed-batch, sender receipt and delivered-answer reconciliation.
Both native sidecars and frontend bodies stay unchanged. Reporting patches
created later but not deployed are not silently substituted into this candidate.

Production read-only hashes match its documented installed trio:
backend `75128d854c9f5ddcdebe85fd9e3c057897f460ae1d10535a67805ed9053bf57b`,
native agentctl `4181384550bbe0d1c1f2f1f5157a4a819482417ed8789a8903155779292da8ec`,
remote agentctl `bc7f9d9494ff117bf2bd884fa10f6f4e0e92104fa8c75cd0063edcc81cfa7869`.
Container `3b95b8dbafb8d29c6956e06467cfff09511ff1592f654aec0fe5fa2f9668d172`, image
`sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`,
started `2026-10-12T22:06:50.719127446Z`, remains unchanged.

Before the separately approved maintenance window, the execution owner must:

1. Capture fresh container/image IDs, trio/asset hashes, exact compose/Dockerfile/
   broker/unit/overlay revisions and a private rollback copy of only the changed
   files. Preserve unrelated changes; no blanket reset/clean. Ensure captured
   image and backup trio remain available and sufficient disk is free. Rebase
   the candidate review if live hotfix provenance has changed.
2. Apply the retained activation patch only as a reviewed delta, changing its
   proposed host state source to `task-preview-c4819364`; the container mount
   remains `/run/kandev-task-preview`. Install the existing broker helper and
   exact tested backend candidate into the normal overlay build path while
   preserving both native sidecars and all 362 frontend bodies. Review the new
   TLS/gateway units and public-trust mount/add-host deltas separately.
3. Preserve the accepted regression package: FTS5/race preview tests, native
   auth/workspace ACL tests, original hotfix regressions, issuer/broker tests,
   source formatting/lint and gateway isolation. Recheck patch applicability and
   unit/config syntax. New bridge config, local trust and actual browser behavior
   are **pending acceptance**, not covered by the old synthetic tests.
4. From deployment **main**, perform only:

   `scripts/kandev-safe-deploy --build`

   Its captured-image HTTP-200 readiness gate and automatic verified rollback
   remain mandatory. No bare Compose recreate or binary hot-swap. A rolled-back
   candidate is **BLOCKED**, even when availability is restored. After a successful
   candidate, require `bash test.sh` green before issuing access. Do not weaken
   tests. Record actual deployed provenance and actual maintenance interruption.
5. Only then complete TLS, exact-target issuance, login staging and installation
   acceptance in the sequence above. Do not start the 24-hour clock while awaiting
   Human decisions, missing certificate trust or an unavailable target.

Rollback prerequisites and order are concrete: keep the captured production
image/trio/config backups and exact old/new state inventories, plus browser
trust/hosts-file backups. Revoke any newly issued grant first, stop only the
new gateway and main TLS bridge, preserve revoked state and all trials. For a
failed deployment let safe-deploy restore and HTTP-200 verify automatically.
For post-deploy test failure, restore only approved file/overlay deltas and use
`scripts/kandev-safe-deploy --restore-image <freshly-captured-image-id>`;
verify HTTP 200 and the original trio. Do not use a mutable tag or guess an old
image after the window. Undo only this proposal's hosts mappings, dedicated
browser CA trust and unit/listener bindings; remove no shared CA or unrelated
settings. Retain private keys/state as operator-controlled revoked evidence per
retention policy; no trial or task cleanup is authorized.

## Exact decisions, smallest inputs and acceptance

The finished package needs these decisions/inputs, not another implementation
permission request or a generic hostname/path guessing exercise:

1. **Production window and rollback approval:** one reviewed safe-deploy --build
   control-plane recreate plus documented rollback; Main Coordinator executes.
2. **Successor scope:** the exact c9b3… container/image/project/boot/59433 target,
   fresh grant ID/state and 24-hour lifetime; authenticated approval receipt,
   existing browser user/native ACL/environment identity, and owner nonsecret
   model/claim digest attestation. Do not infer these from the old V2 bundle.
3. **TLS/main exposure and trust:** approve the two proposed names/private
   listeners, temporary dedicated CA/profile trust, fixed-route main bridge and
   gateway public-bundle/add-host mounts. Supply Human client IP and OS/browser
   to finish exact onboarding/connectivity checks; no private key or password.
   Operator pins the Caddy artifact and records public certificate fingerprints
   and validation before execution; if the proposal cannot be validated, stop.
4. **Owner acceptance:** attach the existing independent activation verdicts when
   supplied. Do not substitute Support for either verifier or infer approval
   from their restored protocol readiness.

After approval/installation, operator and owner acceptance requires: trusted
name-valid TLS on both hosts; exact Host/Origin and loopback-forwarded scheme;
main and preview host-only cookies isolated; main browser authorization and
credential retrieval only for the existing approved user; fixed successor UI
origin; native cross-user/workspace denial; unauthenticated/wrong-origin denial;
wrong-container/model/boot and post-connect-race refusal in isolated fixtures;
expiry/revocation/active-stream termination in synthetic fixtures without editing
a live grant; and owner post-park health/UI persistence within the original fixed
window. Do not mutate another user's workspace or restart a target to test denial.
Final own-grant revocation must actually deny future access. Owner performs real
browser/login/product checks; Support has performed none in this plan request.

The [nested inert plan and receipt](support-evidence/task-preview-c4819364-plan.json)
records observations versus proposals and leaves authority/issuance fields null.
Documentation consistency, exact bindings, no-old-target selection, pending
inputs, hash references and links were checked. No certificates/trust/DNS/firewall/
listeners, production source/config/runtime, trial lifecycle/data, credentials,
capabilities or providers were changed. The rejected model read is explicitly
preserved above; no Human relay or additional approval was needed to publish this
read-only package.
