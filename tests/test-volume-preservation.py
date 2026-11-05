#!/usr/bin/env python3
"""Exact-volume authorization and cold-archive integrity regression tests."""
import copy
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tarfile
import tempfile
import threading
from types import SimpleNamespace
import unittest


PATH = Path(__file__).resolve().parents[1] / 'scripts/kandev-agent-docker-operations.py'
SPEC = importlib.util.spec_from_file_location('volume_operations', PATH)
operations = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(operations)


class Denied(RuntimeError):
    pass


class AuthorizationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / 'task'
        self.cwd = self.root / 'performcoop'
        (self.cwd / '.tox/8241_recovery_20261030').mkdir(parents=True)
        original = operations.PRESERVATION_SCOPE
        self.addCleanup(setattr, operations, 'PRESERVATION_SCOPES', operations.PRESERVATION_SCOPES)
        self.scope = {**original, 'root': str(self.root)}
        operations.PRESERVATION_SCOPES = (self.scope,)
        db = Path(self.temp.name) / 'metadata.db'
        with sqlite3.connect(db) as con:
            con.executescript('''CREATE TABLE tasks(id,workspace_id);
                CREATE TABLE task_sessions(id,task_id,task_environment_id,state);
                CREATE TABLE task_environments(id,task_id,status,workspace_path);''')
            con.execute('INSERT INTO tasks VALUES(?,?)', (self.scope['task'], self.scope['workspace']))
            con.execute('INSERT INTO task_sessions VALUES(?,?,?,?)',
                        (self.scope['session'], self.scope['task'], 'environment', 'RUNNING'))
            con.execute('INSERT INTO task_environments VALUES(?,?,?,?)',
                        ('environment', self.scope['task'], 'ready', str(self.cwd)))
        self.model = {'volumes': {self.scope['logical']: {'name': self.scope['volume']}},
                      'services': {'db': {'volumes': [{'type': 'volume', 'source': self.scope['logical'],
                                                     'target': '/var/lib/mysql'}]}}}
        self.info = dict(Name=self.scope['volume'], Driver='local', Scope='local', Options=None,
                         CreatedAt=self.scope['created'], Mountpoint='/docker/volumes/'+self.scope['volume']+'/_data',
                         Labels={'com.docker.compose.project': self.scope['project'],
                                 'com.docker.compose.volume': self.scope['logical'],
                                 'com.docker.compose.config-hash': self.scope['config_hash']})
        self.calls = []
        self.consumers = ''
        self.absent = False
        self.fake_receipt = {'version': 'task-retained-volume-preservation/v1',
                             'source': {'inventory_metadata_sha256': 'a'*64, 'device': 123, 'inode': 456}, 'verified': True}
        self.b = SimpleNamespace(BrokerError=Denied, sqlite3=sqlite3, KANDEV_DB=db,
                                 ACTIVE_TASK_SESSION_STATES={'RUNNING'}, EXPORT_LOCK=threading.Lock(),
                                 DOCKER_BIN='docker', run_command=self.command,
                                 audit_compose=lambda *args, **kwargs: None,
                                 load_scoped_model=self.model_load, translate_to_host=lambda p:p)
        self.b.MODEL_DIR = Path(self.temp.name) / 'models'
        self.b.MODEL_DIR.mkdir(mode=0o700)
        self.op = operations.Operations(self.b, self.root, self.cwd)

    def model_load(self, root, cwd, project):
        self.assertEqual((root, cwd, project), (self.root, self.cwd/self.scope['model_directory'], self.scope['project']))
        return copy.deepcopy(self.model)

    def command(self, argv, cwd, **kwargs):
        self.calls.append(argv)
        args = argv[1:]
        if args[:2] == ['volume', 'inspect']:
            return (1, '', 'missing') if self.absent else (0, json.dumps([self.info]), '')
        if args[:2] == ['ps', '-aq']:
            return 0, self.consumers, ''
        if args[:1] == ['inspect']:
            return 0, 'sha256:'+'b'*64+'\n', ''
        if args[:1] == ['run']:
            self.assertNotIn('-v', args)
            self.assertNotIn('type=volume', ' '.join(args))
            self.assertIn('type=bind,source='+self.info['Mountpoint']+',target=/source,readonly,bind-propagation=rslave', args)
            self.assertIn('--read-only', args)
            self.assertEqual(args[args.index('--network')+1], 'none')
            self.assertNotIn('/var/run/docker.sock', ' '.join(args))
            return 0, json.dumps(self.fake_receipt), ''
        self.fail('unexpected Docker operation: '+repr(args))

    def invoke(self, mode='inspect', output='.tox/8241_recovery_20261030/db-cold-unit'):
        args = ['kandev', 'volume', mode, self.scope['volume']]
        if mode == 'preserve':
            args += ['--output', output]
        return self.op.handle(args)

    def test_inspect_never_creates_models_volumes_or_containers_with_named_mounts(self):
        self.assertEqual(self.invoke()['returncode'], 0)
        self.assertEqual([call[1] for call in self.calls], ['volume', 'ps', 'inspect', 'run', 'volume', 'ps'])

    def test_absent_volume_fails_before_any_helper(self):
        self.absent = True
        with self.assertRaises(Denied): self.invoke()
        self.assertEqual(len(self.calls), 1)

    def test_wrong_labels_driver_mountpoint_and_created_at_fail_closed(self):
        for key, value in [('Labels', {}), ('Driver', 'nfs'), ('Options', {'device': '/etc'}),
                           ('Mountpoint', '/outside'), ('CreatedAt', 'different')]:
            with self.subTest(key=key):
                saved = self.info[key]; self.info[key] = value; self.calls.clear()
                with self.assertRaises(Denied): self.invoke()
                self.assertFalse(any(call[1] == 'run' for call in self.calls))
                self.info[key] = saved

    def test_other_task_clone_volume_and_stale_model_are_denied(self):
        for attr, value in [('root', self.root.parent), ('cwd', self.root)]:
            saved = getattr(self.op, attr); setattr(self.op, attr, value)
            with self.assertRaises(Denied): self.invoke()
            setattr(self.op, attr, saved)
        with self.assertRaises(Denied):
            self.op.handle(['kandev', 'volume', 'inspect', 'another-volume'])
        self.model['volumes'][self.scope['logical']]['name'] = 'another-volume'
        with self.assertRaises(Denied): self.invoke()
        self.assertFalse(self.calls)

    def test_inactive_main_and_existing_consumers_are_denied(self):
        self.consumers = 'stopped-container\n'
        with self.assertRaises(Denied): self.invoke()
        self.assertFalse(any(call[1] == 'run' for call in self.calls))
        with sqlite3.connect(self.b.KANDEV_DB) as con:
            con.execute("UPDATE task_sessions SET state='COMPLETED'")
        self.calls.clear()
        with self.assertRaises(Denied): self.invoke()
        self.assertFalse(self.calls)

    def test_output_is_new_private_and_cannot_escape_or_overwrite(self):
        for output in ['../escape', '/tmp/out', '.tox/8241_recovery_20261030/other']:
            with self.assertRaises(Denied): self.invoke('preserve', output)
        directory = self.cwd/'.tox/8241_recovery_20261030/db-cold-unit'
        directory.mkdir()
        with self.assertRaises(Denied): self.invoke('preserve')
        directory.rmdir()
        directory.symlink_to(self.cwd, target_is_directory=True)
        with self.assertRaises(Denied): self.invoke('preserve')
        directory.unlink()
        result = self.invoke('preserve')
        self.assertEqual(result['returncode'], 0)
        self.assertEqual(directory.stat().st_mode & 0o777, 0o700)


class RegisteredDirectoryTests(unittest.TestCase):
    model_load = AuthorizationTests.model_load
    command = AuthorizationTests.command
    invoke = AuthorizationTests.invoke

    def setUp(self):
        AuthorizationTests.setUp(self)
        self.scope.update(repository_id='reviewed-repository', source_clone=str(Path(self.temp.name)/'original'),
                          model_directory='.', qualify_directory_on_owner_inspect=True,
                          recorded_engine='13.0.2-MariaDB-ubu2604')
        del self.scope['device'], self.scope['inode']
        (self.cwd/self.scope['output_parent']).chmod(0o700)
        common = Path(self.scope['source_clone']) / '.git'
        self.gitdir = common / 'worktrees/original-task'
        self.gitdir.mkdir(parents=True)
        (self.cwd/'.git').write_text('gitdir: '+str(self.gitdir)+'\n')
        (self.gitdir/'gitdir').write_text(str(self.cwd/'.git')+'\n')
        (self.gitdir/'commondir').write_text('../..\n')
        with sqlite3.connect(self.b.KANDEV_DB) as con:
            con.executescript('''ALTER TABLE tasks ADD COLUMN archived_at;
                CREATE TABLE task_repositories(task_id,repository_id);
                CREATE TABLE repositories(id,workspace_id,local_path,deleted_at);
                CREATE TABLE task_environment_repos(task_environment_id,repository_id,worktree_path,status,
                    deleted_at,worktree_source_clone_path,worktree_source_common_dir);''')
            con.execute('INSERT INTO task_repositories VALUES(?,?)', (self.scope['task'], self.scope['repository_id']))
            con.execute('INSERT INTO repositories VALUES(?,?,?,NULL)',
                        (self.scope['repository_id'], self.scope['workspace'], self.scope['source_clone']))
            con.execute('INSERT INTO task_environment_repos VALUES(?,?,?,?,NULL,?,?)',
                        ('environment', self.scope['repository_id'], str(self.cwd), 'active',
                         self.scope['source_clone'], str(common)))

    def pin(self):
        gate = operations.VolumePreservation(self.op)
        gate.owner(self.scope['volume'])
        return gate.pin_path()

    def test_preserve_cannot_qualify_and_only_inspect_establishes_private_pin(self):
        with self.assertRaisesRegex(Denied, 'run owner volume inspect'):
            self.invoke('preserve')
        self.assertFalse(self.calls)
        result = json.loads(self.invoke()['stdout'])
        self.assertTrue(result['original_registered_directory_verified'])
        self.assertTrue(result['source_directory_pin_established'])
        pin = self.pin()
        self.assertEqual(pin.stat().st_mode & 0o777, 0o600)
        self.assertEqual(pin.parent.stat().st_mode & 0o777, 0o700)
        helper = next(call for call in self.calls if call[1] == 'run')
        cfg = json.loads(helper[-1])
        self.assertTrue(cfg['qualify_directory'])
        self.assertNotIn('device', cfg)
        before = pin.read_bytes()
        self.calls.clear()
        self.assertEqual(self.invoke('preserve')['returncode'], 0)
        helper = next(call for call in self.calls if call[1] == 'run')
        cfg = json.loads(helper[-1])
        self.assertFalse(cfg['qualify_directory'])
        self.assertEqual((cfg['device'], cfg['inode']), (123, 456))
        self.assertEqual(before, pin.read_bytes())

    def test_wrong_task_clone_volume_repository_and_source_backlink_are_denied(self):
        for attr, value in [('root', self.root.parent), ('cwd', self.root)]:
            saved = getattr(self.op, attr); setattr(self.op, attr, value)
            with self.assertRaises(Denied): self.invoke()
            setattr(self.op, attr, saved)
        with self.assertRaises(Denied):
            self.op.handle(['kandev', 'volume', 'inspect', 'another-volume'])
        for sql, restore, value in [
                ("UPDATE repositories SET workspace_id='foreign'", 'UPDATE repositories SET workspace_id=?', self.scope['workspace']),
                ("UPDATE task_repositories SET repository_id='different'", 'UPDATE task_repositories SET repository_id=?', self.scope['repository_id']),
                ("UPDATE task_environment_repos SET worktree_path='/different'", 'UPDATE task_environment_repos SET worktree_path=?', str(self.cwd)),
                ("UPDATE tasks SET archived_at='archived'", 'UPDATE tasks SET archived_at=?', None)]:
            with sqlite3.connect(self.b.KANDEV_DB) as con:
                con.execute(sql)
            with self.assertRaises(Denied): self.invoke()
            with sqlite3.connect(self.b.KANDEV_DB) as con:
                con.execute(restore, (value,))
        backlink = self.gitdir/'gitdir'
        backlink.write_text('/different/.git\n')
        with self.assertRaises(Denied): self.invoke()
        self.assertFalse(self.calls)
        self.assertFalse((self.b.MODEL_DIR/'volume-preservation').exists())

    def test_absent_source_never_creates_a_volume_helper_or_pin(self):
        self.absent = True
        with self.assertRaisesRegex(Denied, 'absent; nothing was created'): self.invoke()
        self.assertEqual([call[1:3] for call in self.calls], [['volume', 'inspect']])
        self.assertFalse(self.pin().exists())

    def test_pin_is_not_replaced_on_new_inode_and_untrusted_pin_files_fail(self):
        self.invoke()
        pin = self.pin(); before = pin.read_bytes()
        self.fake_receipt['source']['inode'] += 1
        with self.assertRaisesRegex(Denied, 'differs from its established owner pin'): self.invoke()
        self.assertEqual(pin.read_bytes(), before)
        pin.chmod(0o644); self.calls.clear()
        with self.assertRaisesRegex(Denied, 'not broker-private'): self.invoke()
        self.assertFalse(self.calls)
        pin.unlink(); pin.symlink_to(self.cwd/'.git')
        with self.assertRaises(Denied): self.invoke()
        self.assertFalse(self.calls)

    def test_consumer_or_changed_engine_identity_cannot_establish_pin(self):
        self.consumers = 'stopped-container\n'
        with self.assertRaises(Denied): self.invoke()
        self.assertFalse(self.pin().exists())
        self.consumers = ''; self.info['CreatedAt'] = 'replacement'
        with self.assertRaises(Denied): self.invoke()
        self.assertFalse(self.pin().exists())
        self.assertFalse(any(call[1] == 'run' for call in self.calls))

    def test_preservation_parent_must_be_private(self):
        self.invoke()
        (self.cwd/self.scope['output_parent']).chmod(0o755)
        with self.assertRaisesRegex(Denied, 'parent must be owner-private'): self.invoke('preserve')
        self.assertFalse((self.cwd/self.scope['output_parent']/'db-cold-unit').exists())


class ArchiveTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        base = Path(self.temp.name)
        self.source = base/'source'; self.source.mkdir()
        self.output = base/'output'; self.output.mkdir()
        self.cfg = dict(mode='inspect', source=str(self.source), output=str(self.output),
                        device=self.source.stat().st_dev, inode=self.source.stat().st_ino,
                        output_device=self.output.stat().st_dev, output_inode=self.output.stat().st_ino,
                        uid=os.getuid(), gid=os.getgid())

    def run_helper(self, code=0):
        result = subprocess.run([sys.executable, '-c', operations.PRESERVATION_HELPER, json.dumps(self.cfg)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, code, result.stderr)
        return json.loads(result.stdout) if code == 0 else result

    def test_empty_wrong_inode_symlinks_and_hardlinks_fail_without_output(self):
        self.run_helper(78)
        (self.source/'ibdata1').write_bytes(b'opaque database fixture')
        self.cfg['inode'] += 1; self.run_helper(78); self.cfg['inode'] -= 1
        (self.source/'escape').symlink_to('/etc/passwd'); self.run_helper(78)
        (self.source/'escape').unlink()
        os.link(self.source/'ibdata1', self.source/'hardlink'); self.run_helper(78)
        self.assertFalse(list(self.output.iterdir()))

    def test_unreadable_nested_directory_is_never_silently_omitted(self):
        if os.geteuid() == 0: self.skipTest('root can traverse the permission fixture')
        (self.source/'ibdata1').write_bytes(b'fixture')
        private = self.source/'private'; private.mkdir(); private.chmod(0)
        try: self.run_helper(78)
        finally: private.chmod(0o700)

    def test_archive_inventory_bytes_and_hashes_are_verified_without_source_changes(self):
        (self.source/'ibdata1').write_bytes(b'opaque fixture\x00'*100)
        (self.source/'nested').mkdir()
        (self.source/'nested/data').write_bytes(bytes(range(256))*10)
        before = self.run_helper()
        self.cfg.update(mode='preserve', inventory_metadata_sha256=before['source']['inventory_metadata_sha256'])
        result = self.run_helper()
        self.assertTrue(result['verified'])
        self.assertEqual(result['verified_files'], 2)
        archive = self.output/'db_volume.tar'
        self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), result['archive_sha256'])
        inventory = json.loads((self.output/'inventory.json').read_bytes())
        with tarfile.open(archive) as tar:
            for row in inventory:
                if row['type'] == 'file':
                    self.assertEqual(tar.extractfile(row['path']).read(), (self.source/row['path']).read_bytes())
        self.assertEqual(result['source']['inventory_metadata_sha256'], result['source_after']['inventory_metadata_sha256'])
        for file in self.output.iterdir(): self.assertEqual(file.stat().st_mode & 0o777, 0o600)
        self.run_helper(78)  # A repeated call cannot overwrite the accepted archive.

    def test_changed_source_after_probe_is_rejected_before_archive_creation(self):
        (self.source/'ibdata1').write_bytes(b'fixture')
        before = self.run_helper()
        self.cfg.update(mode='preserve', inventory_metadata_sha256=before['source']['inventory_metadata_sha256'])
        (self.source/'ibdata1').write_bytes(b'changed fixture')
        self.run_helper(78)
        self.assertFalse(list(self.output.iterdir()))

    def test_kernel_readonly_and_destination_inode_checks(self):
        (self.source/'ibdata1').write_bytes(b'fixture')
        self.cfg['readonly_required'] = True
        self.run_helper(78)
        self.cfg['readonly_required'] = False
        before = self.run_helper()
        self.cfg.update(mode='preserve', inventory_metadata_sha256=before['source']['inventory_metadata_sha256'])
        self.cfg['output_inode'] += 1
        self.run_helper(78)
        self.assertFalse(list(self.output.iterdir()))

    def test_directory_qualification_is_readonly_inspect_only(self):
        (self.source/'ibdata1').write_bytes(b'opaque fixture')
        self.cfg['qualify_directory'] = True
        del self.cfg['device'], self.cfg['inode']
        result = self.run_helper()
        self.assertEqual(result['source']['inode'], self.source.stat().st_ino)
        self.cfg['mode'] = 'preserve'
        self.run_helper(78)
        self.assertFalse(list(self.output.iterdir()))
        self.cfg.update(mode='inspect', readonly_required=True)
        self.run_helper(78)


if __name__ == '__main__':
    unittest.main()
