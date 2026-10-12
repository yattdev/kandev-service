#!/usr/bin/env python3
"""Reviewed Support preflight for an exact standalone provider retirement.

Default operation is read-only. Explicit --terminate requires a reviewed
snapshot digest and Root authorization, tries the exact instance lifecycle
endpoint, then permits only pidfd-bound SIGTERM recovery after HTTP 401.
It never edits SQL rows, uses credentials, or sends SIGKILL.
"""
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import signal
import time
import urllib.error
import urllib.request
import uuid


ACTIVE = {'starting', 'prepared', 'running', 'ready'}
PROVIDER_ROLES = {'bwrap', 'npm exec @agent', 'sh', 'MainThread', 'codex', 'codex-code-mode'}


def require(condition, message):
    if not condition:
        raise ValueError(message)


def sha(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def process(pid, proc=Path('/proc')):
    path = proc / str(pid)
    raw = (path / 'stat').read_text()
    fields = raw[raw.rfind(')') + 2:].split()
    require(len(fields) > 19, 'process stat is incomplete')
    try:
        environment = (path / 'environ').read_bytes()
    except PermissionError:
        environment = b''  # Unknown identity can never enter the owned tree.
    ids = {k.decode(): v.decode() for item in environment.split(b'\0')
           for k, separator, v in [item.partition(b'=')] if separator and
           k in (b'KANDEV_TASK_ID', b'KANDEV_SESSION_ID', b'KANDEV_INSTANCE_ID')}
    try:
        cwd = os.readlink(path / 'cwd')
    except PermissionError:
        cwd = '<unreadable>'
    return dict(pid=pid, ppid=int(fields[1]), pgid=int(fields[2]), sid=int(fields[3]),
                starttime=fields[19], state='Z' if fields[0] == 'Z' else 'live', cwd=cwd, ids=ids,
                role=raw[raw.find('(') + 1:raw.rfind(')')])


def topology(request, proc=Path('/proc')):
    root = request['original']
    rows = {}
    for path in proc.iterdir():
        if not path.name.isdigit():
            continue
        try:
            row = process(int(path.name), proc)
        except (FileNotFoundError, ProcessLookupError):
            continue
        rows[row['pid']] = row
    selected = rows.get(request['provider_pid'])
    require(selected is not None and selected['state'] != 'Z', 'exact old provider is absent')
    require(selected['starttime'] == request['provider_starttime'], 'provider PID incarnation changed')
    identifiers = dict(KANDEV_TASK_ID=request['task'], KANDEV_SESSION_ID=request['old_session'],
                       KANDEV_INSTANCE_ID=request['old_execution'])
    require(selected['ids'] == identifiers, 'provider launch identity differs')
    selected_group = selected['pgid']
    ancestors = set()
    cursor = selected
    while cursor['ppid'] in rows:
        parent = rows[cursor['ppid']]
        if parent['ids'] != identifiers:
            break
        ancestors.add(parent['pid'])
        cursor = parent
    require(cursor['pid'] == request['launch_pid'] and cursor['starttime'] == request['launch_starttime'],
            'provider guard ancestry changed')
    require(cursor['ppid'] == request['controller_pid'], 'provider controller differs')
    owned = set(ancestors) | {selected['pid'], request['launch_pid']}
    while True:
        descendants = {pid for pid, row in rows.items() if row['ppid'] in owned}
        if descendants <= owned:
            break
        owned |= descendants
    for pid in owned:
        row = rows[pid]
        require(row['ids'] == identifiers, 'unrelated process in provider ancestry/tree')
        require(row['cwd'] == root or row['cwd'].startswith(root + '/'), 'provider process escaped task checkout')
        require(row['role'] in PROVIDER_ROLES, 'unknown provider descendant or unique runtime risk')
    groups = {rows[pid]['pgid'] for pid in owned}
    for pid, row in rows.items():
        if row['pgid'] in groups:
            require(pid in owned, 'provider group contains an unrelated process')
    require(selected_group in groups, 'provider group missing')
    protected = process(request['successor_pid'], proc)
    require(protected['starttime'] == request['successor_starttime'] and protected['state'] != 'Z',
            'protected successor process changed')
    require(protected['ids'] == dict(KANDEV_TASK_ID=request['task'], KANDEV_SESSION_ID=request['successor'],
                                    KANDEV_INSTANCE_ID=request['successor_execution']), 'successor launch identity differs')
    require(protected['pid'] not in owned and protected['pgid'] not in groups, 'protected successor overlaps old provider')
    protected.pop('role')  # Stable reference format used by the transfer verifier.
    return dict(old_tree=[rows[pid] for pid in sorted(owned)], old_groups=sorted(groups), successor=protected)


def snapshot(request, db_path=Path('/data/data/kandev.db'), proc=Path('/proc')):
    db = sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True, timeout=10)
    db.row_factory = sqlite3.Row
    task = db.execute('SELECT * FROM tasks WHERE id=? AND archived_at IS NULL', (request['task'],)).fetchone()
    require(task is not None and task['workspace_id'] == request['workspace'], 'target task/workspace differs')
    coordinator = db.execute('SELECT workspace_id FROM tasks WHERE id=? AND archived_at IS NULL', (request['coordinator'],)).fetchone()
    require(coordinator is not None and coordinator['workspace_id'] == request['workspace'], 'coordinator workspace differs')
    sessions = [dict(r) for r in db.execute('SELECT * FROM task_sessions WHERE task_id=? ORDER BY id', (request['task'],))]
    executions = [dict(r) for r in db.execute('SELECT * FROM executors_running WHERE task_id=? ORDER BY id', (request['task'],))]
    for session_id, execution_id in ((request['old_session'], request['old_execution']),
                                     (request['successor'], request['successor_execution'])):
        session = next((r for r in sessions if r['id'] == session_id), None)
        execution = next((r for r in executions if r['session_id'] == session_id), None)
        require(session is not None and session['state'] == 'WAITING_FOR_INPUT', 'selected provider is not at an idle checkpoint')
        require(session['repository_id'] == request['repo'] and session['workspace_path'] == request['original'], 'session binding differs')
        require(execution is not None and execution['agent_execution_id'] == execution_id
                and execution['runtime'] == 'standalone' and execution['status'] == 'ready', 'exact selected execution differs')
        binding = db.execute('''SELECT er.id, er.worktree_id, r.workspace_id
            FROM task_environment_repos er JOIN repositories r ON r.id=er.repository_id
            WHERE er.task_environment_id=? AND er.repository_id=? AND er.worktree_path=?
              AND er.status='active' AND er.deleted_at IS NULL AND r.deleted_at IS NULL''',
            (session['task_environment_id'], request['repo'], request['original'])).fetchall()
        require(len(binding) == 1 and binding[0]['workspace_id'] == request['workspace'], 'registered worktree binding differs')
    active = [r['session_id'] for r in executions if r['status'] in ACTIVE]
    require(set(active) == {request['old_session'], request['successor']} and len(active) == 2,
            'a conflicting writer is active')
    queue = [dict(r) for r in db.execute('SELECT * FROM queued_messages WHERE task_id=? ORDER BY session_id,position,id', (request['task'],))]
    require(not queue, 'new pending input: abort retirement and preserve FIFO')
    protected_sessions = [r for r in sessions if r['id'] != request['old_session']]
    protected_executions = [r for r in executions if r['session_id'] != request['old_session']]
    return dict(task_sha256=sha(dict(task)), protected_sessions_sha256=sha(protected_sessions),
                protected_executions_sha256=sha(protected_executions), fifo_count=0,
                fifo_sha256=hashlib.sha256(b'').hexdigest(), topology=topology(request, proc))


def checkpoint(request):
    """Only read Git; preserve the authorized candidate and immutable lineage."""
    original = Path(request['original'])
    candidate = original / '.kandev/hqa/admission-current-main'
    require(original.resolve() == original and candidate.resolve() == candidate, 'checkpoint path contains a symlink')
    environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    environment['GIT_OPTIONAL_LOCKS'] = '0'

    def git(path, *arguments):
        return subprocess.check_output(['/usr/bin/git', '--no-optional-locks', '-c', 'core.hooksPath=/dev/null',
                                        '-c', 'core.fsmonitor=false', '-C', str(path), *arguments], env=environment).decode().strip()

    lease_path = original / '.kandev/hqa/.candidate-lease/receipt.json'
    lease = json.loads(lease_path.read_text())
    require(sha(lease) == request['reservation_sha256'] and lease['receipt'] == request['reservation'], 'reservation lineage differs')
    for field, expected in [('task', request['task']), ('repo', request['repo']), ('workspace', request['workspace']),
                            ('session', request['old_session']), ('original', request['original']),
                            ('original_head', request['original_head']), ('base', request['base']), ('branch', request['branch'])]:
        require(lease[field] == expected, 'reservation identity differs')
    require(json.loads((candidate / '.git/kandev-candidate.json').read_text()) == lease, 'candidate marker differs')
    require(hashlib.sha256((candidate / '.git/kandev-candidate-control.py').read_bytes()).hexdigest() == lease['helper_sha256'], 'original helper differs')
    require(git(original, 'rev-parse', 'HEAD') == request['original_head'], 'original HEAD differs')
    require(git(original, 'symbolic-ref', '--short', 'HEAD') == lease['binding']['worktree_branch'], 'original branch differs')
    require(git(original, 'rev-parse', 'refs/heads/' + request['branch']) == request['base'], 'failed-attempt branch differs')
    require(git(candidate, 'rev-parse', 'HEAD') == request['head'] and not git(candidate, 'status', '--porcelain'), 'candidate checkpoint differs or is dirty')
    require(git(candidate, 'symbolic-ref', '--short', 'HEAD') == request['branch'], 'candidate branch differs')
    require(git(candidate, 'rev-parse', '--path-format=absolute', '--git-common-dir') == str(candidate / '.git'), 'candidate administration escapes')
    require(not (candidate / '.git/objects/info/alternates').exists(), 'candidate Git objects are shared')
    git(candidate, 'merge-base', '--is-ancestor', request['base'], request['head'])
    prompt_hash = hashlib.sha256((original / 'PROMPT.md').read_bytes()).hexdigest()
    require(prompt_hash == request['prompt_sha256'], 'operator PROMPT changed')
    return dict(reservation_sha256=sha(lease), head=request['head'], original_head=request['original_head'],
                prompt_sha256=prompt_hash, marker_sha256=hashlib.sha256((original / '.git').read_bytes()).hexdigest())


def terminate(request, expected):
    """Try the scoped lifecycle endpoint first; use reviewed TERM-only recovery.

    This does not mint/reuse credentials, edit lifecycle rows, kill a shared
    controller, or send SIGKILL. Lifecycle bookkeeping remains backend-owned.
    A pidfd for each positively bound target prevents PID-only signal selection.
    """
    require(os.environ.get('KANDEV_AGENT_GUARD_ACTIVE') != '1', 'host Support namespace required')
    require(hasattr(os, 'pidfd_open') and hasattr(signal, 'pidfd_send_signal'), 'pidfd signal support unavailable')
    before = snapshot(request)
    before['checkpoint'] = checkpoint(request)
    require(sha(before) == expected, 'reviewed preflight snapshot changed')
    database = sqlite3.connect('file:/data/data/kandev.db?mode=ro', uri=True)
    endpoint = database.execute('SELECT agentctl_url FROM executors_running WHERE session_id=? AND agent_execution_id=?',
                                (request['old_session'], request['old_execution'])).fetchone()[0]
    require(endpoint == request['endpoint'] and endpoint.startswith('http://127.0.0.1:'), 'exact lifecycle endpoint differs')
    # There is intentionally no credential or auth-row fallback. A successful
    # supported stop is followed by the same physical revocation checks.
    api_status = None
    try:
        call = urllib.request.Request(endpoint + '/api/v1/stop', data=b'{"force":false}', method='POST',
                                      headers={'Content-Type': 'application/json'})
        with urllib.request.urlopen(call, timeout=30) as response:
            api_status = response.status
    except urllib.error.HTTPError as error:
        api_status = error.code
        require(api_status == 401, 'supported lifecycle rejected for a reason other than missing authentication')
    # An authenticated API would use its normal graceful teardown. With no
    # credential transport, Root-authorized TERM is bounded to the pinned tree.
    handles = {}
    signaled = []
    try:
        if api_status == 401:
            current = snapshot(request)
            current['checkpoint'] = checkpoint(request)
            require(current == before, 'identity, checkpoint or FIFO changed after lifecycle attempt')
            for row in before['topology']['old_tree']:
                handles[row['pid']] = os.pidfd_open(row['pid'])
                require(process(row['pid']) == row, 'target incarnation changed while pinning pidfd')
            current = snapshot(request)
            current['checkpoint'] = checkpoint(request)
            require(current == before, 'retirement predicates changed before first signal')
            provider = request['provider_pid']
            signal.pidfd_send_signal(handles[provider], signal.SIGTERM)
            signaled.append(provider)
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            alive = []
            for row in before['topology']['old_tree']:
                try:
                    actual = process(row['pid'])
                except (FileNotFoundError, ProcessLookupError):
                    continue
                if actual['starttime'] == row['starttime'] and actual['state'] != 'Z':
                    alive.append(row)
            if not alive:
                break
            time.sleep(0.2)
        else:
            require(api_status == 401, 'normal lifecycle did not revoke all old authority; no raw fallback permitted')
            # Validate every remaining positively bound process and the protected
            # successor before TERM. Never signal a new process or a whole group.
            protected = process(request['successor_pid'])
            protected.pop('role')
            require(protected == before['topology']['successor'], 'protected successor changed')
            require(checkpoint(request) == before['checkpoint'], 'checkpoint changed during graceful retirement')
            require(database.execute('SELECT COUNT(*) FROM queued_messages WHERE task_id=?', (request['task'],)).fetchone()[0] == 0,
                    'new pending input: stop recovery and preserve it')
            for row in reversed(alive):
                actual = process(row['pid'])
                require(actual == row, 'remaining target changed')
                try:
                    signal.pidfd_send_signal(handles[row['pid']], signal.SIGTERM)
                    signaled.append(row['pid'])
                except ProcessLookupError:
                    pass
            deadline = time.monotonic() + 8
            while time.monotonic() < deadline:
                remaining = []
                for row in before['topology']['old_tree']:
                    try:
                        actual = process(row['pid'])
                    except (FileNotFoundError, ProcessLookupError):
                        continue
                    if actual['starttime'] == row['starttime'] and actual['state'] != 'Z':
                        remaining.append(actual['pid'])
                if not remaining:
                    break
                time.sleep(0.2)
            require(not remaining, 'old processes remain after bounded TERM; SIGKILL is prohibited')
    finally:
        for handle in handles.values():
            os.close(handle)
    protected = process(request['successor_pid'])
    protected.pop('role')
    require(protected == before['topology']['successor'], 'successor incarnation changed')
    require(checkpoint(request) == before['checkpoint'], 'checkpoint changed during retirement')
    receipt = dict(receipt=str(uuid.uuid4()), task=request['task'], workspace=request['workspace'],
                   old_session=request['old_session'], old_execution=request['old_execution'],
                   successor=request['successor'], successor_execution=request['successor_execution'],
                   authority_revoked=True, lifecycle_http_status=api_status, signal='SIGTERM' if signaled else None,
                   signaled_pids=signaled, prior_snapshot_sha256=sha(before), checkpoint=before['checkpoint'])
    return dict(receipt, receipt_sha256=sha(receipt))


if __name__ == '__main__':
    try:
        request = json.load(sys.stdin)
        if len(sys.argv) == 3 and sys.argv[1] == '--terminate':
            result = terminate(request, sys.argv[2])
        else:
            result = snapshot(request)
            if 'reservation' in request:
                result['checkpoint'] = checkpoint(request)
        print(json.dumps(result, sort_keys=True))
    except (ValueError, OSError, sqlite3.Error) as error:
        print(json.dumps(dict(status='blocked', error=str(error))), file=sys.stderr)
        sys.exit(78)
