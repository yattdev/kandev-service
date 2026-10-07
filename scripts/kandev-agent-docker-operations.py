"""Ordinary Docker commands, limited to the caller's registered task resources."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import uuid


class Operations:
    def __init__(self, broker, root: Path, cwd: Path, stdin=None):
        self.b, self.root, self.cwd, self.stdin = broker, root, cwd, stdin

    def execute(self, args, *, stdin=False):
        code, stdout, stderr = self.b.run_command(
            [self.b.DOCKER_BIN, *args], self.cwd,
            stdin_stream=self.stdin if stdin else None,
        )
        return {"returncode": code, "stdout": stdout, "stderr": stderr}

    def project(self, kind, alias):
        suffix = hashlib.sha256(alias.encode()).hexdigest()[:16]
        return self.b.scoped_project_name(
            self.root, {"COMPOSE_PROJECT_NAME": f"docker-{kind}-{suffix}"}, self.cwd
        )

    def models(self):
        return self.b.owned_models(self.root)

    def image(self, alias):
        matches = []
        for directory, project, model in self.models():
            for name, service in model.get("services", {}).items():
                image = service.get("image")
                aliases = [image, f"{name}:latest", service.get("x-kandev-image-alias")]
                aliases += service.get("x-kandev-image-aliases", [])
                if service.get("build") and alias in aliases:
                    if image == self.b.scoped_build_image(image, project, name):
                        matches.append(image)
        matches = sorted(set(matches))
        if len(matches) > 1:
            raise self.b.BrokerError("image alias is ambiguous; use the scoped tag shown by docker images")
        if matches:
            return matches[0]
        if alias.startswith("kd_"):
            raise self.b.BrokerError("image is outside this task's registered builds")
        return alias

    def container(self, requested):
        # Inspect exact Docker identities first; accept an alias only if it
        # identifies one container registered by this task's own saved model.
        owners = {project: model for _, project, model in self.models()}
        aliases = []
        for project, model in owners.items():
            for name, service in model.get("services", {}).items():
                if requested in {name, service.get("x-kandev-container-alias")}:
                    aliases.append((project, name))
        candidates = [requested]
        for project, service in aliases:
            code, output, _ = self.b.run_command([
                self.b.DOCKER_BIN, "ps", "-aq", "--filter", f"label=com.docker.compose.project={project}",
                "--filter", f"label=com.docker.compose.service={service}",
            ], self.cwd)
            if code == 0:
                candidates.extend(output.split())
        valid = {}
        for candidate in dict.fromkeys(candidates):
            code, output, _ = self.b.run_command([
                self.b.DOCKER_BIN, "inspect", "--type", "container", candidate,
            ], self.cwd)
            if code != 0:
                continue
            try:
                records = json.loads(output)
                info = records[0]
                labels = info["Config"]["Labels"] or {}
                project = labels.get("com.docker.compose.project")
                service = labels.get("com.docker.compose.service")
                container_id = info["Id"]
                if len(records) != 1 or not re.fullmatch(r"[0-9a-f]{64}", container_id):
                    continue
                if project in owners and service in owners[project].get("services", {}):
                    valid[container_id] = project
            except (ValueError, KeyError, IndexError, TypeError):
                continue
        if len(valid) != 1:
            raise self.b.BrokerError("container must identify one of this task's containers; use docker ps")
        return next(iter(valid.items()))

    def options(self, args, values, flags):
        result, index = [], 0
        while index < len(args) and args[index].startswith("-"):
            arg = args[index]
            option, equal, value = arg.partition("=")
            if option in flags and not equal:
                result.append((option, None))
            elif option in values:
                if not equal:
                    index += 1
                    if index >= len(args):
                        raise self.b.BrokerError(f"missing Docker option value: {option}")
                    value = args[index]
                result.append((option, value))
            else:
                raise self.b.BrokerError(f"unsupported task Docker option: {option}")
            index += 1
        return result, args[index:]

    def build(self, args):
        options, tail = self.options(args, {"-t", "--tag", "-f", "--file", "--build-arg", "--target", "--platform", "--progress"}, {"--pull", "--no-cache", "--load", "-q", "--quiet"})
        if len(tail) != 1 or tail[0] == "-":
            raise self.b.BrokerError("docker build requires one local task-owned context directory")
        context = self.b.resolve_inside(tail[0], self.cwd, self.root)
        if not context.is_dir():
            raise self.b.BrokerError("Docker build context is not a directory")
        tags = [v for k, v in options if k in {"-t", "--tag"}] or ["image:latest"]
        project = self.project("build", tags[0])
        image = f"{project}_image:latest"
        files = [v for k, v in options if k in {"-f", "--file"}]
        dockerfile = self.b.resolve_inside(files[-1] if files else str(context / "Dockerfile"), self.cwd, self.root)
        argv = ["build", "--tag", image, "--file", str(self.b.translate_to_host(dockerfile))]
        for option, value in options:
            if option in {"-t", "--tag", "-f", "--file", "--load"}:
                continue
            if option == "--build-arg" and "=" not in value:
                raise self.b.BrokerError("provide Docker build arguments explicitly as KEY=value")
            argv.append(option)
            if value is not None:
                argv.append(value)
        model = {"services": {"image": {"build": {"context": str(self.b.translate_to_host(context))}, "image": image, "x-kandev-image-aliases": tags}}}
        self.b.save_scoped_model(self.root, self.cwd, project, model)
        result = self.execute([*argv, str(self.b.translate_to_host(context))])
        result["stdout"] = f"task_image={image}\n" + result["stdout"]
        return result

    def run(self, args):
        values = {"--name", "-v", "--volume", "-p", "--publish", "-e", "--env", "-w", "--workdir", "-u", "--user", "--entrypoint", "--network", "--restart"}
        options, tail = self.options(args, values, {"-d", "--detach", "--rm", "-i", "--interactive"})
        if not tail:
            raise self.b.BrokerError("docker run requires an image")
        names = [v for k, v in options if k == "--name"]
        alias = names[-1] if names else "run-" + uuid.uuid4().hex[:12]
        if not self.b.CONTAINER_NAME_RE.fullmatch(alias):
            raise self.b.BrokerError("invalid task container name")
        project = self.project("run", alias)
        name = f"{project}-run-1"
        image = self.image(tail[0])
        model = {"services": {"run": {"image": image, "x-kandev-container-alias": alias}}, "networks": {"default": {"name": f"{project}_default"}}}
        argv = ["run", "--name", name, "--label", f"com.docker.compose.project={project}", "--label", "com.docker.compose.service=run",
                "--label", f"com.docker.compose.project.working_dir={self.b.translate_to_host(self.cwd)}"]
        volumes = {}
        use_network = True
        for option, value in options:
            if option == "--name":
                continue
            if option == "--network":
                if value not in {"bridge", "none"}:
                    raise self.b.BrokerError("docker run network must be the task bridge or none")
                use_network = value != "none"
                continue
            if option in {"-v", "--volume"}:
                parts = value.split(":")
                if len(parts) not in (2, 3) or not parts[1].startswith("/"):
                    raise self.b.BrokerError("Docker volumes require source:/container/path[:ro|rw]")
                if len(parts) == 3 and parts[2] not in {"ro", "rw"}:
                    raise self.b.BrokerError("Docker volume mode must be ro or rw")
                if "docker.sock" in parts[1] or parts[1] in {"/run", "/var/run"}:
                    raise self.b.BrokerError("Docker daemon paths are not task mounts")
                if parts[0].startswith(("/", ".")):
                    source = self.b.resolve_inside(parts[0], self.cwd, self.root)
                    parts[0] = str(self.b.translate_to_host(source))
                else:
                    if not self.b.SAFE_OUTPUT_NAME_RE.fullmatch(parts[0]):
                        raise self.b.BrokerError("invalid task volume name")
                    parts[0] = f"{project}_{parts[0]}"
                    volumes[parts[0]] = {"name": parts[0]}
                value = ":".join(parts)
            if option in {"-e", "--env"} and "=" not in value:
                raise self.b.BrokerError("provide Docker environment values explicitly as KEY=value")
            if option in {"-p", "--publish"}:
                parts = value.split(":")
                if len(parts) > 3 or (len(parts) == 3 and parts[0] != "127.0.0.1"):
                    raise self.b.BrokerError("task Docker ports publish on loopback only")
                if len(parts) < 3:
                    value = "127.0.0.1:" + value if len(parts) == 2 else "127.0.0.1::" + value
            argv.append(option)
            if value is not None:
                argv.append(value)
        if volumes:
            model["volumes"] = volumes
        self.b.save_scoped_model(self.root, self.cwd, project, model)
        if use_network:
            existing = self.b.inspect_owned_network(f"{project}_default")
            if existing is None:
                self.b.handle_network_reserve(self.root, self.cwd, ["kandev", "network", "reserve"], {"COMPOSE_PROJECT_NAME": project})
            else:
                self.b.owned_network_receipt(existing, self.root, project)
        argv += ["--network", f"{project}_default" if use_network else "none", image, *tail[1:]]
        result = self.execute(argv, stdin=any(k in {"-i", "--interactive"} for k, _ in options))
        result["stderr"] += f"task_container={name}\n"
        return result

    def handle(self, args):
        if len(args) == 2 and args[1] == "--help" and args[0] in {"build", "run", "ps", "images", "inspect", "logs", "exec", "start", "stop", "restart", "rm", "pull", "version"}:
            return self.execute(args)
        if args[:2] == ["buildx", "build"]:
            return self.build(args[2:])
        if args[:1] == ["build"]:
            return self.build(args[1:])
        if args[:1] == ["run"]:
            return self.run(args[1:])
        if args in ([], ["--help"], ["help"]):
            return {"returncode": 0, "stdout": "Task Docker: compose, build, buildx build, run, ps, images, inspect, logs, exec, start, stop, restart, rm, pull, version, scout. Resources are scoped automatically.\n", "stderr": ""}
        if args[:1] == ["version"] or args == ["--version"]:
            return self.execute(args)
        if args[0] in {"container", "image"}:
            args = args[1:]
            if not args:
                return self.handle(["--help"])
            if args[:1] == ["ls"]:
                args = ["ps" if "container" in self.original_prefix else "images", *args[1:]]
        if args[:1] in (["ps"], ["images"]):
            options, tail = self.options(args[1:], {"--format", "--filter", "-f"}, {"-a", "--all", "-q", "--quiet", "--no-trunc", "--digests"})
            if tail:
                raise self.b.BrokerError("task Docker listings select the task's own resources")
            for key, value in options:
                if key in {"--filter", "-f"}:
                    allowed = {"status", "health", "name", "id"} if args[0] == "ps" else {"dangling"}
                    if value.split("=", 1)[0] not in allowed:
                        raise self.b.BrokerError("Docker listing filters cannot change task resource selection")
            values = [arg for k, v in options for arg in ([k] if v is None else [k, v])]
            outputs, errors, code = [], [], 0
            if args[0] == "ps":
                for _, project, _ in self.models():
                    result = self.execute(["ps", *values, "--filter", f"label=com.docker.compose.project={project}"])
                    outputs.append(result["stdout"]); errors.append(result["stderr"]); code = code or result["returncode"]
            else:
                images = sorted({s["image"] for _, _, m in self.models() for s in m.get("services", {}).values() if s.get("build") and s.get("image")})
                for image in images:
                    result = self.execute(["images", *values, image])
                    outputs.append(result["stdout"]); errors.append(result["stderr"]); code = code or result["returncode"]
            return {"returncode": code, "stdout": "".join(outputs), "stderr": "".join(errors)}
        if args[:1] == ["pull"]:
            options, tail = self.options(args[1:], {"--platform"}, {"-q", "--quiet"})
            if len(tail) != 1 or tail[0].startswith("kd_"):
                raise self.b.BrokerError("docker pull requires one registry image")
            return self.execute(["pull", *[a for k,v in options for a in ([k] if v is None else [k,v])], tail[0]])
        if args[0] in {"inspect", "logs", "exec", "start", "stop", "restart", "rm"}:
            values = {"--format", "-f", "--type"} if args[0] == "inspect" else {"--tail", "--since", "--until"} if args[0] == "logs" else {"-e", "--env", "-w", "--workdir", "-u", "--user"} if args[0] == "exec" else {"-t", "--time", "--timeout"}
            flags = {"--size", "-s"} if args[0] == "inspect" else {"--timestamps", "-t", "--details"} if args[0] == "logs" else {"-i", "--interactive", "-d", "--detach"} if args[0] == "exec" else {"-f", "--force"} if args[0] == "rm" else set()
            options, tail = self.options(args[1:], values, flags)
            if not tail or (args[0] != "exec" and len(tail) != 1):
                raise self.b.BrokerError("select one exact task-owned Docker resource")
            if args[0] == "exec" and len(tail) < 2:
                raise self.b.BrokerError("docker exec requires a command")
            options_args = [a for k,v in options for a in ([k] if v is None else [k,v])]
            if args[0] == "inspect":
                try:
                    _, _, image = self.b.owned_build_image(self.root, self.cwd, tail[0])
                except self.b.BrokerError:
                    pass
                else:
                    if any(k == "--type" and v != "image" for k,v in options):
                        raise self.b.BrokerError("requested resource is a task image")
                    image_options = [a for k,v in options if k != "--type" for a in ([k] if v is None else [k,v])]
                    return self.execute(["image", "inspect", *image_options, image])
            container_id, project = self.container(tail[0])
            for k,v in options:
                if k in {"-e", "--env"} and "=" not in v:
                    raise self.b.BrokerError("provide Docker environment values explicitly as KEY=value")
            audit_id = str(uuid.uuid4())
            self.b.audit_compose(self.root, self.cwd, project, project, "docker " + args[0], "allow", "preflight", audit_id=audit_id, command_class="read-only" if args[0] in {"inspect", "logs"} else "task-operation")
            result = self.execute([args[0], *options_args, container_id, *tail[1:]], stdin=args[0] == "exec" and any(k in {"-i", "--interactive"} for k,_ in options))
            self.b.audit_compose(self.root, self.cwd, project, project, "docker " + args[0], "allow", "ok" if result["returncode"] == 0 else "error", audit_id=audit_id, command_class="task-operation")
            return result
        raise self.b.BrokerError("unsupported task Docker command; run docker --help for available commands")


def handle(broker, root, cwd, args, stdin=None):
    operations = Operations(broker, root, cwd, stdin)
    operations.original_prefix = args[:1]
    return operations.handle(args)
