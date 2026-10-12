#!/usr/bin/env python3
"""Synthetic candidate creation, preservation, and fail-closed acceptance."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
source = ROOT / 'scripts/kandev-task-candidate.py'
spec = importlib.util.spec_from_file_location('candidate', source)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


def run(path, *args):
    return subprocess.check_output(['/usr/bin/git', '-C', str(path), *args], stderr=subprocess.DEVNULL).decode().strip()


def denied(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('invalid operation accepted')


with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    upstream = root / 'source'
    upstream.mkdir()
    run(upstream, 'init', '-b', 'main')
    run(upstream, 'config', 'user.name', 'Synthetic')
    run(upstream, 'config', 'user.email', 'synthetic@example.invalid')
    (upstream / '.gitignore').write_text('.kandev/hqa/\n')
    (upstream / '.kandev').mkdir()
    (upstream / '.kandev/tracked-config').write_text('preserve tracked configuration\n')
    (upstream / 'file').write_text('base\n')
    run(upstream, 'add', '.')
    run(upstream, 'commit', '-m', 'base')
    base = run(upstream, 'rev-parse', 'HEAD')
    original = root / 'tasks/task-owned/repo'
    original.parent.mkdir(parents=True)
    run(upstream, 'worktree', 'add', '-b', 'feature/original', str(original))
    (original / 'PROMPT.md').write_text('preserve untracked operator data\n')
    (original / 'file').write_text('original dirty source\n')
    run(original, 'branch', 'hqa/candidate', base)
    run(original, 'config', 'remote.upstream.url', 'https://github.com/kdlbs/kandev.git')
    db_path = root / 'metadata.db'
    db = sqlite3.connect(db_path)
    db.executescript('''
    CREATE TABLE tasks(id TEXT,workspace_id TEXT,archived_at TEXT);
    CREATE TABLE task_sessions(id TEXT,task_id TEXT,repository_id TEXT,task_environment_id TEXT,workspace_path TEXT,state TEXT);
    CREATE TABLE task_environments(id TEXT,task_id TEXT,task_dir_name TEXT,status TEXT,executor_type TEXT);
    CREATE TABLE task_environment_repos(id TEXT,task_environment_id TEXT,repository_id TEXT,worktree_id TEXT,worktree_path TEXT,worktree_branch TEXT,updated_at TEXT,status TEXT,deleted_at TEXT);
    CREATE TABLE repositories(id TEXT,workspace_id TEXT,local_path TEXT,deleted_at TEXT);
    CREATE TABLE task_repositories(id TEXT,task_id TEXT,repository_id TEXT);
    CREATE TABLE executors_running(id TEXT,task_id TEXT,session_id TEXT,status TEXT,local_pid INTEGER,pid INTEGER);
    ''')
    db.execute("INSERT INTO tasks VALUES ('task','workspace',NULL)")
    db.execute("INSERT INTO task_sessions VALUES ('hqa','task','repo','env',?,'WAITING_FOR_INPUT')", (str(original),))
    db.execute("INSERT INTO task_environments VALUES ('env','task','task-owned','ready','worktree')")
    db.execute("INSERT INTO task_environment_repos VALUES ('binding','env','repo','incarnation',?,'feature/original','unchanged','active',NULL)", (str(original),))
    db.execute("INSERT INTO repositories VALUES ('repo','workspace',?,NULL)", (str(upstream),))
    db.execute("INSERT INTO task_repositories VALUES ('task-repo','task','repo')")
    db.execute("INSERT INTO executors_running VALUES ('hqa','task','hqa','ready',123,0)")
    db.commit()
    args = SimpleNamespace(operation='provision', task='task', session='hqa', workspace='workspace', repo='repo',
                           original=str(original), original_head=base, base=base, branch='hqa/candidate',
                           slot='candidate', upstream='https://github.com/kdlbs/kandev.git', receipt=None, receipt_sha256=None)
    real_git, real_connect, real_ownership, real_access = m.git, sqlite3.connect, m.ownership, os.access

    def transport(path, *arguments):
        if arguments[0] == 'ls-remote':
            return (base + '\trefs/heads/main\n').encode()
        if arguments[0] == 'clone':
            modified = list(arguments)
            modified[-2] = str(upstream)
            modified.insert(1, '--no-local')
            output = real_git(path, *modified)
            real_git(Path(modified[-1]), 'config', 'remote.upstream.url', args.upstream)
            return output
        return real_git(path, *arguments)

    previous_cwd = Path.cwd()
    os.chdir(original)
    try:
        with patch.dict(os.environ, KANDEV_AGENT_GUARD_ACTIVE='1', KANDEV_AGENT_GUARD_SCOPE='project'), \
             patch.object(m, 'git', transport), \
             patch.object(m, 'ownership', lambda db, a, p: real_ownership(db, a, p, root / 'tasks')), \
             patch.object(m.sqlite3, 'connect', lambda *a, **kw: real_connect(db_path)), \
             patch.object(m.os, 'access', lambda p, mode: False if Path(p) == upstream / '.git/worktrees' else real_access(p, mode)):
            output = io.StringIO()
            with contextlib.redirect_stdout(output):
                m.operate(args, source.read_bytes())
            record = json.loads(output.getvalue())
            assert record['status'] == 'guard_verified'
            assert record['base'] == base
            assert (original / 'PROMPT.md').read_text() == 'preserve untracked operator data\n'
            assert (original / 'file').read_text() == 'original dirty source\n'
            denied(lambda: m.operate(args, source.read_bytes()))
            args.operation, args.receipt = 'verify', record['receipt']
            args.receipt_sha256 = record['receipt_sha256']
            # Existing HQA may resume its source turn; process identity persists.
            db.execute("UPDATE task_sessions SET state='RUNNING' WHERE id='hqa'")
            db.commit()
            with contextlib.redirect_stdout(io.StringIO()):
                m.operate(args, source.read_bytes())
            args.receipt = 'wrong'
            denied(lambda: m.operate(args, source.read_bytes()))
            args.receipt = record['receipt']
            db.execute("UPDATE task_environment_repos SET worktree_id='replacement'")
            db.commit()
            denied(lambda: m.operate(args, source.read_bytes()))
            db.execute("UPDATE task_environment_repos SET worktree_id='incarnation'")
            db.execute("INSERT INTO executors_running VALUES ('other','task','main','running',456,0)")
            db.commit()
            denied(lambda: m.operate(args, source.read_bytes()))
            candidate = Path(record['candidate'])
            (candidate / '.git/objects/info/alternates').write_text(str(upstream / '.git/objects'))
            denied(lambda: m.verify_candidate(candidate, record))
            link = original / '.kandev/hqa/escape'
            link.symlink_to(upstream, target_is_directory=True)
            denied(lambda: m.plain(link))
            # Exercise append-only session transfer on this synthetic clone.
            # The original source and untracked prompt remain untouched.
            (candidate / '.git/objects/info/alternates').unlink()
            link.unlink()
            db.execute("DELETE FROM executors_running WHERE id='other'")
            db.execute("ALTER TABLE executors_running ADD COLUMN agent_execution_id TEXT")
            db.execute("ALTER TABLE executors_running ADD COLUMN updated_at TEXT")
            db.execute("UPDATE executors_running SET status='failed',local_pid=0,agent_execution_id='old-execution',updated_at='retired' WHERE id='hqa'")
            db.execute("UPDATE task_sessions SET state='FAILED' WHERE id='hqa'")
            db.execute("INSERT INTO task_sessions VALUES ('successor','task','repo','env',?,'WAITING_FOR_INPUT')", (str(original),))
            db.execute("INSERT INTO executors_running VALUES ('successor','task','successor','ready',123,0,'new-execution','live')")
            db.commit()
            run(candidate, 'config', 'user.name', 'Synthetic')
            run(candidate, 'config', 'user.email', 'synthetic@example.invalid')
            (candidate / 'candidate-change').write_text('synthetic local commit\n')
            run(candidate, 'add', 'candidate-change')
            run(candidate, 'commit', '-m', 'synthetic candidate checkpoint')
            head = run(candidate, 'rev-parse', 'HEAD')
            transfer_source = ROOT / 'scripts/kandev-task-candidate-transfer.py'
            transfer_spec = importlib.util.spec_from_file_location('transfer', transfer_source)
            t = importlib.util.module_from_spec(transfer_spec)
            transfer_spec.loader.exec_module(t)
            predecessor = json.loads((original / '.kandev/hqa/.candidate-lease/receipt.json').read_text())
            immutable = (original / '.kandev/hqa/.candidate-lease/receipt.json').read_bytes()
            authorization = dict(receipt='retirement', authority_revoked=True, task='task', workspace='workspace',
                                 old_session='hqa', old_execution='old-execution', successor='successor',
                                 successor_execution='new-execution', checkpoint=dict(head=head, original_head=base,
                                 reservation_sha256=m.digest(m.encoded(predecessor))))
            authorization['receipt_sha256'] = m.digest(m.encoded(authorization))
            successor_process = dict(pid=22, ppid=1, starttime='fixed', ids=dict(KANDEV_TASK_ID='task',
                                      KANDEV_SESSION_ID='successor', KANDEV_INSTANCE_ID='new-execution'))
            t.__retirement_receipt__ = authorization
            t.__successor_process__ = successor_process
            preflight = dict(topology=dict(successor=successor_process))
            authorization.pop('receipt_sha256')
            authorization['prior_snapshot_sha256'] = m.digest(m.encoded(preflight))
            authorization['receipt_sha256'] = m.digest(m.encoded(authorization))
            t.__retirement_preflight__ = preflight
            transfer_args = SimpleNamespace(**vars(args))
            transfer_args.operation = 'prepare'
            transfer_args.session = 'successor'
            transfer_args.head = head
            transfer_args.reservation_sha256 = m.digest(m.encoded(predecessor))
            transfer_args.retirement_sha256 = authorization['receipt_sha256']
            real_load = t.load_original

            def synthetic_load(*parameters):
                lease, clone, prior, module = real_load(*parameters)
                module['ownership'] = lambda db, a, p: real_ownership(db, a, p, root / 'tasks')
                return lease, clone, prior, module

            def synthetic_process(pid):
                return successor_process if pid == 22 else dict(pid=pid, ppid=22)

            with patch.object(t, 'load_original', synthetic_load), patch.object(t, 'process_identity', synthetic_process), \
                 patch.object(t, 'process_reference_current', lambda reference: None):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    t.operate(transfer_args, transfer_source.read_bytes())
                transferred = json.loads(output.getvalue())
                assert transferred['original_receipt'] == predecessor['receipt']
                assert transferred['head'] == head
                assert immutable == (original / '.kandev/hqa/.candidate-lease/receipt.json').read_bytes()
                denied(lambda: t.operate(transfer_args, transfer_source.read_bytes()))
                transfer_args.operation = 'verify'
                transfer_args.receipt = transferred['receipt']
                transfer_args.receipt_sha256 = transferred['receipt_sha256']
                with patch.dict(os.environ, KANDEV_TASK_ID='task', KANDEV_SESSION_ID='successor', KANDEV_INSTANCE_ID='new-execution'):
                    with contextlib.redirect_stdout(io.StringIO()):
                        t.operate(transfer_args, transfer_source.read_bytes())
                    with patch.object(t, 'process_identity', lambda pid: dict(pid=pid, ppid=1)):
                        denied(lambda: t.caller_anchor(successor_process))
                    transfer_args.receipt_sha256 = 'stale'
                    denied(lambda: t.operate(transfer_args, transfer_source.read_bytes()))
                    transfer_args.receipt_sha256 = transferred['receipt_sha256']
                    db.execute("UPDATE executors_running SET status='ready',local_pid=123 WHERE id='hqa'")
                    db.commit()
                    denied(lambda: t.operate(transfer_args, transfer_source.read_bytes()))
                assert run(candidate, 'rev-parse', 'HEAD') == head
                assert (original / 'PROMPT.md').read_text() == 'preserve untracked operator data\n'
    finally:
        os.chdir(previous_cwd)
print('PASS: candidate preservation, append-only transfer, receipt/ancestry/incarnation fences, old revival and storage escapes')
