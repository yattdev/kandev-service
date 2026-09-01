#!/usr/bin/env python3
"""Focused transaction tests for scripts/kandev-safe-deploy."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import tempfile
import textwrap
import unittest


REPOSITORY = Path(__file__).parents[1]
SAFE_DEPLOY = REPOSITORY / "scripts/kandev-safe-deploy"


FAKE_DOCKER = r"""#!/usr/bin/env python3
import os
from pathlib import Path
import sys

state = Path(os.environ["KANDEV_DEPLOY_TEST_STATE"])
current = state / "current-image"
target = state / "target-image"
rollback = state / "rollback-image"
args = sys.argv[1:]

if args[:2] == ["inspect", "kandev"]:
    value = current.read_text().strip()
    if "{{.Config.Image}}" in args:
        value = "kandev-local:latest"
    print(value)
elif args[:2] == ["image", "inspect"]:
    image = args[2]
    if image == "kandev-local:latest":
        value = target.read_text().strip()
    elif image == "kandev-local:safe-deploy-previous" and rollback.exists():
        value = rollback.read_text().strip()
    else:
        value = image
    if "--format" in args:
        print(value)
elif args and args[0] == "tag":
    source, destination = args[1:3]
    if source == "kandev-local:safe-deploy-previous":
        source = rollback.read_text().strip()
    elif source == "kandev-local:latest":
        source = target.read_text().strip()
    if destination == "kandev-local:safe-deploy-previous":
        rollback.write_text(source)
    elif destination == "kandev-local:latest":
        target.write_text(source)
elif args and args[0] == "compose":
    if "build" in args:
        target.write_text("sha256:new")
    elif "up" in args:
        up_count = state / "up-count"
        count = int(up_count.read_text()) + 1 if up_count.exists() else 1
        up_count.write_text(str(count))
        current.write_text(target.read_text().strip())
        if os.environ.get("KANDEV_DEPLOY_TEST_UP_FAIL") == "candidate" and count == 1:
            raise SystemExit(17)
elif args and args[0] == "logs":
    print("fake logs")
else:
    raise SystemExit(f"unexpected docker invocation: {args}")
"""


FAKE_CURL = r"""#!/usr/bin/env python3
import os
from pathlib import Path

mode = os.environ.get("KANDEV_DEPLOY_TEST_READY", "always")
current = Path(os.environ["KANDEV_DEPLOY_TEST_STATE"]) / "current-image"
if mode == "always" or current.read_text().strip() == "sha256:old":
    print("200", end="")
else:
    print("503", end="")
"""


class SafeDeployTest(unittest.TestCase):
    def run_deploy(
        self, ready: str, *, up_failure: str = ""
    ) -> tuple[subprocess.CompletedProcess[str], Path, Path]:
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        root = Path(temporary.name)
        fake_bin = root / "bin"
        fake_bin.mkdir()
        for name, content in (("docker", FAKE_DOCKER), ("curl", FAKE_CURL)):
            path = fake_bin / name
            path.write_text(textwrap.dedent(content))
            path.chmod(0o755)
        state = root / "state"
        state.mkdir()
        (state / "current-image").write_text("sha256:old")
        (state / "target-image").write_text("sha256:old")
        log = root / "deploy.log"
        environment = {
            **os.environ,
            "PATH": f"{fake_bin}:{os.environ['PATH']}",
            "KANDEV_DEPLOY_DIR": str(REPOSITORY),
            "KANDEV_DEPLOY_TEST_STATE": str(state),
            "KANDEV_DEPLOY_TEST_READY": ready,
            "KANDEV_DEPLOY_TEST_UP_FAIL": up_failure,
            "KANDEV_DEPLOY_HEALTH_TIMEOUT_SECS": "1",
            "KANDEV_DEPLOY_HEALTH_INTERVAL_SECS": "0.05",
            "KANDEV_DEPLOY_LOG": str(log),
            "KANDEV_DEPLOY_LOCK": str(root / "deploy.lock"),
        }
        completed = subprocess.run(
            [str(SAFE_DEPLOY), "--build"],
            cwd=REPOSITORY,
            env=environment,
            text=True,
            capture_output=True,
            timeout=10,
            check=False,
        )
        return completed, state, log

    def test_candidate_requires_http_200(self) -> None:
        completed, state, log = self.run_deploy("always")
        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertEqual((state / "current-image").read_text(), "sha256:new")
        self.assertIn("Deployment accepted", log.read_text())

    def test_readiness_failure_restores_previous_image_and_fails(self) -> None:
        completed, state, log = self.run_deploy("rollback")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual((state / "current-image").read_text(), "sha256:old")
        output = log.read_text()
        self.assertIn("Candidate rejected; starting automatic rollback", output)
        self.assertIn("Rollback verified", output)
        self.assertIn("rolled back successfully", output)

    def test_compose_recreate_failure_also_restores_previous_image(self) -> None:
        completed, state, log = self.run_deploy("always", up_failure="candidate")
        self.assertNotEqual(completed.returncode, 0)
        self.assertEqual((state / "current-image").read_text(), "sha256:old")
        output = log.read_text()
        self.assertIn("Docker Compose failed while recreating the candidate", output)
        self.assertIn("Rollback verified", output)
        self.assertIn("recreation failed and was rolled back successfully", output)


if __name__ == "__main__":
    unittest.main()
