"""UI-only checks; no VM, guest commands or real progress records."""
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtWidgets import QMessageBox
from course_topics import TOPICS, topic_of, topic_indices, unit_number, checkpoint_label, next_in_topic
from mode_curriculum import curriculum
from native_app import Window, create_application
from layout_presets import PRESETS


class TopicLayoutTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app, cls.ui, cls.mono = create_application()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.windows = []

    def tearDown(self):
        for w in self.windows:
            w._shutdown_ready = True
            w.close(); w.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def window(self, mode='simulation', layout='a'):
        w = Window(self.ui, self.mono, Path(self.temp.name) / 'progress.json', mode, layout)
        self.windows.append(w)
        return w

    def test_numbering_covers_every_unit_without_changing_keys(self):
        for mode in ('simulation', 'real'):
            units, checks = curriculum(mode)
            covered = []
            for topic, count in zip(TOPICS, (60 if mode == 'real' else 35, 15 if mode == 'real' else 10, 20 if mode == 'real' else 0)):
                indices = topic_indices(units, topic)
                self.assertEqual(len(indices), count)
                self.assertEqual([unit_number(units, i) for i in indices], list(range(1, count + 1)))
                covered.extend(indices)
            self.assertEqual(sorted(covered), list(range(len(units))))
            self.assertIn('Docker 01–05', checkpoint_label(units, next(c for c in checks if c.key == 'checkpoint-35')))
            for topic in TOPICS:
                indices = topic_indices(units, topic)
                if indices: self.assertIsNone(next_in_topic(units, indices[-1]))
            if mode == 'real':
                self.assertIn('Docker 11–15', checkpoint_label(units, next(c for c in checks if c.key == 'docker-checkpoint-deployment')))
                self.assertIn('리눅스 56–60', checkpoint_label(units, next(c for c in checks if c.end == 60)))

    def test_topics_are_independent_and_progress_is_preserved(self):
        w = self.window('real')
        self.assertTrue(w.lesson_unlocked(30))
        self.assertTrue(w.lesson_unlocked(40))
        self.assertTrue(w.lesson_unlocked(31))
        w.topic_tabs.setCurrentIndex(1)
        self.assertEqual((w.topic, w.index), ('Docker', 60))
        self.assertIn('Docker 01.', w.heading.text())
        self.assertEqual(w.progress.maximum(), 15)
        visible = [w.course.item(i) for i in range(w.course.count()) if not w.course.item(i).isHidden()]
        self.assertEqual(len(visible), 18)
        self.assertTrue(visible[0].text().startswith('01.'))
        w.completed = [w.units[60].key]
        w.save_progress()
        restored = self.window('real')
        restored.topic_tabs.setCurrentIndex(1)
        self.assertEqual(restored.completed, w.completed)
        self.assertEqual(restored.index, 61)
        self.assertEqual(restored.progress.value(), 1)
        restored.topic_tabs.setCurrentIndex(2)
        self.assertEqual(restored.index, 75)
        self.assertIn('ROS 2 01.', restored.heading.text())

    def test_topic_cancel_preserves_session_and_random_scope(self):
        w = self.window()
        from missions import make_mission
        w.mission = make_mission('navigate', 4242)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            w.topic_tabs.setCurrentIndex(1)
        self.assertEqual((w.topic, w.index, w.topic_tabs.currentIndex()), ('리눅스', 0, 0))
        self.assertIsNotNone(w.mission)
        w.completed = [w.units[0].key, w.units[30].key]
        w.mission = None
        with patch.object(w, 'launch') as launch:
            w.start_random()
            self.assertEqual(launch.call_args.args[0].kind, w.units[0].key)
            self.assertEqual(w.random_keys(), [w.units[0].key])
            w.start_random(all_topics=True)
            self.assertEqual(set(w.random_keys()), set(w.completed))
        self.assertFalse(w.topic_tabs.isTabEnabled(2))

    def test_layout_trials_expand_both_areas_and_keep_default(self):
        sizes = {}
        for key in PRESETS:
            w = self.window('real', key)
            w.show(); w.resize(1220, 880)
            for _ in range(3): self.app.processEvents()
            sizes[key] = (w.instructions.width(), w.instructions.height(), w.terminal.width(), w.terminal.height())
            self.assertEqual((w.width(), w.height()), (1220, 880))
            if key != 'current':
                self.assertIsNotNone(w.practice_splitter)
                self.assertEqual(w.task_tabs.tabText(1), '채점 결과')
                w.practice_splitter.setSizes([170, 450])
                self.app.processEvents()
                self.assertGreater(w.terminal.height(), sizes[key][3])
        for key in ('a', 'b', 'c'):
            self.assertTrue(all(value > baseline for value, baseline in zip(sizes[key], sizes['current'])), sizes)
        self.assertEqual(self.window().layout_key, 'a')

    def test_preview_selector_and_render_are_isolated(self):
        from ui_layout_preview import Preview
        with patch('native_app.create_engine', side_effect=AssertionError('Preview must not create an execution engine')):
            preview = Preview('a')
            from PySide6.QtWidgets import QComboBox
            combo = preview.window.findChild(QComboBox)
            self.assertTrue(combo.isVisible())
            combo.setCurrentIndex(2)
            self.app.processEvents()
            self.assertEqual(preview.window.layout_key, 'b')
            self.assertEqual(list(Path(preview.temporary.name).iterdir()), [])
            preview.window.close(); preview.window.deleteLater()
            preview.temporary.cleanup()
