"""Preferences and random-mode exits without a VM or real user profiles."""
from dataclasses import replace
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPointF
from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QMessageBox

from app_settings import Settings, SettingsDialog, load_settings, save_settings
from native_app import Window, create_application
from missions import make_mission
from terminal_widget import COLORS, TerminalWidget


class UITestCase(unittest.TestCase):
    @classmethod
    def setUpClass(cls): cls.app, cls.ui, cls.mono = create_application()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / 'progress.json'
        self.widgets = []

    def tearDown(self):
        for widget in self.widgets:
            if isinstance(widget, Window):
                widget.simulation_timer.stop()
                widget._shutdown_ready = True
            widget.close()
            widget.deleteLater()
        self.app.processEvents()
        self.temp.cleanup()

    def window(self, mode='simulation'):
        w = Window(self.ui, self.mono, self.path, mode=mode)
        self.widgets.append(w)
        return w

    def terminal(self):
        t = TerminalWidget(self.mono)
        self.widgets.append(t)
        t.resize(700, 350)
        t.show()
        self.app.processEvents()
        return t


class SettingsTests(UITestCase):
    def test_validation_missing_corrupt_and_unknown_settings(self):
        self.assertEqual(load_settings(self.path), Settings())
        self.path.write_text('{bad')
        self.assertEqual(load_settings(self.path), Settings())
        self.assertEqual(self.path.read_text(), '{bad')
        for data in (None, [], 12, 'text'):
            self.assertEqual(Settings.from_dict(data), Settings())
        settings = Settings.from_dict(dict(theme='bogus', terminal_colors='false',
                                           terminal_font_size=10000, text_font_size=-2,
                                           drag_autoscroll=0, color_groups=['green', 'green', 'bogus']))
        self.assertEqual(settings.theme, 'light')
        self.assertTrue(settings.terminal_colors)
        self.assertTrue(settings.drag_autoscroll)
        self.assertEqual((settings.terminal_font_size, settings.text_font_size), (24, 9))
        self.assertEqual(settings.color_groups, ('green',))
        self.assertEqual(Settings.from_dict({'terminal_font_size': True}).terminal_font_size, 12)
        self.assertEqual(Settings.from_dict({'color_groups': []}).color_groups, ())

    def test_persist_separately_and_share_between_modes(self):
        w = self.window()
        w.completed = [w.units[0].key]
        w.save_progress()
        before = self.path.read_bytes()
        settings = Settings(theme='dark', terminal_colors=False, color_groups=('green',),
                            terminal_font_size=14, text_font_size=13, drag_autoscroll=False)
        save_settings(w.settings_path, settings)
        restored = self.window()
        self.assertEqual(restored.settings, settings)
        self.assertEqual(restored.completed, w.completed)
        self.assertEqual(restored.terminal.font_.pointSize(), 14)
        self.assertEqual(restored.instructions.font().pointSize(), 13)
        self.assertEqual(restored.palette().color(QPalette.ColorRole.Window).name(), '#25292e')
        self.assertEqual(self.path.read_bytes(), before)
        real = self.window('real')
        self.assertEqual(real.settings, settings)
        self.assertEqual(real.completed, [])  # Never merge real/simulator progress.
        self.assertEqual(json.loads(w.settings_path.read_text())['schema'], 1)

    def test_cancel_preview_and_defaults_do_not_change_window(self):
        w = self.window()
        dialog = SettingsDialog(w.settings, self.mono, w)
        self.widgets.append(dialog)
        dialog.theme.setCurrentIndex(1)
        dialog.terminal_colors.setChecked(False)
        self.assertEqual(dialog.values().theme, 'dark')
        self.assertFalse(dialog.preview.settings.terminal_colors)
        self.assertEqual(w.settings, Settings())
        dialog.buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).click()
        self.assertEqual(dialog.values(), Settings())
        dialog.reject()
        self.assertFalse(w.settings_path.exists())

    def test_open_settings_save_cancel_and_failure(self):
        w = self.window()
        settings = Settings(theme='dark', terminal_colors=False)
        with patch('native_app.SettingsDialog') as factory:
            dialog = factory.return_value
            dialog.exec.return_value = QDialog.DialogCode.Rejected
            dialog.values.return_value = settings
            w.open_settings()
            self.assertEqual(w.settings, Settings())
            self.assertFalse(w.settings_path.exists())
            dialog.exec.return_value = QDialog.DialogCode.Accepted
            with patch('native_app.save_settings', side_effect=OSError('read only')), patch.object(QMessageBox, 'warning') as warning:
                w.open_settings()
                warning.assert_called_once()
            self.assertEqual(w.settings, Settings())
            w.open_settings()
            self.assertEqual(w.settings, settings)
            self.assertEqual(load_settings(w.settings_path), settings)

    def test_terminal_colors_filter_without_changing_raw_state_or_input(self):
        t = self.terminal()
        t.connected = True
        sent = []
        t.input_bytes.connect(sent.append)
        t.feed(b'\x1b[32mG\x1b[34mB\x1b[31mR\x1b[0mN\x1b[7mI\x1b[0m')
        t.select_all()
        state = (t.screen.display[:], t.selection_start, t.selection_end, t.view_top, id(t.stream))
        t.apply_settings(Settings(terminal_colors=False))
        self.assertEqual(t.display_color('green').name(), t.default_color())
        self.assertEqual(t.display_color('red', True).name(), t.default_color(True))
        self.assertEqual(t.screen.buffer[0][0].fg, 'green')
        self.assertTrue(t.screen.buffer[0][4].reverse)
        self.assertEqual(state, (t.screen.display[:], t.selection_start, t.selection_end, t.view_top, id(t.stream)))
        t.apply_settings(Settings(color_groups=('green',)))
        self.assertEqual(t.display_color('green').name(), COLORS['green'])
        self.assertEqual(t.display_color('brightgreen').name(), COLORS['brightgreen'])
        self.assertEqual(t.display_color('blue').name(), t.default_color())
        self.assertEqual(t.display_color('abcdef').name(), t.default_color())
        t.apply_settings(Settings(color_groups=('extended',)))
        self.assertEqual(t.display_color('abcdef').name(), '#abcdef')
        self.assertEqual(t.display_color('default').name(), t.default_color())
        t.apply_settings(Settings())
        self.assertEqual(t.display_color('red').name(), COLORS['red'])
        self.assertTrue(t.connected)
        self.assertEqual(sent, [])

    def test_terminal_light_font_and_drag_preferences(self):
        t = self.terminal()
        t.feed(''.join(f'line {i}\r\n' for i in range(50)).encode())
        t.dragging = True
        t.drag_position = QPointF(10, -30)
        t.selection_start = t.selection_end = (t.screen.history_serial, 0)
        t.update_drag_scroll()
        self.assertTrue(t.drag_scroll.isActive())
        before = id(t.stream)
        sizes = []
        t.resized.connect(lambda *size: sizes.append(size))
        t.apply_settings(Settings(terminal_theme='light', terminal_font_size=16, drag_autoscroll=False))
        self.assertFalse(t.drag_scroll.isActive())
        self.assertEqual(t.drag_scroll_lines(), 0)
        self.assertEqual(id(t.stream), before)
        self.assertEqual(t.default_color(True), '#f4f7f3')
        self.assertEqual(t.display_color('blue').name(), '#174caa')
        self.assertEqual(t.font_.pointSize(), 16)
        self.assertEqual(len(sizes), 1)
        self.assertGreater(len(t.screen.history.top), 0)

    def test_existing_and_new_terminal_use_preferences(self):
        w = self.window('real')
        settings = Settings(theme='dark', color_groups=('green',))
        w.apply_settings(settings)
        self.assertEqual(w.terminal.settings, settings)
        w.mission = make_mission('navigate', 4242)
        w.engine.channel = SimpleNamespace(open_terminal=lambda start: SimpleNamespace(sid=2))
        with patch.object(w, 'run_job', side_effect=lambda fn, callback: callback(fn(lambda text: None))), patch.object(w, 'attach_reader'):
            w.new_terminal()
        self.assertEqual(len(w.terminals), 2)
        self.assertTrue(all(t.settings == settings for t in w.terminals))
        w.apply_settings(replace(settings, terminal_colors=False))
        self.assertTrue(all(not t.settings.terminal_colors for t in w.terminals))
        w.engine.channel = None

    def test_dark_feedback_keeps_all_seven_checks(self):
        w = self.window()
        checks = [{'label': f'항목 {i}', 'passed': i % 2 == 0} for i in range(7)]
        w.feedback.set_results('결과', checks)
        w.apply_settings(Settings(theme='dark'))
        self.assertIn('#91dda8', w.feedback.toHtml())
        self.assertIn('#ffab96', w.feedback.toHtml())
        self.assertEqual(w.feedback._checks, checks)
        for i in range(7): self.assertIn(f'항목 {i}', w.feedback.text())


class RandomExitTests(UITestCase):
    def test_unfinished_random_can_exit_to_same_unit_without_progress_loss(self):
        w = self.window()
        w.completed = [w.units[0].key, w.units[30].key]
        w.save_progress()
        before = self.path.read_bytes()
        w.select_lesson(5)
        with patch.object(w, 'run_job'):
            w.start_random(all_topics=True)
        self.assertEqual(w.phase, 'random')
        self.assertIn('전체 분야', w.steps.text())
        self.assertFalse(w.exit_random_button.isHidden())
        self.assertTrue(w.exit_random_button.isEnabled())
        self.assertFalse(w.next_button.isEnabled())
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            w.exit_random_button.click()
        self.assertEqual((w.phase, w.index, w.mission), ('learn', 5, None))
        self.assertIsNone(w.random_return)
        self.assertFalse(w.random_all_topics)
        self.assertTrue(w.exit_random_button.isHidden())
        self.assertEqual(self.path.read_bytes(), before)
        self.assertNotIn('평가 중 학습 내용 숨김', w.course.currentItem().text())

    def test_exit_confirmation_cancel_and_busy_preserve_random(self):
        w = self.window()
        w.completed = [w.units[0].key]
        with patch.object(w, 'run_job'): w.start_random()
        mission = w.mission
        anchor = w.random_return
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No):
            w.exit_random()
        self.assertEqual(w.phase, 'random')
        self.assertIs(w.mission, mission)
        self.assertEqual(w.random_return, anchor)
        w.busy = True
        w.update_controls()
        w.exit_random()
        self.assertFalse(w.exit_random_button.isEnabled())
        self.assertEqual(w.phase, 'random')
        w.busy = False

    def test_scope_switch_does_not_replace_return_destination(self):
        w = self.window()
        w.completed = [w.units[0].key, w.units[30].key]
        w.select_lesson(30)
        w.learning_step = 1
        w.render_learning_step()
        with patch.object(w, 'run_job'), patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes):
            w.start_random(all_topics=True)
            anchor = w.random_return
            w.start_random(all_topics=False)
        self.assertEqual(w.random_return, anchor)
        self.assertIn('Docker', w.steps.text())
        self.assertNotIn('전체 분야', w.steps.text())
        self.assertEqual(w.random_keys(), [w.units[30].key])
        w.passed = True
        with patch.object(QMessageBox, 'question') as confirm:
            w.exit_random()
            confirm.assert_not_called()
        self.assertEqual((w.index, w.learning_step, w.phase), (30, 1, 'learn'))

    def test_checkpoint_return_and_direct_lesson_selection(self):
        w = self.window()
        w.completed = [w.units[0].key]
        w.completed_checkpoints = ['unchanged']
        w.select_checkpoint(5)
        with patch.object(w, 'run_job'): w.start_random(all_topics=True)
        w.passed = True
        w.exit_random()
        self.assertEqual((w.phase, w.checkpoint_end), ('checkpoint_ready', 5))
        self.assertEqual(w.completed_checkpoints, ['unchanged'])
        with patch.object(w, 'run_job'): w.start_random(all_topics=True)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Yes): w.select_lesson(2)
        self.assertEqual((w.phase, w.index), ('learn', 2))
        self.assertIsNone(w.random_return)
        self.assertFalse(w.random_all_topics)

    def test_no_completed_units_and_declined_entry_leave_learning_unchanged(self):
        w = self.window()
        w.start_random(all_topics=True)
        self.assertEqual(w.phase, 'learn')
        self.assertIsNone(w.random_return)
        self.assertFalse(w.all_random_action.isEnabled())
        w.completed = [w.units[0].key]
        w.mission = make_mission(w.units[0].key, 4242)
        with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.No): w.start_random(all_topics=True)
        self.assertEqual(w.phase, 'learn')
        self.assertIsNone(w.random_return)


if __name__ == '__main__': unittest.main()
