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
        for directory in ("pending", "processing", "records", "responses"):
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
        completed = subprocess.CompletedProcess([], 0, "support reply\n", "")
        with mock.patch.object(worker.subprocess, "run", return_value=completed) as run:
            worker.process(path)
        command = run.call_args.args[0]
        self.assertEqual(command[:4], [worker.CODEX, "exec", "--approve-for-me", "resume"])
        self.assertEqual(command[4], worker.THREAD_ID)
        response = json.loads((worker.QUEUE / "responses/request-success.json").read_text())
        self.assertEqual(response["returncode"], 0)
        self.assertEqual(response["stdout"], "support reply\n")

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


if __name__ == "__main__":
    unittest.main()
