#!/usr/bin/env python3
"""Regression tests for guarded Docker client terminal output draining."""

from __future__ import annotations

import errno
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import threading


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
    print("PASS: guarded Docker client drains nonblocking terminal output")


if __name__ == "__main__":
    main()
