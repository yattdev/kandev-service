#!/usr/bin/env python3
"""Regression tests for guarded Docker client terminal output draining."""

from __future__ import annotations

import errno
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import struct
import threading
import json


CLIENT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "kandev-agent-docker-client"
loader = importlib.machinery.SourceFileLoader("kandev_agent_docker_client", str(CLIENT_PATH))
spec = importlib.util.spec_from_loader(loader.name, loader)
assert spec is not None
client = importlib.util.module_from_spec(spec)
loader.exec_module(client)


class FileDescriptor:
    def __init__(self, descriptor: int) -> None:
        self.descriptor = descriptor

    def fileno(self) -> int:
        return self.descriptor


def main() -> None:
    assert client.audit_receipt(
        {"audit_id": "11111111-1111-1111-1111-111111111111", "resolved_project": "kd_fixture"}
    ) == (
        "kandev-agent-docker: audit_id=11111111-1111-1111-1111-111111111111 "
        "resolved_project=kd_fixture\n"
    )
    assert client.audit_receipt({"audit_id": "missing-project"}) == ""

    # Simulate hook-sized output to a nonblocking terminal pipe.  The first
    # write is forced to EAGAIN and subsequent writes encounter ordinary pipe
    # backpressure while the reader drains; all bytes must arrive intact.
    read_fd, write_fd = os.pipe()
    os.set_blocking(write_fd, False)
    expected = (b"compose output line\n" * (2 * 1024 * 1024 // len("compose output line\n")))
    received = bytearray()
    start_reader = threading.Event()

    def reader() -> None:
        start_reader.wait(timeout=5)
        while len(received) < len(expected):
            chunk = os.read(read_fd, 65536)
            if not chunk:
                break
            received.extend(chunk)

    drain = threading.Thread(target=reader, daemon=True)
    drain.start()
    original_write = client.os.write
    first_write = True

    def eagain_once(descriptor: int, data: bytes) -> int:
        nonlocal first_write
        if first_write:
            first_write = False
            start_reader.set()
            raise BlockingIOError(errno.EAGAIN, "write would block")
        return original_write(descriptor, data)

    client.os.write = eagain_once
    try:
        client.write_all(FileDescriptor(write_fd), expected.decode("utf-8"))
    finally:
        client.os.write = original_write
        os.close(write_fd)
    drain.join(timeout=10)
    os.close(read_fd)
    assert not drain.is_alive(), "reader did not finish draining guarded output"
    assert bytes(received) == expected, "guarded client dropped or reordered output under backpressure"

    # Client stdin is framed and streamed, not JSON-encoded or buffered.  A
    # binary payload proves NUL bytes survive and the explicit EOF frame is
    # emitted after the final chunk.
    original_stdin = client.sys.stdin

    class BinaryInput:
        def __init__(self, data: bytes) -> None:
            self.buffer = self
            self.data = data
            self.offset = 0

        def isatty(self) -> bool:
            return False

        def read(self, size: int) -> bytes:
            chunk = self.data[self.offset : self.offset + size]
            self.offset += len(chunk)
            return chunk

    payload = (b"\x00stdin-fixture\xff" * 1024)
    class RecordingConnection:
        def __init__(self) -> None:
            self.data = bytearray()

        def sendall(self, data: bytes) -> None:
            self.data.extend(data)

    connection = RecordingConnection()
    client.sys.stdin = BinaryInput(payload)
    try:
        client.send_stdin(connection, True)
        framed = memoryview(connection.data)
        recovered = bytearray()
        offset = 0
        while True:
            length = struct.unpack("!I", framed[offset : offset + 4])[0]
            offset += 4
            if length == 0:
                break
            recovered.extend(framed[offset : offset + length])
            offset += length
    finally:
        client.sys.stdin = original_stdin
    assert bytes(recovered) == payload
    assert client.should_stream_stdin(["compose", "exec", "-T", "db", "mariadb"])
    assert not client.should_stream_stdin(["compose", "version"])
    assert not client.should_stream_stdin(["compose", "exec", "db", "mariadb"])
    assert client.should_stream_stdin(["compose", "-p", "qa", "exec", "-T", "db", "mariadb"])
    assert client.should_stream_stdin(["exec", "-i", "db", "mariadb"])
    assert not client.should_stream_stdin(["exec", "db", "cat", "-i"])
    assert client.should_stream_stdin(["kandev", "git", "apply", "-"])
    assert client.should_stream_stdin(["kandev", "git", "-C", "/task", "credential", "fill"])
    assert not client.should_stream_stdin(["kandev", "git", "status"])
    assert not client.should_stream_stdin(["kandev", "git", "status", "--", "credential"])

    # If the broker rejects an upload early, preserve its structured child
    # status and stderr instead of replacing them with a generic EPIPE.
    class EarlyResponseSocket:
        def __init__(self) -> None:
            self.sent = 0
            self.response = json.dumps({
                "returncode": 7, "stdout": "", "stderr": "fixture reader exited 7\n"
            }).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def connect(self, _path):
            pass

        def sendall(self, _data):
            self.sent += 1
            if self.sent > 1:
                raise BrokenPipeError(errno.EPIPE, "broker closed upload")

        def shutdown(self, _how):
            raise OSError(errno.ENOTCONN, "broker already closed")

        def recv(self, _size):
            response, self.response = self.response, b""
            return response

    original_socket = client.socket.socket
    original_write_all = client.write_all
    original_argv = client.sys.argv
    saved_environment = {
        key: os.environ.get(key)
        for key in ("KANDEV_AGENT_DOCKER_SOCKET", "KANDEV_AGENT_DOCKER_TOKEN", "KANDEV_AGENT_DOCKER_ROOT")
    }
    writes = []
    try:
        client.socket.socket = lambda *_args, **_kwargs: EarlyResponseSocket()
        client.write_all = lambda stream, output: writes.append((stream, output))
        client.sys.stdin = BinaryInput(b"\x00" * (2 * 1024 * 1024))
        client.sys.argv = ["docker", "compose", "exec", "-T", "sink", "cat"]
        os.environ.update({
            "KANDEV_AGENT_DOCKER_SOCKET": "/tmp/proof.sock",
            "KANDEV_AGENT_DOCKER_TOKEN": "proof",
            "KANDEV_AGENT_DOCKER_ROOT": "/tmp/proof-task",
        })
        assert client.main() == 7
        assert any("fixture reader exited 7" in output for _stream, output in writes)
    finally:
        client.socket.socket = original_socket
        client.write_all = original_write_all
        client.sys.stdin = original_stdin
        client.sys.argv = original_argv
        for key, value in saved_environment.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
    print("PASS: guarded Docker client drains nonblocking terminal output")


if __name__ == "__main__":
    main()
