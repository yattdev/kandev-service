#!/usr/bin/env python3
"""Inert candidate execution-boundary review model; no Git or launch operation."""
import hashlib
import json
from pathlib import Path

PARENT_SHA = '13263a5a7b3ba34cefbce132ff288e73fa7a9be82d5f4baca406396c3e5b89db'
CONFIG_SHA = 'b8bf91476663506a6985c393a3b0c95f7cf8ab16e7bab938eb1a57b83d0c37d0'
UPSTREAM = 'https://github.com/kdlbs/kandev.git'
BRANCH = 'hqa/admission-current-main-93236820'
LOCAL_CONFIG = {
    'core.repositoryformatversion': '0', 'core.filemode': 'true',
    'core.bare': 'false', 'core.logallrefupdates': 'true',
    'remote.upstream.url': UPSTREAM,
    'remote.upstream.fetch': '+refs/heads/main:refs/remotes/upstream/main',
    'branch.main.remote': 'upstream', 'branch.main.merge': 'refs/heads/main',
    'branch.' + BRANCH + '.remote': 'upstream',
    'branch.' + BRANCH + '.merge': 'refs/heads/main',
}
READ_ACTIONS = {'status_without_optional_locks', 'inspect_pinned_commit',
                'diff_without_external_driver_or_textconv', 'inspect_index',
                'anonymous_upstream_main_advertisement'}
CONTRACT = '''Candidate capability-only execution boundary, version 1; preparation only.
1. This is a proposed prospective boundary, not an installed capability or
   retrospective proof. Parent proposal, old aggregate failures, reservation,
   retirement, transfer, helpers, markers, original/PROMPT and candidate history
   remain immutable. The shared historical interval remains explicitly unproven.
2. Two independent controls are required: a kernel Source write boundary and a
   trusted candidate Git mediator. An optional CLI wrapper alone is insufficient.
   The current wide Source provider is not made safe by nesting only its shell.
3. A future trusted lifecycle must contain the entire exact successor/provider
   and all tool/child processes in the candidate profile, with no surviving
   wider writer, writable inherited descriptor, writable ancestor or alternative
   namespace route. Validate actual mounts, ancestry, PID start time, binding,
   session/execution incarnation and absence of bypass paths. Existing 882/9af
   stays paused and unchanged now. If its current incarnation cannot acquire
   that boundary, deny adoption; any replacement/incarnation transition needs
   separate exact lifecycle authorization and append-only old/new evidence.
4. Source may write only the candidate worktree and separately approved scratch.
   Original checkout, shared Git and independent candidate Git administration
   are read-only or hidden to Source. Bind administration read-only after its
   writable parent; protect the mountpoint against rename, unlink and symlinks.
   No raw host/socket/path/credential authority, provider bypass or extra grant.
5. A separately isolated mediator is the only candidate-administration writer.
   It has no shared/original write mount and no other repository/ref authority.
   Authenticate the actual caller by kernel peer/launch identity and live backend
   binding, never supplied IDs alone or a copied token. Private PID namespace,
   separate security identity and descriptor isolation must prevent same-UID
   procfs/ptrace/fd access. Recheck authority before every operation; serialize
   candidate writes with a bounded lease. No generic shell/argv endpoint.
6. Git uses exact pinned independent admin/worktree identities and a reviewed
   read-only binary/dependency image, never PATH lookup or agent-supplied tools.
   Start from a fresh environment and empty private HOME/XDG. Suppress system,
   global and worktree config; accept only byte-pinned closed candidate config.
   Reject includes, aliases, filters, fsmonitor, SSH/proxy commands, credential
   helpers, push URLs, signing programs or new extensions/unknown keys. No
   inherited GIT_CONFIG/SSH/ASKPASS/loader/proxy/PATH customization. Independently
   reject commondir, alternates, linked admin and all path/symlink substitutions.
   Trusted invocation disables automatic GC/maintenance and optional locks for
   inspection; these are administration controls, not hook/signature waivers.
7. The pinned candidate has no hooks. Require that absence at operation time and
   keep hook/admin configuration unwritable to Source. Never select shared hooks
   or packages, and never disable a REQUIRED policy/signature gate to commit.
   No core.hooksPath override or blanket SKIP/HUSKY/signing bypass is approved.
8. Initially only typed local inspection and anonymous read-only advertisement
   of named upstream main are proposed. Use the explicit credential-free HTTPS
   identity, HTTPS-only protocol, no redirects/proxy/credential prompts/netrc,
   pinned transport helpers/TLS trust and bounded output/time. No fetch, push,
   local destination, SSH/helper selection, ref update or credential acquisition.
   Worktree attributes, diff drivers, textconv and filters must not execute code.
9. Future staging/local commit remains HELD. Policy-owner review must identify
   every applicable commit-message, formatting, lint, test and signature gate.
   Unknown or required-unsatisfied gates deny commit. A reviewed hermetic gate
   service may supply authenticated tree/parent/message/tool/policy-bound evidence
   without invoking unknown shared hooks. It must preserve required semantics,
   reject stale evidence and report reformatted-tree changes, never quietly waive
   a gate. Required signing without an approved signing boundary stays held.
   A later separately authorized implementation may write only the leased
   candidate branch/index/objects/reflog with exact before/after manifests.
10. Protect all original files, PROMPT, heads/base, marker/helper/receipt bytes,
    config, HEAD, packed-refs and non-authorized entries. Preserve FIFO, accounting
    and limits. Retain complete same-snapshot per-entry content/stat inventories;
    new checkpoint begins only at explicitly approved prospective adoption.
    Unknown/missing/removed/symlinked entries, old revival, foreign candidate
    writer, stale bindings/caller/incarnation, new FIFO or counter reset deny.
11. Retain the parent's finite sibling-owner observation rule: only the named
    same-common-Git 9349 owner/ref may yield authenticated proven fast-forward
    ref replacement, prefix-only reflog append and verified new reachable loose
    objects. Classify the entire inventory delta. No pack rewrite, deletion,
    other owner/ref or omitted entry. Candidate cannot write that ref. The d28
    owner uses different Git administration and is excluded without being paused.
    Revalidate eligible binding/ref and excluded binding; preserve legitimate
    independently approved progress without fabricating a stable shared snapshot.
12. All six parent blockers remain historically unresolved. Their authority is
    excluded only conditionally from this future isolated Git/Source write path;
    no boolean proves exclusion or adopts a baseline. Required future decisions:
    exact contract/proposal and namespace/mediator design approval, repository
    gate-equivalence policy, explicit unproven-historical-boundary decision,
    exact lifecycle route if needed, and separately reviewed implementation,
    enforcement tests, immutable adoption receipt and actual own-caller acceptance.
    Authentication, single-use expiry/nonce, physical enforcement proof and fresh
    inventories are mandatory outside this inert model. Root separately owns
    Source admission. This request authorizes none of those future operations.
'''


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def sha(value):
    return hashlib.sha256(value).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def closed_config(entries, byte_digest):
    """Format model; real bytes must be read/pinned by a future trusted broker."""
    require(byte_digest == CONFIG_SHA, 'candidate-local bytes differ')
    mapping = {}
    for key, value in entries:
        require(key not in mapping, 'duplicate config key')
        require(key in LOCAL_CONFIG and value == LOCAL_CONFIG[key], 'unclassified or executable candidate config')
        mapping[key] = value
    require(mapping == LOCAL_CONFIG, 'incomplete local config')
    return {'status': 'closed_config_shape_only', 'authority_granted': False}


def environment_shape(environment):
    """No live environment mutation or operation; only role-valued model input."""
    expected = {'HOME': 'empty_private_home', 'XDG_CONFIG_HOME': 'empty_private_xdg',
                'PATH': 'pinned_read_only_git_runtime', 'GIT_EXEC_PATH': 'pinned_read_only_git_helpers',
                'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_SYSTEM': 'empty_operator_config',
                'GIT_CONFIG_GLOBAL': 'empty_operator_config', 'GIT_CONFIG_COUNT': '0',
                'GIT_TERMINAL_PROMPT': '0', 'GIT_OPTIONAL_LOCKS': '0'}
    require(environment == expected, 'inherited or unknown environment authority')
    return {'status': 'sterile_environment_shape_only', 'authority_granted': False}


def topology_shape(topology):
    required = {'whole_provider_profile', 'no_wider_writer', 'no_writable_ancestor',
                'no_inherited_admin_fd', 'no_proc_ptrace_fd_bypass', 'private_pid_namespace',
                'separate_mediator_security_identity', 'mediator_no_shared_original_write',
                'read_only_pinned_runtime', 'no_extra_socket_or_credentials'}
    require(set(topology['evidence_roles']) == required, 'incomplete physical boundary evidence schema')
    require(topology['source_write_roles'] == ['candidate_worktree', 'approved_private_scratch'], 'foreign Source write role')
    require(topology['source_admin_mode'] == 'read_only_protected_mountpoint', 'Source can bypass Git mediator')
    require(topology['mediator_write_roles'] == ['independent_candidate_admin'], 'foreign mediator administration')
    require(not topology['symlink'] and not topology['commondir'] and not topology['alternates'], 'foreign or substituted Git administration')
    require(topology['external_proof_required'] is True, 'kernel/backend proof cannot be replaced by JSON')
    return {'status': 'topology_schema_only', 'enforcement_proved': False, 'authority_granted': False}


def caller_shape(identity, caller):
    required = ('task', 'workspace', 'repo', 'successor', 'successor_execution')
    require(set(caller) == set(required) and all(caller[k] == identity[k] for k in required), 'wrong caller or stale incarnation')
    return {'status': 'caller_shape_only', 'authenticated': False}


def operation_shape(action):
    require(action in READ_ACTIONS, 'mutating/foreign/unknown operation or arbitrary argv held')
    return {'status': 'read_action_shape_only', 'executed': False, 'authority_granted': False}


def gate_shape(policy, receipt):
    """Conservative policy model; even a matching receipt cannot authorize here."""
    require(policy['status'] == 'owner_reviewed' and policy['policy_sha256'], 'unknown required policy held')
    require(not receipt.get('waive_hooks') and not receipt.get('disable_signing'), 'required gate bypass denied')
    require(set(receipt['satisfied_gates']) == set(policy['required_gates']), 'unsatisfied or unclassified required gate')
    for key in ('tree', 'parent', 'message_sha256', 'policy_sha256', 'toolchain_sha256'):
        require(receipt.get(key) == policy.get(key), 'stale gate evidence')
    require(bool(receipt.get('authenticated_gate_receipt')), 'trusted gate receipt required outside JSON')
    return {'status': 'gate_receipt_shape_only', 'authenticated': False, 'commit_enabled': False}


def main():
    root = Path(__file__).resolve().parents[1]
    parent = (root / 'support-evidence/candidate-932-0588e44f-proposal.json').read_bytes()
    require(sha(parent) == PARENT_SHA, 'immutable parent proposal differs')
    print(encoded({'version': 'candidate-execution-boundary/1', 'mode': 'inert_review_model',
                   'parent_proposal_sha256': PARENT_SHA, 'contract': CONTRACT,
                   'contract_sha256': sha(CONTRACT.encode()), 'implemented': False,
                   'installed': False, 'adopted': False, 'caller_acceptance': 'not_run',
                   'source_admitted': False}).decode())


if __name__ == '__main__':
    main()
