"""Real disposable accounts, passwords and sudo-policy outcome checks."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import grp
import re
import signal
import stat
import subprocess
import time

OWNED = Path('/opt/shellground/auth-owned.json')
POLICY = Path('/etc/sudoers.d/shellground-auth')
PERSONAL = b'Personal learner notes: keep this file.\n'
HANDOFF = b'Preserve this handoff source.\n'
STALE = b'Previous account status; inspect again.\n'


def guard():
    from agent import require_guest
    require_guest()
    if os.getuid() != 0: raise RuntimeError('Authentication fixture requires owned guest service')


def run(*args, data=None, required=True):
    result = subprocess.run(args, input=data, text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            timeout=15, env=dict(os.environ, LC_ALL='C'))
    if required and result.returncode:
        raise RuntimeError('Authentication fixture command failed: ' + ' '.join(args) + '\n' + result.stderr[-1000:])
    return result


def read(path):
    try:
        s = Path(path).lstat()
        if not stat.S_ISREG(s.st_mode) or s.st_size > 1_000_000: return None
        return Path(path).read_bytes()
    except OSError:
        return None


def shadows():
    return {f[0]: f[1:] for line in Path('/etc/shadow').read_text().splitlines()
            if len(f := line.split(':')) == 9}


def other_accounts(excluded):
    # Store only a digest, not other accounts' password hashes in the response.
    records = ([list(u) for u in pwd.getpwall() if u.pw_name != excluded],
               {k: v for k, v in shadows().items() if k != excluded},
               sorted((g.gr_name, g.gr_gid, sorted(g.gr_mem)) for g in grp.getgrall()))
    return hashlib.sha256(json.dumps(records, sort_keys=True).encode()).hexdigest()


def policies():
    """Fingerprint the local sudoers sources used by this owned guest."""
    paths = [Path('/etc/sudoers'), Path('/etc/sudoers.d')]
    paths += sorted(Path('/etc/sudoers.d').rglob('*'))
    result = {}
    for path in paths:
        try: info = path.lstat()
        except OSError:
            result[str(path)] = None
            continue
        if stat.S_ISREG(info.st_mode):
            content = read(path)
            value = hashlib.sha256(content).hexdigest() if content is not None else 'unreadable'
        elif path.is_symlink(): value = os.readlink(path)
        else: value = None
        result[str(path)] = [info.st_mode, info.st_uid, info.st_gid, value]
    return result


def allowed_commands(text):
    """Compare the complete permission block, ignoring terminal line wrapping."""
    marker = 'may run the following commands on '
    if text.count(marker) != 1: return None
    _, separator, body = text.split(marker, 1)[1].partition(':')
    if not separator or not body.strip(): return None
    return ' '.join(body.split())


def cleanup():
    guard()
    if not OWNED.exists(): return {'clean': True}
    records = json.loads(OWNED.read_text())
    for name, uid in records['users'].items():
        if not re.fullmatch(r'sg(auth|peer)[0-9]{1,4}', name) or not 35000 <= uid <= 55000:
            raise RuntimeError('Refuse unrelated account cleanup')
        try: account = pwd.getpwnam(name)
        except KeyError: account = None
        if account is not None:
            if account.pw_uid != uid: raise RuntimeError('Reserved account identity changed; refusing ambiguous cleanup')
            # Only these explicitly owned guest identities, including a still-open
            # su child; never userdel -r or a host user/process-wide operation.
            run('pkill', '-TERM', '-u', str(uid), required=False)
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                if run('pgrep', '-u', str(uid), required=False).returncode: break
                time.sleep(.05)
            run('pkill', '-KILL', '-u', str(uid), required=False)
            deadline = time.monotonic() + 1
            while time.monotonic() < deadline:
                if run('pgrep', '-u', str(uid), required=False).returncode: break
                time.sleep(.05)
            run('userdel', name)
        try: group = grp.getgrnam(name)
        except KeyError: continue
        if group.gr_gid != uid: raise RuntimeError('Reserved group identity changed; refusing cleanup')
        run('groupdel', name)
    POLICY.unlink(missing_ok=True)
    OWNED.unlink()
    return {'clean': True}


def validate(m):
    seed = m['seed']
    if type(seed) is not int or not 0 <= seed <= 9999: raise ValueError('Invalid exercise seed')
    plan = m['review']
    start = f'/home/learner/auth/session{seed}'
    if (m['start'] != start or plan['user'] != f'sgauth{seed}' or plan['peer'] != f'sgpeer{seed}' or
            plan['uid'] != 35000 + 2 * seed or plan['home'] != start + '/homes/' + plan['user'] or
            plan['protected'] != f'/opt/shellground/auth-data/session{seed}/admin-note.txt'):
        raise ValueError('Invalid owned-account fixture')
    return plan, Path(start)


def prepare(m):
    guard()
    plan, start = validate(m)
    cleanup()
    identities = {plan['user']: plan['uid'], plan['peer']: plan['uid'] + 1}
    # Refuse to take ownership of an existing unrelated identity or numeric ID.
    for name, uid in identities.items():
        for getter, key in ((pwd.getpwnam, name), (pwd.getpwuid, uid), (grp.getgrnam, name), (grp.getgrgid, uid)):
            try: getter(key)
            except KeyError: continue
            raise RuntimeError('Training account/group collision; not replacing existing identity')
    start.mkdir(parents=True, exist_ok=True)
    start.chmod(0o755); os.chown(start, 1100, 1100)
    (start / 'homes').mkdir(mode=0o755)
    OWNED.write_text(json.dumps({'users': identities})); OWNED.chmod(0o600)
    profiles = {}
    for name, uid in identities.items():
        home = start / 'homes' / name
        run('groupadd', '-g', str(uid), name)
        run('useradd', '-u', str(uid), '-g', name, '-s', '/bin/bash', '-d', str(home), '-m', name)
        home.chmod(0o700)
        # Guest-only published exercise secrets, passed via stdin, never argv.
        if name != plan['user'] or m['kind'] not in ('auth_review',) and not (m['kind'] == 'auth_password' and m['practice'] == 0):
            run('chpasswd', data=name + ':' + plan['password'] + '\n')
        if (name == plan['user'] and plan['initial_locked']) or (name == plan['peer'] and plan.get('peer_locked')):
            run('passwd', '-l', name)
        profile = 'export AUTH_TEAM=' + plan['team'] + '\nif [ -n "$BASH_VERSION" ]; then . "$HOME/.bashrc"; fi\n'
        bashrc = "PS1='\\[\\e[01;32m\\]\\u@lab\\[\\e[0m\\]:\\w\\$ '\nalias ls='ls --color=auto'\n"
        for filename, text in (('.profile', profile), ('.bashrc', bashrc)):
            path = home / filename; path.write_text(text); os.chown(path, uid, uid)
            profiles[str(path)] = text
    for filename, content in (('personal.txt', PERSONAL), ('handoff source.txt', HANDOFF),
                               ('status.txt', STALE), ('peer-status.txt', STALE)):
        path = start / filename; path.write_bytes(content); os.chown(path, 1100, 1100)
    if plan['stale']:
        for filename in ('team.txt', 'notice.txt'):
            path = Path(plan['home']) / filename
            path.write_bytes(STALE); os.chown(path, plan['uid'], plan['uid'])
    protected_text = f'NOTICE team={plan["team"]}\nrevision={m["seed"]}\nKEEP source unchanged\n'
    protected = Path(plan['protected']); protected.parent.mkdir(parents=True, exist_ok=True)
    protected.write_text(protected_text); protected.chmod(0o600)
    policy = ''
    if plan['policy']:
        policy = f'{plan["user"]} ALL=(root) NOPASSWD: /usr/bin/cat {protected}\n'
        POLICY.write_text(policy); POLICY.chmod(0o440)
        run('visudo', '-cf', str(POLICY))
    account = pwd.getpwnam(plan['user'])
    return {'ready': True, 'reference': {'profiles': profiles, 'policy': policy,
            'protected': protected_text, 'user_record': list(account),
            'initial_shadow': hashlib.sha256(json.dumps(shadows()[plan['user']]).encode()).hexdigest(),
            'others': other_accounts(plan['user']), 'policies': policies()}}


def parent_environment():
    try:
        pid = int(Path('/tmp/shellground.pid').read_text())
        env = dict(field.split(b'=', 1) for field in Path(f'/proc/{pid}/environ').read_bytes().split(b'\0') if b'=' in field)
        sid = env[b'SG_SESSION'].decode()
        if not sid.isdigit(): return None
        return json.loads(Path('/tmp/shellground-env-' + sid + '.json').read_text())
    except (OSError, ValueError, KeyError): return None


def grade(m):
    guard()
    plan, start = validate(m)
    ref = m['_reference']
    checks = []
    def check(label, value): checks.append({'label': label, 'passed': bool(value)})
    try: user = pwd.getpwnam(plan['user'])
    except KeyError: user = None
    check('대상 계정 · UID/그룹/홈/셸 보존', user is not None and list(user) == ref['user_record'] and
          os.getgrouplist(plan['user'], plan['uid']) == [plan['uid']])
    shadow = shadows().get(plan['user'], [])
    if plan['set_password']:
        import crypt
        value = shadow[0] if shadow else ''
        check('새 연습 암호 설정 · 암호 잠금 없음', bool(value) and not value.startswith(('!', '*')) and
              crypt.crypt(plan['new_password'], value) == value)
    else:
        check('기존 암호·잠금 상태 유지', hashlib.sha256(json.dumps(shadow).encode()).hexdigest() == ref['initial_shadow'])
    check('다른 계정·암호·그룹 구성 유지', other_accounts(plan['user']) == ref['others'])
    check('준비된 로그인 설정 유지', all(read(path) == text.encode() for path, text in ref['profiles'].items()))
    check('personal.txt와 인계 원본 보존', read(start / 'personal.txt') == PERSONAL and read(start / 'handoff source.txt') == HANDOFF)
    if plan['preserve_reports']: check('status backup.txt · 기존 보고서 보존', read(start / 'status backup.txt') == STALE)
    for filename, spec in plan['reports'].items():
        kind, wanted = spec
        at_home = kind not in ('status', 'account')
        path = (Path(plan['home']) if at_home else start) / filename
        content = read(path)
        text = content.decode(errors='replace') if content is not None else ''
        if kind == 'status':
            result = run('passwd', '-S', wanted, required=False)
            valid = result.returncode == 0 and text.split() == result.stdout.split()
        elif kind == 'account':
            result = run('getent', 'passwd', wanted, required=False)
            valid = result.returncode == 0 and text.strip() == result.stdout.strip()
        elif kind == 'home_text': valid = text.strip() == wanted.strip()
        elif kind == 'protected': valid = content == ref['protected'].encode()
        elif kind == 'selected': valid = content == (ref['protected'].splitlines()[0] + '\n').encode()
        elif kind == 'policy':
            result = run('sudo', '-l', '-U', plan['user'], required=False)
            actual = allowed_commands(result.stdout)
            valid = result.returncode == 0 and actual is not None and allowed_commands(text) == actual
        else: raise ValueError('Unknown authentication outcome')
        owned = content is not None and (not at_home or path.stat().st_uid == plan['uid'])
        check(filename + (' · 사용자 홈의 내용/소유자' if at_home else ' · 실제 조회 결과'), valid and owned)
    if plan['home_copy']:
        path = Path(plan['home']) / 'handoff.txt'
        check('handoff.txt · 원본 보존 복사/소유자', read(path) == HANDOFF and path.stat().st_uid == plan['uid'])
    if plan['inherited']:
        variable = 'HANDOFF' if m['kind'] == 'auth_switch' else 'AUTH_TEAM'
        environment = parent_environment()
        check('learner의 임시 환경변수 제거', environment is not None and variable not in environment)
    protected = Path(plan['protected'])
    check('보호 문서 · 내용/소유자/권한 유지', read(protected) == ref['protected'].encode() and
          protected.stat().st_uid == 0 and stat.S_IMODE(protected.stat().st_mode) == 0o600)
    check('sudo 정책 파일·권한 유지', policies() == ref['policies'])
    return {'passed': all(c['passed'] for c in checks), 'checks': checks}


if __name__ == '__main__':
    import sys
    guard()
    if sys.argv[1] == 'cleanup': result = cleanup()
    else: result = {'prepare': prepare, 'grade': grade}[sys.argv[1]](json.load(sys.stdin))
    print(json.dumps(result))
