# Own distribution binding: final installation audit

Request `f9c859f7-c0d1-480b-a571-fc269ece3380`, escalation pass 2.
This is append-only installation evidence, not a deployment or caller receipt.

The broker's explicit distinction between guarded agents and reviewed Support
host diagnostics was presented to automatic review. The proposed read was only
the exact Kandev service's image, PID-namespace mode, init setting and restart
count. It requested no task/process enumeration, environment, credentials,
socket exposure, runtime action or deployment. Automatic review rejected the
request again, saying that it repeated a prohibited Docker/host diagnostic.
The read was not executed or obtained indirectly. Namespace topology remains
UNVERIFIED. Explicit approval of that exact limited read is the concrete next
review request; it would authorize no installation or provider operation.

Both checkouts were inspected and unrelated source changes preserved. Static
review of the retained deployed source adds a precise exclusion: SIGHUP is a
shutdown signal, not native code reload. Startup cancels on its first shutdown
signal; the normal shutdown handler runs graceful shutdown for SIGHUP as well.
It calls lifecycle shutdown, whose survivable standalone detach path remains
the corrected finding from pass 1. No signal was sent. Replacing binary bytes
cannot refresh the running native tool server. No alternative restart, hidden
API, plugin credential, session substitution or unreviewed reload was attempted.

The supported safe deployment explicitly recreates the service container and
may also recreate it during rollback. Its HTTP health gate does not certify
preservation of fb02's provider, existing native MCP process, queue incarnation,
environment generation, FIFO, counters or unique state. Backend detach tests
cannot establish that separate physical boundary. Current provider location and
survival eligibility are unverified and cannot be guessed from compose files.

The least next installation contract must first establish a supported code-load
path preserving the existing fb02 session and provider. If that is impossible,
the deployment owner must obtain separately scoped maintenance authorization
for actual lifecycle effects and recovery; the current request excludes them.
No generic engineering approval or caller acceptance waiver is needed or valid.
A topology-only approval is not a maintenance approval and does not itself make
the prepared tool callable.

Source fix 9fde182 and all three tested candidate binaries remain unchanged.
Original PG16 delivery evidence, preparation receipt and pass 1 audit remain
immutable. No reprovisioning, task resource read/write, product test, provider
operation, queue/counter/question change, overlay installation or deployment
occurred. Actual same-caller acceptance and paired tests remain NOT RUN/UNKNOWN.

The final audit receipt pins retained artifacts and additional static code.
Existing verifier/race/lint/build results remain the original prepared results;
no new runtime or test outcome is claimed by this document.
