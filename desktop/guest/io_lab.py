"""Real file and direct-exec grading for the owned I/O teaching fixture."""
import hashlib
from collections import Counter
import json
import os
from pathlib import Path
import re
import stat
import sys

if __package__:
    from .auth_lab import guard, read, parent_environment
    from .shell_lab import signature, execute
else:
    from auth_lab import guard, read, parent_environment
    from shell_lab import signature, execute

KEYS = ('io_input', 'io_pager', 'io_tree', 'io_binary', 'io_shebang', 'io_review')
PERSONAL = b'Personal I/O practice notes: preserve.\n'
OLD_ENTRY = b'Previous entry: keep for history.\n'
OLD_ANSWER = b'code=OLD\n'
BROKEN_BINARY = b'Damaged program, not an ELF executable.\n'
BAD_SCRIPT = b'#!/missing/bash\nprintf "directory=%s\\n" "$1"\n/bin/ls -1a -- "$1"\n'


def validate(m):
    seed = m['seed']; plan = m['review']
    if type(seed) is not int or not 0 <= seed <= 9999 or m['kind'] not in KEYS:
        raise ValueError('Invalid I/O exercise')
    if type(m['practice']) is not int or m['practice'] not in (0, 1, 2): raise ValueError('Invalid variant')
    start = Path(f'/home/learner/io/session{seed}')
    if m['start'] != str(start): raise ValueError('Invalid I/O root')
    if plan['binary'] not in ('', 'ls', 'tools/local ls') or plan['script'] not in ('', 'show-files.sh'):
        raise ValueError('Invalid executable target')
    if plan['backup'] not in ('', 'entry.txt', 'answer.txt', 'ls', 'show-files.sh'):
        raise ValueError('Invalid backup target')
    if set(plan['files']) - {'entry.txt', 'answer.txt', 'reports/source notes.txt'} or set(plan['reports']) - {'tree.txt', 'dirs.txt'}:
        raise ValueError('Invalid report target')
    return start, plan


def long_notes(seed):
    lines = [f'Reading note {i:03d}: keep the source document unchanged.' for i in range(1, 101)]
    lines[57:57] = ['RELEASE CHECKPOINT', f'code=R{seed}-READY', f'destination=dock-{seed % 5 + 1}', 'END CHECKPOINT']
    return ('\n'.join(lines) + '\n').encode()


def prepare(m):
    guard(); start, plan = validate(m)
    for folder in ('reports', 'tools', 'inventory/.hidden', 'inventory/docs/sub', 'inventory/src',
                   'inventory/empty', 'inventory/folder.deb', 'probe samples/empty', 'probe samples/two words'):
        (start / folder).mkdir(parents=True, exist_ok=True)
    files = {'personal.txt': PERSONAL, 'source notes.txt': b'Original handover notes.\n',
             'long notes.txt': long_notes(m['seed']),
             'correction notes.txt': f'destination=revised-{m["seed"] % 7}\n'.encode(),
             'inventory/.config': b'keep=yes\n', 'inventory/.hidden/settings.txt': b'secret=local\n',
             'inventory/docs/read me.txt': b'A document with spaces.\n', 'inventory/docs/.draft': b'draft\n',
             'inventory/docs/sub/check.txt': b'nested\n', 'inventory/src/main.py': b'print("hello")\n',
             'inventory/src/guide.txt': b'Guide that may be moved by the assigned repair.\n',
             'inventory/folder.deb/metadata': b'A directory is not a package file.\n',
             'inventory/bundle.deb': b'Training placeholder, not an install target.\n',
             'probe samples/two words/.hidden file': b'hidden\n', 'probe samples/two words/file B': b'b\n'}
    for name, content in files.items(): (start / name).write_bytes(content)
    if m['kind'] == 'io_input':
        if m['practice'] == 1: (start / 'entry.txt').write_bytes(OLD_ENTRY)
        elif m['practice'] == 2: (start / 'entry.txt').write_text(f'team=alpha\nrelease={m["seed"]}\n')
    if m['kind'] == 'io_pager' and m['practice'] == 1: (start / 'answer.txt').write_bytes(OLD_ANSWER)
    if m['kind'] == 'io_binary' and m['practice'] == 1:
        (start / 'ls').write_bytes(BROKEN_BINARY); (start / 'ls').chmod(0o644)
    if m['kind'] == 'io_shebang' and m['practice'] == 1:
        (start / 'show-files.sh').write_bytes(BAD_SCRIPT); (start / 'show-files.sh').chmod(0o755)
    for path in (start, *start.rglob('*')): os.chown(path, 1100, 1100)
    preserved = {name: signature(start / name) for name in files if not (plan['move'] and name == 'inventory/src/guide.txt')}
    directories = {str(p.relative_to(start)): directory_signature(p) for p in (start, *start.rglob('*')) if p.is_dir()}
    return {'ready': True, 'reference': {'preserved': preserved, 'directories': directories,
            'system_ls': signature(Path('/bin/ls')), 'moved': files['inventory/src/guide.txt'].decode()}}


def listing(path):
    try: code, output, _ = execute(['/bin/ls', '-1a', '--', str(path)], path.parent)
    except OSError: return None
    return output if code == 0 else None


def directory_signature(path):
    try:
        info = path.lstat()
        return [stat.S_IMODE(info.st_mode), info.st_uid, info.st_gid] if stat.S_ISDIR(info.st_mode) else None
    except OSError: return None


def same_names(actual, expected):
    # The goal specifies one name per line, not a particular sort order.
    return (actual is not None and expected is not None and actual.endswith(b'\n') and
            Counter(actual.splitlines()) == Counter(expected.splitlines()))


def script_output(actual, argument, expected):
    header = ('directory=' + argument + '\n').encode()
    return actual is not None and actual.startswith(header) and same_names(actual[len(header):], expected)


def tree_entries(root, dirs=False, depth=None):
    result = set()
    for path in root.rglob('*'):
        relative = path.relative_to(root)
        if depth is not None and len(relative.parts) > depth: continue
        if dirs and not path.is_dir(): continue
        result.add(relative.as_posix())
    return result


def parse_tree(content, root):
    """Compare hierarchy, not decorative charset, child ordering or footer."""
    if content is None: return None
    text = re.sub(r'\x1b\[[0-9;]*m', '', content.decode('utf-8', errors='replace')).replace('\xa0', ' ')
    lines = text.splitlines()
    if not lines: return None
    label = lines.pop(0).rstrip('/')
    if label not in ('.', 'inventory', './inventory', str(root)): return None
    paths, stack = set(), []
    for line in lines:
        if not line.strip() or re.fullmatch(r'\d+ director(?:y|ies)(?:, \d+ files?)?', line): continue
        match = re.search(r'(?:[├└]──|[|`+]--) ', line)
        if not match or match.start() % 4: return None
        prefix = line[:match.start()]
        if any(prefix[i:i+4] not in ('    ', '│   ', '|   ') for i in range(0, len(prefix), 4)): return None
        depth = match.start() // 4
        if depth > len(stack): return None
        name = line[match.end():]
        if not name or '/' in name or name in ('.', '..'): return None
        stack = stack[:depth] + [name]
        value = '/'.join(stack)
        if value in paths: return None
        paths.add(value)
    return paths


def owned_executable(path):
    try:
        info = path.lstat()
        return stat.S_ISREG(info.st_mode) and info.st_uid == 1100 and bool(info.st_mode & stat.S_IXUSR)
    except OSError: return False


def bash_header(content):
    if content is None: return False
    first = content.split(b'\n', 1)[0]
    return bool(re.fullmatch(rb'#![ \t]*(?:/(?:usr/)?bin/bash|/usr/bin/env[ \t]+bash)[ \t]*', first))


def direct(path, argument, cwd):
    try: return execute([str(path), argument], cwd)
    except OSError as exc: return None, b'', str(exc).encode()


def grade(m):
    guard(); start, plan = validate(m); reference = m['_reference']; checks = []
    def check(label, passed): checks.append(dict(label=label, passed=bool(passed)))
    kind, variant = m['kind'], m['practice']
    for name, content in plan['files'].items(): check('내용·줄 순서 · ' + name, read(start / name) == content.encode())
    if plan['backup']:
        target, content = {'entry.txt': ('previous entry.txt', OLD_ENTRY), 'answer.txt': ('previous answer.txt', OLD_ANSWER),
                           'ls': ('previous tool', BROKEN_BINARY), 'show-files.sh': ('previous script.txt', BAD_SCRIPT)}[plan['backup']]
        check('변경 전 자료 보관 · ' + target, read(start / target) == content)
    if plan['move']:
        check('잘못 배치된 문서 이동·내용과 검토 폴더',
              not os.path.lexists(start / 'inventory/src/guide.txt') and
              read(start / 'inventory/docs/handover guide.txt') == reference['moved'].encode() and
              (start / 'inventory/docs/review').is_dir() and not (start / 'inventory/docs/review').is_symlink())
    for name, options in plan['reports'].items():
        actual = parse_tree(read(start / name), start / 'inventory')
        check('트리 계층·숨김·깊이 범위 · ' + name, actual == tree_entries(start / 'inventory', **options))
    if plan['binary']:
        binary = start / plan['binary']; content = read(binary)
        genuine = content is not None and hashlib.sha256(content).hexdigest() == reference['system_ls'][0]
        success = False
        if genuine and owned_executable(binary):
            code, output, errors = direct(binary, '-a', start / 'probe samples/two words')
            success = code == 0 and output == listing(start / 'probe samples/two words') and not errors
        check('learner 소유·원본 바이트·실행 권한 및 다른 폴더의 직접 실행', genuine and owned_executable(binary) and success)
        report = start / ('reports/names.txt' if kind == 'io_binary' and variant == 2 else 'names.txt')
        names_ok = same_names(read(report), listing(start / 'inventory'))
        if kind != 'io_review': check('요청한 이름 목록 인계', names_ok)
    if plan['script']:
        script = start / plan['script']; header = bash_header(read(script)); executable = owned_executable(script)
        outcomes = []
        probes = [(argument, start) for argument in ('inventory', 'probe samples/two words', 'probe samples/empty')]
        if kind == 'io_shebang' and variant == 2: probes.append(('../inventory/docs', start / 'reports'))
        if header and executable:
            for argument, cwd in probes:
                code, out, err = direct(script, argument, cwd)
                outcomes.append(code == 0 and script_output(out, argument, listing(cwd / argument)) and not err)
        check('Bash 해석기·실행 권한 및 다른 공백 경로의 직접 실행', header and executable and len(outcomes) == len(probes) and all(outcomes))
        run_ok = script_output(read(start / 'run.txt'), 'inventory', listing(start / 'inventory'))
        check('이름 목록·스크립트 실행 결과 인계' if kind == 'io_review' else '스크립트 실행 결과 인계',
              run_ok and (names_ok if kind == 'io_review' else True))
        if kind == 'io_shebang' and variant == 2:
            check('다른 위치에서 경로 인자 전달', script_output(read(start / 'reports/docs.txt'), '../inventory/docs', listing(start / 'inventory/docs')))
    if variant == 2 and kind in ('io_binary', 'io_shebang'):
        check('reports에서 작업 마침', (parent_environment() or {}).get('cwd') == str(start / 'reports'))
    damaged = [name for name, expected in reference['preserved'].items() if signature(start / name) != expected]
    damaged += [name + '/' for name, expected in reference['directories'].items() if directory_signature(start / name) != expected]
    if signature(Path('/bin/ls')) != reference['system_ls']: damaged.append('/bin/ls')
    check('준비 자료·권한·원본 보존' + (': ' + ', '.join(damaged) if damaged else ''), not damaged)
    return {'passed': all(row['passed'] for row in checks), 'checks': checks}


if __name__ == '__main__':
    mission = json.load(sys.stdin)
    action = sys.argv[1]
    if action not in ('prepare', 'grade'): raise SystemExit('Unknown I/O helper action')
    print(json.dumps(globals()[action](mission)))
