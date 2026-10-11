#!/usr/bin/env python3
"""Synthetic project-artifact acceptance; never opens the live DB or source trees."""
import hashlib
import importlib.machinery
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import tempfile
from unittest.mock import patch
import unittest

PATH = Path(os.environ.get('KANDEV_ARTIFACT_TEST_BROKER', str(Path(__file__).resolve().parents[1] / 'scripts/kandev-agent-docker-broker')))
loader = importlib.machinery.SourceFileLoader('artifact_broker_test', str(PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
b = importlib.util.module_from_spec(spec)
loader.exec_module(b)
PROJECT = '11111111-1111-4111-8111-111111111111'
COORD_REPO = '22222222-2222-4222-8222-222222222222'
CALLER = '33333333-3333-4333-8333-333333333333'
TARGET = '44444444-4444-4444-8444-444444444444'
WORKSPACE = '55555555-5555-4555-8555-555555555555'
OTHER = '66666666-6666-4666-8666-666666666666'


class Artifacts(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='artifact-fixture-')
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.code = self.base / 'Code'
        self.data = self.base / 'data'
        self.project = self.code / 'fixture'
        self.project.mkdir(parents=True)
        self.source = self.project / 'artifacts'
        self.source.mkdir()
        self.payload = b'SYNTHETIC TEST INPUT ONLY\n'
        self.file = self.source / 'fixture.sql'
        self.file.write_bytes(self.payload)
        self.file.chmod(0o400)
        self.source.chmod(0o500)
        self.addCleanup(lambda: self.source.chmod(0o700) if self.source.exists() and not self.source.is_symlink() else None)
        (self.data / 'tasks' / 'coordinator-fixture').mkdir(parents=True)
        self.target_root = self.data / 'tasks' / 'target-fixture'
        self.target_root.mkdir()
        for directory in (self.code, self.project, self.data, self.data / 'tasks',
                          self.data / 'tasks' / 'coordinator-fixture', self.target_root):
            directory.chmod(0o700)
        registry_dir = self.base / 'operator'
        registry_dir.mkdir(mode=0o700)
        self.registry_file = registry_dir / 'registry.json'
        self.registry = {'version': 1, 'projects': {PROJECT: {
            'workspace_id': WORKSPACE, 'repository_path': '/data/home/Code/fixture',
            'owner': 'Human', 'owner_uid': os.getuid(), 'directory': 'artifacts',
            'artifacts': {'fixture': {
                'file': 'fixture.sql', 'bytes': len(self.payload),
                'sha256': hashlib.sha256(self.payload).hexdigest(), 'compatible': True,
                'purpose': 'synthetic acceptance', 'format': 'sql', 'version': '1',
                'provenance': 'test-generated', 'refresh_rule': 'replace after review',
                'recipe': {'id': 'fixture-v1', 'instructions': 'Use only a task-owned test instance.',
                           'assertions': ['synthetic marker exists']}}}}}}
        self.save_registry()
        self.db = self.base / 'metadata.db'
        with sqlite3.connect(self.db) as db:
            db.executescript('''
                CREATE TABLE workspaces(id TEXT, name TEXT);
                CREATE TABLE repositories(id TEXT,workspace_id TEXT,local_path TEXT,deleted_at TEXT);
                CREATE TABLE tasks(id TEXT,workspace_id TEXT,workflow_step_id TEXT,state TEXT,title TEXT,metadata TEXT,parent_id TEXT,archived_at TEXT);
                CREATE TABLE task_repositories(task_id TEXT,repository_id TEXT);
                CREATE TABLE workflow_steps(id TEXT,name TEXT);
                CREATE TABLE task_environments(id TEXT,task_id TEXT,status TEXT,task_dir_name TEXT,workspace_path TEXT,ownership_generation INTEGER);
                CREATE TABLE task_sessions(task_id TEXT,task_environment_id TEXT,state TEXT,completed_at TEXT);
            ''')
            db.execute('INSERT INTO workspaces VALUES (?,?)', (WORKSPACE, 'synthetic'))
            for pid, path in ((PROJECT, '/data/home/Code/fixture'), (COORD_REPO, '/data/home/Code/coordinator')):
                db.execute('INSERT INTO repositories VALUES (?,?,?,NULL)', (pid, WORKSPACE, path))
            db.execute("INSERT INTO workflow_steps VALUES ('work','Development')")
            for tid, name, pid in ((CALLER, 'coordinator-fixture', COORD_REPO), (TARGET, 'target-fixture', PROJECT)):
                db.execute('INSERT INTO tasks VALUES (?,?,?,?,?,?,?,NULL)', (tid, WORKSPACE, 'work', 'IN_PROGRESS', 'Synthetic task', '{}', ''))
                db.execute('INSERT INTO task_repositories VALUES (?,?)', (tid, pid))
                db.execute('INSERT INTO task_environments VALUES (?,?,?,?,?,1)', ('env-' + name, tid, 'ready', name, '/data/tasks/' + name))
                db.execute('INSERT INTO task_sessions VALUES (?,?,?,NULL)', (tid, 'env-' + name, 'RUNNING'))
        for key, value in {'KANDEV_DB': self.db, 'ARTIFACT_REGISTRY': self.registry_file,
                           'ARTIFACT_REGISTRY_UID': os.getuid(), 'ARTIFACT_ROOT_UID': Path('/').stat().st_uid,
                           'ARTIFACT_RECEIPTS': self.base / 'receipts',
                           'COORDINATOR_AUDIT_LOG': self.base / 'audit.jsonl'}.items():
            p = patch.object(b, key, value)
            p.start()
            self.addCleanup(p.stop)
        p = patch.dict(os.environ, {'KANDEV_HOST_CODE_DIR': str(self.code), 'KANDEV_HOST_DATA_DIR': str(self.data)})
        p.start()
        self.addCleanup(p.stop)
        self.context = {'task_id': CALLER, 'workspace_id': WORKSPACE, 'workspace_name': 'synthetic'}

    def save_registry(self):
        if self.registry_file.exists():
            self.registry_file.chmod(0o600)
        self.registry_file.write_text(json.dumps(self.registry))
        self.registry_file.chmod(0o400)

    def update(self, sql, *args):
        with sqlite3.connect(self.db) as db:
            db.execute(sql, args)

    def discover(self):
        return b.artifact_discovery(self.context, PROJECT, 'fixture')[0]

    def deliver(self):
        return b.artifact_delivery(self.context, PROJECT, 'fixture', TARGET)

    def test_source_help_flags(self):
        for help_flag in ('help', '--help'):
            result = b.handle_coordinator_source(Path('/data/tasks/coordinator-fixture'),
                       ['kandev', 'source', help_flag])
            self.assertEqual(result['returncode'], 0)
            self.assertIn('artifact-discover', result['stdout'])

    def test_delivery_ack_and_metadata_only(self):
        response = b.handle_coordinator_source(Path('/data/tasks/coordinator-fixture'),
                    ['kandev', 'source', 'artifact-discover', PROJECT, 'fixture'])
        self.assertEqual(json.loads(response['stdout'])['status'], 'AVAILABLE')
        self.assertNotIn('SYNTHETIC TEST INPUT', response['stdout'])
        self.assertNotIn('instructions', response['stdout'])
        result = self.deliver()
        bundle = self.target_root / '.kandev-coordinator-inbox' / result['delivery_id']
        self.assertEqual((bundle / 'fixture.sql').read_bytes(), self.payload)
        self.assertEqual(set(p.name for p in bundle.iterdir()), {'fixture.sql', 'recipe.json', 'receipt.json'})
        self.assertEqual(self.file.read_bytes(), self.payload)
        self.assertIsNone(b.artifact_receipt(Path('/data/tasks/coordinator-fixture'), result['delivery_id'], context=self.context)['target_receipt'])
        for state in ('RECEIVED', 'CONSUMED', 'CONSUMED'):
            receipt = b.artifact_receipt(Path('/data/tasks/target-fixture'), result['delivery_id'], state, result['sha256'])
            self.assertEqual(receipt['target_receipt']['state'], state)
        self.update("UPDATE tasks SET state='DONE' WHERE id=?", TARGET)
        self.assertEqual(b.artifact_receipt(Path('/data/tasks/coordinator-fixture'), result['delivery_id'], context=self.context)['target_receipt']['state'], 'CONSUMED')
        self.assertNotIn('SYNTHETIC TEST INPUT', (self.base / 'audit.jsonl').read_text())

    def test_absent_without_creating_source(self):
        self.source.chmod(0o700)
        self.file.unlink()
        self.source.chmod(0o500)
        self.assertEqual(self.discover()['status'], 'ABSENT')
        self.source.chmod(0o700)
        self.source.rmdir()
        self.assertEqual(self.discover()['status'], 'ABSENT')
        self.assertFalse(self.source.exists())

    def test_stale_and_incompatible(self):
        self.file.chmod(0o600)
        self.file.write_bytes(b'changed')
        self.file.chmod(0o400)
        self.assertEqual(self.discover()['status'], 'STALE_OR_INCOMPATIBLE')
        with self.assertRaises(b.BrokerError): self.deliver()
        self.registry['projects'][PROJECT]['artifacts']['fixture']['compatible'] = False
        self.save_registry()
        self.assertEqual(self.discover()['status'], 'STALE_OR_INCOMPATIBLE')

    def test_source_symlink_hardlink_fifo_and_writable_rejected(self):
        for variant in ('symlink', 'hardlink', 'fifo', 'writable'):
            with self.subTest(variant=variant):
                self.source.chmod(0o700)
                self.file.unlink()
                alias = self.project / 'alias'
                alias.write_bytes(self.payload)
                alias.chmod(0o400)
                if variant == 'symlink': self.file.symlink_to(alias)
                elif variant == 'hardlink': os.link(alias, self.file)
                elif variant == 'fifo': os.mkfifo(self.file)
                else: self.file.write_bytes(self.payload)
                self.source.chmod(0o500)
                self.assertEqual(self.discover()['status'], 'INACCESSIBLE')
                alias.unlink()

    def test_directory_symlink_rejected(self):
        self.source.rename(self.project / 'hidden')
        self.source.symlink_to(self.project / 'hidden', target_is_directory=True)
        self.addCleanup(lambda: (self.project / 'hidden').chmod(0o700))
        self.assertEqual(self.discover()['status'], 'INACCESSIBLE')

    def test_registration_scope_owner_and_traversal(self):
        entry = self.registry['projects'][PROJECT]
        for key, value in (('owner', 'unknown'), ('workspace_id', OTHER), ('directory', '../outside'), ('repository_path', '/data/home/Code/repointed')):
            original = entry[key]
            entry[key] = value
            self.save_registry()
            self.assertEqual(self.discover()['status'], 'INACCESSIBLE')
            entry[key] = original
        self.save_registry()
        self.registry_file.chmod(0o600)
        self.assertEqual(self.discover()['status'], 'INACCESSIBLE')
        self.assertEqual(b.artifact_discovery(self.context, OTHER, 'fixture')[0]['status'], 'INACCESSIBLE')

    def test_target_cross_workspace_archived_lane_feature_and_inactive(self):
        for sql, value, restore in (
            ('UPDATE tasks SET workspace_id=? WHERE id=?', OTHER, WORKSPACE),
            ('UPDATE tasks SET archived_at=? WHERE id=?', 'now', None),
            ('UPDATE tasks SET state=? WHERE id=?', 'DONE', 'IN_PROGRESS'),
            ('UPDATE tasks SET title=? WHERE id=?', 'Feature 8241', 'Synthetic task'),
            ('UPDATE task_environments SET status=? WHERE task_id=?', 'deleted', 'ready'),
            ('UPDATE task_sessions SET state=? WHERE task_id=?', 'COMPLETED', 'RUNNING'),
        ):
            self.update(sql, value, TARGET)
            with self.assertRaises(b.BrokerError): self.deliver()
            self.update(sql, restore, TARGET)
        self.update("UPDATE workflow_steps SET name='ToDeploy'")
        with self.assertRaises(b.BrokerError): self.deliver()
        self.update("UPDATE workflow_steps SET name='Development'")
        self.update('UPDATE tasks SET parent_id=? WHERE id=?', CALLER, TARGET)
        self.update("UPDATE tasks SET title='Feature 8241' WHERE id=?", CALLER)
        with self.assertRaises(b.BrokerError): self.deliver()
        self.assertFalse((self.target_root / '.kandev-coordinator-inbox').exists())

    def test_ordinary_source_caller_denied(self):
        with self.assertRaises(b.BrokerError):
            b.handle_coordinator_source(Path('/data/tasks/target-fixture'), ['kandev', 'source', 'artifact-discover', PROJECT, 'fixture'])

    def test_target_receipt_wrong_task_hash_and_tampering(self):
        result = self.deliver()
        for root, checksum in ((Path('/data/tasks/coordinator-fixture'), result['sha256']), (Path('/data/tasks/target-fixture'), '0' * 64)):
            with self.assertRaises(b.BrokerError): b.artifact_receipt(root, result['delivery_id'], 'CONSUMED', checksum)
        foreign = dict(self.context, workspace_id=OTHER)
        with self.assertRaises(b.BrokerError): b.artifact_receipt(Path('/data/tasks/coordinator-fixture'), result['delivery_id'], context=foreign)
        bundle = self.target_root / '.kandev-coordinator-inbox' / result['delivery_id']
        (bundle / 'fixture.sql').write_bytes(b'tampered')
        with self.assertRaises(b.BrokerError): b.artifact_receipt(Path('/data/tasks/target-fixture'), result['delivery_id'], 'CONSUMED', result['sha256'])

    def test_destination_symlink_and_collision(self):
        inbox = self.target_root / '.kandev-coordinator-inbox'
        inbox.symlink_to(self.project, target_is_directory=True)
        with self.assertRaises(OSError): self.deliver()
        inbox.unlink()
        result = self.deliver()
        with patch.object(b.uuid, 'uuid4', return_value=result['delivery_id']):
            with self.assertRaises(FileExistsError): self.deliver()
        self.assertEqual((inbox / result['delivery_id'] / 'fixture.sql').read_bytes(), self.payload)

    def test_owner_mismatch_and_unsafe_source_directory(self):
        self.registry['projects'][PROJECT]['owner_uid'] = os.getuid() + 100
        self.save_registry()
        self.assertEqual(self.discover()['status'], 'INACCESSIBLE')
        self.registry['projects'][PROJECT]['owner_uid'] = os.getuid()
        self.save_registry()
        self.source.chmod(0o700)
        self.assertEqual(self.discover()['status'], 'INACCESSIBLE')

    def test_unknown_attachment_and_ambiguous_environment(self):
        self.update('DELETE FROM task_repositories WHERE task_id=?', TARGET)
        with self.assertRaises(b.BrokerError): self.deliver()
        self.update('INSERT INTO task_repositories VALUES (?,?)', TARGET, PROJECT)
        self.update("INSERT INTO task_environments VALUES ('second',?,'ready','second','/data/tasks/second',1)", TARGET)
        self.update("INSERT INTO task_sessions VALUES (?,'second','RUNNING',NULL)", TARGET)
        with self.assertRaises(b.BrokerError): self.deliver()
        self.assertFalse((self.target_root / '.kandev-coordinator-inbox').exists())

    def test_recipe_tampering_and_terminal_ack(self):
        result = self.deliver()
        root = Path('/data/tasks/target-fixture')
        recipe = self.target_root / '.kandev-coordinator-inbox' / result['delivery_id'] / 'recipe.json'
        original = recipe.read_bytes()
        recipe.write_bytes(b'tampered')
        with self.assertRaises(b.BrokerError): b.artifact_receipt(root, result['delivery_id'], 'CONSUMED', result['sha256'])
        recipe.write_bytes(original)
        b.artifact_receipt(root, result['delivery_id'], 'FAILED', result['sha256'])
        with self.assertRaises(b.BrokerError): b.artifact_receipt(root, result['delivery_id'], 'CONSUMED', result['sha256'])

    def test_collision_does_not_delete_target_file(self):
        original = b.artifact_write
        def write(directory, name, raw):
            if name == 'recipe.json':
                original(directory, name, b'target-created collision')
            return original(directory, name, raw)
        with patch.object(b, 'artifact_write', side_effect=write):
            with self.assertRaises(FileExistsError): self.deliver()
        files = list((self.target_root / '.kandev-coordinator-inbox').glob('*/recipe.json'))
        self.assertEqual(len(files), 1)
        self.assertEqual(files[0].read_bytes(), b'target-created collision')
        self.assertFalse(any(files[0].parent.glob('receipt.json')))

    def test_source_change_and_target_rebinding_before_publish(self):
        original = b.artifact_write
        for change in ('source', 'target', 'registry'):
            triggered = False
            def write(directory, name, raw):
                nonlocal triggered
                identity = original(directory, name, raw)
                if name == 'recipe.json' and not triggered:
                    triggered = True
                    if change == 'source':
                        self.file.chmod(0o600)
                        self.file.write_bytes(b'changed')
                        self.file.chmod(0o400)
                    elif change == 'target': self.update('UPDATE task_environments SET ownership_generation=2 WHERE task_id=?', TARGET)
                    else:
                        self.registry['projects'][PROJECT]['artifacts']['fixture']['version'] = '2'
                        self.save_registry()
                return identity
            with patch.object(b, 'artifact_write', side_effect=write):
                with self.assertRaises(b.BrokerError): self.deliver()
            self.file.chmod(0o600)
            self.file.write_bytes(self.payload)
            self.file.chmod(0o400)
            self.update('UPDATE task_environments SET ownership_generation=1 WHERE task_id=?', TARGET)
            self.assertFalse(any((self.target_root / '.kandev-coordinator-inbox').glob('*/receipt.json')))


def main():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(Artifacts)
    if not unittest.TextTestRunner(verbosity=1).run(suite).wasSuccessful():
        raise AssertionError('project artifact acceptance failed')


if __name__ == '__main__':
    main()
