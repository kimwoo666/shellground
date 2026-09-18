"""New ROS control exercises over real executables, DDS and player services.

Only imported inside the ownership-guarded disposable guest. This is not a
ROS emulator. The human-readable status is never read back as grading proof.
"""
import json
import math
import os
from pathlib import Path
import subprocess
import sys
import time

try:
    from ros_lab import RosLab, hashes
except ImportError:  # Pure grading helpers can also be tested on the host.
    from guest.ros_lab import RosLab, hashes

OBSERVATION = Path('/run/shellground-ros-controls.json')


def near(a, b): return isinstance(a, (float, int)) and abs(a - b) < 1e-6


def ordered(samples, predicates):
    index = 0
    for sample in samples:
        if predicates[index](sample):
            index += 1
            if index == len(predicates): return True
    return False


def player_outcome(player, key, variant):
    """Evaluate one real process lifetime; never join different players."""
    s = player.get('samples', []); messages = player.get('messages', [])
    if not s or player.get('alive') or player.get('ambiguous') or player.get('extra_messages') or not s[-1].get('stable'): return False
    if not s[0]['paused'] or s[0]['count'] != 0: return False
    if any(m.get('topic') != '/turtle1/cmd_vel' or not near(m['x'], .25 + i * .01) or not near(m['z'], 0) for i, m in enumerate(messages)): return False
    paused = lambda count: lambda x: x['paused'] and x['count'] == count
    at = lambda rate, count=None: lambda x: x['paused'] and near(x['rate'], rate) and (count is None or x['count'] == count)
    if key == 'pause':
        if variant == 0:
            return bool(messages) and ordered(s, [paused(0), lambda x: not x['paused'], lambda x: x['paused'] and x['count'] > 0 and x.get('stable')])
        count = variant
        return len(messages) == count and all(x['paused'] for x in s) and ordered(s, [paused(i) for i in range(count + 1)])
    if variant == 0:
        return bool(messages) and ordered(s, [at(1., 0), at(1.1, 0), at(1., 0), lambda x: not x['paused'], lambda x: x['paused'] and x['count'] > 0 and x.get('stable')])
    if not all(x['paused'] for x in s): return False
    if variant == 1:
        return len(messages) == 2 and ordered(s, [at(1.2, 0), at(1.2, 1),
                                                  at(1., 1), lambda x: at(1., 2)(x) and x.get('stable')])
    return len(messages) == 1 and ordered(s, [at(1., 0), at(1.2, 0), lambda x: at(1.2, 1)(x) and x.get('stable')])


def teleop_outcome(state, prefix, variant):
    pose = state.get('poses', {}).get(prefix, {})
    if pose.get('distance', 0) < .05 or not pose.get('stopped'): return False
    for session in state.get('teleops', {}).values():
        messages = [m for m in session.get('messages', []) if m['topic'] == prefix + '/turtle1/cmd_vel']
        if session.get('alive') or session.get('ambiguous') or not messages: continue
        forward = lambda m: m['x'] > 0 and near(m['z'], 0)
        left = lambda m: near(m['x'], 0) and m['z'] > 0
        if variant != 1 and any(forward(m) for m in messages): return True
        if variant == 1 and left(messages[0]) and ordered(messages, [left, forward]) and pose.get('turn', 0) > .1: return True
    return False


def processes():
    result = {'players': {}, 'teleops': {}}
    for p in Path('/proc').iterdir():
        if not p.name.isdigit(): continue
        try:
            if p.stat().st_uid != 1100: continue
            args = p.joinpath('cmdline').read_bytes().decode(errors='replace').rstrip('\0').split('\0')
            names = [Path(a).name for a in args]
            kind = 'teleops' if names[0] == 'turtle_teleop_key' else None
            if 'ros2' in names and args[names.index('ros2') + 1:names.index('ros2') + 3] == ['bag', 'play']: kind = 'players'
            if not kind: continue
            start = p.joinpath('stat').read_text().rsplit(')', 1)[1].split()[19]
            node = 'rosbag2_player' if kind == 'players' else 'teleop_turtle'; namespace = '/'
            for a in args:
                if a.startswith(('__node:=', '__name:=')): node = a.split(':=', 1)[1]
                if a.startswith('__ns:='): namespace = '/' + a.split(':=', 1)[1].strip('/')
            result[kind][p.name + ':' + start] = dict(name=node, namespace=namespace)
        except (OSError, IndexError): continue
    return result


def graph_owner(node, topic, active):
    """Humble rclpy lacks per-message GID callbacks. Require one endpoint and
    one full node name; associate that graph with the real executable lifetime.
    This is controlled-lab attribution, not cryptographic PID/DDS provenance.
    """
    endpoints = node.get_publishers_info_by_topic(topic)
    if len(endpoints) != 1: return None
    endpoint = endpoints[0]
    full_name = (endpoint.node_name, endpoint.node_namespace)
    if node.get_node_names_and_namespaces().count(full_name) != 1: return None
    matches = [(kind, identity) for kind in ('players', 'teleops') for identity, desc in active[kind].items()
               if (desc['name'], desc['namespace']) == full_name]
    if len(matches) != 1: return None
    return matches[0], bytes(endpoint.endpoint_gid).hex()


class ControlsLab(RosLab):
    def prepare(self, mission):
        self.mission = mission; self.preserved = {}; self.simulators = []
        start = Path(mission['start']); start.mkdir(parents=True)
        for p in (start, start.parent): os.chown(p, 1100, 1100)
        (start / 'keep.txt').write_text('retain original training environment\n')
        os.chown(start / 'keep.txt', 1100, 1100)
        prefix = mission['review']['prefix']
        for ns in ([prefix, '/guard'] if prefix else ['']):
            self.spawn('ros2 run turtlesim turtlesim_node' + (' --ros-args -r __ns:=' + ns if ns else ''))
            self.simulators.append(self.processes[-1])
        if mission['review']['ros_controls'] != 'teleop':
            code, output = self.command('python3 /opt/shellground/ros_controls_lab.py bag control_bag')
            if code: raise RuntimeError('실제 제어용 bag 준비 실패: ' + output)
            self.preserved['bag'] = hashes(start / 'control_bag')
        if mission['review']['ros_controls'] == 'rate' and mission['practice'] == 2:
            (start / 'handoff.txt').write_text('timing=1.2\nlinear_x=0.3\nangular_z=0.0\n')
            os.chown(start / 'handoff.txt', 1100, 1100)
        OBSERVATION.unlink(missing_ok=True)
        log = open('/tmp/shellground-ros-controls.log', 'wb'); self.logs.append(log)
        # Use the same UID for Fast DDS shared-memory access. An inherited
        # write descriptor keeps the internal file root-owned in /run; the
        # separate learner-visible status is never used as grading evidence.
        fd = os.open(OBSERVATION, os.O_RDWR | os.O_CREAT | os.O_TRUNC, 0o644)
        try:
            p = subprocess.Popen(['/bin/bash', '-c', 'source /opt/ros/humble/setup.bash; exec python3 /opt/shellground/ros_controls_lab.py observe "$@"',
                                  'observe', str(start), prefix, str(fd)], stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT,
                                 pass_fds=(fd,), user=1100, group=1100, extra_groups=os.getgrouplist('learner', 1100),
                                 start_new_session=True, env={**os.environ, 'HOME': '/home/learner', 'ROS_DOMAIN_ID': '0'})
        finally: os.close(fd)
        self.processes.append(p)
        deadline = time.monotonic() + 15
        expected = [prefix, '/guard'] if prefix else ['']
        while time.monotonic() < deadline:
            state = self.read_state()
            if all(ns in state.get('poses', {}) for ns in expected): return {'ready': True, 'reference': {}}
            if p.poll() is not None: break
            time.sleep(.2)
        raise RuntimeError('실제 ROS 키 제어 관측 준비 실패: ' + Path('/tmp/shellground-ros-controls.log').read_text(errors='replace')[-3000:])

    def read_state(self):
        try: return json.loads(OBSERVATION.read_text())
        except (OSError, ValueError): return {}

    def grade(self, mission, sid):
        state = self.read_state(); start = Path(mission['start']); key = mission['review']['ros_controls']; v = mission['practice']
        checks = []
        def check(label, ok): checks.append(dict(label=label, passed=bool(ok)))
        fresh = time.monotonic() - state.get('observed_at', 0) < 3 and self.processes[-1].poll() is None
        check('실제 관측 및 준비된 turtlesim 유지', fresh and all(p.poll() is None for p in self.simulators))
        check('입력 노드와 player가 모두 종료됨', not any(item['alive'] for kind in ('players', 'teleops') for item in state.get(kind, {}).values()))
        if key == 'teleop':
            check('실제 입력 노드의 목표 순서·이동·정지·종료', teleop_outcome(state, mission['review']['prefix'], v))
            if v == 2:
                guard = state.get('poses', {}).get('/guard', {})
                check('보호 거북이 위치와 방향을 계속 유지', bool(guard) and guard.get('distance', 999) < .001 and guard.get('turn', 999) < .001)
        else:
            check('같은 player의 목표 상태 전환·선택 메시지·정지 관찰·종료', any(player_outcome(p, key, v) for p in state.get('players', {}).values()))
            check('원본 기록 보존', hashes(start / 'control_bag') == self.preserved['bag'])
            if key == 'rate' and v == 2:
                try:
                    values = dict(line.split('=', 1) for line in (start / 'handoff.txt').read_text().splitlines())
                    ok = set(values) == {'timing', 'linear_x', 'angular_z'} and all(near(float(values[k]), val) for k, val in [('timing', 1.2), ('linear_x', .25), ('angular_z', 0.)])
                except (OSError, ValueError): ok = False
                check('시간 배율과 원본 메시지 값을 구별한 인계', ok)
        try: kept = (start / 'keep.txt').read_text() == 'retain original training environment\n'
        except (OSError, UnicodeError): kept = False
        check('보호 파일 유지', kept)
        return dict(passed=all(c['passed'] for c in checks), checks=checks)


def bag(destination):
    import rosbag2_py
    from rclpy.serialization import serialize_message
    from geometry_msgs.msg import Twist
    from std_msgs.msg import String
    writer = rosbag2_py.SequentialWriter()
    writer.open(rosbag2_py.StorageOptions(uri=destination, storage_id='sqlite3'), rosbag2_py.ConverterOptions('', ''))
    for name, typename in [('/turtle1/cmd_vel', 'geometry_msgs/msg/Twist'), ('/training/notes', 'std_msgs/msg/String')]:
        writer.create_topic(rosbag2_py.TopicMetadata(name=name, type=typename, serialization_format='cdr'))
    for i in range(30):
        msg = Twist(); msg.linear.x = .25 + i * .01
        stamp = 1700000000000000000 + i * 1000000000
        writer.write('/turtle1/cmd_vel', serialize_message(msg), stamp)
        writer.write('/training/notes', serialize_message(String(data='note-' + str(i))), stamp + 100000)
    del writer


def observe(start, prefix, descriptor):
    import rclpy
    from geometry_msgs.msg import Twist
    from turtlesim.msg import Pose
    from std_msgs.msg import String
    from rosbag2_interfaces.srv import IsPaused, GetRate
    rclpy.init(args=[]); node = rclpy.create_node('_shellground_controls')
    state = dict(players={}, teleops={}, poses={}, observed_at=0)
    pending = []; active = {'players': {}, 'teleops': {}}
    current = None; answers = {}; futures = {}
    clients = {}
    types = {'paused': IsPaused, 'rate': GetRate}
    topics = list(dict.fromkeys([prefix + '/turtle1/cmd_vel', '/turtle1/cmd_vel', '/guard/turtle1/cmd_vel', '/training/notes']))
    def received(topic, message):
        attributed = graph_owner(node, topic, active)
        if not attributed:
            for kind in ('players', 'teleops'):
                for identity in active[kind]: state[kind][identity]['ambiguous'] = True
            return
        owner, gid = attributed
        event = dict(t=time.monotonic(), topic=topic, gid=gid)
        if isinstance(message, Twist): event.update(x=message.linear.x, z=message.angular.z)
        pending.append((owner, event))
        del pending[:-600]
    def pose(ns, msg):
        now = time.monotonic(); value = dict(x=msg.x, y=msg.y, theta=msg.theta)
        p = state['poses'].setdefault(ns, dict(initial=value, distance=0., turn=0., last_motion=now))
        p['last'] = value; p['distance'] = max(p['distance'], math.hypot(msg.x - p['initial']['x'], msg.y - p['initial']['y']))
        angle = math.atan2(math.sin(msg.theta - p['initial']['theta']), math.cos(msg.theta - p['initial']['theta']))
        p['turn'] = max(p['turn'], abs(angle))
        if abs(msg.linear_velocity) > .0001 or abs(msg.angular_velocity) > .0001: p['last_motion'] = now
        p['stopped'] = now - p['last_motion'] > .6
    def message_callback(topic):
        def callback(message): received(topic, message)
        return callback
    def pose_callback(ns):
        def callback(message): pose(ns, message)
        return callback
    subscriptions = [node.create_subscription(String if topic == '/training/notes' else Twist, topic,
                     message_callback(topic), 100) for topic in topics]
    for ns in ([prefix, '/guard'] if prefix else ['']):
        subscriptions.append(node.create_subscription(Pose, ns + '/turtle1/pose', pose_callback(ns), 10))

    def tick():
        nonlocal active, current, answers
        now = time.monotonic(); active = processes()
        for kind in ('players', 'teleops'):
            for identity, item in state[kind].items(): item['alive'] = identity in active[kind]
            for identity in active[kind]:
                state[kind].setdefault(identity, dict(alive=True, samples=[], messages=[], extra_messages=[], stable_since=now))
        for owner, message in pending:
            item = state[owner[0]][owner[1]]
            field = 'extra_messages' if message['topic'] == '/training/notes' else 'messages'
            item[field].append(message); del item[field][:-600]
            item['stable_since'] = now
        pending.clear()
        identity = next(iter(active['players'])) if len(active['players']) == 1 else None
        if identity != current:
            current = identity; answers = {}
            for future, _, _ in futures.values(): future.cancel()
            futures.clear()
            for client in clients.values(): node.destroy_client(client)
            clients.clear()
            if current:
                desc = active['players'][current]; full = desc['namespace'].rstrip('/') + '/' + desc['name']
                clients.update(paused=node.create_client(IsPaused, full + '/is_paused'), rate=node.create_client(GetRate, full + '/get_rate'))
        for name, client in clients.items():
            if name in futures:
                future, owner, sent = futures[name]
                if future.done():
                    try:
                        result = future.result()
                        if owner == current and now - sent < 1:
                            answers[name] = (getattr(result, name), now)
                    except Exception: pass
                    del futures[name]
                elif now - sent > 1:
                    future.cancel(); del futures[name]
            if current and name not in futures and client.service_is_ready():
                futures[name] = (client.call_async(types[name].Request()), current, now)
        ready = current and all(name in answers and now - answers[name][1] < .7 for name in clients)
        owner = graph_owner(node, '/turtle1/cmd_vel', active)
        ready = bool(ready and owner and owner[0] == ('players', current))
        if ready:
            p = state['players'][current]
            sample = dict(t=now, paused=answers['paused'][0], rate=answers['rate'][0], count=len(p['messages']),
                          stable=answers['paused'][0] and now - p['stable_since'] >= .7)
            old = p['samples'][-1] if p['samples'] else {}
            if any(sample[k] != old.get(k) for k in ('paused', 'rate', 'count', 'stable')):
                p['samples'].append(sample); del p['samples'][:-256]
            p['last_sample'] = sample
        teleop_owner = graph_owner(node, prefix + '/turtle1/cmd_vel', active)
        ready = bool(ready or teleop_owner and teleop_owner[0][0] == 'teleops')
        state['observed_at'] = now; state['observer_ready'] = ready
        data = json.dumps(state).encode(); os.pwrite(descriptor, data, 0); os.ftruncate(descriptor, len(data))
        last = state['players'].get(current) if current else next(reversed(state['players'].values()), None)
        latest = last.get('last_sample', {}) if last else {}
        display = ['observer_ready=' + str(ready).lower(), 'player_running=' + str(bool(current)).lower()]
        display += [key + '=' + str(latest.get(key, 'unobserved')).lower() for key in ('paused', 'rate', 'count', 'stable')]
        display[-2] = display[-2].replace('count=', 'messages=')
        if last and last['messages']: display += ['last_message=' + json.dumps(last['messages'][-1], ensure_ascii=False)]
        for ns, value in state['poses'].items():
            display += [(ns or '/') + ' pose=' + json.dumps(value['last']) + ' stopped=' + str(value['stopped']).lower()]
        status = Path(start) / 'control-status.txt'; temp = status.with_suffix('.tmp'); temp.write_text('\n'.join(display) + '\n'); temp.replace(status)
    node.create_timer(.25, tick)
    try: rclpy.spin(node)
    except KeyboardInterrupt: pass
    finally:
        node.destroy_node()
        if rclpy.ok(): rclpy.shutdown()


if __name__ == '__main__':
    if sys.argv[1] == 'bag': bag(sys.argv[2])
    elif sys.argv[1] == 'observe': observe(sys.argv[2], sys.argv[3], int(sys.argv[4]))
    else: raise ValueError('unknown ROS control action')
