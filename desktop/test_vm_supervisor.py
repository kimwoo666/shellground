"""Real process/pipe crash tests, without booting a VM or burning CPU."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

from vm_supervisor import create_session, Lease, process_identity, reap_abandoned_sessions, validate_session

ROOT = Path(__file__).resolve().parent


def wait_until(check, timeout=8):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if check():
            return
        time.sleep(.05)
    raise AssertionError('Timed out waiting for owned process cleanup')


def running(pid):
    # Child can briefly remain a zombie under the host's init/reaper.
    path = Path('/proc') / str(pid) / 'stat'
    try:
        data = path.read_text()
        return data[data.rfind(')') + 2:].split()[0] != 'Z'
    except (FileNotFoundError, ProcessLookupError):
        return False


@unittest.skipUnless(sys.platform == 'linux', 'Real Linux process lifetime checks')
class SupervisorTests(unittest.TestCase):
    def setUp(self):
        self.guards = []
        self.directories = []

    def tearDown(self):
        for guard in self.guards:
            if guard.stdin:
                guard.stdin.close()
            try:
                guard.wait(timeout=8)
            except subprocess.TimeoutExpired:
                guard.kill()
                guard.wait(timeout=3)
        for directory in self.directories:
            if directory.exists():
                shutil.rmtree(directory)

    def launch(self, ignore_term=False):
        directory, token = create_session()
        self.directories.append(directory)
        script = 'import time,signal; '
        if ignore_term:
            script += 'signal.signal(signal.SIGTERM, signal.SIG_IGN); '
        script += 'time.sleep(120)'
        guard = subprocess.Popen([sys.executable, str(ROOT / 'vm_supervisor.py'),
            '--session', str(directory), '--token', token, '--', sys.executable, '-c', script],
            stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.guards.append(guard)
        wait_until(lambda: (directory / 'guard.json').is_file() or guard.poll() is not None)
        self.assertIsNone(guard.poll())
        state = json.loads((directory / 'guard.json').read_text())
        return guard, directory, state['child_pid']

    def test_eof_removes_only_owned_child_and_directory(self):
        guard, directory, child = self.launch()
        other, other_directory, other_child = self.launch()
        guard.stdin.close()
        self.assertEqual(guard.wait(timeout=8), 0)
        wait_until(lambda: not running(child))
        self.assertFalse(directory.exists())
        self.assertIsNone(other.poll())
        self.assertTrue(other_directory.exists())
        self.assertTrue(running(other_child))

    def test_active_lease_and_unmarked_directory_are_not_reaped(self):
        guard, directory, child = self.launch()
        unmarked, _ = create_session()
        self.directories.append(unmarked)
        # Limit the scan to our test directories; never sweep other app state.
        with patch('vm_supervisor.Path.glob', return_value=[directory, unmarked]):
            self.assertEqual(reap_abandoned_sessions(), [])
        self.assertTrue(running(child))
        self.assertTrue(unmarked.exists())

    def test_killed_supervisor_cannot_leave_child_running_and_disk_recovers(self):
        guard, directory, child = self.launch()
        guard.kill()
        guard.wait(timeout=3)
        wait_until(lambda: not running(child))
        self.assertTrue(directory.exists())
        with patch('vm_supervisor.Path.glob', return_value=[directory]):
            self.assertEqual(reap_abandoned_sessions(), [str(directory)])
        self.assertFalse(directory.exists())

    def test_app_process_crash_closes_lifetime_pipe(self):
        code = '''
import json, subprocess, sys, time
from pathlib import Path
from vm_supervisor import create_session
directory, token = create_session()
guard = subprocess.Popen([sys.executable, 'vm_supervisor.py', '--session', str(directory),
    '--token', token, '--', sys.executable, '-c', 'import time; time.sleep(120)'],
    stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
deadline = time.monotonic() + 8
while not (directory / 'guard.json').exists():
    if guard.poll() is not None: raise RuntimeError('Guard exited')
    if time.monotonic() > deadline: raise RuntimeError('Guard startup timed out')
    time.sleep(.05)
print(json.dumps(dict(directory=str(directory), **json.loads((directory / 'guard.json').read_text()))), flush=True)
time.sleep(120)
'''
        app = subprocess.Popen([sys.executable, '-c', code], cwd=ROOT,
                               stdout=subprocess.PIPE, text=True)
        try:
            state = json.loads(app.stdout.readline())
            directory = Path(state['directory'])
            self.directories.append(directory)
            app.kill()  # a real abrupt app death, without calling engine.close()
            app.wait(timeout=3)
            wait_until(lambda: not running(state['child_pid']) and not directory.exists())
            wait_until(lambda: not running(state['guard_pid']))
        finally:
            if app.poll() is None:
                app.kill()
                app.wait(timeout=3)
            app.stdout.close()

    def test_uncooperative_child_has_bounded_shutdown(self):
        guard, directory, child = self.launch(ignore_term=True)
        time.sleep(.1)  # allow the child to install its signal handler
        started = time.monotonic()
        guard.stdin.close()
        self.assertEqual(guard.wait(timeout=8), 0)
        self.assertLess(time.monotonic() - started, 7)
        self.assertFalse(running(child))
        self.assertFalse(directory.exists())


class RecoverySafetyTests(unittest.TestCase):
    def setUp(self):
        self.directory, self.token = create_session()

    def tearDown(self):
        shutil.rmtree(self.directory, ignore_errors=True)

    def test_wrong_token_unknown_files_and_links_are_rejected(self):
        with self.assertRaises(ValueError):
            validate_session(self.directory, '0' * 32)
        unknown = self.directory / 'personal-note.txt'
        unknown.write_text('preserve')
        with self.assertRaises(ValueError):
            validate_session(self.directory, self.token)
        unknown.unlink()
        if os.name == 'posix':
            (self.directory / 'practice.qcow2').symlink_to('/etc/passwd')
            with self.assertRaises(ValueError):
                validate_session(self.directory, self.token)

    def test_forged_guard_token_does_not_authorize_disk_removal(self):
        lease = Lease(self.directory, create=True)
        lease.close()
        (self.directory / 'guard.json').write_text(json.dumps({'schema': 1, 'token': '0' * 32}))
        with patch('vm_supervisor.Path.glob', return_value=[self.directory]):
            self.assertEqual(reap_abandoned_sessions(), [])
        self.assertTrue(self.directory.exists())

    def test_creator_identity_includes_birth_time(self):
        identity = process_identity(os.getpid())
        self.assertEqual(identity['pid'], os.getpid())
        self.assertTrue(identity['start'])
        self.assertTrue(identity['boot'])

    @unittest.skipUnless(sys.platform == 'linux', 'Linux procfs termination race')
    def test_process_disappearing_during_proc_read_is_not_a_cleanup_error(self):
        from vm_crash_diagnostics import process_running
        with patch('pathlib.Path.read_text', side_effect=ProcessLookupError):
            self.assertIsNone(process_identity(12345))
            self.assertFalse(process_running(12345))

    def test_crash_before_supervisor_creation_is_recovered(self):
        output = subprocess.check_output([sys.executable, '-c',
            'from vm_supervisor import create_session; print(create_session()[0])'], cwd=ROOT, text=True, timeout=5)
        directory = Path(output.strip())
        try:
            with patch('vm_supervisor.Path.glob', return_value=[directory]):
                self.assertEqual(reap_abandoned_sessions(), [str(directory)])
            self.assertFalse(directory.exists())
        finally:
            shutil.rmtree(directory, ignore_errors=True)

    def test_unreadable_process_identity_never_authorizes_removal(self):
        with patch('vm_supervisor.Path.glob', return_value=[self.directory]), \
             patch('vm_supervisor.process_identity', side_effect=PermissionError):
            self.assertEqual(reap_abandoned_sessions(), [])
        self.assertTrue(self.directory.exists())


if __name__ == '__main__':
    unittest.main()
