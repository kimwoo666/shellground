"""Opt-in end-to-end boot with the same offline pack/engine used by the app."""
import base64
import json
import os
from pathlib import Path
import time
import unittest
from unittest.mock import patch

from real_vm import RealEngine, runtime_info
from ros_lessons import make_ros_mission


@unittest.skipUnless(os.environ.get('SHELLGROUND_BUNDLED_TEST') == '1', 'Explicit bundled-VM test required')
class BundledRuntimeTests(unittest.TestCase):
    def test_real_qemu_cannot_outlive_killed_supervisor(self):
        from vm_crash_diagnostics import process_running
        from vm_supervisor import reap_abandoned_sessions
        engine = RealEngine()
        root, spec = runtime_info()
        base = root / spec['image']
        original = base.stat()
        try:
            engine.boot()
            directory = engine.session_dir
            state = json.loads((directory / 'guard.json').read_text())
            # This test runs the source supervisor: its Popen handle is the
            # actual Python guard, not a onefile bootloader wrapper.
            self.assertEqual(engine.process.pid, state['guard_pid'])
            engine.process.kill()
            engine.process.wait(timeout=3)
            deadline = time.monotonic() + 5
            while process_running(state['child_pid']) and time.monotonic() < deadline:
                time.sleep(.05)
            self.assertFalse(process_running(state['child_pid']))
            self.assertTrue(directory.exists())
            with patch('vm_supervisor.Path.glob', return_value=[directory]):
                self.assertEqual(reap_abandoned_sessions(), [str(directory)])
            self.assertFalse(directory.exists())
        finally:
            engine.close()
        self.assertEqual((base.stat().st_size, base.stat().st_mtime_ns),
                         (original.st_size, original.st_mtime_ns))

    def test_real_vm_app_crash_at_startup_and_after_boot(self):
        from vm_crash_diagnostics import verify_crash_cleanup
        self.assertEqual(len(verify_crash_cleanup()), 2)

    def test_offline_boot_ros_grade_display_and_owned_cleanup(self):
        root, spec = runtime_info()
        base = root / spec['image']
        original = base.stat()
        engine = RealEngine()
        mission = make_ros_mission('ros_set', 7890)
        start = time.monotonic()
        try:
            engine.start(mission)
            process = engine.process
            directory = engine.session_dir
            self.assertIn('none', process.args[process.args.index('-nic') + 1:process.args.index('-nic') + 2])
            engine.open_terminal(mission)
            self.assertFalse(engine.rpc('grade', mission)['passed'])
            result = engine.channel.request('exec', cwd=mission.start, run_timeout=20,
                argv=['bash', '-c', mission.solution])
            self.assertEqual(result['code'], 0, base64.b64decode(result['err']).decode())
            self.assertTrue(engine.rpc('grade', mission)['passed'])
            picture = engine.screen()
            self.assertTrue(picture.startswith(b'\x89PNG'))
            Path('/tmp/shellground-offline-runtime.png').write_bytes(picture)
            print(f'\nOFFLINE_BOOT_SECONDS={engine.start_seconds:.2f}', flush=True)
        finally:
            closing = time.monotonic()
            engine.close()
            print(f'CLOSE_SECONDS={time.monotonic() - closing:.2f}', flush=True)
        self.assertIsNotNone(process.poll())
        self.assertFalse(directory.exists())
        self.assertEqual(base.stat().st_mtime_ns, original.st_mtime_ns)
        self.assertEqual(base.stat().st_size, original.st_size)
        print(f'END_TO_END_SECONDS={time.monotonic() - start:.2f}', flush=True)


if __name__ == '__main__':
    unittest.main()
