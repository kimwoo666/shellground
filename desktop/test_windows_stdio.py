"""Portable contracts only. The frozen Windows probe is a separate gate."""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

import stdio_transport as io
import windows_pipe_diagnostics as diagnostic


class WindowsStdioTests(unittest.TestCase):
    def fixture(self):
        kernel = Mock(); kernel.GetCurrentProcess.return_value = 1
        kernel.GetStdHandle.side_effect = [100, 101, 101]  # stdout/stderr intentionally share a handle
        calls = []
        def duplicate(source, handle, target, result, access, inherit, flags):
            calls.append(('duplicate', handle))
            ctypes.cast(result, ctypes.POINTER(ctypes.c_void_p)).contents.value = 200 + len(calls)
            return 1
        kernel.DuplicateHandle.side_effect = duplicate
        os_api = SimpleNamespace(O_RDONLY=0, O_WRONLY=1, O_BINARY=32768,
                                 dup2=Mock(side_effect=lambda *a, **k: calls.append(('dup2', a))), close=Mock())
        crt = SimpleNamespace(open_osfhandle=Mock(side_effect=[9, 10, 11]))
        return kernel, calls, os_api, crt

    def test_duplicates_all_handles_before_binding_expected_descriptors(self):
        kernel, calls, os_api, crt = self.fixture()
        with patch('windows_vm.system_dll', return_value=kernel), patch('stdio_transport.os', os_api), patch.dict('sys.modules', msvcrt=crt):
            io._restore_windows_descriptors([('stdin', 0, 'r'), ('stdout', 1, 'w'), ('stderr', 2, 'w')])
        self.assertEqual(calls[:3], [('duplicate', 100), ('duplicate', 101), ('duplicate', 101)])
        self.assertEqual([call.args for call in os_api.dup2.call_args_list], [(9, 0), (10, 1), (11, 2)])
        self.assertTrue(all(call.kwargs == {'inheritable': False} for call in os_api.dup2.call_args_list))
        self.assertEqual([call.args for call in os_api.close.call_args_list], [(9,), (10,), (11,)])
        kernel.CloseHandle.assert_not_called()  # CRT owns duplicates; originals remain borrowed

    def test_capture_failure_closes_only_already_duplicated_handles(self):
        kernel, _, os_api, crt = self.fixture(); kernel.GetStdHandle.side_effect = [100, 0]
        with patch('windows_vm.system_dll', return_value=kernel), patch('stdio_transport.os', os_api), patch.dict('sys.modules', msvcrt=crt):
            with self.assertRaisesRegex(RuntimeError, 'pipe: 1'):
                io._restore_windows_descriptors([('stdin', 0, 'r'), ('stdout', 1, 'w')])
        kernel.CloseHandle.assert_called_once_with(201); crt.open_osfhandle.assert_not_called()

    def test_crt_failure_does_not_leak_pending_duplicates(self):
        kernel, _, os_api, crt = self.fixture(); crt.open_osfhandle.side_effect = OSError('CRT failure')
        with patch('windows_vm.system_dll', return_value=kernel), patch('stdio_transport.os', os_api), patch.dict('sys.modules', msvcrt=crt):
            with self.assertRaises(OSError): io._restore_windows_descriptors([('stdin', 0, 'r'), ('stdout', 1, 'w')])
        self.assertEqual([c.args for c in kernel.CloseHandle.call_args_list], [(201,), (202,)])
        os_api.close.assert_not_called()

    def test_restore_wraps_actual_standard_fds_in_utf8_without_owning_them(self):
        streams = SimpleNamespace(stdin=None, stdout=None, stderr=None)
        with (patch('stdio_transport.sys', streams), patch('stdio_transport.os', SimpleNamespace(name='nt')),
              patch('stdio_transport._restore_windows_descriptors') as restore,
              patch('stdio_transport.open', create=True) as opening):
            io.restore_worker_pipes()
            self.assertEqual(restore.call_args.args[0], [('stdin', 0, 'r'), ('stdout', 1, 'w'), ('stderr', 2, 'w')])
            self.assertEqual([c.args for c in opening.call_args_list], [(0, 'r'), (1, 'w'), (2, 'w')])
            self.assertTrue(all(c.kwargs == dict(encoding='utf-8', buffering=1, closefd=False) for c in opening.call_args_list))

    def test_only_windows_internal_and_selftest_entries_restore_gui_pipes(self):
        for system, flag, expected in [('win32', '--internal-vm-supervisor', True),
                                      ('win32', '--self-test-release', True), ('win32', '', False),
                                      ('linux', '--internal-vm-supervisor', False)]:
            with patch('stdio_transport.sys', SimpleNamespace(platform=system)), patch('stdio_transport.restore_worker_pipes') as restore:
                io.prepare_internal_stdio(flag)
                self.assertEqual(restore.called, expected)

    def test_native_report_is_never_created_on_a_non_windows_builder(self):
        with tempfile.TemporaryDirectory() as folder, patch('windows_pipe_diagnostics.sys.platform', 'linux'):
            report = Path(folder) / 'native.json'
            with self.assertRaisesRegex(RuntimeError, 'actual frozen Windows'): diagnostic.main(['--report', str(report)])
            self.assertFalse(report.exists())

    def test_native_probe_result_requires_all_observations(self):
        valid = dict(echo=diagnostic.PAYLOAD, eof=True, cpu_flags=5, cpu_rate=750, logical_cpus=8, utf8_mode=1, kill_on_close=True,
                     cpu_seconds=1.7, wall_seconds=3.1, iterations=100)
        complete = lambda value: subprocess.CompletedProcess([], 0, json.dumps(value), diagnostic.ERROR_MARKER)
        self.assertEqual(diagnostic.validate_probe(complete(valid)), valid)
        for change in ({'echo': 'broken'}, {'eof': False}, {'kill_on_close': False}, {'cpu_flags': 1},
                       {'cpu_seconds': 2.9}, {'wall_seconds': 0}, {'iterations': 0}, {'cpu_rate': 6000}, {'logical_cpus': 0}, {'utf8_mode': 0}):
            with self.assertRaises(RuntimeError): diagnostic.validate_probe(complete(dict(valid, **change)))

    def test_windows_build_adds_native_pipe_check_without_regrading_old_courses(self):
        from build_verification import verification_commands
        windows = verification_commands('app.exe', 'out', 'runtime', 'python', system='win32')
        linux = verification_commands('app', 'out', 'runtime', 'python', system='linux')
        self.assertEqual(windows[0][1], '--self-test-windows-pipes')
        self.assertEqual([c[1] for c in windows[1:]], [c[1] for c in linux])
        self.assertNotIn('--self-test-real', repr(windows))


if __name__ == '__main__': unittest.main()
