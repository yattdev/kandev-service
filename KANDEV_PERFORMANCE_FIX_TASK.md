# Fix PR-watch amplification, task-status contention, and unbounded task-history storage

## Problem

Kandev intermittently becomes very slow despite ample host resources. Investigation rules out CPU, RAM, swap thrashing, and disk I/O.

The slowdown is caused by two Kandev platform issues:

1. GitHub PR watches accumulate across historical agent sessions and generate duplicate polling/events.
2. Agent messages, tool metadata, Git snapshots, and plan revisions grow without an effective retention/compaction mechanism.

## Production evidence

Observed on a live Kandev installation:

- 1,217 GitHub PR-watch rows
- 1,049 watches still marked as searching
- One task had 51 watches for only two branches
- 394 status-summary CAS failures for that task within two hours
- During a ten-minute sample:
  - 57 PR-watch branch changes
  - 56 PR-watch creations
  - 42 exhausted task-status CAS retries
  - 42 event-handler errors
- SQLite database size: 2.8 GB
  - `task_session_messages`: 1.4 GB
  - Message metadata alone: 1.2 GB
  - `task_session_git_snapshots`: 966 MB
  - `task_plan_revisions`: 132 MB
  - One long-lived Coordinator task contained 611 MB of message metadata

Host CPU remained 94–98% idle, approximately 39 GiB RAM remained available, and storage had no measurable I/O pressure.

## Relevant source locations

- `apps/backend/internal/github/store.go`
  - `ListActivePRWatches` considers every watch on a non-archived task active.
- `apps/backend/internal/github/poller.go`
  - `reconcileWatches`, `refreshStaleBranches`, and PR polling process accumulated session-level watches.
- `apps/backend/internal/github/service_pr_watch.go`
  - Watch identity is currently based on session/repository/branch.
- `apps/backend/internal/task/statussummary/projector.go`
  - Concurrent updates exhaust the fixed three-attempt CAS loop.

## Required platform changes

### 1. Make PR watches canonical at task level

A PR belongs to a task/repository/branch, not independently to every historical agent session.

- Canonicalize searching watches by:
  - `task_id`
  - `repository_id`
  - `branch`
- Canonicalize discovered watches by:
  - `task_id`
  - `repository_id`
  - `pr_number`
- Preserve `session_id` only as provenance if still needed; it must not cause duplicate polling.
- A task in Review must remain monitored even when its originating agent session is completed.
- Exclude orphaned watches.
- Ensure multiple agent sessions working on the same task/branch do not create duplicate watches or duplicate GitHub requests.

### 2. Add a safe watch migration

On upgrade:

- Detect duplicate and orphaned watches.
- Retain one canonical row per task/repository/branch or PR.
- Prefer a watch with a discovered PR over a searching watch.
- Preserve the newest check/review/comment timestamps and status.
- Remove redundant rows transactionally.
- Make the migration idempotent.
- Back up or snapshot the database before destructive migration.
- Log before/after counts without exposing credentials.

Do not simply delete all watches associated with completed sessions: Review tasks may still require PR monitoring.

### 3. Stop branch reconciliation oscillation

- Ensure branch resolution has one canonical result per task/repository.
- Repoint a searching watch atomically.
- Consecutive reconciliation cycles with unchanged Git state must produce no writes.
- Add regression tests for repeated resume, branch switching, multiple sessions, and multi-repository tasks.

### 4. Deduplicate PR status events

- Publish `GitHubPRFeedback` and task-PR update events only when relevant state actually changes.
- Coalesce duplicate events by task/repository/PR/head SHA/status.
- Avoid updating task-status summaries once per historical session/watch.

### 5. Make task-status projection contention-safe

- Serialize or single-flight summary projection by `task_id`.
- Coalesce equivalent pending refreshes.
- Re-read/rebase authoritative state after contention.
- Use bounded exponential backoff with jitter for genuine CAS races.
- Do not solve the problem merely by raising the retry count.
- Repeated identical PR events must not produce handler errors.

### 6. Add bounded storage and maintenance

Large tool outputs and Git snapshots must not grow SQLite indefinitely.

- Paginate task/session message retrieval.
- Lazy-load large tool-call metadata rather than including it in normal history hydration.
- Compress or externalize large tool outputs and store a digest/reference in SQLite.
- Deduplicate equivalent Git snapshots.
- Add configurable retention for:
  - superseded tool execution payloads
  - redundant Git snapshots
  - obsolete plan revisions
- Preserve human and agent conversational messages by default.
- Provide a maintenance command with:
  - dry-run mode
  - per-table estimated reclaim
  - database-backup requirement
  - configurable retention
  - safe compaction using `VACUUM INTO` or an equivalent atomic replacement
  - rollback instructions

No historical data should be silently deleted during upgrade unless explicitly covered by a documented safe migration.

### 7. Back off permanent integration failures

Periodic workflow synchronization currently retries GitHub authentication failures repeatedly.

- Classify authentication/configuration failures as non-transient.
- Apply exponential backoff/circuit breaking.
- Surface the disabled/degraded integration in health/status output.
- Resume after credentials/configuration change.
- Do not continuously retry an unchanged invalid credential.

### 8. Add observability

Expose metrics or structured health information for:

- active and searching PR-watch counts
- duplicate/orphan watch count
- polling requests per canonical PR
- task-status CAS retry/exhaustion count
- event-handler failure rate
- message/tool-metadata/snapshot storage size
- database and WAL size
- message-history hydration latency
- queue depth and active runtime count

## Acceptance criteria

1. Fifty historical sessions for the same task/repository/branch result in one canonical PR watch and one GitHub lookup per polling cycle.
2. A Review task remains monitored after its agent session completes.
3. Repeated reconciliation with unchanged Git state creates no rows and performs no branch updates.
4. A branch switch produces one atomic watch transition and does not oscillate.
5. Duplicate PR updates result in at most one effective task-summary update.
6. A concurrency test produces zero exhausted CAS-retry errors and preserves the correct final summary.
7. Upgrade migration removes duplicate/orphan watches without losing active Review monitoring.
8. An invalid GitHub credential enters backoff instead of retrying continuously.
9. Message APIs remain responsive with a multi-gigabyte fixture database and do not load all tool metadata eagerly.
10. Storage maintenance supports dry-run, backup, safe compaction, and rollback.
11. A ten-minute load test with multiple coordinators/tasks produces no PR-watch creation loop, no recurring CAS errors, and stable API latency.

## Tests required

- Unit tests for canonical watch identity and deduplication
- Migration tests using duplicated legacy records
- Multi-session and multi-repository integration tests
- Branch-reconciliation idempotency tests
- Concurrent status-projector tests
- Review-task monitoring after session completion
- Storage-retention and rollback tests
- Large-history API pagination/performance test
- GitHub authentication backoff test

## Non-goals

- Do not require larger host hardware.
- Do not disable PR monitoring.
- Do not delete normal conversation history.
- Do not make completed sessions the sole criterion for deleting watches.
- Do not rely on restarting the container as the fix.

## Deployment follow-up after release

After this is merged and released in the official Kandev image:

1. Back up `kandev.db` together with `master.key`.
2. Update to the released official image.
3. Run the provided migration or maintenance command in dry-run mode.
4. Review the proposed cleanup report.
5. Execute the cleanup and safe compaction.
6. Verify PR-watch counts, CAS-error rate, API latency, database integrity, and board health.

