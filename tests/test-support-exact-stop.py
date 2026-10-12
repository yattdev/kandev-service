#!/usr/bin/env python3
"""Preflight rejects PID reuse, foreign group members and new input."""
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch, MagicMock
import urllib.error

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('retire', ROOT / 'scripts/kandev-support-exact-stop.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def denied(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('unsafe preflight accepted')


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    checkout = base / 'owned'
    checkout.mkdir()
    proc = base / 'proc'
    proc.mkdir()
    request = dict(task='task', workspace='workspace', coordinator='coordinator', repo='repo',
                   original=str(checkout), old_session='old', old_execution='old-execution',
                   successor='new', successor_execution='new-execution', provider_pid=12,
                   provider_starttime='1200', launch_pid=10, launch_starttime='1000',
                   controller_pid=2, successor_pid=22, successor_starttime='2200')

    def create(pid, parent, group, session, execution):
        p = proc / str(pid)
        p.mkdir()
        fields = ['S', str(parent), str(group), str(group)] + ['0'] * 15 + [str(pid * 100)]
        role = {10: 'bwrap', 11: 'npm exec @agent', 12: 'codex', 13: 'codex-code-mode'}.get(pid, 'codex')
        (p / 'stat').write_text(str(pid) + ' (' + role + ') ' + ' '.join(fields))
        ids = dict(KANDEV_TASK_ID='task', KANDEV_SESSION_ID=session, KANDEV_INSTANCE_ID=execution)
        (p / 'environ').write_bytes(b'\0'.join((k + '=' + v).encode() for k, v in ids.items()))
        (p / 'cwd').symlink_to(checkout, target_is_directory=True)

    create(10, 2, 10, 'old', 'old-execution')
    create(11, 10, 11, 'old', 'old-execution')
    create(12, 11, 11, 'old', 'old-execution')
    create(13, 12, 13, 'old', 'old-execution')
    create(22, 2, 22, 'new', 'new-execution')
    db_path = base / 'db'
    db = sqlite3.connect(db_path)
    db.executescript('''
    CREATE TABLE tasks(id TEXT,workspace_id TEXT,archived_at TEXT);
    CREATE TABLE task_sessions(id TEXT,task_id TEXT,state TEXT,repository_id TEXT,workspace_path TEXT,task_environment_id TEXT);
    CREATE TABLE task_environment_repos(id TEXT,task_environment_id TEXT,repository_id TEXT,worktree_path TEXT,worktree_id TEXT,status TEXT,deleted_at TEXT);
    CREATE TABLE repositories(id TEXT,workspace_id TEXT,deleted_at TEXT);
    CREATE TABLE executors_running(id TEXT,task_id TEXT,session_id TEXT,agent_execution_id TEXT,runtime TEXT,status TEXT);
    CREATE TABLE queued_messages(id TEXT,task_id TEXT,session_id TEXT,position INTEGER,content TEXT);
    ''')
    db.executemany('INSERT INTO tasks VALUES (?,?,NULL)', [('task','workspace'),('coordinator','workspace')])
    db.execute("INSERT INTO repositories VALUES ('repo','workspace',NULL)")
    db.execute("INSERT INTO task_environment_repos VALUES ('binding','env','repo',?,'incarnation','active',NULL)", (str(checkout),))
    for session, execution in [('old','old-execution'),('new','new-execution')]:
        db.execute('INSERT INTO task_sessions VALUES (?, ?, ?, ?, ?, ?)', (session,'task','WAITING_FOR_INPUT','repo',str(checkout),'env'))
        db.execute('INSERT INTO executors_running VALUES (?,?,?,?,?,?)', (session,'task',session,execution,'standalone','ready'))
    db.commit()
    result = m.snapshot(request, db_path, proc)
    assert result['fifo_count'] == 0
    assert {r['pid'] for r in result['topology']['old_tree']} == {10,11,12,13}
    altered = {**request, 'provider_starttime': 'reused'}
    denied(lambda: m.snapshot(altered, db_path, proc))
    original_stat = (proc / '13/stat').read_text()
    (proc / '13/stat').write_text(original_stat.replace('(codex-code-mode)', '(unique-db-server)'))
    denied(lambda: m.snapshot(request, db_path, proc))
    (proc / '13/stat').write_text(original_stat)
    create(30, 2, 11, 'new', 'new-execution')
    denied(lambda: m.snapshot(request, db_path, proc))
    for p in (proc / '30').iterdir():
        p.unlink()
    (proc / '30').rmdir()
    db.execute("INSERT INTO queued_messages VALUES ('input','task','old',0,'must preserve')")
    db.commit()
    denied(lambda: m.snapshot(request, db_path, proc))
    assert db.execute('SELECT content FROM queued_messages').fetchone()[0] == 'must preserve'
    # Exercise the TERM-only recovery with fake pidfds and lifecycle transport.
    # No actual process or live database is signaled/mutated by this test.
    request['endpoint'] = 'http://127.0.0.1:41006'
    before = result
    before['checkpoint'] = {'head': 'preserved'}
    rows = {r['pid']: r for r in result['topology']['old_tree']}
    rows[22] = result['topology']['successor']
    signals = []
    ended = [False]

    def fake_process(pid):
        if ended[0] and pid != 22:
            raise FileNotFoundError()
        result = dict(rows[pid])
        if pid == 22:
            result['role'] = 'codex'
        return result

    def send(fd, sig):
        signals.append((fd - 1000, sig))
        ended[0] = True

    fake_db = MagicMock()
    fake_db.execute.return_value.fetchone.return_value = [request['endpoint']]
    denied_http = urllib.error.HTTPError(request['endpoint'], 401, 'auth required', {}, None)
    with patch.object(m, 'snapshot', lambda r: {k: v for k, v in before.items() if k != 'checkpoint'}), \
         patch.object(m, 'checkpoint', lambda r: before['checkpoint']), \
         patch.object(m, 'process', fake_process), \
         patch.object(m.sqlite3, 'connect', return_value=fake_db), \
         patch.object(m.urllib.request, 'urlopen', side_effect=denied_http), \
         patch.object(m.os, 'pidfd_open', side_effect=lambda pid: pid + 1000), \
         patch.object(m.os, 'close'), \
         patch.object(m.signal, 'pidfd_send_signal', side_effect=send):
        denied(lambda: m.terminate(request, 'stale-review'))
        assert not signals
        receipt = m.terminate(request, m.sha(before))
        assert receipt['authority_revoked'] and receipt['lifecycle_http_status'] == 401
        assert signals == [(12, m.signal.SIGTERM)]
        assert receipt['signal'] == 'SIGTERM' and 22 not in receipt['signaled_pids']
print('PASS: exact ancestry, PID incarnation, protected successor, foreign group and FIFO fences')
