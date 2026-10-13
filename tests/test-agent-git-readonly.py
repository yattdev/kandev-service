#!/usr/bin/env python3
"""Inert private-repository regression for late attachment acceptance reads."""
import hashlib
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    source = Path(__file__).resolve().parents[1] / 'scripts/kandev-agent-git'
    with tempfile.TemporaryDirectory(prefix='kandev-git-readonly-') as temporary:
        root = Path(temporary)
        task = root / 'task'
        repo = task / 'attached'
        repo.mkdir(parents=True)
        env = {'PATH': '/usr/bin:/bin', 'HOME': str(root), 'LC_ALL': 'C',
               'GIT_CONFIG_NOSYSTEM': '1', 'GIT_CONFIG_GLOBAL': '/dev/null'}
        subprocess.run(['/usr/bin/git', 'init', '-q', '-b', 'fixture'], cwd=repo, env=env, check=True)
        (repo / 'file').write_text('fixture\n')
        subprocess.run(['/usr/bin/git', 'add', 'file'], cwd=repo, env=env, check=True)
        subprocess.run(['/usr/bin/git', '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-qm', 'fixture'], cwd=repo, env=env, check=True)
        outside = root / 'outside'
        outside.mkdir()
        subprocess.run(['/usr/bin/git', 'init', '-q', '-b', 'outside'], cwd=outside, env=env, check=True)
        (outside / '.git').chmod(0o555)
        (task / 'escape').symlink_to(outside, target_is_directory=True)
        head = subprocess.check_output(['/usr/bin/git', 'rev-parse', 'HEAD'], cwd=repo, env=env).decode().strip()
        monitor_marker = root / 'monitor-called'
        monitor = root / 'monitor'
        monitor.write_text('#!/bin/sh\ntouch "' + str(monitor_marker) + '"\n')
        monitor.chmod(0o700)
        subprocess.run(['/usr/bin/git', 'config', 'core.fsmonitor', str(monitor)], cwd=repo, env=env, check=True)
        calls = root / 'broker-calls'
        broker = root / 'broker'
        broker.write_text('#!/bin/sh\nprintf "%s\\n" "$*" >> "' + str(calls) + '"\nexit 78\n')
        broker.chmod(0o700)
        wrapper = root / 'git-wrapper'
        # Substitute only the broker executable in the test copy; real Git and
        # production routing logic remain intact. No live socket/token is used.
        wrapper.write_text(source.read_text().replace('/usr/local/bin/kandev-agent-docker-client', str(broker)))
        wrapper.chmod(0o700)
        env.update(KANDEV_AGENT_GUARD_ACTIVE='1', KANDEV_AGENT_GUARD_SCOPE='project',
                   KANDEV_AGENT_DOCKER_TOKEN='synthetic-not-a-credential', KANDEV_AGENT_DOCKER_ROOT=str(task))
        metadata = repo / '.git'
        metadata.chmod(0o555)
        assert not os.access(metadata, os.W_OK), 'fixture metadata must be nonwritable'
        before = {str(p.relative_to(metadata)): hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in metadata.rglob('*') if p.is_file()}
        try:
            for args, expected in [(['status', '--porcelain'], ''), (['rev-parse', 'HEAD'], head),
                                   (['branch', '--show-current'], 'fixture'),
                                   (['-C', str(repo), 'rev-parse', '--abbrev-ref', 'HEAD'], 'fixture')]:
                result = subprocess.run([str(wrapper), *args], cwd=repo, env=env, text=True, capture_output=True)
                assert result.returncode == 0, (args, result.returncode, result.stderr)
                assert result.stdout.strip() == expected, (args, result.stdout)
            assert not calls.exists(), 'acceptance reads attempted the unavailable broker'
            assert not monitor_marker.exists(), 'status executed external fsmonitor'
            for args in [['add', 'file'], ['branch', 'new-owner'], ['update-ref', 'refs/heads/foreign', head],
                         ['branch', '--delete', 'fixture'], ['symbolic-ref', 'HEAD', 'refs/heads/foreign'],
                         ['rev-parse', '--parseopt'], ['rev-parse', '--verify HEAD'],
                         ['-c', 'core.fsmonitor=true', 'status'], ['--git-dir=' + str(metadata), 'status'],
                         ['-C', str(outside), 'status'], ['-C', str(task / 'escape'), 'status']]:
                result = subprocess.run([str(wrapper), *args], cwd=repo, env=env, text=True, capture_output=True)
                assert result.returncode == 78, (args, result.returncode, result.stderr)
            override = dict(env, GIT_DIR=str(metadata))
            assert subprocess.run([str(wrapper), 'status'], cwd=repo, env=override, capture_output=True).returncode == 78
            assert len(calls.read_text().splitlines()) == 12
            after = {str(p.relative_to(metadata)): hashlib.sha256(p.read_bytes()).hexdigest()
                     for p in metadata.rglob('*') if p.is_file()}
            assert before == after, 'read acceptance or denied mutation changed Git administration'
        finally:
            metadata.chmod(0o755)
            (outside / '.git').chmod(0o755)
    print('PASS: late-repository acceptance reads preserve administration and retain broker write fences')


if __name__ == '__main__':
    main()
