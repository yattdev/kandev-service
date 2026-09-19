# Local binary hotfix overlay

This directory is intentionally present in the Docker build context. Locally
built `agentctl`, `agentctl-linux-amd64`, and backend `kandev` binaries may be
placed here while a tested Kandev source fix is waiting for an upstream image
release. The binaries are ignored by Git, but `Dockerfile.local` installs them
into every local image rebuild when they are present. Never place only one of
the two `agentctl` binaries here; the backend overlay is independent.

The agentctl overlay was deployed for Support requests
`a335c345-f10a-4ae2-a598-7197e94da5d5` and
`25ab4998-3933-48f4-bc2e-374355b35f9e`, and
`489c9c57-b9ca-4766-b7fa-c4a71dc6b7b4` and
`2064d88b-24c1-4ba2-abf1-b41095a56ffa`.

The backend previously staged for
`27d32008-a595-4e0a-8c9e-ef04ba97b119` was built from source commit
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

The original paired binary SHA-256 values were:

- `agentctl`: `6e3563891cd742f2e959e44243d4226b4185810cec34c630a294dac138c18a4f`
- `agentctl-linux-amd64`: `66ccf5731bf0f42ad0cf0812f50666cb6c70b6d73bce2d1c6c261a66996272fb`
- `kandev`: `7304609866abe143480fdaa9e26feccdfae699e6795eaaf1bd4b55d508066427`

That backend overlay was retired when upstream `v0.94.0` became available. Its
exact binary is retained outside the Docker build context at
`~/.local/share/kandev/hotfix-backups/kandev-b401a094d5fc0f81613eb8470c2544ce87e16f74`.

For Support request `103af197-ff16-45a9-a9af-176244d588d3`, the paired
`agentctl` overlays were rebuilt from source commit
`d41672428e2424b385ee9adff84ad033d266293f`. That commit is a strict child of
the deployed hotfix source `b401a094d5fc0f81613eb8470c2544ce87e16f74`, so it
retains the exact-profile, startup-failure, queue-recovery, attachment, and
other agent-facing tools above. It ports only the reviewed agent-facing plan
projection from upstream plan-safety commit `b1b885714`: plan reads return a
bounded metadata block containing an opaque version and the exact plan body as
a separate block; whole-plan writes advertise and forward `expected_version`
and `allow_truncation`; and successful create/update acknowledgements return
the resulting version. The v0.95 base backend already provides the guarded CAS
implementation and remains unoverlaid.

The active paired binary SHA-256 values are:

- `agentctl`: `8a3ba55c4f0b4e27a8de5835ef36ea08e901c1c195f218e1ea5a47353b380f8f`
- `agentctl-linux-amd64`: `7a1ba8be64931d9edf5c6d4a227cf94081da630aaf8768792759e6ea99932df6`

For Support request `0bf73ca8-18bf-41c1-af92-b9521133de78`, the backend
overlay was restored from source commit
`50d95d2ae` on branch `support/coordinator-profile-controls-0bf73ca8`. Its
base merge `5b6c10bff7b957bb8eb824ca4f0edfe3928003a1` combines canonical
`upstream/main` at `d355a672b1db801e357e8ad7790cfb79a63bcab8` (including the
v0.95 release commit) with the existing exact-profile owner branch at
`e8f5afb3d5bd76aa485a1231f9bf793269e96ea3` and the Coordinator-surface
commit `1b128b6aa36348a4b1425629530ed72f67f8e48a`. It preserves the owner's
strict generation-guarded profile assignment and adds the reusable,
capability-gated canonical Coordinator surface expected by the already
deployed `agentctl` pair. The backend verifies the caller from trusted MCP
provenance and the server-owned canonical Coordinator repository identity,
limits targets to the same workspace, and atomically fences the expected task
state, workflow lane, assignment generation, enabled profile revision, and
exact current model. The selector only records a future exact-profile
selection: it never moves a task, starts inference, or substitutes another
model.

Commit `50d95d2ae` adds a separate canonical-Coordinator handoff tool. It
promotes only an idle sibling with a verified exact-profile launch receipt,
atomically leaves one primary, fences the predecessor, and transfers durable
unread queue identities in FIFO order. The task-scoped plan and future
primary-targeted automation remain attached to the task. A stable operation ID
makes retries idempotent; a failed transfer restores the predecessor before
queue admissions reopen. A fenced predecessor can call only the identical
handoff retry and cannot perform other MCP mutations. The predecessor row and
transcript are preserved for audit and rollback verification.

The response reports the effective profile ID, exact model, immutable profile
revision, resulting assignment generation, target lane, and whether the write
changed state. Bounded session projection then reports the exact-profile
launch receipt and whether the actual launched model matched; raw provider
errors remain private. Ordinary task catalogs and unmodified task launch
behavior are unchanged. This backend embeds a freshly generated complete web
bundle. The active backend binary SHA-256 is:

- `kandev`: `585db8e18ae3e28686019b2b40a985118cdbd805f60cec4780192ac39f54a24c`

The immediately preceding v0.95 backend is retained at
`/tmp/kandev-coordinator-profile-before-0bf73ca8/kandev` with directory mode
`0700`, file mode `0600`, and SHA-256
`f5a0919c9f1e3c0309a3fa36efe76f29bb1f8bc2bb793ab2472055000dae0380`.
The active `agentctl` pair remains unchanged from commit
`d41672428e2424b385ee9adff84ad033d266293f` and therefore retains the plan-CAS,
queue-recovery, attachment, startup-failure, and exact-profile tool fixes
documented above.

An earlier candidate built directly from the pre-v0.95 owner tip had SHA-256
`eff3845eefb7b1f2631e278c02b47b80ab66bdfbe798c73f5752c9e928ad6a44` and
image digest
`sha256:1259108a15eb8a1b7d4535e2f62ca71e20a3e386b2afa9c8527ddf456e9ee114`.
The transactional gate rejected it after it remained in the older migration
path for 960 seconds against the v0.95 database, then verified rollback to
image `sha256:5cd8705cffec51b87d58720ea1c9d124189bcf4931d238c0e840f673ea9d6301`.
It was never accepted as the active deployment. The canonical-main merge
above removes that downgrade path while retaining the reviewed selector.

The immediately preceding pair is retained at
`/tmp/kandev-plan-cas-agentctl-before-103af197` with directory mode `0700`,
file mode `0600`, and SHA-256 values
`6e3563891cd742f2e959e44243d4226b4185810cec34c630a294dac138c18a4f`
and `66ccf5731bf0f42ad0cf0812f50666cb6c70b6d73bce2d1c6c261a66996272fb`.
The v0.95 backend binary from immediately before the interim reconciliation is
retained at
`/tmp/kandev-plan-cas-before-103af197/kandev` with directory mode `0700`, file
mode `0600`, and SHA-256
`f5a0919c9f1e3c0309a3fa36efe76f29bb1f8bc2bb793ab2472055000dae0380`.
The discarded interim upstream backend candidate is retained outside the build
context at `/tmp/kandev-plan-cas-upstream-backend-interim-103af197` with
SHA-256 `1b89be2057eed1fc1a4a168a2b4896d16ceabfd67e7975ca2dbb08f7feeab60a`.

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
