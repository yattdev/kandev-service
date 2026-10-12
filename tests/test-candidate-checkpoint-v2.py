#!/usr/bin/env python3
"""Closed semantic and finite owner-policy regressions; no live Git/hooks."""
import copy
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
def module(name,file):
    spec=importlib.util.spec_from_file_location(name,ROOT/'scripts'/file)
    m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m);return m
v1=module('v1','kandev-candidate-checkpoint.py')
m=module('v2','kandev-candidate-checkpoint-v2.py')


class Semantics(unittest.TestCase):
    def classify(self,key,value):
        return m.semantic(key,value,b'private',vars(v1),{'/registered/selected'},{'/registered/other'},
                          lambda v:dict(kind='commit_ref',oid='a'*40) if v in ('origin/main','a'*40) else None)

    def test_trust_scope_never_discloses_or_grants_path(self):
        for value,scope,blocked in [('*','all_repositories',False),('/registered/selected','exact_selected_registered_repository',False),
                    ('/registered/other','different_registered_repository',True),('/secret/unregistered','unregistered_repository_or_path',True),
                    ('/registered/*','unclassified_path',True)]:
            r=self.classify('safe.directory',value)
            self.assertEqual(r['value']['scope'],scope);self.assertEqual(r['adoption_blocker'],blocked)
            self.assertNotIn('/secret',str(r))
        self.assertTrue(self.classify('maintenance.repo','/unregistered')['adoption_blocker'])

    def test_safe_enums_booleans_and_bounded_integers(self):
        for key,value in [('color.ui','auto'),('remote.upstream.gh-resolved','base'),('remote.compare-abc.tagopt','--no-tags'),
                          ('gc.auto','0'),('maintenance.auto','false')]:
            self.assertFalse(self.classify(key,value)['adoption_blocker'])
        for key,value in [('color.ui','!exec'),('remote.upstream.gh-resolved','arbitrary'),('remote.compare-abc.tagopt','--exec'),
                          ('gc.auto','-1'),('gc.auto','100001'),('maintenance.auto','maybe')]:
            self.assertTrue(self.classify(key,value)['adoption_blocker'])

    def test_merge_base_needs_real_object_or_ref_validity(self):
        key='branch.feature/test.vscode-merge-base'
        self.assertFalse(self.classify(key,'origin/main')['adoption_blocker'])
        for value in ('missing/ref','main@{1}','--exec','https://secret'):
            self.assertTrue(self.classify(key,value)['adoption_blocker'])

    def test_push_disabled_token_is_still_local_authority(self):
        key='remote.compare-abc.pushurl'
        self.assertEqual(self.classify(key,'DISABLED')['classification'],'relative_local_push_target')
        self.assertTrue(self.classify(key,'DISABLED')['adoption_blocker'])
        self.assertFalse(self.classify(key,'https://github.com/kdlbs/kandev.git')['adoption_blocker'])
        self.assertNotIn('SECRET',str(self.classify(key,'https://x:SECRET@github.com/repo.git')))

    def test_includes_commands_and_credentials_stay_held(self):
        for key,value in [('include.path','/secret'),('credential.helper','!exec SECRET'),('alias.x','!sh'),('filter.x.clean','exec')]:
            r=self.classify(key,value);self.assertTrue(r['adoption_blocker']);self.assertNotIn('SECRET',str(r))

    def test_hook_config_is_static_declaration_not_closure(self):
        r=m.config_semantics(b'repos:\n- repo: local\n  hooks:\n  - id: private-check\n    language: system\n    entry: echo SECRET\n')
        self.assertTrue(r['adoption_blocker']);self.assertNotIn('SECRET',str(r))

    def test_module_and_script_review_never_runs_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            (root/'main.py').write_text("raise RuntimeError('NEVER IMPORT THIS')\nimport subprocess\nsubprocess.Popen(['SECRET'])\n")
            trace=m.module_trace(root)
            self.assertEqual(trace['files'],1)
            self.assertIn('subprocess',trace['external_imports'])
            self.assertTrue(trace['adoption_blocker']);self.assertNotIn('SECRET',str(trace))
            command=m.command_projection('python3 main.py SECRET',root)
            self.assertEqual(command['tool'],'python3')
            self.assertIn('original_target_sha256',command)
            self.assertNotIn('SECRET',str(command));self.assertTrue(command['adoption_blocker'])
            escape=m.command_projection('python3 ../outside.py',root)
            self.assertNotIn('original_target_sha256',escape)

    def test_lexical_projection_is_never_full_yaml_or_executable_proof(self):
        raw=b'repos:\n- repo: local\n  hooks:\n  - id: checker\n    language: system\n    entry: npx private-check --token SECRET\n'
        projected=m.configuration_projection(raw)
        self.assertEqual(projected['repos'][0]['hooks'][0]['id'],'checker')
        reviewed=m.config_semantics(raw)
        self.assertTrue(reviewed['adoption_blocker']);self.assertNotIn('SECRET',str(reviewed))
        self.assertTrue(reviewed['repos'][0]['hooks'][0]['command_scope']['adoption_blocker'])


class Policy(unittest.TestCase):
    def setUp(self):
        self.policy=[dict(task='owner1',session='session1',execution='exec1',binding_id='binding1',
                          ref='refs/heads/one',same_registered_common_git=True),
                     dict(task='owner2',session='session2',execution='exec2',binding_id='binding2',
                          ref='refs/heads/two',same_registered_common_git=True)]
        self.event=dict(self.policy[0],candidate_write_authority=False,old_oid='a'*40,new_oid='b'*40,
                        root_operation_receipt='root',owner_guard_receipt='owner',
                        deltas=[dict(kind='ref',path='refs/heads/one')])

    def check(self):return m.event_shape(self.policy,self.event,authenticated_root=True,ancestry=True,reachable_objects=True)

    def test_two_owners_observation_never_grants_foreign_write(self):
        self.assertFalse(self.check()['write_grant'])
        self.event.update(self.policy[1]);self.event['deltas']=[dict(kind='ref',path='refs/heads/two')]
        self.assertFalse(self.check()['adoption'])
        self.event['candidate_write_authority']=True
        with self.assertRaises(ValueError):self.check()

    def test_foreign_owner_stale_execution_and_unrelated_ref_denied(self):
        for field,value in [('task','foreign'),('execution','restarted'),('ref','refs/heads/other')]:
            old=copy.deepcopy(self.event);self.event[field]=value
            with self.assertRaises(ValueError):self.check()
            self.event=old

    def test_rewrite_delete_pack_object_and_log_rewrite_denied(self):
        with self.assertRaises(ValueError):m.event_shape(self.policy,self.event,authenticated_root=True,ancestry=False)
        self.event['new_oid']='0'*40
        # Even an asserted ancestry cannot make deletion an accepted event.
        with self.assertRaises(ValueError):m.event_shape(self.policy,self.event,authenticated_root=True,ancestry=True)
        self.event['new_oid']='b'*40
        for delta in [dict(kind='pack',path='objects/pack/new'),dict(kind='existing_object_edit',path='objects/aa/bb'),
                      dict(kind='reflog_append',path='logs/refs/heads/one',prefix_preserved=False)]:
            self.event['deltas']=[delta]
            with self.assertRaises(ValueError):self.check()

    def test_complete_inventory_cannot_omit_unknown_change(self):
        before={'refs/heads/one':'old','config':'protected'}
        after={'refs/heads/one':'new','config':'tampered'}
        self.event['deltas'][0].update(before='old',after='new')
        with self.assertRaisesRegex(ValueError,'full-inventory'):
            m.complete_delta(self.policy,self.event,before,after,authenticated_root=True,ancestry=True)
        after['config']='protected'
        self.assertFalse(m.complete_delta(self.policy,self.event,before,after,authenticated_root=True,ancestry=True)['adoption'])

    def test_different_common_git_and_unproved_object_denied(self):
        self.policy[0]['same_registered_common_git']=False
        with self.assertRaises(ValueError):self.check()
        self.policy[0]['same_registered_common_git']=True
        oid='c'*40
        self.event['deltas'].append(dict(kind='loose_object_add',path='objects/'+oid[:2]+'/'+oid[2:],oid=oid,
                                         previously_absent=True,oid_content_verified=False))
        with self.assertRaises(ValueError):self.check()
        self.event['deltas'][-1]['oid_content_verified']=True
        self.assertFalse(self.check()['write_grant'])


class RetainedPacket(unittest.TestCase):
    def test_complete_canonical_packet_is_inert_and_links_actual_evidence(self):
        evidence=ROOT/'support-evidence'
        raw=(evidence/'candidate-932-0588e44f-proposal.json').read_bytes()
        packet=json.loads(raw)
        digests=json.loads((evidence/'candidate-932-0588e44f-digests.json').read_text())
        self.assertEqual(raw,m.encoded(packet))
        self.assertEqual(m.sha(raw),digests['proposal_sha256'])
        self.assertEqual(m.sha(packet['contract'].encode()),packet['contract_sha256'])
        for name,key in [('current-review','current_review_sha256'),('static-review','static_trace_sha256')]:
            self.assertEqual(m.sha((evidence/('candidate-932-0588e44f-'+name+'.json')).read_bytes()),packet[key])
        trace=json.loads((evidence/'candidate-932-0588e44f-static-review.json').read_text())
        hooks,configuration=m.public_hook_review(trace['hooks'])
        self.assertEqual(hooks,packet['hooks']);self.assertEqual(configuration,packet['hook_configuration'])
        self.assertEqual(packet['proposed_review_helper_sha256'],m.sha((ROOT/'scripts/kandev-candidate-checkpoint-v2.py').read_bytes()))
        trace['hooks'][1]['config_targets'][0]['bytes_sha256']='0'*64
        with self.assertRaises(ValueError):m.public_hook_review(trace['hooks'])
        self.assertFalse(packet['adoption_authorized']);self.assertFalse(packet['installed'])
        self.assertFalse(packet['source_admitted']);self.assertEqual(len(packet['remaining_blockers']),6)
        self.assertEqual([r['same_registered_common_git'] for r in packet['mutable_ref_policy']],[True,False])
        self.assertTrue(all(r['candidate_write_authority'] is False for r in packet['mutable_ref_policy']))
        self.assertEqual(len(packet['hooks']),2)
        self.assertTrue(all(r['adoption_blocker'] for r in packet['hooks']))
        self.assertIn('explicitly unproven',packet['contract'])


if __name__=='__main__':unittest.main()
