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
    finally:
        os.chdir(previous_cwd)
print('PASS: independent candidate, preservation, duplicate reservation, receipt, incarnation, writer fence, and storage escape checks')
