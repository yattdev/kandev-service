# Caller binding installation audit, escalation1

Request f9c859f7-c0d1-480b-a571-fc269ece3380. This supplements the original
immutable prepared repair receipt; it does not install, deploy, accept a caller,
reprovision PG16, or amend historical hashes.

The original installation diagnosis overstated StopAllAgents. Deployed source
79b0e8a has a survival-enabled, non-passthrough standalone shutdown path that
only detaches backend tracking/stream subscription. It does not call StopInstance
or publish agent.stopped. Other shutdown paths may terminate. Five targeted
synthetic race tests pass for these branches and worktree preservation.
Neither code nor a synthetic test proves the current fb02 runtime's survival
flag, physical placement or persistence through service-container recreation.

Both checkouts were inspected. Ordinary MCP queue/session/conversation reads
omit the required complete tuple. Diagnostic projection also omits it. The
stored HTTP environment getter has no established usable ordinary same-caller
MCP auth route. Dynamic plugin catalog refresh is supported, but existing plugin
Session host ABI omits queue incarnation/environment generation. Extending it
needs backend code replacement. No plugin, grant, hidden API or credential was
used. The broker's task-root HMAC cannot distinguish sibling sessions; no new
session credential or process-based inference was introduced.

In-place binary replacement cannot change a running native/backend process.
No supported provider-preserving own-caller native-code reload was found.
Required safe-deploy recreates the service container, a separate physical
boundary from survivable backend detach. No recreation, raw process restart,
provider operation or alternative deployment was attempted.

Reviewed host escalation requested only the exact Kandev service's image,
PID-namespace and init configuration. Automatic review rejected it, stating
that it conflicts with the raw Docker/host-access restriction and is unnecessary
for the caller-binding verifier. It was not executed or retried indirectly.
Namespace topology remains unverified. The generic Support host-diagnostic
boundary was considered; rejection is retained, not bypassed.

The missing predicate is a supported installation binding that loads both new
native/backend surfaces while preserving the exact Source caller, incarnation,
environment, FIFO/counters and provider runtime. The smallest next action is a
reviewed provider-preserving installation/reload plan from its deployment owner,
or a changed, scoped maintenance contract covering actual lifecycle effects and
preservation/recovery. The engineering fix is already authorized and prepared.
If namespace validation is chosen, the exact rejected read needs reviewed
approval and grants no deployment/provider authority.

Original source fix9fde182, deployment25697a9, repair receipt181094a2, PG16 packet,
archives, correction/recipe and all candidate binaries are unchanged. No caller
or product acceptance is claimed; paired outcomes remain NOT RUN/UNKNOWN.
The append-only audit is support-evidence/pg16-own-binding-f9c859f7-escalation1.json.
