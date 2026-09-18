"""Explicit integration test against the dedicated image-builder VM only."""
import base64
import json
import os
from pathlib import Path
import queue
import socket
import time
import unittest

from missions import make_mission
from real_vm import GuestChannel


class LiveGuestTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if os.environ.get('SHELLGROUND_LIVE_GUEST') != '1':
            raise unittest.SkipTest('Explicit SHELLGROUND_LIVE_GUEST=1 required for private-VM integration')
        connection = socket.create_connection(('127.0.0.1', 19473), timeout=5)
        connection.settimeout(None)
        cls.channel = GuestChannel(connection)
        status = cls.channel.request('status')
        if status.get('guest') != 'shellground' or not status.get('nano'):
            raise RuntimeError('Dedicated guest with real nano required')

    @classmethod
    def tearDownClass(cls):
        cls.channel.close()

    def send(self, terminal, data):
        self.channel.send({'action': 'input', 'session': terminal.sid, 'data': base64.b64encode(data).decode()})

    def drain(self, terminal, seconds=.7):
        out = b''
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline:
            try:
                line = terminal.queue.get(timeout=.1)
            except queue.Empty:
                continue
            if line is None:
                break
            out += base64.b64decode(json.loads(line)['output'])
        return out

    def test_real_nano_save_exit_grade_and_continue(self):
        mission = make_mission('edit', 4242)
        self.channel.request('prepare', mission=mission.payload())
        terminal = self.channel.open_terminal(mission.start)
        from native_app import create_application
        from terminal_widget import TerminalWidget
        app, _, mono = create_application()
        widget = TerminalWidget(mono)
        widget.resize(1000, 620)
        widget.show()
        app.processEvents()
        self.channel.send({'action': 'resize', 'session': terminal.sid,
                           'size': [widget.screen.lines, widget.screen.columns]})
        output = self.drain(terminal)
        result = self.channel.request('grade', mission=mission.payload(), session=terminal.sid, output='')
        self.assertFalse(result['passed'])
        self.send(terminal, ('nano ' + mission.target + '/note.txt\r').encode())
        nano = self.drain(terminal, 2)
        self.assertIn(b'GNU nano', nano)
        # Render actual nano output through our terminal widget, not a mock editor.
        widget.feed(output + nano)
        app.processEvents()
        widget.grab().save('/tmp/shellground-real-nano.png')
        widget.hide()
        self.send(terminal, b'\x0bstatus=ready\x0f')
        output += nano + self.drain(terminal)
        self.send(terminal, b'\r')
        output += self.drain(terminal)
        self.send(terminal, b'\x18')
        output += self.drain(terminal)
        result = self.channel.request('grade', mission=mission.payload(), session=terminal.sid, output=output.decode(errors='replace'))
        self.assertTrue(result['passed'], result)

    def test_terminals_share_files_but_not_environment(self):
        mission = make_mission('mkdir', 5656)
        self.channel.request('prepare', mission=mission.payload())
        first = self.channel.open_terminal(mission.start)
        second = self.channel.open_terminal(mission.start)
        self.drain(first); self.drain(second)
        self.send(first, b'export ONLY_FIRST=yes; printf shared > shared.txt\r')
        self.drain(first)
        self.send(second, b'cat shared.txt; printf "\\nVALUE=[%s]\\n" "$ONLY_FIRST"\r')
        output = self.drain(second)
        self.assertIn(b'shared', output)
        self.assertIn(b'VALUE=[]', output)


if __name__ == '__main__':
    unittest.main()
