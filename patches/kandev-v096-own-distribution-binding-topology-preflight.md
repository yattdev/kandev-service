# Approved service configuration preflight

Request `292c1a55-0dbb-486f-8d02-3c236a07cbb3` completes only the newly
authorized configuration read. It does not install the prepared f9 verifier.
The prior rejected attempts and their receipts remain unchanged.

The broker supplied an answered native Human question
`coordinator_f9_topology_read_20261013`, question ID
`7ee2601c-15f8-4b34-be20-9a5efd6ef1af`, answered at
`2026-10-13T00:36:52.753057377Z` with `q1_opt1` (Allow read).
Support did not submit, reconcile or independently query that answer.
Automatic review approved the newly scoped execution. This command ran once,
with exit 0:

```text
docker inspect kandev --format 'image={{.Image}} pid_mode={{json .HostConfig.PidMode}} init={{json .HostConfig.Init}} restart_count={{.RestartCount}}'
image=sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f pid_mode="" init=null restart_count=0
```

The image matches the retained deployment evidence. Empty PID mode selects the
default container PID namespace configuration; it does not identify the
namespace of fb02 or its descendants. `init=null` is an unspecified Docker init
setting, not an inventory of entrypoint or supervisor processes. Restart count
0 is this container's restart counter, not evidence that it was never recreated
or that a provider survived an earlier operation. These are configuration
observations, not process ownership or survival certificates.

The retained static assessment remains applicable. `StopAllAgents` can detach a
survival-enabled, non-passthrough standalone provider during backend shutdown;
other paths may terminate it. The earlier five synthetic race tests cover those
code branches, not current fb02 eligibility or physical placement. SIGHUP takes
the shutdown path. Replacing on-disk binaries does not load new code into the
running native tool server. Safe deployment and rollback recreate the service
container, and their HTTP gate does not certify provider/caller preservation.
Processes resident in the service's private PID namespace would face that
container lifecycle boundary. This read cannot establish whether fb02 is among
them. No provider-preserving code-load path is established by these four fields.

## Concrete next preparation step

The existing deployment/lifecycle and native-MCP owners must prepare one finite
installation manifest from their already-held authenticated launch/connection
records, bound to task `e8728906-86de-4a75-960f-9da585485823`, session
`fb02c865-374b-40c8-98b8-02c2ff19b394`, workspace
`2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`, repository
`a462935c-6825-463e-aff0-60b20f87f6fb`. No new process scan, credential lookup,
runtime request, replacement session or operational probe is authorized here.
This is a proposed owner preparation step, not an available caller command.

The manifest must include:

- Authenticated current execution/launch reference and queue incarnation
  `2070b0b2-c9ea-4f79-aab7-18f2b0f82702`; environment
  `04c8fe7d-1c9e-487b-b690-3dcbe274a55c`, generation 1; owner epoch and expiry.
- Retained evidence of runtime class, survival setting, passthrough status and
  containment/namespace relationship to the service being replaced. Configuration
  defaults and zero/missing handles do not prove these fields.
- An existing supported operation that loads both backend and native MCP code
  into the same authenticated caller channel, with a before/after binding check.
  Include its effects on service, provider, connection and socket ownership.
- Preservation and recovery guarantees for the exact provider's unique state,
  original PG16 packet and archives, Source head `6bd1bec2679fc71b5333a7255a70693ff4942a01`,
  FIFO/order/counters/questions and other users. Retain every old receipt and
  the complete still-required hotfix superset. HTTP readiness alone is insufficient.
- Explicit missing fields and effects requiring separate maintenance authority.
  Return HELD if any ownership, survival or code-load field is unavailable;
  never infer acceptance or create new identity evidence to fill a gap.

Root reviews that manifest before any installation decision. If the owner cannot
provide a preserving load operation, the next decision is a separately scoped
maintenance/preservation/recovery contract naming actual lifecycle effects and
protected resources. It cannot be authorized by this topology-read approval.
Generic engineering approval is already sufficient for the prepared repair and
does not resolve the missing installation predicate. No maintenance operation or
new diagnostic is requested or executed by this document.

Both local checkouts were inspected; unrelated source changes were preserved.
Prior PG16/f9 evidence, patch, safe-deploy script and all three candidate binary
hashes were revalidated locally. No code changed, so no new synthetic, native or
product tests were run. No target resource was opened, provider operated, binary
installed, service changed, or queue/counter/question mutated. The f9 tool stays
uninstalled; own-caller acceptance and paired tests remain NOT RUN/UNKNOWN.
