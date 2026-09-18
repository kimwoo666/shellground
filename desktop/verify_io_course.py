"""New I/O cases only, using real foreground programs and PTY control keys."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import queue
import re
import time
from io_course import KEYS, make_mission, script_lines
from shell_course import write_script
from real_vm import RealEngine
from verify_real_course import Driver

FILES = ('io_course.py', 'guest/io_lab.py', 'guest/auth_lab.py', 'guest/shell_lab.py', 'guest/agent.py',
         'lab/lab.py', 'real_vm.py', 'missions.py', 'mode_curriculum.py', 'real_course_checks.py',
         'linux_learning.py', 'verify_io_course.py')


class IODriver(Driver):
    def command(self, command): self.send(command + '\r'); self.prompt()

    def expect(self, pattern, timeout=8):
        output = b''; end = time.monotonic() + timeout
        while time.monotonic() < end:
            try: line = self.terminal.queue.get(timeout=.1)
            except queue.Empty: continue
            if line is None: raise RuntimeError('PTY closed')
            data = base64.b64decode(json.loads(line)['output']); self.engine.observe_output(data)
            output += data
            if re.search(pattern, re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output)): return output
        raise TimeoutError('Expected ' + repr(pattern) + ': ' + output.decode(errors='replace')[-2000:])

    def foreground(self, name):
        script = ('import sys,json,pathlib;sys.path.insert(0,"/opt/shellground");from process_lab import inspect;'
                  's=inspect(int(pathlib.Path("/tmp/shellground.pid").read_text()));'
                  'p=[inspect(int(f.name)) for f in pathlib.Path("/proc").iterdir() if f.name.isdigit()];'
                  'print(json.dumps([v["cmd"] for v in p if v and s and v["uid"]==1100 '
                  'and v["pgid"]==s["foreground"] and v["pgid"]!=s["pid"]]))')
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            result = self.engine.channel.request('exec', root=True, cwd='/tmp', argv=['/usr/bin/python3', '-c', script])
            if result['code']: raise RuntimeError(base64.b64decode(result['err']).decode())
            if any(Path(command.split()[0]).name == name for command in json.loads(base64.b64decode(result['out'])) if command): return
            time.sleep(.05)
        raise AssertionError(name + ' did not own the foreground')

    def page(self, command):
        self.send(command + '\r'); self.expect(rb'--More--'); self.foreground('more')
        self.send(' '); self.expect(rb'--More--')
        self.send('\r'); self.expect(rb'--More--')
        self.send('/RELEASE CHECKPOINT\r'); self.expect(rb'--More--')
        result = self.grade()
        if not any(not c['passed'] and '셸로 복귀' in c['label'] for c in result['checks']):
            raise AssertionError('An active pager must require return to shell')
        self.send('q'); self.prompt()

    def solve(self):
        lines = iter(self.mission.solution.splitlines())
        for line in lines:
            if line.startswith('more ') or ' | more ' in line:
                self.page(line)
            elif line.startswith(('cat > ', 'cat >> ')):
                text = []
                for body in lines:
                    if body.startswith('# Ctrl+D'): break
                    text.append(body)
                else: raise AssertionError('Missing EOF instruction')
                self.send(line + '\r'); self.foreground('cat')
                self.send('\r'.join(text) + '\r')
                self.send('\x04'); self.prompt()
            elif line and not line.startswith('#'): self.command(line)


def verify(runtime, destination, cases=None):
    valid = [k + ':' + str(v) for k in KEYS for v in range(3)] + ['io_review:0']
    selected = cases or valid
    if not selected or set(selected) - set(valid): raise ValueError('Unknown I/O selection')
    root = Path(__file__).parent
    hashes = lambda: {n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in FILES}
    report = dict(scope='new-io-block-only', state='in_progress', selected=selected, passed=[], negative=[], failures=[], source_hashes=hashes())
    def save():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix('.tmp'); temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); temporary.replace(destination)
    engine = RealEngine(runtime); driver = IODriver(engine); started = time.monotonic()
    def grade(expected):
        result = driver.grade()
        if result['passed'] is not expected or len(result['checks']) > 7: raise AssertionError(result)
    def remember(name): report['negative'].append(name); save()
    try:
        for case in selected:
            key, variant = case.split(':'); variant = int(variant)
            driver.prepare(make_mission(key, 7251, variant)); grade(False)
            driver.solve(); grade(True); report['passed'].append(case); save(); print('IO_PASS', case, flush=True)
            if key == 'io_shebang' and variant == 2:
                # Correct saved reports must not conceal a tool tied to its original cwd.
                driver.command(write_script('../show-files.sh', ['#!/bin/bash', 'printf "directory=%s\\n" "$1"',
                                      '/bin/ls -1a -- "' + driver.mission.start + '/$1"']))
                grade(False)
                driver.command(write_script('../show-files.sh', script_lines())); grade(True)
                remember('original_cwd_hardcoding_rejected_despite_correct_saved_reports')
            if variant: continue
            if key == 'io_input':
                driver.command('printf "bad\\n" >> entry.txt'); grade(False)
                driver.solve(); grade(True)
                driver.send('cat >> entry.txt\r'); driver.foreground('cat')
                result = driver.grade()
                if not any(not c['passed'] and '셸로 복귀' in c['label'] for c in result['checks']): raise AssertionError(result)
                driver.send('\x04'); driver.prompt(); grade(True)
                remember('wrong_contents_repaired_and_active_cat_cannot_complete')
            elif key == 'io_pager':
                driver.command('printf "code=OLD\\n" > answer.txt'); grade(False)
                driver.command('grep "^code=" "long notes.txt" > answer.txt'); grade(True)
                remember('stale_answer_rejected_equivalent_lookup_accepted_real_paging_and_q_verified')
            elif key == 'io_tree':
                driver.command('tree inventory > tree.txt'); grade(False)
                driver.command('tree -a --charset=ASCII --dirsfirst ./inventory > tree.txt'); grade(True)
                driver.command('find inventory > tree.txt'); grade(False)
                driver.command('tree -a --noreport inventory > tree.txt'); grade(True)
                driver.command('cd inventory; tree -a . > ../tree.txt; cd ..'); grade(True)
                driver.command('chmod 700 inventory/docs'); grade(False)
                driver.command('chmod 755 inventory/docs'); grade(True)
                remember('missing_hidden_and_flat_hierarchy_rejected_equivalent_ascii_order_accepted')
            elif key == 'io_binary':
                driver.command('chmod u-x ./ls'); grade(False)
                driver.command('chmod u+x ./ls'); grade(True)
                driver.command('cp ./ls ./saved-ls')
                driver.command('printf "fake\\n" > ./ls'); grade(False)
                driver.command('cp ./saved-ls ./ls'); grade(True)
                driver.command('./ls -1ar inventory > names.txt'); grade(True)
                remember('nonexecutable_or_fake_copy_rejected_despite_correct_report')
            elif key == 'io_shebang':
                driver.command(write_script('show-files.sh', script_lines()[1:])); grade(False)
                driver.command(write_script('show-files.sh', ['#!/usr/bin/env bash', *script_lines()[1:]])); grade(True)
                driver.command(write_script('show-files.sh', ['#!/bin/bash', 'cat run.txt'])); grade(False)
                driver.command(write_script('show-files.sh', script_lines())); grade(True)
                driver.command(write_script('show-files.sh', [*script_lines()[:2], '/bin/ls -1ar -- "$1"'])); grade(True)
                driver.command('printf "changed\\n" > personal.txt'); grade(False)
                driver.command('printf "Personal I/O practice notes: preserve.\\n" > personal.txt'); grade(True)
                remember('missing_shebang_fixed_report_and_original_corruption_rejected_env_bash_accepted')
        if report['source_hashes'] != hashes(): raise AssertionError('Sources changed during validation')
        report['state'] = 'complete'
    except BaseException as error:
        report['state'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['failures'].append(repr(error)[-6000:]); raise
    finally:
        process, session = engine.process, engine.session_dir; engine.close()
        report.update(seconds=round(time.monotonic() - started, 2), vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        save(); print(json.dumps({k: v for k, v in report.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True); parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cases', nargs='+')
    args = parser.parse_args(); verify(args.runtime, args.report, args.cases)
