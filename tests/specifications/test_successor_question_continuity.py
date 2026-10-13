#!/usr/bin/env python3
"""Offline decision specification. No API, database, credentials or live task reads.

OwnerFixture represents already authenticated backend records. It does not
implement authentication or make fixture grants usable by a real caller.
"""
import copy
import hashlib
import json
import unittest

PIN_KEYS = {'question_id', 'pending_id', 'question_message_id', 'question_sha256'}
IDENTITY = ('task', 'workspace', 'session', 'incarnation', 'execution')


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


class OwnerFixture:
    def __init__(self):
        self.current = dict(task='task-a', workspace='ws-a', session='successor',
                            incarnation='inc-a', execution='exec-a', primary='successor',
                            state='WAITING_FOR_INPUT', ownership_epoch=4, usage=10)
        self.after = copy.deepcopy(self.current)
        # Producer-shaped immutable bytes, including Go JSON HTML escaping.
        self.envelope = (b'{"id":"synthetic-q","options":[{"label":"Read '
                         b'\\u003cscope\\u003e","option_id":"a"},'
                         b'{"label":"Hold","option_id":"b"}],"prompt":"Synthetic?"}')
        self.original = dict(task='task-a', workspace='ws-a', session='original',
                             question_id='synthetic-q', pending_id='pending-a',
                             question_message_id='message-a', requesting_turn='turn-a',
                             question_sha256=digest(self.envelope), status='pending',
                             revision=7, after_revision=7, disconnected=True)
        self.grant = dict(task='task-a', workspace='ws-a', original_session='original',
                          successor='successor', successor_incarnation='inc-a',
                          successor_execution='exec-a', pending_id='pending-a',
                          question_message_id='message-a', question_sha256=digest(self.envelope),
                          scope='exact-original-question-receipt-read', authority_record='grant-a',
                          authority_epoch=4, expires_at=20)
        self.trusted_grants = {'grant-a'}
        self.answer = None
        self.trusted_native_receipts = set()
        self.resources = {'FIFO': ['unrelated-human-input'], 'counters': [9, 27],
                          'other_questions': ['fcb', 'b160', 'plugin19d3']}
        self.answer_reads = 0

    def pins(self):
        return {k: self.original[k] for k in PIN_KEYS}

    def caller(self):
        return {k: self.current[k] for k in IDENTITY}


def decide(pins, caller, owner, now=10):
    """Reference model only; caller/owner are supplied by trusted test fixtures."""
    result = dict(status='HELD', retry_allowed=False, recorded_answer=None,
                  visibility_entitlement_granted=False, mutation=False)
    if set(pins) != PIN_KEYS or any(
            not isinstance(v, str) or not v or len(v) > 128 for v in pins.values()):
        result.update(status='DENIED', missing=['exact_original_pins'])
        return result
    if len(pins['question_sha256']) != 64 or any(
            c not in '0123456789abcdef' for c in pins['question_sha256']):
        result.update(status='DENIED', missing=['exact_original_pins'])
        return result
    for k in IDENTITY:
        if not caller.get(k):
            result['missing'] = ['authenticated_current_' + k]
            return result
        if caller[k] != owner.current.get(k):
            result.update(status='DENIED', missing=['current_caller_mismatch'])
            return result
    if owner.current['primary'] != caller['session'] or owner.current['state'] not in (
            'RUNNING', 'WAITING_FOR_INPUT'):
        result.update(status='DENIED', missing=['current_successor_eligibility'])
        return result
    original = owner.original
    if original is None:
        result['missing'] = ['immutable_original_receipt']
        return result
    if any(original[k] != caller[k] for k in ('task', 'workspace')):
        result.update(status='DENIED', missing=['original_task_scope'])
        return result
    if any(original[k] != pins[k] for k in PIN_KEYS):
        result.update(status='DENIED', missing=['original_identity_or_digest'])
        return result
    grant = owner.grant
    if grant is None or grant['authority_record'] not in owner.trusted_grants:
        result['missing'] = ['authenticated_continuity_record']
        return result
    expected = dict(task=caller['task'], workspace=caller['workspace'],
                    original_session=original['session'], successor=caller['session'],
                    successor_incarnation=caller['incarnation'], successor_execution=caller['execution'],
                    pending_id=pins['pending_id'], question_message_id=pins['question_message_id'],
                    question_sha256=pins['question_sha256'], scope='exact-original-question-receipt-read')
    if any(grant.get(k) != v for k, v in expected.items()):
        result.update(status='DENIED', missing=['continuity_binding_or_scope'])
        return result
    if grant['expires_at'] <= now or grant['authority_epoch'] != owner.current['ownership_epoch']:
        result['missing'] = ['fresh_continuity_epoch']
        return result
    if digest(owner.envelope) != pins['question_sha256']:
        result.update(status='DENIED', missing=['forged_question_envelope'])
        return result
    owner.answer_reads += 1
    answer = owner.answer
    if answer is not None:
        if answer['receipt'] not in owner.trusted_native_receipts:
            result['missing'] = ['authenticated_original_native_answer_receipt']
            return result
        if any(answer[k] != original[k] for k in ('task', 'workspace', 'session', *PIN_KEYS)):
            result.update(status='DENIED', missing=['answer_original_binding'])
            return result
        question = json.loads(owner.envelope)
        valid_choice = (answer['kind'] == 'answer' and len(answer['choices']) == 1
                        and answer['choices'][0] in {o['option_id'] for o in question['options']})
        valid_rejection = answer['kind'] == 'rejection' and answer['choices'] == []
        if not (valid_choice or valid_rejection):
            result.update(status='DENIED', missing=['recorded_choice_validity'])
            return result
        if ((original['status'] == 'answered' and not valid_choice)
                or (original['status'] == 'rejected' and not valid_rejection)):
            result.update(status='DENIED', missing=['native_terminal_receipt_kind'])
            return result
    elif original['status'] in ('answered', 'rejected'):
        result['missing'] = ['authenticated_original_native_answer_receipt']
        return result
    if original['status'] not in ('pending', 'answered', 'rejected', 'expired', 'cancelled'):
        result['missing'] = ['known_native_lifecycle']
        return result
    if (any(owner.after.get(k) != caller[k] for k in IDENTITY)
            or owner.after['primary'] != caller['session']
            or owner.after['state'] not in ('RUNNING', 'WAITING_FOR_INPUT')
            or owner.after['ownership_epoch'] != grant['authority_epoch']
            or original['after_revision'] != original['revision']):
        result['missing'] = ['stable_final_owner_and_question_revision']
        return result
    result.update(status='READ_VERIFIED', native_lifecycle=original['status'],
                  original_session=original['session'], original_pins=copy.deepcopy(pins),
                  original_turn=original['requesting_turn'], disconnected=original['disconnected'],
                  recorded_answer=copy.deepcopy(answer), missing=[])
    return result


class SuccessorQuestionContinuityTests(unittest.TestCase):
    def test_missing_original_never_becomes_not_created_or_retry_permission(self):
        owner = OwnerFixture()
        pins = owner.pins()
        owner.original = None
        result = decide(pins, owner.caller(), owner)
        self.assertEqual(result['status'], 'HELD')
        self.assertFalse(result['retry_allowed'])

    def test_pending_disconnected_original_is_preserved_without_old_session_row(self):
        owner = OwnerFixture()  # No session registry or original-session row exists.
        result = decide(owner.pins(), owner.caller(), owner)
        self.assertEqual((result['status'], result['native_lifecycle']), ('READ_VERIFIED', 'pending'))
        self.assertTrue(result['disconnected'])
        self.assertEqual(result['original_session'], 'original')
        self.assertFalse(result['retry_allowed'])

    def test_current_primary_is_insufficient_without_exact_read_continuity(self):
        owner = OwnerFixture()
        owner.grant = None
        self.assertEqual(decide(owner.pins(), owner.caller(), owner)['status'], 'HELD')
        self.assertEqual(owner.answer_reads, 0)

    def test_forged_or_foreign_request_fields_are_rejected(self):
        for key in ('task', 'session', 'original_session', 'continuity', 'complete', 'answer', 'approved'):
            with self.subTest(key=key):
                owner = OwnerFixture()
                pins = owner.pins() | {key: 'untrusted'}
                self.assertEqual(decide(pins, owner.caller(), owner)['status'], 'DENIED')
                self.assertEqual(owner.answer_reads, 0)

    def test_missing_oversized_or_noncanonical_pins_are_rejected_before_read(self):
        owner = OwnerFixture()
        for pins in (owner.pins() | {'question_id': ''},
                     owner.pins() | {'question_id': 'x' * 129},
                     owner.pins() | {'question_sha256': 'A' * 64},
                     owner.pins() | {'question_sha256': 'x' * 64},
                     owner.pins() | {'question_sha256': '1' * 63}):
            with self.subTest(pins=pins):
                self.assertEqual(decide(pins, owner.caller(), owner)['status'], 'DENIED')
                self.assertEqual(owner.answer_reads, 0)

    def test_wrong_task_workspace_session_execution_or_incarnation(self):
        for key in IDENTITY:
            with self.subTest(key=key):
                owner = OwnerFixture()
                caller = owner.caller() | {key: 'foreign'}
                self.assertEqual(decide(owner.pins(), caller, owner)['status'], 'DENIED')
                self.assertEqual(owner.answer_reads, 0)

    def test_every_original_pin_and_question_envelope_is_checked(self):
        for key in PIN_KEYS | {'envelope', 'task', 'workspace'}:
            with self.subTest(key=key):
                owner = OwnerFixture()
                pins = owner.pins()
                if key == 'envelope': owner.envelope += b' '
                else: owner.original[key] = 'foreign'
                self.assertEqual(decide(pins, owner.caller(), owner)['status'], 'DENIED')

    def test_stale_or_broad_or_forged_continuity_cannot_read_answers(self):
        for key in ('authority_record', 'scope', 'successor', 'successor_incarnation',
                    'successor_execution', 'original_session', 'pending_id', 'question_sha256',
                    'expires_at', 'authority_epoch'):
            with self.subTest(key=key):
                owner = OwnerFixture()
                owner.grant[key] = 0 if key in ('expires_at', 'authority_epoch') else 'forged'
                self.assertIn(decide(owner.pins(), owner.caller(), owner)['status'], ('HELD', 'DENIED'))
                self.assertEqual(owner.answer_reads, 0)

    def test_legitimate_own_turn_and_accounting_progress_is_not_ownership_drift(self):
        owner = OwnerFixture()
        owner.after.update(state='RUNNING', usage=999)
        self.assertEqual(decide(owner.pins(), owner.caller(), owner)['status'], 'READ_VERIFIED')

    def test_changed_successor_or_original_revision_withholds_result(self):
        for key in (*IDENTITY, 'ownership_epoch', 'primary', 'question_revision'):
            with self.subTest(key=key):
                owner = OwnerFixture()
                if key == 'question_revision': owner.original['after_revision'] += 1
                else: owner.after[key] = 'changed'
                result = decide(owner.pins(), owner.caller(), owner)
                self.assertEqual(result['status'], 'HELD')
                self.assertIsNone(result['recorded_answer'])

    def answer_fixture(self, owner):
        answer = {k: owner.original[k] for k in ('task', 'workspace', 'session', *PIN_KEYS)}
        answer.update(receipt='native-answer-a', choices=['b'], kind='answer')
        owner.trusted_native_receipts.add(answer['receipt'])
        owner.original['status'] = 'answered'
        owner.answer = answer

    def test_only_existing_authenticated_original_native_answer_is_projected(self):
        owner = OwnerFixture()
        self.answer_fixture(owner)
        result = decide(owner.pins(), owner.caller(), owner)
        self.assertEqual(result['recorded_answer'], owner.answer)
        self.assertEqual(result['native_lifecycle'], 'answered')
        self.assertFalse(result['visibility_entitlement_granted'])

    def test_missing_or_foreign_or_fabricated_answer_is_not_inferred(self):
        for key in ('missing', 'receipt', 'session', 'question_sha256', 'choices', 'kind'):
            with self.subTest(key=key):
                owner = OwnerFixture()
                self.answer_fixture(owner)
                if key == 'missing': owner.answer = None
                elif key == 'choices': owner.answer[key] = ['invented-choice']
                else: owner.answer[key] = 'foreign'
                result = decide(owner.pins(), owner.caller(), owner)
                self.assertIn(result['status'], ('HELD', 'DENIED'))
                self.assertIsNone(result['recorded_answer'])

    def test_rejection_requires_existing_authenticated_native_rejection_receipt(self):
        owner = OwnerFixture()
        owner.original['status'] = 'rejected'
        self.assertEqual(decide(owner.pins(), owner.caller(), owner)['status'], 'HELD')
        self.answer_fixture(owner)
        owner.original['status'] = 'rejected'
        owner.answer.update(kind='rejection', choices=[])
        result = decide(owner.pins(), owner.caller(), owner)
        self.assertEqual(result['native_lifecycle'], 'rejected')
        self.assertEqual(result['recorded_answer']['choices'], [])

    def test_read_preserves_pending_input_counters_and_independent_barriers(self):
        owner = OwnerFixture()
        before = copy.deepcopy((owner.resources, owner.original, owner.grant))
        result = decide(owner.pins(), owner.caller(), owner)
        self.assertEqual((owner.resources, owner.original, owner.grant), before)
        self.assertFalse(result['mutation'])
        self.assertFalse(result['retry_allowed'])


if __name__ == '__main__':
    unittest.main()
