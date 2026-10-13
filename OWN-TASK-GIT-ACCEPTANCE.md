# Owning-task acceptance reads after repository attachment

Capability version: `own-task-git-acceptance-read/v1`.
Support request: `9455eacf-f452-47b8-bfc0-aa289fceaae7`.

The deployed Git wrapper previously sent every invocation to the task broker
when its metadata directory was nonwritable. A repository attached after guard
construction can have readable, nonwritable administration. Acceptance reads
then unnecessarily depended on a socket which this caller reported as EPERM.
The socket error's underlying cause remains UNKNOWN; it is not a repository
authorization receipt. No socket permission or provider policy was changed.

The existing wrapper now handles a finite set of acceptance reads locally inside
the caller's unchanged guards. It disables optional locks, paging, fsmonitor
and untracked-cache updates. Supported forms are status with the listed ordinary
porcelain/short/branch/untracked options, branch --show-current, and specific
rev-parse HEAD/identity forms. Repeated -C is accepted only while each resolved
directory stays inside the existing task root. Unknown options, -c/custom
administration, environment administration overrides, escaping symlinks and all
mutating commands retain the previous broker dispatch. This is command routing,
not a new authentication surface or Source ownership grant. The wrapper does not
derive authority from a supplied receipt or repository marker.

## Installation and preservation

The original deployed wrapper exactly matched the retained repository parent,
SHA256 `9df53f94a1e8cc67336787d352ac7b60bbed20f4c22f327a1f6bfba26616c9a9`.
The replacement SHA256 is
`3b50f0847262641f6f2357736db4451c5d9eb556811819025872dd5ddb432340`.
Reviewed Support staged it and atomically replaced only the existing service Git
wrapper after comparing both hashes. Existing owner and mode were preserved.
The first installer invocation received no stdin and made no replacement; the
corrected fenced installer completed, and independent readback matched the new
hash. The temporary staging file was consumed by the atomic replacement.

No image was deployed or service recreated. The exact service container/image
identity and restart count remained unchanged. No backend/agentctl binary,
broker, guard, seccomp, AppArmor, token, profile, grant, session, registry row,
provider, task source, Git administration, FIFO or counter was modified. The
versioned wrapper persists the fix for future normal image builds; no rebuild or
deployment is authorized or needed for this script installation.

Rollback is limited to restoring the retained original wrapper atomically after
checking that the active file still matches this replacement. Preserve its
owner/mode and every task resource; no provider restart or Git operation is
part of rollback. No rollback was performed.

## Exact retained caller binding

Support read-only metadata confirms task
`3cf0e07b-eac6-4703-bd5d-5d31920bf3e0`, workspace
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`, session
`e400b8a7-ffe9-4532-abcf-33d00c04ba5d`, queue incarnation
`675d6422-ca23-4943-8e6c-77584d5d3d0d`, environment
`7dc3cda5-cab2-48c6-9878-0a139ea7ffa9`, ownership generation 1.
The caller's recorded guard prefix/modes remain the required outer guard and
agent-full-access. These are metadata observations, not a new launch or a claim
that a physical execution ended. Live task state was REVIEW, unarchived, and the
session WAITING_FOR_INPUT; no state was changed by Support.

Registration `10fa6c96-f66d-4e9d-a49c-176b88839889` identifies canonical repository
`a462935c-6825-463e-aff0-60b20f87f6fb`, base origin/main, position 2. Materialized
slot `7b7b82b6-5225-44db-a293-4f8f680b17ca` is active, with worktree
`309f3ced-758f-47a6-8da7-70c106e71017`, path
`/data/tasks/publish-terminal-ret_6zus7gtg/kdlbs-kandev-origin-main` and recorded
task-private branch `feature/publish-terminal-ret-1qs`. Registration alone does
not grant Source writes. Source must validate the existing marker, actual branch,
clean checkout and expected pin; Support did not open or run Git in that checkout.

## Same-caller inert acceptance

Only the existing authenticated e400 session runs this in its ordinary guard,
after confirming its own task/workspace/repository/registration through existing
supported MCP reads. Root and Support cannot substitute callers. Confirm the
same binding and marker; a changed caller/incarnation/generation/registration,
missing marker, different wrapper or unknown binding holds acceptance. The
metadata receipt is not a transferable credential or accepted caller receipt.

```bash
set -eu
cd /data/tasks/publish-terminal-ret_6zus7gtg/kdlbs-kandev-origin-main
test "$(sha256sum /usr/local/bin/git | cut -d ' ' -f1)" = 3b50f0847262641f6f2357736db4451c5d9eb556811819025872dd5ddb432340
test "$(git rev-parse --show-toplevel)" = "$PWD"
test "$(git branch --show-current)" = feature/publish-terminal-ret-1qs
test "$(git rev-parse HEAD)" = 371d9c18193af5893fbe70387fee9330f7dbb65b
test -z "$(git status --porcelain=v1 --untracked-files=all)"
printf '%s\n' own_task_registered_checkout_read_verified
```

The required pin is caller-supplied admission evidence, not a new Support fetch
or checkout claim. A mismatch must be reported and held; never reset, clean,
rewrite, substitute a branch or retry an old source cohort to force acceptance.
After genuine acceptance, Root separately confirms the registered task-private
branch/Source admission before extraction. This repair issues no write command,
lease, implementation, CI, review, gate PASS or product acceptance. Writes still
use the existing broker; their transport acceptance is not certified here.

## Verification

The private-repository regression failed before the fix with exit78 on status,
then passed after the change. It checks exact HEAD/branch/clean read outputs,
unchanged Git file hashes, no external fsmonitor invocation and preserved broker
dispatch for writes, unknown config/admin flags, outside -C and symlink escape.
Broker policy tests and client framing/output tests pass; Bash syntax and diff
checks pass. These are synthetic platform checks, not retained-Done product
tests or the affected caller's acceptance. The installed bytes match the tested
script. Actual e400 acceptance remains PENDING.
