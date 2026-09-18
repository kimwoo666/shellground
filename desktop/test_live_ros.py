"""Opt-in tests with real ROS Humble binaries in the app-owned guest."""
import base64
import os
from pathlib import Path
import socket
import time
import unittest

from real_vm import GuestChannel
from ros_lessons import make_ros_mission


@unittest.skipUnless(os.environ.get('SHELLGROUND_LIVE_GUEST') == '1', 'Dedicated guest required')
class LiveRosTests(unittest.TestCase):
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
        self.mission = make_ros_mission('ros_' + key, 1234, practice)
        self.channel.request('prepare', timeout=90, mission=self.mission.payload())
        self.terminal = self.channel.open_terminal(self.mission.start)
        return self.mission

    def command(self, text):
        result = self.channel.request('exec', timeout=40, run_timeout=35,
            cwd=self.mission.start, argv=['/bin/bash', '-c', 'source /opt/ros/humble/setup.bash; ' + text])
        self.assertEqual(result['code'], 0, base64.b64decode(result['err']).decode())
        return base64.b64decode(result['out']).decode()

    def send(self, text):
        self.channel.send({'action': 'input', 'session': self.terminal.sid,
                           'data': base64.b64encode(text.encode()).decode()})

    def grade(self):
        return self.channel.request('grade', timeout=40, mission=self.mission.payload(), session=self.terminal.sid)

    def assert_passes_eventually(self, timeout=8):
        deadline = time.monotonic() + timeout
        result = None
        while time.monotonic() < deadline:
            result = self.grade()
            if result['passed']:
                return
            time.sleep(.3)
        self.fail(str(result))

    def test_environment_is_per_terminal_not_just_files(self):
        self.prepare('env')
        self.command('printf "humble\\n" > distro.txt; printf "2\\n" > version.txt')
        self.assertFalse(self.grade()['passed'])
        self.send('source /opt/ros/humble/setup.bash\r')
        self.assert_passes_eventually()

    def test_nodes_and_types_are_actual_tool_outputs(self):
        mission = self.prepare('topics')
        self.assertFalse(self.grade()['passed'])
        self.command(mission.solution)
        self.assert_passes_eventually()

    def test_parameter_correction_without_reset(self):
        self.prepare('set')
        self.command('ros2 param set /turtlesim background_r 150')
        self.assertFalse(self.grade()['passed'])
        self.command('ros2 param set /turtlesim background_b 80')
        self.assert_passes_eventually()

    def test_real_colcon_overlay(self):
        mission = self.prepare('overlay')
        self.send(mission.solution.replace('\n', '\r') + '\r')
        self.assert_passes_eventually(12)

    def test_repeated_publication_is_measured_not_echoed(self):
        self.prepare('rate')
        self.assertFalse(self.grade()['passed'])
        self.command('timeout --signal=INT 6 ros2 topic pub --rate 2 /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 1.0}, angular: {z: 0.5}}"; test "$?" = 124')
        self.assert_passes_eventually()

    def test_actual_bag_creation_inspection_and_playback(self):
        mission = self.prepare('play')
        self.assertFalse(self.grade()['passed'])
        self.command(mission.solution)
        self.assert_passes_eventually()

    def test_actual_service_and_action(self):
        mission = self.prepare('service')
        self.command(mission.solution)
        self.assert_passes_eventually()
        mission = self.prepare('action')
        self.command(mission.solution)
        self.assert_passes_eventually()

    def test_actual_parameter_dump_and_load(self):
        mission = self.prepare('dump')
        self.command(mission.solution)
        self.assert_passes_eventually()
        mission = self.prepare('load')
        self.command(mission.solution)
        self.assert_passes_eventually()

    def test_remaining_readonly_ros_queries(self):
        for key in ('nodes', 'interface', 'params', 'baginfo'):
            with self.subTest(key=key):
                mission = self.prepare(key)
                self.assertFalse(self.grade()['passed'])
                self.command(mission.solution)
                self.assert_passes_eventually()

    def test_run_launch_and_domain(self):
        for key in ('run', 'launch', 'domain'):
            with self.subTest(key=key):
                mission = self.prepare(key)
                self.assertFalse(self.grade()['passed'])
                self.send(mission.solution.replace('\n', '\r') + '\r')
                self.assert_passes_eventually(12)

    def test_once_echo_and_record(self):
        mission = self.prepare('once')
        self.command(mission.solution)
        self.assert_passes_eventually()
        self.prepare('echo')
        self.command('timeout --signal=INT 3 ros2 topic echo /turtle1/pose > pose.txt; '
                     'timeout --signal=INT 4 ros2 topic hz /turtle1/pose > hz.txt; test "$?" = 124')
        self.assert_passes_eventually()
        self.prepare('record')
        self.command('timeout --signal=INT 6 ros2 bag record -o capture /turtle1/cmd_vel /turtle1/pose & recorder=$!; '
                     'sleep 1; ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 1.0}}"; '
                     'wait "$recorder"; test "$?" = 124')
        self.assert_passes_eventually()

    def test_guest_screen_is_actual_png(self):
        self.prepare('set')
        result = self.channel.request('exec', argv=['python3', '/opt/shellground/screen.py'])
        self.assertEqual(result['code'], 0, base64.b64decode(result['err']).decode())
        image = base64.b64decode(result['out'])
        self.assertTrue(image.startswith(b'\x89PNG\r\n\x1a\n'))
        Path('/tmp/shellground-real-turtlesim.png').write_bytes(image)


if __name__ == '__main__':
    unittest.main()
