#!/usr/bin/env python3
"""Append a reviewed transfer receipt; inspect or verify its exact successor.

Prepare is a reviewed Support operation on stdin through the existing guard.
Verify is read-only and requires the successor's own exported launch identity.
The original provision receipt, marker and helper are never overwritten.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sqlite3
import sys
import uuid


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(value).hexdigest()


def process_identity(pid):
    path = Path('/proc') / str(pid)
    raw = (path / 'stat').read_text()
    fields = raw[raw.rfind(')') + 2:].split()
    ids = {k.decode(): v.decode() for item in (path / 'environ').read_bytes().split(b'\0')
           for k, separator, v in [item.partition(b'=')] if separator and
           k in (b'KANDEV_TASK_ID', b'KANDEV_SESSION_ID', b'KANDEV_INSTANCE_ID')}
    return dict(pid=pid, ppid=int(fields[1]), pgid=int(fields[2]), sid=int(fields[3]), starttime=fields[19],
                state='Z' if fields[0] == 'Z' else 'live', cwd=os.readlink(path / 'cwd'), ids=ids)


def process_reference_current(reference):
    # Cross-guard environ/cwd reads are intentionally restricted. The reviewed
    # outer preflight attests those; non-sensitive kernel stat fields pin the
    # same physical process here without widening that restriction.
    raw = (Path('/proc') / str(reference['pid']) / 'stat').read_text()
    fields = raw[raw.rfind(')') + 2:].split()
    require(fields[0] != 'Z' and fields[19] == reference['starttime']
            and int(fields[1]) == reference['ppid'] and int(fields[2]) == reference['pgid']
            and int(fields[3]) == reference['sid'], 'physical successor incarnation changed')


def caller_anchor(reference):
    """Require ancestry through the exact provider captured by trusted Support.

    Match kernel start time and launch IDs as well as PID where visible. This
    rejects session IDs substituted only in the calling shell environment.
    Missing private-proc visibility fails closed; it never widens that boundary.
    """
    pid = os.getpid()
    seen = set()
    while pid > 1 and pid not in seen:
        seen.add(pid)
        identity = process_identity(pid)
        if identity == reference:
            return
        pid = identity['ppid']
    raise ValueError('caller is not a descendant of the pinned successor provider')


def load_original(original, expected):
    lease = original / '.kandev/hqa/.candidate-lease'
    require(lease.resolve() == lease and lease.is_dir(), 'reservation path changed')
    record = json.loads((lease / 'receipt.json').read_text())
    require(digest(encoded(record)) == expected, 'pinned original reservation digest differs')
    candidate = Path(record['candidate'])
    require(candidate == original / '.kandev/hqa' / record['slot'] and candidate.resolve() == candidate,
            'candidate path differs or traverses a symlink')
    require(json.loads((candidate / '.git/kandev-candidate.json').read_text()) == record, 'original candidate marker differs')
    helper = candidate / '.git/kandev-candidate-control.py'
    require(helper.is_file() and not helper.is_symlink(), 'original helper path changed')
    source = helper.read_bytes()
    require(digest(source) == record['helper_sha256'], 'original helper differs')
    module = {'__name__': 'original_candidate', '__file__': str(helper)}
    exec(compile(source, str(helper), 'exec'), module)
    return lease, candidate, record, module


def retired(database, authorization):
    row = database.execute('SELECT * FROM executors_running WHERE task_id=? AND session_id=?',
                           (authorization['task'], authorization['old_session'])).fetchone()
    require(row is not None and row['agent_execution_id'] == authorization['old_execution'], 'retired execution incarnation differs')
    require(row['status'] in ('failed', 'stopped', 'completed') and row['local_pid'] == 0 and row['pid'] == 0,
            'old execution retains eligibility or a process handle')
    return dict(session=authorization['old_session'], execution=authorization['old_execution'], status=row['status'],
                updated_at=row['updated_at'])


def candidate_check(candidate, original_record, head, module):
    git = module['text_git']
    admin = candidate / '.git'
    require(admin.is_dir() and not admin.is_symlink(), 'candidate is not independent')
    require(git(candidate, 'rev-parse', '--absolute-git-dir') == str(admin)
            and git(candidate, 'rev-parse', '--path-format=absolute', '--git-common-dir') == str(admin), 'candidate Git administration escapes')
    require(not (admin / 'commondir').exists() and not (admin / 'objects/info/alternates').exists(), 'candidate shares Git storage')
    require(git(candidate, 'rev-parse', 'HEAD') == head, 'authorized candidate HEAD differs')
    require(git(candidate, 'symbolic-ref', '--short', 'HEAD') == original_record['branch'], 'candidate branch differs')
    require(git(candidate, 'rev-parse', 'refs/remotes/upstream/main') == original_record['base'], 'candidate base differs')
    require(git(candidate, 'config', '--get', 'remote.upstream.url') == original_record['upstream'], 'candidate canonical source differs')
    git(candidate, 'merge-base', '--is-ancestor', original_record['base'], head)
    require(not module['git'](candidate, 'status', '--porcelain'), 'candidate is dirty')
    require(os.access(admin, os.W_OK) and os.access(candidate, os.W_OK), 'candidate is not writable within this guard')


def checked(database, args, authorization, original, candidate, original_record, module):
    require(authorization['task'] == original_record['task'] and authorization['workspace'] == original_record['workspace'],
            'transfer task/workspace differs')
    require(authorization['old_session'] == original_record['session'], 'transfer predecessor differs')
    require(authorization['successor'] == args.session and authorization['successor'] != authorization['old_session'], 'successor identity differs')
    require(authorization['authority_revoked'] is True, 'physical revocation receipt required')
    require(args.task == original_record['task'] and args.workspace == original_record['workspace']
            and args.repo == original_record['repo'] and args.original_head == original_record['original_head']
            and args.base == original_record['base'] and args.branch == original_record['branch']
            and args.slot == original_record['slot'], 'expected candidate identity differs')
    retirement_body = {k: v for k, v in authorization.items() if k != 'receipt_sha256'}
    require(authorization['receipt_sha256'] == digest(encoded(retirement_body)), 'retirement receipt digest differs')
    require(authorization['checkpoint']['head'] == args.head
            and authorization['checkpoint']['original_head'] == args.original_head
            and authorization['checkpoint']['reservation_sha256'] == args.reservation_sha256, 'retirement checkpoint differs')
    old = retired(database, authorization)
    binding = module['ownership'](database, args, original)
    prior_binding = {k: v for k, v in original_record['binding'].items() if k != 'binding_updated_at'}
    current_binding = {k: v for k, v in binding.items() if k != 'binding_updated_at'}
    require(prior_binding == current_binding, 'worktree binding incarnation differs')
    execution = database.execute('SELECT * FROM executors_running WHERE task_id=? AND session_id=?', (args.task, args.session)).fetchone()
    require(execution['agent_execution_id'] == authorization['successor_execution'], 'successor execution incarnation differs')
    candidate_check(candidate, original_record, args.head, module)
    snapshot = module['original_snapshot'](database, args, original, binding)
    for field in ('files_sha256', 'marker_sha256'):
        require(snapshot[field] == original_record['preservation'][field], 'original checkout preservation differs')
    return dict(binding=binding, retired=old, successor_execution=execution['agent_execution_id'], preservation=snapshot)


def operate(args, source):
    require(os.environ.get('KANDEV_AGENT_GUARD_ACTIVE') == '1'
            and os.environ.get('KANDEV_AGENT_GUARD_SCOPE') == 'project', 'existing task guard required')
    original = Path(args.original)
    require(original.resolve() == original and Path.cwd() == original, 'invoke from exact original checkout')
    lease, candidate, original_record, module = load_original(original, args.reservation_sha256)
    database = sqlite3.connect('file:/data/data/kandev.db?mode=ro', uri=True, timeout=10)
    database.row_factory = sqlite3.Row
    if args.operation == 'prepare':
        authorization = globals().get('__retirement_receipt__')
        require(isinstance(authorization, dict), 'reviewed Support retirement receipt required')
        require(args.retirement_sha256 == authorization['receipt_sha256'], 'pinned retirement receipt differs')
        successor_process = globals().get('__successor_process__')
        preflight = globals().get('__retirement_preflight__')
        require(isinstance(preflight, dict) and digest(encoded(preflight)) == authorization['prior_snapshot_sha256'],
                'reviewed outer retirement preflight digest differs')
        require(isinstance(successor_process, dict) and preflight['topology']['successor'] == successor_process,
                'pinned physical successor reference differs')
        process_reference_current(successor_process)
        require(successor_process['ids'] == dict(KANDEV_TASK_ID=args.task, KANDEV_SESSION_ID=args.session,
                                                KANDEV_INSTANCE_ID=authorization['successor_execution']), 'physical successor launch differs')
        before = checked(database, args, authorization, original, candidate, original_record, module)
        transfer_root = lease / 'transfers'
        require(not transfer_root.exists(), 'existing transfer lineage requires reconciliation; do not repeat')
        transfer_root.mkdir(mode=0o700)  # Atomic first-transfer reservation; failures remain reviewable.
        receipt = dict(receipt=str(uuid.uuid4()), operation='transfer', task=args.task, workspace=args.workspace,
                       repo=args.repo, original=args.original, original_head=args.original_head, head=args.head,
                       base=args.base, branch=args.branch, slot=args.slot, successor=args.session,
                       original_receipt=original_record['receipt'], original_receipt_sha256=args.reservation_sha256,
                       retirement=authorization, successor_process=successor_process, helper_sha256=digest(source), **before)
        body = encoded(receipt) + b'\n'
        (transfer_root / (receipt['receipt'] + '.json')).write_bytes(body)
        (candidate / '.git' / ('kandev-transfer-' + receipt['receipt'] + '.json')).write_bytes(body)
        (candidate / '.git/kandev-candidate-transfer.py').write_bytes(source)
        require(before == checked(database, args, authorization, original, candidate, original_record, module),
                'preservation or ownership changed during prepare; receipt retained for reconciliation')
    else:
        require(args.receipt is not None, 'expected transfer receipt required')
        require(str(uuid.UUID(args.receipt)) == args.receipt, 'canonical transfer receipt UUID required')
        transfer_directory = lease / 'transfers'
        require(transfer_directory.resolve() == transfer_directory and transfer_directory.is_dir(), 'transfer directory changed')
        receipt = json.loads((lease / 'transfers' / (args.receipt + '.json')).read_text())
        require(digest(encoded(receipt)) == args.receipt_sha256, 'pinned transfer digest differs')
        require(receipt['receipt'] == args.receipt and receipt['original_receipt_sha256'] == args.reservation_sha256,
                'transfer lineage differs')
        for field in ('task', 'workspace', 'repo', 'original', 'original_head', 'head', 'base', 'branch', 'slot'):
            require(receipt[field] == getattr(args, field), 'expected transfer identity differs')
        require(receipt['successor'] == args.session and receipt['helper_sha256'] == digest(source), 'transfer caller/helper differs')
        require(json.loads((candidate / '.git' / ('kandev-transfer-' + args.receipt + '.json')).read_text()) == receipt,
                'candidate transfer marker differs')
        if args.operation == 'verify':
            for name, expected in [('KANDEV_TASK_ID', args.task), ('KANDEV_SESSION_ID', args.session),
                                   ('KANDEV_INSTANCE_ID', receipt['successor_execution'])]:
                require(os.environ.get(name) == expected, 'authenticated successor launch identity required')
            caller_anchor(receipt['successor_process'])
        process_reference_current(receipt['successor_process'])
        before = checked(database, args, receipt['retirement'], original, candidate, original_record, module)
        require(before['binding'] == receipt['binding'] and before['retired'] == receipt['retired'], 'transfer binding or retired incarnation changed')
        for field, value in receipt['preservation'].items():
            if field not in ('task_state_sha256',):
                require(before['preservation'][field] == value, 'transfer preservation or writer fence differs')
        require(before == checked(database, args, receipt['retirement'], original, candidate, original_record, module), 'state changed during verification')
    print(json.dumps(dict(status='successor_guard_verified' if args.operation == 'verify' else 'support_guard_checked',
                          receipt_sha256=digest(encoded(receipt)), **receipt), sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('prepare', 'inspect', 'verify'))
    for name in ('task', 'session', 'workspace', 'repo', 'original', 'original-head', 'head', 'base', 'branch', 'slot', 'reservation-sha256'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--retirement-sha256')
    parser.add_argument('--receipt')
    parser.add_argument('--receipt-sha256')
    args = parser.parse_args()
    source = globals().get('__candidate_source__')
    if source is None:
        source = Path(__file__).read_bytes()
    # Interface expected by the unchanged original guard helper.
    args.upstream = 'https://github.com/kdlbs/kandev.git'
    operate(args, source)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, sqlite3.Error) as error:
        print('candidate transfer blocked: ' + str(error), file=sys.stderr)
        sys.exit(78)
