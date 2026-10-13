#!/usr/bin/env python3
"""Synthetic reproduction of the caller's connect denial; no live socket."""
import errno
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts/kandev-agent-docker-client'
loader = importlib.machinery.SourceFileLoader('own_git_connect_client', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
client = importlib.util.module_from_spec(spec)
loader.exec_module(client)


class NoEnvironment:
    def get(self, *_):
        raise AssertionError('environment or credential read')


class ConnectDenied:
    attempts = 0
    def __enter__(self): return self
    def __exit__(self, *_): return False
    def settimeout(self, value): self.timeout = value
    def connect(self, endpoint):
        self.attempts += 1
        raise OSError(errno.EPERM, 'unreviewed-policy-details')
    def sendall(self, _): raise AssertionError('request sent after connect refusal')
    def recv(self, _): raise AssertionError('reply read after connect refusal')
    def shutdown(self, _): raise AssertionError('connection used after refusal')


class ConnectObservationTests(unittest.TestCase):
    def test_actual_client_matches_supplied_observation_without_transmission(self):
        output = []
        connection = ConnectDenied()
        with patch.object(client.socket, 'socket', return_value=connection) as create, \
             patch.object(client.os, 'environ', NoEnvironment()), \
             patch.object(client.sys, 'argv', ['docker', 'kandev', 'transport-probe']), \
             patch.object(client, 'write_all', lambda _, text: output.append(text)):
            code = client.main()
        self.assertEqual(code, 78)
        create.assert_called_once_with(client.socket.AF_UNIX, client.socket.SOCK_STREAM)
        self.assertEqual(connection.attempts, 1)
        self.assertEqual(connection.timeout, 3)
        self.assertEqual(json.loads(output[0]), {
            'authenticated_binding': 'UNKNOWN', 'credentials_accessed': False,
            'errno': 1, 'git_operations': 0, 'retries': 0, 'stage': 'connect',
            'status': 'UNKNOWN', 'version': 'broker-transport-observation/v1',
            'write_transport_accepted': False})
        self.assertNotIn('unreviewed-policy-details', output[0])


if __name__ == '__main__':
    unittest.main()
