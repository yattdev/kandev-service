# Local binary hotfix overlay

This directory is intentionally present in the Docker build context. Locally
built `agentctl`, `agentctl-linux-amd64`, and backend `kandev` binaries may be
placed here while a tested Kandev source fix is waiting for an upstream image
release. The binaries are ignored by Git, but `Dockerfile.local` installs them
into every local image rebuild when they are present. Never place only one of
the two `agentctl` binaries here; the backend overlay is independent.

The overlay deployed for Support requests
`a335c345-f10a-4ae2-a598-7197e94da5d5` and
`25ab4998-3933-48f4-bc2e-374355b35f9e` was built from source commit
`cf35864d884661372cc660a24ab255438d6434bd`. That commit is a tested superset
of PR #3473 (`a91e0e66f87456b0c380ad749ddf9734ddf8f37a`) and the still-required live
queue, wake-coalescing, terminal-queue recovery, guarded-inference, liveness,
active-worktree attachment, and attachment-response hotfixes. It adds the
guarded exact-profile assignment capability without replacing those fixes,
then exposes that single capability to the backend-verified canonical Kanban
Coordinator while ordinary task catalogs remain unchanged.

The corresponding binary SHA-256 values are:

- `agentctl`: `91affd565fcfb08ef2b9257f09e3e210761472dfa16bf8f8883da2652cb67839`
- `agentctl-linux-amd64`: `8255052ef13e0f7deb636af514d119d7bf095cea68c4e06f90c2db99af56b013`
- `kandev`: `63fbb8555f4a1608bc895e1705ef94ab2bd533bc338676f1546be64d226a0d4a`

The immediately preceding overlay is retained at
`/tmp/kandev-exact-profile-exposure-before` with directory mode `0700` and
file modes `0600`; its three hashes are recorded in the Support receipt. It is
the binary rollback source in addition to `kandev-safe-deploy`'s image rollback.

The backend was built only after `build-web` and `sync-embedded-web`, so it
contains the complete JavaScript frontend. Do not build the overlay with the
backend-only `build-kandev` target from a clean source tree: that embeds the
fallback HTML without JavaScript assets and produces a white page.

`scripts/build-kandev-liveness-hotfix` remains the reproducer for the older
single liveness patch; it is not the reproducer for this superset overlay.

Remove an overlay after its corresponding fix is verified in the upstream base
image; otherwise the local overlay deliberately continues to win.
