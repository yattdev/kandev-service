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

## Session handoff boundary

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
