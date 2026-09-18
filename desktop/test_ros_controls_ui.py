import unittest
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from native_app import create_application
from terminal_widget import TerminalWidget


class RosControlKeyboardTests(unittest.TestCase):
    def test_native_terminal_forwards_control_keys_without_a_newline(self):
        app, _, mono = create_application(); widget = TerminalWidget(mono)
        received = []; widget.input_bytes.connect(received.append)
        widget.connected = True; widget.show(); widget.setFocus(); app.processEvents()
        try:
            for key in (Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Right, Qt.Key.Key_Left, Qt.Key.Key_Space):
                QTest.keyClick(widget, key)
            QTest.keyClick(widget, Qt.Key.Key_C, Qt.KeyboardModifier.ControlModifier)
            self.assertEqual(received, [b'\x1b[A', b'\x1b[B', b'\x1b[C', b'\x1b[D', b' ', b'\x03'])
        finally:
            widget.close(); widget.deleteLater(); app.processEvents()


if __name__ == '__main__': unittest.main()
