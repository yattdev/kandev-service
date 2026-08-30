#!/usr/bin/env python3
"""Unit coverage for the root-only Support process cleanup predicate gate."""

from __future__ import annotations

import importlib.util
from importlib.machinery import SourceFileLoader
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest import mock


SCRIPT = Path(__file__).parents[1] / "scripts" / "kandev-support-process-cleanup"
SPEC = importlib.util.spec_from_loader("cleanup", SourceFileLoader("cleanup", str(SCRIPT)))
assert SPEC and SPEC.loader
cleanup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cleanup)

WORKSPACE = "11111111-1111-1111-1111-111111111111"
COORDINATOR = "22222222-2222-2222-2222-222222222222"
TASK = "33333333-3333-3333-3333-333333333333"


class CleanupTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.proc = base / "proc"
        self.proc.mkdir()
        self.root = base / "data/tasks/task-dir"
        (self.root / "repo").mkdir(parents=True)
        self.db = base / "db.sqlite"
        database = sqlite3.connect(self.db)
        database.executescript("CREATE TABLE tasks(id TEXT, workspace_id TEXT, archived_at TEXT); CREATE TABLE task_environments(task_id TEXT, task_dir_name TEXT);")
        database.execute("INSERT INTO tasks VALUES (?, ?, NULL)", (COORDINATOR, WORKSPACE))
        database.execute("INSERT INTO tasks VALUES (?, ?, NULL)", (TASK, WORKSPACE))
        database.execute("INSERT INTO task_environments VALUES (?, ?)", (TASK, "task-dir"))
        database.commit()
        database.close()
        self.config = {"data_dir": str(base / "data"), "db_path": str(self.db), "audit_path": str(base / "audit.jsonl")}
        self.previous_proc = cleanup.PROC_ROOT
        cleanup.PROC_ROOT = self.proc
        self.addCleanup(setattr, cleanup, "PROC_ROOT", self.previous_proc)

    def proc_entry(self, pid: int, ppid: int, pgid: int, sid: int) -> None:
        entry = self.proc / str(pid)
        entry.mkdir()
        (entry / "stat").write_text(f"{pid} (service) S {ppid} {pgid} {sid} 0 0 0 0 0\n")
        (entry / "cwd").symlink_to(self.root / "repo")

    def request(self) -> dict:
        return {"coordinator_task_id": COORDINATOR, "workspace_id": WORKSPACE, "task_id": TASK, "signal": "SIGKILL", "targets": [{"pid": 101, "ppid": 99, "pgid": 101, "sid": 98, "members": [101]}], "protected": [{"pid": 500, "pgid": 500, "sid": 500}]}

    def test_kills_only_validated_group_and_audits(self) -> None:
        self.proc_entry(101, 99, 101, 98)
        self.proc_entry(99, 1, 99, 98)
        self.proc_entry(500, 1, 500, 500)
        with mock.patch.object(cleanup.os, "killpg") as kill, mock.patch.object(cleanup.time, "sleep"), mock.patch.object(cleanup.Path, "exists", return_value=False):
            result = cleanup.perform(self.request(), self.config)
        kill.assert_called_once_with(101, cleanup.signal.SIGKILL)
        self.assertTrue(result["ok"])
        self.assertEqual(result["protected"], [500])
        self.assertIn('"ok": true', Path(self.config["audit_path"]).read_text())

    def test_rejects_out_of_root_member_before_signal(self) -> None:
        self.proc_entry(101, 99, 101, 98)
        self.proc_entry(99, 1, 99, 98)
        self.proc_entry(500, 1, 500, 500)
        (self.proc / "101" / "cwd").unlink()
        (self.proc / "101" / "cwd").symlink_to(Path(self.temp.name))
        with mock.patch.object(cleanup.os, "killpg") as kill:
            with self.assertRaisesRegex(cleanup.CleanupError, "outside its task root"):
                cleanup.perform(self.request(), self.config)
        kill.assert_not_called()

    def test_rejects_group_membership_drift_before_signal(self) -> None:
        self.proc_entry(101, 99, 101, 98)
        self.proc_entry(102, 99, 101, 98)
        self.proc_entry(99, 1, 99, 98)
        self.proc_entry(500, 1, 500, 500)
        with mock.patch.object(cleanup.os, "killpg") as kill:
            with self.assertRaisesRegex(cleanup.CleanupError, "membership changed"):
                cleanup.perform(self.request(), self.config)
        kill.assert_not_called()


if __name__ == "__main__":
    unittest.main()
