"""Opt-in acceptance test: Qt actions, real Conda PTY, grading and cleanup.

Run only against the separately exported course-validated guest. All progress
goes to a temporary profile; the real VM transport owns a disposable overlay.
"""
import json
import os
from pathlib import Path
import tempfile
import time
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from PySide6.QtWidgets import QApplication
from conda_app import CondaWindow
from conda_teaching.engine import conda_runtime
from study_window import StudyWindow


@unittest.skipUnless(os.environ.get('SHELLGROUND_TEST_REAL_CONDA') == '1',
                     'Requires explicit opt-in and the validated real Conda VM')
class RealCondaUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        conda_runtime()  # Fail, do not silently skip a requested acceptance run.
        cls.app = QApplication.instance() or QApplication([])

    def wait_for(self, predicate, timeout=150):
        deadline = time.monotonic() + timeout
        while not predicate() and time.monotonic() < deadline:
            self.app.processEvents()
            time.sleep(.02)
        if not predicate():
            from shiboken6 import isValid
            detail = (self.window.status.text() + '\nTerminal:\n' + self.screen()
                      if isValid(self.window) else 'The study page has already closed')
            self.fail('UI operation timed out: ' + detail)

    def screen(self):
        return '\n'.join(self.window.terminal.screen.display)

    def prompt(self):
        lines = [line.rstrip() for line in self.window.terminal.screen.display if line.strip()]
        return lines[-1] if lines else ''

    def test_actual_terminal_retry_progress_and_close(self):
        with tempfile.TemporaryDirectory(prefix='shellground-conda-ui-test-') as profile:
            progress = Path(profile) / 'conda-progress-v1.json'
            host = StudyWindow('sans', 'monospace', Path(profile) / 'progress-v3.json', mode='conda')
            window = self.window = host.pages['conda']
            process = None
            session = None
            try:
                window.index = next(i for i, unit in enumerate(window.units)
                                    if unit['key'] == 'conda_activate')
                window.phase, window.variant = 'practice1', 1
                window.render()
                host.show()
                self.assertIs(window.window(), host)
                self.assertFalse(window.isWindow())
                window.try_button.click()
                self.wait_for(lambda: not window.busy)
                self.assertTrue(window.terminal.connected, window.feedback.toPlainText()
                                if hasattr(window.feedback, 'toPlainText') else window.status.text())
                process, session = window.engine.process, window.engine.session_dir
                self.assertIsNone(process.poll())
                # A prefix-based activation legitimately displays its full path.
                self.wait_for(lambda: 'sg-reading)' in self.prompt() and self.prompt().endswith('$'), 15)
                original_session = window.engine.bridge.sid

                window.grade_button.click()
                self.wait_for(lambda: not window.busy)
                self.assertFalse(window.solved)
                self.assertEqual(window.tabs.currentIndex(), 1)
                self.assertTrue(window.terminal.connected)
                self.assertNotIn('conda_activate:1', window.progress.data['passed'])

                window.tabs.setCurrentIndex(0)
                window.terminal.input_bytes.emit(b'conda activate sg-writing\r')
                self.wait_for(lambda: 'sg-writing)' in self.prompt() and self.prompt().endswith('$'), 20)
                window.grade_button.click()
                self.wait_for(lambda: not window.busy)
                self.assertTrue(window.solved)
                self.assertEqual(window.engine.bridge.sid, original_session)
                self.assertIn('conda_activate:1', window.progress.data['passed'])
                self.assertNotIn('conda_activate', window.progress.data['completed'])

                window.terminal.input_bytes.emit(
                    b"conda export -n sg-writing --from-history --format=environment-yaml --file writing.yml && printf '%s\\n' __FILE_'READY__'\r")
                self.wait_for(lambda: '__FILE_READY__' in self.screen(), 20)
                window.tabs.setCurrentIndex(2)
                self.wait_for(lambda: not window.busy and 'name: sg-writing' in window.file_text.toPlainText(), 20)
                self.assertEqual(window.file_picker.currentText(), 'writing.yml')
                self.assertTrue(window.file_text.isReadOnly())

                window.next_button.click()
                self.wait_for(lambda: not window.busy)
                self.assertEqual((window.phase, window.variant), ('practice2', 2))
                self.wait_for(lambda: 'sg-focus)' in self.prompt() and self.prompt().endswith('$'), 15)
                window.terminal.input_bytes.emit(b'conda deactivate\r')
                # Wait for the command's fresh prompt, not an old prompt line.
                self.wait_for(lambda: self.prompt().endswith('$') and 'sg-focus)' not in self.prompt(), 20)
                window.grade_button.click()
                self.wait_for(lambda: not window.busy)
                self.assertTrue(window.solved)
                self.assertIn('conda_activate', window.progress.data['completed'])
                self.assertIn('[완료]', window.list.item(window.index).text())
                self.assertEqual(window.tabs.currentIndex(), 1)
                screenshot = os.environ.get('SHELLGROUND_CONDA_UI_CAPTURE')
                if screenshot:
                    self.app.processEvents()
                    self.assertTrue(host.grab().save(screenshot))
            finally:
                # The room is hidden but its actual guest still belongs to
                # this one application window and must be stopped with it.
                if not window.busy:
                    host.switch_mode('python')
                host.close()
                self.wait_for(lambda: window.closed, 30)
                self.wait_for(lambda: not host.isVisible(), 30)
                for reader in window.readers:
                    self.assertTrue(reader.wait(3000), 'Terminal reader survived close')
                if process is not None:
                    self.assertIsNotNone(process.poll(), 'Owned VM supervisor survived close')
                if session is not None:
                    self.assertFalse(session.exists(), 'Temporary practice overlay survived close')
            saved = json.loads(progress.read_text())
            self.assertIn('conda_activate', saved['completed'])
            self.assertEqual(saved['resume']['phase'], 'practice2')
            self.assertNotIn('conda activate sg-writing', progress.read_text())


if __name__ == '__main__':
    unittest.main()
