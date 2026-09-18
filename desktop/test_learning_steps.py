import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from course_topics import topic_of
from learning_steps import learning_steps
from mode_curriculum import curriculum
from missions import make_mission
from sim_engine import SimEngine


class LearningStepContentTests(unittest.TestCase):
    def test_every_docker_and_ros_unit_has_short_authored_steps(self):
        for mode in ('simulation', 'real'):
            units, _ = curriculum(mode)
            for unit in units:
                with self.subTest(mode=mode, unit=unit.key):
                    steps = learning_steps(unit, mode)
                    if topic_of(unit) == '리눅스':
                        if mode == 'simulation': self.assertEqual(steps, ())
                        elif steps:
                            self.assertGreaterEqual(len(steps), 2)
                            for step in steps:
                                self.assertTrue(step.explanation and step.commands and step.observation)
                        continue
                    self.assertGreaterEqual(len(steps), 3)
                    self.assertLessEqual(len(steps), 6)
                    self.assertEqual(len({s.title for s in steps}), len(steps))
                    for step in steps:
                        self.assertTrue(step.explanation and step.commands and step.observation)
                        self.assertLess(len(step.explanation), 300)
                        self.assertLess(len(step.text), 750)
                        self.assertNotIn('4242', step.text if not step.commands else step.explanation)

    def test_examples_are_bound_to_actual_mission_not_preview_seed(self):
        units, _ = curriculum('real')
        for unit in units:
            if topic_of(unit) == '리눅스': continue
            mission = make_mission(unit.key, 9853)
            text = '\n'.join(step.text for step in learning_steps(unit, 'real', mission))
            self.assertNotIn('4242', text)
            if unit.key.startswith('sim_'):
                self.assertNotIn('docker pull ubuntu:24.04', text)

    def test_simulated_docker_steps_run_in_order_and_reach_original_goal(self):
        for unit in curriculum('simulation')[0]:
            if topic_of(unit) != 'Docker': continue
            with self.subTest(unit=unit.key):
                m = make_mission(unit.key, 9853)
                engine = SimEngine()
                try:
                    engine.start(m)
                    for step in learning_steps(unit, 'simulation', m):
                        for line in step.commands.splitlines():
                            result = engine.shell.execute(line)
                            self.assertEqual(result.code, 0, (step.title, line, result.err))
                    result = engine.rpc('grade', m)
                    self.assertTrue(result['passed'], result)
                finally:
                    engine.close()


class LearningStepUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from native_app import create_application
        cls.app, cls.ui, cls.mono = create_application()

    def window(self, directory):
        from native_app import Window
        window = Window(self.ui, self.mono, Path(directory) / 'progress.json')
        self.addCleanup(window.deleteLater)
        return window

    def test_step_navigation_keeps_lab_and_does_not_award_completion(self):
        with tempfile.TemporaryDirectory() as directory:
            w = self.window(directory)
            index = next(i for i, u in enumerate(w.units) if u.key == 'sim_limits')
            w.select_lesson(index)
            self.assertEqual(w.learning_step, 0)
            self.assertIn('1/6', w.steps.text())
            with patch.object(w, 'try_lesson') as start:
                w.advance()
                start.assert_called_once()
                self.assertEqual(w.learning_step, 0)
            mission = make_mission('sim_limits', 9853)
            w.mission = mission
            w.engine.start(mission)
            self.addCleanup(w.engine.close)
            w.engine.shell.execute('printf keep > step-marker.txt')
            w.learning_sequence = learning_steps(w.units[index], w.mode, mission)
            w.terminal.connected = True
            w.terminal.feed(b'keep scrollback\r\n')
            generation, terminal, screen = w.generation, w.terminal, w.terminal.screen
            with patch.object(w, 'launch') as launch, patch.object(w, 'save_progress') as save:
                for n in range(1, len(w.learning_sequence)):
                    w.advance()
                    self.assertEqual(w.learning_step, n)
                    self.assertEqual(w.phase, 'learn')
                    self.assertIs(w.mission, mission)
                    self.assertIs(w.terminal, terminal)
                    self.assertIs(w.terminal.screen, screen)
                    self.assertEqual(w.generation, generation)
                    self.assertEqual(w.engine.shell.execute('cat step-marker.txt').out, b'keep')
                    self.assertFalse(w.grade_button.isEnabled())
                launch.assert_not_called()
                self.assertEqual(save.call_count, len(w.learning_sequence) - 1)
                w.previous_learning_step()
                self.assertEqual(w.learning_step, len(w.learning_sequence) - 2)
                w.advance()
                w.advance()
                launch.assert_called_once()
                self.assertEqual(w.phase, 'example')
                self.assertEqual(w.completed, [])
            self.assertTrue(w.progress_path.exists())
            w.terminal.connected = False

    def test_restart_returns_to_first_step_and_tests_hide_navigation(self):
        from PySide6.QtWidgets import QMessageBox
        with tempfile.TemporaryDirectory() as directory:
            w = self.window(directory)
            index = next(i for i, u in enumerate(w.units) if u.key == 'sim_images')
            w.select_lesson(index)
            w.mission = make_mission('sim_images', 9853)
            w.learning_step = 2
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes), patch.object(w, 'launch'):
                w.restart_mission()
            self.assertEqual(w.learning_step, 0)
            w.phase = 'practice'
            w.update_controls()
            self.assertTrue(w.previous_learning.isHidden())
            w.previous_learning_step()
            self.assertEqual(w.learning_step, 0)
            # Linux retains its existing short, single learning screen.
            w.mission = None
            w.select_lesson(0)
            self.assertEqual(w.learning_sequence, ())
            with patch.object(w, 'launch') as launch:
                w.advance()
                launch.assert_called_once()
                self.assertEqual(w.phase, 'example')


if __name__ == '__main__': unittest.main()
