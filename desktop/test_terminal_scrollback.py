"""Offscreen regression checks for browsing while VT output keeps arriving."""
import unittest
from PySide6.QtCore import Qt, QPoint, QPointF
from PySide6.QtGui import QInputMethodEvent, QWheelEvent
from PySide6.QtTest import QTest
from native_app import create_application
from terminal_widget import TerminalWidget


class ScrollbackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, _, cls.mono = create_application()

    def setUp(self):
        self.terminal = TerminalWidget(self.mono)
        self.terminal.connected = True
        self.terminal.feed(''.join(f'line {n:04d}\r\n' for n in range(80)).encode())

    def tearDown(self):
        self.terminal.deleteLater()
        self.app.processEvents()

    def text(self):
        return [''.join(row.get(c, self.terminal.screen.default_char).data
                        for c in range(self.terminal.screen.columns)).rstrip()
                for row in self.terminal.visible_lines()]

    def wheel(self, angle=0, pixels=0):
        event = QWheelEvent(QPointF(20, 20), QPointF(20, 20),
                            QPoint(0, pixels), QPoint(0, angle),
                            Qt.MouseButton.NoButton, Qt.KeyboardModifier.NoModifier,
                            Qt.ScrollPhase.NoScrollPhase, False)
        self.terminal.wheelEvent(event)

    def test_live_follows_but_wheel_anchor_survives_output_and_controls(self):
        t = self.terminal
        self.assertIsNone(t.view_top)
        t.feed(b'live first\r\n')
        self.assertIn('live first', self.text())
        self.wheel(angle=120)
        before = self.text()
        anchor = t.view_top
        for n in range(50):
            t.feed(f'new {n}\r\n'.encode())
            t.feed(b'\x1b[?25l\x1b[?25h')
        self.assertEqual(t.view_top, anchor)
        self.assertEqual(self.text(), before)
        self.assertIn('new 49', [line.rstrip() for line in t.screen.display])
        self.assertEqual(t.screen.history.position, t.screen.history.size)

    def test_paging_copy_and_return_to_bottom(self):
        t = self.terminal
        QTest.keyClick(t, Qt.Key.Key_PageUp, Qt.KeyboardModifier.ShiftModifier)
        before = self.text()
        t.selection_start, t.selection_end = (t.viewport_top(), 0), (t.viewport_top() + 1, 20)
        t.feed(b'more output\r\n')
        QTest.keyClick(t, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        self.assertEqual(self.app.clipboard().text(), '\n'.join(before[:2]))
        self.assertIsNotNone(t.view_top)
        QTest.keyClick(t, Qt.Key.Key_End, Qt.KeyboardModifier.ShiftModifier)
        self.assertIsNone(t.view_top)
        self.assertIn('more output', self.text())
        t.feed(b'latest\r\n')
        self.assertIn('latest', self.text())
        QTest.keyClick(t, Qt.Key.Key_PageUp, Qt.KeyboardModifier.ShiftModifier)
        QTest.keyClick(t, Qt.Key.Key_PageDown, Qt.KeyboardModifier.ShiftModifier)
        self.assertIsNone(t.view_top)

    def test_only_actual_input_returns_to_live_including_paste_and_ime(self):
        t = self.terminal
        sent = []
        t.input_bytes.connect(sent.append)
        t.scroll_history(12)
        QTest.keyPress(t, Qt.Key.Key_Shift)
        QTest.keyRelease(t, Qt.Key.Key_Shift)
        self.assertIsNotNone(t.view_top)
        QTest.keyClick(t, Qt.Key.Key_A)
        self.assertIsNone(t.view_top)
        self.assertEqual(sent[-1], b'a')
        t.scroll_history(12)
        self.app.clipboard().setText('')
        t.paste()
        self.assertIsNotNone(t.view_top)
        self.app.clipboard().setText('pwd')
        t.feed(b'\x1b[?2004h')
        t.paste()
        self.assertIsNone(t.view_top)
        self.assertEqual(sent[-1], b'\x1b[200~pwd\x1b[201~')
        t.scroll_history(12)
        event = QInputMethodEvent()
        event.setCommitString('한글')
        t.inputMethodEvent(event)
        self.assertIsNone(t.view_top)
        self.assertEqual(sent[-1], '한글'.encode())

    def test_history_limit_clamps_to_oldest_not_latest(self):
        t = self.terminal
        t.scroll_history(10000)
        t.feed(''.join(f'overflow {n}\r\n' for n in range(3100)).encode())
        self.assertEqual(len(t.screen.history.top), 3000)
        self.assertIsNotNone(t.view_top)
        self.assertEqual(t.view_top, t.screen.history_serial - 3000)
        self.assertTrue(self.text()[0].startswith('overflow '))
        self.assertNotIn('overflow 3099', self.text())

    def test_reset_and_explicit_history_clear_start_fresh(self):
        t = self.terminal
        t.scroll_history(12)
        t.feed(b'\x1b[3J')
        self.assertIsNone(t.view_top)
        self.assertEqual(len(t.screen.history.top), 0)
        t.feed(b'fresh\r\n' * 50)
        t.scroll_history(12)
        t.reset()
        self.assertIsNone(t.view_top)
        self.assertEqual(t.screen.history_serial, 0)
        self.assertTrue(all(not line for line in self.text()))

    def test_resize_and_touchpad_keep_browsing(self):
        t = self.terminal
        t.show()
        self.app.processEvents()
        self.wheel(pixels=20)
        anchor = t.view_top
        first_line = self.text()[0]
        self.wheel()  # Horizontal/zero vertical delta must not scroll down.
        self.assertEqual(t.view_top, anchor)
        t.resize(950, 450)
        self.app.processEvents()
        t.feed(b'after resize\r\n')
        self.assertEqual(t.view_top, anchor)
        self.assertEqual(self.text()[0], first_line)
        t.hide()
