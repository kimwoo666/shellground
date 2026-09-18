import json
from pathlib import Path
import tempfile
import unittest

from conda_teaching.engine import SHELL_INIT
from export_conda_course import export


class CondaAndroidAssetTests(unittest.TestCase):
    def test_existing_guest_sources_are_staged_without_a_new_engine(self):
        root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory() as folder:
            target = Path(folder)
            export(target)
            scripts = target / 'conda-guest'
            for name, original in (
                ('conda_runtime.py', 'conda_teaching/guest_runtime.py'),
                ('shell_snapshot.py', 'guest/shell_snapshot.py'),
                ('guest_files.py', 'conda_teaching/guest_files.py'),
            ):
                self.assertEqual((scripts / name).read_bytes(), (root / original).read_bytes())
            self.assertEqual((scripts / 'bashrc').read_text(), (root / 'guest/bashrc').read_text() + SHELL_INIT)
            data = json.loads((target / 'conda-course.json').read_text())
            self.assertEqual(data['schema'], 2)
            self.assertEqual(len(data['units']), 18)
            self.assertFalse(data['runtime_integration']['practice_enabled'])
            self.assertFalse(data['runtime_integration']['optional_install_enabled'])
            # Export never grants progress or fabricates a runtime validation.
            self.assertEqual({p.name for p in target.iterdir()}, {'conda-course.json', 'conda-guest'})


if __name__ == '__main__':
    unittest.main()
