"""Run all ROS questions in real Bash/PTYs and an app-owned Humble VM.

Long-running commands are controlled through the same Ctrl+C and extra
terminal operations available to learners. No simulated ros2 outputs.
"""
import argparse
import base64
import json
from pathlib import Path
import queue
import time
from mode_curriculum import curriculum
from course_topics import topic_of
from real_course_checks import make_review
from ros_lessons import make_ros_mission
from missions import make_mission
from real_vm import RealEngine
from verify_real_course import Driver, fingerprint


class RosDriver(Driver):
    def prepare(self, mission):
        super().prepare(mission)
        self.primary=self.terminal;self.recorder=None;self.foreground=False

    def command(self, command):
        self.send(command+'\r');self.prompt(60)

    def extra_terminal(self):
        self.terminal=self.engine.channel.open_terminal(self.mission.start);self.prompt()
        self.command('source /opt/ros/humble/setup.bash')
        self.command('export ROS_DOMAIN_ID='+str(self.mission.review.get('domain',0)))
        self.foreground=False

    def watch(self, seconds=0, until=None, timeout=12):
        started=time.monotonic();output=b''
        while time.monotonic()-started < (timeout if until else seconds):
            try:line=self.terminal.queue.get(timeout=.2)
            except queue.Empty:continue
            if line is None:raise RuntimeError('ROS PTY closed')
            output+=base64.b64decode(json.loads(line)['output'])
            if until and all(word in output for word in until):return
        if until:raise TimeoutError(output.decode(errors='replace')[-2000:])

    def solve(self):
        for command in self.mission.solution.splitlines():
            if not command:continue
            if command.startswith('#'):
                if self.recorder and '터미널 A로 돌아와' in command:
                    self.terminal=self.recorder;self.send('\x03');self.prompt(20);self.recorder=None
                continue
            if self.foreground:self.extra_terminal()
            if command.startswith('ros2 bag record '):
                self.send(command+'\r');self.recorder=self.terminal
                self.watch(until=[b"Subscribed to topic '/turtle1/pose'"])
                self.extra_terminal()
            elif command.startswith(('ros2 run ', 'ros2 launch ')):
                self.send(command+'\r');self.foreground=True
            elif command.startswith(('ros2 topic echo ', 'ros2 topic hz ', 'ros2 topic pub --rate ')):
                self.send(command+'\r')
                if self.recorder and command.startswith('ros2 topic pub --rate '):
                    publisher=self.terminal;self.terminal=self.recorder
                    self.watch(until=[b"Subscribed to topic '/turtle1/cmd_vel'"])
                    self.terminal=publisher
                self.watch(seconds=6)
                if command.startswith('ros2 topic pub --rate ') and 'rate' in self.mission.review['ros']:
                    active=self.grade()
                    assert any(c['label']=='주기적 발행 작업 종료' and not c['passed'] for c in active['checks']),active
                self.send('\x03');self.prompt(20)
            else:self.command(command)

    def grade(self):
        return self.engine.channel.request('grade',timeout=60,mission=self.mission.payload(),session=self.primary.sid)

    def eventual_grade(self):
        deadline=time.monotonic()+12
        while True:
            result=self.grade()
            if result['passed'] or time.monotonic()>deadline:return result
            time.sleep(.3)


def selected_cases(keys=None, cases=None):
    if keys is not None and cases is not None: raise ValueError('Choose keys or exact cases')
    units, reviews = curriculum('real')
    units = [u for u in units if topic_of(u) == 'ROS 2']
    reviews = [r for r in reviews if all(topic_of(u) == 'ROS 2' for u in r.units)]
    all_cases = [(u.key + ':' + str(v), lambda u=u, v=v: make_mission(u.key, 7251, v)) for u in units for v in range(3)]
    all_cases += [(r.key, lambda r=r: make_review(r, 7251)) for r in reviews]
    if keys is not None:
        if not keys or len(keys) != len(set(keys)) or set(keys) - {u.key for u in units}: raise ValueError('Unknown or duplicate ROS key')
        return [(key, factory) for key, factory in all_cases if key.split(':')[0] in keys]
    if cases is not None:
        if not cases or len(cases) != len(set(cases)) or set(cases) - {key for key, _ in all_cases}: raise ValueError('Unknown or duplicate ROS case')
        return [(key, factory) for key, factory in all_cases if key in cases]
    return all_cases


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True);parser.add_argument('--report',type=Path,required=True)
    selection = parser.add_mutually_exclusive_group()
    selection.add_argument('--keys',nargs='+'); selection.add_argument('--cases', nargs='+')
    args=parser.parse_args()
    if args.report.exists(): raise FileExistsError('Preserve prior evidence: choose a new report path')
    cases=selected_cases(args.keys, args.cases)
    from incremental_acceptance import source_snapshot
    source_root=Path(__file__).parent
    report=dict(state='in_progress',source_fingerprint=fingerprint(),source_hashes=source_snapshot(source_root),
                expected=[k for k,_ in cases],passed={},failures={})
    def checkpoint():
        args.report.parent.mkdir(parents=True,exist_ok=True);temporary=args.report.with_suffix('.tmp')
        temporary.write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n');temporary.replace(args.report)
    engine=RealEngine(args.runtime);driver=RosDriver(engine);started=time.monotonic();key=None
    try:
        for key,factory in cases:
            if key.startswith('ros_controls_'):
                from verify_ros_controls import ControlsDriver
                driver = ControlsDriver(engine)
            else:
                driver = RosDriver(engine)
            case_started=time.monotonic();driver.prepare(factory())
            if driver.grade()['passed']:raise AssertionError('Initial fixture already passes: '+key)
            if key=='ros_play:0':
                driver.command('source /opt/ros/humble/setup.bash')
                driver.command('ros2 bag play sample_bag')
                unfiltered=driver.grade()
                assert any(c['label']=='Pose 토픽을 함께 재생하지 않음' and not c['passed'] for c in unfiltered['checks']),unfiltered
                report.setdefault('negative',[]).append('unfiltered_bag_playback_rejected')
                driver.prepare(factory())
            if key=='ros_service:0':
                driver.command('source /opt/ros/humble/setup.bash')
                driver.command('ros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 3.0, theta: 1.57, name: helper}"')
                assert not driver.grade()['passed'],'wrong helper direction accepted'
                driver.command('ros2 service call /kill turtlesim/srv/Kill "{name: helper}"')
                report.setdefault('negative',[]).append('wrong_service_orientation_repaired')
            driver.solve();result=driver.eventual_grade()
            if not result['passed']:raise AssertionError(result)
            if key=='ros_params:0':
                driver.command("printf 'Integer value is: 999\\n' > value.txt")
                assert not driver.grade()['passed'],'stale parameter value accepted'
                driver.command('ros2 param get /turtlesim background_r > value.txt')
                assert driver.eventual_grade()['passed'],'same-session report repair failed'
                report.setdefault('negative',[]).append('stale_parameter_report_repaired')
            report['passed'][key]={'seconds':round(time.monotonic()-case_started,2)}
            checkpoint();print('ROS_COURSE_PASS '+key,flush=True)
        if report['source_hashes'] != source_snapshot(source_root): raise AssertionError('Sources changed during ROS validation')
        report['state']='complete'
    except BaseException as error:
        report['state']='failed';report['failures'][str(key)]=str(error)[-8000:];raise
    finally:
        process,session=engine.process,engine.session_dir;engine.close()
        report.update(seconds=round(time.monotonic()-started,2),vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        checkpoint();print(json.dumps({k:v for k,v in report.items() if k not in ('expected','passed')})+
                           f' passed={len(report["passed"])}/{len(cases)}',flush=True)


if __name__=='__main__':main()
