"""Generate developer acceptance fixtures from the real desktop curriculum."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'desktop'))
from missions import make_mission

ROS_TOPIC = '''import time
import rclpy
from std_msgs.msg import String
rclpy.init()
pub_node=rclpy.create_node('sg_android_acceptance_publisher')
sub_node=rclpy.create_node('sg_android_acceptance_subscriber')
received=[]
publisher=pub_node.create_publisher(String,'/sg_android_acceptance',10)
subscription=sub_node.create_subscription(String,'/sg_android_acceptance',lambda msg: received.append(msg.data),10)
deadline=time.monotonic()+25
try:
    while time.monotonic()<deadline and 'real-dds-message' not in received:
        publisher.publish(String(data='real-dds-message'))
        rclpy.spin_once(sub_node,timeout_sec=0.1)
    assert 'real-dds-message' in received, received
    print('SG_REAL_ROS_TOPIC_OK',flush=True)
finally:
    pub_node.destroy_node()
    sub_node.destroy_node()
    rclpy.shutdown()
'''


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', type=Path, required=True)
    args = parser.parse_args()
    args.destination.mkdir(parents=True, exist_ok=True)
    (args.destination / 'full-guest-test.json').write_text(json.dumps({
        'mission': make_mission('edit', 4242).payload(), 'ros_topic_python': ROS_TOPIC},
        ensure_ascii=False, indent=2) + '\n')
