import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mode_curriculum import curriculum, ROS_UNITS, ROS_CHECKPOINTS
from missions import UNITS, lesson_text, make_mission, random_mission
from checkpoints import make_checkpoint
from native_app import Window, create_application
from real_vm import RealEngine


class RosCurriculumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def test_preserves_original_curriculum_and_adds_real_ros(self):
        self.assertEqual(curriculum('simulation')[0][:40], UNITS)
        real, reviews = curriculum('real')
        self.assertTrue({u.key for u in UNITS}.issubset({u.key for u in real}))
        self.assertEqual(len(real), 95)
        self.assertEqual([c.end for c in reviews], list(range(5, 96, 5)))
        self.assertEqual(tuple(u for c in ROS_CHECKPOINTS for u in c.units), ROS_UNITS)
        for unit in ROS_UNITS:
            self.assertIn('직접 해볼 예시', lesson_text(unit))
            for variant in (0, 1, 2):
                mission = make_mission(unit.key, 1234, variant)
                self.assertTrue(mission.review['ros'])
                self.assertTrue(mission.solution)
        for checkpoint in ROS_CHECKPOINTS:
            actual = next(c for c in reviews if c.key == checkpoint.key)
            self.assertEqual(actual.units, checkpoint.units)
            self.assertEqual(make_checkpoint(actual.end).review['checkpoint'], checkpoint.key)

    def test_ros_can_start_independently_and_progress_survives(self):
        with tempfile.TemporaryDirectory() as directory, patch('native_app.create_engine', return_value=RealEngine()):
            path = Path(directory) / 'progress.json'
            window = Window(self.ui, self.mono, path, mode='real')
            self.assertTrue(window.lesson_unlocked(75))
            self.assertTrue(window.lesson_unlocked(76))
            window.select_lesson(75)
            self.assertEqual(window.index, 75)
            window.completed = [u.key for u in ROS_UNITS[:5]]
            self.assertTrue(window.checkpoint_unlocked(80))
            window.completed_checkpoints = ['checkpoint-45']
            self.assertTrue(window.save_progress())
            self.assertTrue(window.lesson_unlocked(80))
            window.completed, window.completed_checkpoints = [], []
            window.load_progress()
            self.assertIn('checkpoint-45', window.completed_checkpoints)
            window.phase = 'practice'
            window.refresh_course()
            row = window.course.item(window.unit_rows[75]).text()
            self.assertNotIn('source', row)
            self.assertNotIn(ROS_UNITS[0].title, row)
            mission = random_mission(['ros_env'], units=window.units)
            self.assertEqual(mission.kind, 'ros_env')
            self.assertFalse(path.exists())
            window.deleteLater()
            self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
