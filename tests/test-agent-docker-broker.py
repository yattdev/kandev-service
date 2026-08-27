#!/usr/bin/env python3
"""Focused unit tests for the task-scoped Docker broker policy."""

from __future__ import annotations

import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
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

    print("PASS: task Docker broker policy tests")


if __name__ == "__main__":
    main()
