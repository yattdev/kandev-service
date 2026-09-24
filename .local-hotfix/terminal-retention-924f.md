# Task-scoped terminal retention overlay (Support 924f3f41)

The active image before this overlay was stock Kandev v0.95.1
(`sha256:ea1c3b22d17424f9d98ae4b37746a6a1d59a1ee5fc8f1e373234b01305026a81`).
The retired v0.95.1 hotfix binaries remained outside the build context; no
binary overlay was active. This replacement is therefore based on the same
verified canonical release tag `v0.95.1` (`7b2a4c07123b406ad5bff086128c8092e018553d`)
plus exactly the task-scoped terminal-retention backport
`db8a88b63f56eee13d9d2d36aa4eea74a53cc620`. Its canonical upstream/main
source commit is `d278af53d6420098cf8e17cb1c9126c70e724aec`.

The backend refuses direct and cascade archive of a held task before cleanup,
and the auto-archive loop skips it. `update_task_kandev` accepts the explicit
`terminal_retention` boolean only for a verified direct parent task in the same
workspace. Generic metadata writes cannot set or clear it. A task-specific
hold should be set and read back before a Done move; the move must use
`entry_options.skip_step_prompt=true`. Clearing the hold later re-enables
normal archive behavior and needs a separate preservation decision.

The backend and both Linux agentctl binaries were built from the same
backport. The frontend was rebuilt and embedded from the same v0.95.1 source;
no backend-only fallback HTML is present. Focused backend, handler, and tool
schema tests passed. The broad package run in the canonical main worktree
hit unrelated sandbox-only directory and socket failures.

- `.local-hotfix/kandev`: `bb4066beac58eacff3681307006baf998c5e70976669978d2408bfbc5189d60f`
- `.local-hotfix/agentctl`: `91077dc0efbe7abdf71e0921b07ed659393bd04671cd4f65be8268863dc1f575`
- `.local-hotfix/agentctl-linux-amd64`: `7de887bd0e7709d1e9657eff86b7eb74acd45b02cecaa84b3ed427ecc3af4052`

`scripts/kandev-safe-deploy --build` accepted image
`sha256:c967ef9bf9bb018059882ad345d2d6b37843e5cd68fd0d5b32a79431773966b7`
on 2026-09-24 at 06:52:13 UTC after guarded-runtime preflight and HTTP 200.
The exact prior image remains tagged `kandev-local:safe-deploy-previous`.
Live binary hashes match the three values above; AppArmor remains
`kandev-codex` with its seccomp policy.

Task `b7cb6fe6-3766-4b81-a7ee-f5e9c16627cf` still needs a separate
direct-parent Coordinator call to set the hold, followed by an optioned Done
move. Until the hold reads back true, the card remains in Blocked and this
deployment is not a task-specific terminal acceptance receipt.
