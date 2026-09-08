# Local binary hotfix overlay

This directory is intentionally present in the Docker build context. Locally
built `agentctl`, `agentctl-linux-amd64`, and backend `kandev` binaries may be
placed here while a tested Kandev source fix is waiting for an upstream image
release. The binaries are ignored by Git, but `Dockerfile.local` installs them
into every local image rebuild when they are present. Never place only one of
the two `agentctl` binaries here; the backend overlay is independent.

The overlay deployed for Support requests
`a335c345-f10a-4ae2-a598-7197e94da5d5` and
`25ab4998-3933-48f4-bc2e-374355b35f9e`, and
`489c9c57-b9ca-4766-b7fa-c4a71dc6b7b4` and
`2064d88b-24c1-4ba2-abf1-b41095a56ffa`, with the backend extended for
`27d32008-a595-4e0a-8c9e-ef04ba97b119`, was built from source commit
`b401a094d5fc0f81613eb8470c2544ce87e16f74`. That commit is a tested superset
of PR #3473 (`a91e0e66f87456b0c380ad749ddf9734ddf8f37a`) and the still-required live
queue, wake-coalescing, terminal-queue recovery, guarded-inference, liveness,
active-worktree attachment, and attachment-response hotfixes. It adds the
guarded exact-profile assignment capability without replacing those fixes,
then exposes that single capability to the backend-verified canonical Kanban
Coordinator while ordinary task catalogs remain unchanged. It also projects a
strict exact-model startup denial through `list_task_sessions_kandev` as a
bounded typed `startup_failure`, while leaving arbitrary raw provider errors
private. The projection recognizes the exact lifecycle wrapper persisted on a
failed session as well as the unwrapped strict-model error. The backend also
includes PR #3473's current ACP rebind rollback correction and prevents a
lane-scoped exact profile from leaking into an unconfigured successor lane:
the successor now stops before an agent prompt and emits a bounded profile
selection warning.

The corresponding binary SHA-256 values are:

- `agentctl`: `6e3563891cd742f2e959e44243d4226b4185810cec34c630a294dac138c18a4f`
- `agentctl-linux-amd64`: `66ccf5731bf0f42ad0cf0812f50666cb6c70b6d73bce2d1c6c261a66996272fb`
- `kandev`: `7304609866abe143480fdaa9e26feccdfae699e6795eaaf1bd4b55d508066427`

The immediately preceding overlay is retained at
`/tmp/kandev-review-qa-before-27d32008` with directory mode `0700` and file mode
`0600`; its backend hash is recorded in the Support receipt. The unchanged
agentctl pair remains covered by the preceding `/tmp/kandev-gpt54-wire-before`
backup. These are binary rollback sources in addition to
`kandev-safe-deploy`'s image rollback.

The backend embeds the complete generated JavaScript frontend retained from
the preceding overlay build; the generated asset tree was copied unchanged
into the isolated source worktree before relinking. Do not build the overlay
with the backend-only `build-kandev` target from a clean source tree: that
embeds the fallback HTML without JavaScript assets and produces a white page.

`scripts/build-kandev-liveness-hotfix` remains the reproducer for the older
single liveness patch; it is not the reproducer for this superset overlay.

Remove an overlay after its corresponding fix is verified in the upstream base
image; otherwise the local overlay deliberately continues to win.
