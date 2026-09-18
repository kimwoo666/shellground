"""Opt-in learning-script checks in one owned KVM guest, never host Docker."""
import base64
import os
import unittest

from learning_steps import learning_steps
from mode_curriculum import curriculum
from missions import make_mission
from real_vm import RealEngine
import test_live_extensions as helpers


@unittest.skipUnless(os.environ.get('SHELLGROUND_LEARNING_LIVE') == '1', 'Owned KVM guest required')
class LiveLearningStepTests(unittest.TestCase):
    send = helpers.LiveExtensionTests.send
    wait_prompt = helpers.LiveExtensionTests.wait_prompt
    solve_in_terminal = helpers.LiveExtensionTests.solve_in_terminal
    @classmethod
    def setUpClass(cls):
        cls.engine = RealEngine()
        cls.addClassCleanup(cls.engine.close)

    def test_actual_docker_step_sequences(self):
        units = {u.key: u for u in curriculum('real')[0]}
        for key in ('sim_limits', 'docker_bind', 'docker_volume', 'docker_network', 'docker_build', 'docker_diagnose'):
            with self.subTest(unit=key):
                mission = make_mission(key, 9853)
                self.engine.start(mission)
                self.engine.open_terminal(mission)
                self.assertFalse(self.engine.rpc('grade', mission)['passed'])
                for step in learning_steps(units[key], 'real', mission):
                    # Stop's timeout affects only cleanup latency, not the taught state change.
                    script = step.commands.replace('docker stop ', 'docker stop -t 1 ')
                    result = self.engine.channel.request('exec', timeout=50, run_timeout=45,
                        cwd=mission.start, argv=['bash', '-c', 'set -e\n' + script])
                    self.assertEqual(result['code'], 0,
                                     (key, step.title, base64.b64decode(result['err']).decode(errors='replace')))
                result = self.engine.rpc('grade', mission)
                self.assertTrue(result['passed'], result)
                print('VERIFIED learning steps:', key, flush=True)

    def test_reported_copy3504_real_fixture_and_solution(self):
        m = make_mission('copy', 3504, 2)
        self.engine.start(m)
        self.engine.open_terminal(m)
        for path, expected in ((m.source + '/guide.txt', b'Release 3504 user guide\n'),
                               (m.target + '/manual.txt', b'CORRUPTED\n'),
                               (m.target + '/draft.txt', b'Draft 3504\n')):
            result = self.engine.channel.request('exec', argv=['cat', path])
            self.assertEqual(result['code'], 0, result)
            self.assertEqual(base64.b64decode(result['out']), expected)
        self.assertFalse(self.engine.rpc('grade', m)['passed'])
        result = self.engine.channel.request('exec', cwd=m.start,
                                            argv=['bash', '-c', 'set -e\n' + m.solution])
        self.assertEqual(result['code'], 0, result)
        graded = self.engine.rpc('grade', m)
        self.assertTrue(graded['passed'], graded)
        print('VERIFIED copy3504 source guide.txt -> target manual.txt, draft backup and preservation', flush=True)

    def test_reported_linux14_and15_goals_in_actual_shell(self):
        for key, seed, practice in [('long', 5942, 2), ('mixed', 8372, 0), ('mixed', 8133, 2)]:
            with self.subTest(key=key, seed=seed):
                m = make_mission(key, seed, practice)
                self.engine.start(m)
                self.channel = self.engine.channel
                self.terminal = self.engine.open_terminal(m)
                if seed == 8133:
                    result = self.channel.request('exec', argv=['cat', m.source + '/guide.txt'])
                    self.assertEqual(result['code'], 0, result)
                    self.assertEqual(base64.b64decode(result['out']), b'Release 8133 user guide\n')
                    result = self.channel.request('exec', argv=['test', '-e', m.target + '/backup'])
                    self.assertEqual(result['code'], 1)  # Creation is intentionally a learner task.
                self.assertFalse(self.engine.rpc('grade', m)['passed'])
                self.solve_in_terminal(m.solution)
                result = self.engine.rpc('grade', m)
                self.assertTrue(result['passed'], result)
                if key == 'long':
                    result = self.channel.request('exec', argv=['cat', m.report + '.where'])
                    self.assertEqual(base64.b64decode(result['out']), (m.source + '\n').encode())
                if seed == 8133:
                    result = self.channel.request('exec', argv=['cat', m.target + '/backup/guide.txt'])
                    self.assertEqual(base64.b64decode(result['out']), b'Release 8133 user guide\n')
                    result = self.channel.request('exec', argv=['bash', '-c', f'printf changed > {m.source}/guide.txt'])
                    self.assertEqual(result['code'], 0)
                    result = self.engine.rpc('grade', m)
                    self.assertFalse(result['passed'])
                    self.assertTrue(any(not c['passed'] and m.source + '/guide.txt' in c['label'] for c in result['checks']))
                print(f'VERIFIED real shell {key}/{practice} seed={seed}', flush=True)


if __name__ == '__main__': unittest.main()
