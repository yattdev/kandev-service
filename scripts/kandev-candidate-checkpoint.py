#!/usr/bin/env python3
"""Prepare an inert prospective checkpoint proposal; never install or adopt it."""
import argparse
import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import sqlite3
import subprocess
import sys
from datetime import datetime, timezone
from urllib.parse import urlsplit


VERSION = 'candidate-prospective-checkpoint/1'
CONTRACT = '''Candidate prospective checkpoint contract, version 1 (proposal only)
1. This creates a prospective preservation boundary, not historical correction.
   The interval from transfer preparation until approved adoption is unproven
   for shared config and inventory. Old aggregate failures remain recorded.
2. Reservation, retirement, transfer, historical report and setup-audit UUIDs
   and digests remain immutable parents. No receipt, helper, marker or history
   is replaced, deleted, restored or silently re-pinned.
3. Root must approve this exact proposal and contract digest, task/workspace/
   repo, original and candidate heads/base/branch, successor session/execution,
   binding and physical process incarnation. Repository-owner review must approve
   the exact shared-config byte digest and sanitized assessment. Unreviewable
   authority-bearing values, unresolved includes or executable code block adoption.
4. Required approval fields: proposal_sha256, contract_sha256, shared_config_sha256,
   identity, lineage, preflight_sha256, approve_new_boundary=true,
   acknowledge_unproven_interval=true, approve_config_assessment=true,
   mutable_ref_policy, reviewer_id, review_receipt, repository_review_receipt,
   preservation_decision_receipt, expires_at and single_use_nonce. Approval must
   arrive through authenticated reviewed controls; JSON alone is not authority.
5. Before adoption, a separate reviewed operation revalidates the exact original
   tracked/untracked files including PROMPT, linked Git marker/admin/backlink,
   original branch/head, failed-attempt branch, clean independent candidate at
   its exact authorized head/base/branch, all old helper/receipt hashes, exact
   live binding and retired predecessor. No provider action or shared Git write.
6. It also requires the same sole eligible successor and pinned physical provider
   ancestry/incarnation, old authority still revoked, no foreign active executor,
   unchanged protected sessions/executions and limits, and an empty FIFO. New
   input is preserved and invalidates adoption; no replay, disposal or counter reset.
7. Adoption retains complete per-entry content/presence and inventory-stat maps
   collected and hashed from the same stable snapshot; manifest and scope digests
   enter a new append-only receipt. Baseline starts at adoption, never retroactively.
   Failed preparation/adoption artifacts remain for reconciliation, not cleanup.
8. Protected entries include original admin/files/marker, selected original and
   failed-attempt refs, pinned canonical base, shared config/HEAD/packed-refs and
   all non-authorized refs. Any change denies subsequent verification. Missing,
   added, symlinked, renamed or unreadable protected entries deny verification.
9. Only refs/heads/feature/allow-coordinator-re-wxo may advance prospectively.
   Each advance needs exact old/new OIDs, verified ancestry (no deletion/rewrite),
   same-workspace owner and Root operation receipt. No other ref permission.
   Associated ref/reflog replacements and newly appended reachable Git objects
   need a complete per-entry delta bound to that operation. Unrelated changes,
   pre-existing object mutation/removal or pack rewriting remain blocking.
   The original full inventory remains evidence; it is not simply ignored.
10. Successor RUNNING/idle transitions and monotonically increasing own usage
    are permitted; ownership, execution/process incarnation and budget/limit
    fields remain pinned. Other writer fences and accounting remain unchanged.
11. After approved adoption, only the authenticated successor's own guard can
    verify its launch IDs and ancestry against the append-only receipt. Root or
    Support cannot substitute the caller. Changed binding/provider, old revival,
    foreign writer, stale/expired/reused approval or any unclassified drift denies.
12. Preparation issues no accepted caller command, Source admission, lane/model/
    primary/grant change or runtime authority. Adoption requires separately
    reviewed implementation and tests. Root retains separate Source admission.
'''


def require(condition, message):
    if not condition:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def digest(value):
    return sha(encoded(value))


def approval_shape(packet, approval, authenticated_review=False, now=None):
    """Offline validation only; the trusted broker must authenticate reviewers.

    There is no adoption operation. Even a valid approval cannot install this
    proposal or stand in for the successor's own guarded acceptance.
    """
    require(authenticated_review, 'authenticated reviewed authority required; JSON is not authority')
    require(packet['mode'] == 'proposal_only' and not packet['adoption_authorized']
            and not packet['installed'] and not packet['source_admitted'], 'proposal mode differs')
    require(not packet['adoption_blockers'] and packet['config_assessment']['adoption_eligible'],
            'hidden or unreviewable authority precludes adoption')
    body = {k: v for k, v in packet.items() if k != 'proposal_sha256'}
    require(packet['proposal_sha256'] == digest(body), 'proposal digest differs')
    for field in ('proposal_sha256', 'contract_sha256', 'identity', 'lineage', 'preflight_sha256', 'mutable_ref_policy'):
        require(approval.get(field) == packet[field], 'approval must pin exact ' + field)
    require(approval.get('shared_config_sha256') == packet['config_assessment']['shared_config_sha256'],
            'approval must pin exact shared config')
    for field in ('approve_new_boundary', 'acknowledge_unproven_interval', 'approve_config_assessment'):
        require(approval.get(field) is True, 'explicit preservation/config decision required')
    for field in ('reviewer_id', 'review_receipt', 'repository_review_receipt', 'preservation_decision_receipt', 'single_use_nonce'):
        require(isinstance(approval.get(field), str) and bool(approval[field]), 'named review and single-use binding required')
    expiry = datetime.fromisoformat(approval['expires_at'].replace('Z', '+00:00'))
    require(expiry.tzinfo is not None and expiry > (now or datetime.now(timezone.utc)), 'approval expired or timezone missing')
    return dict(status='approval_shape_valid_only', adoption_performed=False, caller_acceptance='not_run')


def private_commitment(key, value):
    return hmac.new(key, value.encode(), hashlib.sha256).hexdigest()


def remote_identity(value):
    # Git's fixed SSH service username is public routing metadata, not a token.
    if re.fullmatch(r'git@[A-Za-z0-9.-]+:[A-Za-z0-9_./-]+', value):
        host, path = value[4:].split(':', 1)
        return dict(transport='ssh', host=host, repository=path, service_user='git')
    parsed = urlsplit(value)
    require(parsed.scheme in ('https', 'ssh') and parsed.hostname is not None,
            'unreviewable remote transport')
    require(parsed.password is None and parsed.username in (None, 'git')
            and not parsed.query and not parsed.fragment and '%' not in value,
            'credential-bearing or encoded remote identity')
    require(re.fullmatch(r'/[A-Za-z0-9_./-]+', parsed.path) is not None,
            'unreviewable remote path')
    return dict(transport=parsed.scheme, host=parsed.hostname, port=parsed.port,
                repository=parsed.path.lstrip('/'), service_user=parsed.username)


def classify(name, value, key):
    """Closed allowlist: unknown values never become reviewable authority."""
    lower = name.lower()
    row = dict(key=name, classification='redacted', value='<withheld>',
               private_commitment=private_commitment(key, name + '\0' + value), adoption_blocker=True)
    # Subsection names can themselves contain credential-bearing URLs/paths.
    if re.search(r'://|@|password|token|secret|extraheader', lower):
        row['key'] = lower.split('.', 1)[0] + '.<redacted-key>'
        row['reason'] = 'credential-bearing key/value or authority cannot be publicly reviewed'
        return row
    safe_scalars = {'core.repositoryformatversion', 'core.filemode', 'core.bare', 'core.logallrefupdates',
                    'core.ignorecase', 'core.precomposeunicode', 'core.autocrlf', 'core.safecrlf',
                    'core.eol', 'core.symlinks', 'core.quotepath', 'extensions.worktreeconfig',
                    'pull.rebase', 'fetch.prune', 'init.defaultbranch', 'push.default'}
    if lower in safe_scalars and re.fullmatch(r'[A-Za-z0-9_-]{0,64}', value):
        row.update(classification='reviewable_scalar', value=value, adoption_blocker=False)
    elif re.fullmatch(r'remote\.[A-Za-z0-9_-]+\.(url|pushurl)', lower):
        try:
            row.update(classification='credential_free_remote', value=remote_identity(value), adoption_blocker=False)
        except ValueError:
            row['reason'] = 'remote identity or credentials unreviewable'
    elif re.fullmatch(r'remote\.[A-Za-z0-9_-]+\.fetch', lower) and re.fullmatch(r'\+?refs/[A-Za-z0-9_./*-]+:refs/[A-Za-z0-9_./*-]+', value):
        row.update(classification='reviewable_refspec', value=value, adoption_blocker=False)
    elif re.fullmatch(r'branch\.[A-Za-z0-9_/-]+\.(remote|pushremote|merge)', lower) and re.fullmatch(r'[A-Za-z0-9_./-]+', value):
        row.update(classification='reviewable_branch_routing', value=value, adoption_blocker=False)
    elif lower in ('user.name', 'user.email'):
        row.update(classification='identity_withheld', adoption_blocker=False,
                   reason='non-authority personal identity withheld')
    elif lower == 'core.hookspath' and value == '/dev/null':
        row.update(classification='hooks_disabled', value='/dev/null', adoption_blocker=False)
    elif lower == 'core.fsmonitor' and value.lower() == 'false':
        row.update(classification='fsmonitor_disabled', value=False, adoption_blocker=False)
    elif lower == 'credential.helper' and value == '':
        row.update(classification='credential_helper_disabled', value='', adoption_blocker=False)
    elif lower.startswith(('include.', 'includeif.')):
        row.update(classification='unresolved_include', reason='include not followed; hidden authority precludes adoption')
    elif lower.startswith(('alias.', 'filter.', 'credential.', 'diff.')) or lower in (
            'core.hookspath', 'core.fsmonitor', 'core.sshcommand', 'core.gitproxy', 'gpg.program', 'user.signingkey'):
        row.update(classification='unreviewed_executable_or_authority', reason='requires reviewable executable/authority semantics')
    else:
        row['reason'] = 'outside closed safe-semantic allowlist'
    return row


def config_source(path, origin, key):
    require(not path.is_symlink(), 'config source type/symlink unreviewable')
    if not path.exists():
        return dict(origin=origin, presence='absent', entries=[])
    require(path.is_file() and not path.is_symlink(), 'config source type/symlink unreviewable')
    require(path.stat().st_size <= 256 * 1024, 'config source exceeds bound')
    before = path.read_bytes()
    environment = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['/usr/bin/git', 'config', '--no-includes', '--null', '--list', '--file', str(path)],
                            env=environment, capture_output=True, timeout=15)
    require(result.returncode == 0 and len(result.stdout) <= 1024 * 1024, 'config parsing failed; values withheld')
    entries = []
    for item in result.stdout.decode().split('\0'):
        if not item:
            continue
        name, separator, value = item.partition('\n')
        entries.append(classify(name, value if separator else 'true', key))
    require(before == path.read_bytes(), 'config changed during bounded review')
    return dict(origin=origin, presence='present', bytes_sha256=sha(before), entries=entries,
                includes_followed=False, parser='git config --no-includes; no helper/hook/filter execution')


def hooks_review(directory, key):
    require(not directory.is_symlink(), 'hooks directory changed or symlinked')
    if not directory.exists():
        return dict(origin='shared.default_hooks', presence='absent', entries=[])
    require(directory.is_dir() and not directory.is_symlink(), 'hooks directory changed or symlinked')
    rows = []
    for path in sorted(directory.iterdir()):
        if path.name.endswith('.sample'):
            continue
        require(len(rows) < 64, 'hook inventory exceeds bound')
        if path.is_symlink() or not path.is_file() or path.stat().st_size > 256 * 1024:
            rows.append(dict(name='<unreviewable-entry>', adoption_blocker=True))
            continue
        before = path.stat()
        raw = path.read_bytes()
        require(before == path.stat(), 'hook changed during bounded review')
        executable = bool(before.st_mode & 0o111)
        name = path.name if re.fullmatch(r'[a-z-]+', path.name) else '<redacted-name>'
        rows.append(dict(name=name, bytes_sha256=sha(raw), executable=executable,
                         semantics='<code not exposed or executed>', adoption_blocker=executable,
                         private_name_commitment=private_commitment(key, path.name)))
    return dict(origin='shared.default_hooks', presence='present', entries=rows)


def config_review(common, admin, candidate):
    key = os.urandom(32)  # No secret value or HMAC key is persisted or delivered.
    sources = [(Path('/etc/gitconfig'), 'system'), (Path('/data/home/.config/git/config'), 'user.xdg'),
               (Path('/data/home/.gitconfig'), 'user'), (common / 'config', 'shared'),
               (admin / 'config.worktree', 'original.worktree'), (candidate / '.git/config', 'candidate')]
    rows = [config_source(path, label, key) for path, label in sources]
    shared = next(r for r in rows if r['origin'] == 'shared')
    require(shared['presence'] == 'present', 'shared config missing')
    hooks = hooks_review(common / 'hooks', key)
    blockers = [dict(origin=r['origin'], key=e['key'], classification=e['classification'])
                for r in rows for e in r['entries'] if e['adoption_blocker']]
    blockers.extend(dict(origin=hooks['origin'], hook=e['name'], classification='unreviewed_hook_code')
                    for e in hooks['entries'] if e['adoption_blocker'])
    return dict(shared_config_sha256=shared['bytes_sha256'], sources=rows, hooks=hooks,
                adoption_eligible=not blockers, blockers=blockers,
                private_commitments='HMAC-SHA256; per-review undisclosed ephemeral key; no credential values retained',
                config_environment='GIT_* removed; system/user/local examined separately; includes never followed',
                capability_git_overrides=dict(system_and_user_config='disabled', credential_helper='disabled',
                                              hooks_path='/dev/null', fsmonitor=False),
                limitations=['ambient GIT_* overrides and executable code are not adopted by this proposal',
                             'no historical config attribution or inventory reconstructed',
                             'Source commands are not admitted by capability Git overrides',
                             'configured custom hook locations are withheld/unresolved; never traversed'],
                conclusions=['read-only parser executed no hook/helper/filter and followed no include',
                             'authority blockers must be resolved through reviewable semantics before adoption'
                             if blockers else 'listed config semantics are reviewable; explicit repository/Root approval still required'])


def review(args, source):
    require(os.environ.get('KANDEV_AGENT_GUARD_ACTIVE') == '1'
            and os.environ.get('KANDEV_AGENT_GUARD_SCOPE') == 'project', 'existing project guard required')
    original = Path(args.original)
    require(Path.cwd() == original and original.resolve() == original, 'exact original guard root required')
    lease = original / '.kandev/hqa/.candidate-lease'
    transfer = json.loads((lease / 'transfers' / (args.transfer + '.json')).read_text())
    require(digest(transfer) == args.transfer_sha256, 'pinned transfer differs')
    candidate = original / '.kandev/hqa' / transfer['slot']
    require(candidate.resolve() == candidate, 'candidate path differs')
    installed = candidate / '.git/kandev-candidate-transfer.py'
    require(installed.is_file() and not installed.is_symlink(), 'old transfer helper path differs')
    require(sha(installed.read_bytes()) == transfer['helper_sha256'], 'old transfer helper differs')
    module = {'__name__': 'retained_transfer', '__file__': str(installed)}
    exec(compile(installed.read_bytes(), str(installed), 'exec'), module)
    _, clone, reservation, git_module = module['load_original'](original, args.reservation_sha256)
    require(json.loads((candidate / '.git' / ('kandev-transfer-' + args.transfer + '.json')).read_text()) == transfer,
            'old transfer marker differs')
    require(clone == candidate and reservation['receipt'] == args.reservation, 'reservation candidate differs')
    for field in ('task', 'workspace', 'repo', 'original_head', 'head', 'base', 'branch'):
        require(getattr(args, field) == transfer[field], 'proposal checkpoint identity differs')
    require(args.session == transfer['successor'] and args.reservation_sha256 == transfer['original_receipt_sha256'],
            'proposal successor/lineage differs')
    database = sqlite3.connect('file:/data/data/kandev.db?mode=ro', uri=True, timeout=10)
    database.row_factory = sqlite3.Row
    database.execute('BEGIN')
    args.upstream = reservation['upstream']
    binding = git_module['ownership'](database, args, original)
    require(binding == transfer['binding'], 'binding changed since transfer')
    require(module['retired'](database, transfer['retirement']) == transfer['retired'], 'retired incarnation changed')
    module['process_reference_current'](transfer['successor_process'])
    owner = dict(database.execute('SELECT * FROM task_sessions WHERE id=? AND task_id=?', (args.session, args.task)).fetchone())
    require(owner['state'] == 'WAITING_FOR_INPUT', 'successor must remain paused during proposal preparation')
    executions = [dict(r) for r in database.execute('SELECT * FROM executors_running WHERE task_id=? ORDER BY id', (args.task,))]
    successor = next(r for r in executions if r['session_id'] == args.session)
    require(successor['agent_execution_id'] == transfer['successor_execution'], 'successor execution changed')
    queue = [dict(r) for r in database.execute('SELECT * FROM queued_messages WHERE task_id=? ORDER BY id', (args.task,))]
    require(not queue, 'new input: preserve FIFO; proposal preflight denied')
    module['candidate_check'](candidate, reservation, args.head, git_module)
    git = git_module['text_git']
    require(git(original, 'rev-parse', 'HEAD') == args.original_head
            and git(original, 'symbolic-ref', '--short', 'HEAD') == binding['worktree_branch'], 'original branch/head differs')
    require(git(original, 'rev-parse', 'refs/heads/' + args.branch) == args.base, 'failed-attempt branch differs')
    marker = original / '.git'
    require(sha(marker.read_bytes()) == transfer['preservation']['marker_sha256'], 'original marker differs')
    admin = Path(git(original, 'rev-parse', '--absolute-git-dir'))
    common = Path(binding['source']) / '.git'
    require(admin.parent == common / 'worktrees' and (admin / 'gitdir').read_text().strip() == str(marker), 'original administration/backlink differs')
    require(not os.access(common / 'worktrees', os.W_OK), 'shared worktree registry writable')
    contents = {}
    for raw in git_module['git'](original, 'ls-files', '-z', '--cached', '--others', '--exclude-standard').split(b'\0'):
        if not raw:
            continue
        name = os.fsdecode(raw)
        require(not name.startswith(('.kandev/hqa/' + transfer['slot'] + '/', '.kandev/hqa/.candidate-lease/')),
                'candidate capability paths no longer ignored')
        path = original / name
        contents[name] = ['symlink', os.readlink(path)] if path.is_symlink() else (
            ['file', sha(path.read_bytes()), path.stat().st_mode] if path.is_file() else ['missing'])
    require(digest(contents) == transfer['preservation']['files_sha256'], 'original files or PROMPT differ')
    sessions = [dict(r) for r in database.execute('SELECT * FROM task_sessions WHERE task_id=? ORDER BY id', (args.task,))]
    fences = dict(sessions=[r for r in sessions if r['id'] != args.session],
                  executors=[r for r in executions if r['session_id'] != args.session],
                  owner={k: owner[k] for k in ('id', 'task_id', 'repository_id', 'task_environment_id', 'workspace_path')},
                  owner_execution={k: successor[k] for k in ('id', 'session_id', 'local_pid', 'pid')})
    require(digest(fences) == transfer['preservation']['fences_sha256'], 'protected writer/accounting fence differs')
    preflight = dict(binding=binding, retired=transfer['retired'], successor_process=transfer['successor_process'],
                     successor_state=owner['state'], files_sha256=digest(contents), marker_sha256=sha(marker.read_bytes()),
                     sessions_sha256=digest(sessions), executions_sha256=digest(executions), fifo_count=0,
                     fences_sha256=digest(fences),
                     fifo_sha256=digest(queue), original_head=args.original_head, head=args.head,
                     prompt_sha256=sha((original / 'PROMPT.md').read_bytes()),
                     counters={k: v for k, v in owner.items() if isinstance(v, (int, float)) and
                               re.search(r'token|cost|iteration|budget|limit|turn|usage', k, re.I)})
    assessment = config_review(common, admin, candidate)
    packet = dict(version=VERSION, mode='proposal_only', adoption_authorized=False, installed=False,
                  caller_acceptance='not_run', source_admitted=False,
                  identity={k: transfer[k] for k in ('task', 'workspace', 'repo', 'original', 'original_head',
                            'head', 'base', 'branch', 'slot', 'successor', 'successor_execution')},
                  lineage=dict(reservation=args.reservation, reservation_sha256=args.reservation_sha256,
                               retirement=transfer['retirement']['receipt'], retirement_sha256=transfer['retirement']['receipt_sha256'],
                               transfer=args.transfer, transfer_sha256=args.transfer_sha256,
                               historical_report_sha256=args.historical_report_sha256, setup_audit_sha256=args.setup_audit_sha256),
                  contract=CONTRACT, contract_sha256=sha(CONTRACT.encode()), preflight=preflight,
                  preflight_sha256=digest(preflight), config_assessment=assessment,
                  mutable_ref_policy=dict(ref='refs/heads/feature/allow-coordinator-re-wxo',
                                          mode='reviewed_fast_forward_only', unclassified_delta='deny'),
                  review_helper_sha256=sha(source), adoption_blockers=assessment['blockers'],
                  baseline_status='not_created; complete maps required only in separately approved adoption')
    print(json.dumps(dict(proposal_sha256=digest(packet), **packet), sort_keys=True))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation', choices=('review',))
    for name in ('task', 'session', 'workspace', 'repo', 'original', 'original-head', 'head', 'base', 'branch',
                 'reservation', 'reservation-sha256', 'transfer', 'transfer-sha256',
                 'historical-report-sha256', 'setup-audit-sha256'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args()
    source = globals().get('__candidate_source__', None)
    if source is None:
        source = Path(__file__).read_bytes()
    review(args, source)


if __name__ == '__main__':
    try:
        main()
    except (ValueError, OSError, sqlite3.Error, subprocess.SubprocessError) as error:
        print('checkpoint proposal blocked: ' + str(error), file=sys.stderr)
        sys.exit(78)
