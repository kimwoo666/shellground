"""Verify only new ROS keyboard questions, typing keys into actual guest PTYs."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import time
from real_vm import RealEngine
from ros_controls_course import KEYS, make_mission
from verify_ros_acceptance import RosDriver

FILES = ('ros_controls_course.py', 'guest/ros_controls_lab.py', 'guest/ros_lab.py', 'real_vm.py',
         'missions.py', 'mode_curriculum.py', 'learning_steps.py', 'verify_ros_controls.py')


class ControlsDriver(RosDriver):
    def observed(self):
        result = self.engine.channel.request('exec', root=True, argv=['cat', '/run/shellground-ros-controls.json'], timeout=8)
        return json.loads(base64.b64decode(result['out']))

    def wait_state(self, predicate, timeout=14):
        deadline = time.monotonic() + timeout; state = {}
        while time.monotonic() < deadline:
            state = self.observed()
            if predicate(state): return state
            time.sleep(.25)
        raise AssertionError('ROS observation timeout: ' + json.dumps(state)[-8000:])

    def player(self, state):
        return next(reversed(state.get('players', {}).values()), {})

    def sample(self, state): return self.player(state).get('last_sample', {})

    def state_at(self, paused=True, rate=None, count=None, stable=False):
        def matches(state):
            s = self.sample(state)
            return (state.get('observer_ready') and s.get('paused') == paused and
                    (rate is None or abs(s.get('rate', 0) - rate) < 1e-6) and
                    (count is None or s.get('count') == count) and (not stable or s.get('stable')))
        return self.wait_state(matches)

    def key(self, data, **expected):
        self.send(data); return self.state_at(**expected)

    def solve(self):
        key = self.mission.review['ros_controls']; v = self.mission.practice
        self.command('source /opt/ros/humble/setup.bash')
        command = next(line for line in self.mission.solution.splitlines() if line.startswith('ros2 '))
        self.send(command + '\r')
        if key == 'teleop':
            self.watch(until=[b'Use arrow keys'])
            self.wait_state(lambda s: s.get('observer_ready') and bool(s['teleops']))
            if v == 1:
                self.send('\x1b[D')
                self.wait_state(lambda s: s['poses']['']['turn'] > .1 and s['poses']['']['stopped'])
                assert not self.grade()['passed'], 'rotation-only accepted'
            self.send('\x1b[A')
            prefix = self.mission.review['prefix']
            self.wait_state(lambda s: s['poses'][prefix]['distance'] > .05 and s['poses'][prefix]['stopped'])
        else:
            self.state_at(rate=1.2 if key == 'rate' and v == 1 else 1., count=0, stable=True)
            if key == 'pause' and v in (1, 2):
                self.key('\x1b[C', count=1, stable=True)
                if v == 2:
                    assert not self.grade()['passed'], 'one message accepted for two-message objective'
                    self.key('\x1b[C', count=2, stable=True)
            elif key == 'rate' and v == 1:
                self.key('\x1b[C', rate=1.2, count=1, stable=True)
                self.key('\x1b[B', rate=1.1, count=1)
                self.key('\x1b[B', rate=1., count=1)
                self.key('\x1b[C', rate=1., count=2, stable=True)
            elif key == 'rate' and v == 2:
                self.key('\x1b[A', rate=1.1, count=0)
                self.key('\x1b[A', rate=1.2, count=0)
                self.key('\x1b[C', rate=1.2, count=1, stable=True)
            else:
                if key == 'rate':
                    self.key('\x1b[A', rate=1.1, count=0)
                    self.key('\x1b[B', rate=1., count=0)
                self.key(' ', paused=False)
                self.wait_state(lambda s: self.sample(s).get('count', 0) >= 2)
                self.key(' ', paused=True, stable=True)
        assert not self.grade()['passed'], 'running foreground job accepted despite required exit'
        self.send('\x03'); self.prompt(20)
        self.wait_state(lambda s: all(not item['alive'] for kind in ('players', 'teleops') for item in s[kind].values()))
        if key == 'rate' and v == 2:
            assert not self.grade()['passed'], 'wrong handoff accepted'
            self.command('printf "timing=1.2\\nlinear_x=0.25\\nangular_z=0.0\\n" > handoff.txt')
        self.command('cat control-status.txt')


def verify(runtime, destination, selected=None):
    if destination.exists(): raise FileExistsError('Preserve prior proof')
    valid = [key + ':' + str(v) for key in KEYS for v in range(3)]
    selected = valid if selected is None else selected
    if not selected or len(set(selected)) != len(selected) or set(selected) - set(valid): raise ValueError('Invalid selection')
    root = Path(__file__).parent
    hashes = lambda: {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES}
    report = dict(scope='new-ros-controls-actual-pty-only', state='in_progress', selected=selected, passed=[], negative=[], failures=[], evidence={}, source_hashes=hashes())
    def save():
        destination.parent.mkdir(parents=True, exist_ok=True); temp = destination.with_suffix('.tmp')
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); temp.replace(destination)
    engine = RealEngine(runtime); driver = ControlsDriver(engine); began = time.monotonic()
    try:
        for case in selected:
            key, v = case.split(':'); driver.prepare(make_mission(key, 7251, int(v)))
            assert not driver.grade()['passed'], 'initial fixture accepted'
            driver.solve(); result = driver.eventual_grade()
            if not result['passed']: raise AssertionError(result)
            report['passed'].append(case); report['evidence'][case] = driver.observed()
            report['negative'].append(case + ':initial_and_foreground_not_complete')
            if case == 'ros_controls_teleop:1': report['negative'].append('rotation_without_forward_rejected')
            if case == 'ros_controls_pause:2': report['negative'].append('one_instead_of_two_messages_rejected')
            if case == 'ros_controls_rate:2': report['negative'].append('rate_scaled_twist_claim_rejected_and_repaired_in_place')
            save(); print('ROS_CONTROLS_PASS', case, flush=True)
        if hashes() != report['source_hashes']: raise AssertionError('Sources changed during real validation')
        report['state'] = 'complete'
    except BaseException as error:
        report['state'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['failures'].append(repr(error)[-10000:])
        try:
            report['failed_observation'] = driver.observed()
            result = engine.channel.request('exec', root=True, argv=['tail', '-60', '/tmp/shellground-ros-controls.log'])
            report['observer_log'] = base64.b64decode(result['out']).decode(errors='replace')
        except Exception: pass
        raise
    finally:
        process, session = engine.process, engine.session_dir; engine.close()
        report.update(seconds=round(time.monotonic() - began, 2), vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        save(); print(json.dumps({k: v for k, v in report.items() if k not in ('evidence', 'source_hashes', 'failed_observation')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True); parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cases', nargs='+'); args = parser.parse_args(); verify(args.runtime, args.report, args.cases)
