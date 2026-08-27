#!/usr/bin/env python3
"""Focused unit tests for the task-scoped Docker broker policy."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile


BROKER_PATH = Path(__file__).resolve().parents[1] / "scripts" / "kandev-agent-docker-broker"
loader = importlib.machinery.SourceFileLoader("kandev_agent_docker_broker", str(BROKER_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None
broker = importlib.util.module_from_spec(spec)
loader.exec_module(broker)


def expect_denied(function, message: str) -> None:
    try:
        function()
    except broker.BrokerError:
        return
    raise AssertionError(message)


def main() -> None:
    with tempfile.TemporaryDirectory(prefix="kandev-broker-test-") as temporary:
        base = Path(temporary).resolve()
        task_root = base / "task"
        repository = task_root / "repo"
        repository.mkdir(parents=True)
        outside = base / "outside"
        outside.mkdir()
        os.environ["KANDEV_HOST_CODE_DIR"] = str(base)
        project = broker.project_name(task_root)

        model = {
            "name": project,
            "services": {
                "app": {
                    "image": "alpine:latest",
                    "volumes": [
                        {
                            "type": "bind",
                            "source": str(repository),
                            "target": "/workspace",
                            "read_only": False,
                        },
                        {"type": "volume", "source": "state", "target": "/state"},
                    ],
                }
            },
            "volumes": {"state": {"name": f"{project}_state"}},
            "networks": {"default": {"name": f"{project}_default"}},
        }
        sanitized = broker.validate_model(
            json.loads(json.dumps(model)), repository, task_root, task_root, project
        )
        bind = sanitized["services"]["app"]["volumes"][0]
        assert bind["read_only"] is True
        assert bind["source"] == str(repository)

        build_model = json.loads(json.dumps(model))
        dockerfile = repository / "Containerfile"
        dockerfile.touch()
        build_model["services"]["app"]["build"] = {
            "context": str(repository),
            "dockerfile": "Containerfile",
        }
        build_model["services"]["app"]["image"] = "production-app:latest"
        sanitized_build = broker.validate_model(
            build_model, repository, task_root, task_root, project
        )
        assert sanitized_build["services"]["app"]["image"] == f"{project}_app:latest"
        assert sanitized_build["services"]["app"]["build"]["context"] == str(repository)
        assert sanitized_build["services"]["app"]["build"]["dockerfile"] == str(dockerfile)

        config_file = repository / "app.conf"
        config_file.touch()
        config_model = json.loads(json.dumps(model))
        config_model["configs"] = {"app": {"file": str(config_file)}}
        sanitized_config = broker.validate_model(
            config_model, repository, task_root, task_root, project
        )
        assert sanitized_config["configs"]["app"]["file"] == str(config_file)

        outside_model = json.loads(json.dumps(model))
        outside_model["services"]["app"]["volumes"][0]["source"] = str(outside)
        expect_denied(
            lambda: broker.validate_model(outside_model, repository, task_root, task_root, project),
            "outside bind mount was accepted",
        )

        privileged_model = json.loads(json.dumps(model))
        privileged_model["services"]["app"]["privileged"] = True
        expect_denied(
            lambda: broker.validate_model(privileged_model, repository, task_root, task_root, project),
            "privileged service was accepted",
        )

        external_model = json.loads(json.dumps(model))
        external_model["volumes"]["state"] = {"external": True, "name": "production"}
        expect_denied(
            lambda: broker.validate_model(external_model, repository, task_root, task_root, project),
            "external volume was accepted",
        )

        expect_denied(
            lambda: broker.split_compose_args(
                ["compose", "--project-name", "escape", "up"], repository, task_root
            ),
            "agent-selected project name was accepted",
        )
        expect_denied(
            lambda: broker.split_compose_args(
                ["compose", "run", "-v/tmp:/host", "app"], repository, task_root
            ),
            "extra Compose run bind was accepted",
        )
        expect_denied(
            lambda: broker.split_compose_args(
                ["compose", "down", "--rmi", "all"], repository, task_root
            ),
            "Compose image deletion was accepted",
        )

        key = b"test-key"
        token = broker.expected_token(key, task_root)
        assert token != broker.expected_token(key, outside)

        metadata = base / "kandev.db"
        with sqlite3.connect(metadata) as database:
            database.executescript(
                """
                CREATE TABLE workspaces (id TEXT PRIMARY KEY, name TEXT NOT NULL);
                CREATE TABLE tasks (
                    id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, archived_at TEXT
                );
                CREATE TABLE task_environments (
                    task_id TEXT NOT NULL, workspace_path TEXT, task_dir_name TEXT
                );
                CREATE TABLE repositories (
                    id TEXT PRIMARY KEY, workspace_id TEXT NOT NULL, local_path TEXT,
                    deleted_at TEXT
                );
                CREATE TABLE task_repositories (task_id TEXT, repository_id TEXT);
                """
            )
            database.executemany(
                "INSERT INTO workspaces(id, name) VALUES (?, ?)",
                (("ws-one", "Workspace One"), ("ws-two", "Workspace Two")),
            )
            database.executemany(
                "INSERT INTO tasks(id, workspace_id, archived_at) VALUES (?, ?, NULL)",
                (
                    ("11111111-1111-1111-1111-111111111111", "ws-one"),
                    ("22222222-2222-2222-2222-222222222222", "ws-one"),
                    ("33333333-3333-3333-3333-333333333333", "ws-one"),
                ),
            )
            database.executemany(
                "INSERT INTO task_environments(task_id, workspace_path, task_dir_name) "
                "VALUES (?, ?, ?)",
                (
                    (
                        "11111111-1111-1111-1111-111111111111",
                        "/data/tasks/coord-task/coordinator",
                        "coord-task",
                    ),
                    (
                        "22222222-2222-2222-2222-222222222222",
                        "/data/tasks/ordinary-task/app",
                        "ordinary-task",
                    ),
                    (
                        "33333333-3333-3333-3333-333333333333",
                        "/data/tasks/target-task/app",
                        "target-task",
                    ),
                ),
            )
            database.executemany(
                "INSERT INTO repositories(id, workspace_id, local_path, deleted_at) "
                "VALUES (?, ?, ?, NULL)",
                (
                    ("coordinator", "ws-one", "/data/home/Code/coordinator"),
                    ("app-one", "ws-one", "/data/home/Code/app"),
                    ("app-two", "ws-two", "/data/home/Code/other"),
                ),
            )
            database.executemany(
                "INSERT INTO task_repositories(task_id, repository_id) VALUES (?, ?)",
                (
                    ("11111111-1111-1111-1111-111111111111", "coordinator"),
                    ("22222222-2222-2222-2222-222222222222", "app-one"),
                    ("33333333-3333-3333-3333-333333333333", "app-one"),
                ),
            )

        broker.KANDEV_DB = metadata
        data_root = base / "data"
        (data_root / "tasks" / "target-task").mkdir(parents=True)
        os.environ["KANDEV_HOST_DATA_DIR"] = str(data_root)

        coordinator = broker.coordinator_context(Path("/data/tasks/coord-task"))
        assert coordinator["task_id"] == "11111111-1111-1111-1111-111111111111"
        assert coordinator["workspace_id"] == "ws-one"
        expect_denied(
            lambda: broker.coordinator_context(Path("/data/tasks/ordinary-task")),
            "ordinary task received coordinator source authority",
        )
        expect_denied(
            lambda: broker.coordinator_context(Path("/data/home/Code/coordinator")),
            "unidentified shared coordinator checkout received source authority",
        )

        same_workspace_info = {
            "Config": {
                "Labels": {
                    "com.docker.compose.project.working_dir": str(base / "app")
                }
            }
        }
        other_workspace_info = {
            "Config": {
                "Labels": {
                    "com.docker.compose.project.working_dir": str(base / "other")
                }
            }
        }
        assert "ws-one" in broker.container_workspace_ids(same_workspace_info)
        assert "ws-one" not in broker.container_workspace_ids(other_workspace_info)

        destination, container_destination = broker.target_task_inbox(
            "33333333-3333-3333-3333-333333333333", "ws-one", "source.sql"
        )
        assert destination.parent.name == ".kandev-coordinator-inbox"
        assert container_destination == (
            "/data/tasks/target-task/.kandev-coordinator-inbox/source.sql"
        )
        expect_denied(
            lambda: broker.target_task_inbox(
                "33333333-3333-3333-3333-333333333333", "ws-two", "source.sql"
            ),
            "cross-workspace target task was accepted",
        )

        dump_args, dump_environment = broker.database_export_command(
            {
                "Config": {
                    "Image": "mariadb:12",
                    "Env": [
                        "MARIADB_DATABASE=application",
                        "MARIADB_USER=reader",
                        "MARIADB_PASSWORD=super-secret",
                    ],
                },
                "NetworkSettings": {
                    "Networks": {"default": {"IPAddress": "172.20.0.5"}}
                },
            }
        )
        assert dump_environment == {"MYSQL_PWD": "super-secret"}
        assert all("super-secret" not in argument for argument in dump_args)
        assert broker.redact_logs("password=visible token:abc") == (
            "password=<redacted> token:<redacted>"
        )

        exported = base / "bounded-export.sql"
        code, stderr, size, checksum = broker.run_bounded_export(
            ["/usr/bin/printf", "SELECT 1;\n"], {}, exported
        )
        assert code == 0 and stderr == ""
        assert size == len(b"SELECT 1;\n")
        assert checksum == broker.hashlib.sha256(b"SELECT 1;\n").hexdigest()
        assert exported.read_bytes() == b"SELECT 1;\n"

    print("PASS: task Docker broker policy tests")


if __name__ == "__main__":
    main()
