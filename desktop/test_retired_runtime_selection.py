"""Selection checks only: no VM boot or repeat of already passed lessons."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import real_vm


class RetiredRuntimeSelectionTests(unittest.TestCase):
    def test_source_uses_current_shared_pack(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for relative in ('.vm-runtime-conda/linux-x86_64', '.vm-runtime/linux-x86_64'):
                pack = root / relative
                pack.mkdir(parents=True)
                (pack / 'runtime.json').touch()
            with patch.object(real_vm, 'resource_path', side_effect=lambda p: root / p), \
                    patch.object(real_vm.sys, 'executable', str(root / 'python')), \
                    patch.object(real_vm.sys, 'frozen', False, create=True), \
                    patch('platform_runtime.runtime_tag', return_value='linux-x86_64'):
                self.assertEqual(real_vm.runtime_root(), root / '.vm-runtime-conda/linux-x86_64')

    def test_frozen_keeps_its_own_runtime(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            pack = root / 'runtime/linux-x86_64'
            pack.mkdir(parents=True)
            (pack / 'runtime.json').touch()
            with patch.object(real_vm, 'resource_path', side_effect=lambda p: root / 'resources' / p), \
                    patch.object(real_vm.sys, 'executable', str(root / 'Shellground')), \
                    patch.object(real_vm.sys, 'frozen', True, create=True), \
                    patch('platform_runtime.runtime_tag', return_value='linux-x86_64'):
                self.assertEqual(real_vm.runtime_root(), pack)


if __name__ == '__main__':
    unittest.main()
