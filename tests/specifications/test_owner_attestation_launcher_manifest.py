"""Synthetic launcher metadata exclusions; never read a live manifest/socket."""
import unittest

from test_owner_attestation_preflight import fixture, review


class LauncherManifestExclusions(unittest.TestCase):
    def test_backend_manifest_does_not_authenticate_task_domain(self):
        request, principal, _ = fixture()
        legacy = {
            'version': 1, 'mode': 'run', 'created_at': 'synthetic-time',
            'task': principal['task'], 'workspace': principal['workspace'],
            'complete': True, 'backend_launch_manifest_ref': 'synthetic-global-manifest',
        }
        result = review(request, principal, legacy)
        self.assertEqual(result['status'], 'HELD')
        self.assertIn('protected_partition_ref', result['missing'])
        self.assertIn('descendant_coverage_ref', result['missing'])
        self.assertFalse(result['source_admission'])

    def test_control_accepted_reply_is_not_owner_attestation(self):
        request, principal, owner = fixture()
        owner['authenticated_receipts'] = {}
        owner['control_reply'] = {'accepted': True}
        result = review(request, principal, owner)
        self.assertEqual(result['status'], 'HELD')
        self.assertIn('authenticated_protected_partition_ref', result['missing'])
        self.assertEqual(result['physical_action'], 'UNAVAILABLE')


if __name__ == '__main__':
    unittest.main()
