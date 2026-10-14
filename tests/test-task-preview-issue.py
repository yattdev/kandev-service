#!/usr/bin/env python3
"""Synthetic issuer verification: immutable target, TLS listener and fixed TTL."""
from contextlib import redirect_stdout
import hashlib
from importlib.machinery import SourceFileLoader
import io
import json
from pathlib import Path
import tempfile
from unittest.mock import patch

root = Path(__file__).parents[1]
module = SourceFileLoader('preview_issue', str(root / 'scripts/kandev-task-preview-issue')).load_module()
template = json.loads((root / 'support-evidence/task-preview-85278886-template.json').read_text())
template.update(main_origin='https://main.example.invalid', preview_origin='https://preview.example.invalid:59433', listen_address='10.23.4.5:59433')

with tempfile.TemporaryDirectory(prefix='preview-issuer-') as tmp:
    base = Path(tmp)
    models = base / 'agent-docker-models'
    name = hashlib.sha256(template['project'].encode()).hexdigest() + '.json'
    model = models / hashlib.sha256(template['task_root'].encode()).hexdigest() / name
    claim = models / 'projects' / name
    body = json.dumps({key: template[key] for key in ('task_root', 'cwd', 'project')}).encode()
    for path in (model, claim):
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        path.write_bytes(body)
        path.chmod(0o600)
    template['model_sha256'] = hashlib.sha256(body).hexdigest()
    source = base / 'reviewed.json'
    source.write_text(json.dumps(template))
    record = dict(id=template['container_id'], image=template['image_id'], running=True,
                  project=template['project'], service=template['service'],
                  started_at='2023-01-01T00:00:00.123456789Z',
                  ports={'59430/tcp': [{'HostIp': '127.0.0.1', 'HostPort': '59432'}]})

    def inspect(args, **kwargs):
        assert args[-1] == template['container_id']
        assert kwargs['env']['DOCKER_CONFIG'] == '/run/kandev-preview-empty-docker-config'
        assert set(kwargs['env']) == {'PATH', 'DOCKER_HOST', 'DOCKER_CONFIG'}
        return json.dumps(record).encode()

    output = io.StringIO()
    with patch.object(module.subprocess, 'check_output', inspect), redirect_stdout(output):
        module.issue(source, base / 'state', models)
    receipt = json.loads(output.getvalue())
    assert receipt['expires_at'] - receipt['issued_at'] == 86400
    assert not receipt['listener_started'] and not receipt['capability_delivered']
    assert (base / 'state/key').stat().st_size == 32
    assert (base / 'state/key').stat().st_mode & 0o777 == 0o600
    assert 'key' not in receipt and 'password' not in output.getvalue()
    manifest = json.loads((base / 'state/manifest.json').read_text())
    assert manifest['model_path'] == str(model)
    assert manifest.get('container_started_at') == record['started_at']
    with patch.object(module.subprocess, 'check_output', inspect):
        try:
            module.issue(source, base / 'state', models)
        except ValueError:
            pass
        else:
            raise AssertionError('renewal/reissue accepted')
    for name, change in [('public', {'listen_address': '0.0.0.0:59433'}),
                         ('cookie-host', {'preview_origin': 'https://main.example.invalid:59433'}),
                         ('plaintext', {'main_origin': 'http://main.example.invalid'})]:
        source.write_text(json.dumps(template | change))
        try:
            with patch.object(module.subprocess, 'check_output', inspect):
                module.issue(source, base / name, models)
        except ValueError:
            pass
        else:
            raise AssertionError('unsafe origin/listener accepted')
        assert not (base / name).exists()
    source.write_text(json.dumps(template))
    for number, bad_start in enumerate(['not-a-timestamp', '2999-01-01T00:00:00Z']):
        record['started_at'] = bad_start
        destination = base / ('bad-start-' + str(number))
        try:
            with patch.object(module.subprocess, 'check_output', inspect):
                module.issue(source, destination, models)
        except ValueError:
            pass
        else:
            raise AssertionError('invalid container boot accepted')
        assert not destination.exists()
print('PASS: exact target, private TLS listener, no renewal, private key, fixed 24h, content-free receipt, no service start')
