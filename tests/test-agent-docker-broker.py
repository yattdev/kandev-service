#!/usr/bin/env python3
"""Focused unit tests for the task-scoped Docker broker policy."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import hashlib
import ipaddress
import json
import os
from contextlib import contextmanager
from pathlib import Path
import sqlite3
import tempfile
import io
import struct
import time


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
        assert bind["read_only"] is False
        assert bind["source"] == str(repository)

        read_only_model = json.loads(json.dumps(model))
        read_only_model["services"]["app"]["volumes"][0]["read_only"] = True
        sanitized_read_only = broker.validate_model(
            read_only_model, repository, task_root, task_root, project
        )
        assert sanitized_read_only["services"]["app"]["volumes"][0]["read_only"] is True

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
        build_model["services"]["app"]["image"] = f"{project}_app:qa-8bf9"
        pinned_build = broker.validate_model(
            build_model, repository, task_root, task_root, project
        )
        assert pinned_build["services"]["app"]["image"] == f"{project}_app:qa-8bf9"
        build_model["services"]["app"]["image"] = f"{project}_app:bad/tag"
        assert broker.validate_model(
            build_model, repository, task_root, task_root, project
        )["services"]["app"]["image"] == f"{project}_app:latest"

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

        spoofed_instance_model = json.loads(json.dumps(model))
        spoofed_instance_model["services"]["app"]["labels"] = {
            "kandev.instance_id": "another-task-execution"
        }
        expect_denied(
            lambda: broker.validate_model(
                spoofed_instance_model, repository, task_root, task_root, project
            ),
            "agent-selected Kandev execution identity was accepted",
        )

        external_model = json.loads(json.dumps(model))
        external_model["volumes"]["state"] = {"external": True, "name": "production"}
        expect_denied(
            lambda: broker.validate_model(external_model, repository, task_root, task_root, project),
            "external volume was accepted",
        )

        named_globals, named_command, _ = broker.split_compose_args(
            ["compose", "--project-name", "escape", "up"], repository, task_root
        )
        _, named_environment = broker.compose_project_options(named_globals, {})
        assert named_command == "up"
        assert named_environment == {"COMPOSE_PROJECT_NAME": "escape"}
        assert broker.scoped_project_name(task_root, named_environment, repository).startswith("kd_")
        assert broker.scoped_project_name(task_root, named_environment, repository) != "escape"
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

        # A global dry-run flag must survive saved-model replay. Compose also
        # accepts the same flag after `down`; retain that legal position, while
        # rejecting value-bearing lookalikes before any daemon invocation.
        model_file = base / "saved-model.json"
        before_globals, before_command, before_args = broker.split_compose_args(
            ["compose", "--dry-run", "down"], repository, task_root
        )
        global_dry_run = broker.compose_replay_command(
            project, model_file, before_globals, before_command, before_args
        )
        assert global_dry_run == [
            broker.DOCKER_BIN,
            "compose",
            "--project-name",
            project,
            "-f",
            str(model_file),
            "--dry-run",
            "down",
        ]
        after_globals, after_command, after_args = broker.split_compose_args(
            ["compose", "down", "--dry-run"], repository, task_root
        )
        command_dry_run = broker.compose_replay_command(
            project, model_file, after_globals, after_command, after_args
        )
        assert command_dry_run[-2:] == ["down", "--dry-run"]
        profile_dry_run = broker.compose_replay_command(
            project,
            model_file,
            ["--profile", "qa", "--dry-run", "--file", "compose.yml"],
            "down",
            [],
        )
        assert profile_dry_run[-4:] == ["--profile", "qa", "--dry-run", "down"]
        assert "--file" not in profile_dry_run[:-1]
        assert broker.compose_replay_command(
            project, model_file, [], "ps", ["--all"]
        )[-2:] == ["ps", "--all"]
        expect_denied(
            lambda: broker.split_compose_args(
                ["compose", "--dry-run=true", "down"], repository, task_root
            ),
            "value-bearing global dry-run was accepted",
        )
        expect_denied(
            lambda: broker.split_compose_args(
                ["compose", "down", "--dry-run=false"], repository, task_root
            ),
            "value-bearing command dry-run was accepted",
        )
        daemon_calls: list[list[str]] = []
        original_run_command = broker.run_command

        def reject_daemon_call(args, *unused_args, **unused_kwargs):
            daemon_calls.append(args)
            raise AssertionError("malformed dry-run reached daemon execution")

        broker.run_command = reject_daemon_call
        malformed_request = {
            "task_root": str(task_root),
            "cwd": str(repository),
            "token": broker.expected_token(b"dry-run-test-key", task_root),
        }
        try:
            for malformed_args in (
                ["compose", "--dry-run=false", "down"],
                ["compose", "down", "--dry-run=nope"],
            ):
                expect_denied(
                    lambda malformed_args=malformed_args: broker.handle_request(
                        {**malformed_request, "args": malformed_args}, b"dry-run-test-key"
                    ),
                    "malformed dry-run reached request execution",
                )
        finally:
            broker.run_command = original_run_command
        assert daemon_calls == []

        assert broker.compose_environment(
            {"COMPOSE_PROJECT_NAME": "task_8402", "DB_PORT": "13306", "WEB_PORT": "18080"}
        ) == {"COMPOSE_PROJECT_NAME": "task_8402", "DB_PORT": "13306", "WEB_PORT": "18080"}
        expect_denied(
            lambda: broker.compose_environment({"UNRELATED_SECRET": "nope"}),
            "unrelated environment key was accepted",
        )
        expect_denied(
            lambda: broker.compose_environment({"DB_PORT": "70000"}),
            "out-of-range Compose port was accepted",
        )

        # A disposable clone may select its own guarded kd_ project, but that
        # project is bound to both the task root and clone before existing or
        # destructive operations can use it.  The registered main clone's
        # saved model cannot be reused from a sibling clone.
        original_model_dir = broker.MODEL_DIR
        original_compose_audit = broker.COMPOSE_AUDIT_LOG
        broker.MODEL_DIR = base / "models"
        broker.COMPOSE_AUDIT_LOG = base / "compose-audit.jsonl"
        disposable_project = "kd_task8402_qa5db6"
        assert broker.scoped_project_name(
            task_root, {"COMPOSE_PROJECT_NAME": disposable_project}
        ) == disposable_project
        alias = {"COMPOSE_PROJECT_NAME": "performcoop"}
        assert broker.scoped_project_name(task_root, alias, repository) != "performcoop"
        assert broker.scoped_project_name(task_root, alias, repository) != broker.scoped_project_name(outside, alias, outside)
        owned_model = {"name": disposable_project, "services": {"probe": {"image": "alpine"}}}
        broker.save_scoped_model(task_root, repository, disposable_project, owned_model)
        assert broker.load_scoped_model(task_root, repository, disposable_project) == owned_model
        expect_denied(
            lambda: broker.save_scoped_model(outside, repository, disposable_project, owned_model),
            "another task was able to claim the disposable project",
        )
        sibling_clone = task_root / "qa-clean"
        sibling_clone.mkdir()
        assert broker.scoped_project_name(task_root, {}, repository) != broker.scoped_project_name(task_root, {}, sibling_clone)
        legacy_model = {"services": {"probe": {"image": "alpine"}}}
        broker.save_scoped_model(task_root, repository, project, legacy_model)
        assert broker.scoped_project_name(task_root, {}, repository) == project
        assert broker.scoped_project_name(task_root, {}, sibling_clone) != project
        try:
            broker.destructive_model_preflight(
                task_root, sibling_clone, disposable_project, disposable_project, "down"
            )
        except broker.ComposeAuditError as exc:
            denied_audit_id = exc.audit_id
            assert exc.project == disposable_project
        else:
            raise AssertionError("sibling clone destructive request was accepted")
        expect_denied(
            lambda: broker.load_scoped_model(outside, repository, disposable_project),
            "saved model was reusable by another task root",
        )
        allowed_model, allowed_audit_id = broker.destructive_model_preflight(
            task_root, repository, disposable_project, disposable_project, "down"
        )
        assert allowed_model == owned_model
        lines = [json.loads(line) for line in broker.COMPOSE_AUDIT_LOG.read_text().splitlines()]
        denied = next(event for event in lines if event["audit_id"] == denied_audit_id)
        allowed = next(event for event in lines if event["audit_id"] == allowed_audit_id)
        assert denied["ownership_decision"] == "deny"
        assert denied["result"] == "denied"
        assert denied["requested_project"] == disposable_project
        assert denied["resolved_project"] == disposable_project
        assert denied["canonical_project_directory"] == str(sibling_clone)
        assert denied["authenticated_task_scope"] == str(task_root)
        assert allowed["ownership_decision"] == "allow"
        assert allowed["result"] == "preflight"
        assert allowed["command_class"] == "destructive"
        assert "args" not in allowed and "environment" not in allowed

        # A one-off may be removed only by its exact name after both the saved
        # clone claim and Docker's immutable container labels have been checked.
        oneoff_name = f"{disposable_project}-probe-run-deadbeef1234"
        oneoff_id = "b" * 64
        oneoff_info = {
            "Id": oneoff_id, "Name": "/" + oneoff_name,
            "State": {"Status": "running"},
            "Config": {"Labels": {
                "com.docker.compose.project": disposable_project,
                "com.docker.compose.service": "probe",
                "com.docker.compose.oneoff": "True",
                "com.docker.compose.project.working_dir": str(repository),
            }},
        }
        oneoff_calls = []
        original_oneoff_run = broker.run_command
        original_translate = broker.translate_to_host
        broker.translate_to_host = lambda path: path

        def fake_oneoff_run(args, cwd, *unused, **unused_kwargs):
            oneoff_calls.append(args)
            if args[1:3] == ["inspect", "--type"]:
                return 0, json.dumps([oneoff_info]), ""
            if args[1:4] == ["container", "rm", "--force"]:
                return 0, oneoff_id + "\n", ""
            raise AssertionError(f"unexpected oneoff command: {args}")

        broker.run_command = fake_oneoff_run
        oneoff_args = ["kandev", "oneoff", "inspect", oneoff_name]
        oneoff_env = {"COMPOSE_PROJECT_NAME": disposable_project}
        try:
            inspected = broker.handle_oneoff(task_root, repository, oneoff_args, oneoff_env)
            assert json.loads(inspected["stdout"])["status"] == "running"
            assert len(oneoff_calls) == 1
            expect_denied(
                lambda: broker.handle_oneoff(task_root, sibling_clone, oneoff_args, oneoff_env),
                "sibling clone inspected another clone's oneoff",
            )
            expect_denied(
                lambda: broker.handle_oneoff(outside, repository, oneoff_args, oneoff_env),
                "different task inspected another task's oneoff",
            )
            oneoff_info["Config"]["Labels"]["com.docker.compose.oneoff"] = "False"
            expect_denied(
                lambda: broker.handle_oneoff(task_root, repository,
                    ["kandev", "oneoff", "remove", oneoff_name], oneoff_env),
                "ordinary service was removed as a oneoff",
            )
            oneoff_info["Config"]["Labels"]["com.docker.compose.oneoff"] = "True"
            removed = broker.handle_oneoff(task_root, repository,
                ["kandev", "oneoff", "remove", oneoff_name], oneoff_env)
            assert json.loads(removed["stdout"])["status"] == "removed"
            assert oneoff_calls[-1] == [broker.DOCKER_BIN, "container", "rm", "--force", oneoff_id]
            assert removed["audit_id"]
            removal_events = [json.loads(line) for line in broker.COMPOSE_AUDIT_LOG.read_text().splitlines()
                              if "oneoff remove" in line]
            assert [event["result"] for event in removal_events] == ["preflight", "ok"]
        finally:
            broker.run_command = original_oneoff_run
            broker.translate_to_host = original_translate

        # Network admission is bound to the saved task/clone project. The
        # broker skips a host route, creates only this project's default bridge,
        # and returns its own verified ID on an idempotent retry.
        reservation_model = {
            "name": disposable_project,
            "services": {"db": {"image": "alpine:latest"}},
            "networks": {"default": {"name": f"{disposable_project}_default", "ipam": {}}},
        }
        broker.save_scoped_model(task_root, repository, disposable_project, reservation_model)
        original_routes = broker.host_ipv4_routes
        original_network_run = broker.run_command
        broker.host_ipv4_routes = lambda: [ipaddress.IPv4Network("198.18.0.0/24")]
        network_id = "a" * 64
        network_name = f"{disposable_project}_default"
        created = False
        create_calls = []

        def fake_network_run(args, cwd, *unused, **unused_kwargs):
            nonlocal created
            if args[1:3] == ["network", "inspect"]:
                if not created:
                    return 1, "", f"No such network: {network_name}"
                return 0, json.dumps([{
                    "Id": network_id, "Name": network_name,
                    "Labels": {
                        "com.docker.compose.project": disposable_project,
                        "com.docker.compose.network": "default",
                        "kandev.agent.task_digest": hashlib.sha256(str(task_root).encode()).hexdigest(),
                    },
                    "IPAM": {"Config": [{"Subnet": "198.18.1.0/24"}]},
                }]), ""
            if args[1:3] == ["network", "create"]:
                create_calls.append(args)
                assert args[args.index("--subnet") + 1] == "198.18.1.0/24"
                assert args[-1] == network_name
                created = True
                return 0, network_id, ""
            raise AssertionError(f"unexpected Docker command: {args}")

        broker.run_command = fake_network_run
        try:
            first = broker.handle_network_reserve(
                task_root, repository, ["kandev", "network", "reserve"],
                {"COMPOSE_PROJECT_NAME": disposable_project},
            )
            assert first["returncode"] == 0
            assert json.loads(first["stdout"]) == {
                "project": disposable_project, "network": network_name,
                "network_id": network_id, "subnet": "198.18.1.0/24", "existing": False,
            }
            second = broker.handle_network_reserve(
                task_root, repository, ["kandev", "network", "reserve"],
                {"COMPOSE_PROJECT_NAME": disposable_project},
            )
            assert json.loads(second["stdout"])["existing"] is True
            assert len(create_calls) == 1
            inspected = broker.inspect_owned_network(network_name)
            assert inspected is not None
            inspected["Containers"] = {"foreign-consumer": {}}
            original_inspect_owned = broker.inspect_owned_network
            broker.inspect_owned_network = lambda unused_name: inspected
            try:
                expect_denied(
                    lambda: broker.handle_network_reserve(
                        task_root, repository, ["kandev", "network", "reserve"],
                        {"COMPOSE_PROJECT_NAME": disposable_project},
                    ),
                    "occupied network was reused by reservation",
                )
            finally:
                broker.inspect_owned_network = original_inspect_owned
            expect_denied(
                lambda: broker.handle_network_reserve(
                    outside, repository, ["kandev", "network", "reserve"],
                    {"COMPOSE_PROJECT_NAME": disposable_project},
                ),
                "another task reserved an existing project network",
            )
            reservation_model["networks"]["default"]["ipam"] = {
                "config": [{"subnet": "198.18.9.0/24"}]}
            broker.save_scoped_model(task_root, repository, disposable_project, reservation_model)
            expect_denied(
                lambda: broker.handle_network_reserve(
                    task_root, repository, ["kandev", "network", "reserve"],
                    {"COMPOSE_PROJECT_NAME": disposable_project},
                ),
                "agent-selected IPAM entered guarded network reservation",
            )
        finally:
            broker.host_ipv4_routes = original_routes
            broker.run_command = original_network_run
        broker.MODEL_DIR = original_model_dir
        broker.COMPOSE_AUDIT_LOG = original_compose_audit

        observed_environment: dict[str, str] | None = None
        original_run_command = broker.run_command

        def fake_run_command(args, cwd, timeout=broker.COMMAND_TIMEOUT, environment_overrides=None):
            nonlocal observed_environment
            observed_environment = environment_overrides
            return 0, json.dumps({"services": {"app": {"image": "alpine:latest"}}}), ""

        broker.run_command = fake_run_command
        try:
            broker.compose_config(
                repository,
                project,
                [],
                {"COMPOSE_PROJECT_NAME": "task_8402", "DB_PORT": "13306", "WEB_PORT": "18080"},
            )
        finally:
            broker.run_command = original_run_command
        assert observed_environment == {
            "COMPOSE_PROJECT_NAME": project,
            "DB_PORT": "13306",
            "WEB_PORT": "18080",
        }

        # The host broker must preserve binary redirected stdin and must fail
        # closed for an incomplete framed stream rather than treating it as an
        # empty successful import.
        empty = struct.pack("!I", 0)
        code, stdout, stderr = broker.run_command(
            ["/bin/sh", "-c", "wc -c"], repository,
            stdin_stream=broker.FramedInput(io.BytesIO(empty)),
        )
        assert code == 0 and stdout.strip() == "0" and not stderr

        binary = b"\x00broker-stdin\xff" * (4 * 1024 * 1024 // len(b"\x00broker-stdin\xff"))
        framed_parts = []
        for offset in range(0, len(binary), 1024 * 1024):
            chunk = binary[offset : offset + 1024 * 1024]
            framed_parts.extend((struct.pack("!I", len(chunk)), chunk))
        framed_parts.append(struct.pack("!I", 0))
        framed = b"".join(framed_parts)
        code, stdout, stderr = broker.run_command(
            ["/bin/sh", "-c", "sha256sum | awk '{print $1}'"], repository,
            stdin_stream=broker.FramedInput(io.BytesIO(framed)),
        )
        assert code == 0 and stdout.strip() == hashlib.sha256(binary).hexdigest() and not stderr
        code, _stdout, _stderr = broker.run_command(
            ["/bin/sh", "-c", "head -c 1 >/dev/null; exit 7"], repository,
            stdin_stream=broker.FramedInput(io.BytesIO(framed)),
        )
        assert code == 7, "an early input consumer exit must not become success"
        class SlowInput(io.BytesIO):
            def read(self, size=-1):
                time.sleep(0.4)
                return super().read(size)

        # An early child exit used to close the broker socket after a fixed
        # five-second feeder join, before a finite producer finished sending.
        slow_payload = binary[:1024 * 1024]
        slow_framed = struct.pack("!I", len(slow_payload)) + slow_payload + empty
        code, _stdout, stderr = broker.run_command(
            ["/bin/sh", "-c", "head -c 1 >/dev/null; echo child-exit >&2; exit 7"],
            repository,
            stdin_stream=broker.FramedInput(SlowInput(slow_framed)),
        )
        assert code == 7 and "child-exit" in stderr and "stdin transport failed" not in stderr
        code, _stdout, stderr = broker.run_command(
            ["/bin/sh", "-c", "cat"], repository,
            stdin_stream=broker.FramedInput(io.BytesIO(struct.pack("!I", 8) + b"short")),
        )
        assert code == 78 and "stdin transport failed" in stderr

        ports_model = json.loads(json.dumps(model))
        ports_model["services"]["app"]["ports"] = [
            {"target": 3306, "published": "53306", "host_ip": "127.0.0.1"},
            {"target": 8080, "published": "60003", "host_ip": "0.0.0.0"},
        ]
        assert broker.validate_model(ports_model, repository, task_root, task_root, project)["services"]["app"]["ports"] == ports_model["services"]["app"]["ports"]
        # A service-only recreate must use its explicit overlay even when an
        # earlier command saved a different model for the same project.
        original_model_dir = broker.MODEL_DIR
        broker.MODEL_DIR = base / "force-recreate-models"
        try:
            broker.save_scoped_model(task_root, repository, project, ports_model)
            assert broker.model_path(task_root, project).exists()
            runtime = task_root / ".kandev-runtime"
            runtime.mkdir()
            compose_file = repository / "docker-compose.yml"
            compose_file.touch()
            project_directory = broker.compose_project_directory(
                runtime, task_root, ["--file", "../repo/docker-compose.yml"]
            )
            assert project_directory == repository
            # A post-restart broker must load the original clone's persisted
            # model when a sibling runtime wrapper names that Compose file.
            assert broker.load_scoped_model(task_root, project_directory, project) == ports_model
            sibling = task_root / "sibling"
            sibling.mkdir()
            sibling_file = sibling / "docker-compose.yml"
            sibling_file.touch()
            expect_denied(
                lambda: broker.load_scoped_model(task_root, sibling, project),
                "a sibling clone reused the persisted project model",
            )

            overlay_model = {
                "services": {
                    "db": {"image": "mariadb:12.3.3"},
                    "web": {
                        "image": "alpine:latest",
                        "command": ["sh", "-c", "echo overlay"],
                        "depends_on": {"db": {"condition": "service_started"}},
                    },
                },
            }
            original_compose_config = broker.compose_config
            calls: list[list[str]] = []

            def overlay_config(_cwd, _project, global_args, _environment):
                calls.append(global_args)
                return overlay_model

            broker.compose_config = overlay_config
            files = ["-f", str(compose_file), "-f", str(repository / "overlay.yml")]
            try:
                expect_denied(
                    lambda: broker.render_model_for_command(
                        task_root, repository, repository, task_root, project,
                        files, "up", ["-d", "--force-recreate", "web"], {},
                    ),
                    "dependent service recreation without --no-deps was accepted",
                )
                assert broker.load_scoped_model(task_root, repository, project) == ports_model
                rendered = broker.render_model_for_command(
                    task_root, repository, repository, task_root, project,
                    files, "up", ["-d", "--no-deps", "--force-recreate", "web"], {},
                )
                assert rendered["services"]["db"]["image"] == "mariadb:12.3.3"
                assert rendered["services"]["web"]["command"] == ["sh", "-c", "echo overlay"]
                assert broker.load_scoped_model(task_root, repository, project) == rendered
                assert calls == [files, files]
            finally:
                broker.compose_config = original_compose_config
        finally:
            broker.MODEL_DIR = original_model_dir

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
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, status TEXT NOT NULL,
                    workspace_path TEXT, container_id TEXT, task_dir_name TEXT,
                    updated_at TEXT
                );
                CREATE TABLE task_sessions (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL, state TEXT NOT NULL,
                    task_environment_id TEXT
                );
                CREATE TABLE executors_running (
                    id TEXT PRIMARY KEY, session_id TEXT NOT NULL UNIQUE,
                    task_id TEXT NOT NULL, status TEXT NOT NULL, container_id TEXT,
                    agent_execution_id TEXT
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
                    ("44444444-4444-4444-4444-444444444444", "ws-two"),
                ),
            )
            database.executemany(
                "INSERT INTO task_environments(id, task_id, status, workspace_path, "
                "container_id, task_dir_name) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    (
                        "env-coordinator",
                        "11111111-1111-1111-1111-111111111111",
                        "ready",
                        "/data/tasks/coord-task/coordinator",
                        "",
                        "coord-task",
                    ),
                    (
                        "env-ordinary",
                        "22222222-2222-2222-2222-222222222222",
                        "ready",
                        "/data/tasks/ordinary-task/app",
                        "",
                        "ordinary-task",
                    ),
                    (
                        "env-target",
                        "33333333-3333-3333-3333-333333333333",
                        "ready",
                        "/data/tasks/target-task/app",
                        "",
                        "target-task",
                    ),
                    (
                        "env-other",
                        "44444444-4444-4444-4444-444444444444",
                        "ready",
                        "/data/tasks/other-task/app",
                        "",
                        "other-task",
                    ),
                ),
            )
            database.executemany(
                "INSERT INTO task_sessions(id, task_id, state, task_environment_id) "
                "VALUES (?, ?, ?, ?)",
                (
                    (
                        "session-live",
                        "22222222-2222-2222-2222-222222222222",
                        "WAITING_FOR_INPUT",
                        "env-ordinary",
                    ),
                    (
                        "session-other",
                        "44444444-4444-4444-4444-444444444444",
                        "RUNNING",
                        "env-other",
                    ),
                ),
            )
            database.executemany(
                "INSERT INTO executors_running(id, session_id, task_id, status, container_id, "
                "agent_execution_id) VALUES (?, ?, ?, ?, ?, ?)",
                (
                    (
                        "execution-live",
                        "session-live",
                        "22222222-2222-2222-2222-222222222222",
                        "ready",
                        "",
                        "instance-live",
                    ),
                    (
                        "execution-other",
                        "session-other",
                        "44444444-4444-4444-4444-444444444444",
                        "running",
                        "",
                        "instance-other",
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
        expect_denied(
            lambda: broker.workspace_task_probe(
                coordinator, "44444444-4444-4444-4444-444444444444"
            ),
            "unknown/cross-workspace task received coordinator probe",
        )

        # A coordinator can synchronize only its own description from a file
        # inside its task root; the broad temporary PAT never reaches the
        # agent-facing response or socket request.
        charter = task_root / "PROMPT.md"
        charter.write_text("# Coordinator charter\n\nExact content.\n", encoding="utf-8")
        calls: list[tuple[str, str, dict[str, object] | None]] = []

        @contextmanager
        def fake_token():
            yield "broker-only-token"

        def fake_backend(method: str, path: str, token: str, payload=None):
            assert token == "broker-only-token"
            calls.append((method, path, payload))
            if method == "GET":
                return {"description": "old"}
            return {"description": payload["description"]}

        broker.temporary_operator_token = fake_token
        broker.backend_json = fake_backend
        broker.COORDINATOR_AUDIT_LOG = base / "description-audit.jsonl"
        result = broker.coordinator_description_update(coordinator, task_root, "PROMPT.md")
        response = json.loads(result["stdout"])
        assert response["changed"] is True
        assert calls[-1][0] == "PATCH"
        assert calls[-1][2] == {"description": "# Coordinator charter\n\nExact content."}
        assert "broker-only-token" not in result["stdout"]
        expect_denied(
            lambda: broker.coordinator_description_update(
                coordinator, task_root, str(outside / "description.md")
            ),
            "outside description source was accepted",
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

        runtime_labels = {
            "kandev.managed": "true",
            "kandev.task_id": "22222222-2222-2222-2222-222222222222",
            "kandev.session_id": "session-live",
            "kandev.task_environment_id": "env-ordinary",
        }
        runtime_info = {
            "Id": "container-live",
            "Name": "/runtime-live",
            "State": {"Status": "running"},
            "Config": {"Labels": runtime_labels, "WorkingDir": "/workspace"},
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": str(data_root / "tasks" / "ordinary-task" / "app"),
                    "Destination": "/workspace",
                }
            ],
        }
        assert broker.container_workspace_ids(runtime_info) == {"ws-one"}
        # Re-reading an existing runtime registration is deterministic and
        # does not require a second principal or ownership record.
        assert broker.container_workspace_ids(runtime_info) == {"ws-one"}

        # Canonical Docker executors clone inside /workspace and deliberately
        # have no host workspace bind. Their backend-issued instance label is
        # still an exact binding to executors_running.agent_execution_id.
        clone_inside_runtime = json.loads(json.dumps(runtime_info))
        clone_inside_runtime["Config"]["Labels"]["kandev.instance_id"] = "instance-live"
        clone_inside_runtime["Mounts"] = []
        assert broker.container_workspace_ids(clone_inside_runtime) == {"ws-one"}

        wrong_instance_runtime = json.loads(json.dumps(clone_inside_runtime))
        wrong_instance_runtime["Config"]["Labels"]["kandev.instance_id"] = "instance-wrong"
        assert broker.container_workspace_ids(wrong_instance_runtime) == set()

        # A WorkingDir string is agent-controlled and cannot substitute for an
        # inspected bind source when all durable container IDs are empty.
        forged_unmounted_runtime = json.loads(json.dumps(runtime_info))
        forged_unmounted_runtime["Config"]["WorkingDir"] = "/data/tasks/ordinary-task"
        forged_unmounted_runtime["Mounts"] = []
        assert broker.container_workspace_ids(forged_unmounted_runtime) == set()
        original_docker_inspect = broker.docker_inspect_container
        broker.docker_inspect_container = lambda _: runtime_info
        try:
            assert broker.require_workspace_container("runtime-live", "ws-one") == runtime_info
            expect_denied(
                lambda: broker.require_workspace_container("runtime-live", "ws-two"),
                "another workspace received a registered task runtime",
            )
        finally:
            broker.docker_inspect_container = original_docker_inspect

        cross_workspace_runtime = {
            "Id": "container-other",
            "Config": {
                "Labels": {
                    "kandev.managed": "true",
                    "kandev.task_id": "44444444-4444-4444-4444-444444444444",
                    "kandev.session_id": "session-other",
                    "kandev.task_environment_id": "env-other",
                },
                "WorkingDir": "/workspace",
            },
            "Mounts": [
                {
                    "Type": "bind",
                    "Source": str(data_root / "tasks" / "other-task" / "app"),
                    "Destination": "/workspace",
                }
            ],
        }
        assert broker.container_workspace_ids(cross_workspace_runtime) == {"ws-two"}
        assert "ws-one" not in broker.container_workspace_ids(cross_workspace_runtime)

        original_run_command = broker.run_command

        def fake_container_listing(
            args, cwd, timeout=broker.COMMAND_TIMEOUT, environment_overrides=None
        ):
            if args == [broker.DOCKER_BIN, "container", "ls", "--all", "--quiet"]:
                return 0, "container-live\ncontainer-other\n", ""
            if args[:4] == [broker.DOCKER_BIN, "inspect", "--type", "container"]:
                return 0, json.dumps([runtime_info, cross_workspace_runtime]), ""
            raise AssertionError(f"unexpected source-list command: {args}")

        broker.run_command = fake_container_listing
        try:
            visible = broker.list_workspace_containers("ws-one")
        finally:
            broker.run_command = original_run_command
        assert len(visible) == 1
        assert visible[0]["name"] == "runtime-live"
        assert visible[0]["id"] == "container-li"

        stale_session_runtime = json.loads(json.dumps(runtime_info))
        stale_session_runtime["Config"]["Labels"]["kandev.session_id"] = "session-stale"
        stale_session_runtime["Config"]["Labels"][
            "com.docker.compose.project.working_dir"
        ] = str(base / "app")
        assert broker.container_workspace_ids(stale_session_runtime) == set()

        wrong_path_runtime = json.loads(json.dumps(runtime_info))
        wrong_path_runtime["Mounts"][0]["Source"] = str(
            data_root / "tasks" / "other-task" / "app"
        )
        wrong_path_runtime["Config"]["Labels"][
            "com.docker.compose.project.working_dir"
        ] = str(base / "app")
        assert broker.container_workspace_ids(wrong_path_runtime) == set()

        incomplete_runtime = json.loads(json.dumps(runtime_info))
        del incomplete_runtime["Config"]["Labels"]["kandev.task_environment_id"]
        incomplete_runtime["Config"]["Labels"][
            "com.docker.compose.project.working_dir"
        ] = str(base / "app")
        assert broker.container_workspace_ids(incomplete_runtime) == {"ws-one"}

        # Empty persisted IDs are the deployed shape. Once either source gains
        # an ID, it becomes an additional exact constraint without weakening
        # the authoritative identity/path binding.
        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE task_environments SET container_id = 'container-wrong' "
                "WHERE id = 'env-ordinary'"
            )
        assert broker.container_workspace_ids(runtime_info) == set()
        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE task_environments SET container_id = 'container-live' "
                "WHERE id = 'env-ordinary'"
            )
        assert broker.container_workspace_ids(runtime_info) == {"ws-one"}
        exact_id_clone_inside_runtime = json.loads(json.dumps(runtime_info))
        exact_id_clone_inside_runtime["Mounts"] = []
        assert broker.container_workspace_ids(exact_id_clone_inside_runtime) == {"ws-one"}
        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE executors_running SET container_id = 'container-wrong' "
                "WHERE session_id = 'session-live'"
            )
        assert broker.container_workspace_ids(runtime_info) == set()
        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE executors_running SET container_id = 'container-live' "
                "WHERE session_id = 'session-live'"
            )
        assert broker.container_workspace_ids(runtime_info) == {"ws-one"}

        spoofed_container_runtime = json.loads(json.dumps(runtime_info))
        spoofed_container_runtime["Id"] = "container-spoofed"
        assert broker.container_workspace_ids(spoofed_container_runtime) == set()

        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE tasks SET archived_at = '2026-09-05T00:00:00Z' "
                "WHERE id = '22222222-2222-2222-2222-222222222222'"
            )
        assert broker.container_workspace_ids(runtime_info) == set()
        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE tasks SET archived_at = NULL "
                "WHERE id = '22222222-2222-2222-2222-222222222222'"
            )

        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE task_sessions SET state = 'COMPLETED' WHERE id = 'session-live'"
            )
        assert broker.container_workspace_ids(runtime_info) == set()
        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE task_sessions SET state = 'WAITING_FOR_INPUT' WHERE id = 'session-live'"
            )
            database.execute(
                "UPDATE task_environments SET status = 'stopped' WHERE id = 'env-ordinary'"
            )
        assert broker.container_workspace_ids(runtime_info) == set()
        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE task_environments SET status = 'ready' WHERE id = 'env-ordinary'"
            )
            database.execute(
                "UPDATE executors_running SET status = 'stopped' WHERE session_id = 'session-live'"
            )
        assert broker.container_workspace_ids(runtime_info) == set()
        with sqlite3.connect(metadata) as database:
            database.execute(
                "UPDATE executors_running SET status = 'ready' WHERE session_id = 'session-live'"
            )
            database.execute("DELETE FROM executors_running WHERE session_id = 'session-live'")
        assert broker.container_workspace_ids(runtime_info) == set()
        with sqlite3.connect(metadata) as database:
            database.execute(
                "INSERT INTO executors_running(id, session_id, task_id, status, container_id, "
                "agent_execution_id) VALUES ('execution-restored', 'session-live', "
                "'22222222-2222-2222-2222-222222222222', 'ready', 'container-live', "
                "'instance-live')"
            )
            database.execute("DELETE FROM task_environments WHERE id = 'env-ordinary'")
        assert broker.container_workspace_ids(runtime_info) == set()

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

        # Static logical backups are a deliberately narrow alternative when a
        # workspace database container is stopped: only last_db.sql directly
        # under a registered same-workspace source root is readable.
        source_repository = base / "app"
        source_repository.mkdir(exist_ok=True)
        backup = source_repository / "last_db.sql"
        backup_bytes = b"-- logical backup fixture\nSELECT 104;\n"
        backup.write_bytes(backup_bytes)
        source, container_source = broker.registered_static_backup(
            "/data/home/Code/app/last_db.sql", "ws-one"
        )
        assert source == backup
        assert container_source == "/data/home/Code/app/last_db.sql"
        static_destination, static_container_destination = broker.target_task_inbox(
            "33333333-3333-3333-3333-333333333333", "ws-one", "static-fixture.sql"
        )
        size, checksum = broker.copy_static_backup(source, static_destination)
        assert static_container_destination.endswith("/static-fixture.sql")
        assert size == len(backup_bytes)
        assert checksum == hashlib.sha256(backup_bytes).hexdigest()
        assert static_destination.read_bytes() == backup_bytes
        expect_denied(
            lambda: broker.registered_static_backup("/data/home/Code/app/other.sql", "ws-one"),
            "arbitrary SQL file was accepted as a static backup",
        )
        backup.unlink()
        backup.symlink_to(outside / "outside.sql")
        expect_denied(
            lambda: broker.registered_static_backup("/data/home/Code/app/last_db.sql", "ws-one"),
            "symlinked static backup was accepted",
        )
        backup.unlink()
        backup.write_bytes(backup_bytes)

        original_context = broker.coordinator_context
        broker.coordinator_context = lambda _: coordinator
        try:
            response = broker.handle_coordinator_source(
                Path("/data/tasks/coord-task"),
                [
                    "kandev",
                    "source",
                    "static-backup",
                    "/data/home/Code/app/last_db.sql",
                    "--target-task",
                    "33333333-3333-3333-3333-333333333333",
                    "--name",
                    "delivered-static.sql",
                ],
            )
        finally:
            broker.coordinator_context = original_context
        delivery = json.loads(response["stdout"])
        assert delivery["source"] == "/data/home/Code/app/last_db.sql"
        assert delivery["target_task_id"] == "33333333-3333-3333-3333-333333333333"
        assert delivery["bytes"] == len(backup_bytes)
        assert delivery["sha256"] == hashlib.sha256(backup_bytes).hexdigest()
        assert delivery["path"].endswith("/delivered-static.sql")

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

        # Scout may inspect only the image registered by the approved built
        # service, from the same task clone that saved the Compose model.
        original_model_dir = broker.MODEL_DIR
        original_audit_log = broker.COMPOSE_AUDIT_LOG
        original_run_command = broker.run_command
        broker.MODEL_DIR = base / "scout-models"
        broker.COMPOSE_AUDIT_LOG = base / "scout-audit.jsonl"
        scout_image = f"{project}_backend-stripe:latest"
        scout_model = {"services": {"backend-stripe": {
            "build": {"context": str(repository)}, "image": scout_image,
        }}}
        broker.save_scoped_model(task_root, repository, project, scout_model)
        image_id = "sha256:" + "a" * 64
        digest = "sha256:" + "b" * 64
        scout_calls = []

        def fake_scout_command(args, cwd, **kwargs):
            scout_calls.append((args, kwargs))
            if args[1:3] == ["image", "inspect"]:
                return 0, json.dumps([{"Id": image_id, "Descriptor": {"digest": digest}}]), ""
            assert args[1:4] == ["scout", "cves", "--only-severity"]
            assert args[4] in {"critical", "high"} and args[-1] == f"local://{scout_image}"
            assert kwargs["environment_overrides"] == {
                "DOCKER_CONFIG": broker.SCOUT_DOCKER_CONFIG
            }
            return 0, "critical CVE report\n", ""

        broker.run_command = fake_scout_command
        try:
            scout_args = ["scout", "cves", "--only-severity", "critical", scout_image]
            result = broker.handle_scout_cves(task_root, repository, scout_args, {})
            assert result["returncode"] == 0
            assert f"manifest_digest={digest}" in result["stdout"]
            assert "critical CVE report" in result["stdout"]
            assert len(scout_calls) == 3
            scout_calls.clear()
            alias_args = ["scout", "cves", "--only-severity", "critical",
                          "backend-stripe:latest"]
            alias_result = broker.handle_scout_cves(task_root, repository, alias_args, {})
            assert alias_result["returncode"] == 0
            assert f"task_image={scout_image}" in alias_result["stdout"]
            assert scout_calls[1][0][-1] == f"local://{scout_image}"
            scout_calls.clear()
            local_args = ["scout", "cves", "--only-severity", "critical", f"local://{scout_image}"]
            assert broker.handle_scout_cves(task_root, repository, local_args, {})["returncode"] == 0
            scout_calls.clear()
            high_args = ["scout", "cves", "--only-severity", "high", scout_image]
            assert broker.handle_scout_cves(task_root, repository, high_args, {})["returncode"] == 0
            scout_calls.clear()
            for denied_args in (
                ["scout", "cves", "--output", str(outside / "report"), scout_image],
                ["scout", "cves", "--only-severity", "critical", "alpine:latest"],
            ):
                expect_denied(
                    lambda denied_args=denied_args: broker.handle_scout_cves(
                        task_root, repository, denied_args, {}
                    ), "Scout accepted an unapproved scan"
                )
            expect_denied(
                lambda: broker.handle_scout_cves(outside, repository, scout_args, {}),
                "another task received Scout access",
            )
            expect_denied(
                lambda: broker.handle_scout_cves(task_root, sibling_clone, scout_args, {}),
                "sibling clone reused Scout model",
            )
            assert scout_calls == []
        finally:
            broker.run_command = original_run_command
            broker.MODEL_DIR = original_model_dir
            broker.COMPOSE_AUDIT_LOG = original_audit_log

    print("PASS: task Docker broker policy tests")


if __name__ == "__main__":
    main()
    import runpy
    runpy.run_path(str(Path(__file__).with_name('test-project-artifacts.py')), run_name='__main__')
