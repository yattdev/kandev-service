#!/usr/bin/env python3
"""Exercise metadata-only adoption and fail-closed retirement attestations."""
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import sqlite3
import subprocess
import tempfile
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
loader = importlib.machinery.SourceFileLoader('registration', str(ROOT/'scripts/kandev-workspace-registration.py'))
spec = importlib.util.spec_from_loader(loader.name, loader)
m = importlib.util.module_from_spec(spec)
loader.exec_module(m)


def denied(call):
    try:
        call()
    except ValueError:
        return
    raise AssertionError('invalid workspace repair accepted')


def run(*args):
    subprocess.run(args, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)


with tempfile.TemporaryDirectory() as tmp:
    base = Path(tmp)
    tasks = base/'tasks'
    root = tasks/'task-owned'
    root.mkdir(parents=True)
    retired, adopted, original = root/'old', root/'clone', base/'source'
    retired.mkdir()
    adopted.mkdir()
    original.mkdir()
    for path in (adopted, original):
        run('/usr/bin/git', 'init', '-b', 'fix', str(path))
        run('/usr/bin/git', '-C', str(path), 'config', 'remote.origin.url', 'https://example.invalid/owned/repo.git')
    marker = retired/'.git'
    missing = original/'.git/worktrees/missing'
    marker.write_text('gitdir: '+str(missing)+'\n')
    (retired/'db_backups.sql').write_bytes(b'sensitive disposable test fixture')
    (adopted/'changed.py').write_text('uncommitted content\n')
    (adopted/'.env.local').write_text('private disposable fixture\n')
    before = {p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    db_path = base/'data/kandev.db'
    db_path.parent.mkdir()
    db = m.connect(db_path, True)
    db.executescript('''
    CREATE TABLE tasks(id TEXT,workspace_id TEXT,archived_at TEXT);
    CREATE TABLE task_sessions(id TEXT,task_id TEXT,state TEXT,task_environment_id TEXT,workspace_path TEXT);
    CREATE TABLE task_environments(id TEXT,task_id TEXT,status TEXT,executor_type TEXT,task_dir_name TEXT,workspace_path TEXT);
    CREATE TABLE task_environment_repos(id TEXT,task_environment_id TEXT,repository_id TEXT,worktree_id TEXT,worktree_path TEXT,worktree_branch TEXT,status TEXT,deleted_at TEXT,position INTEGER,updated_at TEXT);
    CREATE TABLE task_repositories(id TEXT,task_id TEXT,repository_id TEXT,checkout_branch TEXT,position INTEGER,updated_at TEXT);
    CREATE TABLE repositories(id TEXT,workspace_id TEXT,local_path TEXT,deleted_at TEXT);
    CREATE TABLE executors_running(id TEXT,task_id TEXT,session_id TEXT,status TEXT);
    ''')
    db.execute('INSERT INTO tasks VALUES (?,?,NULL)', ('task','workspace'))
    db.execute('INSERT INTO task_sessions VALUES (?,?,?,?,?)', ('session','task','WAITING_FOR_INPUT','env',str(root)))
    db.execute('INSERT INTO task_environments VALUES (?,?,?,?,?,?)', ('env','task','ready','worktree',root.name,str(root)))
    db.execute('INSERT INTO repositories VALUES (?,?,?,NULL)', ('repo','workspace',str(original)))
    db.execute('INSERT INTO task_environment_repos VALUES (?,?,?,?,?,?,?,NULL,?,?)', ('binding','env','repo','same-worktree-id',str(retired),'old','active',1,'prior'))
    db.execute('INSERT INTO task_environment_repos VALUES (?,?,?,?,?,?,?,NULL,?,?)', ('sibling','env','repo','sibling-id',str(root/'sibling'),'main','active',0,'prior'))
    db.execute('INSERT INTO task_repositories VALUES (?,?,?,?,?,?)', ('task-repo','task','repo','fix',1,'prior'))
    db.execute('INSERT INTO task_repositories VALUES (?,?,?,?,?,?)', ('task-sibling','task','repo','main',0,'prior'))
    db.execute('INSERT INTO executors_running VALUES (?,?,?,?)', ('execution','task','session','ready'))
    db.commit()
    plan = m.plan
    m.plan = lambda db,*args: plan(db,*args,tasks_base=tasks)
    arguments = SimpleNamespace(task='task', session='session', retire=str(retired), checkout=str(adopted), apply=False)
    assert m.apply(db_path, arguments)['mode'] == 'preview'
    assert not db.execute("SELECT 1 FROM sqlite_master WHERE name=?", (m.TABLE,)).fetchone()
    denied(lambda:m.plan(db,'task','other-session',retired,adopted))
    denied(lambda:m.plan(db,'task','session',retired,original))
    run('/usr/bin/git','-C',str(adopted),'config','remote.origin.url','https://example.invalid/other/repo.git')
    denied(lambda:m.plan(db,'task','session',retired,adopted))
    run('/usr/bin/git','-C',str(adopted),'config','remote.origin.url','https://example.invalid/owned/repo.git')
    db.execute("UPDATE executors_running SET status='running'")
    db.commit()
    denied(lambda:m.apply(db_path,arguments))
    db.execute("UPDATE executors_running SET status='ready'")
    db.commit()
    arguments.apply=True
    applied=m.apply(db_path,arguments)
    assert Path(applied['backup_path']).stat().st_mode & 0o777 == 0o600
    assert db.execute('PRAGMA quick_check').fetchone()[0] == 'ok'
    binding=db.execute("SELECT * FROM task_environment_repos WHERE id='binding'").fetchone()
    assert binding['worktree_id']=='same-worktree-id' and binding['worktree_path']==str(adopted) and binding['position']==0
    assert db.execute("SELECT position FROM task_environment_repos WHERE id='sibling'").fetchone()[0]==1
    assert db.execute("SELECT COUNT(*) FROM task_sessions").fetchone()[0]==1
    assert db.execute("SELECT workspace_path FROM task_sessions").fetchone()[0]==str(root)
    assert m.retired_marker(db,root,marker)
    assert m.adopted_checkout(db,adopted)
    assert not m.adopted_checkout(db,original)
    run('/usr/bin/git','-C',str(adopted),'config','remote.origin.url','https://example.invalid/foreign/repo.git')
    denied(lambda:m.adopted_checkout(db,adopted))
    run('/usr/bin/git','-C',str(adopted),'config','remote.origin.url','https://example.invalid/owned/repo.git')
    assert not m.retired_marker(db,root,adopted/'.git')
    assert not m.retired_marker(db,base,marker)
    marker.write_text('gitdir: /forged/metadata\n')
    denied(lambda:m.retired_marker(db,root,marker))
    marker.write_bytes(before['old/.git'])
    missing.mkdir(parents=True)
    denied(lambda:m.retired_marker(db,root,marker))
    missing.rmdir()
    db.execute("UPDATE task_environment_repos SET worktree_path=? WHERE id='binding'",(str(retired),))
    denied(lambda:m.retired_marker(db,root,marker))
    db.rollback()
    assert m.retired_marker(db,root,marker)
    after={p.relative_to(root).as_posix():p.read_bytes() for p in root.rglob('*') if p.is_file()}
    assert before==after, 'repair changed checkout contents'
    with sqlite3.connect(applied['backup_path']) as saved:
        assert saved.execute("SELECT worktree_path FROM task_environment_repos WHERE id='binding'").fetchone()[0]==str(retired)
    assert m.rollback(db_path,applied['repair_id'])['mode']=='rolled-back'
    assert db.execute("SELECT worktree_path FROM task_environment_repos WHERE id='binding'").fetchone()[0]==str(retired)
    assert not m.retired_marker(db,root,marker)
    db.close()

print('PASS: in-place adoption preserves contents and identities; retirement remains task-scoped and fails closed')
