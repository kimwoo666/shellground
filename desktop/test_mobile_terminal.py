"""Android VT adapter contract, using the same existing pyte dependency."""
import base64
import importlib.util
import json
from pathlib import Path
import unittest

_SOURCE = Path(__file__).resolve().parents[1] / 'android/app/src/main/python/linux_terminal.py'


@unittest.skipUnless(importlib.util.find_spec('pyte'), 'Requires actual pyte')
class MobileTerminalTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('android_linux_terminal_test', _SOURCE)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.terminal = module.Terminal(30, 6)

    def feed(self, data):
        self.terminal.feed(base64.b64encode(data).decode())

    def test_partial_utf8_color_cursor_and_erase(self):
        raw = '\x1b[32m한글\x1b[0m'.encode()
        for byte in raw: self.feed(bytes([byte]))
        frame = json.loads(self.terminal.frame())
        self.assertEqual(frame['rows'][0][0][1:3], ['한', 'green'])
        self.assertEqual(frame['rows'][0][1][:2], [2, '글'])
        self.feed(b'\r\x1b[2Kready')
        self.assertEqual(self.terminal.text().splitlines()[0], 'ready')
        self.assertEqual(json.loads(self.terminal.frame())['cursor'], [5, 0, True])

    def test_background_output_does_not_move_history_view(self):
        self.feed(''.join(f'line{i}\r\n' for i in range(12)).encode())
        self.terminal.scroll(-4)
        before = json.loads(self.terminal.frame())
        self.feed(b'new output\r\n')
        after = json.loads(self.terminal.frame())
        self.assertEqual(before['top'], after['top'])
        self.assertEqual(before['rows'], after['rows'])
        self.assertFalse(after['cursor'][2])
        self.terminal.live()
        self.assertTrue(json.loads(self.terminal.frame())['cursor'][2])

    def test_history_is_bounded_and_copy_includes_history(self):
        self.feed(''.join(f'line{i}\r\n' for i in range(1200)).encode())
        text = self.terminal.text()
        self.assertLessEqual(len(text.splitlines()), 1006)
        self.assertNotIn('line0\n', text)
        self.assertIn('line1199', text)
        self.terminal.scroll(-100000)
        frame = json.loads(self.terminal.frame())
        self.assertEqual(frame['top'], frame['first'])

    def test_resize_limits_and_vt_query_reply(self):
        self.terminal.resize(40, 8)
        self.feed(b'abc\x1b[6n')
        frame = json.loads(self.terminal.frame())
        self.assertEqual(base64.b64decode(frame['reply']), b'\x1b[1;4R')
        self.assertEqual(json.loads(self.terminal.frame())['reply'], '')
        with self.assertRaises(ValueError): self.terminal.resize(10000, 8)
        with self.assertRaises(ValueError): self.terminal.feed('!' * 400000)


if __name__ == '__main__': unittest.main()
