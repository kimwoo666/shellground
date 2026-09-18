"""Only the new Docker sessions/archive/prune cases, with real terminal keystrokes."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import queue
import re
import time
from real_vm import RealEngine
from verify_real_course import Driver
from docker_sessions_course import KEYS, make_mission

FILES = ('docker_sessions_course.py', 'guest/docker_sessions_lab.py', 'guest/docker_lab.py', 'guest/agent.py',
         'real_vm.py', 'missions.py', 'mode_curriculum.py', 'real_course_checks.py', 'learning_steps.py', 'verify_docker_sessions.py')


class SessionDriver(Driver):
    def wait_for(self, pattern, timeout=20):
        output = b''; end = time.monotonic() + timeout
        while time.monotonic() < end:
            try: line = self.terminal.queue.get(timeout=.2)
            except queue.Empty: continue
            if line is None: raise RuntimeError('PTY closed')
            data = base64.b64decode(json.loads(line)['output']); output += data; self.engine.observe_output(data)
            clean = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output)
            if re.search(pattern, clean): return clean
        raise TimeoutError('Terminal expectation failed: ' + output.decode(errors='replace')[-2000:])

    def inner(self): return self.wait_for(rb'(?:^|\n)(?:sg-session# |/[^\r\n]* # )')
    def command(self, command): self.send(command + '\r'); self.prompt()
    def enter(self, command):
        self.send(command + '\r'); self.send('\r'); self.inner()
    def detach(self): self.send('\x10\x11'); self.prompt()
    def solve(self):
        inside = False
        for line in self.mission.solution.splitlines():
            if line.startswith('# 키 입력:'):
                self.detach(); inside = False
            elif line.startswith('#') or not line: continue
            elif line.startswith(('docker run -it ', 'docker run --rm -it ', 'docker start -ai ', 'docker attach ', 'docker exec -it ')):
                self.enter(line); inside = True
            elif line.startswith('exit') and inside:
                self.send(line + '\r'); self.prompt(); inside = False
            elif inside:
                self.send(line + '\r'); self.inner()
            elif line.startswith('docker container prune '):
                self.send(line + '\r'); self.wait_for(rb'\[y/N\]'); self.send('y\r'); self.prompt()
            else: self.command(line)


def verify(runtime, destination, cases=None):
    if destination.exists(): raise FileExistsError('Preserve the previous evidence')
    valid = [key + ':' + str(v) for key in KEYS for v in range(3)] + ['docker_sessions_review:0']
    selected = valid if cases is None else cases
    if not selected or len(set(selected)) != len(selected) or set(selected) - set(valid): raise ValueError('Invalid selection')
    root = Path(__file__).parent
    hashes = lambda: {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES}
    report = dict(scope='new-docker-sessions-only', state='in_progress', selected=selected, passed=[], negative=[], failures=[], source_hashes=hashes())
    def save():
        destination.parent.mkdir(parents=True, exist_ok=True); tmp = destination.with_suffix('.tmp')
        tmp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); tmp.replace(destination)
    engine = RealEngine(runtime); driver = SessionDriver(engine); started = time.monotonic()
    def grade(expected):
        result = driver.grade()
        if result['passed'] is not expected or len(result['checks']) > 7: raise AssertionError(result)
    def remember(label): report['negative'].append(label); save()
    try:
        for case in selected:
            key, v = case.split(':'); v = int(v); driver.prepare(make_mission(key, 7251, v)); grade(False)
            name = driver.mission.review['name']
            if case in ('docker_sessions_interactive:1', 'docker_sessions_attach:2'):
                initial = engine.channel.request('exec', root=True, cwd='/tmp', argv=['docker', 'inspect', '--format', '{{.State.Status}}', name])
                if base64.b64decode(initial['out']).strip() != b'exited': raise AssertionError('Fixture was never executed')
            if case == 'docker_sessions_interactive:2':
                driver.command('printf "export 7251\\n" > "output/daily note.txt"'); grade(False)
                remember('host_file_alone_does_not_prove_interactive_container_with_bind')
            driver.solve(); grade(True); report['passed'].append(case); save(); print('DOCKER_SESSION_PASS', case, flush=True)
            if case == 'docker_sessions_attach:0':
                driver.enter('docker attach ' + name); grade(False); driver.detach(); grade(True)
                driver.command(f"docker exec {name} sh -c 'printf wrong > /session.txt'"); grade(False)
                driver.solve(); grade(True); remember('connected_terminal_and_wrong_main_shell_value_rejected')
            elif case == 'docker_sessions_exec:2':
                driver.command(f'docker exec {name} chown 0:0 "/work notes/copied note.txt"'); grade(False)
                driver.command(f'docker exec {name} chown 1100:1100 "/work notes/copied note.txt"'); grade(True)
                remember('file_content_without_requested_real_owner_rejected')
            elif case == 'docker_sessions_archive:0':
                driver.command('mv "image backup.tar.gz" good.gz')
                driver.command('gzip -dc good.gz > "image backup.tar.gz"'); grade(False)
                driver.command('cp good.gz "image backup.tar.gz"'); grade(True)
                remember('uncompressed_tar_with_gzip_extension_rejected')
            elif case == 'docker_sessions_archive:1':
                driver.command('printf wrong > restored-id.txt'); grade(False)
                driver.solve(); grade(True); remember('wrong_restored_image_id_rejected')
            elif case == 'docker_sessions_prune:1':
                driver.command('mv "receipt backup.txt" receipt-good.txt'); grade(False)
                driver.command('cp receipt-good.txt "receipt backup.txt"'); grade(True)
                remember('deletion_without_rescued_receipt_rejected')
            elif case == 'docker_sessions_prune:0':
                driver.command('docker cp sgs7251-finished:/keep-me.txt protected-good.txt')
                driver.command('printf wrong > wrong.txt')
                driver.command('docker cp wrong.txt sgs7251-finished:/keep-me.txt'); grade(False)
                driver.command('docker cp protected-good.txt sgs7251-finished:/keep-me.txt'); grade(True)
                remember('unrelated_stopped_container_contents_preserved')
        if hashes() != report['source_hashes']: raise AssertionError('Sources changed during execution')
        report['state'] = 'complete'
    except BaseException as error:
        report['state'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['failures'].append(repr(error)[-7000:]); raise
    finally:
        process, session = engine.process, engine.session_dir; engine.close()
        report.update(seconds=round(time.monotonic() - started, 2), vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        save(); print(json.dumps({k:v for k,v in report.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True); parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cases', nargs='+'); args = parser.parse_args()
    verify(args.runtime, args.report, args.cases)
