"""Exact-task login staging and revocation; no provider or routing operations."""
from __future__ import annotations
import json
import os
from pathlib import Path
import stat
import time

STATE = Path('/run/kandev-task-preview')


def task_file(path: Path, root: Path) -> int:
    # Resolve-inside alone cannot defeat a task swapping an ancestor after its
    # path check. Walk anchored directory descriptors without following links.
    parts = path.relative_to(root).parts
    if not parts or any(part in ('.', '..') for part in parts):
        raise ValueError('exact task-private file required')
    directory = os.open(root, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        for part in parts[:-1]:
            child = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW, dir_fd=directory)
            os.close(directory)
            directory = child
        return os.open(parts[-1], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory)
    finally:
        os.close(directory)


def private_read(path: Path, maximum: int, root: Path | None = None) -> bytes:
    descriptor = task_file(path, root) if root else os.open(path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    with os.fdopen(descriptor, 'rb') as stream:
        info = os.fstat(stream.fileno())
        if (not stat.S_ISREG(info.st_mode) or info.st_uid not in (0, os.geteuid())
                or info.st_mode & 0o077 or info.st_size > maximum):
            raise ValueError('private regular file required')
        return stream.read(maximum + 1)


def handle(broker, root: Path, cwd: Path, args: list[str]):
    # The parent has already verified the guard's exact task-root token.
    # Neither callers nor environment variables can select this private store.
    try:
        directory = STATE.lstat()
        if (not stat.S_ISDIR(directory.st_mode) or directory.st_mode & 0o077
                or directory.st_uid not in (0, os.geteuid())):
            raise ValueError('private preview state required')
        grant = json.loads(private_read(STATE / 'manifest.json', 16384))
        if (len(args) not in (2, 3) or args[1] != grant['id']
                or str(root) != grant['task_root']):
            raise ValueError('exact owner task and grant required')
        if args[0] == 'revoke' and len(args) == 2:
            try:
                descriptor = os.open(STATE / 'revoked', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            except FileExistsError:
                pass
            else:
                with os.fdopen(descriptor, 'wb') as stream:
                    stream.write(b'revoked\n')
                    stream.flush()
                    os.fsync(stream.fileno())
            result = {'grant_id': grant['id'], 'revoked': True}
        elif args[0] == 'stage-login' and len(args) == 3:
            if STATE.joinpath('revoked').exists() or not grant['issued_at'] <= time.time() < grant['expires_at']:
                raise ValueError('active preview grant required')
            source = broker.resolve_inside(args[2], cwd, root)
            body = private_read(source, 8192, root)
            login = json.loads(body)
            if (not isinstance(login, dict) or set(login) != {'email', 'password'}
                    or any(not isinstance(v, str) or not v or len(v) > 2048 for v in login.values())):
                raise ValueError('existing disposable trial login required')
            # Exact task-private credentials only. Never print values or hashes.
            descriptor = os.open(STATE / 'login.json', os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(descriptor, 'wb') as stream:
                stream.write(body)
                stream.flush()
                os.fsync(stream.fileno())
            result = {'grant_id': grant['id'], 'login_delivery_ready': True}
        else:
            raise ValueError('unsupported preview operation')
    except (OSError, ValueError, KeyError, TypeError):
        raise broker.BrokerError('preview operation unavailable or outside exact owner grant') from None
    return {'returncode': 0, 'stdout': json.dumps(result) + '\n', 'stderr': ''}
