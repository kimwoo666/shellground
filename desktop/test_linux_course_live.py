"""Opt-in acceptance tests in one private real Linux, never the host shell."""
import base64
import os
import queue
import time
import unittest

from checkpoints import make_checkpoint
from learning_steps import learning_steps
from linux_course import NEW_KEYS
from missions import make_mission
from mode_curriculum import curriculum
from real_lessons import adapt_real_mission
from real_vm import RealEngine
import test_live_extensions as helpers


@unittest.skipUnless(os.environ.get('SHELLGROUND_COURSE_LIVE') == '1', 'Owned KVM course acceptance required')
class RealCourseAcceptance(unittest.TestCase):
    send = helpers.LiveExtensionTests.send
    wait_prompt = helpers.LiveExtensionTests.wait_prompt

    @classmethod
    def setUpClass(cls):
        cls.engine = RealEngine()
        cls.addClassCleanup(cls.engine.close)

    def prepare(self, m):
        self.mission = adapt_real_mission(m)
        self.engine.start(self.mission)
        self.channel = self.engine.channel
        self.terminal = self.engine.open_terminal(self.mission)
        self.engine.observe_output(self.wait_prompt())

    def type_commands(self, script):
        for command in script.splitlines():
            if not command or command.startswith('#'): continue
            if command.startswith('nano '):
                self.send(command + '\r')
                # nano runs in the actual PTY; keep writes separate from its
                # input flush and save prompt. No fixture edits stand in for it.
                time.sleep(.25)
                self.send('\x0bstatus=ready\x0f')
                time.sleep(.15)
                self.send('\r')
                time.sleep(.15)
                self.send('\x18')
            else:
                command = command.replace('sudo apt install tree', 'sudo apt install -y tree')
                self.send(command + '\r')
            self.engine.observe_output(self.wait_prompt())

    def test_all_new_units_three_variants_on_real_linux(self):
        for key in sorted(NEW_KEYS):
            for practice in (0, 1, 2):
                with self.subTest(key=key, practice=practice):
                    self.prepare(make_mission(key, 7251, practice))
                    result = self.engine.rpc('grade', self.mission)
                    self.assertFalse(result['passed'], (key, practice, 'already passed'))
                    self.type_commands(self.mission.solution)
                    result = self.engine.rpc('grade', self.mission)
                    self.assertTrue(result['passed'], (key, practice, result))
            print('VERIFIED 3 real variants:', key, flush=True)

    def test_new_linux_reviews_and_early_prerequisite_adjustments(self):
        missions = [make_checkpoint(c.end, 7251, mode='real') for c in curriculum('real')[1] if c.end <= 60]
        missions += [make_mission(key, 7251, 2) for key in ('list', 'recursive')]
        for m in missions:
            with self.subTest(key=m.review.get('checkpoint', m.kind)):
                self.prepare(m)
                self.assertFalse(self.engine.rpc('grade', self.mission)['passed'])
                self.type_commands(self.mission.solution)
                result = self.engine.rpc('grade', self.mission)
                self.assertTrue(result['passed'], result)
                print('VERIFIED real review:', m.review.get('checkpoint', m.kind), flush=True)

    def test_authored_linux_learning_sequences_reach_their_goals(self):
        for unit in curriculum('real')[0][:60]:
            m = make_mission(unit.key, 7252)
            sequence = learning_steps(unit, 'real', m)
            if not sequence: continue
            with self.subTest(key=unit.key):
                self.prepare(m)
                for step in sequence:
                    self.type_commands(step.commands)
                result = self.engine.rpc('grade', self.mission)
                self.assertTrue(result['passed'], (unit.key, result))
                print('VERIFIED real learning:', unit.key, flush=True)


if __name__ == '__main__': unittest.main()
