"""New real process lessons, with actual terminal foreground and signals."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import time
from process_course import KEYS, make_mission
from real_vm import RealEngine
from verify_real_course import Driver

DEPENDENCIES = ('process_course.py', 'guest/process_lab.py', 'guest/auth_lab.py', 'guest/bashrc',
                'lab/lab.py', 'real_vm.py', 'missions.py', 'mode_curriculum.py',
                'real_course_checks.py', 'linux_learning.py', 'verify_process_course.py')


class ProcessDriver(Driver):
    def command(self, line): self.send(line + '\r'); self.prompt()

    def snapshot(self):
        result = self.engine.channel.request('exec', root=True, cwd='/tmp',
            argv=['/usr/bin/python3', '/opt/shellground/process_lab.py', 'snapshot'])
        if result['code']: raise RuntimeError(base64.b64decode(result['err']).decode())
        return json.loads(base64.b64decode(result['out']))

    def foreground(self):
        self.send('fg %?job-main\r')
        end = time.monotonic() + 5
        while time.monotonic() < end:
            current = self.snapshot()['current'].get('main')
            if current and current['pgid'] != current['session'] and current['pgid'] == current['foreground']: return
            time.sleep(.05)
        raise AssertionError('The job never became foreground')

    def solve(self):
        for line in self.mission.solution.splitlines():
            if line.startswith('fg '): self.foreground()
            elif line.startswith('# Ctrl+Z'): self.send('\x1a'); self.prompt()
            elif line and not line.startswith('#'): self.command(line)


def verify(runtime, destination, cases=None):
    allowed = [k + ':' + str(v) for k in KEYS for v in range(3)] + ['process_review:0']
    selected = cases or allowed
    if not selected or set(selected) - set(allowed): raise ValueError('Unknown process cases')
    root = Path(__file__).parent
    report = dict(scope='new-process-block-only', state='in_progress', selected=selected, passed=[], negative=[], failures=[],
                  source_hashes={n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in DEPENDENCIES})
    def save():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); temporary.replace(destination)
    engine = RealEngine(runtime); driver = ProcessDriver(engine); started = time.monotonic()
    def grade(expected):
        result = driver.grade()
        if result['passed'] is not expected:
            result['process_snapshot'] = driver.snapshot()
            raise AssertionError(result)
    def remember(name): report['negative'].append(name); save()
    try:
        for case in selected:
            key, variant = case.split(':'); variant = int(variant)
            driver.prepare(make_mission(key, 7251, variant)); grade(False)
            driver.solve(); grade(True)
            report['passed'].append(case); save(); print('PROCESS_PASS', case, flush=True)
            if variant != 0: continue
            if key == 'process_list':
                driver.command("sed -i '/sgm7251/d' processes.txt"); grade(False)
                driver.command('ps -U learner > processes.txt'); grade(True)
                remember('missing_owned_process_row_rejected_then_restored')
                driver.command("sed -i -E 's/[0-9]+:[0-9]+:[0-9]+/99:99:99/g' processes.txt"); grade(False)
                driver.command('ps -U learner -o pid,tty,time,comm > processes.txt'); grade(True)
                remember('impossible_cpu_time_rejected_equivalent_ps_columns_accepted')
            elif key == 'process_threads':
                driver.command('cp threads.txt saved-threads.txt')
                driver.command('head -n 2 saved-threads.txt > threads.txt'); grade(False)
                driver.command('cp saved-threads.txt threads.txt')
                driver.command('printf "sgsupervisor sgm7251 sgs7251 sgb7251 learner\\n" > tree.txt'); grade(False)
                driver.command('pstree -A -n -T -p -u "$(cat supervisor.pid)" > tree.txt'); grade(True)
                remember('missing_thread_and_flat_tree_rejected_ascii_numeric_tree_accepted')
                driver.command('cp supervisor.pid old-supervisor.pid')
                driver.command('printf "1\\n" | sudo tee supervisor.pid')
                changed = engine.channel.request('exec', root=True, cwd='/tmp',
                    argv=['/bin/cat', driver.mission.start + '/supervisor.pid'])
                if changed['code'] or base64.b64decode(changed['out']).strip() != b'1':
                    raise AssertionError('Supervisor PID mutation was not applied')
                grade(False)
                driver.command('sudo cp old-supervisor.pid supervisor.pid'); grade(True)
                remember('supervisor_pid_file_tampering_rejected_then_restored')
            elif key == 'process_stop':
                driver.command('bg %?job-main'); grade(False)
                driver.foreground(); driver.send('\x1a'); driver.prompt(); grade(True)
                remember('running_is_not_stopped_same_pid_repaired')
            elif key == 'process_resume':
                driver.foreground(); grade(False)
                driver.send('\x1a'); driver.prompt(); driver.command('bg %?job-main'); grade(True)
                remember('foreground_is_not_background_then_same_job_restored')
            elif key == 'process_signals':
                driver.command('./restart-services.sh')
                driver.command('kill -KILL "$(cat main.pid)"')
                driver.command('kill -KILL "$(cat blocker.pid)"'); grade(False)
                old = driver.snapshot()['workers']['main']['pid']
                driver.command('./restart-services.sh'); driver.solve(); grade(True)
                if driver.snapshot()['workers']['main']['pid'] == old: raise AssertionError('Service restart did not replace the process')
                remember('forced_main_exit_rejected_services_restarted_without_losing_terminal')
        # Check the new root supervisor/bootstrap lifecycle, not an old solve.
        old = driver.snapshot()
        from missions import make_mission as ordinary
        engine.start(ordinary('navigate', 1234))
        script = ('import json,sys;sys.path.insert(0,"/opt/shellground");import process_lab as p;'
                  's=json.loads(sys.argv[1]);print(json.dumps({"workers":[k for k,v in s["workers"].items() '
                  'if p.identity(v) and p.identity(v)["state"] not in ("Z","X")],'
                  '"supervisor":bool(s.get("supervisor") and p.identity(s["supervisor"],False)),'
                  '"bootstrap":p.BOOTSTRAP.exists()}))')
        result = engine.channel.request('exec', root=True, cwd='/tmp', argv=['/usr/bin/python3', '-c', script, json.dumps(old)])
        clean = json.loads(base64.b64decode(result['out']))
        if clean != {'workers': [], 'supervisor': False, 'bootstrap': False}: raise AssertionError(clean)
        remember('owned_supervisor_workers_and_bootstrap_cleaned_on_problem_change')
        report['state'] = 'complete'
    except BaseException as error:
        report['state'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['failures'].append(repr(error)[-6500:]); raise
    finally:
        process, session = engine.process, engine.session_dir; engine.close()
        report.update(seconds=round(time.monotonic() - started, 2), vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        save(); print(json.dumps({k: v for k, v in report.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cases', nargs='+')
    args = parser.parse_args(); verify(args.runtime, args.report, args.cases)
