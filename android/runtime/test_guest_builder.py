import importlib.util
from pathlib import Path
import tempfile
import subprocess
import unittest

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location('arm_guest_builder', HERE / 'build_guest.py')
builder = importlib.util.module_from_spec(spec)
spec.loader.exec_module(builder)


class GuestBuilderTests(unittest.TestCase):
    def test_ros_setup_allows_optional_variables_but_errors_still_fail(self):
        command = builder.ros_command('ros2 pkg prefix turtlesim')
        self.assertEqual(['bash', '-ec'], command[:2])
        self.assertIn('source /opt/ros/humble/setup.bash;', command[2])
        # Execute the selected flags against a minimal setup-script contract.
        flags = command[:2]
        result = subprocess.run(flags + ['unset AMENT_TRACE_SETUP_FILES; '
            'test -z "$AMENT_TRACE_SETUP_FILES"; printf setup-ok'], capture_output=True, text=True)
        self.assertEqual(0, result.returncode, result.stderr)
        self.assertEqual('setup-ok', result.stdout)
        self.assertNotEqual(0, subprocess.run(flags + ['false; printf must-not-pass'],
            capture_output=True).returncode)

    def test_pinned_sources_are_arm_guest_not_host_package(self):
        self.assertEqual('aarch64', builder.SOURCES['guest_arch'])
        for key in ('image', 'kernel', 'initrd'):
            source = builder.SOURCES['files'][key]
            self.assertIn('arm64', source['name'])
            self.assertIn('/release-20260913/', source['url'])
            self.assertRegex(source['sha256'], r'^[0-9a-f]{64}$')

    def test_vm_is_bounded_and_no_host_directory_is_mounted(self):
        command = builder.command_for('/owned/image', '/owned/seed', '/qemu', 31000, False)
        self.assertEqual('2', command[command.index('-smp') + 1])
        self.assertEqual('2048', command[command.index('-m') + 1])
        self.assertEqual('none', command[command.index('-nic') + 1])
        self.assertNotIn('-virtfs', command)
        self.assertNotIn('-fsdev', command)
        channel = command[command.index('-chardev') + 1]
        self.assertIn('host=127.0.0.1', channel)
        self.assertNotIn('server=on', channel)
        self.assertIn('virtserialport,chardev=sg,name=org.shellground.agent', command)

    def test_build_network_has_no_exposed_guest_ports(self):
        command = builder.command_for('/image', '/seed', '/qemu', 31000, True)
        self.assertIn('user,id=net0', command)
        self.assertNotIn('hostfwd', ' '.join(command))

    def test_hash_uses_actual_bytes(self):
        with tempfile.TemporaryDirectory() as name:
            path = Path(name) / 'source'
            path.write_bytes(b'abc')
            self.assertEqual('ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad', builder.sha256(path))
