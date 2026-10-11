# Coordinator project artifact broker v1

Support request `725262ad-4336-42ea-92ce-59f8b68d27e6` implements the artifact
route in the Human-approved board coordination RFC. Source owner: this deployment
repository, `scripts/kandev-agent-docker-broker`; image/policy owner: Kandev Host
Support. Platform identity authority: Kandev repositories, task repositories,
tasks, environments, sessions, workflow steps, and parent relationships, read
through the existing read-only metadata connection. No new Host API or database
migration is required. Task `9b4f74dd-1324-496c-bbb5-beccb41b77c6` owns the Host's
discovery presentation, deduplication, recipe/use workflow, and receipt handling.
It must request source operations through its registered Coordinator; ordinary
source-task agents remain denied. Support provisions the reusable capability,
not recurring artifact handoffs.

## Wire contract

Commands use the existing authenticated, task-root-bound Docker broker client:

```text
docker kandev source artifact-discover <repository-UUID> <artifact-key>
docker kandev source artifact-deliver <repository-UUID> <artifact-key> --target-task <task-UUID>
docker kandev source artifact-receipt <delivery-UUID>
```

Only a registered live same-workspace Coordinator may call these operations.
Repository identity is a full platform UUID, never a name or caller pathname.
Delivery additionally requires that repository be attached to the target task.
The target must have one ready environment with an active incomplete session;
its root comes from that environment's exact task directory. Archived, terminal,
ToDeploy, and Feature 8241 tasks (including descendants) are denied before task
filesystem access. No task source, PR, lane, or task metadata is changed.

Discovery returns JSON with one of `AVAILABLE`, `ABSENT`,
`STALE_OR_INCOMPATIBLE`, `INACCESSIBLE`. `AVAILABLE` means the named file's actual
size/hash and read-only ownership match a compatible registration. `ABSENT`
means an approved owner-selected directory or named file is missing. Unknown
projects, owners, artifact keys, inaccessible sources, and invalid registrations
are `INACCESSIBLE`, never a claim that project data does not exist. Invalid CLI
shape is a broker denial. Discovery never creates a source directory. Returned
metadata includes repository UUID, artifact key, Human owner, purpose, format,
version, size, SHA-256, provenance, refresh rule, reviewed recipe ID, registration
hash, and a content-free reason. It contains neither bytes nor recipe text.

Delivery revalidates discovery, then writes exactly the named regular file,
`recipe.json`, and `receipt.json` beneath:

```text
<platform-target-root>/.kandev-coordinator-inbox/<broker-generated-delivery-UUID>/
```

The caller cannot choose a destination path, filename, or delivery UUID. A new
bundle is exclusive; existing files/directories are preserved on collisions.
The recipe is inert JSON with reviewed instructions and expected assertions;
**the broker never executes it or restores/imports data**. Receipt publication
is the completion marker; a target must ignore a bundle without `receipt.json`.
Source file/directory identity, registration digest, Coordinator eligibility,
project attachment, target environment/generation, lane/state, and inbox identity
are checked again before publication. Changed sources or identities fail closed.
Receipt provenance and hash/size metadata are stored independently outside task
writable scope and audited without bytes. Delivery returns those metadata and
the derived target inbox path; the Coordinator receives no payload bytes.

The exact target acknowledges through its own authenticated broker route:

```text
docker kandev artifact-ack <delivery-UUID> RECEIVED <sha256>
docker kandev artifact-ack <delivery-UUID> CONSUMED <sha256>
docker kandev artifact-ack <delivery-UUID> FAILED <sha256>
```

The broker checks target root, active platform environment/generation, artifact
hash/size, and recipe hash before recording an acknowledgement. Identical retries
are idempotent. `RECEIVED` can advance to `CONSUMED` or `FAILED`; a terminal
acknowledgement cannot change. The originating Coordinator can read its own
same-workspace receipt even after the target completes. `target_receipt: null`
means no acknowledgement. A `CONSUMED` receipt is the target's authenticated
assertion, not independent proof that a restore/test succeeded. The Host/task
workflow must also report its bounded expected-assertion/use result through the
normal child→parent→Coordinator route; do not include source bytes in messages.

## Operator registration and owner provisioning

An empty registry is shipped deliberately. Human chooses an existing direct
registered project below `/data/home/Code`, a single project-local directory
basename (usually `artifacts`), the exact file basename, metadata, and reviewed
recipe. There is no generic directory listing, glob, arbitrary absolute path,
sibling worktree, registered folder-source, or credential discovery operation.
No source directories or real data are provisioned by this Support change.

The Human creates optional source inputs outside Git. The artifact directory
and file must have the registered Human numeric UID and no write bits (for
example directory `0500`, file `0400`). Source ancestors must have safe ownership
and no group/other write bits. Symlinks at **any** component, hard-linked files,
non-regular files, traversal, unsafe ownership, oversized files, and changed
sources are rejected. Limits: 64 MiB per file, 128 KiB registration, 32 KiB recipe.
A refresh requires replacing the Human input and reviewing a new size/hash and
compatibility entry; a hash alone is not a secret scanner. Human must identify
which input is authorized and suitable for the target's isolated test scope.

Host Support reviews the selected registration against platform records, owner
provenance, intended artifact/recipe, and protected-task constraints. It places
only reviewed metadata in the Git-ignored
`.local-project-artifacts/registry.json`, then uses `scripts/kandev-safe-deploy
--build` and acceptance checks. The image installs that JSON root-owned, mode
`0444`, at `/etc/kandev/project-artifacts.json`; agents cannot register or update
it. Keep the local registry across rebuilds. It contains no raw data, secrets,
credentials, or executable code. A source-owned manifest may be evidence for
operator review, but is not broker authorization. Do not automatically trust
agent-editable repository manifests. Support must review private registry
changes before every image rollout; copying an unreviewed local JSON into an
image does not constitute approval.

Synthetic schema example (replace IDs, owner UID, and hashes only after review):

```json
{
  "version": 1,
  "projects": {
    "11111111-1111-4111-8111-111111111111": {
      "workspace_id": "55555555-5555-4555-8555-555555555555",
      "repository_path": "/data/home/Code/fixture",
      "owner": "Human",
      "owner_uid": 1000,
      "directory": "artifacts",
      "artifacts": {
        "fixture": {
          "file": "fixture.sql",
          "bytes": 26,
          "sha256": "REPLACE_WITH_REVIEWED_SHA256",
          "compatible": true,
          "purpose": "isolated synthetic QA",
          "format": "sql",
          "version": "1",
          "provenance": "Human-created synthetic fixture",
          "refresh_rule": "owner replaces input and reviews registration",
          "recipe": {
            "id": "fixture-v1",
            "instructions": "Import only into an isolated task-owned test instance.",
            "assertions": ["expected synthetic marker is present"]
          }
        }
      }
    }
  }
}
```

`repository_path` must agree with the exact registered repository UUID's current
path. Repointing a platform registration does not repoint the artifact grant.
Unknown ownership or location requires a single deduplicated owner provisioning
request; never create empty folders or move real data to satisfy discovery.

## Acceptance and boundary limits

`tests/test-project-artifacts.py` uses only temporary synthetic files and SQLite
fixtures. It is included in `tests/test-agent-docker-broker.py` and `test.sh`.
Coverage includes all four discovery states, ordinary-agent denial, workspace
and owner mismatch, source links/FIFO/permissions, stale integrity/compatibility,
protected and inactive targets, exact delivery, target tampering, wrong receipts,
collisions, and source/registration/environment changes during delivery.

No raw Docker, socket, source shell, database mutation, or broader guard mounts
are added. This API confines delivery and receipt authority. The existing
same-UID guard does not provide kernel-enforced cross-task read confidentiality
(see `CLAUDE.md`); this change must not be advertised as repairing that separate
boundary. No live artifact data was selected or read for initial acceptance.
Feature 8241 and Human-owned ToDeploy are outside rollout scope.

Initial acceptance, 2026-10-11: all 129 deployment checks and all 16 synthetic
artifact tests passed. The exact installed broker was tested in a disposable
container without network or live data. Live guarded Coordinator help succeeded;
the ordinary source task remained denied with exit 78. The empty operator
registry was verified as root-owned/read-only and readable by the service user.
Safe deploy accepted image
`sha256:619f9a66988b9c32084cdfae49deee3bd0bcbe20a415ce19a0a57eb3a6047abd`
after HTTP 200. Backend and both agentctl overlays remained byte-identical.
