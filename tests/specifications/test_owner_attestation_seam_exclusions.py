"""Offline seam-exclusion regressions; no live owner or control calls.

Reuse the reviewed preflight model. Evidence dictionaries below represent
insufficient static/legacy facts, never authenticated physical observations.
"""
import copy
import unittest

from test_owner_attestation_preflight import fixture, review


class OwnerSeamExclusions(unittest.TestCase):
    def test_guard_configuration_is_not_launch_or_closure_evidence(self):
        request, principal, owner = fixture()
        owner['authenticated_receipts'] = {}
        owner['guard_configuration'] = {
            'private_pid_namespace_supported': True,
            'die_with_parent': True,
            'coordinator_scope_revoked': True,
            'complete': True,
        }
        before = copy.deepcopy(owner)
        result = review(request, principal, owner)
        self.assertEqual(result['status'], 'HELD')
        self.assertIn('authenticated_descendant_coverage_ref', result['missing'])
        self.assertFalse(result['source_admission'])
        self.assertEqual(owner, before)

    def test_terminal_recovery_inventory_is_not_full_closure(self):
        request, principal, owner = fixture()
        owner['route'] = 'original'
        owner['executor_running'] = {'status': 'stopped', 'local_pid': 0}
        owner['execution_owner'] = {'task': principal['task'], 'session': principal['session']}
        result = review(request, principal, owner)
        self.assertEqual(result['status'], 'HELD')
        self.assertIn('original_launch_incarnations_and_closure', result['missing'])
        self.assertEqual(result['physical_action'], 'UNAVAILABLE')

    def test_other_platform_handle_cannot_fill_missing_supervisor_proof(self):
        request, principal, owner = fixture()
        owner['preexisting_record_ref'] = None
        owner['platform_handle'] = {'kind': 'WindowsJobObject', 'valid': True}
        result = review(request, principal, owner)
        self.assertEqual(result['status'], 'HELD')
        self.assertIn('authenticated_preexisting_scope_binding', result['missing'])
        self.assertFalse(result['source_admission'])


if __name__ == '__main__':
    unittest.main()
