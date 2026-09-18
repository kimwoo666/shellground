"""Opt-in actual account/permission checks in the app-owned Linux guest."""
import base64
import os
import socket
import unittest

from admin_lessons import make_admin_mission
from mode_curriculum import ADMIN_UNITS
from real_vm import GuestChannel
from sim_engine import SimEngine
import test_live_extensions as live


@unittest.skipUnless(os.environ.get('SHELLGROUND_LIVE_GUEST') == '1', 'Dedicated guest required')
class LiveAdminTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        connection = socket.create_connection(('127.0.0.1', 19473), timeout=10)
        connection.settimeout(None)
        cls.channel = GuestChannel(connection)
        assert 'admin' in cls.channel.request('status')['adapters']

    @classmethod
    def tearDownClass(cls): cls.channel.close()

    command = live.LiveExtensionTests.command
    send = live.LiveExtensionTests.send
    grade = live.LiveExtensionTests.grade
    wait_prompt = live.LiveExtensionTests.wait_prompt
    solve_in_terminal = live.LiveExtensionTests.solve_in_terminal

    def prepare(self, key, variant=0):
        self.mission = make_admin_mission(key, 1234, variant)
        self.channel.request('prepare', mission=self.mission.payload(), timeout=60)
        self.terminal = self.channel.open_terminal(self.mission.start)
        return self.mission

    def raw(self, script):
        return self.channel.request('exec', cwd=self.mission.start, argv=['bash', '-c', script])

    def test_every_new_unit_and_variant_with_actual_commands(self):
        for unit in ADMIN_UNITS:
            for variant in (0, 1, 2):
                with self.subTest(key=unit.key, variant=variant):
                    mission = self.prepare(unit.key, variant)
                    self.assertFalse(self.grade()['passed'])
                    self.command(mission.solution)
                    self.assertTrue(self.grade()['passed'], self.grade())

    def test_review_through_real_terminal_input(self):
        mission = self.prepare('admin_review')
        self.assertFalse(self.grade()['passed'])
        self.solve_in_terminal(mission.solution)
        self.assertTrue(self.grade()['passed'], self.grade())
        self.command('printf "wrong\\n" > keep.txt')
        self.assertFalse(self.grade()['passed'])
        self.command('printf "unrelated file\\n" > keep.txt')
        self.assertTrue(self.grade()['passed'])

    def test_missing_append_cannot_pass_and_can_be_repaired_without_reset(self):
        mission = self.prepare('admin_groups')
        self.command(mission.solution.replace('usermod -a -G', 'usermod -G'))
        self.assertFalse(self.grade()['passed'])
        self.command('sudo usermod -a -G sgaudit1234 sguser1234; id -Gn sguser1234 > groups.txt')
        self.assertTrue(self.grade()['passed'])

    def test_missing_home_and_wrong_uid_do_not_pass_and_reset_works(self):
        mission = self.prepare('admin_users')
        self.command(mission.solution.replace(' -m ', ' ').replace('-u 21234', '-u 21235'))
        self.assertFalse(self.grade()['passed'])
        mission = self.prepare('admin_users')
        self.command(mission.solution)
        self.assertTrue(self.grade()['passed'])

    def test_group_access_matches_simulation(self):
        mission = self.prepare('admin_owners')
        sim = SimEngine(); sim.start(mission)
        for line in mission.solution.splitlines():
            self.command(line)
            self.assertEqual(sim.shell.execute(line).code, 0)
        for script in ('id -u sguser1234', 'id -gn sguser1234', 'sudo -u sguser1234 cat handoff.txt',
                       'chmod 600 handoff.txt', 'sudo -u sguser1234 cat handoff.txt', 'whoami'):
            actual, fake = self.raw(script), sim.shell.execute(script)
            self.assertEqual(actual['code'], fake.code, script)
            self.assertEqual(base64.b64decode(actual['out']), fake.out, script)


if __name__ == '__main__': unittest.main()
