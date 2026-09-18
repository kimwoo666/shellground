"""Actual DDS observations, inside the private Linux guest only."""
import json
from pathlib import Path
import sys
import time

import rclpy
from geometry_msgs.msg import Twist
from turtlesim.msg import Pose


def main():
    destination = Path(sys.argv[1])
    rclpy.init(args=[])
    node = rclpy.create_node('_shellground_observer')
    state = {'velocity': [], 'pose': {}, 'helper': {}, 'extra_pose_publishers': [], 'pose_graph_observed': False}

    def velocity(message):
        state['velocity'].append([time.monotonic(), message.linear.x, message.angular.z])
        del state['velocity'][:-600]

    def pose(key, message):
        state[key] = {k: getattr(message, k) for k in ('x', 'y', 'theta')}

    node.create_subscription(Twist, '/turtle1/cmd_vel', velocity, 50)
    node.create_subscription(Pose, '/turtle1/pose', lambda m: pose('pose', m), 10)
    node.create_subscription(Pose, '/helper/pose', lambda m: pose('helper', m), 10)

    def persist():
        # The prepared turtlesim owns Pose. Replaying the bag without a topic
        # filter creates a second real DDS publisher; retain that observation
        # even after the short playback ends. This is not command-text grading.
        publishers = node.get_publishers_info_by_topic('/turtle1/pose')
        state['pose_graph_observed'] = True
        for endpoint in publishers:
            if endpoint.node_name != 'turtlesim':
                name=endpoint.node_namespace.rstrip('/')+'/'+endpoint.node_name
                if name not in state['extra_pose_publishers']:state['extra_pose_publishers'].append(name)
        state['observed_at'] = time.monotonic()
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(state))
        temporary.replace(destination)

    node.create_timer(0.5, persist)
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    finally:
        persist()
        node.destroy_node()
        if rclpy.ok():
            rclpy.shutdown()


if __name__ == '__main__':
    main()
