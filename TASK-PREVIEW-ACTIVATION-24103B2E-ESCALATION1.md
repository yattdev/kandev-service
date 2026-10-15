# Approved preview activation: escalation 1 continuation audit

Request `24103b2e-b245-4644-9828-15ff9adaf614` remains **BLOCKED only for complete
browser/capability activation**. The accepted production and main TLS work is
preserved; the original approval is not being requested again. No second build,
rollback, new implementation, duplicate worker or polling routine occurred.

The [continuation EXECUTING receipt](support-evidence/task-preview-activation-24103b2e-escalation1-executing.json)
was pushed at `0108598`, within five minutes of this audit's pickup. It reports
read-only continuation, not a second deployment. The original one-build receipt
and [actual activation report](TASK-PREVIEW-ACTIVATION-24103B2E.md) remain unchanged.
Platform turn ID is not exported; the receipt labels its local operation ID
honestly rather than inventing a platform turn identity.

## Verified existing progress

Both named checkouts were inspected. Deployment is main with only the previously
recorded unrelated user files preserved; shared source remains cfd6bdf… with its
unrelated tracked/untracked files intact. The accepted compatible source checkout
is unchanged at `883439a99d97f8809401f6a83baa8a20279af99d`. This is not an
upstream-only issue, nor a restriction on reviewed Support host diagnostics.

Reviewed host escalation succeeded for the bounded checkpoint:

- Production is still container `2d2b866221ecad48a67383db0dcae20a15128b38ad477ca41b406e451a5dcdbe`,
  image `sha256:7cd0c17fd24fd6c7e84ae29a3a0d4c374942aaf3def54a4716e26dd149e3422f`,
  boot `2026-10-15T00:05:57.269376664Z`.
- Installed backend is exactly `dbec5779bcfafc858a41c6240cbebf3557b3613922150e6df4a1f85ed57cacc0`;
  native/remote hashes remain respectively `4181384550bbe0d1c1f2f1f5157a4a819482417ed8789a8903155779292da8ec`
  and `bc7f9d9494ff117bf2bd884fa10f6f4e0e92104fa8c75cd0063edcc81cfa7869`.
- The private attempt/result markers confirm exactly one safe-deploy --build,
  exit 0. Its original 129/129 mandatory deployment checks remain green evidence;
  no code/config change or new failure justified repeating the whole suite.
- Frozen trial c9b3a34c… is still running at the exact approved boot/image and
  only `127.0.0.1:59433`→59430. No HTTP request or lifecycle operation was sent.
- The main TLS bridge remains active. The preview unit remains inactive, and
  manifest/signing-key/login/gateway-env files remain absent from the fresh
  c4819364 state. No usable preview URL or issuance/expiry exists.

One remaining independent safe installation check was completed: the exact
unchanged gateway image
`sha256:1476f52391b522e43fab380b96059c6b8f8f3c693a77e199fedbcc09e618429b`
was invoked once in a disposable no-network, read-only, cap-free/non-root
container, mounting only the empty c481 state read-only. It denied with the
expected grant-unavailable condition **before** TLS or listener setup. No key,
model, source/data, provider file or Docker socket was mounted. The disposable
container was removed; production/trial/gateway services were not started or
restarted by that check. This proves absent authority fails closed, not actual
browser/ACL access or a real revocation result.

## Scope audit and exhausted safe routes

The request explicitly forbids raw retained-model read/hash, including the prior
rejected action, and permits only approved nonsecret owner attestation. This is
an explicit Support boundary, not an agent-facing Docker restriction mistakenly
applied to Host diagnostics. No fresh rejection was needed to discover the same
boundary: source inspection suffices and the prohibited read was not repeated.

Existing deployed-source behavior remains:

1. `scripts/kandev-task-preview-issue` opens the original model/claim, parses owner
   fields and hashes the complete model before publishing authority.
2. `internal/taskpreview/inspector.go` with the backend's model checks enabled
   reads and hashes that retained model again during request validation.
3. The scalar owner-provided `model_sha256` is a comparison input; it does not
   select an attestation-only reader. No installed attestation-only API/flag was
   found in these exact accepted components. The broker helper supports only
   guarded stage-login/revoke, not issuance through another authority source.

Therefore invoking the ordinary issuer, indirectly hashing through another
helper, substituting a shadow registry, manually constructing authority, or
turning off model checks is not an authorized solution. None was attempted.
A new implementation or second production build is not inferred from this
escalation. The existing accepted code and fail-closed ownership checks stay
intact until Root resolves the exact validation contract.

No callable Kandev connector/browser control or authenticated task-message
surface is available in this Support tool set. Reading/copying cookies or minting
an operator token to obtain one would violate the current constraints. No raw
credential route was substituted. Reviewed host access is available and used;
it cannot establish an unspecified Human client OS or manufacture a fresh owner
attestation from the absent input. No hidden task/plan/foreign-content probe was
used, and absence from this request is not a claim that no record exists elsewhere.

## Smallest remaining follow-through

Root/c6 should complete the exact existing owner/client chain, without another
Support job or Human relay:

- **c6 / existing trial MAIN:** return the fresh approved nonsecret environment,
  root/cwd/claim/model-reference/digest and real native user/task/workspace ACL
  attestations already requested. Do not send raw model, key, login, header or
  provider data. Local Review/QA PASS is preserved as target-local evidence.
- **c6 / client onboarding owner:** record the missing Chrome client OS, the
  corresponding dedicated-profile CA import/remove and name-resolution recipe,
  and Human trust readiness. Do not infer OS from the supplied server IP or from
  the host's own Linux/Chrome installation. No client trust change is authorized
  before that record; existing production browser identity is not copied.
- **Root / reviewed platform authority:** either identify an already approved
  attestation-compatible validation operation, or make the specific decision
  whether the existing trusted issuer/backend may perform its exact pinned
  model/claim checks without returning content. Such permission is not present
  in this request's explicit no-read rule. If implementation rather than that
  existing validation is required, it needs separately scoped review/activation;
  do not silently change the contract or repeat the already consumed build.

The [original owner-input artifact](support-evidence/task-preview-activation-24103b2e-owner-inputs.json)
contains the exact task/MAIN and required nonsecret fields. The pushed broker
outcome is the available Root/c6 coordination path; no duplicate owner prompt was
sent and no generic deployment/TLS permission is requested again.

Only after every gate is satisfied may the issuer fix +86400 seconds, the
preview unit start, the owner stage its existing disposable login, and real
installed/browser/own-grant-revoke acceptance occur. Those receipts cannot be
inferred from successful server deployment, synthetic tests or this empty-state
check. Current leaf validity ends 2026-10-17T00:03:01Z; a complete 24-hour grant
must fit before that end (last issuance before 2026-10-16T00:03:01Z with margin).
No renewal or changed target is implied. Rollback custody and the exact
--restore-image procedure in the first-pass report remain available and unused.

Only this audit and [content-free continuation receipt](support-evidence/task-preview-activation-24103b2e-escalation1.json)
changed. No production/source/config/client/TLS trust change, additional deploy,
trial request, model access, auth token, grant, login delivery, provider call,
source feature work or task/session/queue/database mutation was performed.
