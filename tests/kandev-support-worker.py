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
        worker.THREAD_ID = "00000000-0000-0000-0000-000000000001"
        worker.SOURCE_REPOSITORY = Path("/home/test/Code/kandev-source")
        self.notify = mock.patch.object(worker, "notify_coordinator")
        self.notify_mock = self.notify.start()
        self.notify_mock.return_value = "message-id"
        self.addCleanup(self.notify.stop)
        for directory in ("pending", "processing", "records", "responses", "notifications"):
            (worker.QUEUE / directory).mkdir()

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
        self.assertEqual(command[6], worker.THREAD_ID)
        self.assertIn("Inspect both checkouts", command[7])
        response = json.loads((worker.QUEUE / "responses/request-success.json").read_text())
        self.assertEqual(response["returncode"], 0)
        self.assertEqual(response["resolution_status"], "resolved")
        self.assertEqual(response["coordinator_notification"], "delivered")
        self.assertEqual(response["coordinator_message_id"], "message-id")

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


if __name__ == "__main__":
    unittest.main()
