"""ROS mission lifecycle and outcome grading against real processes/files/DDS.

Imported by the guest agent only after its ownership guard has succeeded.
Learner commands still run unmodified in Bash. This module never supplies CLI
output; it seeds exercises and independently inspects their resulting state.
"""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
import signal
import sqlite3
import subprocess
import time


def hashes(directory):
    return {str(p.relative_to(directory)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in directory.rglob('*') if p.is_file()}


def running_cli(operation, topic, proc=Path('/proc')):
    """Inspect actual learner-owned processes, not a fabricated shell log."""
    for path in proc.iterdir():
        if not path.name.isdigit(): continue
        try:
            if path.stat().st_uid != 1100: continue
            args=path.joinpath('cmdline').read_bytes().decode(errors='replace').split('\0')
            index=next(i for i,arg in enumerate(args) if Path(arg).name=='ros2')
        except (OSError, StopIteration): continue
        tail=args[index+1:]
        if tail[:len(operation)]==list(operation) and topic in tail: return True
    return False


class RosLab:
    def __init__(self, agent):
        self.agent = agent
        self.processes = []
        self.logs = []
        self.mission = None
        self.preserved = {}
        self.observation = Path('/tmp/shellground-ros-observation.json')
        self.controls_lab = None

    def command(self, command, timeout=15):
        script = ('source /opt/ros/humble/setup.bash; export ROS_DOMAIN_ID=' +
                  str(self.mission['review'].get('domain', 0)) + '; ' + command)
        result = self.agent.run(['/bin/bash', '-c', script], cwd=self.mission['start'], timeout=timeout)
        return result['code'], base64.b64decode(result['out']).decode(errors='replace')

    def spawn(self, command):
        log = open('/tmp/shellground-ros-' + str(len(self.processes)) + '.log', 'wb')
        process = subprocess.Popen(['/bin/bash', '-c',
            'source /opt/ros/humble/setup.bash; exec ' + command],
            cwd=self.mission['start'], user=1100, group=1100,
            extra_groups=os.getgrouplist('learner', 1100), start_new_session=True,
            env={**os.environ, 'HOME': '/home/learner', 'DISPLAY': ':0',
                 'ROS_DOMAIN_ID': str(self.mission['review'].get('domain', 0))},
            stdin=subprocess.DEVNULL, stdout=log, stderr=subprocess.STDOUT)
        self.processes.append(process)
        self.logs.append(log)

    def close(self):
        if self.controls_lab:
            self.controls_lab.close()
            self.controls_lab = None
        for process in self.processes:
            if process.poll() is None:
                try:
                    os.killpg(process.pid, signal.SIGTERM)
                    process.wait(timeout=2)
                except (ProcessLookupError, subprocess.TimeoutExpired):
                    if process.poll() is None:
                        os.killpg(process.pid, signal.SIGKILL)
                        process.wait(timeout=2)
        self.processes.clear()
        for log in self.logs:
            log.close()
        self.logs.clear()

    def prepare(self, mission):
        if mission.get('review', {}).get('ros_controls'):
            from ros_controls_lab import ControlsLab
            self.mission = mission
            self.controls_lab = ControlsLab(self.agent)
            return self.controls_lab.prepare(mission)
        self.mission = mission
        self.preserved = {}
        start = Path(mission['start'])
        start.mkdir(parents=True)
        for path in (start, start.parent):
            os.chown(path, 1100, 1100)
        components = mission['review']['ros']
        self.observation.unlink(missing_ok=True)
        # Owned by the learner process that writes it; root only reads it.
        self.spawn('/usr/bin/python3 /opt/shellground/ros_observer.py ' + str(self.observation))
        if any(key not in ('env', 'overlay', 'run', 'launch', 'domain') for key in components):
            self.spawn('ros2 run turtlesim turtlesim_node')
            deadline = time.monotonic() + 12
            while time.monotonic() < deadline:
                _, nodes = self.command('ros2 node list')
                if '/turtlesim' in nodes.splitlines():
                    code, value = self.command('ros2 param get /turtlesim background_r', timeout=5)
                    if code == 0 and 'Integer value is:' in value:
                        break
                time.sleep(.2)
            else:
                raise RuntimeError('실제 TurtleSim 시작에 실패했습니다. 게스트 ROS 로그를 확인하세요.')
        if 'overlay' in components:
            code, _ = self.command('python3 /opt/shellground/ros_fixture.py overlay /home/learner/training_ws', 60)
            if code:
                raise RuntimeError('colcon 오버레이 준비 실패')
        if any(k in components for k in ('baginfo', 'play')):
            code, _ = self.command('python3 /opt/shellground/ros_fixture.py bag sample_bag')
            if code:
                raise RuntimeError('실제 ROS bag 준비 실패')
            self.preserved['sample_bag'] = hashes(start / 'sample_bag')
        if 'load' in components:
            restore = start / 'restore.yaml'
            restore.write_text('/turtlesim:\n  ros__parameters:\n    background_r: 120\n    background_b: 90\n')
            os.chown(restore, 1100, 1100)
            self.preserved['restore.yaml'] = restore.read_text()
        for name, text in mission['review'].get('stale_reports', {}).items():
            if Path(name).name != name: raise ValueError('Invalid report fixture')
            path=start/name;path.write_text(text);os.chown(path,1100,1100)
        return {'ready': True, 'reference': {}}

    def grade(self, mission, sid):
        if self.controls_lab:
            return self.controls_lab.grade(mission, sid)
        import yaml
        start = Path(mission['start'])
        checks = []
        def check(label, passed):
            checks.append({'label': label, 'passed': bool(passed)})
        def read(name):
            try:
                return (start / name).read_text()
            except (OSError, UnicodeError):
                return ''
        def contains(name, words):
            check(name + '에 필요한 조사 결과 기록', all(w in read(name) for w in words))
        def parameter(name, value):
            code, output = self.command('ros2 param get /turtlesim ' + name)
            check(f'{name} 실제 값 = {value}', code == 0 and output.strip() == f'Integer value is: {value}')
        _, nodes_text = self.command('ros2 node list --no-daemon --spin-time 0.5')
        nodes = set(nodes_text.splitlines())
        try:
            observation = json.loads(self.observation.read_text())
            if time.monotonic() - observation.get('observed_at', 0) > 3:
                observation = {}
        except (OSError, ValueError):
            observation = {}
        components = mission['review']['ros']
        try:
            environment = json.loads(Path('/tmp/shellground-env-' + str(sid) + '.json').read_text())
        except (OSError, ValueError):
            environment = {}
        for key in components:
            if key == 'env':
                check('현재 터미널의 실제 ROS 환경 활성화', environment.get('ROS_DISTRO') == 'humble' and environment.get('ROS_VERSION') == '2')
                check('ROS_DISTRO 기록', read('distro.txt').strip() == 'humble')
                check('ROS_VERSION 기록', read('version.txt').strip() == '2')
            elif key == 'overlay':
                prefix = read('package.txt').strip()
                check('실제로 빌드한 오버레이 패키지 설치 경로',
                      prefix == '/home/learner/training_ws/install/shellground_demo' and
                      (Path(prefix) / 'share/ament_index/resource_index/packages/shellground_demo').is_file())
                check('현재 터미널의 오버레이 활성화', prefix != '' and prefix in environment.get('AMENT_PREFIX_PATH', '').split(':'))
            elif key in ('run', 'nodes'):
                check('기본 TurtleSim 노드 실행 중', '/turtlesim' in nodes)
                if key == 'nodes':
                    contains('nodes.txt', ['/turtlesim'])
                    contains('node-info.txt', ['/turtlesim', '/turtle1/cmd_vel', '/turtle1/pose', 'Subscribers:', 'Publishers:'])
            elif key == 'launch':
                check('두 이름공간의 노드 실행 중', {'/turtlesim1/turtlesim', '/turtlesim2/turtlesim'} <= nodes)
            elif key == 'domain':
                check('도메인 42에서 지정한 이름으로 실행 중', '/team/turtle' + str(mission['seed']) in nodes)
            elif key == 'topics':
                contains('topics.txt', ['/turtle1/cmd_vel', 'geometry_msgs/msg/Twist', '/turtle1/pose'])
                check('실제 메시지 타입 기록', read('type.txt').strip() == 'geometry_msgs/msg/Twist')
                contains('topic-info.txt', ['geometry_msgs/msg/Twist', 'Publisher count:', 'Subscription count:'])
                code, current = self.command('ros2 topic info /turtle1/cmd_vel')
                fields = lambda text: dict(re.findall(r'(Publisher count|Subscription count):\s*(\d+)', text))
                check('연결 수를 현재 토픽 상태로 기록', code==0 and len(fields(current))==2 and fields(read('topic-info.txt'))==fields(current))
            elif key == 'interface':
                contains('twist.txt', ['linear', 'angular', 'float64 x', 'float64 y', 'float64 z'])
            elif key == 'echo':
                try:
                    messages = [x for x in yaml.safe_load_all(read('pose.txt')) if isinstance(x, dict)]
                except yaml.YAMLError:
                    messages = []
                check('실제 Pose 필드가 있는 수신 기록', any(all(k in m for k in ('x', 'y', 'theta')) for m in messages))
                contains('hz.txt', ['average rate:', 'min:', 'max:'])
                check('메시지·주기 관찰 작업 종료', not running_cli(('topic','echo'),'/turtle1/pose') and
                      not running_cli(('topic','hz'),'/turtle1/pose'))
            elif key in ('once', 'rate', 'play'):
                samples = [v for v in observation.get('velocity', []) if abs(v[1] - 1) < .001 and abs(v[2] - .5) < .001]
                check('목표 Twist 메시지를 DDS에서 실제 수신', bool(samples))
                if key == 'rate':
                    gaps = [b[0] - a[0] for a, b in zip(samples, samples[1:])]
                    check('약 2 Hz로 3초 이상 발행', len(samples) >= 7 and samples[-1][0] - samples[0][0] >= 2.8
                          and all(.25 < gap < .9 for gap in gaps[-6:]))
                    check('주기적 발행 작업 종료', not running_cli(('topic','pub'),'/turtle1/cmd_vel'))
                if key == 'play':
                    check(f'bag의 이동 메시지 수신: {len(samples)} / 8개 이상', len(samples) >= 8)
                    check('Pose 토픽을 함께 재생하지 않음', observation.get('pose_graph_observed') is True and
                          not observation.get('extra_pose_publishers'))
            elif key == 'params':
                contains('params.txt', ['background_r', 'background_b'])
                contains('description.txt', ['background_r', 'integer'])
                code, value = self.command('ros2 param get /turtlesim background_r')
                check('현재 background_r 실제 값 기록', code==0 and read('value.txt').strip()==value.strip())
            elif key == 'set':
                parameter('background_r', 150)
                parameter('background_b', 80)
            elif key == 'dump':
                parameter('background_r', 150)
                try:
                    saved = yaml.safe_load(read('turtle.yaml'))['/turtlesim']['ros__parameters']
                except (yaml.YAMLError, KeyError, TypeError):
                    saved = {}
                check('노드 이름과 실제 빨강 값을 포함한 YAML', saved.get('background_r') == 150)
            elif key == 'load':
                parameter('background_r', 120)
                parameter('background_b', 90)
            elif key == 'record':
                counts = {}
                for database in (start / 'capture').glob('*.db3'):
                    try:
                        with sqlite3.connect('file:' + str(database) + '?mode=ro', uri=True) as connection:
                            for name, count in connection.execute('SELECT topics.name, count(messages.id) FROM topics LEFT JOIN messages ON topics.id=messages.topic_id GROUP BY topics.id'):
                                counts[name] = counts.get(name, 0) + count
                    except sqlite3.Error:
                        pass
                check('기록 종료 후 metadata.yaml 생성', (start / 'capture/metadata.yaml').is_file())
                for name in ('/turtle1/cmd_vel', '/turtle1/pose'):
                    check(name + ' 실제 기록 메시지 존재', counts.get(name, 0) > 0)
            elif key == 'baginfo':
                contains('bag-info.txt', ['/turtle1/cmd_vel', '/turtle1/pose', 'geometry_msgs/msg/Twist', 'Messages:', '16'])
            elif key == 'service':
                pose = observation.get('helper', {})
                check('기존 turtle1 보존', bool(observation.get('pose')))
                check('helper를 지정한 위치에 생성', abs(pose.get('x', -10) - 2) < .03 and abs(pose.get('y', -10) - 3) < .03)
                check('helper의 초기 방향 = 0', abs(pose.get('theta', -10)) < .03)
            elif key == 'action':
                check('실제 거북이 회전 완료', abs(observation.get('pose', {}).get('theta', -10) - 1.57) < .03)
            else:
                raise ValueError('ROS 채점 규칙 없음: ' + key)
        for name, original in self.preserved.items():
            check(name + ' 원본 보존', hashes(start / name) == original if isinstance(original, dict) else read(name) == original)
        if mission.get('practice') == 2:
            if mission['review'].get('handoff') == 'reports':
                results = [p for p in start.iterdir() if p.is_file() and p.suffix in ('.txt', '.yaml')]
                check('모든 결과를 reports에 원본과 동일하게 보관', bool(results) and all(
                    (start / 'reports' / p.name).is_file() and (start / 'reports' / p.name).read_bytes() == p.read_bytes() for p in results))
            elif mission['review'].get('handoff') == 'nodes':
                saved = set(read('nodes-after.txt').splitlines())
                expected = {n for n in nodes if not n.startswith('/_shellground')}
                check('작업 후 노드 목록 기록', bool(saved) and expected <= saved)
        return {'passed': bool(checks) and all(c['passed'] for c in checks), 'checks': checks}
