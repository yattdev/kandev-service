# Board-loader exact startup recovery: escalation audit

Request `811127b4-88c1-4758-ba6f-f175ee0e6153` remains BLOCKED for live continuation.
The [original failure evidence and exact admission tuples](https://github.com/yattdev/kandev-service/blob/69950a7e7da8244ffbf50c6ac4030dccd71ccabb/BOARD-LOADER-811127B4.md)
are preserved. No safe recovery or actual new agent instruction-read is claimed.

## Authority audit and narrower blocker

The prior conclusion was too broad in saying all task-bound worktree repair was
excluded. A safe supported exact-session recovery is within the requested goal;
foreign-worktree restrictions do not by themselves prohibit reviewed Support
host diagnostics. This pass treats preservation-safe task-bound recovery as a
possible route and evaluates the actual installed guards rather than requesting
the same generic permission again.

Both named checkouts were inspected. Deployment remains on main; the named
source checkout remains at `cfd6bdf65ae6f631d7701c105791a099c0325cc3` with its
unrelated edits intact. It predates the installed recovery-admission code. The
clean restored deployed lineage at `80fdc4ce072ced98c6d72996f02e2c578d64dd82`
was used to review the installed paths and run isolated tests. No new source
worktree, source implementation, image or deployment was created.

Reviewed host access succeeded for the exact pointer/mount checks and isolated
mock-socket tests. There is no unrequested host escalation or approval rejection
blocking this result. No raw host/socket authority was given to a task agent.

## Missing metadata is real, not a mount alias

Only the two exact failing registered `.git` pointers and their recovery-record
paths were checked. Their targets are under the container's registered
`/data/home/Code/kandev-source/.git/worktrees` directory. The live mount maps
`/home/ayattara/Code` to `/data/home/Code`.

| Registered worktree | Exact admin leaf | Container target | Mapped host target | Recovery record / lock |
| --- | --- | --- | --- | --- |
| `e8821e3b-c3b0-45a5-8923-c2157eaf6a77` | `kandev-source39` | missing in original check | missing | absent / absent |
| `046e49a9-fa4f-433d-a263-a84ca28aa2aa` | `kandev-source-feature-add-guarded-queue-cl-sls` | missing in original check | missing | absent / absent |

Thus a host/container path translation correction cannot restore these targets.
There is no exact existing `.kandev-recovery.json` operation to adopt at either
registered checkout. This is not a global backup search or a claim that no
matching backup can exist elsewhere. No Git objects, task source, index,
credential store, sibling checkout or unrelated recovery record was read.

The production worktree store uses the environment's `task_environment_repos`
rows as physical worktree ownership. Sessions resolve through their environment;
there is no independent session-to-worktree table that can be silently repaired
while retaining a different authoritative physical binding. The original
selected slots therefore remain the relevant recovery boundary.

## Existing recovery alternatives

- **Ordinary resume / recovery action `resume`:** retains saved resume identity,
  but still requires valid selected Git checkout/recovery admission. For a
  terminal FAILED session, executor resume can invoke
  `CleanupStaleExecutionBySessionID` before the worktree recovery check. That
  helper can stop a runtime instance and remove its in-memory execution. The
  concurrent-resume guard does re-read current state; this audit does not claim
  it blindly kills a successor. Nevertheless, resume is not a content-free
  diagnostic or a preservation-neutral retry of these retained entries.
- **Workspace restore:** may reuse a retained same-session execution, reuse an
  execution belonging to another session in the environment, or create a new
  lightweight agentctl runtime. A successful restore does not establish the
  exact selected owner or consume the original FIFO receipt. Cold repo-backed
  creation validates Git identity; cached/shared reuse is not a repair of the
  missing Git administration metadata. It was not invoked.
- **Automatic worktree recovery:** snapshots the original, rematerializes a
  sibling checkout on a new recovery branch and atomically publishes a new
  worktree identity/path. It preserves original files, but is a real resource /
  Git-binding change, not an in-place no-op. It first needs the durable recovery
  claim that currently refuses these environments.
- **Recovery claim:** the installed consumer query counts every attached
  executor row, including the requesting session's stopped row, plus other
  nonterminal sessions. The original evidence contains both kinds of consumers
  for each environment. Merely proving physical quiescence does not make that
  compiled predicate pass. Deleting resumable rows, changing waiting sessions
  to terminal, clearing a lease or removing the guard is not an eligible fix.
- **Fresh start, new branch, repo-free start, alternate primary, new owner or
  direct prompt:** changes preserved identity/context/resources or bypasses the
  original receipt. None is a safe same-owner continuation for this request.

The original missing-admin admission failure and subsequent `queue dispatch
claim changed` failure-release error remain distinct. Existing expired-lease
takeover is useful only after safe exact-session execution admission. No queue
row, flag, transcript message, turn, counter or incarnation was changed here.
The prior queue/session snapshot is retained; this pass did not poll live sender
status or assert new current process liveness from old stopped records.

## Additional acceptance evidence

Six existing isolated regressions passed with Go 1.26.0, `-race`, `-count=1`:

- `TestManager_RecoverWorktreeSnapshotsAndRematerializesCheckout`.
- `TestEnsureWorkspaceExecutionForSession_ReusesExistingTaskEnvironmentExecution`.
- `TestWorkspaceRestoreReusesRetainedTerminalRuntime`.
- `TestWorkspaceRestoreRejectsActiveCleanupWithoutMutation`.
- `TestManager_CleanupStaleExecution_StopsRuntimeInstance`.
- `TestResumeSession_ConcurrentResumeReReadsFreshState`.

They verify the real behavior behind the alternatives above: sibling recovery,
shared-environment reuse, retained-runtime reuse, cleanup refusal, runtime-stop
side effects and concurrent-resume state revalidation. Mock runtime calls and
synthetic temporary Git repositories do not operate on the supplied tasks or
invoke a real agent/provider. All yielded test runs completed successfully.
The seven original guard/lease regressions remain valid and were not repeated.
No application code changed; no live start acceptance is claimed.

## Concrete remaining owner and smallest action

The Kandev platform/storage operator owns the missing prerequisite. Two bounded
routes are available for a subsequent concrete decision:

1. Supply a trusted, exact matching recovery source for the **two original Git
   administration directories**, with original HEAD/index/backlink/history
   provenance and a preservation receipt. A reviewed restoration of those exact
   metadata directories may allow normal checkout validation without invoking
   automatic rematerialization. Original same-session writer admission, Human /
   pending-input / WIP fences and the retained FIFO still must be established;
   restoring files alone does not authorize dispatch. No matching recovery source
   has been supplied or discovered in the permitted exact paths.
2. If exact metadata restoration is unavailable, authorize the narrowly scoped
   **backend recovery implementation and activation** needed to admit these two
   environments while preserving historical rows and nonterminal session state.
   It must bind caller/workspace, both original task/session/incarnation tuples,
   exact environment owner/generation, original queue/turn/head and unchanged
   lane; prove quiescence and enforce sole-writer exclusion before recovery;
   preserve original files/Git evidence; deny ambiguous or attempted/accepted
   delivery; and use normal expired-lease takeover for the same original entry.
   The retained-versus-ordinary failure-release correction needs its own exact
   reservation regression. Source implementation and deployment remain expressly
   excluded by this request. No broad rights/provider grant is required.

The second route cannot be achieved by a host-policy toggle or general restore
API. Any proposed activation must preserve the deployed hotfix superset, have a
concrete rollback plan and obtain the separately required deployment authority;
Kandev recreation, if approved later, must use `scripts/kandev-safe-deploy` with
its readiness/rollback gate. No such activation is performed here.

**Do not resend either original packet, retry terminal resume as a probe or send
the v2 correction yet.** Root acceptance remains actual new instruction-reading
agent output in `5e0de349-8eaf-404f-9ae9-e5d102f70686` and
`2376d3fe-6818-4486-a1fb-7dc99c3bf433`, correlated to the original open turns and
packets, with lane `89985050-d740-4421-bbbe-4aa018d8c7ab` and all source/runtime/
provider holds unchanged. Root then supplies `BOARD-LOADER-FIT-20261014-v2`.

No task, source, worktree, plan, historical session, original queue/turn, runtime,
provider, credential, lane or production artifact was mutated. Only this audit
and its content-free receipt were committed and pushed; no Human relay is needed.
