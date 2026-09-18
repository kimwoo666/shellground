"""Mode separation must never imply a simulated command ran on real Linux."""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from execution_modes import create_engine, mode_progress_path
from mode_dialog import ModeDialog
from native_app import Window, create_application, main
from missions import UNITS, make_mission
from sim_engine import SimEngine


class ExecutionModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def test_backend_factory_never_falls_back(self):
        self.assertIsInstance(create_engine('simulation'), SimEngine)
        with patch('real_vm.runtime_info', side_effect=RuntimeError('missing runtime')), self.assertRaises(RuntimeError):
            create_engine('real')
        with self.assertRaises(ValueError):
            create_engine('typo')

    def test_progress_paths_do_not_overlap(self):
        path = Path('/tmp/progress-v3.json')
        self.assertEqual(mode_progress_path(path, 'simulation'), path)
        self.assertEqual(mode_progress_path(path, 'real'), Path('/tmp/progress-v3-real.json'))
        with self.assertRaises(ValueError):
            mode_progress_path(path, 'typo')

    def test_dialog_truthfully_blocks_unavailable_backend(self):
        with patch('mode_dialog.mode_available', side_effect=lambda key: key == 'simulation'):
            dialog = ModeDialog()
            self.assertFalse(dialog.buttons['real'].isEnabled())
            dialog.select_mode('real')
        self.assertIsNone(dialog.selected_mode)
        dialog.buttons['simulation'].click()
        self.assertEqual(dialog.selected_mode, 'simulation')
        self.assertEqual(dialog.result(), dialog.DialogCode.Accepted)

    def test_existing_progress_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'progress.json'
            path.write_text(json.dumps({'schema': 3, 'completed': [UNITS[0].key]}))
            window = Window(self.ui, self.mono, path)
            self.assertEqual(window.completed, [UNITS[0].key])
            self.assertIn('시뮬레이션 모드', window.windowTitle())
            self.assertTrue(window.save_progress())
            self.assertFalse(mode_progress_path(path, 'real').exists())
            window.deleteLater()
            self.app.processEvents()

    def test_picker_shows_each_modes_saved_progress_without_copying(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'progress.json'
            path.write_text(json.dumps({'schema': 3, 'completed': [u.key for u in UNITS[:9]], 'checkpoints': ['checkpoint-05']}))
            dialog = ModeDialog(progress_path=path)
            self.assertIn('단원 9개', dialog.progress_labels['simulation'].text())
            self.assertIn('종합 복습 1개', dialog.progress_labels['simulation'].text())
            self.assertIn('기록이 없습니다', dialog.progress_labels['real'].text())
            self.assertFalse(mode_progress_path(path, 'real').exists())
            dialog.deleteLater(); self.app.processEvents()

    def test_opening_picker_preserves_practice_state(self):
        with tempfile.TemporaryDirectory() as directory:
            window = Window(self.ui, self.mono, Path(directory) / 'progress.json')
            mission = make_mission('mkdir', 4242)
            window.engine.start(mission)
            window.engine.shell.execute('echo keep > /home/learner/keep.txt')
            window.mission = mission
            window.terminal.connected = True
            generation = window.generation
            with patch.object(ModeDialog, 'exec', return_value=ModeDialog.DialogCode.Rejected):
                window.choose_mode()
            self.assertIs(window.mission, mission)
            self.assertEqual(window.generation, generation)
            self.assertTrue(window.terminal.connected)
            self.assertEqual(window.engine.shell.fs.read('/home/learner/keep.txt'), b'keep\n')
            window.engine.close()
            window.deleteLater()
            self.app.processEvents()

    def test_real_cli_fails_before_creating_application(self):
        with patch('sys.argv', ['shellground', '--mode', 'real']), patch('native_app.mode_available', return_value=False), patch('native_app.create_application') as create:
            self.assertEqual(main(), 2)
            create.assert_not_called()


if __name__ == '__main__':
    unittest.main()
