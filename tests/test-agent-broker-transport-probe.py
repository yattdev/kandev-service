#!/usr/bin/env python3
"""Credential-free, no-Git transport diagnostics using synthetic sockets only."""
import errno
import importlib.machinery
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

path = Path(__file__).resolve().parents[1] / 'scripts/kandev-agent-docker-client'
loader = importlib.machinery.SourceFileLoader('transport_probe_client', str(path))
spec = importlib.util.spec_from_loader(loader.name, loader)
client = importlib.util.module_from_spec(spec)
loader.exec_module(client)

broker_path = path.parent / 'kandev-agent-docker-broker'
broker_loader = importlib.machinery.SourceFileLoader('transport_probe_broker', str(broker_path))
broker_spec = importlib.util.spec_from_loader(broker_loader.name, broker_loader)
broker = importlib.util.module_from_spec(broker_spec)
broker_loader.exec_module(broker)


class NoEnvironment:
    def get(self, *_args):
        raise AssertionError('probe accessed environment/credentials')


class FixtureSocket:
    def __init__(self, failure=None, response=None):
        self.failure = failure
        self.response = response or json.dumps({'returncode': 78, 'stdout': '',
            'stderr': 'kandev-agent-docker: missing task scope\n'}).encode()
        self.sent = []
        self.path = None
        self.deadline = None

    def __enter__(self): return self
    def __exit__(self, *_args): return False
    def settimeout(self, value): self.deadline = value
    def connect(self, path):
        self.path = path
        if self.failure == 'connect': raise OSError(errno.EPERM, 'secret-path-not-for-output')
    def sendall(self, data):
        if self.failure == 'send': raise OSError(errno.EPIPE, 'secret-token-not-for-output')
        self.sent.append(data)
    def shutdown(self, _how): pass
    def recv(self, size):
        if self.failure == 'receive': raise TimeoutError('secret-header-not-for-output')
        result, self.response = self.response[:size], self.response[size:]
        return result


class TransportProbeTests(unittest.TestCase):
    def run_probe(self, socket_factory, args=None):
        output = []
        with patch.object(client.socket, 'socket', socket_factory), \
             patch.object(client.sys, 'argv', ['docker', 'kandev', 'transport-probe', *(args or [])]), \
             patch.object(client.os, 'environ', NoEnvironment()), \
             patch.object(client, 'write_all', lambda _stream, text: output.append(text)):
            code = client.main()
        self.assertEqual(len(output), 1)
        result = json.loads(output[0])
        self.assertFalse(result['write_transport_accepted'])
        self.assertEqual(result['authenticated_binding'], 'UNKNOWN')
        self.assertNotIn('secret', output[0])
        return code, result

    def test_socket_create_refusal_is_classified_without_secret_text(self):
        def denied(*_args): raise OSError(errno.EPERM, 'secret-token')
        code, result = self.run_probe(denied)
        self.assertEqual(code, 78)
        self.assertEqual(result['stage'], 'socket_create')
        self.assertEqual(result['errno'], errno.EPERM)

    def test_connect_refusal_is_distinct(self):
        sock = FixtureSocket('connect')
        code, result = self.run_probe(lambda *_args: sock)
        self.assertEqual((code, result['stage'], result['errno']), (78, 'connect', errno.EPERM))
        self.assertEqual(sock.sent, [])

    def test_anonymous_denial_proves_only_protocol_reachability(self):
        sock = FixtureSocket()
        code, result = self.run_probe(lambda *_args: sock)
        self.assertEqual(code, 0)
        self.assertEqual(result['status'], 'anonymous_protocol_reachable')
        self.assertEqual(sock.sent, [b'{}\n', b'\x00\x00\x00\x00'])
        self.assertEqual(sock.path, '/run/kandev-agent-docker.sock')
        self.assertEqual(sock.deadline, 3)

    def test_send_and_timeout_remain_unknown(self):
        for failure in ('send', 'receive'):
            with self.subTest(failure=failure):
                code, result = self.run_probe(lambda *_args: FixtureSocket(failure))
                self.assertEqual(code, 78)
                self.assertEqual(result['stage'], failure)

    def test_unexpected_success_or_malformed_or_large_reply_is_not_acceptance(self):
        for response in (b'{"returncode":0}', b'not-json', b'x' * 4097):
            with self.subTest(response=response[:20]):
                code, result = self.run_probe(lambda *_args: FixtureSocket(response=response))
                self.assertEqual(code, 78)
                self.assertEqual(result['stage'], 'reply')

    def test_probe_rejects_all_target_overrides_before_io(self):
        for args in (['--task', 'foreign'], ['--socket', '/foreign'], ['--pid', '1']):
            with self.subTest(args=args):
                code, result = self.run_probe(lambda *_args: self.fail('socket accessed'), args)
                self.assertEqual(code, 64)
                self.assertEqual(result['stage'], 'arguments')

    def test_existing_task_hmac_does_not_sign_session_or_generation(self):
        # Pure existing signing function with synthetic key/path. No real key,
        # process, connection, request or task resource is read or created.
        key = b'synthetic-test-only'
        root = Path('/synthetic/owned-task')
        contexts = [{'session': 'source', 'incarnation': 'old', 'generation': 1},
                    {'session': 'sibling', 'incarnation': 'replacement', 'generation': 2}]
        tokens = [broker.expected_token(key, root) for _context in contexts]
        self.assertEqual(tokens[0], tokens[1])

    def test_existing_hmac_still_distinguishes_task_roots(self):
        key = b'synthetic-test-only'
        self.assertNotEqual(broker.expected_token(key, Path('/synthetic/owned-task')),
                            broker.expected_token(key, Path('/synthetic/foreign-task')))


if __name__ == '__main__':
    unittest.main()
