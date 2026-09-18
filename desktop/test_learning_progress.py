import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from learning_progress import cursor_for, read_records, remember
from learning_steps import LearningStep, learning_steps
from missions import make_mission
from native_app import Window, create_application


class LearningProgressTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def window(self, path, mode='real'):
        w = Window(self.ui, self.mono, path, mode=mode)
        self.addCleanup(w.deleteLater)
        return w

    def test_cursor_and_confirmations_survive_restart_without_lab_or_mastery(self):
        for mode, key in (('real', 'admin_user_home'), ('real', 'ros_topics'), ('simulation', 'sim_limits')):
            with self.subTest(mode=mode, key=key), tempfile.TemporaryDirectory() as d:
                path = Path(d) / 'progress.json'
                w = self.window(path, mode)
                w.select_lesson(next(i for i, u in enumerate(w.units) if u.key == key))
                w.mission = make_mission(key, 9853)
                w.learning_sequence = learning_steps(w.units[w.index], mode, w.mission)
                w.terminal.connected = True
                w.terminal.feed(b'private command not for saving\r\n')
                w.advance()
                self.assertEqual(w.learning_step, 1)
                data = json.loads(w.progress_path.read_text())
                self.assertEqual(data['last_learning'], key)
                self.assertEqual(data['learning'][key]['confirmed'], [w.learning_sequence[0].title])
                self.assertEqual(data['completed'], [])
                self.assertNotIn('private command', w.progress_path.read_text())
                self.assertNotIn('9853', w.progress_path.read_text())
                restored = self.window(path, mode)
                self.assertEqual(restored.units[restored.index].key, key)
                self.assertEqual(restored.learning_step, 1)
                self.assertEqual(restored.completed, [])
                self.assertIsNone(restored.mission)
                self.assertFalse(restored.terminal.connected)
                self.assertFalse(restored.resume_preparation.isHidden())
                self.assertIn('확인 1/', restored.steps.text())
                self.assertIn('복원되지 않습니다', restored.feedback.text())
                with patch.object(restored, 'launch') as launch:
                    restored.try_lesson()
                    launch.assert_called_once()
                    self.assertEqual(restored.learning_step, 1)
                restored.previous_learning_step()
                self.assertEqual(restored.learning_step, 0)
                again = self.window(path, mode)
                self.assertEqual(again.learning_step, 0)
                self.assertEqual(len(again.learning_progress[key]['confirmed']), 1)
                w.terminal.connected = False

    def test_last_step_confirmation_is_not_a_graded_completion(self):
        with tempfile.TemporaryDirectory() as d:
            w = self.window(Path(d) / 'p.json')
            w.select_lesson(next(i for i, u in enumerate(w.units) if u.key == 'linux_ls_detail'))
            w.mission = make_mission('linux_ls_detail', 7251)
            w.terminal.connected = True
            with patch.object(w, 'launch'):
                for _ in w.learning_sequence: w.advance()
            self.assertEqual(w.phase, 'example')
            data = json.loads(w.progress_path.read_text())
            self.assertEqual(len(data['learning']['linux_ls_detail']['confirmed']), len(w.learning_sequence))
            self.assertEqual(data['completed'], [])
            self.assertNotIn('last_learning', data)
            w.terminal.connected = False

    def test_old_progress_and_unknown_records_are_preserved_modes_are_separate(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'p.json'
            real_path = path.with_name('p-real.json')
            old = {'schema': 3, 'completed': ['lsintro', 'admin_users', 'future_unit'],
                   'checkpoints': ['checkpoint-05', 'checkpoint-35'],
                   'learning': {'future_unit': {'cursor': 'step A', 'confirmed': ['step A']}}}
            real_path.write_text(json.dumps(old))
            w = self.window(path)
            self.assertEqual(set(w.completed), {'lsintro', 'admin_users'})
            self.assertNotIn('admin_user_uid', w.completed)
            self.assertEqual(w.archived_checkpoints, ['checkpoint-05'])
            w.select_lesson(next(i for i, u in enumerate(w.units) if u.key == 'admin_user_home'))
            w.learning_step = 1
            w.remember_learning(0)
            data = json.loads(real_path.read_text())
            self.assertEqual(set(data['completed']), set(old['completed']))
            self.assertEqual(set(data['checkpoints']), set(old['checkpoints']))
            self.assertEqual(data['learning']['future_unit'], old['learning']['future_unit'])
            simulation = self.window(path, 'simulation')
            self.assertEqual(simulation.learning_progress, {})
            self.assertEqual(simulation.completed, [])

    def test_reordered_steps_restore_by_title_and_bad_values_are_safe(self):
        steps = [LearningStep(x, '', '', '') for x in ('A', 'B', 'C')]
        records = {}
        remember(records, 'unit', steps, 1, 0)
        self.assertEqual(cursor_for(records, 'unit', steps[::-1]), 1)
        changed = [LearningStep(x, '', '', '') for x in ('A', 'new', 'C')]
        self.assertEqual(cursor_for(records, 'unit', changed), 1)
        self.assertEqual(read_records(None), {})
        self.assertEqual(read_records({'bad': [], 'ok': {'cursor': [], 'confirmed': None}}),
                         {'ok': {'cursor': '', 'confirmed': []}})


if __name__ == '__main__': unittest.main()
