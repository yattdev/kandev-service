# Independent task candidates

The local agent guard intentionally mounts a source repository's shared
`.git/worktrees` registry read-only. An ordinary task can use its existing
administration entry, but `git worktree add` cannot create another shared entry.
This is deployment guard policy, not a canonical Kandev worktree-manager defect.

For a reviewed Support request authorizing one current-main candidate,
`scripts/kandev-task-candidate.py` provisions an independent clone below the
original checkout's ignored `.kandev/hqa/<slot>` directory. It runs inside the
existing task guard; no guard change, image deployment, new session, database
write, or shared worktree registration is required. It supports the canonical
public `https://github.com/kdlbs/kandev.git` repository only.

The helper requires the exact task, HumanQA session, workspace, registered
repository UUID, original HEAD, existing failed-attempt branch, and verified
current upstream/main SHA. HumanQA must be the sole active executor. It checks
the live environment/binding/worktree incarnation and original Git backlink,
then compares original tracked/visible untracked files, original Git
administration, shared refs/storage inventory, task metadata, and writer fences
before and after creation. It does not traverse ignored runtime/build trees or
sibling worktree administration. Commands that mutate Git target only the new
clone; Git reads of the original disable optional locks and hooks.

The atomic `.kandev/hqa/.candidate-lease` reservation allows one candidate per
original checkout. The independent clone has its own objects, refs, index and
HEAD, with no alternates or shared administration. Its branch has the requested
name in its private Git namespace; the existing shared branch is preserved.
The lease and `.git/kandev-candidate.json` record task/session/repository identity,
binding incarnation, preservation hashes, helper hash, and a unique receipt.
Support returns the receipt UUID and SHA-256 of its canonical JSON. They must be
pinned in subsequent verification; task-owned marker files alone are not a
trusted ownership grant and do not confer any new broker authority.

Support can pipe the reviewed helper into Python through an existing guard:

```sh
# Run from the canonical deployment checkout; substitute only reviewed IDs.
docker exec -i -u kandev -w '<original-container-checkout>' kandev \
  /usr/local/bin/kandev-agent-guard -- /usr/bin/python3 -c \
  'import sys; source=sys.stdin.read(); exec(compile(source,"<stdin>","exec"), {"__name__":"__main__","__file__":"<stdin>","__candidate_source__":source.encode()})' \
  provision --task '<task-uuid>' --session '<existing-HQA-session-uuid>' \
  --workspace '<workspace-uuid>' --repo '<registered-repository-uuid>' \
  --original '<original-container-checkout>' --original-head '<original-full-SHA>' \
  --base '<verified-upstream-main-full-SHA>' --branch '<failed-attempt-branch>' \
  --slot '<authorized-slot>' < scripts/kandev-task-candidate.py
```

The owner uses the exact command and hashes returned by Support, from the
original checkout inside its existing guarded source turn:

```sh
python3 .kandev/hqa/<slot>/.git/kandev-candidate-control.py verify \
  --task '<task-uuid>' --session '<existing-HQA-session-uuid>' \
  --workspace '<workspace-uuid>' --repo '<registered-repository-uuid>' \
  --original '<original-container-checkout>' --original-head '<original-full-SHA>' \
  --base '<verified-upstream-main-full-SHA>' --branch '<failed-attempt-branch>' \
  --slot '<authorized-slot>' --receipt '<Support-receipt-uuid>' \
  --receipt-sha256 '<Support-receipt-SHA256>'
```

Verification is read-only. It requires a clean candidate at the pinned base,
independent writable candidate administration, a read-only shared registry,
unchanged original files/refs, unchanged other-writer fences, and the same HQA
process/binding incarnation. HQA may have transitioned from idle to running in
its existing source turn. It does not run product acceptance tests, change
workflow state, resume a session, or authorize ordinary task implementation.

A reservation, partial clone, moved upstream base, changed binding, or changed
preservation fingerprint stops the operation. Do not retry provisioning, remove
the lease, reset the original, or discard a partial candidate. Reconcile the
receipt and failed operation through reviewed Support first. Concurrent shared
repository activity can invalidate the conservative storage/ref fingerprint;
that is a review condition, not proof that the helper made those writes.

Run the isolated regression checks with `python3 tests/test-task-candidate.py`.
Live verification must use the affected task's guard; a Coordinator's mount
namespace is not evidence of another task's permissions.

## Session handoff boundary and reviewed control

Version 1 implements initial candidate provision/verification only. Its
reservation names one session, and verification requires that session to be
the sole active executor. It also pins the candidate HEAD to the initial base.
A later clean commit does not invalidate the Git repository, but the initial
receipt is not an authorization to transfer or accept that changed HEAD.
Do not substitute the old session ID, overwrite the receipt, reprovision the
slot, or relax the active-executor check to make a successor pass.

A conversational PAUSED acknowledgement is not lifecycle revocation. A
`WAITING_FOR_INPUT` session with executor status `ready` can still have a live
guarded provider with write access. For standalone execution, `local_pid`
identifies the shared agentctl controller, not the session-specific provider;
equal controller PIDs do not prove that either provider has stopped. A private
agent PID namespace also cannot prove absence of another session's processes.

A reviewed transfer needs all of these predicates before any new ownership
receipt is issued:

- The authorized existing lifecycle control has retired the exact old
  session/execution incarnation. Its executor is no longer active, and trusted
  process/lifecycle evidence confirms its provider tree and outstanding commands
  have exited or an enforced write revocation has taken effect. An ACK alone
  cannot satisfy this predicate.
- The exact authenticated successor is the sole active executor for the task
  and matches its workspace, repository, environment, binding and worktree
  incarnation. Caller authentication must come from the trusted launch/broker
  boundary; a session argument or a task-owned marker is not sufficient alone.
- The original reservation and candidate marker match their pinned canonical
  receipt digest. The original checkout, untracked operator data, original
  branch and failed-attempt branch remain preserved. The candidate is clean,
  retains its independent Git administration and branch, and has the explicitly
  authorized current HEAD descending from the pinned base.
- The transfer records a new append-only lineage entry containing the previous
  receipt/digest, old and successor session/execution identities, binding and
  process incarnations, unchanged base/branch, authorized current HEAD, helper
  digest and before/after preservation fingerprints. The original receipt
  remains immutable; no reset, cleanup or rollback is inferred.

Initial receipt fingerprints of all other sessions and shared Git activity
are conservative initial-admission checks. A transfer must explicitly reconcile
authorized lifecycle changes and reservation lineage; it must not silently
replace those fingerprints. A refreshed binding timestamp also requires
reconciliation even when the worktree UUID and path have remained the same.

If the old provider is still live, the reviewed Support request forbids runtime
mutation, or exact caller/revocation evidence is unavailable, transfer is
BLOCKED. Return the exact execution and missing predicate with preservation
evidence. The smallest next action is an independently authorized retirement
or enforced write revocation of that exact old execution through existing
lifecycle controls, followed by a reviewed transfer/acceptance request. Do not
stop the shared agentctl server, stop all sessions, mutate database rows, reset
CI budgets, replay a source turn, or infer Source admission from a capability
request. Root retains the final acceptance and Source-admission decision.

### Exact-old retirement

`scripts/kandev-support-exact-stop.py` is an operator-only reviewed recovery
control. Its default mode reads a JSON request on stdin and emits a content-free
preflight. The request pins coordinator/task/workspace/repository, exact old and
successor session/execution UUIDs, original checkout, provider/guard/controller
PIDs and kernel start times, protected successor PID/start time, exact old
instance endpoint, original reservation/digest, original HEAD, authorized
candidate HEAD/base/branch, and operator prompt hash.

It requires both selected sessions at idle checkpoints, exactly those two active
executors, matching registered repository/worktree bindings, all task FIFOs
empty, unchanged checkpoint/receipt hashes, valid guard ancestry and exact
process-group membership. Unknown descendants or runtime roles fail closed.
The reviewed requester must also attest that the old checkpoint contains no
unique runtime/Human artifact requiring preservation; a clean Git tree alone
does not prove that. The preflight exposes only identities and digests.

With explicit Root retirement authorization and automatic host review, pass
`--terminate <preflight-SHA256>` to the same control. It revalidates the entire
preflight, tries the exact old instance's supported `POST /api/v1/stop` endpoint
first, and uses no credentials or auth-row edits. HTTP 401 permits the explicitly
reviewed recovery path: open pidfds for the positively bound old provider tree,
revalidate again, send SIGTERM to the exact provider, wait eight seconds, and
only then TERM still-identical pinned members with another bounded grace.
It never sends a group-wide signal or SIGKILL. Changed predicates, new input,
unexpected API errors or surviving old processes stop recovery. Do not retry
signals against a changed checkpoint or reuse an already completed preflight.

Normal backend process-exit handling owns terminal lifecycle bookkeeping.
Support must then verify terminal old executor status, cleared process handle,
absence of the old provider, unchanged protected successor/CI/MAIN records,
unchanged FIFO/transcript/counters and source artifacts, and sole successor
eligibility. A TERM receipt alone is not a transfer grant. No raw process,
socket, sudo or credential capability is exposed to the Coordinator.

### Reservation-preserving transfer

`scripts/kandev-task-candidate-transfer.py` is a separate version 2 companion;
the original provision marker, lease receipt and helper remain immutable.
Reviewed Support pipes `prepare` through the existing exact-task guard with
the retirement receipt, its pinned outer preflight and the protected successor
process reference supplied by the trusted bootstrap. `--retirement-sha256`
pins that retirement receipt. Cross-guard environment access stays restricted:
the outer reviewed preflight attests launch identity, and readable kernel stat
fields pin the same physical successor inside the guard.

Preparation requires a terminal exact old execution with cleared process
handles, the exact sole eligible successor, unchanged worktree binding IDs,
unchanged original checkout/operator prompt, clean independent candidate at
the explicitly authorized current HEAD descending from its pinned base, and
the original reservation digest. A refreshed binding timestamp is explicitly
reconciled against unchanged immutable IDs and captured in the new receipt.
Before/after snapshots prove preservation during preparation.

It reserves `.candidate-lease/transfers` atomically and appends matching JSON
receipts there and in the candidate's `.git/`, plus the new task-owned transfer
helper. Original history, marker, receipt and helper are preserved. Existing
transfer data stops repeat preparation; failures remain for reviewed
reconciliation, with no deletion, overwrite or inferred rollback. This utility
supports one reviewed transfer per original reservation; further transfers
require a separately reviewed lineage extension.

Support uses `inspect` for neutral read-only verification. Only the actual
successor uses `verify`, with its own exported task/session/execution IDs and
ancestry through the exact protected provider PID/start-time reference.
Substituting environment IDs without that provider ancestry fails closed.
Missing process visibility never widens the guard. Support returns the new
receipt UUID, canonical JSON digest and exact caller command:

```sh
python3 .kandev/hqa/<slot>/.git/kandev-candidate-transfer.py verify \
  --task '<task-uuid>' --session '<actual-successor-session-uuid>' \
  --workspace '<workspace-uuid>' --repo '<registered-repository-uuid>' \
  --original '<original-container-checkout>' --original-head '<original-full-SHA>' \
  --head '<authorized-clean-candidate-full-SHA>' --base '<pinned-base-full-SHA>' \
  --branch '<reserved-private-branch>' --slot '<authorized-slot>' \
  --reservation-sha256 '<original-provision-receipt-SHA256>' \
  --receipt '<new-transfer-receipt-uuid>' --receipt-sha256 '<new-transfer-receipt-SHA256>'
```

`successor_guard_verified` is an inert capability acceptance result. Root still
owns Source admission; no Source turn, product tests, lane move, model change,
primary selection or CI budget reset follows automatically. A revived old
execution, new competing writer, changed helper/receipt, changed checkpoint,
stale binding or different successor process incarnation denies acceptance.

Regression checks are `python3 tests/test-support-exact-stop.py` and
`python3 tests/test-task-candidate.py`. They use synthetic Git/metadata/process
fixtures and fake pidfds; they do not signal live processes or run product tests.

### Offline per-entry preservation reconciliation

`scripts/kandev-candidate-preservation.py` analyzes retained JSON evidence only.
It does not traverse Git, read the database, install a helper, write a receipt,
or accept a caller. Pin the original transfer's canonical JSON digest outside
the evidence file:

```sh
python3 scripts/kandev-candidate-preservation.py \
  --transfer '<retained-transfer-body.json>' \
  --transfer-sha256 '<original-transfer-canonical-SHA256>' \
  --evidence '<reviewed-retained-evidence.json>'
```

The transfer body excludes response-only `status` and `receipt_sha256` fields.
Evidence schema 1 binds the task/workspace/repository, original/candidate
checkpoint, successor execution and reservation context through that transfer.
`recorded_observed` contains the two aggregate hashes from a retained diagnostic.
`before` and `after` are complete per-entry manifests, or explicit `null` when
unavailable. Partial `historical_entries` retain content hashes, presence,
provenance and reconstructed ref values, but always remain `aggregate_proven:
false`; they cannot substitute for complete manifest proof.

A manifest contains `schema`, `identity`, `entries` and `aggregates`.
`git_metadata_sha256` maps the exact original administration and shared
refs/config/HEAD/packed-refs/marker paths to their content hashes (or the legacy
null value for absent fixed files). `shared_inventory_sha256` maps every entry
in the legacy shared inventory, excluding all worktree administration, to its
exact `[size, mtime_ns, mode, inode]` tuple. The exact original administration
path must match the original marker hash; foreign administration is rejected.
Canonical JSON hashing must reproduce both original transfer aggregates and
both recorded diagnostic aggregates. A plausible before-state that does not
reproduce those hashes is rejected, even if its ref provenance is authorized.

Only then does the control enumerate every added, removed or changed entry.
Each delta needs an exact collection/path/before/after authorization with actor,
operation, external review receipt and evidence digest. A ref-byte approval
does not approve config changes, object writes, reflog changes or inode/mtime
changes. Unknowns stay blocking even when maps are complete. Exit 78 reports
missing evidence/authority. Exit 0, `offline_delta_proven`, proves only the
reviewed offline delta: it never grants Source access or issues a correction.
Any subsequent correction still needs the existing live guard's exact caller,
binding, retirement, process incarnation, FIFO and immutable artifact checks,
with a separately reviewed append-only receipt and helper lineage.

For future reviewed preparation, retain the exact `metadata` and
`shared_inventory` dictionaries in `original_snapshot` before discarding them
after hashing. Package them with `prospective_manifest(identity, entries)`,
and pin the manifest digest in the new append-only receipt. Retain matching
before/after manifests under Support control. Collection and hashing must use
the same maps, not separate traversals, and preserve a stable preparation
checkpoint. The existing installed helper and receipts are unchanged; this
prospective packaging function cannot retroactively recover an old manifest.
Deployment of that collection change requires its own reviewed lineage.

The evidence for request `2c4c14f1` is retained in
`support-evidence/candidate-932-2c4c14f1.json`. Reflog history supports candidate
before ref bytes `7bbe8e2a…\n` and recorded diagnostic after ref bytes
`cf07b842…\n`, matching the recorded ref content hash. It does not recover the
missing complete maps, historical config hash or historical inventory tuples.
Known ref changes remain informational rather than a blanket aggregate
approval. Scope grant/revocation audit events are not per-file config-write
audit events.

The additive `support-evidence/candidate-932-2c4c14f1-setup-audit.json`
records the bounded historical setup-log search during escalation. Its negative
result does not identify a writer or prove that no config write occurred, and
does not replace the original evidence/report or recover either manifest.

If those historical maps cannot be recovered, the smallest recovery alternative
is a separately reviewed **new preservation epoch**, not a successful correction
of the old receipt. The repository owner must review the intended shared config
and explicitly approve its exact state; Root must decide whether the remaining
unattributed historical interval is acceptable for this candidate. That decision
must name the missing evidence and exact bounded entries/scope; a general
"refresh hashes" approval is insufficient. Unknown historical config operations
can have materially changed repository behavior, so ref provenance alone cannot
make that decision.

An authorized epoch would retain every original receipt/helper and the failed
historical comparison; append a new contract/helper/manifest lineage; preserve
the exact original files/PROMPT/branch, candidate commit/history/base, reservation,
retired predecessor and live successor incarnation; and retain the FIFO,
counter, other-writer and shared-write restrictions. It would acknowledge the
unproven historical shared-metadata interval rather than claim it was proven
harmless. It needs no provider restart, second candidate, cleanup or shared Git
write. Root still owns actual successor acceptance and separate Source admission.
The current request does not authorize this decision, and this control contains
no epoch override or mechanism to ignore the existing comparisons.

`python3 tests/test-candidate-preservation.py` covers aggregate reconstruction,
partial history, exact authorization, unknown config, complete added/removed
entry reporting, missing inventory statistics, scope/incarnation mismatches and
nonmutating CLI behavior. Candidate regressions also cover a successor RUNNING
verification with usage progress, foreign writers, real original-file drift
and old execution revival.

### Concrete prospective checkpoint proposal (preparation only)

`scripts/kandev-candidate-checkpoint.py review` prepares version
`candidate-prospective-checkpoint/1` through the existing exact-task guard.
There is no adoption/install operation. It verifies the pinned original and
clean independent candidate, immutable reservation/retirement/transfer markers
and helpers, exact binding and successor execution/process reference, paused
successor, unchanged protected writer/accounting fence, and empty FIFO in a
read-only database snapshot. It does not rescan the shared inventory or attempt
historical reconstruction.

The bounded current review hashes shared config bytes and examines system,
user/XDG, original worktree and candidate config separately with
`git config --no-includes`. It never executes aliases, hooks, credential helpers
or filters, follows includes, or exposes configured credentials. Unknown
semantics are withheld and block adoption. Included authority remains unresolved
and blocking, rather than being assumed absent. Executable shared hook code is
hashed without executing or exposing it; unresolved semantics block adoption.
Private row commitments use HMAC with a per-review ephemeral key that is never
persisted or delivered. Source admission does not follow from the capability's
own safe Git overrides.

Request `380833bd` retained the complete sanitized proposal and byte-exact
contract in `support-evidence/candidate-932-380833bd-proposal.json` and
`support-evidence/candidate-932-380833bd-contract.txt`. Canonical proposal digest:
`e4fcdeef114bdfa321b629037c9767f4bb76c7a05e6c2d10aa112f97a952e352`.
Contract text digest:
`a22e2adb6e694da22232ce573c6f51838470a2286916b70047ce50b5838a25df`.
The packet is reviewable but has unresolved adoption blockers. No new baseline,
checkpoint receipt, helper installation, accepted caller command or Source
admission has occurred.

`approval_shape` is offline format validation only: it requires trusted reviewed
authentication supplied outside JSON, exact proposal/config/identity/lineage/
preflight/ref-policy bindings, an explicit historical-gap decision, named
repository and preservation review receipts, expiry and single-use nonce.
Hidden authority cannot be approved merely by a boolean. Actual approval
consumption, single-use enforcement, live adoption and owner acceptance require
a separately authorized implementation; this helper performs none of them.

The existing project-artifact delivery route is Coordinator-only and requires
operator registration installed through a reviewed image deployment. It is not
a general Support upload route. This preparation request authorizes neither
registration/deployment nor Support impersonating the Coordinator. Therefore
the proactive Support result supplies the full nonsecret contract text, hashes
and assessment rather than claiming broker delivery or creating a task inbox.

`python3 tests/test-candidate-checkpoint.py` checks credential/header/key
redaction, safe remote identities, non-followed includes, unexecuted hooks,
symlink denial, exact approval bindings, unresolved authority, historical-gap
acknowledgement, expiry and proposal-only behavior. The retained actual packet
also fails the approval gate while any authority blocker remains.

### Closed semantic review revision (review only, request 0588e44f)

`scripts/kandev-candidate-checkpoint-v2.py` is an additive review control. The
v1 packet, contract, installed candidate/transfer helpers and every receipt are
unchanged. The new control neither adopts a baseline nor verifies an accepted
caller. Its closed classifiers cover exact trust/maintenance registration
scopes, bounded GC integers, Git booleans, display/tag/GitHub-role enums,
credential-free remote identities and commit references resolved only in the
selected repository. Unknown paths, includes, executable configuration and
credentials stay held. A push URL token that looks like "disabled" still
selects a relative filesystem destination in Git; it is not classified as
disabled authority.

The retained current review and subsequent static-only trace are separate
artifacts. Static tracing hashes the two original wrappers, interpreter and
original hook config without executing hooks or importing their runtime.
The config permits bash/python3/node dispatch; six original script targets
were byte-pinned. Python package resolution, PATH fallback, child tools,
imports/sourced files and complete configuration semantics remain unproved.
Lexical YAML projection is explicitly not full parsing or executable proof.
Both hook closures therefore remain held. Two hidden unregistered path scopes
and two relative local push destinations also remain held: six blockers total.
The known system-wide ownership-trust setting is visible as a material existing
scope, not a new grant. Adoption cannot clear unknown authority by boolean.

Only the two named Source owners were evaluated through registered metadata
and source-administration device/inode comparison; their task worktrees were
not accessed. Owner 9349b6e5 shares the selected common Git; owner d28be44c
uses different administration and needs no mutable-ref exception. Neither
Source owner is paused by this proposal. Candidate932 gets no authority to
write either owner's ref. The finite rule requires full task/session/execution/
binding/ref identity, exact old/new commits with proved fast-forward ancestry,
authenticated Root/own-guard operation receipts and every inventory difference.
Only exact ref replacement, prefix-preserving reflog append and verified newly
reachable loose objects may be attributed. Pack changes, rewrites/deletion,
other writers, unrelated or omitted entries stay blocking. This format gate
never authenticates an event, accepts a checkpoint or grants writes itself.

`support-evidence/candidate-932-0588e44f-proposal.json` is the complete canonical
sanitized body, UTF-8 with no final newline. Its SHA-256 is
`13263a5a7b3ba34cefbce132ff288e73fa7a9be82d5f4baca406396c3e5b89db`.
The complete contract is its `contract` string and the byte-exact companion
`candidate-932-0588e44f-contract.txt`; contract SHA-256 is
`3d5da0e7af860b785d7f31d040271f161e4d74e2d2770d5f5aa14ed8f9ac6889`.
Current and static evidence are retained separately and linked by external
digests; compacting repeated config declarations does not discard blockers.
Historical aggregate differences remain unresolved and explicitly unproven.
Fresh adoption revalidation and separately authenticated review are mandatory.

The safe alternatives are exact repository-scope attestations and a complete
owner-reviewed executable/config/runtime closure, or separate review of an
inert capability-only Git subprocess contract that proves it excludes the
hidden authority. Such a contract would suppress global/system configuration,
hooks and credential helpers and limit administration to the exact independent
candidate. This proposal does not implement that alternative, alter shared
configuration, waive historical evidence or authorize Source. Root reviews
ordinary aspects and the material historical-boundary decision only after the
remaining authority is reviewable.

`python3 tests/test-candidate-checkpoint-v2.py` exercises enum/bound/reference
denials, credential redaction, scope classification, nonexecuting static code
review, finite owner/incarnation binding, different-common-Git denial, deletion/
rewrite/pack/unknown-object denial, full inventory completeness and canonical
packet provenance. Existing preservation, transfer and v1 approval regressions
remain mandatory and unchanged.

The v2 contract anchors only eligible same-common-Git refs. Excluded owner
bindings are revalidated without reading their unrelated refs or worktrees.
The initial preparation remains in commit `a6ae65c`; this clarification does
not replace any historical candidate receipt or v1 artifact.

### Candidate-only execution boundary (preparation only, request 3c33a9fb)

The complete canonical review packet is
`support-evidence/candidate-932-3c33a9fb-proposal.json` (UTF-8, no final newline),
SHA-256 `1d04c4f882fefff053a989848ddc0f3bd2d18785208cd44b00fd9d049b628b6b`.
Its complete contract is the `contract` string and companion
`candidate-932-3c33a9fb-contract.txt`, SHA-256
`a0119d496184f232bc6169611e53415d76a4aa2be1f9c7a4aa9d7673213cbe0f`.
The previous proposal and every original receipt/helper remain unchanged.

`scripts/kandev-candidate-boundary-review.py` is only an inert review model;
it performs no Git, launch, adoption, authentication or write operation. Its
closed local-config, environment, topology, caller and gate schemas allow
meaningful synthetic denial tests without creating a live broker. Even matching
model inputs never prove enforcement or enable a commit. No installed helper,
guard, config, checkpoint or task runtime is changed by this preparation.

One bounded static read of the exact candidate confirmed the retained local
config digest, absent hooks and absent worktree config/commondir/alternates.
No hook, package or Git command was invoked by that read. Candidate policy
guidance still references commitlint, pre-commit formatting/lint and i18n checks;
its mention of signing does not establish a Git-signature requirement. Unknown
or required-unsatisfied gates keep future commits held. Shared hook suppression
cannot quietly become a waiver of a required check. The proposed alternative
is owner-reviewed equivalent hermetic gate evidence, bound to exact tree,
parent, message, policy and toolchain. Signing needs an approved boundary if
required; no signing override is proposed.

The six unknown shared/global authorities are conditionally excluded from a
future candidate-only Git execution path by empty external config origins,
strict byte-pinned local config, pinned absent local hooks, fixed anonymous
upstream HTTPS transport and no push action. They remain unresolved in the
historical record. No safe-exclusion boolean can adopt the old preservation
gap or establish a physical boundary.

An optional CLI allowlist is insufficient: the current guard's broad writable
task root and common Git permit Source to bypass it. The smallest proposed
enforced write boundary combines a whole-provider candidate-only namespace
with read-only candidate Git administration and a separately isolated,
authenticated narrow Git mediator. It must protect original/shared resources,
mountpoints, descriptors and procfs/ptrace routes. The mediator alone may write
independent candidate administration after appropriate gate/lease checks.
Read-only inspection is the initial operation set; staging/commit remains held.

The entire successor/provider/tool process tree must be confined. Nesting a
shell below a still-writable provider is insufficient. A future lifecycle route
must prove the absence of wider writers and revalidate exact incarnation,
binding, FIFO and counters. If the existing incarnation cannot acquire this
boundary, adoption fails; replacement or incarnation transition needs separate
exact authorization and append-only migration evidence. This request permits
no such operation. Existing 882/9af and all other executors remain untouched.

The packet retains finite authenticated same-common-Git sibling progress and
full inventory classification; it excludes the separately administered d28
owner without freezing its work. Root still must review the actual design,
repository gate equivalence and the material unproven historical interval,
then separately authorize implementation, physical enforcement tests, adoption
and actual own-caller acceptance. Source admission remains a separate decision.

`python3 tests/test-candidate-boundary-review.py` covers executable/unknown config,
include/alias/filter/helper/SSH/push/hook injection, environment/PATH/loader
authority, missing whole-provider enforcement, symlink/foreign administration,
wrong caller/incarnation, forbidden operations, required gate/signing waiver,
stale gate evidence, complete inventory and finite sibling progress. Existing
candidate, preservation and proposal regressions remain unchanged.
