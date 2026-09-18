"""Bounded POSIX build checks with durable output and owned process cleanup.

Used inside the marked developer guest, never to run learner code on the host.
The small lifecycle tests use only disposable Python children. Commands cannot
opt out of the new session; timeouts terminate that session's process group.
"""
import json
import os
from pathlib import Path
import signal
import subprocess
import time


def read_tail(path, limit=16384):
    with Path(path).open('rb') as stream:
        stream.seek(0, os.SEEK_END)
        stream.seek(max(0, stream.tell()-limit))
        return stream.read(limit).decode('utf-8', errors='replace')


def _stop_owned(process, grace):
    # Do not reap the session leader during the grace period: its PID keeps
    # the process-group identity reserved even if it exits before its children.
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        pass
    time.sleep(grace)
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        pass
    process.wait(timeout=5)


def run_logged(argv, output, *, timeout, grace=3, env=None, identity=None):
    """Return command evidence; a zero exit alone is not a curriculum proof.

    output must be a fresh file in a caller-owned directory. Its sibling JSON
    file records even timeouts/cancellation. Old runs are never overwritten.
    identity optionally supplies guest-only (uid, gid) without a runuser child
    whose session semantics could detach the actual checker from our group.
    """
    if os.name != 'posix':
        raise RuntimeError('This supervisor is for the real Linux guest only')
    if timeout <= 0 or not 0 <= grace <= 10:
        raise ValueError('A positive deadline and bounded cleanup are required')
    output = Path(output)
    metadata = output.with_suffix(output.suffix+'.json')
    options = {}
    if identity is not None:
        uid, gid = identity
        options = dict(user=uid, group=gid, extra_groups=[gid])
    started = time.monotonic()
    evidence = {'schema': 1, 'kind': 'owned-command-observation', 'argv': list(argv),
                'timeout_seconds': timeout, 'status': 'starting', 'returncode': None}
    process = None
    # Exclusive creation also rejects dangling symlinks. Keep a successfully
    # created diagnostic file if another path fails; never overwrite evidence.
    with metadata.open('x', encoding='utf-8') as record, output.open('xb') as stream:
        def save():
            evidence['elapsed_seconds'] = round(time.monotonic()-started, 3)
            record.seek(0);json.dump(evidence, record, indent=2);record.truncate()
            record.flush();os.fsync(record.fileno())
        save()
        try:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL,
                stdout=stream, stderr=subprocess.STDOUT, start_new_session=True,
                env=env, **options)
            evidence.update(status='running', pid=process.pid)
            save()
            try:
                code = process.wait(timeout=timeout)
                evidence.update(status='passed' if code == 0 else 'failed', returncode=code)
            except subprocess.TimeoutExpired:
                evidence['status'] = 'timeout'
                _stop_owned(process, grace)
                evidence['returncode'] = process.returncode
        except BaseException:
            evidence['status'] = 'interrupted' if process is not None else 'start-failed'
            if process is not None:
                _stop_owned(process, grace)
                evidence['returncode'] = process.returncode
            raise
        finally:
            stream.flush();os.fsync(stream.fileno())
            save()
    evidence['tail'] = read_tail(output)
    return evidence
