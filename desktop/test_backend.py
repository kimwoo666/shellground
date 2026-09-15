"""Read-only backend policy tests; no Windows services/settings are modified."""
import json
import unittest
from unittest.mock import patch
from engine import LabEngine, LabError, validate_backend


class BackendTests(unittest.TestCase):
    def test_linux_and_windows_linuxkit(self):
        validate_backend({'OSType': 'linux', 'KernelVersion': '6.8.0-generic'}, 'linux')
        validate_backend({'OSType': 'linux', 'KernelVersion': '6.10.14-linuxkit'}, 'win32')

    def test_wsl_unknown_and_windows_containers_rejected(self):
        for kernel in ['5.15.167.4-microsoft-standard-WSL2', 'WSL2-linuxkit', '', None, '6.8.0-generic']:
            with self.subTest(kernel=kernel), self.assertRaises(LabError):
                validate_backend({'OSType': 'linux', 'KernelVersion': kernel}, 'win32')
        with self.assertRaises(LabError): validate_backend({'OSType': 'windows'}, 'win32')

    def test_wsl_cannot_build_or_start(self):
        info = json.dumps({'OSType': 'linux', 'KernelVersion': 'microsoft-standard-WSL2'})
        for operation in ['status', 'build', 'start']:
            engine = LabEngine()
            with patch('engine.sys.platform', 'win32'), patch.object(engine, 'command', return_value=info) as command, patch('engine.subprocess.Popen') as popen:
                with self.assertRaisesRegex(LabError, 'WSL 기반'):
                    getattr(engine, operation)(None) if operation == 'start' else getattr(engine, operation)()
                self.assertEqual(command.call_count, 1)
                self.assertEqual(command.call_args.args[:1], ('info',))
                popen.assert_not_called()

    def test_bad_info_fails_closed(self):
        for value in ['not json', 'null', '[]']:
            with patch.object(LabEngine, 'command', return_value=value), self.assertRaises(LabError):
                LabEngine().status()


if __name__ == '__main__': unittest.main()
