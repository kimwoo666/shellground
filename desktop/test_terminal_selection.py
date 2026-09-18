"""Native mouse selection across scrollback, including stationary edge drag."""
import unittest
from PySide6.QtCore import Qt, QPointF, QEvent
from PySide6.QtGui import QMouseEvent, QFocusEvent
from PySide6.QtTest import QTest
from native_app import create_application
from terminal_widget import TerminalWidget


class TerminalSelectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app, _, cls.mono = create_application()

    def setUp(self):
        self.t = TerminalWidget(self.mono)
        self.t.resize(700, 260)
        self.t.show()
        self.app.processEvents()
        self.t.connected = True
        self.t.feed(''.join(f'line {n:04d}\r\n' for n in range(80)).encode())

    def tearDown(self):
        self.t.stop_drag()
        self.t.deleteLater()
        self.app.processEvents()

    def mouse(self, kind, x, y):
        event = QMouseEvent(kind, QPointF(x, y), QPointF(x, y),
                           Qt.MouseButton.LeftButton if kind != QEvent.Type.MouseMove else Qt.MouseButton.NoButton,
                           Qt.MouseButton.NoButton if kind == QEvent.Type.MouseButtonRelease else Qt.MouseButton.LeftButton,
                           Qt.KeyboardModifier.NoModifier)
        self.app.sendEvent(self.t, event)

    def press(self, row=2, col=0):
        self.mouse(QEvent.Type.MouseButtonPress, 8 + col*self.t.cell_w, 8 + row*self.t.cell_h)

    def move(self, x, y): self.mouse(QEvent.Type.MouseMove, x, y)

    def release(self, x, y): self.mouse(QEvent.Type.MouseButtonRelease, x, y)

    def test_upward_drag_keeps_absolute_anchor_and_copies_hidden_lines(self):
        self.press()
        anchor = self.t.selection_start
        self.move(8, -100)
        self.assertTrue(self.t.drag_scroll.isActive())
        for _ in range(100): self.t.autoscroll_selection()
        self.assertEqual(self.t.viewport_top(), 0)
        self.assertEqual(self.t.selection_start, anchor)
        self.assertFalse(self.t.drag_scroll.isActive())
        self.release(8, -100)
        self.t.copy_selection()
        copied = self.app.clipboard().text().splitlines()
        self.assertEqual(copied[0], 'line 0000')
        self.assertIn('line 0040', copied)
        self.assertGreater(len(copied), self.t.screen.lines)

    def test_downward_drag_to_live_end_and_reverse_direction(self):
        self.t.scroll_history(10000)
        self.press(row=0)
        anchor = self.t.selection_start
        self.move(300, self.t.height() + 100)
        for _ in range(100): self.t.autoscroll_selection()
        self.assertEqual(self.t.viewport_top(), self.t.screen.history_serial)
        self.assertEqual(self.t.selection_start, anchor)
        self.assertFalse(self.t.drag_scroll.isActive())
        self.t.copy_selection()
        self.assertIn('line 0000', self.app.clipboard().text())
        self.assertIn('line 0079', self.app.clipboard().text())
        self.move(8, -30)
        self.t.autoscroll_selection()
        self.assertLess(self.t.viewport_top(), self.t.screen.history_serial)
        self.assertEqual(self.t.selection_start, anchor)

    def test_stationary_edge_uses_timer_and_release_stops_it(self):
        self.press()
        before = self.t.viewport_top()
        self.move(20, -30)
        QTest.qWait(180)
        self.assertLess(self.t.viewport_top(), before)
        self.release(20, -30)
        after = self.t.viewport_top()
        self.assertFalse(self.t.drag_scroll.isActive())
        QTest.qWait(160)
        self.assertEqual(self.t.viewport_top(), after)

    def test_new_output_does_not_move_a_selection(self):
        self.press(row=0)
        self.move(200, 8 + 2*self.t.cell_h)
        self.release(200, 8 + 2*self.t.cell_h)
        self.t.copy_selection()
        copied, top = self.app.clipboard().text(), self.t.viewport_top()
        self.t.feed(b'new output\r\n' * 50)
        self.t.copy_selection()
        self.assertEqual(self.app.clipboard().text(), copied)
        self.assertEqual(self.t.viewport_top(), top)

    def test_idle_center_focus_loss_hide_and_reset_stop_scrolling(self):
        self.assertFalse(self.t.drag_scroll.isActive())
        self.press()
        self.move(20, -50)
        self.move(20, 80)
        self.assertFalse(self.t.drag_scroll.isActive())
        self.move(20, -50)
        self.t.focusOutEvent(QFocusEvent(QEvent.Type.FocusOut))
        self.assertFalse(self.t.drag_scroll.isActive())
        self.press(); self.move(20, -50); self.t.hide()
        self.assertFalse(self.t.drag_scroll.isActive())
        self.t.show(); self.app.processEvents()
        self.press(); self.move(20, -50); self.t.reset()
        self.assertFalse(self.t.drag_scroll.isActive())
        self.assertIsNone(self.t.selection_start)

    def test_select_all_korean_and_history_limit(self):
        self.t.feed('한글 공백 파일\r\n'.encode())
        QTest.keyClick(self.t, Qt.Key.Key_A, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        QTest.keyClick(self.t, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.ShiftModifier)
        self.assertIn('line 0000', self.app.clipboard().text())
        self.assertIn('한글 공백 파일', self.app.clipboard().text())
        self.t.feed(b'overflow\r\n' * 3100)
        self.t.copy_selection()  # Entire selected range was evicted; no crash/stale indexing.
        self.t.select_all(); self.t.copy_selection()
        self.assertNotIn('line 0000', self.app.clipboard().text())
        self.assertIn('overflow', self.app.clipboard().text())
        self.assertLessEqual(len(self.app.clipboard().text().splitlines()), 3000 + self.t.screen.lines)


if __name__ == '__main__': unittest.main()
