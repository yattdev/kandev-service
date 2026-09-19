#!/usr/bin/env python3
"""Focused tests for the host-side Kandev Support queue worker."""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock


WORKER_PATH = Path(__file__).parents[1] / "scripts" / "kandev-support-worker"
SPEC = importlib.util.spec_from_loader(
    "kandev_support_worker", SourceFileLoader("kandev_support_worker", str(WORKER_PATH))
)
assert SPEC and SPEC.loader
worker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(worker)


class WorkerTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        worker.QUEUE = Path(self.temporary.name)
        worker.THREAD_STATE_OVERRIDE = ""
        worker.THREAD_MAX_AGE_SECONDS = 86400
        worker.TURN_TIMEOUT_SECONDS = 7200
        worker.SOURCE_REPOSITORY = Path("/home/test/Code/kandev-source")
        self.notify = mock.patch.object(worker, "notify_coordinator")
        self.notify_mock = self.notify.start()
        self.notify_mock.return_value = "message-id"
        self.addCleanup(self.notify.stop)
        self.guard = mock.patch.object(
            worker,
            "deployment_guard",
            return_value={"container_id": "before", "image_id": "image-before", "started_at": "t0"},
        )
        self.guard.start()
        self.addCleanup(self.guard.stop)
        self.postcondition = mock.patch.object(
            worker,
            "enforce_deployment_postcondition",
            return_value={"changed": False, "status": "unchanged"},
        )
        self.postcondition.start()
        self.addCleanup(self.postcondition.stop)
        for directory in ("pending", "processing", "records", "responses", "notifications"):
            (worker.QUEUE / directory).mkdir()
        self.seed_thread()

    def seed_thread(self, created_at: float | None = None) -> str:
        thread_id = "00000000-0000-0000-0000-000000000001"
        worker.persist_thread_state(
            thread_id,
            worker.time.time() if created_at is None else created_at,
        )
        return thread_id

    def record(self, request_id: str, created_at: str = "2026-08-29T00:00:00Z") -> Path:
        path = worker.QUEUE / "pending" / f"{request_id}.json"
        path.write_text(json.dumps({
            "id": request_id,
            "created_at": created_at,
            "coordinator_task_id": "task-id",
            "worktree": "/data/tasks/coordinator/repo",
            "problem": "problem",
            "evidence": "evidence",
            "expected_outcome": "outcome",
            "security_constraints": "constraints",
        }))
        return path

    def test_success_uses_dedicated_thread_and_reviewed_approval(self) -> None:
        path = self.record("request-success")
        thread_id = self.seed_thread()
        completed = subprocess.CompletedProcess(
            [], 0, "KANDEV_SUPPORT_STATUS: RESOLVED\nsupport reply\n", ""
        )
        with mock.patch.object(worker.subprocess, "run", return_value=completed) as run:
            worker.process(path)
        command = run.call_args.args[0]
        self.assertEqual(
            command[:6],
            [
                worker.CODEX,
                "exec",
                "--approve-for-me",
                "--add-dir",
                str(worker.SOURCE_REPOSITORY),
                "resume",
            ],
        )
        self.assertEqual(command[6], thread_id)
        self.assertIn("Inspect both checkouts", command[7])
        self.assertIn("upstream/main is the canonical project base", command[7])
        self.assertIn("A yielded tool is not a completed tool", command[7])
        self.assertIn("kandev-safe-deploy", command[7])
        self.assertIn("Never call bare 'docker compose up'", command[7])
        self.assertIn("replacement must preserve all still-required fixes", command[7])
        self.assertEqual(run.call_args.kwargs["timeout"], worker.TURN_TIMEOUT_SECONDS)
        response = json.loads((worker.QUEUE / "responses/request-success.json").read_text())
        self.assertEqual(response["returncode"], 0)
        self.assertEqual(response["resolution_status"], "resolved")
        self.assertEqual(response["coordinator_notification"], "delivered")
        self.assertEqual(response["coordinator_message_id"], "message-id")

    def test_expired_thread_starts_fresh_and_persists_new_identity(self) -> None:
        path = self.record("request-rotated")
        self.seed_thread(created_at=100.0)
        new_thread_id = "00000000-0000-0000-0000-000000000002"
        completed = subprocess.CompletedProcess(
            [],
            0,
            "\n".join((
                json.dumps({"type": "thread.started", "thread_id": new_thread_id}),
                json.dumps({"type": "turn.started"}),
                json.dumps({
                    "type": "item.completed",
                    "item": {
                        "type": "agent_message",
                        "text": "KANDEV_SUPPORT_STATUS: RESOLVED\nrotated reply",
                    },
                }),
                json.dumps({"type": "turn.completed"}),
            )),
            "",
        )
        with (
            mock.patch.object(worker.time, "time", return_value=86500.0),
            mock.patch.object(worker.subprocess, "run", return_value=completed) as run,
        ):
            worker.process(path)

        command = run.call_args.args[0]
        self.assertEqual(command[:5], [
            worker.CODEX,
            "exec",
            "--approve-for-me",
            "--add-dir",
            str(worker.SOURCE_REPOSITORY),
        ])
        self.assertEqual(command[5], "--json")
        self.assertNotIn("resume", command)
        state = json.loads(worker.thread_state_path().read_text())
        self.assertEqual(state, {"thread_id": new_thread_id, "created_at": 86500.0})
        response = json.loads((worker.QUEUE / "responses/request-rotated.json").read_text())
        self.assertEqual(response["returncode"], 0)
        self.assertEqual(response["resolution_status"], "resolved")
        self.assertEqual(response["stdout"], "KANDEV_SUPPORT_STATUS: RESOLVED\nrotated reply")

    def test_missing_thread_state_starts_fresh(self) -> None:
        worker.thread_state_path().unlink()
        self.assertEqual(worker.reusable_thread_id(now=100.0), "")

    def test_future_thread_state_is_not_reused(self) -> None:
        self.seed_thread(created_at=101.0)
        self.assertEqual(worker.reusable_thread_id(now=100.0), "")

    def test_diagnosis_without_explicit_outcome_is_not_success(self) -> None:
        path = self.record("request-incomplete")
        completed = subprocess.CompletedProcess([], 0, "Try this command.\n", "")
        with mock.patch.object(worker.subprocess, "run", return_value=completed):
            worker.process(path)
        response = json.loads((worker.QUEUE / "responses/request-incomplete.json").read_text())
        self.assertEqual(response["returncode"], 70)
        self.assertEqual(response["resolution_status"], "invalid")
        self.assertIn("contract violation", response["stderr"])

    def test_explicit_blocker_is_automatically_escalated_before_terminal(self) -> None:
        path = self.record("request-blocked")
        completed = subprocess.CompletedProcess(
            [], 0, "KANDEV_SUPPORT_STATUS: BLOCKED\nNeeds external authority.\n", ""
        )
        with mock.patch.object(worker.subprocess, "run", return_value=completed):
            worker.process(path)
        self.assertFalse((worker.QUEUE / "responses/request-blocked.json").exists())
        pending_path = worker.QUEUE / "pending/request-blocked.json"
        pending = json.loads(pending_path.read_text())
        self.assertEqual(pending["_blocked_escalation_attempts"], 1)
        self.assertIn("Needs external authority", pending["_prior_blocked_response"])

        pending["_blocked_escalation_attempts"] = worker.MAX_BLOCKED_ESCALATIONS
        pending_path.write_text(json.dumps(pending))
        with mock.patch.object(worker.subprocess, "run", return_value=completed):
            worker.process(pending_path)
        response = json.loads((worker.QUEUE / "responses/request-blocked.json").read_text())
        self.assertEqual(response["returncode"], 75)
        self.assertEqual(response["resolution_status"], "blocked")

    def test_escalation_prompt_separates_agent_and_support_boundaries(self) -> None:
        path = self.record("request-escalated")
        record = json.loads(path.read_text())
        record["_blocked_escalation_attempts"] = 1
        record["_prior_blocked_response"] = "incorrectly blocked"
        rendered = worker.prompt(record)
        self.assertIn("does not prohibit this reviewed host Support worker", rendered)
        self.assertIn("AUTOMATIC ESCALATION PASS 1", rendered)

    def test_writer_conflict_is_requeued(self) -> None:
        path = self.record("request-busy")
        completed = subprocess.CompletedProcess([], 1, "", "already has an active writer")
        with mock.patch.object(worker.subprocess, "run", return_value=completed):
            worker.process(path)
        pending = json.loads((worker.QUEUE / "pending/request-busy.json").read_text())
        self.assertEqual(pending["_writer_conflict_attempts"], 1)
        self.assertFalse((worker.QUEUE / "responses/request-busy.json").exists())

    def test_restart_recovers_processing_and_queue_is_oldest_first(self) -> None:
        newer = self.record("newer", "2026-08-29T02:00:00Z")
        interrupted = self.record("older", "2026-08-29T01:00:00Z")
        interrupted.replace(worker.QUEUE / "processing/older.json")
        worker.recover_interrupted()
        self.assertEqual(
            [path.name for path in worker.pending_requests()],
            ["older.json", newer.name],
        )

    def test_failed_notification_is_persisted_and_retried(self) -> None:
        path = self.record("request-notify-retry")
        completed = subprocess.CompletedProcess(
            [], 0, "KANDEV_SUPPORT_STATUS: RESOLVED\nsupport reply\n", ""
        )
        self.notify_mock.side_effect = RuntimeError("backend unavailable")
        with mock.patch.object(worker.subprocess, "run", return_value=completed):
            worker.process(path)
        self.assertTrue((worker.QUEUE / "notifications/request-notify-retry.json").exists())
        response_path = worker.QUEUE / "responses/request-notify-retry.json"
        response = json.loads(response_path.read_text())
        self.assertEqual(response["coordinator_notification"], "failed")

        self.notify_mock.side_effect = None
        self.notify_mock.return_value = "retry-message-id"
        worker.retry_notifications(ignore_backoff=True)
        self.assertFalse((worker.QUEUE / "notifications/request-notify-retry.json").exists())
        response = json.loads(response_path.read_text())
        self.assertEqual(response["coordinator_notification"], "delivered")
        self.assertEqual(response["coordinator_message_id"], "retry-message-id")
        self.assertNotIn("notification_error", response)

    def test_notification_content_requires_coordinator_acceptance(self) -> None:
        content = worker.notification_content(
            {"id": "request-id"},
            {
                "resolution_status": "resolved",
                "stdout": "verified fix",
                "stderr": "",
            },
        )
        self.assertIn("delivered proactively", content)
        self.assertIn("run the requested acceptance check", content)

    def test_coordinator_session_returns_queue_incarnation(self) -> None:
        import sqlite3

        database = Path(self.temporary.name) / "kandev.db"
        connection = sqlite3.connect(database)
        self.addCleanup(connection.close)
        connection.execute(
            "CREATE TABLE task_sessions (id TEXT, task_id TEXT, state TEXT, "
            "queue_incarnation_id TEXT, is_primary INTEGER, updated_at TEXT)"
        )
        connection.execute(
            "INSERT INTO task_sessions VALUES (?,?,?,?,?,?)",
            ("session", "task-id", "WAITING_FOR_INPUT", "incarnation", 1, "2026-09-19"),
        )
        connection.commit()
        previous = worker.KANDEV_DB
        worker.KANDEV_DB = database
        self.addCleanup(setattr, worker, "KANDEV_DB", previous)

        self.assertEqual(
            worker.coordinator_session({"coordinator_task_id": "task-id"}),
            ("session", "WAITING_FOR_INPUT", "incarnation"),
        )

    def test_changed_deployment_is_not_accepted_before_http_200(self) -> None:
        self.postcondition.stop()
        before = {"container_id": "old-container", "image_id": "old-image", "started_at": "t0"}
        candidate = {"container_id": "new-container", "image_id": "new-image", "started_at": "t1"}
        restored = {"container_id": "rollback-container", "image_id": "old-image", "started_at": "t2"}
        response: dict[str, object] = {
            "returncode": 0,
            "resolution_status": "resolved",
            "stdout": "KANDEV_SUPPORT_STATUS: RESOLVED\n",
            "stderr": "",
        }
        restore = subprocess.CompletedProcess([], 0, "rollback verified", "")
        with (
            mock.patch.object(worker, "deployment_state", side_effect=[candidate, restored]),
            mock.patch.object(worker, "wait_for_kandev_http_200", return_value=False),
            mock.patch.object(worker, "kandev_http_200", return_value=True),
            mock.patch.object(worker.subprocess, "run", return_value=restore) as run,
        ):
            result = worker.enforce_deployment_postcondition(before, response)
        self.assertEqual(result["status"], "readiness_failed")
        self.assertEqual(result["rollback"], "verified")
        self.assertEqual(response["returncode"], 76)
        self.assertEqual(response["resolution_status"], "failed")
        self.assertIn("captured image was restored", response["stderr"])
        self.assertEqual(
            run.call_args.args[0],
            [str(worker.SAFE_DEPLOY), "--restore-image", "old-image"],
        )

    def test_changed_deployment_is_accepted_only_after_http_200(self) -> None:
        self.postcondition.stop()
        before = {"container_id": "old-container", "image_id": "old-image", "started_at": "t0"}
        candidate = {"container_id": "new-container", "image_id": "new-image", "started_at": "t1"}
        response: dict[str, object] = {"returncode": 0, "stdout": "", "stderr": ""}
        with (
            mock.patch.object(worker, "deployment_state", return_value=candidate),
            mock.patch.object(worker, "wait_for_kandev_http_200", return_value=True),
            mock.patch.object(worker.subprocess, "run") as run,
        ):
            result = worker.enforce_deployment_postcondition(before, response)
        self.assertEqual(result["status"], "ready")
        self.assertEqual(response["returncode"], 0)
        run.assert_not_called()

    def test_deployment_snapshot_is_persisted_before_support_turn(self) -> None:
        self.guard.stop()
        processing = worker.QUEUE / "processing/request.json"
        record: dict[str, object] = {"id": "request"}
        captured = {"container_id": "container", "image_id": "image", "started_at": "time"}
        with mock.patch.object(worker, "deployment_state", return_value=captured):
            self.assertEqual(worker.deployment_guard(record, processing), captured)
        persisted = json.loads(processing.read_text())
        self.assertEqual(persisted["_deployment_guard"], captured)


if __name__ == "__main__":
    unittest.main()
