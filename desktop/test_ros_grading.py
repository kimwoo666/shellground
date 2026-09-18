import unittest
from unittest.mock import Mock
from guest.ros_lab import running_cli


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


if __name__=='__main__':unittest.main()
