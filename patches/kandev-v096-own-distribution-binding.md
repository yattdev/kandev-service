# Authenticated own distribution binding (prepared, not installed)

Support request `f9c859f7-c0d1-480b-a571-fc269ece3380` repairs the missing same-caller read surface required by the PG16 distribution contract. Implementation and synthetic verification are authorized; installation is held by this request's explicit provider/runtime mutation exclusion.

## Read contract

The prepared `verify_own_distribution_binding_kandev` MCP tool accepts exactly five nonsecret fields: `repository_id`, `packet_path`, `delivery_id`, `receipt_sha256`, `manifest_sha256`. The task/session identifiers are injected by the ordinary task MCP server and checked against the trusted backend execution-stream principal. A supplied task/session/workspace/incarnation/environment, raw path, body, command, credential or native probe is not a tool argument. External, automation, Office, configuration and question-disabled catalogs do not acquire this operation.

The backend obtains its own live session queue incarnation and environment ownership generation through existing repository interfaces. It validates the same workspace, attached repository, active session, ready environment, unique active registered worktree slot and immediate task-root containment. Terminal, archived, unknown/protected lane and incomplete/stale ownership fail closed. It rechecks authenticated caller and complete durable binding after static filesystem verification.

Only the named own-worktree `.kandev/diagnostics/` packet is read. Receipt and manifest hashes are external immutable review pins, not authority inferred from packet bytes. The exact delivery ID and every packet binding field must match backend-derived ownership. Original `.git` marker, administration HEAD/index and original PROMPT presence/hash must match the original delivery's preservation record, and the live branch ref must resolve to its pinned head. This version requires a linked worktree marker and a loose branch ref; packed/missing refs are an explicit refusal, not inferred equivalence. Symbolic links, path traversal, public packet modes, oversized/nonregular/replaced files, missing receipt fields and changed packet/Git bytes refuse. No Git subprocess, executable helper, hook, native binary, package, SQL write, queue operation, receipt acknowledgement, status/lane mutation or runtime request runs.

The response is `own-distribution-binding/v1` with `status:own_binding_verified`, the full nonsecret backend-derived `binding`, `delivery_id`, original `receipt_sha256` and `manifest_sha256`, relative `packet_path`, unchanged `preservation`, `native_probes_run:false` and `product_acceptance:false`. It is a read observation on an authenticated stream, not a signed offline credential or transferable grant. Source must retain that genuine response and compare the exact task/session/workspace/repository/incarnation/environment/generation/worktree/branch/head tuple. Lifecycle, usage and queue counters are neither read as immutable preservation bytes nor modified. A replaced queue incarnation or environment generation cannot pass the old receipt.

## Exact future caller operation (NOT installed or accepted)

Only existing Source `fb02c865-374b-40c8-98b8-02c2ff19b394`, task `e8728906-86de-4a75-960f-9da585485823`, may perform its acceptance after separately authorized installation and ordinary MCP discovery. Root/Support cannot substitute their own caller.

```json
{
  "repository_id": "a462935c-6825-463e-aff0-60b20f87f6fb",
  "packet_path": ".kandev/diagnostics/pg16-31a2d4ae",
  "delivery_id": "b21ff77b-0e84-4a80-983e-98e98b7bc192",
  "receipt_sha256": "eb4572656cebb52deffdbd748c50a77bcbe0eb1be3ac5a87aa88691f9d0c7fba",
  "manifest_sha256": "d3fb175f74039a333a463eea5583e24b8552265a493f7f9cc93c629fad9b0555"
}
```

Require the exact original workspace `2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd`, incarnation `2070b0b2-c9ea-4f79-aab7-18f2b0f82702`, environment `04c8fe7d-1c9e-487b-b690-3dcbe274a55c`, generation `1`, worktree ID `d41703e1-a354-4503-a5b5-324606065e54`, own registered worktree, branch `feature/fix-plugin-task-prio-w7w` and head `6bd1bec2679fc71b5333a7255a70693ff4942a01`. Require the supplied packet hashes and correction/recipe hashes already given by request31a2; this operation preserves the latter files and does not replace Source's independent signature/index/package/file/dependency acceptance. It runs no binary or selector. Root separately authorizes the unchanged count1/retries0/250ms paired selectors only after actual own-caller packet acceptance.

## Installation boundary and smallest next action

There is no established supported hot reload for adding native backend/MCP code to this exact existing caller. The current broker token authenticates a task root, not a session, so it cannot provide an equivalent sibling-resistant receipt. Direct DB access, caller-export inference, new credentials and a packet-only identity claim are ineligible alternatives.

The required safe deployment recreates the service. The current backend's `stopLifecycleManager` calls `StopAllAgents` on shutdown; this is an actual provider lifecycle effect, not merely a tool-catalog refresh. No deployment, binary-overlay installation or provider action is performed here. The separately reviewable next action is a deployment-owner maintenance contract that explicitly authorizes those provider effects and preserves/reconciles affected sessions, FIFO, counters and unique state, or an existing supported authenticated reload that proves provider preservation. Generic additional engineering approval is unnecessary. Do not start/replay Source or present the prepared invocation as a live acceptance command while installation remains held.

## Immutable lineage

The implementation is a strict child of own-answer source `79b0e8a39b7a3ff74cf15fa611202ab558dfaa64`, retaining all preceding local fixes. The separate existing adoption patch SHA256 `79b787b189b8df3742d5bd67d838974232f2517c14e3bdd4ce64bab0e9274e2a` remains applied in the private Support build tree and is excluded from this new patch. The deployment/source canonical checkouts and all unrelated user files are preserved. Original PG16 manifest, delivery receipt, socket correction, recipe, archives and target task are not edited or reprovisioned. The capability receipt below records verification and candidate hashes; none are a deployment or caller-acceptance claim.

## Prepared build and verification

Source commit `9fde182148c2a186c308376cae0efa8f107d4a66` retains the exact parent above. All three native candidates were built without installing or invoking them. Backend CGO=1 with fts5; native agentctl CGO=1; remote linux/amd64 CGO=0; all use buildvcs=false and stripped linkage. Full artifactbinding, MCP handler and MCP server suites pass with race detection; lint has zero issues. The catalog rebuild count was updated to include exactly this tool, and restricted catalogs remain excluded. All 361 frontend bytes match the retained baseline.

- Candidate kandev: `bf170441899c7533eb6783a121838230dd5f5a373abdfbf98a4788223f1b73fb`
- Candidate agentctl: `9731de452fabcb4389fb12537e6fb2d0bee67dd70dbbeb561338fb2274f4f16c`
- Candidate agentctl-linux-amd64: `061206dda525d05a39da2058f3504e5fc5bdbd5572d7c8456d8acc3bef064e32`

Source patch SHA256: `282e5c5749614a92cfda3becf785f1bbb1eb95a053a51075e24ebd1391b958b9`. Preparation receipt SHA256: `181094a23a2572a2b25894ed578c927546014a98b4e91f9b0d2aec6a79d15740`. Live image remains `sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`, running with restart count0 and AppArmor kandev-codex. No service recreation, overlay replacement, caller acceptance or task/PG runtime operation occurred.
