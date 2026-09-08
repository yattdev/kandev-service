# Local binary hotfix overlay

This directory is intentionally present in the Docker build context. Locally
built `agentctl`, `agentctl-linux-amd64`, and backend `kandev` binaries may be
placed here while a tested Kandev source fix is waiting for an upstream image
release. The binaries are ignored by Git, but `Dockerfile.local` installs them
into every local image rebuild when they are present. Never place only one of
the two `agentctl` binaries here; the backend overlay is independent.

The overlay deployed for Support request
`a335c345-f10a-4ae2-a598-7197e94da5d5` was built from source commit
`29fbaca7dd5035d7ed1ed4a01edb731097fceb34`. That commit is a tested superset
of PR #3473 (`a91e0e66f87456b0c380ad749ddf9734ddf8f37a`) and the still-required live
queue, wake-coalescing, terminal-queue recovery, guarded-inference, liveness,
active-worktree attachment, and attachment-response hotfixes. It adds the
guarded exact-profile assignment capability without replacing those fixes.

The corresponding binary SHA-256 values are:

- `agentctl`: `57a64686b57941531a674608a604e002640d0d0f0cb34fb854fc0ee395b52fba`
- `agentctl-linux-amd64`: `737f92ee123a832321b37be15cb98567bb75ca6ff9593d36f98d8686ad559592`
- `kandev`: `6e47a7ca5e6ee054bc9d5a59702a4c0f0adb07c55ca730885e34d1c380cf4049`

The backend was built only after `build-web` and `sync-embedded-web`, so it
contains the complete JavaScript frontend. Do not build the overlay with the
backend-only `build-kandev` target from a clean source tree: that embeds the
fallback HTML without JavaScript assets and produces a white page.

`scripts/build-kandev-liveness-hotfix` remains the reproducer for the older
single liveness patch; it is not the reproducer for this superset overlay.

Remove an overlay after its corresponding fix is verified in the upstream base
image; otherwise the local overlay deliberately continues to win.
