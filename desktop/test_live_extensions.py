"""Real Linux/Docker/package exercises; explicit dedicated guest required."""
import base64
import os
import socket
import json
import queue
import re
import time
import unittest

from checkpoints import make_checkpoint
from missions import make_mission
from real_lessons import adapt_real_mission
from real_vm import GuestChannel


@unittest.skipUnless(os.environ.get('SHELLGROUND_LIVE_GUEST') == '1', 'Dedicated guest required')
class LiveExtensionTests(unittest.TestCase):
    def test_large_guest_reply_remains_a_complete_frame(self):
        result = self.channel.request('exec', argv=['python3', '-c', 'print("x" * 100000)'])
        self.assertEqual(base64.b64decode(result['out']), b'x' * 100000 + b'\n')

    @classmethod
    def setUpClass(cls):
        connection = socket.create_connection(('127.0.0.1', 19473), timeout=10)
        connection.settimeout(None)
        cls.channel = GuestChannel(connection)
        assert cls.channel.request('status')['guest'] == 'shellground'

    @classmethod
    def tearDownClass(cls):
        cls.channel.close()

    def prepare(self, key, practice=0):
        self.mission = adapt_real_mission(make_mission('sim_' + key, 1234, practice))
        self.channel.request('prepare', timeout=90, mission=self.mission.payload())
        self.terminal = self.channel.open_terminal(self.mission.start)
        time.sleep(.15)
        return self.mission

    def command(self, text):
        # Short stop timeout speeds automated tests; the learner still executes
        # the real unmodified Docker CLI and may use any valid timeout option.
        text = text.replace('docker stop ', 'docker stop -t 1 ').replace('sudo apt install tree', 'sudo apt install -y tree')
        result = self.channel.request('exec', timeout=65, run_timeout=60,
            cwd=self.mission.start, argv=['/bin/bash', '-c', 'set -e\n' + text])
        self.assertEqual(result['code'], 0, base64.b64decode(result['err']).decode())
        return base64.b64decode(result['out']).decode()

    def send(self, text):
        self.channel.send({'action': 'input', 'session': self.terminal.sid,
                           'data': base64.b64encode(text.encode()).decode()})

    def wait_prompt(self, timeout=25):
        deadline = time.monotonic() + timeout
        output = b''
        while time.monotonic() < deadline:
            try:
                line = self.terminal.queue.get(timeout=.2)
            except queue.Empty:
                continue
            if line is None:
                self.fail('Terminal closed before prompt')
            output += base64.b64decode(json.loads(line)['output'])
            clean = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output)
            if re.search(rb'learner@lab:[^\r\n]*\$ ', clean):
                return output
        self.fail('No shell prompt: ' + output.decode(errors='replace')[-1200:])

    def solve_in_terminal(self, solution):
        # Type a new line only after Bash regains the terminal. sudo/apt can
        # flush type-ahead input when restoring terminal settings.
        self.wait_prompt()
        for command in solution.splitlines():
            self.send(command + '\r')
            self.wait_prompt()

    def grade(self):
        return self.channel.request('grade', timeout=60, mission=self.mission.payload(), session=self.terminal.sid)

    def assert_passes_eventually(self, timeout=8):
        deadline = time.monotonic() + timeout
        result = None
        while time.monotonic() < deadline:
            result = self.grade()
            if result['passed']:
                return
            time.sleep(.15)
        self.fail(str(result))

    def test_actual_environment_scripts_and_jobs(self):
        for key in ('env', 'author', 'jobs'):
            for practice in (0, 2):
                with self.subTest(key=key, practice=practice):
                    mission = self.prepare(key, practice)
                    self.assertFalse(self.grade()['passed'])
                    self.solve_in_terminal(mission.solution)
                    self.assert_passes_eventually()

    def test_actual_offline_apt(self):
        mission = self.prepare('apt', 2)
        self.assertFalse(self.grade()['passed'])
        self.command(mission.solution)
        self.assert_passes_eventually()

    def test_actual_docker_lifecycle_and_images(self):
        for key in ('images', 'run', 'lifecycle', 'exec', 'cleanup', 'update', 'tag', 'commit', 'save', 'limits'):
            with self.subTest(key=key):
                mission = self.prepare(key, 2)
                self.assertFalse(self.grade()['passed'])
                self.command(mission.solution)
                self.assert_passes_eventually()

    def test_pull_alone_does_not_replace_container(self):
        mission = self.prepare('update')
        self.command('docker pull ' + mission.review['registry']['ubuntu'])
        self.assertFalse(self.grade()['passed'])
        self.command(mission.solution)
        self.assert_passes_eventually()

    def test_save_without_load_cannot_claim_restore(self):
        mission = self.prepare('save')
        self.command('docker save -o images.tar ' + mission.review['registry']['ubuntu'])
        self.assertFalse(self.grade()['passed'])
        self.command(mission.solution)
        self.assert_passes_eventually()

    def test_actual_five_unit_checkpoints(self):
        for end in (30, 35, 40):
            with self.subTest(end=end):
                self.mission = adapt_real_mission(make_checkpoint(end, 1234, mode='simulation'))
                self.channel.request('prepare', timeout=90, mission=self.mission.payload())
                self.terminal = self.channel.open_terminal(self.mission.start)
                self.assertFalse(self.grade()['passed'])
                if end == 30:
                    solution = self.mission.solution.replace('sudo apt install tree', 'sudo apt install -y tree')
                    self.solve_in_terminal(solution)
                    self.assert_passes_eventually(20)
                else:
                    self.command(self.mission.solution)
                    self.assert_passes_eventually()


if __name__ == '__main__':
    unittest.main()
