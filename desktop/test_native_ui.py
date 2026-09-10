"""Offscreen Qt tests; no desktop screen capture or host UI control."""
import tempfile
import os
import time
import unittest
from pathlib import Path
from unittest.mock import patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QRawFont
from PySide6.QtTest import QTest
from native_app import create_application, Window
from missions import UNITS
from terminal_widget import TerminalWidget


class NativeUITests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, cls.ui, cls.mono = create_application()

    def wait_job(self, window):
        end = time.monotonic() + 5
        while window.busy and time.monotonic() < end:
            self.app.processEvents()
            time.sleep(.005)
        self.assertFalse(window.busy)

    def test_korean_glyphs_and_terminal_cells(self):
        font = QRawFont.fromFont(QFont(self.ui, 12))
        for char in '리눅스명령어연습단계활용문제':
            self.assertTrue(font.supportsCharacter(ord(char)), char)
        terminal = TerminalWidget(self.mono)
        terminal.feed('한글 abc\r\n'.encode())
        self.assertEqual(terminal.screen.buffer[0][0].data, '한')
        self.assertEqual(terminal.screen.buffer[0][1].data, '')
        terminal.feed(b'\x1b[31mERROR\x1b[0m')
        self.assertEqual(terminal.screen.buffer[1][0].fg, 'red')

    def test_raw_keys_and_bracketed_paste(self):
        terminal = TerminalWidget(self.mono)
        terminal.connected = True
        events = []
        terminal.input_bytes.connect(events.append)
        QTest.keyClick(terminal, Qt.Key.Key_Tab)
        QTest.keyClick(terminal, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
        QTest.keyClick(terminal, Qt.Key.Key_Up)
        self.assertEqual(events, [b'\t', b'\x03', b'\x1b[A'])
        terminal.feed(b'\x1b[?2004h')
        self.app.clipboard().setText('echo first\necho second')
        terminal.paste()
        self.assertEqual(events[-1], b'\x1b[200~echo first\necho second\x1b[201~')

    def test_progression_requires_two_practices_and_persists(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.json'
            window = Window(self.ui, self.mono, path)
            self.assertEqual(window.phase, 'learn')
            self.assertFalse(window.random_button.isEnabled())
            window.select_lesson(5)
            self.assertEqual(window.index, 0)
            def launch(mission):
                window.mission, window.passed = mission, False
                window.terminal.connected = True
                window.update_controls()
            window.launch = launch
            window.engine.rpc = lambda action, mission: {'passed': True, 'checks': [{'label': 'result', 'passed': True}]}
            window.advance()
            self.assertEqual(window.phase, 'example')
            window.grade(); self.wait_job(window)
            self.assertEqual(window.completed, [])
            window.advance()
            self.assertEqual((window.phase, window.practice_number), ('practice', 1))
            window.grade(); self.wait_job(window)
            self.assertEqual(window.completed, [])
            window.advance()
            window.grade(); self.wait_job(window)
            self.assertEqual(window.completed, [UNITS[0].key])
            self.assertTrue(path.is_file())
            window.start_random()
            self.assertEqual(window.mission.kind, UNITS[0].key)
            restored = Window(self.ui, self.mono, path)
            self.assertEqual(restored.completed, window.completed)
            window.deleteLater(); restored.deleteLater()
            self.app.processEvents()

    def test_corrupt_progress_and_worker_error(self):
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / 'progress.json'
            path.write_text('{bad', encoding='utf-8')
            window = Window(self.ui, self.mono, path)
            self.assertEqual(window.completed, [])
            def fail(log): raise RuntimeError('Docker unavailable')
            window.run_job(fail, lambda value: None)
            self.wait_job(window)
            self.assertIn('Docker unavailable', window.feedback.text())
            self.assertTrue(window.next_button.isEnabled())
            window.deleteLater(); self.app.processEvents()

    @unittest.skipUnless(os.environ.get('SHELLGROUND_INTEGRATION') == '1', 'Requires Docker')
    def test_real_terminal_through_native_learning_flow(self):
        with tempfile.TemporaryDirectory() as temporary:
            window = Window(self.ui, self.mono, Path(temporary) / 'progress.json')
            window.show()
            self.app.processEvents()
            def wait_for(predicate):
                end = time.monotonic() + 15
                while not predicate() and time.monotonic() < end:
                    self.app.processEvents()
                    time.sleep(.01)
                self.assertTrue(predicate(), window.feedback.text())
            try:
                for stage in range(3):
                    window.advance()
                    wait_for(lambda: not window.busy and window.terminal.connected)
                    wait_for(lambda: 'learner@lab:' in '\n'.join(window.terminal.screen.display))
                    QTest.keyClicks(window.terminal, 'cd ' + window.mission.source + '/docs')
                    QTest.keyClick(window.terminal, Qt.Key.Key_Return)
                    wait_for(lambda: '/docs$' in '\n'.join(window.terminal.screen.display))
                    window.grade()
                    wait_for(lambda: not window.busy)
                    self.assertTrue(window.passed, window.feedback.text())
                self.assertEqual(window.completed, ['navigate'])
            finally:
                window.generation += 1
                window.run_job(lambda log: window.engine.close(), lambda value: None)
                wait_for(lambda: not window.busy)
                for reader in window.readers: reader.wait(3000)
                window.hide(); window.deleteLater(); self.app.processEvents()


if __name__ == '__main__': unittest.main()
