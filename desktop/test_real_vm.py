"""Private VM transport and cleanup regression tests (no VM required)."""
import base64
import json
import io
from pathlib import Path
import socket
import subprocess
import tempfile
import threading
import types
import unittest
from unittest.mock import Mock, patch

from engine import LabError
from real_vm import GuestChannel, RealEngine, TerminalProcess, runtime_info


class RealRuntimeTests(unittest.TestCase):
    def test_latest_grading_sources_are_shipped_only_to_owned_guest(self):
        engine=RealEngine();engine.channel=Mock()
        engine.channel.request.return_value={'code':0,'err':''}
        engine.configure_grader()
        engine.channel.request.assert_called_once()
        options=engine.channel.request.call_args.kwargs
        files=json.loads(base64.b64decode(options['input']))
        self.assertEqual(list(files),
                         ['lab.py','ros_lab.py','ros_controls_lab.py','ros_observer.py','apt_lab.py','auth_lab.py','shell_lab.py','process_lab.py','io_lab.py','system_lab.py','docker_lab.py','docker_sessions_lab.py','docker_runtime_lab.py','shell_snapshot.py'])
        self.assertTrue(options['root'])
        self.assertIn('require_guest()',options['argv'][-1])
        for name, data in files.items():
            compile(base64.b64decode(data), name, 'exec')

    def test_invalid_bundle_is_rejected_before_any_guest_file_is_written(self):
        engine=RealEngine(); engine.channel=Mock()
        engine.channel.request.return_value={'code':0,'err':''}
        engine.configure_grader()
        options=engine.channel.request.call_args.kwargs
        original=json.loads(base64.b64decode(options['input']))
        unexpected=dict(original, **{'../escape.py': base64.b64encode(b'pass').decode()})
        broken=dict(original, **{'shell_snapshot.py': base64.b64encode(b'def :').decode()})
        for files, error in ((unexpected, ValueError), (broken, SyntaxError)):
            guest=types.ModuleType('agent'); guest.require_guest=Mock()
            with patch.dict('sys.modules', {'agent': guest}), patch('sys.stdin', io.StringIO(json.dumps(files))), \
                 patch('pathlib.Path.write_bytes') as write, patch('sys.path', []):
                with self.assertRaises(error): exec(options['argv'][-1], {})
                guest.require_guest.assert_called_once()
                write.assert_not_called()

    def test_grader_installation_error_is_reported(self):
        engine=RealEngine(); engine.channel=Mock()
        engine.channel.request.return_value={'code':1,'err':base64.b64encode(b'write failed').decode()}
        with self.assertRaisesRegex(LabError, 'write failed'): engine.configure_grader()

    def test_shell_configuration_is_guest_scoped_and_packaged(self):
        engine = RealEngine()
        engine.channel = Mock()
        engine.channel.request.return_value = {'code': 0, 'err': ''}
        engine.configure_shell()
        args, options = engine.channel.request.call_args
        self.assertEqual(args, ('exec',))
        self.assertTrue(options['root'])
        self.assertIn('require_guest()', options['argv'][-1])
        self.assertIn("Path('/opt/shellground/bashrc')", options['argv'][-1])
        self.assertEqual(base64.b64decode(options['input']),
                         Path(__file__).with_name('guest').joinpath('bashrc').read_bytes())

    def test_shell_configuration_failure_is_not_silently_ignored(self):
        engine = RealEngine()
        engine.channel = Mock()
        engine.channel.request.return_value = {'code': 1, 'err': base64.b64encode(b'not guest').decode()}
        with self.assertRaisesRegex(LabError, 'not guest'):
            engine.configure_shell()

    def test_supervised_close_releases_pipe_before_wait_without_signalling_pids(self):
        engine = RealEngine()
        engine.supervised = True
        engine.process = process = Mock()
        process.poll.return_value = None
        engine.close()
        process.stdin.close.assert_called()
        process.wait.assert_called_once_with(timeout=7)
        process.terminate.assert_not_called()
        process.kill.assert_not_called()

    def test_closed_transport_is_cleaned_before_reboot(self):
        engine = RealEngine()
        engine.process = Mock()
        engine.close = Mock()
        with patch('real_vm.runtime_info', side_effect=LabError('missing pack')):
            with self.assertRaises(LabError):
                engine.boot()
        engine.close.assert_called_once()

    def test_old_runtime_is_not_treated_as_supporting_new_lessons(self):
        from missions import make_mission
        engine = RealEngine()
        engine.boot = Mock()
        engine.channel = Mock()
        with self.assertRaises(LabError):
            engine.start(make_mission('sim_images', 1234))
        engine.channel.request.assert_not_called()

    def test_missing_bundle_is_not_a_host_shell_fallback(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(LabError):
                runtime_info(directory)
            with patch('real_vm.subprocess.Popen') as popen:
                with self.assertRaises(LabError):
                    RealEngine(directory).boot()
                popen.assert_not_called()

    def test_manifest_cannot_escape_bundle(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'runtime.json').write_text(json.dumps({'protocol': 1, 'provisioned': True,
                 'qemu': '/usr/bin/bash', 'qemu_img': '/usr/bin/bash', 'image': '/etc/passwd'}))
            with self.assertRaises(LabError):
                runtime_info(root)

    def test_close_kills_only_owned_process_and_removes_only_own_overlay(self):
        engine = RealEngine()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            base = root / 'base.qcow2'
            base.write_bytes(b'keep immutable base')
            owned = root / 'session'
            owned.mkdir()
            (owned / 'overlay.qcow2').write_bytes(b'temporary')
            engine.session_dir = owned
            process = Mock()
            process.poll.return_value = None
            process.wait.side_effect = [subprocess.TimeoutExpired('qemu', 3), 0]
            engine.process = process
            engine.close()
            process.terminate.assert_called_once()
            process.kill.assert_called_once()
            self.assertFalse(owned.exists())
            self.assertEqual(base.read_bytes(), b'keep immutable base')
            engine.close()
            process.kill.assert_called_once()

    def test_terminal_buffer_is_bounded_and_can_always_close(self):
        terminal = TerminalProcess('1')
        for _ in range(200):
            terminal.emit(base64.b64encode(b'hello').decode())
        self.assertLessEqual(terminal.queue.qsize(), 128)
        terminal.close()
        list(terminal)
        self.assertEqual(terminal.poll(), 0)

    def test_channel_routes_output_to_independent_terminals(self):
        # Some sandbox profiles prohibit local sockets. Run this test on the
        # unrestricted development host; never interpret a skip as verification.
        try:
            host, guest = socket.socketpair()
        except OSError as exc:
            self.skipTest(str(exc))
        channel = GuestChannel(host)
        def server():
            stream = guest.makefile('rb')
            for _ in range(2):
                request = json.loads(stream.readline())
                sid = str(request['id'])
                # Output may arrive before the open reply is delivered.
                guest.sendall((json.dumps({'session': sid, 'output': base64.b64encode(sid.encode()).decode()}) + '\n').encode())
                guest.sendall((json.dumps({'id': request['id'], 'result': {'session': sid}}) + '\n').encode())
            stream.close()
        worker = threading.Thread(target=server, daemon=True)
        worker.start()
        try:
            first = channel.open_terminal('/home/learner')
            second = channel.open_terminal('/home/learner')
            self.assertNotEqual(first.sid, second.sid)
            self.assertEqual(base64.b64decode(json.loads(next(first))['output']), b'1')
            self.assertEqual(base64.b64decode(json.loads(next(second))['output']), b'2')
        finally:
            channel.close()
            guest.shutdown(socket.SHUT_RDWR)
            guest.close()
            worker.join(2)


if __name__ == '__main__':
    unittest.main()
