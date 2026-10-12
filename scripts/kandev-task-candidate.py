#!/usr/bin/env python3
"""Provision one independent candidate through an existing task guard.

Run this file on stdin to Python inside kandev-agent-guard, from the original
checkout. No service installation, shared Git registration, or database write
is needed. A failed reservation is retained for reviewed reconciliation.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
import uuid


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(value):
    return hashlib.sha256(value).hexdigest()


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def git(path, *args):
    environment = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    environment.update(GIT_OPTIONAL_LOCKS="0", GIT_TERMINAL_PROMPT="0",
                       GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL="/dev/null")
    command = ["/usr/bin/git", "--no-optional-locks", "-c", "safe.directory=*",
               "-c", "credential.helper=", "-c", "core.hooksPath=/dev/null",
               "-c", "core.fsmonitor=false", "-C", str(path), *args]
    result = subprocess.run(command, env=environment, capture_output=True, timeout=600)
    require(result.returncode == 0, "Git operation failed; diagnostics withheld")
    return result.stdout


def text_git(path, *args):
    return git(path, *args).decode().strip()


def plain(path):
    require(path.is_absolute() and path.resolve() == path, "path contains a symlink or traversal")
    for parent in (path, *path.parents):
        require(not parent.is_symlink(), "symlink in candidate path")


def ownership(database, args, original, tasks_base=Path('/data/tasks')):
    row = database.execute("""
        SELECT t.workspace_id, te.id AS environment_id, te.task_dir_name,
               er.id AS binding_id, er.worktree_id, er.worktree_path,
               er.worktree_branch, er.updated_at AS binding_updated_at,
               r.local_path AS source
        FROM tasks t JOIN task_sessions ts ON ts.task_id=t.id
        JOIN task_environments te ON te.id=ts.task_environment_id AND te.task_id=t.id
        JOIN task_environment_repos er ON er.task_environment_id=te.id
        JOIN repositories r ON r.id=er.repository_id AND r.workspace_id=t.workspace_id
        WHERE t.id=? AND ts.id=? AND r.id=? AND t.archived_at IS NULL
          AND ts.state IN ('WAITING_FOR_INPUT','RUNNING') AND te.status='ready'
          AND te.executor_type='worktree' AND er.status='active'
          AND er.deleted_at IS NULL AND r.deleted_at IS NULL
          AND er.worktree_path=? AND ts.workspace_path=er.worktree_path
    """, (args.task, args.session, args.repo, str(original))).fetchall()
    require(len(row) == 1, "exact live task/session/repository binding is unavailable")
    result = dict(row[0])
    require(result["workspace_id"] == args.workspace, "workspace differs")
    require(original.parent == tasks_base / result['task_dir_name'], "not the exact task checkout")
    active = database.execute("""SELECT session_id,status FROM executors_running
        WHERE task_id=? AND status IN ('starting','prepared','running','ready')""", (args.task,)).fetchall()
    require(len(active) == 1 and active[0]['session_id'] == args.session,
            "HumanQA is not the sole active executor; preserve writer fences")
    for variable, expected in (("KANDEV_TASK_ID", args.task), ("KANDEV_SESSION_ID", args.session),
                               ("KANDEV_WORKSPACE_ID", args.workspace)):
        require(not os.environ.get(variable) or os.environ[variable] == expected, "exported caller identity differs")
    return result


def original_snapshot(database, args, original, binding):
    marker = original / '.git'
    require(marker.is_file() and not marker.is_symlink(), "original is not a linked checkout")
    admin = Path(text_git(original, 'rev-parse', '--absolute-git-dir'))
    common = Path(text_git(original, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    require(common == Path(binding['source']) / '.git', "source common directory differs")
    require(admin.parent == common / 'worktrees', "original administration is outside its source")
    require((admin / 'gitdir').read_text().strip() == str(marker), "original backlink differs")
    require(text_git(original, 'rev-parse', 'HEAD') == args.original_head, "original HEAD differs")
    require(text_git(original, 'symbolic-ref', '--short', 'HEAD') == binding['worktree_branch'], "original branch differs")
    require(text_git(original, 'rev-parse', 'refs/heads/' + args.branch) == args.base,
            "preserved branch from failed worktree attempt differs")
    require(text_git(original, 'config', '--get', 'remote.upstream.url') == args.upstream,
            "original canonical remote differs")
    require(not os.access(common / 'worktrees', os.W_OK), "shared worktree registry is writable")
    # Record tracked and visible untracked files, including PROMPT.md. Ignored
    # runtime/build trees are not traversed or touched by this capability.
    files = git(original, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0')
    contents = {}
    for name in files:
        if not name:
            continue
        relative = os.fsdecode(name)
        require(not relative.startswith(('.kandev/hqa/' + args.slot + '/', '.kandev/hqa/.candidate-lease/')),
                "candidate slot or lease is not ignored")
        path = original / relative
        if path.is_symlink():
            contents[relative] = ['symlink', os.readlink(path)]
        elif path.is_file():
            contents[relative] = ['file', digest(path.read_bytes()), path.stat().st_mode]
        else:
            contents[relative] = ['missing']
    # Hash the exact original administration and all shared refs, never a
    # sibling's administration directory. No write command targets these paths.
    metadata = {}
    for base in (admin, common / 'refs'):
        for path in sorted(base.rglob('*')):
            if path.is_file() and not path.is_symlink():
                metadata[str(path)] = digest(path.read_bytes())
    for path in (marker, common / 'config', common / 'HEAD', common / 'packed-refs'):
        metadata[str(path)] = digest(path.read_bytes()) if path.is_file() else None
    shared_inventory = {}
    for directory, children, names in os.walk(common):
        if Path(directory) == common:
            children[:] = [name for name in children if name != 'worktrees']
        for name in names:
            path = Path(directory) / name
            stat = path.lstat()
            shared_inventory[str(path)] = [stat.st_size, stat.st_mtime_ns, stat.st_mode, stat.st_ino]
    state = {}
    for table, column in (('tasks', 'id'), ('task_sessions', 'task_id'),
                          ('executors_running', 'task_id'), ('task_environments', 'task_id'),
                          ('task_repositories', 'task_id')):
        state[table] = [dict(r) for r in database.execute(f'SELECT * FROM {table} WHERE {column}=? ORDER BY id', (args.task,))]
    fences = dict(sessions=[r for r in state['task_sessions'] if r['id'] != args.session],
                  executors=[r for r in state['executors_running'] if r['session_id'] != args.session])
    owner = next(r for r in state['task_sessions'] if r['id'] == args.session)
    owner_execution = next(r for r in state['executors_running'] if r['session_id'] == args.session)
    # A subsequent source turn can change its own RUNNING/idle state. Its exact
    # binding/process incarnation and the other writers' fences must persist.
    fences['owner'] = {k: owner[k] for k in ('id', 'task_id', 'repository_id', 'task_environment_id', 'workspace_path')}
    fences['owner_execution'] = {k: owner_execution[k] for k in ('id', 'session_id', 'local_pid', 'pid')}
    return dict(marker_sha256=digest(marker.read_bytes()), files_sha256=digest(encoded(contents)),
                git_metadata_sha256=digest(encoded(metadata)), shared_inventory_sha256=digest(encoded(shared_inventory)),
                fences_sha256=digest(encoded(fences)), task_state_sha256=digest(encoded(state)))


def verify_candidate(candidate, record):
    plain(candidate)
    admin = candidate / '.git'
    require(admin.is_dir() and not admin.is_symlink(), "candidate administration is not independent")
    require(text_git(candidate, 'rev-parse', '--absolute-git-dir') == str(admin), "candidate Git directory escapes")
    require(text_git(candidate, 'rev-parse', '--path-format=absolute', '--git-common-dir') == str(admin), "candidate common directory escapes")
    require(not (admin / 'objects/info/alternates').exists() and not (admin / 'commondir').exists(), "candidate shares Git storage")
    require(text_git(candidate, 'rev-parse', 'HEAD') == record['base'], "candidate HEAD differs from base")
    require(text_git(candidate, 'symbolic-ref', '--short', 'HEAD') == record['branch'], "candidate branch lease differs")
    require(text_git(candidate, 'config', '--get', 'remote.upstream.url') == record['upstream'], "candidate canonical remote differs")
    require(text_git(candidate, 'rev-parse', 'refs/remotes/upstream/main') == record['base'], "candidate upstream/main differs")
    require(not git(candidate, 'status', '--porcelain'), "candidate source is dirty")
    marker = admin / 'kandev-candidate.json'
    require(marker.is_file() and not marker.is_symlink() and json.loads(marker.read_text()) == record,
            "candidate ownership marker differs")
    require(os.access(admin, os.W_OK) and os.access(candidate, os.W_OK), "candidate is not writable in this caller")


def operate(args, helper):
    require(os.environ.get('KANDEV_AGENT_GUARD_ACTIVE') == '1'
            and os.environ.get('KANDEV_AGENT_GUARD_SCOPE') == 'project', "run inside the existing task guard")
    original = Path(args.original)
    plain(original)
    require(Path.cwd() == original, "invoke from the original checkout")
    require(re.fullmatch(r'[0-9a-f]{40}', args.base) and re.fullmatch(r'[0-9a-f]{40}', args.original_head), "full commit IDs required")
    require(re.fullmatch(r'[a-zA-Z0-9_-]+', args.slot), "invalid candidate slot")
    require(args.upstream == 'https://github.com/kdlbs/kandev.git', "only the reviewed canonical public remote is supported")
    text_git(original, 'check-ref-format', '--branch', args.branch)
    candidate = original / '.kandev/hqa' / args.slot
    lease = original / '.kandev/hqa/.candidate-lease'
    plain(candidate)
    plain(lease)
    require(text_git(original, 'check-ignore', str(candidate)), "candidate must be ignored by original checkout")
    database = sqlite3.connect('file:/data/data/kandev.db?mode=ro', uri=True, timeout=10)
    database.row_factory = sqlite3.Row
    binding = ownership(database, args, original)
    before = original_snapshot(database, args, original, binding)
    identity = {k: getattr(args, k) for k in ('task', 'session', 'workspace', 'repo', 'original', 'original_head', 'base', 'branch', 'upstream', 'slot')}
    if args.operation == 'provision':
        require(not candidate.exists() and not lease.exists(), "existing candidate or reservation requires reconciliation; do not repeat provisioning")
        remote = text_git(original, 'ls-remote', '--exit-code', args.upstream, 'refs/heads/main').split()
        require(remote == [args.base, 'refs/heads/main'], "canonical current main moved; do not substitute a base")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        lease.mkdir(mode=0o700)  # Atomic one-candidate reservation; never removed on failure.
        record = dict(identity, receipt=str(uuid.uuid4()), binding=binding, preservation=before,
                      candidate=str(candidate), helper_sha256=digest(helper))
        (lease / 'receipt.json').write_bytes(encoded(record) + b'\n')
        git(original, 'clone', '--template=', '--no-hardlinks', '--no-checkout', '--single-branch',
            '--branch', 'main', '--origin', 'upstream', '--', args.upstream, str(candidate))
        require(text_git(candidate, 'rev-parse', 'refs/remotes/upstream/main') == args.base, "base moved during fetch; reservation retained")
        git(candidate, 'checkout', '--track', '-b', args.branch, 'upstream/main')
        (candidate / '.git/kandev-candidate.json').write_bytes(encoded(record) + b'\n')
        (candidate / '.git/kandev-candidate-control.py').write_bytes(helper)
    else:
        require(lease.is_dir() and not lease.is_symlink(), "candidate reservation missing")
        record = json.loads((lease / 'receipt.json').read_text())
        require(args.receipt_sha256 == digest(encoded(record)), "expected Support receipt digest differs")
        require(all(record[k] == v for k, v in identity.items()), "expected candidate identity differs")
        require(record['binding'] == binding, "task binding incarnation changed")
        require(all(before[k] == v for k, v in record['preservation'].items() if k != 'task_state_sha256'),
                "original checkout, refs, writer fences or process incarnation changed since provision")
        require(record['helper_sha256'] == digest(helper), "candidate control helper differs")
        require(args.receipt == record['receipt'], "expected receipt required")
    verify_candidate(candidate, record)
    require(binding == ownership(database, args, original), "binding changed during operation")
    require(before == original_snapshot(database, args, original, binding), "preservation check failed; candidate retained for review")
    print(json.dumps(dict(status='guard_verified', operation=args.operation,
                         receipt_sha256=digest(encoded(record)), **record), sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('provision', 'verify'))
    for name in ('task', 'session', 'workspace', 'repo', 'original', 'original-head', 'base', 'branch', 'slot'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--upstream', default='https://github.com/kdlbs/kandev.git')
    parser.add_argument('--receipt')
    parser.add_argument('--receipt-sha256')
    args = parser.parse_args()
    # The stdin bootstrap supplies its exact source bytes. Verification reads
    # its own task-owned copy; no helper is installed into the running service.
    helper = globals().get('__candidate_source__')
    if helper is None:
        helper = Path(__file__).read_bytes()
    operate(args, helper)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, sqlite3.Error, subprocess.TimeoutExpired) as error:
        print('candidate operation blocked: ' + str(error), file=sys.stderr)
        sys.exit(78)
