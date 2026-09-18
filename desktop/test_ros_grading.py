import json
import subprocess
import unittest
from unittest.mock import Mock, patch
from guest.ros_lab import RosLab, running_cli


class RosProcessInspectionTests(unittest.TestCase):
    def proc(self,args,uid=1100):
        process=Mock();process.name='42';process.stat.return_value.st_uid=uid
        process.joinpath.return_value.read_bytes.return_value='\0'.join(args).encode()+b'\0'
        proc=Mock();proc.iterdir.return_value=[process]
        return proc

    def test_only_actual_owned_ros_cli_matches(self):
        args=['/usr/bin/python3','/opt/ros/humble/bin/ros2','topic','pub','--rate','2',
              '/turtle1/cmd_vel','geometry_msgs/msg/Twist','{linear: {x: 1.0}}']
        self.assertTrue(running_cli(('topic','pub'),'/turtle1/cmd_vel',self.proc(args)))
        self.assertFalse(running_cli(('topic','echo'),'/turtle1/cmd_vel',self.proc(args)))
        self.assertFalse(running_cli(('topic','pub'),'/other',self.proc(args)))
        self.assertFalse(running_cli(('topic','pub'),'/turtle1/cmd_vel',self.proc(args,0)))
        self.assertFalse(running_cli(('topic','pub'),'/turtle1/cmd_vel',
                                    self.proc(['/bin/bash','-c','ros2 topic pub /turtle1/cmd_vel'])))


class RosReadinessTests(unittest.TestCase):
    def fixture(self):
        lab=RosLab(Mock());lab.observation=Mock()
        lab.command=Mock(return_value=(0,'Integer value is: 69'))
        process=Mock();process.poll.return_value=None;lab.processes=[process]
        return lab

    def test_cold_start_waits_for_real_pose_without_spawning_node_list(self):
        lab=self.fixture()
        lab.observation.read_text.side_effect=[FileNotFoundError(),json.dumps({'pose':{'x':5},'observed_at':100})]
        with patch('guest.ros_lab.time.monotonic',return_value=101),patch('guest.ros_lab.time.sleep'):
            lab.wait_for_turtlesim()
        self.assertEqual(lab.command.call_count,1)
        self.assertEqual(lab.command.call_args.args,('ros2 param get /turtlesim background_r',))

    def test_stale_pose_does_not_mark_guest_ready(self):
        lab=self.fixture();lab.observation.read_text.return_value=json.dumps({'pose':{'x':5},'observed_at':1})
        with patch('guest.ros_lab.time.monotonic',side_effect=[100,100,100,102]),patch('guest.ros_lab.time.sleep'):
            with self.assertRaisesRegex(RuntimeError,'준비 시간'):lab.wait_for_turtlesim(timeout=1)
        lab.command.assert_not_called()

    def test_exited_observer_fails_without_waiting_for_full_deadline(self):
        lab=self.fixture();lab.observation.read_text.side_effect=FileNotFoundError()
        lab.processes[0].poll.return_value=1
        with self.assertRaisesRegex(RuntimeError,'프로세스가 종료'):lab.wait_for_turtlesim()

    def test_transient_parameter_startup_timeout_can_recover(self):
        lab=self.fixture();lab.observation.read_text.return_value=json.dumps({'pose':{'x':5},'observed_at':100})
        lab.command.side_effect=[subprocess.TimeoutExpired('ros2',15),(0,'Integer value is: 69')]
        with patch('guest.ros_lab.time.monotonic',return_value=101),patch('guest.ros_lab.time.sleep'):
            lab.wait_for_turtlesim()
        self.assertEqual(lab.command.call_count,2)


if __name__=='__main__':unittest.main()
