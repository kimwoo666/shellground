"""Bash exercise fixtures and behavioral grading inside the owned real guest."""
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import signal
import stat
import subprocess
import tempfile
import resource

if __package__:
    from .auth_lab import guard, read, parent_environment
else:
    from auth_lab import guard, read, parent_environment

BROKEN = '#!/bin/bash\nprintf "broken\\n"\n'
PERSONAL = b'Keep these personal notes.\n'
SOURCE = b'First handover line.\nSecond line with spaces.\n'


def validate(m):
    seed = m['seed']
    if type(seed) is not int or not 0 <= seed <= 9999: raise ValueError('Invalid shell seed')
    start = Path(f'/home/learner/shell/session{seed}')
    if m['start'] != str(start) or m['kind'] not in ('shell_path', 'shell_source', 'shell_args', 'shell_if', 'shell_noclobber', 'shell_review'):
        raise ValueError('Invalid owned shell exercise')
    if m['review']['script'] not in ('', 'arguments.sh', 'handover.sh', 'guard.sh', 'reports/guard.sh'):
        raise ValueError('Invalid script target')
    return start, m['review']


def signature(path):
    content = read(path)
    if content is None: return None
    info = path.lstat()
    return [hashlib.sha256(content).hexdigest(), stat.S_IMODE(info.st_mode), info.st_uid]


def prepare(m):
    guard()
    start, plan = validate(m)
    start.mkdir(parents=True, exist_ok=True)
    (start / 'reports').mkdir()
    os.chown(start, 1100, 1100); os.chown(start / 'reports', 1100, 1100)
    files = {'personal.txt': PERSONAL, 'source notes.txt': SOURCE,
             'settings.sh': ('export LAB_PROJECT=' + shlex.quote(plan['project']) + '\ncd ' + shlex.quote(str(start / 'reports')) + '\n').encode(),
             'child.sh': b'export LAB_PROJECT=child-only\nprintenv LAB_PROJECT\n',
             'broken.sh': BROKEN.encode()}
    for color in ('blue', 'green'):
        files['tools/' + color + '/sgtool'] = ('#!/bin/bash\nprintf "' + color + '-' + str(m['seed']) + '\\n"\n').encode()
    for name, content in files.items():
        path = start / name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content); path.chmod(0o755 if name.startswith('tools/') else 0o644); os.chown(path, 1100, 1100)
    if plan['script']:
        draft = BROKEN
        if m['practice'] == 1:
            draft = {'shell_args': '#!/bin/bash\nprintf "script=%s\\ncount=%s\\n" "$0" "$#"\nprintf "arg=%s\\n" "$*"\nprintf "joined=%s\\n" "$*"\n',
                     'shell_if': '#!/bin/bash\ncat -- "$1" > "$2"\n',
                     'shell_noclobber': '#!/bin/bash\nprintf "ready\\n" > "$1"\n'}.get(m['kind'], BROKEN)
        path = start / plan['script']; path.write_text(draft); os.chown(path, 1100, 1100)
    for name in ('result.txt', 'selected.txt', 'reports/project.txt', 'reports/location.txt'):
        path = start / name; path.write_text('obsolete\n'); os.chown(path, 1100, 1100)
    return {'ready': True, 'reference': {'preserved': {name: signature(start / name) for name in files}}}


def execute(argv, cwd, env=None):
    """Never run a learner-authored script as root, or leave its children alive."""
    with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
        def limits():
            resource.setrlimit(resource.RLIMIT_FSIZE, (1_000_000, 1_000_000))
            resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
            resource.setrlimit(resource.RLIMIT_CPU, (2, 3))
            resource.setrlimit(resource.RLIMIT_AS, (256 * 1024 ** 2, 256 * 1024 ** 2))
            resource.setrlimit(resource.RLIMIT_NPROC, (64, 64))
        process = subprocess.Popen(argv, cwd=cwd, env=env or dict(os.environ, LC_ALL='C.UTF-8'),
            user=1100, group=1100, extra_groups=[], stdin=subprocess.DEVNULL,
            stdout=output, stderr=errors, start_new_session=True, preexec_fn=limits)
        try:
            process.wait(timeout=3)
            output.seek(0); errors.seek(0)
            out, err = output.read(1_000_001), errors.read(1_000_001)
            if max(len(out), len(err)) > 1_000_000: return None, b'', b'output limit exceeded'
            return process.returncode, out, err
        except subprocess.TimeoutExpired:
            return None, b'', b'execution timed out'
        finally:
            try: os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError: pass
            process.wait()


def argument_output(script, args):
    return (f'script={script}\ncount={len(args)}\n' + ''.join('arg=' + arg + '\n' for arg in args) +
            'joined=' + ' '.join(args) + '\n').encode()


def probe(script, kind, start, check):
    if read(script) is None:
        check('일반 스크립트 파일 작성', False)
        return
    with tempfile.TemporaryDirectory(prefix='.shell-grade-', dir=start) as temporary:
        root = Path(temporary); root.chmod(0o700); os.chown(root, 1100, 1100)
        def put(name, content):
            path = root / name; path.write_bytes(content); os.chown(path, 1100, 1100); return path
        def run(*args): return execute(['/bin/bash', str(script), *args], root)
        if kind == 'shell_args':
            for args in (['one'], ['daily notes', '*.txt'], ['', 'a b', '*', '-n']):
                code, out, err = run(*args)
                check('다른 인자 경계·개수 ' + repr(args), code == 0 and out == argument_output(str(script), args) and not err)
        elif kind == 'shell_if':
            for number, content in enumerate((b'one line\n', '공백 경로의 다른 내용\n두 번째 줄\n'.encode())):
                source = put(f'source {number}.txt', content)
                target = root / f'result {number}.txt'
                code, _, _ = run(source.name, target.name)
                check('새 원본·공백 경로 인계 ' + str(number + 1), code == 0 and read(target) == content and read(source) == content)
            for args in ([], ['source 0.txt'], ['source 0.txt', 'result 0.txt', 'extra']):
                before = {p.name: signature(p) for p in root.iterdir()}
                code, out, err = run(*args)
                after = {p.name: signature(p) for p in root.iterdir()}
                check('인자 ' + str(len(args)) + '개 · 사용법/상태 2/파일 보존', code == 2 and not out and
                      err == f'usage: {script} SOURCE RESULT\n'.encode() and before == after)
        else:
            existing = put('existing notes.txt', b'Existing protected content\n')
            code, _, err = run(existing.name)
            check('기존 일반 파일 거절·보존', code not in (None, 0) and bool(err) and read(existing) == b'Existing protected content\n')
            for name in ('new notes.txt', 'second.txt'):
                code, _, _ = run(name)
                check('새 파일 작성 ' + name, code == 0 and read(root / name) == b'ready\n')


def grade(m):
    guard()
    start, plan = validate(m)
    checks = []
    def check(label, value): checks.append(dict(label=label, passed=bool(value)))
    environment = parent_environment() or {}
    kind = m['kind']
    if kind == 'shell_path':
        wanted = str(start / 'tools' / plan['desired'] / 'sgtool')
        path = environment.get('PATH', '')
        cwd = Path(environment.get('cwd', str(start)))
        search = ':'.join(str((cwd / item).resolve()) for item in path.split(':'))
        found = shutil.which('sgtool', path=search)
        check('현재 PATH 선택과 표준 도구 경로 유지', found is not None and str(Path(found).resolve()) == str(Path(wanted).resolve()) and
              {str(Path(item).resolve()) for item in ('/usr/bin', '/bin')} <= set(search.split(':')))
        if m['practice'] == 1:
            check('기존 green 도구 검색 경로 유지', str(start / 'tools/green') in
                  {str(Path(item).resolve()) for item in search.split(':')})
        selected = (read(start / 'selected.txt') or b'').decode(errors='replace').strip()
        check('선택 경로와 실행 결과', bool(selected) and str((cwd / selected).resolve()) == wanted and
              read(start / 'result.txt') == f'{plan["desired"]}-{m["seed"]}\n'.encode())
        check('pwd 내장 명령 구분', read(start / 'kind.txt') == b'pwd is a shell builtin\n')
        code, actual, _ = execute(['/usr/bin/whereis', 'bash'], start)
        check('bash 관련 위치 조사', code == 0 and (read(start / 'locations.txt') or b'').split() == actual.split())
        if m['practice'] == 2: check('reports로 이동 후 선택 유지', environment.get('cwd') == str(start / 'reports'))
    elif kind in ('shell_source', 'shell_review'):
        check('현재 셸 프로젝트·작업 위치', environment.get('LAB_PROJECT') == plan['project'] and
              environment.get('cwd') == str(start / 'reports'))
        check('현재 값과 위치 보고서', read(start / 'reports/project.txt') == (plan['project'] + '\n').encode() and
              read(start / 'reports/location.txt') == (str(start / 'reports') + '\n').encode())
        if m['practice'] == 2: check('자식의 별도 환경 결과', read(start / 'reports/child.txt') == b'child-only\n')
        if m['practice'] == 1: check('이전 프로젝트 보고서 보관', read(start / 'previous project.txt') == b'obsolete\n')
    if plan['script']:
        script = start / plan['script']
        probe(script, kind, start, check)
        if kind == 'shell_args':
            report = read(start / 'result.txt') or b''
            first = report.split(b'\n', 1)[0].decode(errors='replace')
            invoked = first.removeprefix('script=')
            try: same_script = bool(invoked) and (start / invoked).samefile(script)
            except OSError: same_script = False
            check('지정 인자 실행 보고서', first.startswith('script=') and same_script and
                  report == argument_output(invoked, ['daily notes', '*.txt']))
        elif kind == 'shell_if': check('문서 인계 결과', read(start / 'received notes.txt') == SOURCE)
        else: check('새 결과 파일', read(script.parent / 'fresh.txt') == b'ready\n')
    # Check preservation AFTER executing submitted scripts, so a side effect in
    # a behavioral probe cannot pass against an earlier snapshot.
    changed = [name for name, expected in m['_reference']['preserved'].items()
               if signature(start / name) != expected]
    if plan['backup'] and read(start / 'original script.txt') != BROKEN.encode(): changed.append('original script.txt (초안 복사본)')
    label = '준비된 자료·도구 보존' + ('과 초안 복사' if plan['backup'] else '')
    check(label + (' · 미충족: ' + ', '.join(changed) if changed else ''), not changed)
    return dict(passed=all(c['passed'] for c in checks), checks=checks)


if __name__ == '__main__':
    import sys
    guard()
    print(json.dumps({'prepare': prepare, 'grade': grade}[sys.argv[1]](json.load(sys.stdin))))
