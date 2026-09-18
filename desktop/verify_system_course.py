"""Only the newly added real system-investigation block and its negative cases."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import time
from real_vm import RealEngine
from system_course import KEYS, make_mission
from verify_real_course import Driver

FILES = ('system_course.py', 'guest/system_lab.py', 'guest/auth_lab.py', 'guest/shell_lab.py', 'guest/agent.py',
         'lab/lab.py', 'real_vm.py', 'missions.py', 'mode_curriculum.py', 'real_course_checks.py', 'linux_learning.py', 'verify_system_course.py')


class SystemDriver(Driver):
    def command(self, command): self.send(command + '\r'); self.prompt()


def verify(runtime, destination, cases=None):
    if destination.exists(): raise FileExistsError('Use a new evidence path')
    valid = [key + ':' + str(v) for key in KEYS for v in range(3)] + ['system_review:0']
    selected = valid if cases is None else cases
    if not selected or len(selected) != len(set(selected)) or set(selected) - set(valid): raise ValueError('Invalid system case selection')
    root = Path(__file__).parent
    hashes = lambda: {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES}
    report = dict(scope='new-system-investigation-only', state='in_progress', selected=selected, passed=[], negative=[], failures=[], source_hashes=hashes())
    def save():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix('.tmp'); temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); temporary.replace(destination)
    engine = RealEngine(runtime); driver = SystemDriver(engine); started = time.monotonic()
    def grade(expected):
        result = driver.grade()
        if result['passed'] is not expected or len(result['checks']) > 7: raise AssertionError(result)
    def root_command(argv):
        result = engine.channel.request('exec', root=True, cwd='/tmp', argv=argv)
        if result['code']: raise RuntimeError(base64.b64decode(result['err']).decode())
        return base64.b64decode(result['out']).decode()
    def remember(name): report['negative'].append(name); save()
    try:
        for case in selected:
            key, variant = case.split(':'); variant = int(variant)
            driver.prepare(make_mission(key, 7251, variant)); grade(False)
            driver.solve(); grade(True); report['passed'].append(case); save(); print('SYSTEM_PASS', case, flush=True)
            a, b = driver.mission.review['interfaces']
            if case == 'system_identity:2':
                driver.command('uname -r > distro.txt'); grade(False)
                driver.command("grep '^VERSION_ID=' /etc/os-release > distro.txt"); grade(True)
                remember('kernel_release_cannot_replace_distribution_version')
            elif case == 'system_links:0':
                driver.command('ip link show > links.txt'); grade(True)
                driver.command('ifconfig -a > links.txt'); grade(True)
                driver.command(f'ip link show dev {a} > links.txt'); grade(False)
                driver.command('ip -brief link show > links.txt'); grade(True)
                root_command(['ip', 'link', 'set', 'dev', b, 'up']); grade(False)
                root_command(['ip', 'link', 'set', 'dev', b, 'down']); grade(True)
                root_command(['ip', 'link', 'set', 'dev', b, 'alias', 'changed-alias']); grade(False)
                root_command(['ip', 'link', 'set', 'dev', b, 'alias', 'shellground-system-7251-v1']); grade(True)
                remember('missing_down_interface_network_state_and_alias_mutation_rejected_ip_and_ifconfig_accepted')
            elif case == 'system_links:1':
                driver.command('ifconfig > legacy.txt'); grade(False)
                driver.command('ifconfig -a > legacy.txt'); grade(True)
                remember('legacy_listing_without_all_interfaces_rejected')
            elif case == 'system_addresses:1':
                driver.command(f'ip -6 -brief address show dev {a} > ipv6.txt'); grade(True)
                driver.command(f'ip -4 address show dev {a} > ipv6.txt'); grade(False)
                driver.command(f'ip -6 -o address show dev {a} > ipv6.txt'); grade(True)
                remember('wrong_address_family_rejected_brief_and_one_line_accepted')
            elif case == 'system_time:0':
                driver.command('printf "300\\n" > epoch.txt'); grade(False)
                driver.solve(); grade(True)
                driver.command('printf "2030-01-01T00:00:00Z\\n" > utc.txt'); grade(False)
                driver.command('date -u -d "@$(cat epoch.txt)" +%FT%TZ > utc.txt'); grade(True)
                remember('stale_epoch_and_different_utc_instant_rejected')
            elif case == 'system_time:2':
                driver.command('touch "source notes.txt"'); grade(False)
                driver.command('touch -d @' + str(1700000000 + 7251 * 60) + ' "source notes.txt"'); grade(True)
                remember('original_modification_time_change_rejected_and_repaired')
            elif case == 'system_clock:2':
                sync = root_command(['timedatectl', 'show', '-p', 'NTPSynchronized', '--value']).strip()
                wrong = 'yes' if sync == 'no' else 'no'
                driver.command(f"sed -i 's/^synchronized=.*/synchronized={wrong}/' conclusion.txt"); grade(False)
                driver.solve(); grade(True)
                driver.command('printf "777\\n" > rtc-exit.txt'); grade(False)
                driver.solve(); grade(True)
                remember('active_is_not_synchronized_and_false_rtc_status_rejected')
        # Exercise the new cleanup path, not any existing solved course.
        driver.prepare(make_mission('system_identity', 7252))
        interfaces = root_command(['ip', '-j', 'link', 'show'])
        if any(row['ifname'].startswith('sgsi7251') for row in json.loads(interfaces)): raise AssertionError('Owned interfaces survived problem change')
        remember('owned_virtual_interfaces_cleaned_on_problem_change')
        if report['source_hashes'] != hashes(): raise AssertionError('Sources changed during validation')
        report['state'] = 'complete'
    except BaseException as error:
        report['state'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['failures'].append(repr(error)[-6000:]); raise
    finally:
        process, session = engine.process, engine.session_dir; engine.close()
        report.update(seconds=round(time.monotonic()-started, 2), vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        save(); print(json.dumps({k:v for k,v in report.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True); parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--cases', nargs='+'); args = parser.parse_args()
    verify(args.runtime, args.report, args.cases)
