# Approved successor activation: server deployment accepted, access unissued

Request `24103b2e-b245-4644-9828-15ff9adaf614` is **BLOCKED for complete browser
activation**, with the approved independent server work completed below. This is
an execution result, not another plan or permission request. Original request
85278886 stays closed. Main Coordinator owns production execution; c6 owns trial
owner/client follow-through. No duplicate worker or polling routine was created.

## Execution and authorization receipt

The content-free [EXECUTING receipt](support-evidence/task-preview-activation-24103b2e-executing.json)
was pushed at commit `1573273`, approximately one minute after pickup, before
production changes. It names thread `01a137d6-f9dc-7ad0-b2c0-10bb5a542722`, request
and started exact-image/target/candidate preflight. Platform turn ID was not
exported; local operation-turn correlation
`dd53cd84-c99a-4c17-bfb6-dab8c16d3f4c` is explicitly not a fabricated platform ID.

Human authorization supplied by Root is bundle
`4a3b754f-1d56-4d47-aebd-10344897befc`, answered q1_opt1 at
2026-10-14T23:55:02.716295774Z; question message
`90f4bb32-73fd-483b-9554-40d6c61ea7a4`, SHA-256
`dff0b8b2a9965df090c624cbaffeb90c151aeaac75472201f5173a638ca28c83`.
The reported client answer is Chrome and LAN IP 192.168.50.131. **Client OS is
still unspecified.** No client trust/hosts/session change was made or inferred.
The original exact approval readback is caller-attested; Support did not mint an
auth token or query other conversations to restate it.

## Actual production operation and preservation

Exactly **one** `scripts/kandev-safe-deploy --build` ran from deployment main.
It exited 0, accepted HTTP 200 and did not roll back. An exclusive attempt marker
and content-free result are retained in the private rollback directory. No second
build/recreate, raw Compose up, binary process hot-swap or manual restart ran.

| Item | Actual accepted value |
| --- | --- |
| New production container | `2d2b866221ecad48a67383db0dcae20a15128b38ad477ca41b406e451a5dcdbe` |
| New production image | `sha256:7cd0c17fd24fd6c7e84ae29a3a0d4c374942aaf3def54a4716e26dd149e3422f` |
| Started UTC | `2026-10-15T00:05:57.269376664Z` |
| Backend | `dbec5779bcfafc858a41c6240cbebf3557b3613922150e6df4a1f85ed57cacc0` |
| Native agentctl, unchanged | `4181384550bbe0d1c1f2f1f5157a4a819482417ed8789a8903155779292da8ec` |
| Remote agentctl, unchanged | `bc7f9d9494ff117bf2bd884fa10f6f4e0e92104fa8c75cd0063edcc81cfa7869` |
| Deployment suite | `bash test.sh`: **129 passed, 0 failed**, exit 0 |
| AppArmor | `kandev-codex`; deployment suite verifies sandbox profiles |

The live preimage matched the approved historical image and trio before copying.
Rollback custody at
`/home/ayattara/.local/share/kandev/support-rollback/preview-24103b2e` contains the
original trio, exact changed configuration copies and a digest manifest; directory
0700/files0600. Captured immutable image is
`sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`, additionally
retained under `kandev-local:preview-24103b2e-preimage`. Rollback uses the **image ID**,
not that mutable retention tag. No database/key/model snapshot was taken.

The exact accepted source remains compatible superset
`883439a99d97f8809401f6a83baa8a20279af99d`, canonical feature
`1b29c2ff5b86f2b4af08cf1c4bc3be836c46a455`. The full installed lineage was reconciled
against `.local-hotfix/README.md` and the accepted [compatible review](TASK-PREVIEW-85278886-ESCALATION1.md):
queue/wake/terminal recovery, guarded inference/liveness, attachment/worktree
adoption, strict profile/Coordinator handoff/global-profile scope, plan CAS,
own-question/mixed batches, sender receipts and delivered-answer reconciliation.
The unchanged adoption patch and 362 retained frontend file bodies remain covered
by the accepted manifest
`9795fb290a348d7dc6bdbd6ce6bb4fd563f260e771d93f54f63559e2f1120289` and exact old/new
binary digests. No undeployed later reporting patch was substituted. New suite
SPA/asset checks also passed. Shared source remains at cfd6bdf… with unrelated
tracked/untracked files untouched; unrelated deployment tests/files also survive.

The approved image adds the existing preview broker helper and mounts only the
fresh empty `task-preview-c4819364` store at `/run/kandev-task-preview`. The agent
guard hides this private mount. No manifest, signing key, login or gateway env
exists in that store. Backend preview access therefore remains fail-closed.

## Actual TLS and auxiliary-service preparation

Official Caddy release [v2.11.7](https://github.com/caddyserver/caddy/releases/tag/v2.11.7)
was resolved from caddyserver/caddy at immutable source
`72dd0fb067f6d7826c7f79907670ba4a713bfe37`. Archive SHA-256
`727b91701a392de6ebc5027509f548bf39979e5216340d0faed8fa5e69c84f8b` matched GitHub's
published asset digest; SHA-512 also matched its official checksum manifest
(SHA-256 `5d27b76b95f496638d79208c55250317b8755fd9e90005f7466aa32956944a90`).
No Sigstore verification is claimed. Static binary SHA-256 is
`678ade3bfc088749c81a681adc603333ee0bb023b6a6cfe3c0f58bef8ff854e9`.
The non-root scratch bridge image is pinned at
`sha256:53932d6768f7da3e67f30c9916ea5a346395cb8e6cbf991de90c0003faa153c3`.
A preactivation binary-mode error was corrected and offline validation passed
before starting this auxiliary service; this was not a failed Kandev deployment.

Actual new server-only PKI is in
`/home/ayattara/.config/kandev/preview-c4819364-tls`, with private directories and
leaf keys. No key values were printed, logged, committed or copied to agents.
The CA is encrypted, critical name-constrained to the two approved names, pathlen
0. Its random signing passphrase existed only in memory/stdin and was discarded
after signing exactly the two approved leaves; no later CA signing/renewal is
available from that passphrase. The retained encrypted CA private key is never
container-mounted. This is a nonrenewing temporary authority, not a reusable CA.

| Public certificate metadata | Value |
| --- | --- |
| Root SHA-256 fingerprint | `22:27:92:2E:88:99:A0:6A:C5:C8:6D:AE:D6:0F:C7:AD:28:AB:AA:2D:5A:E4:6D:EA:DB:EA:B4:8B:5B:C0:39:3B` |
| Root validity | 2026-10-15T00:03:01Z to 2026-10-22T00:03:01Z |
| Both leaf validities | 2026-10-15T00:03:01Z to 2026-10-17T00:03:01Z |
| Exact separate SANs | `kandev-main.test`; `trial-afdb2ef3.test` |

To fit a full 24-hour grant within these leaf validities, issuance must precede
2026-10-16T00:03:01Z (allow operational margin). Otherwise stop; new certificates/
authority trust need a concrete reviewed continuation, never silent renewal.
No system-wide CA import or browser trust change occurred.

The approved main TLS unit is **active** at only `192.168.50.131:59443`, forwarding
only to `127.0.0.1:38429`, with exact Host and loopback-forwarded https scheme.
Its non-root container is read-only, cap-drop ALL, NoNewPrivileges, with only
Caddyfile and dedicated main leaf/key mounts. Admin, ACME, HTTP redirects,
HTTP/3/UDP and access logs are disabled. No new firewall, NAT, wildcard bind,
system DNS/hosts mapping or client reachability claim is included.

The preview unit is installed **stopped**, with exact future private 59444 binding,
fixed trial 59433, read-only public CA bundle and main --add-host mapping. Gateway
binary/image remains unchanged:
`cb6d21167dc47f9796f02a2c66ead4a0dae899ba0c6106e3c32c10ed5f04d4f6` /
`sha256:1476f52391b522e43fab380b96059c6b8f8f3c693a77e199fedbcc09e618429b`.
There is **no listener on 59444**, no gateway env/manifest and no usable preview URL.

## Verification separated from missing access gates

Completed platform acceptance:

- Activation patch applicability, unit verification and offline Caddy config /
  exact leaf-reference validation passed. Official artifact digests were checked.
- Compatible preview and backend native authorization tests passed with FTS5/race
  using synthetic fixtures; existing issuer/broker tests passed. No real provider
  or trial request was submitted. Retained wider hotfix tests remain the accepted
  source evidence, and the full actual deployment suite passed all 129 checks.
- OpenSSL chain/SAN checks passed for the two names; unrelated-name checks denied.
  Independent public-certificate parsing confirmed critical constraints/pathlen.
- Exact main TLS SNI/Host verified using the dedicated public CA (no curl-k or
  system trust change). Main root returned 200; unauth authorize/credentials 401;
  foreign Origin request and unsigned/no-grant control 403. Wrong Host returned
  no upstream content. No response cookies, headers, body or login values were
  printed/copied. The [platform TLS receipt](support-evidence/task-preview-activation-24103b2e-tls.json)
  distinguishes these results from authenticated browser acceptance.

Still **not complete**, so no grant/lifetime/login delivery is claimed:

1. c6/trial MAIN's already-running fresh **nonsecret** ownership/model/claim,
   environment/root/MAIN and actual existing-user/native task-workspace ACL
   attestations have not been supplied to this request. No duplicate owner prompt
   or hidden status probe was sent. Supplied local verifier PASS addenda apply
   only to the frozen target, not this installation or Human browser.
2. Client OS for Chrome remains missing. c6/owner must record it, then record the
   precise dedicated-profile CA import/removal and hosts-resolution recipe and
   Human trust readiness before any client trust change. Browser sign-in must
   use the existing account at the exact TLS host; never copy sessions. Root's
   supplied IP equals the server address, but does not prove client OS/topology.
3. **Existing issuer/validator contract must be reconciled with the raw-model
   prohibition.** `scripts/kandev-task-preview-issue` reads the retained model and
   hashes its bytes; `internal/taskpreview/inspector.go` also reads/hashes it for
   runtime ownership checks. An owner-provided digest alone does not make those
   reads disappear or make the current issuer attestation-only. Neither path was
   invoked; no sanitized shadow model, proxy reader, indirect hash or manual
   manifest was substituted. Preserve fail-closed checks. Root must identify a
   reviewed attestation-compatible operation, or obtain exact scoped authority
   for the existing trusted issuer/runtime validation; current instructions do
   not authorize Support to resolve this by new implementation or model access.
4. Authenticated real-browser/native ACL positive, cross-user/workspace and
   installed preview cookie/origin/target/boot/expiry/revocation tests remain
   pending. Synthetic tests cover those branches, but are not a real grant.
   Trial owner alone stages the existing disposable login through
   `docker kandev preview stage-login c4819364-2566-4876-848f-84c559f8d328 <own-task-login.json>`
   only after the grant is safely issued. Human then uses authenticated main
   credentials/authorize flows; no raw password is delivered in plans/logs/URLs.
   Final real own-grant revoke denial also remains pending, not claimed from mocks.

The [owner-input artifact](support-evidence/task-preview-activation-24103b2e-owner-inputs.json)
is directed to c6 and the existing MAIN, not a Human relay request or another
trial work order. It requests only the missing OS and nonsecret attestations.
No callable authenticated Kandev messaging surface was available to this Support
turn; a token-minting notification workaround was not used. This pushed outcome
returns through the originating reviewed broker for Root/c6 coordination.

## Preserved target and remaining operation

Final curated metadata still matches c9b3a34c… at boot
2026-10-14T02:34:57.681270133Z, image4c48…, project kd_35edab1ae47e8cae45d91975/core,
only loopback 59433→59430. Old fed730… remains stopped/reserved at59432. No trial
request, rebuild/restart, data/login mutation, task move/cleanup, source feature
work, session/queue operation, direct DB/auth write, auth token mint, provider
configuration/inference/evaluation or client trust change was performed by Support.

The next authorized execution does **not** need another unqualified production
build: hooks and helper are already installed. Do not rerun this request's build
marker. Complete only the exact missing owner/client/model-contract gates, then
use a fresh fully approved template/receipt, issue once at +86400 seconds, start
the dedicated preview gateway, have the owner stage the login, and complete the
installed/browser/revoke checks. If those gates cannot be met, keep access
unissued. No whole-trial PASS or token-free usable preview URL exists yet.

Approved rollback custody remains available. Revoke any later grant first and
stop only these two auxiliary units. For a required production rollback, restore
only the request-owned config/overlay deltas from the private captured manifest
(preserving unrelated files) and use
`scripts/kandev-safe-deploy --restore-image sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`;
require HTTP200 and original trio. This is the existing specific rollback consent,
not authority for another build. No rollback was needed in this execution.

The [final content-free receipt](support-evidence/task-preview-activation-24103b2e-final.json)
records preparation/deployment/tests/TLS/client/issuance/login/ACL/browser gates
separately. The prior automatic rejection of raw model access is still honored;
no rejected read was reattempted. Actual server progress is persisted without
claiming complete activation or asking for the already granted deployment/TLS
approval again.
