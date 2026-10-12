# Delivered Human answer reconciliation

Support request `cec73e6a-6760-40d0-9a92-25c15d7fbd96` repairs an intake gap in the deployed own-question lifecycle: an authenticated native conversation answer can already have reached its own session while its original disconnected clarification remains pending. Replaying `/respond` is unsafe after the original turn has advanced. This repair binds existing server evidence without dispatching a turn or submitting a new answer.

## Guarded contract

Only ordinary task-mode MCP exposes `reconcile_own_question_answer_kandev`. Its six required arguments are original question/pending/message IDs and original question/body SHA-256 values. The server injects the execution's own task/session; the backend requires trusted non-automation Kanban provenance, live same-workspace ownership, a nonarchived task and nonterminal session. Neither a choice/body nor another task/session/workspace can be supplied. Office, configuration, automation, external and question-disabled catalogs gain no tool. Raw WebSocket clients cannot dispatch `mcp.*` actions.

The backend requires the exact agent-authored clarification, pending and disconnected with no live waiter or response in flight; the complete persisted Human content must exactly equal its original context, title, prompt and one uniquely identifiable option label. This version supports one single-choice question in the bundle only. Custom text, quotes, residual instructions, ambiguous repeated question envelopes, edited evidence, unknown origins and oversized evidence fail closed.

A `user` author label alone never suffices. The message must have only the server-native fingerprint and queue-admission fields. The retained native user admission must contain identical content and exactly that admission identity, with no sender/agent metadata, in the session's current incarnation. Its immutable JSON hash is pinned in the binding audit. The historical message has no recorded account ID: this control proves the protected native user ingress, not a reconstructed named-account identity. In-session task messages are excluded by their mandatory sender/intent metadata and envelope.

Task-before-session admission locks and per-row compare-and-swap commit exactly two metadata changes: the original question receives answered status, the derived option ID, and an immutable binding audit; the original Human message receives the binding receipt ID. Original bodies, creation times, turn identities and all existing metadata fields survive. No queue entry, counter, task state/lane/primary, provider, question on another session, permission request or credential is modified. Ordinary message-update publication updates lifecycle readers/UI; no PrimaryAnswered/resume event or prompt dispatch is emitted. Identical retry validates the same evidence and returns the original receipt with `changed:false`; conflicts never replace it.

`get_own_question_status_kandev` now exposes the typed `answer_receipt` along with its existing answer projection. The receipt binds workspace/task/session/incarnation, original pending/question/message identities and digests, Human message and admission evidence hashes, and bind time. The fixed namespace receipt ID for this evidence is `936094a4-4a3f-54f0-875c-1a82f0cc7e4d`; that candidate ID is not a claim that Root has accepted it.

## Exact Root acceptance

Refresh MCP discovery using the existing caller task `a68df3ae-aaf5-4591-a46d-9d73db62e46d`, session `13d8c011-6e49-40ef-80e9-2f1445296d06`. Support does not operate that caller.

First use `get_own_question_status_kandev`:

```json
{"question_ids":["coordinator_shared_mobile_lock_owner_20261012"]}
```

Preserve any already recorded genuine answer. If the exact original question is still pending/disconnected, call `reconcile_own_question_answer_kandev` once with:

```json
{
  "question_id": "coordinator_shared_mobile_lock_owner_20261012",
  "pending_id": "abb398da-aa99-4e8e-8326-9f24242e8b01",
  "question_message_id": "1f853401-5b78-4c93-84c7-057017dbf603",
  "question_sha256": "8e8d1ed69938f26208e88c50d6af859e4f2a0870bcba1cbda89630c75fb8c635",
  "answer_message_id": "22f9ad84-4ccc-5efe-8a09-1bfa9e5ae16b",
  "answer_sha256": "bd91e709b82e25da7fac2fe0c092120221005f5c161a0529f61dbd5ebc3fef39"
}
```

Require `receipt.status:answered`, the original pending/message identities and unchanged question hash, `selected_options:["q1_opt1"]`, and the audit's exact original Human message/hash. Re-read the same own-question ID to verify durable settlement. After a timeout, correlate status before retry; never resend the Human message. Publication failure can be retried with the same tuple without making another binding. An existing genuine answer with another lifecycle receipt is preserved, not overwritten.

The next real child material report can use normal `message_task_kandev` to that same Root session. Support sends/replays no child prompt/report. Other unanswered requests still enforce the ordinary barrier. Root owns that real caller and report acceptance.

## Provenance and verification

Source fix `79b0e8a39b7a3ff74cf15fa611202ab558dfaa64` is based on exact deployed hotfix `02bb5d05944141c9e03ad746dde120668f98e46f`, preserving its full prior lineage. Canonical `https://github.com/kdlbs/kandev.git` upstream/main was fetched and verified as `d6887b98b60f530b7e52d5d874019ea1a960550a` before materialization. The private Support administration avoids every shared source ref/worktree-metadata write. The adjacent patch contains only this fix and its tests. The unchanged adoption patch is applied separately, SHA-256 `79b787b189b8df3742d5bd67d838974232f2517c14e3bdd4ce64bab0e9274e2a`; all 361 retained frontend hashes match. The existing shared source checkout's unrelated tracked/untracked files remain untouched.

The live pre-replacement trio matches the task-message-receipt provenance exactly: backend `5d803423d161ba4ebb77e53dc71bc100117199c487d0d2aa101346eada2a3753`, native MCP `7b48366861f4a878c6c70e3922651c9ebcb2e0b3dda37cffd2eef40ed8c2030e`, remote MCP `a4c382a005e621d9629edd03e780b77178c7284a7d0e7cc124dcb69e71c1a88a`. Captured image: `sha256:75c7dbe0ba212fdab6732e6b3f6afcaf5ca37d21aaba1903d064f8081f801564`.

TDD demonstrated missing tool registration and missing durable-admission refusal before implementation. Synthetic regressions cover concurrent exactly-once binding, repeat readback, native admission absence, changed hashes/origin/body, ambiguous questions, attached waiters, inactive/foreign callers, restricted catalogs, ordinary material admission after settlement and continued refusal for an independent unanswered question. Full SQLite, MCP handlers/server, task service and clarification suites passed across scoped runs; the full server catalog passes with ordinary task mode adding exactly one tool and every restricted catalog retained. Adoption/worktree and backend wiring regressions pass on the combined overlay. Backend lint has zero issues; SQL guard and persistence conformance pass. PostgreSQL parity fixtures are environment-gated; no configured test DSN was available. Sandbox-denied loopback/filesystem tests passed using reviewed synthetic host test access; no assertion was weakened.

Backend flags: CGO=1, fts5, buildvcs=false, stripped. Native sidecar CGO=1; remote sidecar linux/amd64 CGO=0; both buildvcs=false and stripped. Deployment and final binary hashes are appended below after the safe-deploy gate. This receipt is capability installation evidence; Support does not claim live question or child acceptance.

## Accepted deployment

`scripts/kandev-safe-deploy --build` exited zero and accepted HTTP 200 at 2026-10-12T22:10:35Z on image `sha256:cee318f8d409330e9945cd958bb6c6159eec72c56e990f43cc31323debfba16f`. No rollback occurred. The live trio matches these candidate hashes:

- agentctl: `4181384550bbe0d1c1f2f1f5157a4a819482417ed8789a8903155779292da8ec`
- agentctl-linux-amd64: `bc7f9d9494ff117bf2bd884fa10f6f4e0e92104fa8c75cd0063edcc81cfa7869`
- kandev: `75128d854c9f5ddcdebe85fd9e3c057897f460ae1d10535a67805ed9053bf57b`

Restart count is zero; AppArmor `kandev-codex` and seccomp remain enforced. All 129 deployment tests passed. Original binaries remain in the private Support rollback directory; the safe-deploy previous image preserves the entire old installation. No live question reconciliation, child message delivery/replay or Source admission was performed by Support. Root owns the exact caller acceptance above.
