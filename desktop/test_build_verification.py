from pathlib import Path
import tempfile
import unittest
from build_verification import verification_commands
from release_smoke import manifest, RESOURCES


class IncrementalBuildTests(unittest.TestCase):
    def test_explicit_build_only_never_launches_native_tests(self):
        self.assertEqual(verification_commands('Shellground.exe', 'out', 'runtime', 'python',
            conda=True, notebook=True, system='win32', build_only=True), [])
        with self.assertRaises(ValueError):
            verification_commands('app', 'out', 'runtime', 'python', full=True, build_only=True)

    def test_default_is_packaged_smoke_not_old_courses(self):
        commands = verification_commands('Shellground', 'out', 'runtime', 'python', conda=True, notebook=True)
        flags = [command[1] for command in commands]
        self.assertEqual(flags, ['--self-test-release', '--self-test-study-ui', '--self-test-conda', '--self-test-notebook-package'])
        text = repr(commands)
        for flag in ('--self-test-real', '--self-test-python', '--self-test-ros-course', '--self-test-notebook-ui'):
            self.assertNotIn(flag, text)
        self.assertNotIn('unittest', text)

    def test_full_rerun_requires_explicit_choice(self):
        commands = verification_commands('Shellground', 'out', 'runtime', 'python', conda=True, notebook=True, full=True)
        self.assertIn(['Shellground', '--self-test'], commands)
        self.assertIn(['python', '-m', 'unittest', 'test_python_packaged', '-v'], commands)
        self.assertTrue(any(c[1] == '--self-test-notebook' for c in commands))

    def test_bundle_manifest_binds_new_helpers_and_current_catalog(self):
        value = manifest(Path(__file__).parent)
        self.assertEqual(set(value['resources']), set(RESOURCES))
        self.assertEqual(len(value['catalog']['concepts']), 44)
        self.assertIn('docker_sessions_attach', value['catalog']['units'])
        self.assertIn('system_clock', value['catalog']['units'])
        self.assertEqual(len(value['catalog']['units']), 138)
        self.assertEqual(len(value['catalog']['python']), 95)
        self.assertTrue(all(len(digest) == 64 for digest in value['resources'].values()))

    def test_source_execution_cannot_be_mislabeled_as_frozen(self):
        from release_smoke import main
        from notebook_teaching.package_smoke import main as notebook
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'proof.json'
            with self.assertRaisesRegex(RuntimeError, 'executable'): main(['--report', str(path)])
            with self.assertRaisesRegex(RuntimeError, 'executable'): notebook(['--runtime', folder, '--report', str(path)])
            self.assertFalse(path.exists())


if __name__ == '__main__': unittest.main()
