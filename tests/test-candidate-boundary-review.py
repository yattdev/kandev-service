#!/usr/bin/env python3
"""Synthetic exclusion/preservation tests; never launch Git, hooks or Source."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value
m=module('boundary','kandev-candidate-boundary-review.py')
v2=module('v2','kandev-candidate-checkpoint-v2.py')
parent=json.loads((ROOT/'support-evidence/candidate-932-0588e44f-proposal.json').read_bytes())


class Boundary(unittest.TestCase):
    def test_exact_config_and_all_executable_key_classes(self):
        entries=list(m.LOCAL_CONFIG.items())
        self.assertFalse(m.closed_config(entries,m.CONFIG_SHA)['authority_granted'])
        for key in ('include.path','includeIf.gitdir.path','alias.safe','filter.x.clean','core.sshCommand',
                    'credential.helper','remote.compare-dead.pushurl','core.hooksPath','core.fsmonitor',
                    'gpg.program','user.signingkey','extensions.worktreeConfig'):
            with self.subTest(key=key),self.assertRaises(ValueError):
                m.closed_config(entries+[(key,'unreviewed')],m.CONFIG_SHA)
        for bad in (entries[:-1],entries+[entries[0]]):
            with self.assertRaises(ValueError):m.closed_config(bad,m.CONFIG_SHA)
        with self.assertRaises(ValueError):m.closed_config(entries,'0'*64)

    def test_changed_remote_cannot_reuse_safe_config_hash(self):
        for url in ('file:private','git@host:private','https://user:SECRET@host/repo','/foreign/repository'):
            entries=[(k,url if k=='remote.upstream.url' else v) for k,v in m.LOCAL_CONFIG.items()]
            with self.assertRaises(ValueError):m.closed_config(entries,m.CONFIG_SHA)

    def environment(self):
        return dict(HOME='empty_private_home',XDG_CONFIG_HOME='empty_private_xdg',PATH='pinned_read_only_git_runtime',
                    GIT_EXEC_PATH='pinned_read_only_git_helpers',GIT_CONFIG_NOSYSTEM='1',
                    GIT_CONFIG_SYSTEM='empty_operator_config',GIT_CONFIG_GLOBAL='empty_operator_config',
                    GIT_CONFIG_COUNT='0',GIT_TERMINAL_PROMPT='0',GIT_OPTIONAL_LOCKS='0')

    def test_path_helper_loader_proxy_and_git_environment_cannot_leak(self):
        clean=self.environment();self.assertFalse(m.environment_shape(clean)['authority_granted'])
        for key in ('GIT_CONFIG_PARAMETERS','GIT_DIR','GIT_WORK_TREE','GIT_SSH_COMMAND','GIT_ASKPASS',
                    'SSH_ASKPASS','LD_PRELOAD','PYTHONPATH','HTTPS_PROXY','HUSKY','SKIP'):
            with self.subTest(key=key),self.assertRaises(ValueError):m.environment_shape(dict(clean,**{key:'SECRET'}))
        for key in ('PATH','HOME','GIT_EXEC_PATH'):
            bad=dict(clean);bad[key]='agent_mutable'
            with self.assertRaises(ValueError):m.environment_shape(bad)

    def topology(self):
        return dict(evidence_roles=['whole_provider_profile','no_wider_writer','no_writable_ancestor',
                    'no_inherited_admin_fd','no_proc_ptrace_fd_bypass','private_pid_namespace',
                    'separate_mediator_security_identity','mediator_no_shared_original_write',
                    'read_only_pinned_runtime','no_extra_socket_or_credentials'],
                    source_write_roles=['candidate_worktree','approved_private_scratch'],
                    source_admin_mode='read_only_protected_mountpoint',mediator_write_roles=['independent_candidate_admin'],
                    symlink=False,commondir=False,alternates=False,external_proof_required=True)

    def test_optional_wrapper_and_wider_provider_do_not_prove_boundary(self):
        shape=m.topology_shape(self.topology())
        self.assertFalse(shape['enforcement_proved']);self.assertFalse(shape['authority_granted'])
        for removed in ('whole_provider_profile','no_wider_writer','no_proc_ptrace_fd_bypass','no_inherited_admin_fd'):
            bad=self.topology();bad['evidence_roles'].remove(removed)
            with self.assertRaises(ValueError):m.topology_shape(bad)
        bad=self.topology();bad['source_admin_mode']='writable_by_source'
        with self.assertRaises(ValueError):m.topology_shape(bad)

    def test_symlink_linked_or_foreign_administration_denied(self):
        for flag in ('symlink','commondir','alternates'):
            bad=self.topology();bad[flag]=True
            with self.assertRaises(ValueError):m.topology_shape(bad)
        for key in ('source_write_roles','mediator_write_roles'):
            bad=self.topology();bad[key].append('shared_git')
            with self.assertRaises(ValueError):m.topology_shape(bad)

    def test_actual_caller_cannot_be_replaced_by_root_or_old_session(self):
        identity=parent['identity'];caller={k:identity[k] for k in ('task','workspace','repo','successor','successor_execution')}
        self.assertFalse(m.caller_shape(identity,caller)['authenticated'])
        for key in caller:
            bad=dict(caller);bad[key]='foreign'
            with self.assertRaises(ValueError):m.caller_shape(identity,bad)

    def test_no_push_fetch_commit_hook_shell_or_user_argv_operation(self):
        for action in m.READ_ACTIONS:self.assertFalse(m.operation_shape(action)['executed'])
        for action in ('push','fetch','commit','run_hook','git -c alias.x=exec x','local_push','update_foreign_ref','shell'):
            with self.assertRaises(ValueError):m.operation_shape(action)

    def gates(self):
        policy=dict(status='owner_reviewed',required_gates=['commit_message','format','lint','signature'],
                    tree='tree',parent='parent',message_sha256='message',policy_sha256='policy',toolchain_sha256='tools')
        receipt=dict(policy,satisfied_gates=list(policy['required_gates']),authenticated_gate_receipt='external-proof-reference')
        return policy,receipt

    def test_required_gate_or_signing_bypass_is_never_approved(self):
        policy,receipt=self.gates()
        shape=m.gate_shape(policy,receipt);self.assertFalse(shape['commit_enabled']);self.assertFalse(shape['authenticated'])
        for key in ('waive_hooks','disable_signing'):
            bad=dict(receipt);bad[key]=True
            with self.assertRaises(ValueError):m.gate_shape(policy,bad)
        receipt['satisfied_gates'].remove('signature')
        with self.assertRaises(ValueError):m.gate_shape(policy,receipt)
        policy['status']='unknown'
        with self.assertRaises(ValueError):m.gate_shape(policy,receipt)

    def test_tree_message_parent_tool_changes_stale_gate_evidence(self):
        policy,receipt=self.gates()
        for key in ('tree','parent','message_sha256','policy_sha256','toolchain_sha256'):
            bad=dict(receipt);bad[key]='changed'
            with self.assertRaises(ValueError):m.gate_shape(policy,bad)

    def test_complete_inventory_and_finite_sibling_progress_remain_required(self):
        policy=parent['mutable_ref_policy'];owner=policy[0]
        event={k:owner[k] for k in ('task','session','execution','ref','binding_id')}
        event.update(candidate_write_authority=False,old_oid='a'*40,new_oid='b'*40,
                     root_operation_receipt='authenticated-root-proof',owner_guard_receipt='authenticated-owner-proof',
                     deltas=[dict(kind='ref',path=owner['ref'],before='a',after='b')])
        before={owner['ref']:'a','config':'pinned','original':'pinned','candidate':'pinned','receipt':'pinned'}
        after=dict(before);after[owner['ref']]='b'
        result=v2.complete_delta(policy,event,before,after,authenticated_root=True,ancestry=True)
        self.assertFalse(result['adoption']);self.assertFalse(result['write_grant'])
        for key in ('config','original','candidate','receipt'):
            drift=dict(after);drift[key]='changed'
            with self.assertRaises(ValueError):v2.complete_delta(policy,event,before,drift,authenticated_root=True,ancestry=True)
        with self.assertRaises(ValueError):v2.complete_delta(policy,event,before,after,authenticated_root=False,ancestry=True)
        with self.assertRaises(ValueError):v2.complete_delta(policy,event,before,after,authenticated_root=True,ancestry=False)
        event.update({k:policy[1][k] for k in ('task','session','execution','ref','binding_id')})
        with self.assertRaises(ValueError):v2.event_shape(policy,event,authenticated_root=True,ancestry=True)

    def test_canonical_parent_and_contract_prohibit_live_authority(self):
        self.assertEqual(m.sha((ROOT/'support-evidence/candidate-932-0588e44f-proposal.json').read_bytes()),m.PARENT_SHA)
        self.assertIn('explicitly unproven',m.CONTRACT)
        self.assertIn('An optional CLI wrapper alone is insufficient',m.CONTRACT)
        self.assertIn('Required signing without an approved signing boundary stays held',m.CONTRACT)

    def test_retained_packet_is_byte_pinned_and_exclusion_is_conditional(self):
        evidence=ROOT/'support-evidence'
        raw=(evidence/'candidate-932-3c33a9fb-proposal.json').read_bytes();packet=json.loads(raw)
        digests=json.loads((evidence/'candidate-932-3c33a9fb-digests.json').read_bytes())
        self.assertEqual(raw,m.encoded(packet));self.assertEqual(m.sha(raw),digests['proposal_sha256'])
        self.assertEqual(m.sha(packet['contract'].encode()),packet['contract_sha256'])
        self.assertEqual(packet['contract'],m.CONTRACT)
        self.assertEqual(packet['review_model_sha256'],m.sha((ROOT/'scripts/kandev-candidate-boundary-review.py').read_bytes()))
        self.assertEqual(packet['parent_proposal_sha256'],m.PARENT_SHA)
        self.assertEqual(packet['lineage'],parent['lineage'])
        self.assertEqual(packet['finite_sibling_policy'],parent['mutable_ref_policy'])
        self.assertEqual(packet['retained_preflight_sha256'],parent['preflight_sha256'])
        static=(evidence/'candidate-932-3c33a9fb-static-review.json').read_bytes()
        self.assertEqual(m.sha(static),packet['static_candidate_review_sha256'])
        self.assertEqual(packet['static_candidate_review']['active_hook_count'],0)
        for key in ('implemented','installed','adopted','source_admitted'):self.assertFalse(packet[key])
        self.assertEqual(packet['caller_acceptance'],'not_run')
        self.assertTrue(all(not r['current_authority_resolved'] for r in packet['exclusion_verdicts']))


if __name__=='__main__':unittest.main()
