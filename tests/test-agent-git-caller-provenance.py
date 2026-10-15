#!/usr/bin/env python3
"""Static broker integration checks with no real guard or Git invocation."""
import importlib.machinery
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts/kandev-agent-docker-broker'
loader = importlib.machinery.SourceFileLoader('git_caller_provenance_broker', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
broker = importlib.util.module_from_spec(spec)
loader.exec_module(broker)


class CallerProvenanceTests(unittest.TestCase):
    def test_claimed_identity_is_not_a_trusted_guard_execution_binding(self):
        request = {'session_id': 'claimed-source', 'incarnation': 'claimed-inc',
                   'environment_id': 'claimed-env', 'generation': 1,
                   'git_environment': {}}
        with patch.object(broker, 'run_command', return_value=(0, '', '')) as run:
            result = broker.handle_git(Path('/synthetic/task'),
                                       Path('/synthetic/task/repo'),
                                       ['status'], request, None)
        self.assertEqual(result, {'returncode': 0, 'stdout': '', 'stderr': ''})
        argv, cwd = run.call_args.args
        self.assertEqual(argv, [broker.GUARD_BIN, '--', '/usr/bin/git', 'status'])
        self.assertEqual(cwd, Path('/synthetic/task/repo'))
        self.assertEqual(run.call_args.kwargs['environment_overrides'], {})
        self.assertNotIn('authenticated_binding', result)

    def test_git_environment_cannot_inject_caller_identity(self):
        for key in ('KANDEV_TASK_ID', 'KANDEV_SESSION_ID', 'KANDEV_WORKSPACE_ID',
                    'QUEUE_INCARNATION_ID', 'ENVIRONMENT_GENERATION'):
            with self.subTest(key=key), patch.object(
                    broker, 'run_command', side_effect=AssertionError('guard launched')):
                with self.assertRaisesRegex(broker.BrokerError, '^invalid Git environment$'):
                    broker.handle_git(Path('/synthetic/task'),
                                      Path('/synthetic/task/repo'), ['status'],
                                      {'git_environment': {key: 'claimed-identity'}}, None)


if __name__ == '__main__':
    unittest.main()
