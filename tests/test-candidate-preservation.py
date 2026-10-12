#!/usr/bin/env python3
"""Offline manifest/provenance regression; no live Git or task operations."""
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'scripts/kandev-candidate-preservation.py'
spec = importlib.util.spec_from_file_location('preservation', SOURCE)
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class Preservation(unittest.TestCase):
    def setUp(self):
        self.common = '/data/home/Code/source/.git'
        self.admin = self.common + '/worktrees/original'
        self.ref = self.common + '/refs/heads/sibling'
        self.config = self.common + '/config'
        self.identity = dict(task='task', workspace='workspace', repo='repo', original='/data/tasks/task/source',
                             original_head='original', head='candidate', base='base', branch='hqa/candidate',
                             slot='candidate', successor='successor', successor_execution='execution')
        self.entries = dict(git_metadata_sha256={self.config: 'a' * 64, self.ref: 'b' * 64,
                                                self.admin + '/HEAD': 'c' * 64},
                            shared_inventory_sha256={self.config: [10, 100, 33188, 1000],
                                                     self.ref: [41, 101, 33188, 1001]})
        self.before = m.prospective_manifest(self.identity, copy.deepcopy(self.entries))
        self.transfer = dict(operation='transfer', receipt='transfer', **self.identity,
                             binding=dict(source='/data/home/Code/source'),
                             preservation=dict(**self.before['aggregates'],
                             marker_sha256=hashlib.sha256(('gitdir: ' + self.admin + '\n').encode()).hexdigest()))
        self.after = copy.deepcopy(self.entries)
        self.after['git_metadata_sha256'][self.ref] = 'd' * 64
        self.after['shared_inventory_sha256'][self.ref] = [41, 200, 33188, 2001]
        self.evidence = dict(schema=1, identity=self.identity, original_admin=self.admin,
                             before=self.before, after=m.prospective_manifest(self.identity, self.after),
                             recorded_observed={k: m.sha(v) for k, v in self.after.items()},
                             authorizations=[], unknowns=[], historical_entries=[])
        for collection in m.COLLECTIONS:
            self.authorize(collection, self.ref)

    def authorize(self, collection, path):
        self.evidence['authorizations'].append(dict(collection=collection, path=path,
            before=dict(present=path in self.entries[collection], value=self.entries[collection].get(path)),
            after=dict(present=path in self.after[collection], value=self.after[collection].get(path)),
            actor='exact-sibling-owner', operation='normal-commit', review_receipt='root-review',
            evidence_sha256='e' * 64))

    def analyze(self):
        return m.analyze(self.transfer, m.sha(self.transfer), self.evidence)

    def refresh_after(self):
        self.evidence['after'] = m.prospective_manifest(self.identity, self.after)
        self.evidence['recorded_observed'] = self.evidence['after']['aggregates']

    def test_exact_authorized_delta_is_offline_proof_only(self):
        before = copy.deepcopy(self.evidence)
        report = self.analyze()
        self.assertEqual(report['status'], 'offline_delta_proven')
        self.assertEqual(len(report['deltas']), 2)
        self.assertFalse(report['source_access_granted'])
        self.assertFalse(report['correction_issued'])
        self.assertEqual(before, self.evidence)

    def test_no_invented_baseline_even_with_known_ref(self):
        self.evidence['before'] = None
        self.evidence['historical_entries'] = [dict(collection='git_metadata_sha256', path=self.ref,
            before=dict(present=True, value='b' * 64), after=dict(present=True, value='d' * 64),
            evidence_sha256='e' * 64, attribution='Root-approved ref event')]
        report = self.analyze()
        self.assertEqual(report['status'], 'blocked')
        self.assertFalse(report['historical_entries'][0]['aggregate_proven'])

    def test_reconstruction_must_match_original_aggregate(self):
        changed = copy.deepcopy(self.entries)
        changed['git_metadata_sha256'][self.config] = 'f' * 64
        self.evidence['before'] = m.prospective_manifest(self.identity, changed)
        with self.assertRaisesRegex(ValueError, 'reproduce pinned aggregate'):
            self.analyze()

    def test_authorized_ref_never_authorizes_config(self):
        self.after['git_metadata_sha256'][self.config] = 'f' * 64
        self.refresh_after()
        report = self.analyze()
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue(any(row.get('path') == self.config for row in report['blockers']))

    def test_changed_removed_added_inventory_entries_all_reported(self):
        del self.after['shared_inventory_sha256'][self.config]
        added = self.common + '/objects/aa/bb'
        self.after['shared_inventory_sha256'][added] = [8, 300, 33060, 3001]
        self.refresh_after()
        report = self.analyze()
        self.assertEqual(report['status'], 'blocked')
        delta = {r['path']: r for r in report['deltas'] if r['collection'] == 'shared_inventory_sha256'}
        self.assertFalse(delta[self.config]['after']['present'])
        self.assertFalse(delta[added]['before']['present'])
        self.assertIn(self.ref, delta)

    def test_inventory_statistics_cannot_be_inferred_from_ref_bytes(self):
        self.evidence['authorizations'] = [self.evidence['authorizations'][0]]
        report = self.analyze()
        self.assertEqual(report['status'], 'blocked')
        self.assertTrue(any(r.get('collection') == 'shared_inventory_sha256' for r in report['blockers']))

    def test_unknowns_remain_blocking_even_with_complete_maps(self):
        self.evidence['unknowns'] = [dict(predicate='unattributed_config_setup')]
        self.assertEqual(self.analyze()['status'], 'blocked')

    def test_stale_ownership_and_marker_rejected(self):
        self.evidence['identity'] = dict(self.identity, successor_execution='replacement')
        with self.assertRaisesRegex(ValueError, 'incarnation'):
            self.analyze()
        self.evidence['identity'] = self.identity
        self.evidence['original_admin'] = self.common + '/worktrees/foreign'
        with self.assertRaisesRegex(ValueError, 'pinned marker'):
            self.analyze()

    def test_foreign_administration_and_tampered_aggregate_rejected(self):
        path = self.common + '/worktrees/foreign/HEAD'
        self.entries['git_metadata_sha256'][path] = 'f' * 64
        self.after['git_metadata_sha256'][path] = 'f' * 64
        self.before = m.prospective_manifest(self.identity, self.entries)
        self.transfer['preservation'].update(self.before['aggregates'])
        self.evidence['before'] = self.before
        self.refresh_after()
        with self.assertRaisesRegex(ValueError, 'outside exact original'):
            self.analyze()
        del self.entries['git_metadata_sha256'][path]
        self.evidence['before']['aggregates']['git_metadata_sha256'] = 'f' * 64
        with self.assertRaisesRegex(ValueError, 'aggregate or schema'):
            self.analyze()

    def test_cli_missing_history_exits_78_and_never_writes_inputs(self):
        self.evidence['before'] = None
        with tempfile.TemporaryDirectory() as folder:
            transfer, evidence = Path(folder) / 'transfer.json', Path(folder) / 'evidence.json'
            transfer.write_text(json.dumps(self.transfer))
            evidence.write_text(json.dumps(self.evidence))
            original = [p.read_bytes() for p in (transfer, evidence)]
            result = subprocess.run([sys.executable, str(SOURCE), '--transfer', str(transfer),
                '--transfer-sha256', m.sha(self.transfer), '--evidence', str(evidence)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 78)
            self.assertEqual(json.loads(result.stdout)['status'], 'blocked')
            self.assertEqual(original, [p.read_bytes() for p in (transfer, evidence)])
            evidence.write_text('{"schema":1,"schema":1}')
            result = subprocess.run([sys.executable, str(SOURCE), '--transfer', str(transfer),
                '--transfer-sha256', m.sha(self.transfer), '--evidence', str(evidence)], capture_output=True, text=True)
            self.assertEqual(result.returncode, 78)
            self.assertIn('duplicate JSON key', result.stderr)


if __name__ == '__main__':
    unittest.main()
