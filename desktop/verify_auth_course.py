"""New auth lessons only, including real PAM prompts in the learner PTY."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import queue
import re
import time

from auth_course import KEYS
from missions import make_mission
from real_vm import RealEngine
from verify_real_course import Driver

DEPENDENCIES = ('auth_course.py', 'guest/auth_lab.py', 'guest/shell_snapshot.py',
                'lab/lab.py', 'real_vm.py', 'missions.py', 'mode_curriculum.py',
                'real_course_checks.py', 'linux_learning.py', 'verify_auth_course.py')


class AuthDriver(Driver):
    def read_until(self, pattern, timeout=20):
        output = b''
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            try: line = self.terminal.queue.get(timeout=.15)
            except queue.Empty: continue
            if line is None: raise RuntimeError('Authentication PTY closed')
            data = base64.b64decode(json.loads(line)['output'])
            output += data; self.engine.observe_output(data)
            clean = re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]', b'', output)
            if re.search(pattern, clean): return clean
        raise TimeoutError('Expected authentication prompt: ' + output.decode(errors='replace')[-1600:])

    def prompt(self, timeout=30):
        return self.read_until(rb'(?:learner|sgauth[0-9]+)@lab:[^\r\n]*[$#] ', timeout)

    def command(self, line):
        self.send(line + '\r')
        return self.prompt()

    def password(self, value):
        user = self.mission.review['user']
        self.send(f'sudo passwd {user}\r')
        self.read_until(rb'New password:')
        self.send(value + '\r')
        first = self.read_until(rb'Retype new password:')
        self.send(value + '\r')
        second = self.prompt()
        if value.encode() in first + second:
            raise AssertionError('Password input was echoed by the terminal')

    def switch(self, login):
        plan = self.mission.review
        self.send('su ' + ('- ' if login else '') + plan['user'] + '\r')
        self.read_until(rb'Password:')
        value = plan['new_password'] if plan['set_password'] else plan['password']
        self.send(value + '\r')
        output = self.prompt()
        if value.encode() in output: raise AssertionError('Authentication secret was echoed')
        if ('learner@lab:').encode() in output: raise AssertionError('su did not enter target account')

    def solve(self):
        for line in self.mission.solution.splitlines():
            if not line or line.startswith('#'): continue
            if line == 'sudo passwd ' + self.mission.review['user']:
                self.password(self.mission.review['new_password'])
            elif line.startswith('su '): self.switch(line.startswith('su - '))
            else: self.command(line)


def verify(runtime, destination, keys=None, audit_only=False):
    selected = tuple(keys or (*KEYS, 'auth_review'))
    if set(selected) - set((*KEYS, 'auth_review')) or not selected:
        raise ValueError('Unknown or empty auth selection')
    root = Path(__file__).parent
    report = dict(scope='auth-grading-audit-delta' if audit_only else 'new-auth-block-only', state='in_progress',
                  selected=['auth_sudo:2'] if audit_only else list(selected),
                  source_hashes={n: hashlib.sha256((root / n).read_bytes()).hexdigest() for n in DEPENDENCIES},
                  passed=[], negative=[], failures=[])
    def save():
        destination.parent.mkdir(parents=True, exist_ok=True)
        temp = destination.with_suffix('.tmp')
        temp.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); temp.replace(destination)
    engine = RealEngine(runtime); driver = AuthDriver(engine); started = time.monotonic()
    def grade(expected):
        result = driver.grade()
        if result['passed'] is not expected: raise AssertionError(result)
    def remember(name): report['negative'].append(name); save()
    try:
        for key in (() if audit_only else selected):
            for variant in ((0,) if key == 'auth_review' else range(3)):
                driver.prepare(make_mission(key, 7251, variant)); grade(False)
                plan = driver.mission.review
                if key == 'auth_password' and variant == 0:
                    driver.password('Wrong-Practice-7251!')
                    driver.command(f'sudo passwd -S {plan["user"]} > status.txt'); grade(False)
                    remember('wrong_password_rejected_not_only_P_status')
                if key == 'auth_password' and variant == 2:
                    driver.command(f'sudo passwd -u {plan["user"]}')
                    driver.command(f'sudo passwd -S {plan["user"]} > status.txt'); grade(False)
                    remember('unlock_without_password_rotation_rejected')
                if key == 'auth_login' and variant == 0:
                    driver.switch(False)
                    for line in ('whoami > "$HOME/who.txt"', 'pwd > "$HOME/location.txt"',
                                 'printenv AUTH_TEAM > "$HOME/team.txt"', 'exit'):
                        driver.command(line)
                    grade(False); remember('nonlogin_shell_not_login_environment')
                driver.solve(); grade(True)
                report['passed'].append(key + ':' + str(variant)); save()
                print('AUTH_PASS', report['passed'][-1], flush=True)
                if key == 'auth_status' and variant == 0:
                    driver.command("sed -i 's/ L / P /' status.txt"); grade(False)
                    driver.command(f'sudo passwd -S {plan["user"]} > status.txt'); grade(True)
                    remember('false_status_report_rejected_and_repaired')
                if key == 'auth_sudo' and variant == 0:
                    driver.switch(True)
                    driver.command(f'cat {plan["protected"]} > "$HOME/notice.txt"')
                    denied = driver.command('sudo -n /usr/bin/id -u')
                    if not any(word in denied for word in (b'not allowed', b'password is required')):
                        raise AssertionError('Unlisted sudo command was not rejected: ' + repr(denied))
                    driver.command('exit'); grade(False)
                    driver.solve(); grade(True)
                    remember('unprivileged_read_and_unlisted_sudo_rejected_then_repaired')
                if key == 'auth_review':
                    driver.command(f'sudo passwd -l {plan["user"]}'); grade(False)
                    driver.password(plan['new_password']); grade(True)
                    remember('locked_password_rejected_same_session_repaired')
        if audit_only:
            driver.prepare(make_mission('auth_sudo', 7251, 2)); grade(False)
            driver.solve(); grade(True)
            report['passed'].append('auth_sudo:2'); save()
            plan = driver.mission.review
            # All other conditions stay solved. Each mutation targets a newly
            # strengthened invariant; restoration must pass in the same session.
            driver.switch(True)
            grade(False)
            driver.command('exit'); grade(True)
            remember('unfinished_su_foreground_rejected_then_exit_accepted')
            driver.switch(True)
            driver.command('printf "    (ALL) NOPASSWD: ALL\\n" >> "$HOME/allowed.txt"')
            driver.command('exit'); grade(False)
            driver.switch(True)
            driver.command('sudo -l > "$HOME/allowed.txt"')
            driver.command('exit'); grade(True)
            remember('invented_extra_grant_in_report_rejected_then_repaired')
            driver.command(f'sudo usermod -a -G sudo {plan["peer"]}'); grade(False)
            driver.command(f'sudo gpasswd -d {plan["peer"]} sudo'); grade(True)
            remember('peer_supplementary_group_mutation_rejected_then_repaired')
            extra = '/etc/sudoers.d/shellground-auth-audit'
            result = engine.channel.request('exec', root=True, cwd='/tmp', argv=['test', '-e', extra])
            if result['code'] == 0: raise AssertionError('Refuse to replace an existing policy')
            driver.command(f'printf "{plan["user"]} ALL=(root) NOPASSWD: /usr/bin/id\\n" | sudo tee {extra}')
            grade(False)
            driver.command(f'sudo rm -- {extra}'); grade(True)
            remember('additional_policy_source_rejected_then_removed')
        # Directly affected lifecycle: leave an su child open, then change
        # problem. Verify cleanup, not a repeat solve of an old Linux lesson.
        if not audit_only:
            driver.prepare(make_mission('auth_login', 7251)); driver.switch(True)
            engine.start(make_mission('navigate', 1234))
            result = engine.channel.request('exec', root=True, cwd='/tmp',
                argv=['getent', 'passwd', 'sgauth7251', 'sgpeer7251'])
            if base64.b64decode(result['out']).strip(): raise AssertionError('Owned accounts survived problem switch')
            remember('open_su_session_and_owned_accounts_cleaned_on_problem_switch')
        report['state'] = 'complete'
    except BaseException as error:
        report['state'] = 'cancelled' if isinstance(error, KeyboardInterrupt) else 'failed'
        report['failures'].append(repr(error)[-7000:]); raise
    finally:
        process, session = engine.process, engine.session_dir; engine.close()
        report.update(seconds=round(time.monotonic() - started, 2), vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        save(); print(json.dumps({k: v for k, v in report.items() if k != 'source_hashes'}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--keys', nargs='+')
    parser.add_argument('--audit-only', action='store_true')
    args = parser.parse_args()
    verify(args.runtime, args.report, args.keys, args.audit_only)
