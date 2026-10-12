#!/usr/bin/env python3
"""Proposal-only config and approval regressions; no live provider operations."""
import copy
from datetime import datetime, timezone
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checkpoint', ROOT / 'scripts/kandev-candidate-checkpoint.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class ConfigReview(unittest.TestCase):
    def test_remote_password_and_headers_are_never_exposed(self):
        key = b'private test key'
        rows = [m.classify('remote.origin.url', 'https://alice:TOP_SECRET@github.com/kdlbs/kandev.git', key),
                m.classify('http.https://TOP_SECRET@github.com.extraHeader', 'Authorization: TOP_SECRET', key),
                m.classify('credential.helper', '!echo TOP_SECRET', key)]
        self.assertNotIn('TOP_SECRET', json.dumps(rows))
        self.assertTrue(all(row['adoption_blocker'] for row in rows))
        self.assertTrue(all(len(row['private_commitment']) == 64 for row in rows))

    def test_safe_remotes_retain_credential_free_identity(self):
        for value in ('https://github.com/kdlbs/kandev.git', 'git@github.com:kdlbs/kandev.git'):
            row = m.classify('remote.upstream.url', value, b'key')
            self.assertFalse(row['adoption_blocker'])
            self.assertEqual(row['value']['repository'], 'kdlbs/kandev.git')
        row = m.classify('remote.origin.url', 'https://github.com/repo.git?token=SECRET', b'key')
        self.assertTrue(row['adoption_blocker'])
        self.assertNotIn('SECRET', json.dumps(row))

    def test_include_is_reported_without_following_or_exposing_path(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            hidden = folder / 'hidden'
            hidden.write_text('NOT VALID GIT CONFIG; SECRET')
            config = folder / 'config'
            config.write_text('[core]\nfilemode = true\n[include]\npath = ' + str(hidden) + '\n')
            row = m.config_source(config, 'shared', b'key')
            self.assertFalse(row['includes_followed'])
            self.assertEqual(row['bytes_sha256'], m.sha(config.read_bytes()))
            self.assertNotIn(str(hidden), json.dumps(row))
            self.assertTrue(next(e for e in row['entries'] if e['key'] == 'include.path')['adoption_blocker'])
            self.assertEqual(hidden.read_text(), 'NOT VALID GIT CONFIG; SECRET')

    def test_exec_hooks_never_execute_or_disclose_code(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            hook = folder / 'pre-commit'
            hook.write_text('#!/bin/sh\necho TOP_SECRET\n')
            hook.chmod(0o700)
            result = m.hooks_review(folder, b'key')
            self.assertTrue(result['entries'][0]['adoption_blocker'])
            self.assertNotIn('TOP_SECRET', json.dumps(result))
            self.assertEqual(result['entries'][0]['bytes_sha256'], m.sha(hook.read_bytes()))

    def test_symlink_config_denied(self):
        with tempfile.TemporaryDirectory() as temporary:
            folder = Path(temporary)
            (folder / 'actual').write_text('[core]\nfilemode = true\n')
            (folder / 'config').symlink_to(folder / 'actual')
            with self.assertRaisesRegex(ValueError, 'symlink'):
                m.config_source(folder / 'config', 'shared', b'key')


class ApprovalReview(unittest.TestCase):
    def setUp(self):
        self.packet = dict(mode='proposal_only', adoption_authorized=False, installed=False, source_admitted=False,
                           contract_sha256=m.sha(m.CONTRACT.encode()), identity=dict(task='task', successor_execution='execution'),
                           lineage=dict(transfer='immutable'), preflight_sha256='a' * 64,
                           mutable_ref_policy=dict(ref='refs/heads/feature/allow-coordinator-re-wxo',mode='reviewed_fast_forward_only'),
                           adoption_blockers=[], config_assessment=dict(shared_config_sha256='b' * 64,adoption_eligible=True))
        self.rehash()
        self.approval = {k: self.packet[k] for k in ('proposal_sha256','contract_sha256','identity','lineage','preflight_sha256','mutable_ref_policy')}
        self.approval.update(shared_config_sha256='b' * 64, approve_new_boundary=True, acknowledge_unproven_interval=True,
                             approve_config_assessment=True, reviewer_id='root', review_receipt='review',
                             repository_review_receipt='repo-review', preservation_decision_receipt='decision',
                             expires_at='2030-01-01T00:00:00Z',single_use_nonce='unique')

    def rehash(self):
        self.packet['proposal_sha256'] = m.digest({k:v for k,v in self.packet.items() if k!='proposal_sha256'})

    def check(self):
        return m.approval_shape(self.packet, self.approval, authenticated_review=True,
                                now=datetime(2026,10,12,tzinfo=timezone.utc))

    def test_valid_shape_still_never_adopts_or_accepts_caller(self):
        result = self.check()
        self.assertFalse(result['adoption_performed'])
        self.assertEqual(result['caller_acceptance'], 'not_run')
        with self.assertRaisesRegex(ValueError, 'JSON is not authority'):
            m.approval_shape(self.packet, self.approval)

    def test_unreviewable_authority_cannot_be_approved_by_boolean(self):
        self.packet['adoption_blockers'] = [dict(key='credential.helper')]
        self.packet['config_assessment']['adoption_eligible'] = False
        self.rehash()
        self.approval['proposal_sha256'] = self.packet['proposal_sha256']
        with self.assertRaisesRegex(ValueError, 'unreviewable authority'):
            self.check()

    def test_approval_must_pin_caller_config_lineage_and_ref_policy(self):
        for field, value in [('identity',dict(task='foreign')),('shared_config_sha256','c'*64),
                             ('lineage',dict(transfer='replacement')),('mutable_ref_policy',dict(ref='*'))]:
            approval = copy.deepcopy(self.approval)
            self.approval[field] = value
            with self.assertRaises(ValueError): self.check()
            self.approval = approval

    def test_historical_gap_expiry_and_single_use_binding_required(self):
        for field,value in [('acknowledge_unproven_interval',False),('expires_at','2020-01-01T00:00:00Z'),('single_use_nonce','')]:
            approval = copy.deepcopy(self.approval)
            self.approval[field] = value
            with self.assertRaises(ValueError): self.check()
            self.approval = approval

    def test_no_install_or_adoption_cli(self):
        source = (ROOT / 'scripts/kandev-candidate-checkpoint.py').read_text()
        self.assertIn("choices=('review',)",source)
        self.assertNotIn('write_bytes(',source)
        self.assertNotIn('write_text(',source)


if __name__ == '__main__':
    unittest.main()
