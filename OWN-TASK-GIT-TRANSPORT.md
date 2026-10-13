# Exact-caller Git transport: inert diagnosis and held integration

Request `b3ec1917-833a-411b-b4ea-eac46325e635` follows the accepted 9455 checkout
reads. The original receipt and read wrapper remain immutable. This capability
does not accept Git write transport or admit Source.

## Installed inert diagnostic

Existing e400 may run, inside its ordinary guard, once with no retries:

```bash
docker kandev transport-probe
```

This is an additive mode of the existing reviewed broker client, not a new
helper, credential, socket or provider. It uses only the existing fixed mapped
broker endpoint. It does not read any environment/token, caller-supplied address,
task/session, PID or path. It sends an empty anonymous object and framed EOF.
The current server's missing-scope check rejects this before task dispatch,
database access, Git, guard launch, Docker or any source operation.

The observation version is broker-transport-observation/v1. Stages are
arguments, socket_create, connect, send, receive and reply; only numeric errno
is returned, never exception text or response bodies. Timeout is three seconds,
reply is limited to 4096 bytes, and retries are zero. An EPERM observation pins
which syscall phase failed; it does not identify the policy issuer without
additional authorized evidence. Only the exact expected anonymous denial yields
status=anonymous_protocol_reachable and exit0. All results retain
authenticated_binding=UNKNOWN and write_transport_accepted=false. Exit0 is
protocol reachability, not ownership or write acceptance. Unexpected success,
malformed/large replies or extra target arguments refuse. Root must attribute the
genuine observation to existing e400 through its normal authenticated task turn.
Support did not run this command or impersonate that caller.

The old client SHA256 was
963dd4ed6455e370e9c398d4ef900469b8b1f886ed04adfc27a6ccefc7a04e1e;
the tested/read-back installed SHA256 is
58257df3e82d24445b4c31ae6aa025ec88d6ee28c53c60e0f6edf3e7a38d9cfe.
Only that client file was atomically replaced under exact hash fences; owner and
mode were retained. No service/provider/broker restart, image deployment or
policy change occurred. Normal authenticated client behavior is unchanged.
Rollback requires the exact installed hash fence and an atomic restoration of
the retained old client, preserving owner/mode; no task operation is involved.

## Exact server-side authority gap

The existing HMAC signs only task_root. The broker does not authenticate a
session incarnation or environment generation, and receives no trusted backend
execution-stream principal. Adding those IDs to a client request would create
self-asserted fields. The same task-root HMAC is shared across task contexts and
cannot distinguish Source from a sibling. A successful authenticated task-level
Git request still cannot supply the requested exact-caller receipt by itself.

The prior 9455 Support metadata observation is retained historical evidence:
incarnation675d6422, environment7dc3cda5, generation1. These values have not been
newly read or certified in this request. Current actual own-caller binding stays
UNKNOWN, as requested. The Root-reported checkout acceptance at00:24:26 is
recorded as provided evidence, not a Support rerun or original receipt rewrite.

The running Python broker loads handlers once and has no authenticated hot-reload
operation. Its startup unlinks/recreates the socket. The guard bind-mounts the
socket inode into an existing caller namespace: restarting a listener and
recreating its pathname alone cannot prove that existing e400 reaches the new
socket. No restart/rebind or new transport was attempted. Relaxing inner policy,
granting network/raw Docker, anonymous credentials, caller-export inference or
a new filesystem relay is not an authorized repair.

## Bounded prospective integration

The canonical JSON proposal defines an ordinary own-read MCP operation using
the existing native transport and backend mcpscope.Principal, session/environment
repositories, registration checks and generation revalidation. It reuses the
authenticated-own-binding pattern already prepared by f9; it is not that PG16
operation, is not implemented/callable, and grants no product or Source approval.
Only repository UUID, registration UUID and expected HEAD are public inputs.
Task/workspace/session/incarnation/environment/slot/path derive server-side.

The backend compares exact reviewed target, current principal, registered row,
actual environment/generation and materialized worktree/branch against the
preserved original binding. Missing or changed binding is HELD or DENIED. A
normal own verification turn may be RUNNING and advance accounting; neither is
immutable ownership drift. No queue/counter/question is reset. Native transport
observations must arrive through the existing authenticated caller channel,
not an arbitrary caller result/body, supplied PID, task HMAC, nonce or transcript
claim. Existing opaque auth may be used only by its current supported internal
transport; no credentials are extracted, copied or minted. If that integration
cannot obtain existing trusted principal provenance, it remains HELD.

The combined read must recheck caller/incarnation/generation/registration before
returning a short-lived transport_and_own_binding_verified observation. It is
not a transferable grant or Source lease. Root still owns separate Source
admission. No accepted own-caller command exists for this uninstalled operation.

## Maintenance boundary requiring separate review

No provider-preserving code-load path for the current native/backend operation
has been established. Copying new broker bytes does not refresh its running
handlers. Any future loader/restart/recreation must first be separately reviewed
and prove it preserves existing e400, its incarnation/environment generation,
all other users, and the broker listening FD/socket inode or exact mapping.

The deployment/lifecycle owner must supply finite code/resource bindings and a
supported loading method. Target code is only the exact broker-read MCP
adapter/backend handler and any required existing broker handler. No Source
file, registry/profile/auth row or task branch is an installation target.
Preflight must identify all affected provider/MCP/listener identities and the
preservation/recovery contract without credential or global process scans.
If any protected provider, FIFO/counter, unique-state or socket coverage is
unknown, installation is HELD. No approval of unknown handles is proposed.

Any required image recreate must use kandev-safe-deploy and preserve every live
hotfix as a tested superset. HTTP200/automatic rollback alone is insufficient:
the exact caller bindings, other users, queues/counters, and original socket
reachability must also be preserved. Rollback must restore code/socket service
without Source replay, credential reconstruction, session replacement or lost
unique state. A rollback candidate is failed, not RESOLVED. This request grants
none of these lifecycle actions; broad/family stop, signals and environment
recycle remain excluded. A read-only diagnostic approval is not maintenance
authorization.

## Verification and current disposition

Eight synthetic tests pass, including credential/environment non-access,
distinct socket/create/connect/send/receive/reply failures, bounded replies,
target-argument rejection, anonymous-denial-only reachability and task-HMAC
identity limitations. Existing client and 9455 read regressions also pass.
Tests do not authenticate a real caller or identify the live EPERM cause.

Both checkouts were inspected; unrelated source changes survived. No affected
task source, refs/index, provider, registry, lifecycle, credentials, Human runtime,
queues/counters or original questions were changed. The client diagnostic is
installed; actual Source observation, authenticated binding, write acceptance
and Source admission remain UNKNOWN/PENDING/HELD. Root's smallest next action
is e400's single inert observation; the backend owner must then supply the
supported exact-caller read integration/code-load binding above. No instruction
or queued message was relayed by Support.
