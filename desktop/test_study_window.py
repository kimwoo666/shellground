"""Real Qt mode navigation and editor keys; no host desktop control."""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QLabel
from native_app import create_application
from study_window import StudyWindow


class StudyWindowTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def setUp(self):
        self.folder = tempfile.TemporaryDirectory()
        self.path = Path(self.folder.name) / 'progress-v3.json'
        self.window = StudyWindow(self.ui, self.mono, self.path, mode='simulation')
        self.window.show()
        self.app.processEvents()

    def wait_for(self, condition, timeout=15):
        deadline = time.monotonic() + timeout
        while not condition() and time.monotonic() < deadline:
            self.app.processEvents()
            QTest.qWait(10)
        self.app.processEvents()
        self.assertTrue(condition())

    def tearDown(self):
        self.window.close()
        self.wait_for(lambda: not self.window.isVisible())
        self.window.deleteLater()
        self.app.processEvents()
        self.folder.cleanup()

    def python_page(self):
        self.window.pages['linux'].open_python()
        self.app.processEvents()
        return self.window.pages['python']

    def test_modes_are_one_window_and_keep_editor_and_progress(self):
        host = self.window
        linux = host.pages['linux']
        python = self.python_page()
        python.advance()
        python.editor.setPlainText('remember_me = 42')
        host.switch_mode('linux')
        self.assertIs(host.stack.currentWidget(), linux)
        self.assertTrue(linux.simulation_timer.isActive())
        host.switch_mode('python')
        self.assertIs(host.stack.currentWidget(), python)
        self.assertFalse(linux.simulation_timer.isActive())
        self.assertIs(python.window(), host)
        self.assertIs(linux.window(), host)
        self.assertFalse(python.isWindow())
        self.assertEqual(python.step, 1)
        self.assertEqual(python.editor.toPlainText(), 'remember_me = 42')
        visible = [w for w in self.app.topLevelWidgets() if w.isVisible()]
        self.assertEqual(visible, [host])
        saved = self.path.with_name('python-progress-v1.json').read_text()
        self.assertEqual(json.loads(saved)['resume']['step'], 1)
        self.assertNotIn('remember_me', saved)
        capture = os.environ.get('SHELLGROUND_STUDY_UI_CAPTURE')
        if capture:
            self.assertTrue(host.grab().save(capture))

    def test_shift_enter_executes_once_without_newline_and_enter_still_indents(self):
        page = self.python_page()
        for key, modifiers in ((Qt.Key.Key_Return, Qt.KeyboardModifier.ShiftModifier),
                (Qt.Key.Key_Enter, Qt.KeyboardModifier.ShiftModifier | Qt.KeyboardModifier.KeypadModifier)):
            source = 'runs = globals().get("runs", 0) + 1\nprint("RAN", runs)'
            page.editor.setPlainText(source)
            page.editor.setFocus()
            QTest.keyClick(page.editor, key, modifiers)
            self.wait_for(lambda: not page.busy)
            self.assertEqual(page.editor.toPlainText(), source)
        self.assertIn('RAN 1', page.output.toPlainText())
        self.assertIn('RAN 2', page.output.toPlainText())
        self.assertNotIn('RAN 3', page.output.toPlainText())
        page.editor.setPlainText('if True:')
        page.editor.moveCursor(page.editor.textCursor().MoveOperation.End)
        QTest.keyClick(page.editor, Qt.Key.Key_Return)
        self.assertEqual(page.editor.toPlainText(), 'if True:\n    ')

    def test_only_active_mode_handles_function_key(self):
        page = self.python_page()
        linux = self.window.pages['linux']
        before = (linux.phase, linux.learning_step)
        page.editor.setFocus()
        self.app.processEvents()
        QTest.keyClick(page.editor, Qt.Key.Key_F6)
        self.app.processEvents()
        self.assertEqual(page.step, 1)
        self.assertEqual((linux.phase, linux.learning_step), before)

    def test_conda_navigation_embeds_and_reuses_room_without_starting_vm(self):
        page = self.python_page()
        page.open_conda()
        conda = self.window.pages['conda']
        self.assertIs(conda.window(), self.window)
        self.assertFalse(conda.isWindow())
        self.assertFalse(conda.terminal.connected)
        self.window.switch_mode('python')
        page.open_conda()
        self.assertIs(self.window.stack.currentWidget(), conda)

    def test_close_stops_hidden_python_process(self):
        page = self.python_page()
        page.editor.setPlainText('answer = 42')
        page.run_code()
        self.wait_for(lambda: not page.busy)
        process = page.engine.process
        self.assertIsNone(process.poll())
        self.window.switch_mode('linux')
        self.window.close()
        self.wait_for(lambda: not self.window.isVisible())
        self.assertIsNotNone(process.poll())
        self.assertFalse(self.window.pages)

    def test_running_python_is_cancelled_when_shared_window_closes(self):
        page = self.python_page()
        page.editor.setPlainText('while True:\n    pass')
        page.run_code()
        self.wait_for(lambda: page.engine.process is not None)
        process = page.engine.process
        self.window.close()
        self.wait_for(lambda: not self.window.isVisible())
        self.assertIsNotNone(process.poll())
        self.assertFalse(self.window.pages)

    def test_close_waits_for_queued_worker_finish_even_after_thread_stops(self):
        page=self.python_page()
        page.job(lambda:'finished before UI dispatch',lambda value:page.output.setPlainText(value))
        self.assertTrue(page.worker.wait(3000))
        self.assertTrue(page.busy)
        self.assertFalse(page.worker.isRunning())
        self.window.close()
        self.wait_for(lambda:not self.window.isVisible())
        self.assertFalse(self.window.pages)

    def test_failed_cleanup_can_be_retried_without_orphaning_hidden_room(self):
        page = self.python_page()
        linux = self.window.pages['linux']
        with patch.object(linux.engine, 'close', side_effect=[RuntimeError('retry cleanup'), None]):
            self.window.close()
            self.wait_for(lambda: not self.window._closing)
            self.assertTrue(self.window.isVisible())
            self.assertIs(self.window.stack.currentWidget(), linux)
            self.assertNotIn('python', self.window.pages)
            self.assertTrue(page.study_closed)
            self.window.close()
            self.wait_for(lambda: not self.window.isVisible())

    def test_busy_mode_is_not_hidden_by_navigation(self):
        page = self.python_page()
        page.busy = True
        try:
            self.window.mode_tabs.setCurrentIndex(0)
            self.assertIs(self.window.stack.currentWidget(), page)
            self.assertEqual(self.window.mode_tabs.currentIndex(), 1)
        finally:
            page.busy = False

    def test_navigation_does_not_overwrite_unmodified_linux_progress(self):
        # Simulate another writer or a corrupted file after this room loaded.
        # A navigation-only action has no new Linux completion to persist.
        original = '{preserve this existing progress for recovery'
        self.path.write_text(original)
        self.python_page()
        self.window.switch_mode('linux')
        self.window.close()
        self.wait_for(lambda: not self.window.isVisible())
        self.assertEqual(self.path.read_text(), original)

    def test_failed_mode_load_keeps_current_room(self):
        page = self.python_page()
        with patch.object(self.window, '_page_factory', side_effect=RuntimeError('missing runtime')), \
                patch('study_window.QMessageBox.warning') as warning:
            self.window.switch_mode('conda')
        warning.assert_called_once()
        self.assertEqual(self.window.active_mode, 'python')
        self.assertEqual(self.window.mode_tabs.currentIndex(), 1)
        self.assertIs(self.window.stack.currentWidget(), page)

    def test_python_header_has_no_environment_warning_banner(self):
        page = self.python_page()
        labels = '\n'.join(widget.text() for widget in page.findChildren(QLabel))
        self.assertNotIn('실제 CPython', labels)
        self.assertNotIn('별도 프로세스', labels)
        self.assertTrue(any(action.text() == '사용 안내' for action in page.menuBar().actions()))


if __name__ == '__main__':
    unittest.main()
