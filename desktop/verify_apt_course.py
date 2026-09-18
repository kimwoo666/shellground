"""Incremental real-VM acceptance for the newly added APT block only."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import time

from apt_course import KEYS, STATUS, UPDATES
from missions import make_mission
from real_vm import RealEngine
from verify_real_course import Driver

DEPENDENCIES = ('apt_course.py', 'guest/apt_lab.py', 'lab/lab.py', 'real_vm.py',
                'missions.py', 'mode_curriculum.py', 'real_course_checks.py',
                'linux_learning.py', 'verify_apt_course.py')


def source_hashes():
    root = Path(__file__).parent
    return {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in DEPENDENCIES}


def command(driver, text):
    # Only confirmation automation differs from the displayed reference.
    text = re.sub(r'^sudo apt (upgrade|remove|purge)\b', r'sudo apt -y \1', text)
    text = text.replace('sudo apt --fix-broken install', 'sudo apt -y --fix-broken install')
    driver.send(text + '\r')
    driver.prompt(timeout=45)


def solve(driver, script=None):
    for line in (script or driver.mission.solution).splitlines():
        if line.strip(): command(driver, line)


def verify(runtime, report_path, keys=None):
    selected = tuple(keys or (*KEYS, 'apt_review'))
    if not selected or set(selected) - set((*KEYS, 'apt_review')) or len(selected) != len(set(selected)):
        raise ValueError('Choose unique APT unit keys; never silently verify zero cases')
    report = dict(scope='new-apt-block-only', state='in_progress', source_hashes=source_hashes(),
                  selected=list(selected), passed=[], negative=[], failures=[])
    def save():
        report_path.parent.mkdir(parents=True, exist_ok=True)
        temp = report_path.with_suffix('.tmp')
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
        temp.replace(report_path)
    engine = RealEngine(runtime)
    driver = Driver(engine)
    started = time.monotonic()
    def grade(passed):
        result = driver.grade()
        if result['passed'] is not passed: raise AssertionError(result)
    def negative(name, script):
        solve(driver, script); grade(False)
        report['negative'].append(name)
        save()
    try:
        for key in (k for k in KEYS if k in selected):
            for variant in range(3):
                driver.prepare(make_mission(key, 7251, variant)); grade(False)
                if key == 'apt_upgrade' and variant == 0:
                    negative('update_without_upgrade_rejected', 'sudo apt update\n' + STATUS + '\n' + UPDATES)
                if key == 'apt_repair' and variant == 0:
                    negative('report_without_dependency_repair_rejected', STATUS)
                solve(driver); grade(True)
                report['passed'].append(key + ':' + str(variant)); save()
                print('APT_PASS', report['passed'][-1], flush=True)
                if key == 'apt_inspect' and variant == 0:
                    negative('wrong_current_version_in_candidate_report_rejected',
                             "sed -i 's/upgradable from: 1.0/upgradable from: 2.0/g' updates.txt")
                    solve(driver, UPDATES); grade(True)
                if key == 'apt_inspect' and variant == 1:
                    solve(driver, 'printf "" > updates.txt'); grade(True)
                    report['negative'].append('empty_candidate_list_equivalent_accepted')
                if key == 'apt_upgrade' and variant == 0:
                    negative('stale_report_after_upgrade_rejected', "printf 'old data\\n' > packages.txt")
                    solve(driver, STATUS); grade(True)
                    report['negative'].append('same_session_report_repair')
                if key == 'apt_remove' and variant == 0:
                    negative('purge_instead_of_remove_rejected', 'sudo apt purge shellground-note\n' + STATUS)
                if key == 'apt_purge' and variant == 0:
                    negative('unrelated_document_loss_rejected', 'rm personal.txt')
        if 'apt_review' in selected:
            driver.prepare(make_mission('apt_review', 7251)); grade(False)
            solve(driver); grade(True); report['passed'].append('apt_review')
            negative('review_cannot_replace_restored_note_with_report',
                     'sudo apt purge shellground-note\n' + STATUS + '\n' + UPDATES)
        # An equivalent targeted upgrade must pass without exact history.
        if 'apt_upgrade' in selected:
            driver.prepare(make_mission('apt_upgrade', 7251, 1))
            solve(driver, 'sudo apt install -y shellground-note\n' + STATUS + '\n' + UPDATES); grade(True)
            report['negative'].append('targeted_install_equivalent_accepted')
        # Removing just the file must not substitute for purge in dpkg.
        if 'apt_purge' in selected:
            driver.prepare(make_mission('apt_purge', 7251, 1))
            negative('rm_config_is_not_purge', 'sudo rm /etc/shellground-note.conf\n' + STATUS)
            solve(driver); grade(True)
            report['negative'].append('same_session_purge_repair')
        report['state'] = 'complete'
    except BaseException as error:
        report['state'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['failures'].append(repr(error)[-7000:])
        raise
    finally:
        process, session = engine.process, engine.session_dir
        engine.close()
        report.update(seconds=round(time.monotonic() - started, 2),
                      vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        save()
        print(json.dumps({k: v for k, v in report.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--keys', nargs='+', help='Only new/changed units; other PASS reports are preserved')
    args = parser.parse_args()
    verify(args.runtime, args.report, args.keys)
