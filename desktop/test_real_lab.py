"""Opt-in integration tests: SHELLGROUND_INTEGRATION=1 python -m unittest test_real_lab -v."""
import base64
import json
import os
import queue
import threading
import time
import unittest
from engine import LabEngine
from missions import UNITS, make_mission, random_mission


class CurriculumTests(unittest.TestCase):
    def test_generated_scenarios(self):
        for unit in UNITS:
            for seed in range(30):
                mission = make_mission(unit.key, seed)
                self.assertNotEqual(mission.start, mission.source)
                self.assertTrue(mission.solution)
                self.assertTrue(mission.prompt)
                self.assertEqual(mission, make_mission(unit.key, seed))

    def test_random_only_learned(self):
        with self.assertRaises(ValueError): random_mission([])
        for _ in range(50):
            self.assertEqual(random_mission(['navigate']).kind, 'navigate')
            self.assertEqual(random_mission(['navigate', 'workspace'], 'navigate').kind, 'workspace')


@unittest.skipUnless(os.environ.get('SHELLGROUND_INTEGRATION') == '1', 'Set SHELLGROUND_INTEGRATION=1 for Docker tests')
class RealLabTests(unittest.TestCase):
    def setUp(self):
        self.engine = LabEngine()
        self.engine.status()
        self.addCleanup(self.engine.close)

    def shell(self, command):
        return self.engine.command('exec', '-w', self.mission.start, self.engine.name, 'bash', '-c', command)

    def start(self, kind, seed=4242):
        self.mission = make_mission(kind, seed)
        self.engine.start(self.mission)
        return self.mission

    def test_every_goal_rejects_untouched_and_accepts_real_results(self):
        for unit in UNITS:
            if unit.key == 'navigate': continue
            with self.subTest(kind=unit.key):
                mission = self.start(unit.key)
                self.assertFalse(self.engine.rpc('grade', mission)['passed'])
                self.shell(mission.solution)
                result = self.engine.rpc('grade', mission)
                self.assertTrue(result['passed'], result)

    def test_list_option_order_relative_paths_and_missing_hidden_files(self):
        m = self.start('recursive')
        self.shell(f'ls -lR {m.source} > {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        self.shell(f'ls -al {m.source} > {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        for command in [f'ls -Ral {m.source} > {m.report}',
                        f'cd {m.source} && ls -laR > {m.report}',
                        f'cd {m.source} && ls --all -l --recursive . > {m.report}',
                        f'cd /home/learner && ls -l -R -a {m.source.removeprefix("/home/learner/")} > {m.report}']:
            self.shell(command)
            result = self.engine.rpc('grade', m)
            self.assertTrue(result['passed'], (command, result))
        self.shell(f'rm {m.source}/.env && ls -alR {m.source} > {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'], 'Deleting source data must not change the grading oracle')

    def test_wrong_name_corrupt_download_and_fifo_fail(self):
        m = self.start('curl')
        self.shell(f'curl -fsS {m.url} -o {m.target}/wrong-name')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        self.shell(f'echo corrupted > {m.target}/received-{m.artifact}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        m = self.start('list')
        self.shell(f'mkfifo {m.report}')
        self.assertFalse(self.engine.rpc('grade', m)['passed'])

    def test_download_all_formats_both_tools(self):
        for artifact in ['toolkit.deb', 'setup.sh', 'bundle.tar.gz', 'bundle.zip']:
            seed = next(i for i in range(100) if make_mission('curl', i).artifact == artifact)
            m = self.start('curl', seed)
            self.shell(f'wget -q -O {m.target}/received-{artifact} {m.url}')
            self.assertTrue(self.engine.rpc('grade', m)['passed'])

    def test_isolation(self):
        self.start('workspace')
        info = json.loads(self.engine.command('inspect', self.engine.name))[0]
        self.assertTrue(info['HostConfig']['ReadonlyRootfs'])
        self.assertEqual(info['HostConfig']['NetworkMode'], 'none')
        self.assertFalse(info['HostConfig']['Binds'])
        self.assertEqual(info['Config']['User'], '1100:1100')
        self.assertEqual(self.shell('test ! -e /var/run/docker.sock && test ! -w /etc && echo isolated').strip(), 'isolated')

    def test_real_pty_cwd_tab_history_errors_interrupt_and_resize(self):
        m = self.start('navigate')
        process = self.engine.open_terminal(m)
        outputs = queue.Queue()
        def read():
            for line in process.stdout:
                outputs.put(base64.b64decode(json.loads(line)['output']))
        reader = threading.Thread(target=read, daemon=True)
        reader.start()
        def until(token, timeout=8):
            collected = b''
            end = time.monotonic() + timeout
            while token not in collected and time.monotonic() < end:
                try: collected += outputs.get(timeout=.2)
                except queue.Empty: pass
            self.assertIn(token, collected)
            return collected
        until(b'learner@lab:')
        self.engine.resize(31, 95)
        self.engine.send(f'cd {m.source}/do'.encode() + b'\t\r')
        until(b'/docs$')
        self.assertTrue(self.engine.rpc('grade', m)['passed'])
        self.engine.send(b"stty size; printf '\\n__DONE1__\\n'\r")
        self.assertIn(b'31 95', until(b'\r\n__DONE1__\r\n'))
        self.engine.send(b'echo persistent-history\r')
        until(b'\rpersistent-history\r\n')
        self.engine.send(b'\x1b[A\r')
        until(b'\rpersistent-history\r\n')
        self.engine.send(b'not_a_real_command\r')
        until(b'command not found')
        self.engine.send(b'sleep 30\r')
        time.sleep(.2)
        self.engine.send(b'\x03')
        until(b'^C')
        self.engine.send(b"printf '\\n__ALIVE__\\n'\r")
        until(b'\r\n__ALIVE__\r\n')
        self.engine.send(b'exit\r')
        process.wait(timeout=5)
        reader.join(timeout=3)


if __name__ == '__main__': unittest.main()
