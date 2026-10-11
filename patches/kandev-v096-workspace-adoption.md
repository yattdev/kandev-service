# Independent task checkout adoption overlay

Base source: `37b8f8a744ea57fe212e8a72d7ea879b37809615`, the exact preceding
v0.96 backend overlay. `kandev-v096-workspace-adoption.patch` adds one admission
case to the existing checkout integrity validator: a plain independent `.git`
directory whose exact path is attested by the installed
`kandev-workspace-registration check-adopted` command. Ordinary independent
clones, symlinks, changed ownership, changed origins, changed branches and
invalid retirement artifacts remain rejected. Existing linked-worktree checks
are unchanged. Attach-only reuse retains its pinned directory handle and
ownership checks, and admits the independent checkout only through that same
attestation. A read-only live probe exercised both integrity and attach-only
reuse against the repaired checkout before deployment. The patch includes Go
unit tests; Python policy tests cover the real database attestation.
To repeat the optional live Go probe, set `KANDEV_TEST_ADOPTED_CHECKOUT` and
`KANDEV_TEST_ADOPTED_TASK_ID` to the existing repaired checkout and its task UUID.

The helper reads the canonical live database and validates the existing
operator repair record against current task/environment ownership. It grants
no extra filesystem access and performs no Git checkout, reset or materialization.

Build from an exported archive of the pinned commit (no clone or worktree is
needed), apply the patch, run `go test -tags fts5 ./internal/worktree`, then build
with `go build -tags fts5 -buildvcs=false -ldflags='-s -w' ./cmd/kandev`.
Embed the matching complete generated frontend in
`apps/backend/internal/webapp/embedded/generated` before building. The existing
frontend was preserved from the live static files, with only the per-request
boot payload removed from index.html. The pinned asset archive and hashes are
kept privately under `/data/hotfix-backups/workspace-adoption-20261009/`.

The previous backend binary is retained in that same private directory.
Install the candidate as `.local-hotfix/kandev`, deploy through
`scripts/kandev-safe-deploy --build`, and require the full `bash test.sh` suite
before resuming the existing session. Dockerfile.local persists this binary and
the attestation helper across rebuilds. No agentctl binary change is required.

Final backend SHA-256:
`68eaa38d6027240935f0c80c6190df137184730ff0c81a33ae71bd6e8dbc4a2d`.

This operator adoption is specific to the SQLite deployment. When carrying it
upstream, expose an equivalent backend-owned adoption operation through the
normal repository/service API and keep admission tied to authoritative ownership.
