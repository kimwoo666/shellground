"""Generate an actual ROS bag and colcon overlay, not mock command responses."""
from pathlib import Path
import sys


def bag(destination):
    import rosbag2_py
    from rclpy.serialization import serialize_message
    from geometry_msgs.msg import Twist
    from turtlesim.msg import Pose
    writer = rosbag2_py.SequentialWriter()
    writer.open(rosbag2_py.StorageOptions(uri=str(destination), storage_id='sqlite3'),
                rosbag2_py.ConverterOptions('', ''))
    for topic, typename in [('/turtle1/cmd_vel', 'geometry_msgs/msg/Twist'),
                            ('/turtle1/pose', 'turtlesim/msg/Pose')]:
        writer.create_topic(rosbag2_py.TopicMetadata(name=topic, type=typename, serialization_format='cdr'))
    for index in range(8):
        twist = Twist()
        twist.linear.x, twist.angular.z = 1.0, 0.5
        pose = Pose()
        pose.x, pose.y = 5.5 + index * .1, 5.5
        stamp = 1700000000000000000 + index * 500000000
        writer.write('/turtle1/cmd_vel', serialize_message(twist), stamp)
        writer.write('/turtle1/pose', serialize_message(pose), stamp)
    del writer  # Finalize metadata before the learner opens the directory.


def overlay(destination):
    package = destination / 'src/shellground_demo'
    package.mkdir(parents=True, exist_ok=True)
    (package / 'package.xml').write_text('''<?xml version="1.0"?>
<package format="3"><name>shellground_demo</name><version>1.0.0</version>
<description>Shellground overlay practice fixture</description>
<maintainer email="training@example.invalid">Shellground</maintainer>
<license>MIT</license><buildtool_depend>ament_cmake</buildtool_depend>
<export><build_type>ament_cmake</build_type></export></package>
''')
    (package / 'CMakeLists.txt').write_text('cmake_minimum_required(VERSION 3.8)\n'
        'project(shellground_demo)\nfind_package(ament_cmake REQUIRED)\nament_package()\n')
    import subprocess
    subprocess.run(['colcon', 'build', '--executor', 'sequential'], cwd=destination, check=True)


if __name__ == '__main__':
    {'bag': bag, 'overlay': overlay}[sys.argv[1]](Path(sys.argv[2]))
