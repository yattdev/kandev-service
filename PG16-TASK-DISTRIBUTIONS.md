# Signed task-private PostgreSQL 16 distribution

Contract `signed-pg16-task-distribution-v1`; Support request
`31a2d4ae-9603-4cf9-b503-de4d7147d20f`.

This capability supplies an inert, extraction-only native distribution. Source
owns acceptance, initdb, synthetic schema, diagnostics and stop verification.
Support does not launch PostgreSQL, run product tests, change test budgets, or
claim a CI result. No apt installation, maintainer script, system service,
shared package cache, credential or new agent helper is needed.

## Trust and delivery

Use the official PostgreSQL PGDG HTTPS repository, suite `bookworm-pgdg`,
component `main`, architecture `amd64`. Pin the public key fingerprint
`B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8`, published by PostgreSQL. Verify the
InRelease signature before selecting any package; verify index size and SHA256
against its SHA256 section; verify each exact package/version/architecture,
payload size and SHA256 against that authenticated index. Retain the public key,
signed release, package index and original debs beside the extraction.

Only `dpkg-deb --extract` is used. Install-time common-package wrappers,
service creation, generated locales, SSL certificate provisioning and package
maintainer scripts do not run. This fixture uses locale C with UTF8 encoding,
Unix sockets, peer authentication, SSL off and JIT off. The optional LLVM19
JIT module is not certified. Arbitrary extensions and external preload modules
are outside this diagnostic contract. The distribution is a PG16 native
diagnostic; it does not claim byte equivalence to the pinned CI container.

The new server/client and libpq payloads have PGDG signature provenance.
Their remaining loaded libraries come from the preissued read-only Debian12
Kandev runtime, not newly installed packages. The delivery dependency receipt
records those actual resolved library hashes and installed package versions.
This is an explicit existing-runtime trust boundary, not a retrospective
PGDG signature claim for Debian libraries. Acceptance must reject missing or
changed required libraries. LLVM dependencies are excluded only because the
fixture forbids JIT; server, initdb, pg_ctl, psql, createdb and plpgsql must load.

The generic Human artifact broker requires an existing owner registration.
Support must not fabricate a Human registration for its own distribution.
This request instead authorizes one reviewed Support resource packet to the
exact existing task-private diagnostic slot. Reuse this contract for future
authorized tasks, with fresh exact bindings and signed package pins. It does
not create a general write grant or new artifact catalog.

Delivery uses exclusive creation, directory descriptors and no-follow checks.
Reject target symlinks, collisions, hardlinks, archive traversal, special files,
stale session incarnation, changed environment generation, task/workspace/repo
mismatch, protected/terminal task or changed source HEAD/index. All packet
directories are mode0700; provenance/receipts/debs are mode0600. Read-only
native `--version` and dependency-loader checks may validate capability; they
never initialize a cluster or execute a product diagnostic. Publish the
completion receipt last after binding and preservation rechecks. A partial
packet has no authority and must not be consumed or silently overwritten.

## Exact caller acceptance

The authorized task is `e8728906-86de-4a75-960f-9da585485823`, session
`fb02c865-374b-40c8-98b8-02c2ff19b394`, queue incarnation
`2070b0b2-c9ea-4f79-aab7-18f2b0f82702`, workspace
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`, repository
`a462935c-6825-463e-aff0-60b20f87f6fb`, environment
`04c8fe7d-1c9e-487b-b690-3dcbe274a55c`, generation1.

The existing worktree is
`/data/tasks/fix-plugin-task-prio_rksfvx9c/kdlbs-kandev`, branch
`feature/fix-plugin-task-prio-w7w`, preserved HEAD
`6bd1bec2679fc71b5333a7255a70693ff4942a01`.
The packet slot is `.kandev/diagnostics/pg16-31a2d4ae`.

Source must obtain its current authenticated own-session/incarnation receipt
through its existing supported Kandev surface and compare every binding above.
Root cannot substitute its caller. If exported task/session IDs are present,
they must also match; absence is not permission to infer caller identity from
the packet. A mismatched/replaced session or incarnation needs a fresh reviewed
delivery binding. Verify the completion receipt and manifest hashes supplied
in the Support result independently, plus every manifest file and symlink.
Never trust a locally edited receipt alone. Check all task-private ancestors
are real directories and not symlinks; packet owner/modes must match.

The offline signature and package verification commands are:

```bash
set -euo pipefail
umask 077
DIST="$PWD/.kandev/diagnostics/pg16-31a2d4ae"
gpgv --keyring "$DIST/provenance/pgdg.gpg" --status-fd 1 \
  "$DIST/provenance/pgdg.InRelease"
```

Require the exact VALIDSIG fingerprint above. The supplied manifest gives the
release/index/keyring/deb hashes, sizes and package fields. Parse the signed
SHA256 section and the compressed package index to check their linkage; merely
verifying a key signature without checking package-index membership is
insufficient. Check SHA256 for every original deb and every extracted file,
and ensure symlink targets remain within the distribution.

Clear inherited PG authentication/service settings for capability probes:

```bash
PGBIN="$DIST/sysroot/usr/lib/postgresql/16/bin"
PGLIB="$DIST/sysroot/usr/lib/x86_64-linux-gnu"
env -i PATH=/usr/bin:/bin LC_ALL=C LD_LIBRARY_PATH="$PGLIB" \
  "$PGBIN/postgres" --version
env -i PATH=/usr/bin:/bin LC_ALL=C LD_LIBRARY_PATH="$PGLIB" \
  "$PGBIN/initdb" --version
env -i PATH=/usr/bin:/bin LC_ALL=C LD_LIBRARY_PATH="$PGLIB" \
  "$PGBIN/psql" --version
```

Require `16.15` for all three and compare the runtime dependency receipt. These
commands do not start a database. The actual Source turn performs acceptance
inside its existing outer guard, without raw Docker or host credentials.

## Source-owned fixture and cleanup

After accepted binding, create one new ignored mode0700 fixture directory
below the same task's `.kandev` directory. The socket's complete filename must
be at most107 UTF8 bytes on Linux; nesting it inside this long packet path
would produce118 bytes and fail. The shorter exact path below produces98.
Existing fixture state is a collision, not a cleanup license. An append-only
`unix-socket-correction.json` links the original receipt to the corrected
recipe; verify both hashes from the Support result before using it. Original
package/manifest/receipt evidence remains immutable. No Support operation runs
these commands:

```bash
FIXTURE="$PWD/.kandev/pg16-31a2d4ae"
mkdir -m 700 "$FIXTURE"
mkdir -m 700 "$FIXTURE/socket"
PGUSER_LOCAL="$(id -un)"
env -i PATH="$PGBIN:/usr/bin:/bin" LC_ALL=C LD_LIBRARY_PATH="$PGLIB" \
  "$PGBIN/initdb" -D "$FIXTURE/data" --locale=C --encoding=UTF8 \
  --auth-local=peer --auth-host=reject -U "$PGUSER_LOCAL" \
  -L "$DIST/sysroot/usr/share/postgresql/16"
env -i PATH="$PGBIN:/usr/bin:/bin" LC_ALL=C LD_LIBRARY_PATH="$PGLIB" \
  "$PGBIN/pg_ctl" -D "$FIXTURE/data" -l "$FIXTURE/server.log" \
  -w -t 30 -o "-k $FIXTURE/socket -p 55432 -c listen_addresses='' \
  -c unix_socket_permissions=0700 -c ssl=off -c jit=off \
  -c shared_preload_libraries='' -c session_preload_libraries='' \
  -c local_preload_libraries=''" start
```

Paths are exact fixed packet paths without whitespace or shell metacharacters.
Do not generalize pg_ctl's string into untrusted caller arguments. Use the
same clean environment for all subsequent PostgreSQL utilities, with only
PGHOST set to this private socket directory, PGPORT55432, PGUSER to the local
OS account and PGDATABASE to the synthetic database. Do not inherit PGPASSWORD,
PGPASSFILE, PGSERVICE/PGSERVICEFILE, another DSN, arbitrary LD_PRELOAD or a helper.

Source verifies server version, `listen_addresses=''`, socket path/permissions,
peer authentication, JIT off, SSL off and expected client/server identity using
the private client and a benign SQL health query. Record native client version,
server version, owned data directory, socket and postmaster PID/start evidence.
No passwords are created or copied. The mode0600 DSN file is task-private and
outside tracked files; construct its value from this socket/database only.
A successful Unix connection alone does not prove TCP is disabled: record the
effective setting and this postmaster's listen configuration.

Source owns synthetic schema creation and exactly the existing retention
Postgres selectors: once at base `bc0d3b90477078bb5e002e1a18d5e7fbe9c91f71`
and once at merge `17232d18965d6fcd9b4723bfd9024d4ad39b23a8`, count1, no retries,
unchanged250ms retention batch context budget. Preserve the existing ignored
archives and test-file hash. Verify selector execution was unskipped and record
exit/schema/client evidence. Native outcomes remain NOT RUN/UNKNOWN until the
Source supplies its own evidence. No source/test edits, checkout switch, CI
rerun or alternate gate is authorized by this capability receipt.

Stop only the fixture started by this exact Source acceptance:

```bash
env -i PATH="$PGBIN:/usr/bin:/bin" LC_ALL=C LD_LIBRARY_PATH="$PGLIB" \
  "$PGBIN/pg_ctl" -D "$FIXTURE/data" -m fast -w -t 30 stop
```

Verify pg_ctl status returns3, the same fixture's postmaster.pid is absent,
and its socket/socket-lock files are gone. Preserve logs, receipt, DSN and data
as task-private diagnostic evidence; cleanup means graceful service stop,
not artifact deletion. Never use process-name scans, broad kills, another data
directory, shared/live databases or a sibling task's server. If stop cannot be
proved, hold the fixture and escalate the exact owned PID/start binding.
