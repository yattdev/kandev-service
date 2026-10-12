#!/usr/bin/env python3
"""Static, review-only semantic revision; never executes hooks or adopts state."""
import argparse
import ast
import contextlib
import hashlib
import hmac
import io
import json
import os
from pathlib import Path
import re
import shlex
import stat
import sys


V1_HELPER = '7c32db93b243becf513c102259d801545695daf05a185091560bb13074783b39'
V1_PROPOSAL = 'e4fcdeef114bdfa321b629037c9767f4bb76c7a05e6c2d10aa112f97a952e352'
OWNERS = (
    ('9349b6e5-a167-4d88-af14-cb355015e3dd', '48815ef5', 'refs/heads/feature/allow-coordinator-re-wxo', 'Root96c69 stableintent'),
    ('d28be44c-136f-47af-af5d-faa7e6381818', 'd2b0b80c', 'refs/heads/feature/fence-cancelled-task-9cs', 'Root73ea/8a repair packets'),
)
CONTRACT = '''Candidate prospective checkpoint contract, version 2; review only.
The unproven shared-config/inventory interval from the immutable v1 transfer
until any future adoption remains explicitly unproven. Historical hashes,
failures, v1 proposal, receipts, helpers and markers remain unchanged.
No adoption, baseline installation, Source admission or caller acceptance occurs.
Required approval fields are exact proposal/contract/config/preflight digests,
identity, lineage, finite mutable-ref policy, reviewer and authenticated Root,
repository/config and historical-preservation decision receipts, explicit new-
boundary and historical-gap acknowledgement, expiry and single-use nonce.
JSON or an approval boolean cannot authenticate authority or clear unknown code.
Before separately authorized adoption, revalidate original files/PROMPT/admin/
backlink/branch/head, failed-attempt ref, clean independent candidate head/base/
branch, all parent hashes, exact binding and retired predecessor, sole successor
session/execution/provider ancestry and incarnation, protected accounting and
limits, and empty FIFO. Preserve new input; no replay, disposal or counter reset.
Retain complete per-entry content/presence and size/mtime_ns/mode/inode maps
from one stable adoption snapshot, including object content hashes. Pin manifest
and scope digests in new append-only lineage; never claim retrospective proof.
Protect original932/candidate, config, HEAD, packed-refs, helper/receipt/marker
bytes and all non-authorized entries. Unknown includes, executable/config/code
targets, credential-bearing semantics and unclassified changes deny adoption.
Only exact task/session/execution/ref bindings marked same-common-Git in this
proposal's two-owner evaluation may produce authenticated owner operations.
An owner on different Git administration needs no exception and is not frozen.
This grants
candidate932 no foreign-ref write authority and does not pause independent work.
Each event needs exact old/new OIDs, verified commit ancestry without deletion
or rewrite, live registered same-common-Git owner/binding, authenticated Root
operation and owner guard receipts, and a complete per-entry delta. Only exact
ref replacement, prefix-preserving reflog append and newly added loose objects
verified by content/OID and reachability from that new tip are attributable.
Existing object edits/removals, pack changes, other refs or unrelated entries
remain blocking. Full inventory remains retained and classified, never ignored.
Actual adoption must freshly anchor eligible refs and excluded owner bindings,
and preserve any completed
approved owner progress, rather than require source owners to stop or roll back.
After adoption, own RUNNING/idle and monotonic usage progress may change; identity,
execution/process incarnation, budgets/limits and other writer fences stay pinned.
Only the actual successor guard may authenticate its own IDs and ancestry.
Old revival, foreign candidate writer, stale binding/incarnation, expired/reused
approval, new FIFO input or unmatched delta denies. No accepted caller command
exists until separately reviewed implementation/adoption and actual acceptance.
Root retains separate Source admission. Unknown hook closure stays held; a
scoped byte-pinned executable/config closure must be reviewed without running it.
'''


def require(ok, message):
    if not ok:
        raise ValueError(message)


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def digest(value):
    return sha(encoded(value))


def boolean(value):
    values = {'true': True, 'yes': True, 'on': True, '1': True,
              'false': False, 'no': False, 'off': False, '0': False}
    return values.get(value.lower())


def scoped_path(value, source, registered):
    if value == '*':
        return dict(scope='all_repositories', material_policy='broad ownership trust; outer filesystem guard unchanged')
    if not value.startswith('/') or '..' in Path(value).parts or value.endswith('/*'):
        return dict(scope='unclassified_path', blocker=True)
    # Never emit a host pathname. Exact registered identities are metadata, not
    # write grants; a broad parent is not treated as an exact repository.
    normalized = str(Path(value))
    if normalized in source:
        return dict(scope='exact_selected_registered_repository')
    if normalized in registered:
        result=dict(scope='different_registered_repository', blocker=True)
        if isinstance(registered,dict):result['repository_id']=registered[normalized]
        return result
    return dict(scope='unregistered_repository_or_path', blocker=True)


def semantic(name, value, key, v1, source_paths, registered_paths, verify_ref):
    row = v1['classify'](name, value, key)
    lower = name.lower()
    result = None
    if lower in ('safe.directory', 'maintenance.repo'):
        result = scoped_path(value, source_paths, registered_paths)
        row.update(classification='reviewed_trust_scope' if lower == 'safe.directory' else 'reviewed_maintenance_scope',
                   value=result, adoption_blocker=result.get('blocker', False))
        if lower == 'maintenance.repo':
            row['semantics'] = 'maintenance registration only; any actual pack rewrite remains prohibited by checkpoint policy'
    elif lower == 'color.ui' and value.lower() in ('auto', 'always', 'never', 'true', 'false'):
        row.update(classification='reviewed_display_enum', value=value.lower(), adoption_blocker=False)
    elif lower == 'gc.auto' and re.fullmatch(r'(0|[1-9][0-9]{0,5})', value) and int(value) <= 100000:
        row.update(classification='reviewed_gc_bound', value=int(value), adoption_blocker=False,
                   semantics='zero disables automatic loose-object GC; nonzero may cause policy-blocking pack changes')
    elif lower == 'maintenance.auto' and boolean(value) is not None:
        row.update(classification='reviewed_boolean', value=boolean(value), adoption_blocker=False,
                   semantics='pack mutation is never implicitly authorized')
    elif re.fullmatch(r'remote\.[A-Za-z0-9_-]+\.tagopt', lower) and value in ('--tags', '--no-tags'):
        row.update(classification='reviewed_tag_enum', value=value, adoption_blocker=False)
    elif lower == 'remote.upstream.gh-resolved' and value in ('base', 'head'):
        row.update(classification='reviewed_gh_role', value=value, adoption_blocker=False,
                   semantics='GitHub CLI repository-role hint; not a remote or permission grant')
    elif re.fullmatch(r'branch\.[A-Za-z0-9_/-]+\.vscode-merge-base', lower):
        if re.fullmatch(r'[0-9a-f]{40}', value) or (
                re.fullmatch(r'[A-Za-z0-9_/-]+', value) and '..' not in value and not value.startswith('-')):
            resolved = verify_ref(value)
            if resolved:
                row.update(classification='reviewed_commit_reference', value=resolved, adoption_blocker=False,
                           semantics='editor merge-base hint validated only in selected registered Git repository')
    elif re.fullmatch(r'remote\.compare-[0-9a-f]+\.pushurl', lower) and row['adoption_blocker']:
        # A nominal "DISABLED" token is still a relative filesystem push target
        # to Git. Never turn arbitrary strings into a disabled-authority claim.
        if re.fullmatch(r'[A-Za-z0-9_-]{1,64}', value):
            row.update(classification='relative_local_push_target', value='<withheld relative path>',
                       semantics='not a syntactically disabled remote; may select a local repository', adoption_blocker=True)
    if row['classification'] != v1['classify'](name,value,key)['classification']:
        row.pop('reason',None)
        if row['adoption_blocker']:
            row['reason']=row.get('semantics','configured scope has no approved exact selected-repository binding')
    return row


def bounded_bytes(path, limit=2 * 1024 * 1024):
    require(path.is_file() and not path.is_symlink() and path.stat().st_size <= limit,
            'static target unavailable, symlinked or exceeds bound')
    before = path.stat()
    raw = path.read_bytes()
    require(before == path.stat(), 'static target changed during review')
    return raw


def wrapper_trace(path, expected, original):
    raw = bounded_bytes(path)
    require(sha(raw) == expected, 'hook wrapper differs from byte-pinned v1')
    text = raw.decode()
    install = re.search(r'^INSTALL_PYTHON=(.*)$', text, re.M)
    args = re.search(r'^ARGS=\(([^\n]*)\)$', text, re.M)
    parsed = shlex.split(args.group(1)) if args else []
    expected_args = ['hook-impl', '--config=.pre-commit-config.yaml', '--hook-type=' + path.name]
    # Recognize the generated shape without executing it; every unknown shape
    # or fallback remains held. The pinned hash excludes hidden edits.
    shape = (install is not None and parsed == expected_args and '-mpre_commit' in text
             and 'command -v pre-commit' in text and 'ARGS+=(--hook-dir "$HERE" -- "$@")' in text)
    row = dict(hook=path.name, bytes_sha256=expected, interpreter='bash',
               wrapper_classified=shape, module='pre_commit' if shape else '<unclassified>',
               command_scope='hook-impl; fixed config and hook type; forwarded caller args' if shape else '<unclassified>',
               fallback='PATH pre-commit; runtime selection not authenticated by static bytes', adoption_blocker=True)
    if not shape:
        row['unresolved'] = ['wrapper grammar unclassified']
        return row
    interpreter_tokens = shlex.split(install.group(1))
    if len(interpreter_tokens) != 1:
        row['unresolved'] = ['interpreter expression unclassified']
        return row
    interpreter = Path(interpreter_tokens[0])
    allowed = ('/data/home/.local/share/', '/data/home/.cache/', '/usr/', '/opt/')
    if not str(interpreter).startswith(allowed):
        row['unresolved'] = ['interpreter target outside reviewed shared runtime scope; no foreign worktree accessed']
        return row
    try:
        target = interpreter.resolve(strict=True)
        require(str(target).startswith(allowed), 'interpreter resolves outside reviewed runtime scope')
        row['interpreter_sha256'] = sha(bounded_bytes(target, 64 * 1024 * 1024))
        row['interpreter_role'] = 'shared tool runtime; no pathname disclosed'
        roots = list((interpreter.parent.parent / 'lib').glob('python*/site-packages/pre_commit'))
        roots += list(Path('/data/home/.local/lib').glob('python*/site-packages/pre_commit'))
        roots += list(Path('/usr/local/lib').glob('python*/site-packages/pre_commit'))
        distro=Path('/usr/lib/python3/dist-packages/pre_commit')
        if distro.is_dir():roots.append(distro)
        candidates=[];seen=set()
        for root in roots:
            resolved=root.resolve(strict=True)
            require(str(resolved).startswith(allowed),'module target outside reviewed shared runtime scope')
            if resolved in seen:continue
            seen.add(resolved)
            require(len(candidates)<4,'module candidate bound exceeded')
            candidates.append(module_trace(resolved))
        row['module_candidates']=candidates
        row['module_resolution']='static possible targets only; caller PATH/PYTHONPATH and startup customization remain unproven'
        require(bool(candidates),'module target unavailable in bounded static locations')
        row['unresolved'] = ['PATH fallback can select another executable', 'external imports and installed hook environments not a complete byte-pinned closure',
                             'configuration-selected commands may install environments, fetch repositories and execute hook code']
    except (ValueError, OSError, SyntaxError):
        row['unresolved'] = ['interpreter/module closure inaccessible or unclassified; no execution attempted']
        row['module_resolution'] = 'no complete readable module target in bounded static runtime locations'
    configs = []
    for config in (original / '.pre-commit-config.yaml',):
        try:
            content = bounded_bytes(config)
            configs.append(dict(origin='original.pre_commit_config', bytes_sha256=sha(content),
                                command_scope='configuration-defined executable graph; held pending exact hook/environment closure',
                                declared_hooks=config_semantics(content,original)))
        except (ValueError, OSError):
            configs.append(dict(origin='original.pre_commit_config', presence='unavailable', adoption_blocker=True))
    row['config_targets'] = configs
    return row


def module_trace(root):
    files={};imports=set();calls=set();unparsed=0
    for item in sorted(root.rglob('*.py')):
        require(len(files)<512,'module trace exceeds bound')
        data=bounded_bytes(item);files[str(item.relative_to(root))]=sha(data)
        try:tree=ast.parse(data)
        except SyntaxError:
            unparsed+=1;continue
        for node in ast.walk(tree):
            if isinstance(node,ast.Import):imports.update(a.name.split('.')[0] for a in node.names)
            elif isinstance(node,ast.ImportFrom) and node.module:imports.add(node.module.split('.')[0])
            elif isinstance(node,ast.Call):
                expression=ast.unparse(node.func)
                if re.fullmatch(r'[A-Za-z0-9_.]+',expression):calls.add(expression)
    return dict(module='pre_commit',manifest_sha256=digest(files),files=len(files),entry_sha256=files.get('main.py'),
                external_imports=sorted(imports-{'pre_commit'}),unparsed_or_template_files=unparsed,
                dispatch_evidence=sorted(c for c in calls if re.search(r'cmd_output|run_hook|install|exec|clone|Popen',c))[:24],
                adoption_blocker=True)


def configuration_projection(content):
    """Bounded lexical declaration projection, never claims full YAML parsing."""
    text=content.decode();repos=[];repo=None;hook=None
    for line in text.splitlines():
        stripped=line.strip()
        match=re.fullmatch(r'- repo:\s*(.+)',stripped)
        if match:
            require(len(repos)<32,'configuration repository projection bound')
            repo={'repo':match.group(1).strip('"\''),'hooks':[]};repos.append(repo);hook=None;continue
        if repo is None:continue
        match=re.fullmatch(r'rev:\s*(.+)',stripped)
        if match:repo['rev']=match.group(1).strip('"\'');continue
        match=re.fullmatch(r'- id:\s*(.+)',stripped)
        if match:
            require(len(repo['hooks'])<64,'configuration hook projection bound')
            hook={'id':match.group(1).strip('"\'')};repo['hooks'].append(hook);continue
        if hook is None:continue
        match=re.fullmatch(r'(language|entry|args):\s*(.*)',stripped)
        if match:hook[match.group(1)]=match.group(2)
    require(bool(repos),'configuration projection unclassified')
    return {'repos':repos}


def command_projection(entry,original=None):
    """Identify declared tool scope; never execute or claim dependency closure."""
    row=dict(status='unclassified_command',adoption_blocker=True)
    if not isinstance(entry,str):return row
    try:tokens=shlex.split(entry)
    except ValueError:return row
    if not tokens:return row
    tools={'bash','sh','python','python3','node','npx','pnpm','npm','go','gofmt','uv','ruff'}
    if tokens[0] not in tools:return row
    row.update(status='declared_tool_only',tool=tokens[0],arguments='<withheld>',
               semantics='may launch child processes or load project/runtime configuration; not an approved executable closure')
    if original is not None and tokens[0] in ('bash','sh','python','python3','node') and len(tokens)>1:
        target=tokens[1]
        # Never follow an absolute path, option, traversal or symlink outside
        # this original checkout. Runtime tools/arguments remain unclassified.
        if re.fullmatch(r'[A-Za-z0-9_./-]+',target) and not target.startswith(('/','-')) and '..' not in Path(target).parts:
            path=original/target
            try:
                require(path.resolve().is_relative_to(original),'declared target escapes original')
                raw=bounded_bytes(path)
                row['original_target_sha256']=sha(raw)
                row['original_target_scope']='byte-pinned original-checkout script; imports/sourced files/children unreviewed'
                if tokens[0] in ('python','python3'):
                    tree=ast.parse(raw);imports=set()
                    for node in ast.walk(tree):
                        if isinstance(node,ast.Import):imports.update(a.name.split('.')[0] for a in node.names)
                        elif isinstance(node,ast.ImportFrom) and node.module:imports.add(node.module.split('.')[0])
                    row['module_names_sha256']=digest(sorted(imports))
                    row['module_count']=len(imports)
            except (OSError,ValueError,SyntaxError):row['original_target_scope']='unavailable or unclassified; no execution attempted'
    return row


def config_semantics(content,original=None):
    """Safe YAML parser, never pre_commit imports or configuration execution."""
    projection=False
    try:
        import yaml
        parsed = yaml.safe_load(content)
    except ImportError:
        try:parsed=configuration_projection(content);projection=True
        except (ValueError,UnicodeError):return dict(status='parser_unavailable_or_unclassified',adoption_blocker=True)
    except Exception:return dict(status='parser_unavailable_or_unclassified', adoption_blocker=True)
    if not isinstance(parsed, dict) or not isinstance(parsed.get('repos'), list) or len(parsed['repos']) > 32:
        return dict(status='unclassified_configuration', adoption_blocker=True)
    rows=[]
    for repo in parsed['repos']:
        if not isinstance(repo,dict):return dict(status='unclassified_configuration', adoption_blocker=True)
        location=repo.get('repo','')
        key=os.urandom(32)
        row=dict(repo_kind='local' if location=='local' else 'meta' if location=='meta' else 'remote',
                 repo_private_hash=hmac.new(key,str(location).encode(),hashlib.sha256).hexdigest(),hooks=[])
        if location not in ('local','meta'):
            # Credential-bearing remote identity is never emitted.
            try:
                from urllib.parse import urlsplit
                url=urlsplit(location)
                require(url.scheme=='https' and url.username is None and url.password is None
                        and not url.query and not url.fragment and re.fullmatch(r'/[A-Za-z0-9_./-]+',url.path),
                        'hook repository identity unreviewable')
                row['remote_identity']=dict(host=url.hostname,repository=url.path.lstrip('/'))
            except (ValueError,TypeError):row['remote_identity']='<withheld/unreviewable>'
        revision=repo.get('rev','')
        row['revision']=revision if isinstance(revision,str) and (re.fullmatch(r'[0-9a-f]{40}',revision) or re.fullmatch(r'v?[0-9]+\.[0-9]+\.[0-9]+',revision)) else '<withheld/unclassified>'
        hooks=repo.get('hooks',[])
        if not isinstance(hooks,list) or len(hooks)>64:return dict(status='hook_set_unclassified',adoption_blocker=True)
        for hook in hooks:
            if not isinstance(hook,dict):return dict(status='hook_set_unclassified',adoption_blocker=True)
            ident=hook.get('id','')
            language=hook.get('language','repository_manifest')
            item=dict(id=ident if isinstance(ident,str) and re.fullmatch(r'[a-z0-9_-]+',ident) else '<withheld>',
                      language=language if language in ('system','python','node','golang','script','docker','repository_manifest') else '<unclassified>',
                      executable_config_sha256=digest(hook),adoption_blocker=True)
            if 'entry' in hook:
                item['command_scope']=command_projection(hook['entry'],original)
            if 'args' in hook:item['args']='<withheld; no argument/header/credential values exposed>'
            row['hooks'].append(item)
        rows.append(row)
    return dict(status='lexical_declaration_projection_only' if projection else 'declared_scopes_only',repos=rows,adoption_blocker=True,
                limitation='repository manifests, environment installation, executable entrypoints and dependency closure still require byte-pinned review')


def event_shape(policy, event, authenticated_root=False, ancestry=False, reachable_objects=False):
    """Format gate only, no live acceptance/write; external proofs are mandatory."""
    require(authenticated_root, 'authenticated Root operation receipt required')
    matches = [r for r in policy if all(event.get(k) == r[k] for k in
                ('task', 'session', 'execution', 'ref', 'binding_id'))]
    require(len(matches) == 1 and matches[0]['same_registered_common_git'], 'foreign or stale source owner/ref binding')
    require(event.get('candidate_write_authority') is False, 'candidate cannot write foreign refs')
    require(all(re.fullmatch(r'[0-9a-f]{40}', event.get(k, '')) for k in ('old_oid', 'new_oid'))
            and event['old_oid'] != '0'*40 and event['new_oid'] != '0'*40
            and event['old_oid'] != event['new_oid'] and ancestry, 'deletion/rewrite/unproved ancestry denied')
    require(all(isinstance(event.get(k), str) and event[k] for k in ('root_operation_receipt', 'owner_guard_receipt')),
            'exact Root and owner receipts required')
    for delta in event.get('deltas', []):
        kind = delta.get('kind')
        if kind == 'ref':
            require(delta.get('path') == event['ref'], 'unrelated ref delta')
        elif kind == 'reflog_append':
            require(delta.get('path') == 'logs/' + event['ref'] and delta.get('prefix_preserved') is True,
                    'reflog rewrite denied')
        elif kind == 'loose_object_add':
            oid = delta.get('oid', '')
            require(re.fullmatch(r'[0-9a-f]{40}', oid) and delta.get('path') == 'objects/' + oid[:2] + '/' + oid[2:]
                    and delta.get('previously_absent') is True and delta.get('oid_content_verified') is True and reachable_objects,
                    'object mutation/unproved append denied')
        else:
            raise ValueError('pack, existing object or unclassified inventory mutation denied')
    require(bool(event.get('deltas')), 'complete per-entry delta required')
    return dict(status='event_shape_valid_only', write_grant=False, adoption=False)


def public_hook_review(traces):
    """Deduplicate identical config bytes without dropping unknown authority."""
    require(len(traces)==2,'both pinned wrappers required')
    targets=[h['config_targets'][0] for h in traces]
    require(all(len(h['config_targets'])==1 for h in traces),'unclassified extra hook config target')
    require(all(t.get('bytes_sha256')==targets[0].get('bytes_sha256') and t.get('bytes_sha256') for t in targets),
            'hook configuration unavailable or inconsistent')
    target=targets[0];declarations=target['declared_hooks'];rows=[];scopes=[]
    for repo in declarations.get('repos',[]):
        scope={k:v for k,v in repo.items() if k not in ('hooks','repo_private_hash','revision')}
        if repo.get('repo_kind') not in ('local','meta'):scope.update(private_hash=repo['repo_private_hash'],revision=repo['revision'])
        scopes.append(scope)
        for item in repo['hooks']:
            command=item.get('command_scope',{})
            row={k:v for k,v in item.items() if k not in ('command_scope','adoption_blocker')}
            row['tool']=command.get('tool','<unclassified>')
            for key in ('original_target_sha256','module_names_sha256','module_count','original_target_scope'):
                if key in command:row[key]=command[key]
            rows.append(row)
    configuration=dict(bytes_sha256=target['bytes_sha256'],origin=target['origin'],status=declarations['status'],
        repo_scopes=scopes,hooks=rows,all_adoption_blocked=True,arguments='withheld; no executable arguments/headers emitted',
        scope='declared tool dispatch only; imports, sourced code, children, runtime package/PATH resolution and complete executable/config semantics unproved',
        lexical_projection_is_not_full_yaml=declarations['status']=='lexical_declaration_projection_only')
    hooks=[]
    for item in traces:
        row={k:v for k,v in item.items() if k!='config_targets'}
        row['configuration_sha256']=target['bytes_sha256'];hooks.append(row)
    return hooks,configuration


def complete_delta(policy,event,before,after,**proofs):
    """All inventory differences must match the explicit event, never ignored."""
    changed={path for path in set(before)|set(after) if before.get(path)!=after.get(path) or (path in before)!=(path in after)}
    declared={row['path'] for row in event.get('deltas',[])}
    require(changed==declared and len(declared)==len(event.get('deltas',[])), 'unmatched, missing or duplicate full-inventory delta')
    for row in event['deltas']:
        require(row.get('before')==before.get(row['path']) and row.get('after')==after.get(row['path']),
                'exact entry evidence differs')
    return event_shape(policy,event,**proofs)


def owner_policy(database, args, common, git, original):
    rows = []
    for task, prefix, ref, provenance in OWNERS:
        found = database.execute('''SELECT ts.id AS session, ts.task_id AS task, x.agent_execution_id AS execution,
            er.id AS binding_id, er.worktree_branch, r.id AS repo, r.local_path AS source, t.workspace_id
            FROM tasks t JOIN task_sessions ts ON ts.task_id=t.id
            JOIN task_environment_repos er ON er.task_environment_id=ts.task_environment_id
            JOIN repositories r ON r.id=er.repository_id
            LEFT JOIN executors_running x ON x.task_id=t.id AND x.session_id=ts.id
            WHERE t.id=? AND ts.id LIKE ? AND t.workspace_id=? AND r.workspace_id=?
              AND er.status='active' AND er.deleted_at IS NULL AND r.deleted_at IS NULL''',
            (task, prefix + '%', args.workspace, args.workspace)).fetchall()
        require(len(found) == 1, 'exact named source owner metadata unavailable or ambiguous')
        row = dict(found[0])
        source_admin=Path(row.pop('source'))/'.git'
        require(source_admin.is_dir() and not source_admin.is_symlink(), 'registered source administration unavailable')
        admin_info,common_info=source_admin.stat(),common.stat()
        same=(admin_info.st_dev,admin_info.st_ino)==(common_info.st_dev,common_info.st_ino)
        require(row.pop('worktree_branch') == ref.removeprefix('refs/heads/'), 'named owner branch binding differs')
        tip = git(original, 'rev-parse', '--verify', ref + '^{commit}') if same else None
        rows.append(dict(task=row['task'],session=row['session'],execution=row['execution'],binding_id=row['binding_id'],
                         repo=row['repo'],ref=ref, observed_old_oid=tip, proposed_new_oid='must be supplied exactly in each authenticated event' if same else None,
                         same_registered_common_git=same, owner_mapping='registered source admin device/inode compared; foreign worktree/backlink not accessed',
                         root_provenance=provenance, candidate_write_authority=False,
                         operation_requirements=['exact old/new OIDs and commit ancestry','authenticated Root operation receipt',
                                                 'owner own-guard incarnation/backlink receipt','complete related per-entry delta'],
                         proposed_permissions='observation of approved owner progress only; no source/candidate grant' if same else 'excluded: different Git administration; unrelated source work unaffected'))
    return rows


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('task','session','workspace','repo','original','original-head','head','base','branch','reservation',
                'reservation-sha256','transfer','transfer-sha256','historical-report-sha256','setup-audit-sha256'):
        parser.add_argument('--'+key,required=True)
    parser.add_argument('--static-trace-only',action='store_true')
    args = parser.parse_args()
    require(os.environ.get('KANDEV_AGENT_GUARD_ACTIVE') == '1', 'existing guard required')
    v1_source = globals().get('__v1_source__')
    require(isinstance(v1_source, bytes) and sha(v1_source) == V1_HELPER, 'immutable v1 review helper required')
    prior = globals().get('__v1_proposal__')
    require(isinstance(prior, dict) and prior.get('proposal_sha256') == V1_PROPOSAL
            and digest({k:v for k,v in prior.items() if k!='proposal_sha256'}) == V1_PROPOSAL, 'immutable v1 proposal required')
    module = dict(__name__='v1_review', __file__='<retained-v1>')
    exec(compile(v1_source,'<retained-v1>','exec'),module)
    original = Path(args.original)
    require(original.resolve()==original and Path.cwd()==original,'exact original guard root required')
    if args.static_trace_only:
        current=globals().get('__current_review__')
        require(isinstance(current,dict) and digest(current)==globals().get('__current_review_sha256__'),
                'externally pinned retained bounded review required')
        require(current['identity']==prior['identity'],'retained review ownership differs')
        common=Path(current['preflight']['binding']['source'])/'.git'
        traces=[wrapper_trace(common/'hooks'/h['hook'],h['bytes_sha256'],original) for h in current['hooks']]
        for old,new in zip(current['hooks'],traces):
            require(old.get('interpreter_sha256')==new.get('interpreter_sha256'),'interpreter changed since bounded review')
            require(old['config_targets'][0]['bytes_sha256']==new['config_targets'][0]['bytes_sha256'],
                    'hook configuration changed since bounded review')
        print(encoded(dict(mode='static_trace_only',parent_review_sha256=digest(current),hooks=traces,
                           helper_sha256=sha(globals()['__candidate_source__']),adoption=False,execution=False)).decode())
        return
    database = module['sqlite3'].connect('file:/data/data/kandev.db?mode=ro',uri=True)
    database.row_factory = module['sqlite3'].Row
    registered = {r['local_path']:r['id'] for r in database.execute('SELECT id,local_path FROM repositories WHERE workspace_id=? AND deleted_at IS NULL',(args.workspace,))}
    registered.update({p.replace('/data/home/Code/','/home/ayattara/Code/'):registered[p] for p in list(registered) if p.startswith('/data/home/Code/')})
    source_paths = {'/data/home/Code/kandev-source','/home/ayattara/Code/kandev-source'}
    require(args.repo == prior['identity']['repo'] and args.original == prior['identity']['original'], 'selected repo differs')
    original_classify = module['classify']
    classifier_base = dict(module, classify=original_classify)
    git_helper = {}
    candidate = original / '.kandev/hqa/admission-current-main'
    original_source = (candidate / '.git/kandev-candidate-control.py').read_bytes()
    require(sha(original_source)=='d94e0fcec05f1d75b290553ef8e142f4986be95575ebe5a48cdbb44b450736a5','original helper differs')
    git_helper['__name__']='retained_git_helper'
    exec(compile(original_source,'<original-helper>','exec'),git_helper)
    git = git_helper['text_git']
    common = Path(git(original,'rev-parse','--path-format=absolute','--git-common-dir'))
    admin = Path(git(original,'rev-parse','--absolute-git-dir'))
    def verify_ref(value):
        try:
            oid = git(original,'rev-parse','--verify',value+'^{commit}')
            return dict(kind='commit_oid' if re.fullmatch(r'[0-9a-f]{40}',value) else 'selected_repo_commit_ref',oid=oid)
        except ValueError:return None
    module['classify'] = lambda name,value,key: semantic(name,value,key,classifier_base,source_paths,registered,verify_ref)
    def configuration(common, admin, candidate):
        key = os.urandom(32)
        locations = [(Path('/etc/gitconfig'),'system'),(Path('/data/home/.config/git/config'),'user.xdg'),
                     (Path('/data/home/.gitconfig'),'user'),(common/'config','shared'),
                     (admin/'config.worktree','original.worktree'),(candidate/'.git/config','candidate')]
        sources = [module['config_source'](p,label,key) for p,label in locations]
        traces = [wrapper_trace(common/'hooks'/n,h,original) for n,h in (
            ('commit-msg','bae3834dc9c39fd24091e8489a34778e13bc0fb1f30a312fa7eac3faa65e6efc'),
            ('pre-commit','5539e9d3d64329b4f49ed104400c1817edd9f1b87379a27594039172e9ca6259'))]
        return dict(shared_config_sha256=next(s['bytes_sha256'] for s in sources if s['origin']=='shared'),
                    sources=sources,hooks=traces,adoption_eligible=False,blockers=['hook executable/config closure unresolved'],
                    includes_executed=False,hooks_executed=False)
    module['config_review']=configuration
    policy=owner_policy(database,args,common,git,original)
    captured=io.StringIO()
    with contextlib.redirect_stdout(captured): module['review'](args,globals()['__candidate_source__'])
    reviewed=json.loads(captured.getvalue())
    selected={(s['origin'],r['key']) for s in prior['config_assessment']['sources'] for r in s['entries'] if r['adoption_blocker']}
    semantic_rows=[];other_counts={};source_info=[];blockers=[];remotes=[]
    for source in reviewed['config_assessment']['sources']:
        source_info.append({k:v for k,v in source.items() if k in ('origin','presence','bytes_sha256')})
        for row in source['entries']:
            if row['classification']=='credential_free_remote':remotes.append(dict(origin=source['origin'],key=row['key'],value=row['value']))
            if (source['origin'],row['key']) in selected or row['adoption_blocker']:
                public_row=dict(origin=source['origin'],**row)
                if not public_row['adoption_blocker']:public_row.pop('private_commitment',None)
                semantic_rows.append(public_row)
                if row['adoption_blocker']:blockers.append(dict(origin=source['origin'],key=row['key'],reason=row.get('semantics',row.get('reason','scope or value unclassified'))))
            else:other_counts[row['classification']]=other_counts.get(row['classification'],0)+1
    blockers.extend(dict(hook=h['hook'],reason=h['unresolved']) for h in reviewed['config_assessment']['hooks'])
    hooks,hook_configuration=public_hook_review(reviewed['config_assessment']['hooks'])
    packet=dict(version='candidate-prospective-checkpoint/2',mode='review_only',adoption_authorized=False,installed=False,
                source_admitted=False,caller_acceptance='not_run',parent_proposal_sha256=V1_PROPOSAL,
                parent_contract_sha256=prior['contract_sha256'],parent_helper_sha256=V1_HELPER,
                identity=reviewed['identity'],lineage=reviewed['lineage'],preflight=reviewed['preflight'],
                preflight_sha256=reviewed['preflight_sha256'],contract=CONTRACT,contract_sha256=sha(CONTRACT.encode()),
                config=dict(shared_config_sha256=reviewed['config_assessment']['shared_config_sha256'],sources=source_info,
                            reviewed_key_rows=semantic_rows,other_closed_class_counts=other_counts,
                            other_rows_semantics='v1 closed classifications only; no unknown authority omitted',
                            private_hashes='per-review HMAC with undisclosed ephemeral key; no raw credentials or paths retained',
                            credential_free_remote_identities=remotes,
                            includes_executed=False,executable_code_executed=False),
                hooks=hooks,hook_configuration=hook_configuration,mutable_ref_policy=policy,remaining_blockers=blockers,
                safe_alternative='Keep adoption held; obtain a scoped byte-pinned hook/config/runtime closure from the registered repository owner, including PATH fallback and installed hook environments, for static review. Preserve existing hook suppression in capability Git commands. No shared config write or Source pause is needed.',
                required_decisions=['review exact config semantics and finite policy','resolve hidden/unreviewable authority without boolean override',
                                    'separate explicit historical-boundary decision after reviewable authority','separately authorize implementation/adoption and actual own-caller verification'],
                review_helper_sha256=sha(globals()['__candidate_source__']))
    # Emit exactly the complete canonical body; its digest is external, avoiding
    # self-referential hashing. This compact review packet fits proactive delivery.
    raw=encoded(packet)
    require(len(raw)<23000,'canonical packet exceeds proactive review bound')
    print(raw.decode())


if __name__=='__main__':
    try:main()
    except (ValueError,OSError,KeyError) as error:
        print('v2 proposal blocked: '+str(error),file=sys.stderr);sys.exit(78)
