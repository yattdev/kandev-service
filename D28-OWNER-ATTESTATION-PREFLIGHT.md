# D28 retained owner-attestation preflight review

Contract `D28-OWNER-ATTESTATION-PREFLIGHT-v1`, request
`8347ed58-d488-446f-bb17-dc8b48d6e98f`. This review prepares a closed read
contract and tests its decision model. It does not install a capability,
create evidence, contact any owner, certify current resources, or permit
physical operations. Original b4/15388 artifacts remain immutable.

## Smallest existing-owner seam

The trusted backend execution stream derives the existing caller's task,
workspace, session and current queue incarnation. Existing833 is the only own
D28 caller contemplated here; Root13d8 reviews its authentic receipt and cannot
substitute that caller. The backend validates actual registered repository,
environment and worktree identity through existing repositories. The supplied
repository UUID is an expected pin, not new proof of physical registration.

Use existing lifecycle.Manager association/recovery bookkeeping and existing
instance/process/launcher owner read locks. Resolve only retained immutable
owner evidence already authenticated through those owners. Take a consistent
read revision, then recheck caller incarnation, owner epoch and scope generations
before returning. Never call a runtime API, enumerate instances/processes,
refresh/adopt/reconnect an owner, acquire credentials, install new containment,
or mutate an admission gate to make the read work. A hash proves bytes, not an
issuer's authority. No generic receipt-import/authentication endpoint is proposed.

The static review identifies why that seam cannot currently supply complete
D28 evidence:

- ControlServerRecord retains installation endpoint/server identity/capabilities
  and a private credential reference; it is not a task closure/partition ledger.
  The previous audit already found its row absent. No new ledger read occurred.
- instance.Manager owns indexed instances, task/session association and their
  process managers. Its retained last-turn slot and index do not certify all
  detached descendants or task-scoped admission/escape coverage.
- The Linux process lifecycle handle is empty and ownsProcessLifecycle returns
  false. Setpgid and a direct-child Pdeathsig do not establish an inescapable
  task domain or a durable scope generation. processGroupAlive/probes can scan
  global /proc; they are not permitted preflight reads and were not invoked.
- The launcher owns a shared in-memory managed-child list and process groups,
  without a durable task-scoped complete coverage/protected partition record.
  Actual external supervisor evidence remains UNKNOWN; none was queried.

The existing stop APIs are ineligible and unused. Exposing these partial records
as an attestation would still leave complete ownership UNKNOWN. Installing a
read projection cannot recover evidence that was never retained.

## Proposed closed read schema

Reserved tool `prepare_own_task_owner_attestation_kandev` is NOT callable.
Only three string inputs are proposed: exact reviewed `contract_sha256`, accepted
own `preservation_receipt_id`, and `preservation_sha256`. The SHA values are
64 lowercase hex characters. Reject every additional field, including
complete=true, PID/path/scope/target lists, owner proof bodies, task/session
substitution, credentials and physical mode. Resolve the immutable contract by
server-owned review registration; do not accept a caller-generated contract.

The current preservation handoff7129a4b4 with intent
`D28-B4C9-PRESERVATION-ATTESTATION-v1` is pending. It supplies neither an accepted
preservation receipt/hash nor physical coverage. No placeholder command using
that pending identity is offered.

A successful authenticated read returns version `owner-attestation-preflight/v1`
and DENIED, HELD or REVIEWABLE. It includes server-derived caller/task/workspace/
repository evidence; owner reference/epoch; immutable attestation reference/digest;
evidence route; actual opaque scope ID/generation; expiry/read revision;
preservation and protected-partition digests; exact nonsecret missing fields or
protected overlap classifications. Unknown fields stay explicit null/UNKNOWN.
Every status has physical_action_available=false and source_admission=false.
REVIEWABLE means evidence can be considered for a later finite physical proposal;
it never means fenced, sole writer, approved operation or Source admission.

## Proof required before REVIEWABLE

Both routes require authenticated current ownership, registered physical binding,
all exact historical execution coverage, complete descendant/escape/admission
proofs, unexpired consistent epoch/revision, and a complete protected partition.
Preservation must cover the frozen head/fork/eleven commits, tracked/untracked/
ignored and volatile unique state, privatePG/data/DSNs, F3/gates/archives, FIFO
order/content and counters, without disclosing those private contents.

The original route additionally needs original launch/runtime/session incarnation
and complete closure receipts for execution98fbeabc and executionadea40f6. UUID
associations, failed state, empty rows/PIDs, or synthetic test identities cannot
replace those records.

The prospective route additionally needs an actual PRE-EXISTING owner-issued
domain ID/generation, a retained launch/domain binding predating the old launches,
complete write-capability membership including unindexed descendants, and owner-
enforced escape/admission coverage. A new scope around visible processes is
ineligible. Lost historical incarnations remain UNKNOWN on this route.

Any current833, privatePG, helper, shared, foreign, or unique-state resource in
that domain makes it HELD. Partial or unknown partitions are HELD too. No actual
D28 overlap is asserted here; physical membership is unbound. Original protected
Human questions, candidate932, Root, and all other tasks/resources remain excluded.

## Acceptance and next owner decision

After separately reviewed read-capability installation and a genuine accepted
preservation receipt, existing833 may perform one ordinary authenticated read
with the exact contract digest and preservation identity/hash. Root validates
that actual same-caller result. If any evidence is absent, require HELD plus
exact missing fields; unavailable authentication or caller/schema mismatch denies.
Neither Root nor Support can produce a substitute caller receipt. No current
accepted/read command is issued while installation and bindings are unavailable.

The smallest owner operation is to provide ONLY already-retained, task-bound
launch/domain/closure proof references and a protected partition through existing
backend provenance. The specific unavailable seam is a retained authenticated
supervisor containment/coverage record with an actual scope ID, generation and
complete descendant/escape/admission certificate. If no such original/pre-existing
record exists, the retained-only contract cannot establish physical exclusivity.
A separate decision must identify a changed physical evidence/preservation boundary
before any new physical inspection or operation; do not ask Human to approve
unknown handles, generic engineering work or a shared shutdown.

## Verification and lineage

Fourteen offline specification tests pass, covering forged completeness, PID/path
input, wrong caller/workspace/repository, stale generation/epoch/incarnation/expiry,
partial descendants/escape/admission coverage, missing/unverified original proof,
new scope, protected overlap/partial partition, receipt tampering and preservation
drift. Positive fixtures are synthetic authenticated-owner assumptions, not live
or cryptographic authentication tests. They return review-only, with no physical
operation or Source grant. The test model has no I/O or lifecycle controls.

Canonical review packet is support-evidence/d28-owner-preflight-8347ed58-contract.json,
9904 UTF8 bytes, SHA256
46eac56e3636b2e76aa7731835adad87224c17f78a2ff8e49d01f9291647a784.
Audit receipt is support-evidence/d28-owner-preflight-8347ed58-review.json, SHA256
7b67b0a2160e48f6c3bd766f32ff58d5b49389a1c5e420935a22dcc7ddaf9e4b.
It pins all static manager files and original b4/15388 hashes. Both checkouts were
inspected; unrelated source edits were preserved. No target files, live records,
runtime, credentials, provider, queue, counters, question or deployment changed.
