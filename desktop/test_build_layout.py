from pathlib import Path
import unittest
from build_layout import executable_path, runtime_directory, bundle_options


class BuildLayoutTests(unittest.TestCase):
    def test_macos_app_carries_its_runtime_when_moved(self):
        app = executable_path(Path('/Applications'), 'darwin')
        self.assertEqual(app, Path('/Applications/Shellground.app/Contents/MacOS/Shellground'))
        self.assertEqual(runtime_directory(app, 'darwin'),
                         Path('/Applications/Shellground.app/Contents/Resources/runtime'))
        self.assertEqual(bundle_options('darwin'), ['--onedir', '--windowed'])

    def test_windows_and_linux_keep_sibling_runtime(self):
        for system, filename in [('win32', 'Shellground/Shellground.exe'), ('linux', 'Shellground')]:
            with self.subTest(system=system):
                app = executable_path(Path('output'), system)
                self.assertEqual(app, Path('output') / filename)
                self.assertEqual(runtime_directory(app, system), app.parent / 'runtime')
                expected = ['--onedir' if system == 'win32' else '--onefile', '--windowed']
                if system == 'win32': expected += ['--python-option', 'X utf8']
                self.assertEqual(bundle_options(system), expected)

    def test_macos_development_python_is_not_mistaken_for_app(self):
        self.assertEqual(runtime_directory(Path('/venv/bin/python'), 'darwin'),
                         Path('/venv/bin/runtime'))
