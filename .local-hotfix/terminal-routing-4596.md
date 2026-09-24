# Silent retained terminal routing (Support 4596cc9d)

Support request `924f3f41` first deployed task-scoped `terminal_retention`.
The directly authorized Coordinator set that hold on Redmine task
`b7cb6fe6-3766-4b81-a7ee-f5e9c16627cf`, then moved it to Done with
`entry_options.skip_step_prompt=true`. The task service completed the card,
but the orchestrator still applied Done's `new` agent-profile policy. That
created an idle session and projected the task back to REVIEW. The Coordinator
returned the card to Blocked; both moves and their sessions remain in history.

The prior active image was
`sha256:c967ef9bf9bb018059882ad345d2d6b37843e5cd68fd0d5b32a79431773966b7`.
Its backend and agentctl pair were built from verified canonical v0.95.1
(`7b2a4c07123b406ad5bff086128c8092e018553d`) plus retention backport
`db8a88b63f56eee13d9d2d36aa4eea74a53cc620`; see
`terminal-retention-924f.md`. This repair is the direct child
`71eb54d2443eb9214a0713be54c325db76b34012` of that backport. It only
changes the backend. Both agentctl binaries remain byte identical, so the
replacement is a tested superset of every source fix in the active pair.
The equivalent capability is also committed on freshly fetched canonical
`upstream/main` `25271b6e7fc04344e3e8e851bc73257dd783e538` as
`236905dbe` (retention) and `9ebe543203136eb5a29e2dd8204f7075e02cef8f`
(routing) in the isolated Support source worktree.

For a completed task with `terminal_retention=true` entering a terminal step
whose one-shot overlay has no prompt or on-entry actions, the orchestrator
finishes source-step exit and skips destination session preparation. This
preserves the existing session and completed task state. A regression test
uses a Done step with a prompt, auto-start action and `new` profile policy;
it verifies no added session and no REVIEW projection. The full release
orchestrator package passed against the exact deployed source commit after
the final narrowing to zero residual on-entry actions. Focused canonical
main orchestrator and task-service retention tests also passed. The backend
was rebuilt with the complete existing generated web bundle; no frontend
assets changed.

The predecessor backend is retained at
`/tmp/kandev-support-4596-previous-kandev` with SHA-256
`bb4066beac58eacff3681307006baf998c5e70976669978d2408bfbc5189d60f`.
The deployed overlay hashes are:

- `kandev`: `4d889dcf7dae33ae2b7db509bf0a4b32c2dc792fc9a5b2af3541636af9461153`
- `agentctl`: `91077dc0efbe7abdf71e0921b07ed659393bd04671cd4f65be8268863dc1f575`
- `agentctl-linux-amd64`: `7de887bd0e7709d1e9657eff86b7eb74acd45b02cecaa84b3ed427ecc3af4052`

`scripts/kandev-safe-deploy --build` accepted image
`sha256:4ba6f4b8812135f595f7311ad34e8ce85882c31297d9befc9acced2ee0d61749`
at 2026-09-24 07:27:16 UTC after guarded-runtime preflight and HTTP 200.
Post-deploy readback found the exact live binary hashes above, AppArmor
`kandev-codex`, and HTTP 200.

The Redmine card remains Blocked/REVIEW, unarchived, with retention true.
It has 17 historical sessions and none RUNNING, zero active executors, zero
open turns and zero pending cleanup jobs. Environment
`8df583e4-a49f-49db-bc9d-16f8b4ce9327` is ready; worktree
`98b83314-8919-493e-a8b4-c0ec9b55ae2e` remains active at
`/data/tasks/register-redmine-plu_03jpa2en/kdlbs-kandev`, clean at merged
PR #3684 head `c5837cb5f64a34445ab5814f62b65a3b575b7755`. Support did
not move the card or start a task session.

The direct parent Coordinator can retry one authenticated
`move_task_kandev` to Done step `30ae45bd-e99e-455a-8eb7-10e7a038200f`
with `entry_options={"skip_step_prompt":true}` and no instructions. It must
read back Done/COMPLETED, `terminal_retention=true`, no archive timestamp,
no added session or turn, and the same environment and worktree IDs before
accepting terminal disposition. If any predicate fails, keep the card visible
in Blocked with Need-help and return the exact move and readback receipt.
