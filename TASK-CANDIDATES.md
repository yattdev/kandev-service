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
