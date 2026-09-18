"""Changed launch/control-flow contracts, no old course or VM is executed."""
import os
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch
from contextlib import ExitStack

from engine import LabError
from real_vm import RealEngine


class WindowsBootContractTests(unittest.TestCase):
    def boot_fixture(self, stack, case='ready'):
        temporary = Path(stack.enter_context(tempfile.TemporaryDirectory()))
        root = temporary / '런타임, 폴더'; root.mkdir()
        session = temporary / '실습, 진행'; session.mkdir()
        spec = dict(qemu='qemu/qemu-system-x86_64.exe', qemu_img='qemu/qemu-img.exe',
                    image='base.qcow2', firmware='qemu/share', bios='qemu/share/bios-256k.bin')
        (root / 'qemu/share').mkdir(parents=True)
        (root / spec['bios']).write_bytes(b'test-bios')
        (root / 'qemu/share/kvmvapic.bin').write_bytes(b'test-vapic')
        engine = RealEngine(root)
        process = Mock(); process.poll.return_value = None
        listener = Mock(); listener.accept.return_value = (Mock(), ('127.0.0.1', 10))
        listener.getsockname.return_value = ('127.0.0.1', 32123)
        channel = Mock(); channel.request.return_value = {'protocol': 1, 'provisioned': True}
        for name, value in (
            ('os', SimpleNamespace(name='nt', environ=os.environ)),
            ('runtime_info', Mock(return_value=(root, spec))),
            ('accelerator_args', Mock(return_value=['-accel', 'tcg,thread=multi', '-cpu', 'max'])),
            ('reap_abandoned_sessions', Mock(return_value=[])),
            ('create_session', Mock(return_value=(session, 'a' * 32))),
            ('vm_process_options', Mock(return_value={})), ('lower_priority', Mock()),
            ('GuestChannel', Mock(return_value=channel))):
            stack.enter_context(patch('real_vm.' + name, value))
        stack.enter_context(patch('real_vm.socket.socket', return_value=listener))
        run = stack.enter_context(patch('real_vm.subprocess.run'))
        def launch(*args, **kwargs):
            if case == 'failed':
                process.poll.return_value = 1
                kwargs['stdout'].write(b'CPU limit failed: denied'); kwargs['stdout'].flush()
            elif case == 'cancelled': engine.cancelled.set()
            return process
        popen = stack.enter_context(patch('real_vm.subprocess.Popen', side_effect=launch))
        engine.configure_shell = Mock(); engine.configure_grader = Mock()
        return engine, root, session, run, popen, process, listener

    def test_windows_argv_log_and_successful_control_channel(self):
        with ExitStack() as stack:
            engine, root, session, run, popen, process, listener = self.boot_fixture(stack)
            lines = []
            try:
                engine.boot(lines.append)
                argv = popen.call_args.args[0]
                self.assertEqual(argv[argv.index('-L') + 1], '.')
                self.assertEqual(argv[argv.index('-bios') + 1], 'qemu-bios.bin')
                self.assertEqual(popen.call_args.kwargs['cwd'], root)
                self.assertIn('file=practice.qcow2,format=qcow2,if=virtio', argv)
                self.assertIn('file:console.log', argv)
                self.assertEqual((session / 'qemu-bios.bin').read_bytes(), b'test-bios')
                self.assertEqual((session / 'kvmvapic.bin').read_bytes(), b'test-vapic')
                self.assertNotIn('--library-dir', argv)
                self.assertIn('socket,id=sg,host=127.0.0.1,port=32123,reconnect-ms=1000', argv)
                self.assertEqual(run.call_args.args[0][-1], str(session / 'practice.qcow2'))
                self.assertIn('소프트웨어 실행', lines[-1])
                self.assertFalse((session / 'qemu.log').exists())
                engine.configure_shell.assert_called_once(); engine.configure_grader.assert_called_once()
                listener.close.assert_called()  # socket close is idempotent
            finally: engine.close()
            self.assertFalse(session.exists()); process.stdin.close.assert_called()

    def test_failed_cpu_guard_has_diagnostic_and_cleanup_without_retry(self):
        with ExitStack() as stack:
            engine, _, session, _, popen, _, listener = self.boot_fixture(stack, 'failed')
            with self.assertRaisesRegex(LabError, 'CPU limit failed: denied'): engine.boot()
            self.assertEqual(popen.call_count, 1)
            self.assertFalse(session.exists()); self.assertIsNone(engine.log_file)
            listener.close.assert_called()
            engine.configure_grader.assert_not_called()

    def test_software_boot_remains_immediately_cancellable(self):
        with ExitStack() as stack:
            engine, _, session, _, popen, process, _ = self.boot_fixture(stack, 'cancelled')
            with self.assertRaisesRegex(LabError, '취소'): engine.boot()
            self.assertEqual(popen.call_count, 1)
            process.stdin.close.assert_called(); self.assertFalse(session.exists())


if __name__ == '__main__': unittest.main()
