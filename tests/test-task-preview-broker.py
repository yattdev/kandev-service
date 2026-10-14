#!/usr/bin/env python3
"""Synthetic acceptance: own-task secret handoff and irreversible scoped revoke."""
import importlib.util
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import time

spec = importlib.util.spec_from_file_location('preview', Path(__file__).parents[1] / 'scripts/kandev-task-preview-broker.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class Denied(Exception):
    pass


with tempfile.TemporaryDirectory(prefix='preview-broker-') as temporary:
    base = Path(temporary)
    root = base / 'task'
    root.mkdir(mode=0o700)
    module.STATE = base / 'private-state'
    module.STATE.mkdir(mode=0o700)
    grant = {'id': '85278886-f97b-4219-b7ba-9182f7059c69', 'task_root': str(root),
             'issued_at': int(time.time()), 'expires_at': int(time.time()) + 86400}

    def private_json(path, value):
        path.write_text(json.dumps(value))
        path.chmod(0o600)

    private_json(module.STATE / 'manifest.json', grant)
    source = root / 'disposable-login.json'
    private_json(source, {'email': 'synthetic@example.invalid', 'password': 'synthetic-test-only'})

    def resolve(path, cwd, task_root):
        candidate = (cwd / path).resolve()
        if not candidate.is_relative_to(task_root):
            raise Denied('outside task')
        return candidate

    broker = SimpleNamespace(BrokerError=Denied, resolve_inside=resolve)

    def denied(task, args):
        try:
            module.handle(broker, task, task, args)
        except Denied:
            return
        raise AssertionError('scope denial expected')

    denied(base, ['stage-login', grant['id'], str(source)])
    denied(root, ['stage-login', 'different-grant', str(source)])
    denied(root, ['stage-login', grant['id'], '../outside.json'])
    # Simulate an ancestor swapped after the existing resolve-inside check.
    outside = base / 'outside'
    outside.mkdir()
    private_json(outside / 'login.json', {'email': 'outside', 'password': 'must-not-deliver'})
    (root / 'raced').symlink_to(outside, target_is_directory=True)
    broker.resolve_inside = lambda *args: root / 'raced/login.json'
    denied(root, ['stage-login', grant['id'], 'raced/login.json'])
    assert not (module.STATE / 'login.json').exists()
    broker.resolve_inside = resolve
    fifo = root / 'fifo'
    os.mkfifo(fifo, 0o600)
    denied(root, ['stage-login', grant['id'], str(fifo)])
    result = module.handle(broker, root, root, ['stage-login', grant['id'], str(source)])
    assert 'synthetic-test-only' not in json.dumps(result)
    assert (module.STATE / 'login.json').read_bytes() == source.read_bytes()
    assert (module.STATE / 'login.json').stat().st_mode & 0o777 == 0o600
    denied(root, ['stage-login', grant['id'], str(source)])  # immutable delivery
    denied(base, ['revoke', grant['id']])
    module.handle(broker, root, root, ['revoke', grant['id']])
    module.handle(broker, root, root, ['revoke', grant['id']])  # idempotent
    denied(root, ['stage-login', grant['id'], str(source)])
    assert (module.STATE / 'revoked').exists()
    assert source.read_text().find('synthetic-test-only') >= 0
print('PASS: exact task/grant, bounded private login delivery, no secret output, immutable stage, scoped idempotent revoke')
