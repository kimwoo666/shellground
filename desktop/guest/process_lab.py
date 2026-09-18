"""Real low-load processes and protected exit-status evidence in the owned VM."""
import ctypes
import json
import os
from pathlib import Path
import re
import signal
import stat
import subprocess
import sys
import threading
import time

if __package__:
    from .auth_lab import guard, read
else:
    from auth_lab import guard, read

ROOT = Path('/opt/shellground/process-course')
CONFIG = ROOT / 'config.json'
STATE = ROOT / 'state.json'
CONTROL = ROOT / 'restart.json'
BOOTSTRAP = Path('/opt/shellground/process-bootstrap.sh')
SCRIPT = '/opt/shellground/process_lab.py'
PERSONAL = b'Keep personal process notes.\n'
STALE = b'Previous service list.\n'
ROLES = ('main', 'spare', 'blocker')


def write_json(path, data):
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(data)); temporary.chmod(0o600); temporary.replace(path)


def inspect(pid):
    try:
        path = Path('/proc') / str(int(pid))
        text = (path / 'stat').read_text(); fields = text.rsplit(')', 1)[1].split()
        return dict(pid=int(pid), name=text.split('(', 1)[1].rsplit(')', 1)[0], state=fields[0],
                    ppid=int(fields[1]), pgid=int(fields[2]), session=int(fields[3]),
                    start_ticks=int(fields[19]), uid=path.stat().st_uid,
                    tty=int(fields[4]), foreground=int(fields[5]),
                    cpu_seconds=(int(fields[11]) + int(fields[12])) / os.sysconf('SC_CLK_TCK'),
                    tids=sorted(int(t.name) for t in (path / 'task').iterdir()),
                    cmd=(path / 'cmdline').read_bytes().replace(b'\0', b' ').decode(errors='replace'))
    except (OSError, ValueError): return None


def identity(record, worker=True):
    actual = inspect(record.get('pid', 0))
    return actual if actual and actual['start_ticks'] == record.get('start_ticks') and SCRIPT in actual['cmd'] and (
        actual['uid'] == (1100 if worker else 0)) else None


def kill_owned(record, sig, worker=True):
    current = identity(record, worker)
    if current:
        try: os.kill(current['pid'], sig)
        except ProcessLookupError: pass


def wait_record(pid, name):
    end = time.monotonic() + 4
    while time.monotonic() < end:
        result = inspect(pid)
        if result and result['name'] == name: return result
        time.sleep(.025)
    raise RuntimeError('Practice worker did not become ready')


def cleanup():
    guard()
    BOOTSTRAP.unlink(missing_ok=True)
    if not STATE.exists(): return {'clean': True}
    state = json.loads(STATE.read_text())
    supervisor = state.get('supervisor')
    if supervisor: kill_owned(supervisor, signal.SIGTERM, worker=False)
    for record in state.get('workers', {}).values():
        kill_owned(record, signal.SIGCONT); kill_owned(record, signal.SIGTERM)
    deadline = time.monotonic() + 1
    while time.monotonic() < deadline and any(identity(r) for r in state.get('workers', {}).values()): time.sleep(.05)
    for record in state.get('workers', {}).values(): kill_owned(record, signal.SIGKILL)
    if supervisor: kill_owned(supervisor, signal.SIGKILL, worker=False)
    for path in (STATE, CONFIG, CONTROL, ROOT / 'trees.json'): path.unlink(missing_ok=True)
    return {'clean': True}


def worker(seed, role, behavior, count):
    from agent import require_guest
    require_guest()
    if os.getuid() != 1100 or role not in ROLES: raise RuntimeError('Worker is learner-only')
    event = threading.Event()
    signal.signal(signal.SIGTERM, signal.SIG_IGN if behavior == 'stubborn' else lambda *_: event.set())
    # This workload sleeps. It demonstrates real threads without busy loops.
    threads = [threading.Thread(target=event.wait, daemon=True) for _ in range(count - 1)]
    for thread in threads: thread.start()
    name = 'sg' + role[0] + str(seed)
    ctypes.CDLL(None).prctl(15, name.encode(), 0, 0, 0)
    print('PROCESS_READY ' + name, flush=True)
    event.wait()
    for thread in threads: thread.join(timeout=.2)


def launch(config, role):
    mode = 'stubborn' if role == 'blocker' and config['kind'] in ('process_signals', 'process_review') else 'normal'
    count = 3 if role == 'main' else 1
    process = subprocess.Popen(['/usr/bin/python3', SCRIPT, 'worker', str(config['seed']), role, mode, str(count), 'job-' + role],
        user=1100, group=1100, extra_groups=[], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL, cwd=config['start'], start_new_session=True)
    record = wait_record(process.pid, 'sg' + role[0] + str(config['seed']))
    if role in config['review']['initial_stopped']: os.kill(process.pid, signal.SIGSTOP)
    return process, record


def publish_pids(config, state):
    start = Path(config['start'])
    for role, record in state['workers'].items():
        path = start / (role + '.pid'); path.write_text(str(record['pid']) + '\n'); path.chmod(0o644)
    if state.get('supervisor'):
        (start / 'supervisor.pid').write_text(str(state['supervisor']['pid']) + '\n')


def capture_trees(state):
    # Called by the request helper, never the supervisor: otherwise pstree
    # itself would appear as a new child in its own expected tree.
    pid = str(state['supervisor']['pid'])
    outputs = []
    for charset in ('-A', '-U'):
        for order in ([], ['-n']):
            for threads in ([], ['-T']):
                outputs.append(subprocess.check_output(['pstree', '-p', '-u', charset, *order, *threads, pid],
                    text=True, timeout=2, env=dict(os.environ, LC_ALL='C.UTF-8')))
    write_json(ROOT / 'trees.json', outputs)


def supervise():
    guard()
    config = json.loads(CONFIG.read_text()); stop = threading.Event()
    signal.signal(signal.SIGTERM, lambda *_: stop.set())
    ctypes.CDLL(None).prctl(15, b'sgsupervisor', 0, 0, 0)
    children = {}
    state = dict(supervisor=inspect(os.getpid()), workers={}, exits={}, generation=0)
    def restart():
        for role, (process, record) in children.items():
            kill_owned(record, signal.SIGCONT); kill_owned(record, signal.SIGKILL)
            process.wait(timeout=2)
        children.clear(); state['workers'] = {}; state['exits'] = {}; state['generation'] += 1
        for role in ROLES:
            process, record = launch(config, role)
            children[role] = process, record; state['workers'][role] = record
        publish_pids(config, state); write_json(STATE, state)
    try:
        restart()
        while not stop.wait(.1):
            if CONTROL.exists():
                CONTROL.unlink(); restart()
            changed = False
            for role, (process, _) in children.items():
                code = process.poll()
                if code is not None and role not in state['exits']:
                    state['exits'][role] = code; changed = True
            if changed: write_json(STATE, state)
    finally:
        for process, record in children.values():
            kill_owned(record, signal.SIGCONT); kill_owned(record, signal.SIGKILL)
            process.wait(timeout=2)


def validate(m):
    seed = m['seed']
    if type(seed) is not int or not 0 <= seed <= 9999: raise ValueError('Invalid process seed')
    start = Path(f'/home/learner/process/session{seed}')
    if m['start'] != str(start) or m['kind'] not in ('process_list', 'process_threads', 'process_stop', 'process_resume', 'process_signals', 'process_review'):
        raise ValueError('Invalid process lesson')
    if set(m['review']['initial_stopped']) - set(ROLES): raise ValueError('Invalid initial process roles')
    return start


def prepare(m):
    guard(); start = validate(m); cleanup()
    ROOT.mkdir(mode=0o700, exist_ok=True)
    start.mkdir(parents=True, exist_ok=True); os.chown(start, 1100, 1100)
    inventory = start / 'inventory'; (inventory / 'docs').mkdir(parents=True)
    for name, data in (('personal.txt', PERSONAL), ('processes.txt', STALE), ('inventory/.hidden', b'hidden\n'),
                       ('inventory/docs/read me.txt', b'Process exercise data\n')):
        path = start / name; path.write_bytes(data); os.chown(path, 1100, 1100)
    restart = '#!/bin/bash\nsudo -n /usr/bin/python3 /opt/shellground/process_lab.py restart\n'
    script = start / 'restart-services.sh'; script.write_text(restart); script.chmod(0o755)
    write_json(CONFIG, m)
    if m['review']['jobs']:
        lines = ['# Owned process-course fixture: seed jobs only once.',
                 'if sudo -n /usr/bin/python3 /opt/shellground/process_lab.py claim "$SG_SESSION"; then']
        for role in ROLES:
            lines += [f'  /usr/bin/python3 {SCRIPT} worker {m["seed"]} {role} normal {3 if role == "main" else 1} job-{role} &',
                      f'  _sg_course_{role}=$!']
        lines += ['  sudo -n /usr/bin/python3 /opt/shellground/process_lab.py register "$SG_SESSION" "$_sg_course_main" "$_sg_course_spare" "$_sg_course_blocker"',
                  '  unset _sg_course_main _sg_course_spare _sg_course_blocker', 'fi']
        BOOTSTRAP.write_text('\n'.join(lines) + '\n'); BOOTSTRAP.chmod(0o644)
        write_json(STATE, dict(workers={}, exits={}, session=None))
    else:
        with (ROOT / 'supervisor.log').open('ab') as log:
            process = subprocess.Popen(['/usr/bin/python3', SCRIPT, 'supervise'], stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, stderr=log, start_new_session=True)
        end = time.monotonic() + 6
        while not STATE.exists() and time.monotonic() < end and process.poll() is None: time.sleep(.05)
        if not STATE.exists():
            process.terminate()
            raise RuntimeError('Process supervisor initialization failed')
        capture_trees(json.loads(STATE.read_text()))
    return {'ready': True, 'reference': {'restart': restart}}


def claim(sid):
    guard()
    if not sid.isdigit(): return False
    state = json.loads(STATE.read_text())
    if state.get('session') is not None: return False
    state['session'] = sid; write_json(STATE, state); return True


def register(sid, pids):
    guard()
    config = json.loads(CONFIG.read_text()); state = json.loads(STATE.read_text())
    if state.get('session') != sid or state['workers']: raise RuntimeError('Process jobs already registered')
    records = {}
    for role, pid in zip(ROLES, pids):
        record = wait_record(int(pid), 'sg' + role[0] + str(config['seed']))
        if record['uid'] != 1100 or SCRIPT not in record['cmd']: raise RuntimeError('Not an owned practice worker')
        if record['pgid'] != record['pid'] or record['pgid'] == record['session']:
            raise RuntimeError('Practice jobs must start after interactive job control is enabled')
        records[role] = record
        if role in config['review']['initial_stopped']: os.kill(record['pid'], signal.SIGSTOP)
    state['workers'] = records; write_json(STATE, state); publish_pids(config, state)


def restart_services():
    guard()
    config = json.loads(CONFIG.read_text()); state = json.loads(STATE.read_text())
    if config['kind'] not in ('process_signals', 'process_review') or not identity(state['supervisor'], False):
        raise RuntimeError('This lesson does not offer service restart')
    generation = state['generation']; write_json(CONTROL, {'restart': True})
    end = time.monotonic() + 6
    while time.monotonic() < end:
        if json.loads(STATE.read_text()).get('generation', 0) > generation:
            capture_trees(json.loads(STATE.read_text()))
            print('Practice services restarted; read the updated .pid files.'); return
        time.sleep(.05)
    raise RuntimeError('Practice service restart timed out')


def table(content):
    if content is None: return [], []
    lines = content.decode(errors='replace').splitlines()
    if not lines: return [], []
    aliases = {'TT': 'TTY', 'TNAME': 'TTY', 'COMMAND': 'CMD', 'COMM': 'CMD'}
    header = [aliases.get(name, name) for name in lines[0].split()]
    if len(set(header)) != len(header): return [], []
    rows = [line.split(None, len(header) - 1) for line in lines[1:] if line.strip()]
    return header, [dict(zip(header, row)) for row in rows if len(row) == len(header)]


def cpu_time(text):
    match = re.fullmatch(r'(?:(\d+)-)?(\d+):([0-5]\d):([0-5]\d)', text)
    if not match: return None
    days, hours, minutes, seconds = match.groups()
    if days is not None and int(hours) > 23: return None
    return int(days or 0) * 86400 + int(hours) * 3600 + int(minutes) * 60 + int(seconds)


def grade(m):
    guard(); start = validate(m)
    state = json.loads(STATE.read_text()); plan = m['review']; checks = []
    def check(label, value): checks.append(dict(label=label, passed=bool(value)))
    records = state.get('workers', {})
    check('연습 서비스 준비', set(records) == set(ROLES))
    if set(records) != set(ROLES): return {'passed': False, 'checks': checks}
    current = {role: identity(record) for role, record in records.items()}
    stopped = ['main'] if m['kind'] == 'process_stop' else ['spare'] if m['kind'] in ('process_signals', 'process_review') and m['practice'] == 2 else []
    finishing = m['kind'] in ('process_signals', 'process_review')
    if finishing:
        # Let the parent reap an already-dead child, not an arbitrary UI sleep.
        end = time.monotonic() + .5
        while time.monotonic() < end and len(state.get('exits', {})) < 2:
            state = json.loads(STATE.read_text()); time.sleep(.025)
        check('main 정상 정리 종료', state.get('exits', {}).get('main') == 0)
        check('blocker 강제 종료', state.get('exits', {}).get('blocker') == -signal.SIGKILL)
    active_roles = ('spare',) if finishing else ROLES
    correct_states = all(current[role] and
          (current[role]['state'] in ('T', 't') if role in stopped else current[role]['state'] not in ('T', 't', 'Z', 'X'))
          for role in active_roles)
    details = ', '.join(role + ': ' + (current[role]['state'] if current[role] else '원래 프로세스 없음') for role in active_roles)
    check('원래 PID와 목표 중지/실행 상태' + (' · ' + details if not correct_states else ''), correct_states)
    for name, kind in plan['reports'].items():
        content = read(start / name); header, rows = table(content)
        if kind in ('processes', 'subject'):
            targets = ('main',) if kind == 'subject' else ROLES
            valid = {'PID', 'TTY', 'TIME', 'CMD'} <= set(header)
            for role in targets:
                hits = [row for row in rows if row.get('PID') == str(records[role]['pid'])]
                elapsed = cpu_time(hits[0].get('TIME', '')) if len(hits) == 1 else None
                maximum = (current[role] or records[role]).get('cpu_seconds', 0)
                valid = valid and len(hits) == 1 and hits[0]['CMD'] == records[role]['name'] and hits[0]['TTY'] == '?' and (
                    elapsed is not None and int(records[role].get('cpu_seconds', 0)) <= elapsed <= int(maximum) + 1)
            if kind == 'subject': valid = valid and len(rows) == 1
        elif kind in ('threads', 'spare_threads'):
            record = records['spare' if kind == 'spare_threads' else 'main']
            valid = {'UID', 'PID', 'PPID', 'LWP', 'NLWP'} <= set(header) and len(rows) == len(record['tids']) and all(
                row.get('UID') in ('learner', '1100') and row.get('PID') == str(record['pid']) and
                row.get('PPID') == str(record['ppid']) and row.get('NLWP') == str(len(record['tids'])) for row in rows) and {
                    row.get('LWP') for row in rows} == {str(tid) for tid in record['tids']}
        elif kind == 'tree':
            text = (content or b'').decode(errors='replace')
            def normalized(value): return '\n'.join(line.rstrip() for line in value.expandtabs().strip('\n').splitlines())
            valid = normalized(text) in {normalized(value) for value in json.loads((ROOT / 'trees.json').read_text())}
        elif kind == 'count': valid = content is not None and content.strip() == str(len(records['main']['tids'])).encode()
        else: raise ValueError('Unknown process report')
        check(name + ' · 실제 대상 정보', valid)
    if plan['inventory']:
        actual = subprocess.check_output(['/bin/ls', '-alR', 'inventory'], cwd=start, env=dict(os.environ, LC_ALL='C.UTF-8'))
        check('inventory.txt · 전체 상세 목록', (read(start / 'inventory.txt') or b'').split() == actual.split())
    if plan['backup']: check('이전 프로세스 보고서 보관', read(start / 'previous processes.txt') == STALE)
    check('개인 파일·원본 자료·실행 도구 보존', read(start / 'personal.txt') == PERSONAL and
          read(start / 'inventory/.hidden') == b'hidden\n' and read(start / 'inventory/docs/read me.txt') == b'Process exercise data\n' and
          read(start / 'restart-services.sh') == m['_reference']['restart'].encode() and
          all(read(start / (role + '.pid')) == (str(record['pid']) + '\n').encode() for role, record in records.items()) and
          (not state.get('supervisor') or read(start / 'supervisor.pid') == (str(state['supervisor']['pid']) + '\n').encode()))
    return dict(passed=all(c['passed'] for c in checks), checks=checks)


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'worker': worker(int(sys.argv[2]), sys.argv[3], sys.argv[4], int(sys.argv[5]))
    else:
        guard()
        if action == 'claim': sys.exit(0 if claim(sys.argv[2]) else 1)
        if action == 'register': register(sys.argv[2], sys.argv[3:]); sys.exit(0)
        if action == 'supervise': supervise(); sys.exit(0)
        if action == 'restart': restart_services(); sys.exit(0)
        if action == 'snapshot':
            state = json.loads(STATE.read_text())
            state['current'] = {role: identity(record) for role, record in state.get('workers', {}).items()}
            print(json.dumps(state)); sys.exit(0)
        result = cleanup() if action == 'cleanup' else {'prepare': prepare, 'grade': grade}[action](json.load(sys.stdin))
        print(json.dumps(result))
