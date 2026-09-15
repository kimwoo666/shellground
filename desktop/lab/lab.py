"""Fixture creation and filesystem grading, executed only inside the lab container."""
import functools
import base64
import http.server
import json
import os
from pathlib import Path
import re
import shutil
import stat
import subprocess
import sys
import tarfile
import tempfile
import zipfile

FIXTURES = Path('/srv/fixtures')
README = b'Shellground training bundle\nVersion 1.0\n'
HELLO = b'#!/bin/sh\nprintf "Hello from Linux\\n"\n'
MESSAGE = b'Extracted from a real Debian package.\n'
SCRIPT = b'#!/bin/sh\nset -eu\n# Write a receipt at the path supplied as the first argument.\nprintf "Linux script completed\\n" > "$1"\n'


def fixtures():
    FIXTURES.mkdir(parents=True, exist_ok=True)
    (FIXTURES / 'setup.sh').write_bytes(SCRIPT)
    with tempfile.TemporaryDirectory() as temp:
        root = Path(temp)
        (root / 'bin').mkdir()
        (root / 'README.txt').write_bytes(README)
        (root / 'bin/hello.sh').write_bytes(HELLO)
        (root / 'bin/hello.sh').chmod(0o755)
        with tarfile.open(FIXTURES / 'bundle.tar.gz', 'w:gz') as archive:
            archive.add(root / 'README.txt', arcname='README.txt')
            archive.add(root / 'bin', arcname='bin')
        with zipfile.ZipFile(FIXTURES / 'bundle.zip', 'w') as archive:
            archive.write(root / 'README.txt', 'README.txt')
            archive.write(root / 'bin/hello.sh', 'bin/hello.sh')
        package = root / 'package'
        (package / 'DEBIAN').mkdir(parents=True)
        (package / 'DEBIAN/control').write_text('Package: shellground-toolkit\nVersion: 1.0\nArchitecture: all\nMaintainer: Shellground <lab@example.invalid>\nDescription: Offline command training fixture\n')
        (package / 'usr/share/shellground').mkdir(parents=True)
        (package / 'usr/share/shellground/message.txt').write_bytes(MESSAGE)
        subprocess.run(['dpkg-deb', '--build', '--root-owner-group', str(package), str(FIXTURES / 'toolkit.deb')], check=True)


def tree_paths(m):
    index = m['seed'] % 3
    return ['.cache', '.metadata', '.private'][index], ['nested/deep', 'releases/linux/amd64', 'packages/current'][index]


def prepare(m):
    source, target = Path(m['source']), Path(m['target'])
    hidden, nested = tree_paths(m)
    for path in [Path(m['start']), source / 'docs', source / hidden, source / nested, source / 'folder.deb', target, Path(m['report']).parent]:
        path.mkdir(parents=True, exist_ok=True)
    samples = {
        'guide.txt': f"Release {m['seed']} user guide\n".encode(),
        '.env': b'LAB_MODE=training\n',
        'docs/read me.txt': b'A file name with spaces\n',
        'docs/.draft': b'Hidden document\n',
        nested + '/events.log': b'INFO start\nERROR stop\n',
        hidden + '/.state': b'Cached state\n',
        'app.log': b'INFO start\nERROR disk full\nwarning warm\nerror timeout\nINFO ready\nError network\n',
    }
    for name, contents in samples.items():
        (source / name).write_bytes(contents)
    if m['kind'] == 'pwdpaths':
        (Path(m['start']) / 'shortcut').symlink_to(source / 'docs', target_is_directory=True)
    if m['kind'] == 'lsoptions':
        (source / 'large-sample.bin').write_bytes(b'X' * 16384)
    for name in ['toolkit.deb', hidden + '/extra.deb', nested + '/agent.deb']:
        shutil.copyfile(FIXTURES / 'toolkit.deb', source / name)
    for name in ['setup.sh', 'bundle.tar.gz', 'bundle.zip']:
        shutil.copyfile(FIXTURES / name, source / name)
    (target / 'draft.txt').write_text(f"Draft {m['seed']}\n")
    (target / 'obsolete.txt').write_text('Remove this file\n')
    if m['kind'] == 'edit': (target / 'note.txt').write_text('status=draft\n')
    if m['kind'] == 'permissions': (target / 'local.sh').write_bytes(HELLO)
    for item in m.get('review', {}).get('setup', []):
        path = Path(item['path'])
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(item['text'])
    for path in source.rglob('*'):
        os.utime(path, (1700000000, 1700000000))
    os.utime(source, (1700000000, 1700000000))
    reference = {}
    if m['kind'] == 'lsintro':
        reference['names'] = subprocess.check_output(['ls', '-1a', str(source)], text=True, timeout=5).splitlines()
    if m['kind'] in ('list', 'long', 'recursive', 'mixed'):
        option = {'list': '-1a', 'long': '-al', 'recursive': '-alR', 'mixed': '-al'}[m['kind']]
        reference['listing'] = subprocess.check_output(['ls', option, str(source)], text=True, timeout=5)
    if m['kind'] == 'lsoptions':
        for suffix, option in [('names', '-1A'), ('sizes', '-alh'), ('largest', '-1S')]:
            reference[suffix] = subprocess.check_output(['ls', option, str(source)], text=True, timeout=5)
    reference['review'] = {}
    for index, goal in enumerate(m.get('review', {}).get('goals', [])):
        if goal['type'] == 'copy':
            reference['review'][str(index)] = base64.b64encode(Path(goal['source']).read_bytes()).decode()
        elif goal['type'] == 'listing':
            reference['review'][str(index)] = subprocess.check_output(['ls', goal['options'], goal['source']], text=True, timeout=5)
    return {'ready': True, 'reference': reference}


def read_regular(path):
    """Never follow links or block on a user-created FIFO during grading."""
    try:
        if not stat.S_ISREG(path.lstat().st_mode) or path.stat().st_size > 2_000_000:
            return None
        return path.read_bytes()
    except OSError:
        return None


def long_records(text, root, recursive):
    """Compare ls records, accepting absolute/relative headings and option order."""
    sections = {}
    section = ''
    for line in text.splitlines():
        if not line.strip() or line.startswith('total '):
            continue
        if line.endswith(':'):
            heading = line[:-1].rstrip('/')
            if heading in ('.', root, Path(root).name) or heading.endswith('/' + Path(root).name):
                section = ''
            elif heading.startswith('./'):
                section = heading[2:]
            elif heading.startswith(root + '/'):
                section = heading[len(root) + 1:]
            elif '/' + Path(root).name + '/' in '/' + heading:
                section = ('/' + heading).split('/' + Path(root).name + '/', 1)[1]
            else:
                section = heading
            continue
        fields = line.split(None, 8)
        if len(fields) != 9 or not re.fullmatch(r'[bcdlps-][rwxstST-]{9}[.+@]?', fields[0]):
            return None
        # Preserve every displayed field, but ignore horizontal alignment padding.
        sections.setdefault(section, []).append(tuple(fields))
    return {k: sorted(v) for k, v in sections.items()}


def grade_base(m):
    source, target, report = Path(m['source']), Path(m['target']), Path(m['report'])
    checks = []
    def check(label, passed):
        checks.append({'label': label, 'passed': bool(passed)})
    kind = m['kind']
    output = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', m.get('_terminal_output', ''))
    if kind in ('navigate', 'mixed'):
        try:
            pid = Path('/tmp/shellground.pid').read_text().strip()
            cwd = os.readlink(f'/proc/{int(pid)}/cwd')
        except (OSError, ValueError):
            cwd = ''
        if kind == 'navigate':
            check('셸의 현재 위치가 목표 docs 폴더', cwd == str(source / 'docs'))
        else:
            check('셸의 현재 위치가 목표 폴더', cwd == str(source))
            content = read_regular(report)
            actual = long_records(content.decode(errors='replace'), str(source), False) if content is not None else None
            expected = long_records(m['_reference']['listing'], str(source), False)
            check('숨김 포함 상세 보고서', actual is not None and actual == expected)
    elif kind == 'pwdpaths':
        lines = output.splitlines()
        check('화면에 논리 경로 출력', m['start'] + '/shortcut' in lines)
        check('화면에 실제 경로 출력', str(source / 'docs') in lines)
    elif kind == 'lsintro':
        check('화면에 숨김 포함 전체 목록 출력', set(m['_reference']['names']).issubset(set(output.split())))
    elif kind == 'report':
        check('보고서에 시작 위치 저장', read_regular(report) == (m['start'] + '\n').encode())
    elif kind == 'mkdir':
        check('practice 폴더 생성', (target / 'practice').is_dir())
    elif kind == 'touch':
        check('notes.txt 빈 일반 파일 생성', read_regular(target / 'notes.txt') == b'')
    elif kind == 'read':
        expected = f"Release {m['seed']} user guide"
        check('파일 내용이 화면에 출력됨', expected in output.splitlines())
        check('원본 내용 보존', read_regular(source / 'guide.txt') == (expected + '\n').encode())
    elif kind == 'edit':
        check('note.txt를 status=ready로 수정하고 저장', read_regular(target / 'note.txt') == b'status=ready\n')
    elif kind == 'duplicate':
        expected = f"Release {m['seed']} user guide\n".encode()
        check('원본 보존', read_regular(source / 'guide.txt') == expected)
        check('manual.txt 복사본 생성', read_regular(target / 'manual.txt') == expected)
    elif kind == 'rename':
        check('draft.txt가 final.txt로 변경됨', not os.path.lexists(target / 'draft.txt') and read_regular(target / 'final.txt') == f"Draft {m['seed']}\n".encode())
    elif kind == 'remove':
        check('obsolete.txt 삭제', not os.path.lexists(target / 'obsolete.txt'))
        check('draft.txt 보존', read_regular(target / 'draft.txt') == f"Draft {m['seed']}\n".encode())
    elif kind == 'permissions':
        path = target / 'local.sh'
        check('내용 보존', read_regular(path) == HELLO)
        check('소유자 실행 권한 추가', path.exists() and bool(path.stat().st_mode & stat.S_IXUSR))
    elif kind == 'lsoptions':
        for suffix, label in [('names', '숨김 포함, .과 .. 제외'), ('sizes', '숨김·상세·읽기 쉬운 크기'), ('largest', '숨김 제외 큰 크기순 이름')]:
            content = read_regular(Path(str(report) + '.' + suffix))
            actual = content.decode(errors='replace') if content is not None else ''
            expected = m['_reference'][suffix]
            if suffix == 'sizes':
                matched = long_records(actual, str(source), False) == long_records(expected, str(source), False)
            else:
                actual_lines, expected_lines = actual.splitlines(), expected.splitlines()
                matched = (sorted(actual_lines) == sorted(expected_lines) if suffix == 'names' else actual_lines == expected_lines)
            check(label + ' 보고서', content is not None and matched)
    elif kind == 'workspace':
        check('공백을 포함한 목표 폴더 생성', (target / 'daily notes').is_dir())
        check('done.txt가 빈 일반 파일', read_regular(target / 'daily notes/done.txt') == b'')
    elif kind == 'copy':
        guide = f"Release {m['seed']} user guide\n".encode()
        check('원본 guide.txt 보존', read_regular(source / 'guide.txt') == guide)
        check('manual.txt에 원본 내용 복사', read_regular(target / 'manual.txt') == guide)
        check('draft.txt를 final.txt로 이동', not os.path.lexists(target / 'draft.txt') and read_regular(target / 'final.txt') == f"Draft {m['seed']}\n".encode())
        check('obsolete.txt 삭제', not os.path.lexists(target / 'obsolete.txt'))
    elif kind in ('list', 'long', 'recursive'):
        content = read_regular(report)
        check('지정한 경로와 이름의 보고서 생성', content is not None)
        if content is not None:
            decoded = content.decode('utf-8', errors='replace')
            if kind == 'list':
                expected = m['_reference']['listing'].splitlines()
                check('숨김 항목을 포함한 바로 아래 항목 전체', sorted(decoded.splitlines()) == sorted(expected))
            else:
                expected = m['_reference']['listing']
                actual_records = long_records(decoded, str(source), kind == 'recursive')
                expected_records = long_records(expected, str(source), kind == 'recursive')
                check('숨김·상세 정보' + ('와 모든 하위 폴더 목록' if kind == 'recursive' else '가 있는 전체 목록'), actual_records is not None and actual_records == expected_records)
    elif kind == 'grep':
        expected = b'ERROR disk full\nerror timeout\nError network\n'
        check('대소문자 무관 error 줄 3개를 순서대로 기록', read_regular(report) == expected)
        check('개수 파일에 3 기록', (read_regular(Path(str(report) + '.count')) or b'').strip() == b'3')
    elif kind == 'find':
        hidden, nested = tree_paths(m)
        expected = sorted(str(source / name) for name in ['toolkit.deb', hidden + '/extra.deb', nested + '/agent.deb'])
        content = read_regular(report)
        check('숨김 폴더 포함 .deb 일반 파일의 절대 경로', content is not None and sorted(content.decode(errors='replace').splitlines()) == expected)
    elif kind in ('curl', 'wget', 'archive', 'script', 'deb'):
        downloaded = target / ('received-' + m['artifact'])
        check('지정한 이름·경로에 원본과 동일한 파일 저장', read_regular(downloaded) == (FIXTURES / m['artifact']).read_bytes())
        if kind == 'archive':
            check('압축 해제: README.txt 복원', read_regular(target / 'unpacked/README.txt') == README)
            check('압축 해제: bin/hello.sh 복원', read_regular(target / 'unpacked/bin/hello.sh') == HELLO)
        elif kind == 'script':
            check('소유자 실행 권한 추가', downloaded.exists() and bool(downloaded.stat().st_mode & stat.S_IXUSR))
            check('스크립트 결과 receipt.txt 생성', read_regular(target / 'receipt.txt') == b'Linux script completed\n')
        elif kind == 'deb':
            check('패키지 내용 복원', read_regular(target / 'unpacked/usr/share/shellground/message.txt') == MESSAGE)
    else:
        raise ValueError('Unknown mission kind')
    return {'passed': bool(checks) and all(c['passed'] for c in checks), 'checks': checks}


def grade(m):
    review = m.get('review', {})
    if not review: return grade_base(m)
    checks = grade_base(m)['checks'] if review.get('keep_base') else []
    output = re.sub(r'\x1b\[[0-?]*[ -/]*[@-~]', '', m.get('_terminal_output', ''))
    labels = {'dir': '폴더 생성', 'absent': '이전 경로 제거', 'copy': '원본 내용 보존',
              'file': '파일 내용', 'stripped_file': '집계 값', 'cwd': '현재 위치',
              'output': '화면 출력', 'output_contains': '화면 내용', 'listing': '목록 형식과 내용',
              'file_contains': '파일에 필수 내용 포함', 'executable': '실행 권한'}
    for index, goal in enumerate(review['goals']):
        kind = goal['type']
        path = Path(goal.get('path', '/tmp/unused'))
        content = read_regular(path) if kind in ('copy', 'file', 'stripped_file', 'listing', 'file_contains') else None
        if kind == 'dir': passed = path.is_dir()
        elif kind == 'absent': passed = not os.path.lexists(path)
        elif kind == 'file': passed = content == goal['text'].encode()
        elif kind == 'stripped_file': passed = content is not None and content.strip() == goal['text'].encode()
        elif kind == 'copy': passed = content == base64.b64decode(m['_reference']['review'][str(index)])
        elif kind == 'file_contains': passed = content is not None and goal['text'].encode() in content
        elif kind == 'cwd':
            try:
                pid = int(Path('/tmp/shellground.pid').read_text().strip())
                passed = os.readlink(f'/proc/{pid}/cwd') == str(path)
            except (OSError, ValueError): passed = False
        elif kind == 'output': passed = output.splitlines().count(goal['text']) >= goal.get('count', 1)
        elif kind == 'output_contains': passed = goal['text'] in output
        elif kind == 'executable': passed = path.is_file() and bool(path.stat().st_mode & stat.S_IXUSR) == goal['value']
        elif kind == 'listing':
            expected = m['_reference']['review'][str(index)]
            actual = content.decode(errors='replace') if content is not None else ''
            if 'R' in goal['options']:
                passed = content is not None and long_records(actual, goal['source'], True) == long_records(expected, goal['source'], True)
            else:
                def records(text): return [line.split(None, 8) for line in text.splitlines() if line.strip() and not line.startswith('total ')]
                passed = content is not None and records(actual) == records(expected)
        else: raise ValueError('Unknown review goal ' + kind)
        checks.append({'label': labels[kind] + ': ' + goal.get('path', goal.get('text', '')), 'passed': bool(passed)})
    return {'passed': bool(checks) and all(c['passed'] for c in checks), 'checks': checks}


if __name__ == '__main__':
    action = sys.argv[1]
    if action == 'fixtures':
        fixtures()
    elif action == 'serve':
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(FIXTURES))
        http.server.ThreadingHTTPServer(('127.0.0.1', 8765), handler).serve_forever()
    else:
        mission = json.load(sys.stdin)
        print(json.dumps(prepare(mission) if action == 'prepare' else grade(mission)))
