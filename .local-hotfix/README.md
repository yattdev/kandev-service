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
`489c9c57-b9ca-4766-b7fa-c4a71dc6b7b4` was built from source commit
`df1916c062b530553d2235896c82010ba6373499`. That commit is a tested superset
of PR #3473 (`a91e0e66f87456b0c380ad749ddf9734ddf8f37a`) and the still-required live
queue, wake-coalescing, terminal-queue recovery, guarded-inference, liveness,
active-worktree attachment, and attachment-response hotfixes. It adds the
guarded exact-profile assignment capability without replacing those fixes,
then exposes that single capability to the backend-verified canonical Kanban
Coordinator while ordinary task catalogs remain unchanged. It also projects a
strict exact-model startup denial through `list_task_sessions_kandev` as a
bounded typed `startup_failure`, while leaving arbitrary raw provider errors
private.

The corresponding binary SHA-256 values are:

- `agentctl`: `3bae175f5980f3d4c3fba84a587017725d39955f3954184a84e62d82ab45d5b4`
- `agentctl-linux-amd64`: `d7ab09a6890d5d7ce112bc7a5804ff26ba90822f7218058736cac5622d8f05e4`
- `kandev`: `f34b31bfce78f80632bb25674a2a2778d9a99621ae0152d0d3366c82b083b51d`

The immediately preceding overlay is retained at
`/tmp/kandev-gpt54-start-before` with directory mode `0700` and file modes
`0600`; its three hashes are recorded in the Support receipt. It is
the binary rollback source in addition to `kandev-safe-deploy`'s image rollback.

The backend was built only after `build-web` and `sync-embedded-web`, so it
contains the complete JavaScript frontend. Do not build the overlay with the
backend-only `build-kandev` target from a clean source tree: that embeds the
fallback HTML without JavaScript assets and produces a white page.

`scripts/build-kandev-liveness-hotfix` remains the reproducer for the older
single liveness patch; it is not the reproducer for this superset overlay.

Remove an overlay after its corresponding fix is verified in the upstream base
image; otherwise the local overlay deliberately continues to win.
