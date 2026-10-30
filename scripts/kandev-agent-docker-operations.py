"""Ordinary Docker commands, limited to the caller's registered task resources."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import uuid


# Operator-reviewed preservation exception. This does not permit arbitrary
# volume access: the existing task token, live MAIN binding, immutable project
# claim, engine labels and retained directory identity must all agree.
PRESERVATION_SCOPE = {
    "root": "/data/tasks/feature-8241-pc-upgr_10c",
    "task": "3c2a0d34-64ad-46f6-a8db-582ce9c623c8",
    "session": "48733aaa-f324-4ba1-9d0f-cc6fecb30ce2",
    "workspace": "d35ace87-2aae-4e9c-9114-f9899af7f64b",
    "project": "kd_8241phase2_20261028",
    "logical": "phase2_ambo_20261028_db",
    "volume": "kd_8241phase2_20261028_phase2_ambo_20261028_db",
    "created": "2026-10-28T10:31:09-04:00",
    "config_hash": "af564ab8dd65b8f6c41704fd2f0068c58adcb627e09bc89139a69c0d70c8d4c3",
    "device": 66310,
    "inode": 40393626,
}


# Executed only by a fixed Python entrypoint in the platform's pinned image.
# No caller commands, images, source paths, or environment enter this helper.
PRESERVATION_HELPER = r'''
import hashlib, json, os, pathlib, stat, sys, tarfile

def require(ok, message):
    if not ok:
        raise ValueError(message)

def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()

def inventory(source, expected):
    root = source.lstat()
    require(stat.S_ISDIR(root.st_mode), 'source is not a directory')
    require((root.st_dev, root.st_ino) == (expected['device'], expected['inode']), 'source inode identity changed')
    rows = []
    def failed(error):
        raise ValueError('source inventory traversal failed')
    for directory, dirs, files in os.walk(source, followlinks=False, onerror=failed):
        dirs.sort(); files.sort()
        for name in ['.'] if directory == str(source) else []:
            rows.append(record(source, source))
        for name in dirs + files:
            rows.append(record(pathlib.Path(directory) / name, source))
    rows.sort(key=lambda row: row['path'])
    if expected.get('readonly_required'):
        require(all(os.statvfs(source / row['path']).f_flag & os.ST_RDONLY for row in rows),
                'source contains a writable descendant mount')
    regular = [row for row in rows if row['type'] == 'file']
    require(regular and any(row['path'] == 'ibdata1' and row['size'] > 0 for row in regular), 'source is empty or lacks retained MariaDB marker')
    fs = os.statvfs(source)
    summary = dict(device=root.st_dev, inode=root.st_ino, root_mtime_ns=root.st_mtime_ns,
                   root_ctime_ns=root.st_ctime_ns, files=len(regular),
                   directories=len(rows)-len(regular), bytes=sum(row['size'] for row in regular),
                   inventory_metadata_sha256=digest(rows), capacity_bytes=fs.f_blocks*fs.f_frsize,
                   available_bytes=fs.f_bavail*fs.f_frsize)
    return rows, summary

def record(path, source):
    s = path.lstat()
    require(s.st_dev == source.lstat().st_dev, 'source crosses a filesystem')
    require(stat.S_ISREG(s.st_mode) or stat.S_ISDIR(s.st_mode), 'source contains a link or special file')
    require(not stat.S_ISREG(s.st_mode) or s.st_nlink == 1, 'source contains a hard link')
    return dict(path=path.relative_to(source).as_posix(), type='file' if stat.S_ISREG(s.st_mode) else 'directory',
                size=s.st_size, mode=stat.S_IMODE(s.st_mode), uid=s.st_uid, gid=s.st_gid,
                mtime_ns=s.st_mtime_ns, ctime_ns=s.st_ctime_ns, device=s.st_dev, inode=s.st_ino)

def hash_stream(stream):
    h = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024*1024), b''):
        h.update(chunk)
    return h.hexdigest()

def create(path, cfg):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    os.fchown(fd, cfg['uid'], cfg['gid'])
    return os.fdopen(fd, 'wb')

class HashReader:
    def __init__(self, stream):
        self.stream = stream
        self.hash = hashlib.sha256()
    def read(self, size):
        data = self.stream.read(size)
        self.hash.update(data)
        return data

def main(cfg):
    source = pathlib.Path(cfg['source'])
    require(not cfg.get('readonly_required') or os.statvfs(source).f_flag & os.ST_RDONLY, 'source mount is not read-only')
    rows, before = inventory(source, cfg)
    if cfg['mode'] == 'inspect':
        return dict(version='task-retained-volume-preservation/v1', source=before)
    require(before['inventory_metadata_sha256'] == cfg['inventory_metadata_sha256'], 'source inventory changed since preflight')
    output = pathlib.Path(cfg['output'])
    destination = output.lstat()
    require(stat.S_ISDIR(destination.st_mode) and (destination.st_dev, destination.st_ino)
            == (cfg['output_device'], cfg['output_inode']), 'output inode identity changed')
    require(not list(output.iterdir()), 'output directory is not empty')
    fs = os.statvfs(output)
    require(fs.f_bavail*fs.f_frsize > before['bytes'] + len(rows)*4096 + 10*1024*1024, 'insufficient private archive capacity')
    archive = output / 'db_volume.tar'
    with create(archive, cfg) as stream:
        with tarfile.open(fileobj=stream, mode='w', format=tarfile.PAX_FORMAT) as tar:
            for row in rows:
                path = source / row['path']
                require(record(path, source) == {k:v for k,v in row.items() if k != 'sha256'}, 'source entry changed')
                info = tar.gettarinfo(str(path), arcname=row['path'])
                if row['type'] == 'file':
                    fd = os.open(path, os.O_RDONLY | os.O_NOFOLLOW)
                    with os.fdopen(fd, 'rb') as data:
                        s = os.fstat(data.fileno())
                        require((s.st_dev,s.st_ino,s.st_size) == (row['device'],row['inode'],row['size']), 'source entry identity changed')
                        reader = HashReader(data)
                        tar.addfile(info, reader)
                        row['sha256'] = reader.hash.hexdigest()
                else:
                    tar.addfile(info)
        stream.flush(); os.fsync(stream.fileno())
    after_rows, after = inventory(source, cfg)
    require(after['inventory_metadata_sha256'] == before['inventory_metadata_sha256'], 'source changed during preservation')
    expected = {row['path']:row for row in rows}
    seen = set()
    with tarfile.open(archive, mode='r:') as tar:
        for member in tar:
            require(member.name in expected and member.name not in seen, 'archive inventory mismatch')
            seen.add(member.name); row = expected[member.name]
            require(member.size == (row['size'] if row['type'] == 'file' else 0), 'archive size mismatch')
            require((member.uid, member.gid, member.mode) == (row['uid'], row['gid'], row['mode']), 'archive ownership or mode mismatch')
            if row['type'] == 'file':
                require(member.isfile(), 'archive entry type mismatch')
                with tar.extractfile(member) as data:
                    require(hash_stream(data) == row['sha256'], 'archive content hash mismatch')
            else:
                require(member.isdir(), 'archive entry type mismatch')
    require(seen == set(expected), 'archive is missing source entries')
    payload = (json.dumps(rows, sort_keys=True, indent=2) + '\n').encode()
    with create(output / 'inventory.json', cfg) as stream:
        stream.write(payload); stream.flush(); os.fsync(stream.fileno())
    with archive.open('rb') as stream:
        checksum = hash_stream(stream)
    receipt = dict(version='task-retained-volume-preservation/v1', verified=True, source=before,
                   source_after=after, archive_bytes=archive.stat().st_size, archive_sha256=checksum,
                   inventory_sha256=hashlib.sha256(payload).hexdigest(), verified_files=before['files'],
                   verified_file_bytes=before['bytes'])
    receipt.update(cfg.get('receipt_identity', {}))
    with create(output / 'receipt.json', cfg) as stream:
        stream.write((json.dumps(receipt, sort_keys=True, indent=2)+'\n').encode())
        stream.flush(); os.fsync(stream.fileno())
    fd = os.open(output, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)
    return receipt

try:
    print(json.dumps(main(json.loads(sys.argv[1])), sort_keys=True))
except Exception as error:
    # Never emit source file contents, inventory names, or runtime tracebacks.
    print('retained-volume preservation failed: ' + (str(error) if isinstance(error, ValueError) else type(error).__name__), file=sys.stderr)
    sys.exit(78)
'''


class VolumePreservation:
    def __init__(self, operations):
        self.op = operations
        self.b = operations.b
        self.scope = PRESERVATION_SCOPE

    def require(self, condition, message):
        if not condition:
            raise self.b.BrokerError(message)

    def owner(self, volume):
        s = self.scope
        repository = Path(s['root']) / 'performcoop'
        self.require(self.op.root == Path(s['root']) and self.op.cwd == repository and volume == s['volume'],
                     'volume preservation is restricted to the reviewed task, clone and exact retained volume')
        with self.b.sqlite3.connect(f'file:{self.b.KANDEV_DB}?mode=ro', uri=True) as con:
            row = con.execute('''SELECT t.workspace_id, s.state, e.status, e.workspace_path
                FROM tasks t JOIN task_sessions s ON s.task_id=t.id
                JOIN task_environments e ON e.id=s.task_environment_id AND e.task_id=t.id
                WHERE t.id=? AND s.id=?''', (s['task'], s['session'])).fetchone()
        self.require(row and row[0] == s['workspace'] and row[1] in self.b.ACTIVE_TASK_SESSION_STATES
                     and row[2] == 'ready' and row[3] == str(repository), 'reviewed MAIN binding is no longer active')
        model = self.b.load_scoped_model(self.op.root, repository / '.tox/phase2_qa', s['project'])
        self.require((model.get('volumes') or {}).get(s['logical'], {}).get('name') == volume,
                     'retained volume does not match the saved task model')
        self.require(any(m.get('type') == 'volume' and m.get('source') == s['logical']
                         and m.get('target') == '/var/lib/mysql'
                         for service in model.get('services', {}).values() for m in service.get('volumes', [])),
                     'saved model does not identify the retained database mount')

    def volume(self):
        s = self.scope
        result = self.op.execute(['volume', 'inspect', s['volume']])
        self.require(result['returncode'] == 0, 'exact retained volume is absent; nothing was created')
        try:
            records = json.loads(result['stdout'])
            self.require(len(records) == 1, 'retained volume identity is ambiguous')
            info = records[0]
            mountpoint = info['Mountpoint']
            expected_labels = {'com.docker.compose.project': s['project'], 'com.docker.compose.volume': s['logical'],
                               'com.docker.compose.config-hash': s['config_hash']}
            self.require(info['Name'] == s['volume'] and info['Driver'] == 'local' and info['Scope'] == 'local'
                         and info['CreatedAt'] == s['created'] and not info.get('Options')
                         and all((info.get('Labels') or {}).get(k) == v for k,v in expected_labels.items())
                         and Path(mountpoint).is_absolute() and ',' not in mountpoint
                         and mountpoint.endswith('/volumes/' + s['volume'] + '/_data'),
                         'retained volume engine metadata does not match the reviewed identity')
        except (ValueError, KeyError, TypeError) as exc:
            raise self.b.BrokerError('retained volume engine identity is unreadable') from exc
        consumers = self.op.execute(['ps', '-aq', '--filter', 'volume=' + s['volume']])
        self.require(consumers['returncode'] == 0 and not consumers['stdout'].strip(),
                     'cold preservation requires an unreferenced volume, including stopped containers')
        return info

    def helper(self, image, info, mode, before=None, output=None):
        s = self.scope
        cfg = dict(mode=mode, source='/source', device=s['device'], inode=s['inode'], uid=os.getuid(), gid=os.getgid(),
                   readonly_required=True, receipt_identity={'volume': s['volume'], 'project': s['project'],
                   'source_read_only': True, 'mountpoint_sha256': hashlib.sha256(info['Mountpoint'].encode()).hexdigest()})
        argv = ['run', '--rm', '--name', 'kandev-volume-preserve-' + uuid.uuid4().hex,
                '--label', 'kandev.volume-preservation=v1', '--network', 'none', '--read-only',
                '--cap-drop', 'ALL', '--cap-add', 'DAC_OVERRIDE', '--security-opt', 'no-new-privileges:true',
                '--user', '0:0', '--mount', 'type=bind,source=' + info['Mountpoint'] + ',target=/source,readonly,bind-propagation=rslave']
        if output is not None:
            host = self.b.translate_to_host(output)
            self.require(',' not in str(host), 'output path cannot contain a mount delimiter')
            identity = output.lstat()
            cfg.update(output='/out', inventory_metadata_sha256=before['source']['inventory_metadata_sha256'],
                       output_device=identity.st_dev, output_inode=identity.st_ino)
            argv += ['--cap-add', 'CHOWN', '--mount', 'type=bind,source=' + str(host) + ',target=/out']
        argv += ['--entrypoint', '/usr/bin/python3', image, '-c', PRESERVATION_HELPER, json.dumps(cfg)]
        result = self.op.execute(argv)
        self.require(result['returncode'] == 0, 'read-only preservation helper failed; any partial output was retained: '
                     + result['stderr'][-512:])
        try:
            return json.loads(result['stdout'])
        except ValueError as exc:
            raise self.b.BrokerError('preservation helper returned an invalid receipt') from exc

    def handle(self, args):
        self.require((len(args) == 4 and args[:3] == ['kandev', 'volume', 'inspect'])
                     or (len(args) == 6 and args[:3] == ['kandev', 'volume', 'preserve'] and args[4] == '--output'),
                     'usage: docker kandev volume inspect <exact-volume> | preserve <exact-volume> --output <new-private-directory>')
        self.owner(args[3])
        self.require(self.b.EXPORT_LOCK.acquire(blocking=False), 'preservation/export is busy; retry later')
        audit_id = str(uuid.uuid4())
        try:
            self.b.audit_compose(self.op.root, self.op.cwd, self.scope['project'], self.scope['project'],
                                 'volume ' + args[2], 'allow', 'preflight', audit_id=audit_id,
                                 command_class='cold-preservation')
            info = self.volume()
            platform = self.op.execute(['inspect', '--type', 'container', 'kandev', '--format', '{{.Image}}'])
            image = platform['stdout'].strip()
            self.require(platform['returncode'] == 0 and re.fullmatch(r'sha256:[0-9a-f]{64}', image),
                         'trusted platform helper image is unavailable')
            result = self.helper(image, info, 'inspect')
            if args[2] == 'preserve':
                candidate = Path(args[5])
                self.require(not candidate.is_absolute() and '..' not in candidate.parts,
                             'preservation output must be relative to the reviewed clone')
                candidate = self.op.cwd / candidate
                parent = self.op.cwd / '.tox/8241_recovery_20261030'
                self.require(candidate.parent == parent and re.fullmatch(r'db-cold-[a-zA-Z0-9_-]{1,80}', candidate.name),
                             'preservation output must be a new db-cold-* directory in the approved recovery folder')
                self.require(parent.resolve(strict=True) == parent and not candidate.exists() and not candidate.is_symlink(),
                             'preservation output already exists or traverses a symlink')
                self.require(self.volume() == info, 'retained volume metadata changed during preflight')
                candidate.mkdir(mode=0o700)
                result = self.helper(image, info, 'preserve', result, candidate)
                self.require(self.volume() == info, 'retained volume metadata/consumers changed; archive is not accepted')
                result['output_directory'] = str(candidate)
            result.update(volume=args[3], project=self.scope['project'], source_read_only=True,
                          mountpoint_sha256=hashlib.sha256(info['Mountpoint'].encode()).hexdigest())
            self.b.audit_compose(self.op.root, self.op.cwd, self.scope['project'], self.scope['project'],
                                 'volume ' + args[2], 'allow', 'ok', audit_id=audit_id,
                                 command_class='cold-preservation')
            return {'returncode': 0, 'stdout': json.dumps(result, sort_keys=True) + '\n', 'stderr': ''}
        except self.b.BrokerError:
            self.b.audit_compose(self.op.root, self.op.cwd, self.scope['project'], self.scope['project'],
                                 'volume ' + args[2], 'deny', 'denied', audit_id=audit_id,
                                 command_class='cold-preservation')
            raise
        finally:
            self.b.EXPORT_LOCK.release()


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
        if args[:2] == ['kandev', 'volume']:
            return VolumePreservation(self).handle(args)
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
