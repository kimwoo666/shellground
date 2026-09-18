"""No prerequisite locks; completion remains distinct from availability."""
import json
from pathlib import Path
import tempfile
import unittest

from execution_modes import mode_progress_path
from native_app import Window, create_application
from ui_layout_preview import NoExecution


class FreeSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app, cls.ui, cls.mono = create_application()

    def test_all_lessons_and_reviews_open_with_empty_progress(self):
        with tempfile.TemporaryDirectory() as directory:
            for mode in ('real', 'simulation'):
                w = Window(self.ui, self.mono, Path(directory) / 'progress.json', mode, engine=NoExecution())
                for index in range(len(w.units)):
                    self.assertTrue(w.lesson_unlocked(index))
                    w.select_lesson(index)
                    self.assertEqual(w.index, index)
                    self.assertEqual(w.phase, 'learn')
                for checkpoint in w.checkpoints:
                    self.assertTrue(w.checkpoint_unlocked(checkpoint.end))
                    w.select_checkpoint(checkpoint.end)
                    self.assertEqual(w.checkpoint_end, checkpoint.end)
                self.assertEqual(w.completed, [])
                self.assertEqual(w.completed_checkpoints, [])
                self.assertTrue(all('잠김' not in w.course.item(i).text() for i in range(w.course.count())))
                self.assertFalse(w.lesson_unlocked(-1))
                self.assertFalse(w.lesson_unlocked(len(w.units)))
                self.assertFalse(w.checkpoint_unlocked(6))
                w.deleteLater(); self.app.processEvents()

    def test_independently_completed_review_survives_reload(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'progress.json'
            w = Window(self.ui, self.mono, path, engine=NoExecution())
            w.completed_checkpoints = ['checkpoint-20']
            w.save_progress()
            restored = Window(self.ui, self.mono, path, engine=NoExecution())
            self.assertEqual(restored.completed_checkpoints, ['checkpoint-20'])
            self.assertEqual(restored.completed, [])
            w.deleteLater(); restored.deleteLater(); self.app.processEvents()

    def test_nine_completed_lessons_resume_at_ten_without_forcing_review(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'progress.json'
            w = Window(self.ui, self.mono, path, mode='real', engine=NoExecution())
            w.completed = [u.key for u in w.units[:9]]
            w.save_progress()
            restored = Window(self.ui, self.mono, path, mode='real', engine=NoExecution())
            self.assertEqual(restored.index, 9)
            self.assertIsNone(restored.checkpoint_end)
            self.assertEqual(len(restored.completed), 9)
            self.assertFalse(path.exists(), 'Other mode must not be modified')
            self.assertEqual(len(json.loads(mode_progress_path(path, 'real').read_text())['completed']), 9)
            w.deleteLater(); restored.deleteLater(); self.app.processEvents()
