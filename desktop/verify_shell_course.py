"""Incremental real-PTY validation of only the new Bash teaching block."""
import argparse
import hashlib
import json
from pathlib import Path
import time

from real_vm import RealEngine
from verify_real_course import Driver
from shell_course import KEYS, make_mission, reference_script, write_script

DEPENDENCIES = ('shell_course.py', 'guest/shell_lab.py', 'guest/auth_lab.py', 'guest/shell_snapshot.py',
                'lab/lab.py', 'real_vm.py', 'missions.py', 'mode_curriculum.py', 'real_course_checks.py',
                'linux_learning.py', 'verify_shell_course.py')


def verify(runtime, destination, cases=None):
    valid = [k + ':' + str(v) for k in KEYS for v in range(3)] + ['shell_review:0']
    selected = cases or valid
    if not selected or set(selected) - set(valid): raise ValueError('Unknown shell cases')
    root = Path(__file__).parent
    report = dict(scope='new-shell-block-only', state='in_progress', selected=selected, passed=[], negative=[], failures=[],
                  source_hashes={name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in DEPENDENCIES})
    def save():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix('.tmp')
        temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); temporary.replace(destination)
    engine = RealEngine(runtime); driver = Driver(engine); started = time.monotonic()
    def command(line): driver.send(line + '\r'); driver.prompt()
    def grade(passed):
        result = driver.grade()
        if result['passed'] is not passed: raise AssertionError(result)
    def remember(name): report['negative'].append(name); save()
    try:
        for case in selected:
            key, variant = case.split(':'); variant = int(variant)
            driver.prepare(make_mission(key, 7251, variant)); grade(False)
            driver.solve(); grade(True)
            report['passed'].append(case); save(); print('SHELL_PASS', case, flush=True)
            if key == 'shell_path' and variant == 1:
                command('export PATH="' + driver.mission.start + '/tools/blue:/usr/bin:/bin"'); grade(False)
                command('export PATH="' + driver.mission.start + '/tools/green:$PATH"')
                command('export PATH="' + driver.mission.start + '/tools/blue:$PATH"'); grade(True)
                remember('missing_preserved_search_directory_rejected_then_repaired')
            if key == 'shell_source' and variant == 1:
                command('printf "new value\\n" > "../previous project.txt"'); grade(False)
                command('printf "obsolete\\n" > "../previous project.txt"'); grade(True)
                remember('replaced_historical_report_rejected_then_repaired')
            if variant != 0: continue
            if key == 'shell_path':
                command('export PATH=/usr/bin:/bin'); grade(False)
                command('export PATH="tools/green/.:/usr/bin/:/bin/"')
                command('type -P sgtool > selected.txt'); grade(True)
                remember('stale_report_without_current_path_rejected_relative_path_accepted')
            elif key == 'shell_source':
                command('source ../child.sh'); grade(False)
                command('source ../settings.sh'); grade(True)
                remember('source_child_polluting_parent_rejected_then_repaired')
            elif key == 'shell_args':
                lines = [s.replace('"$@"', '"$*"') for s in reference_script(key)]
                command(write_script('arguments.sh', lines)); grade(False)
                command(write_script('arguments.sh', reference_script(key))); grade(True)
                remember('flattened_argument_boundaries_rejected_despite_saved_report')
                command('bash ./arguments.sh "daily notes" "*.txt" > result.txt'); grade(True)
                command('bash ' + driver.mission.start + '/arguments.sh "daily notes" "*.txt" > result.txt'); grade(True)
                remember('equivalent_relative_and_absolute_script_invocations_accepted')
            elif key == 'shell_if':
                command(write_script('handover.sh', ['#!/bin/bash', 'cat -- "$1" > "$2"'])); grade(False)
                command(write_script('handover.sh', reference_script(key))); grade(True)
                remember('missing_arity_validation_rejected_despite_saved_copy')
            elif key == 'shell_noclobber':
                command(write_script('guard.sh', ['#!/bin/bash', 'printf "ready\\n" > "$1"'])); grade(False)
                command(write_script('guard.sh', ['#!/bin/bash', '[ -e "$1" ] && { printf "exists\\n" >&2; exit 1; }', 'printf "ready\\n" > "$1"']))
                grade(True)
                remember('overwriting_writer_rejected_alternative_guard_accepted')
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
    parser.add_argument('--runtime', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    parser.add_argument('--cases', nargs='+')
    args = parser.parse_args()
    verify(args.runtime, args.report, args.cases)
