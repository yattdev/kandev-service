"""Offline contract model, not an installed authenticator or control surface.

Trusted snapshots below are synthetic fixtures. No PID, filesystem, DB, runtime,
HTTP, environment, credential or lifecycle operation is available in this model.
"""
import copy
import hashlib
import json
import unittest

TASK = 'd28be44c-136f-47af-af5d-faa7e6381818'
WORKSPACE = '2e62401b-5ffe-4050-bc1b-d49ea5d5dbcd'
CALLER = '833d9d08-69b8-4855-9ff8-6b05c59a1647'
REPOSITORY = 'a462935c-6825-463e-aff0-60b20f87f6fb'
EXECUTIONS = ['98fbeabc-5542-40ba-9d87-228ce3ddf370',
              'adea40f6-b704-4579-be95-4856810e7099']
PROTECTED = {'current833', 'privatePG', 'helper', 'shared', 'foreign', 'unique-state'}
INPUT_FIELDS = {'contract_sha256', 'preservation_receipt_id', 'preservation_sha256'}
REQUIRED = ['owner_epoch', 'registered_binding_ref', 'preservation_ref',
            'protected_partition_ref', 'descendant_coverage_ref',
            'escape_enforcement_ref', 'admission_coverage_ref']


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def review(request, principal, owner):
    """Specification gate using a separately authenticated owner's read view.

    Production must authenticate/resolve owner receipts through existing owners;
    passing this model a caller-built owner dictionary is not authentication.
    """
    if set(request) != INPUT_FIELDS:
        return {'status': 'DENIED', 'missing': ['input_schema']}
    if principal is None or principal.get('task') != TASK or principal.get('workspace') != WORKSPACE or principal.get('session') != CALLER or not principal.get('incarnation'):
        return {'status': 'DENIED', 'missing': ['authenticated_caller']}
    if owner is None:
        return {'status': 'HELD', 'missing': ['retained_authenticated_owner_record']}
    missing = []
    for key in REQUIRED:
        if not owner.get(key):
            missing.append(key)
    if principal['incarnation'] != owner.get('current_caller_incarnation'):
        missing.append('current_caller_incarnation')
    if owner.get('task') != TASK or owner.get('workspace') != WORKSPACE:
        missing.append('owner_task_workspace_binding')
    if owner.get('repository_id') != REPOSITORY:
        missing.append('registered_repository_binding')
    if owner.get('contract_sha256') != request['contract_sha256']:
        missing.append('contract_sha256')
    if (owner.get('preservation_ref') != request['preservation_receipt_id'] or
            owner.get('preservation_sha256') != request['preservation_sha256']):
        missing.append('preservation_receipt')
    if owner.get('owner_epoch') != owner.get('current_epoch') or owner.get('scope_generation') != owner.get('current_generation'):
        missing.append('epoch_or_generation')
    if owner.get('expires_at', 0) <= owner.get('read_at', 0):
        missing.append('expiry')
    if owner.get('read_revision') != owner.get('final_revision'):
        missing.append('consistent_read_revision')
    refs = owner.get('authenticated_receipts', {})
    for key in REQUIRED:
        ref = owner.get(key)
        record = refs.get(ref)
        if not proof_matches(record, owner, key):
            missing.append('authenticated_' + key)
    if set(owner.get('covered_executions', [])) != set(EXECUTIONS):
        missing.append('all_historical_execution_coverage')
    if owner.get('route') == 'prospective':
        if not owner.get('scope_id') or not owner.get('scope_generation') or not owner.get('preexisting_record_ref'):
            missing.append('preexisting_scope_binding')
        if not proof_matches(refs.get(owner.get('preexisting_record_ref')), owner, 'preexisting_scope'):
            missing.append('authenticated_preexisting_scope_binding')
        if owner.get('scope_created_at', 0) > owner.get('first_old_launch_at', 0):
            missing.append('preexisting_scope_interval')
    elif owner.get('route') == 'original':
        if set(owner.get('original_launch_refs', {})) != set(EXECUTIONS):
            missing.append('original_launch_incarnations_and_closure')
        for execution in EXECUTIONS:
            ref = owner.get('original_launch_refs', {}).get(execution)
            record = refs.get(ref)
            if (not proof_matches(record, owner, 'original_launch_closure') or
                    record['payload'].get('execution') != execution or
                    not record['payload'].get('original_session_incarnation') or
                    not record['payload'].get('original_launch_epoch') or
                    not record['payload'].get('full_closure_evidence_ref')):
                missing.append('authenticated_original_launch_closure_' + execution)
    else:
        missing.append('evidence_route')
    if any(member in PROTECTED for member in owner.get('scope_members', [])):
        missing.append('protected_resource_overlap')
    if owner.get('partition_members') != sorted(owner.get('scope_members', [])):
        missing.append('complete_protected_partition')
    if missing:
        return {'status': 'HELD', 'missing': sorted(set(missing)), 'physical_action': 'UNAVAILABLE', 'source_admission': False}
    return {'status': 'REVIEWABLE', 'missing': [], 'physical_action': 'UNAVAILABLE', 'source_admission': False, 'historical_proof': owner['route'] == 'original'}


def proof_matches(record, owner, kind):
    if record is None or record.get('issuer_epoch') != owner.get('owner_epoch'):
        return False
    payload = record.get('payload', {})
    return (record.get('payload_sha256') == digest(payload) and
            payload.get('task') == owner.get('task') and
            payload.get('workspace') == owner.get('workspace') and
            payload.get('repository_id') == owner.get('repository_id') and
            payload.get('kind') == kind and
            payload.get('scope') == owner.get('scope_id') and
            payload.get('generation') == owner.get('scope_generation') and
            bool(payload.get('immutable_evidence_ref')))


def add_proof(owner, ref, kind, extra=None):
    payload = {'task': TASK, 'workspace': WORKSPACE, 'repository_id': REPOSITORY, 'kind': kind,
               'scope': owner['scope_id'], 'generation': owner['scope_generation'],
               'immutable_evidence_ref': 'synthetic-proof-'+kind, **(extra or {})}
    owner['authenticated_receipts'][ref] = {
        'issuer_epoch': owner['owner_epoch'], 'payload': payload,
        'payload_sha256': digest(payload)}


def fixture():
    request = {'contract_sha256': 'synthetic-contract-hash',
               'preservation_receipt_id': 'synthetic-preservation',
               'preservation_sha256': 'synthetic-preservation-hash'}
    principal = {'task': TASK, 'workspace': WORKSPACE, 'session': CALLER, 'incarnation': 'synthetic-caller-incarnation'}
    owner = {'task': TASK, 'workspace': WORKSPACE, 'repository_id': REPOSITORY, 'route': 'prospective',
             'current_caller_incarnation': principal['incarnation'],
             'scope_id': 'synthetic-scope', 'scope_generation': 7, 'current_generation': 7,
             'owner_epoch': 'synthetic-owner-epoch', 'current_epoch': 'synthetic-owner-epoch',
             'expires_at': 200, 'read_at': 100, 'read_revision': 9, 'final_revision': 9,
             'scope_created_at': 10, 'first_old_launch_at': 20,
             'preexisting_record_ref': 'synthetic-preexisting-launch',
             'covered_executions': EXECUTIONS.copy(), 'scope_members': ['old-provider'],
             'partition_members': ['old-provider'], 'authenticated_receipts': {},
             **request}
    owner['preservation_ref'] = request['preservation_receipt_id']
    for key in REQUIRED:
        if key != 'owner_epoch' and key != 'preservation_ref':
            owner[key] = 'synthetic-' + key
        add_proof(owner, owner[key], key)
    add_proof(owner, owner['preexisting_record_ref'], 'preexisting_scope')
    return request, principal, owner


class PreflightSpecification(unittest.TestCase):
    def test_synthetic_preexisting_complete_disjoint_review_only(self):
        r, p, o = fixture()
        actual = review(r, p, o)
        self.assertEqual(actual['status'], 'REVIEWABLE')
        self.assertFalse(actual['historical_proof'])
        self.assertFalse(actual['source_admission'])
        self.assertEqual(actual['physical_action'], 'UNAVAILABLE')

    def test_synthetic_original_route_needs_actual_launch_references(self):
        r, p, o = fixture()
        o['route'] = 'original'
        self.assertEqual(review(r, p, o)['status'], 'HELD')
        o['original_launch_refs'] = {e: 'synthetic-original-' + e for e in EXECUTIONS}
        self.assertEqual(review(r, p, o)['status'], 'HELD')
        for e, ref in o['original_launch_refs'].items():
            add_proof(o, ref, 'original_launch_closure', {
                'execution': e, 'original_session_incarnation': 'synthetic-original-inc-'+e,
                'original_launch_epoch': 'synthetic-original-epoch',
                'full_closure_evidence_ref': 'synthetic-closure-'+e})
        self.assertEqual(review(r, p, o)['status'], 'REVIEWABLE')

    def test_caller_cannot_supply_scope_or_completeness(self):
        for key in ['complete', 'pid', 'path', 'scope_id', 'owner', 'targets', 'task_id', 'session_id']:
            r, p, o = fixture()
            r[key] = True
            with self.subTest(key=key):
                self.assertEqual(review(r, p, o)['status'], 'DENIED')

    def test_foreign_or_unavailable_authenticated_caller(self):
        r, p, o = fixture()
        self.assertEqual(review(r, None, o)['status'], 'DENIED')
        for key in ['task', 'workspace', 'session', 'incarnation']:
            bad = copy.deepcopy(p)
            bad[key] = '' if key == 'incarnation' else 'foreign'
            with self.subTest(key=key):
                self.assertIn(review(r, bad, o)['status'], ['DENIED', 'HELD'])

    def test_missing_record_never_fenced(self):
        r, p, _ = fixture()
        self.assertEqual(review(r, p, None)['status'], 'HELD')

    def test_coverage_boolean_cannot_replace_receipts(self):
        for key in REQUIRED:
            r, p, o = fixture()
            o[key] = None
            o['complete'] = True
            with self.subTest(key=key):
                self.assertEqual(review(r, p, o)['status'], 'HELD')

    def test_stale_binding_and_new_scope(self):
        for key, value in [('current_generation', 8), ('current_epoch', 'new-owner'),
                           ('current_caller_incarnation', 'replacement'), ('expires_at', 99),
                           ('final_revision', 10), ('preexisting_record_ref', None),
                           ('scope_created_at', 21), ('scope_id', None)]:
            r, p, o = fixture()
            o[key] = value
            with self.subTest(key=key):
                self.assertEqual(review(r, p, o)['status'], 'HELD')

    def test_partial_descendants_escape_or_admission(self):
        r, p, o = fixture()
        o['covered_executions'] = [EXECUTIONS[0]]
        self.assertEqual(review(r, p, o)['status'], 'HELD')
        for key in ['descendant_coverage_ref', 'escape_enforcement_ref', 'admission_coverage_ref']:
            r, p, o = fixture()
            del o['authenticated_receipts'][o[key]]
            self.assertEqual(review(r, p, o)['status'], 'HELD')

    def test_protected_partitions(self):
        for member in PROTECTED:
            r, p, o = fixture()
            o['scope_members'].append(member)
            o['partition_members'] = sorted(o['scope_members'])
            with self.subTest(member=member):
                result = review(r, p, o)
                self.assertEqual(result['status'], 'HELD')
                self.assertIn('protected_resource_overlap', result['missing'])

    def test_partial_partition_and_tampered_owner_receipt(self):
        r, p, o = fixture()
        o['partition_members'] = []
        self.assertEqual(review(r, p, o)['status'], 'HELD')
        r, p, o = fixture()
        o['authenticated_receipts'][o['descendant_coverage_ref']]['payload']['generation'] = 8
        self.assertEqual(review(r, p, o)['status'], 'HELD')

    def test_preservation_mismatch(self):
        r, p, o = fixture()
        r['preservation_sha256'] = 'changed'
        self.assertEqual(review(r, p, o)['status'], 'HELD')

    def test_proof_must_match_exact_task_kind_and_generation(self):
        for field, value in [('task', 'foreign'), ('workspace', 'foreign'),
                             ('kind', 'unrelated'), ('generation', 8), ('repository_id', 'foreign'),
                             ('immutable_evidence_ref', '')]:
            r, p, o = fixture()
            record = o['authenticated_receipts'][o['descendant_coverage_ref']]
            record['payload'][field] = value
            record['payload_sha256'] = digest(record['payload'])
            with self.subTest(field=field):
                self.assertEqual(review(r, p, o)['status'], 'HELD')

    def test_foreign_registered_repository(self):
        r, p, o = fixture()
        o['repository_id'] = 'foreign'
        self.assertEqual(review(r, p, o)['status'], 'HELD')

    def test_repeat_is_inert(self):
        r, p, o = fixture()
        before = copy.deepcopy((r, p, o))
        self.assertEqual(review(r, p, o), review(r, p, o))
        self.assertEqual((r, p, o), before)


if __name__ == '__main__':
    unittest.main()
