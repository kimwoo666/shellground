"""Real dpkg/APT fixtures and outcome grading; no command emulation.

Called only by the guarded lab inside Shellground's disposable guest.
"""
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile

NOTE = 'shellground-note'
HELPER = 'shellground-helper'
PACKAGES = (NOTE, HELPER)
CONF = Path('/etc/shellground-note.conf')
REPOSITORY = Path('/opt/shellground/apt-repo')
PERSONAL = b'My own notes. Not a package configuration file.\n'
STALE = b'Outdated handover: verify the real package state.\n'
RETIRED = 'shellground-retired-note'
RETIRED_CONF = Path('/etc/shellground-retired-note.conf')
RETIRED_TEXT = b'status=retired\nteam=previous\n'


def require_guest():
    from agent import require_guest as guard
    guard()
    if os.getuid() != 0:
        raise RuntimeError('Package fixture/inspection requires the owned guest service')


def run(*argv, required=True):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        timeout=30, env=dict(os.environ, LC_ALL='C', DEBIAN_FRONTEND='noninteractive'))
    if required and result.returncode:
        raise RuntimeError('Package fixture command failed: ' + ' '.join(argv) + '\n' + result.stderr[-1500:])
    return result


def package_states():
    text = run('dpkg-query', '-W', '-f=${Package}\t${Version}\t${Status}\n').stdout
    return {row[0]: row[1:] for line in text.splitlines() if len(row := line.split('\t')) == 3}


def read(path):
    try:
        info = Path(path).lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 2_000_000:
            return None
        return Path(path).read_bytes()
    except OSError:
        return None


def outside(states, retired=False):
    excluded = (*PACKAGES, RETIRED) if retired else PACKAGES
    return {name: value for name, value in states.items() if name not in excluded}


def apt_rows(text):
    """Ignore headings/order/automatic flag, not installed/candidate versions."""
    rows = []
    for line in text.splitlines():
        fields = line.split()
        if fields and '/' in fields[0] and fields[0].split('/')[0] in PACKAGES:
            if len(fields) < 3: return None
            status = re.search(r'\[([^]]+)\]', line)
            status = status.group(1) if status else ''
            change = re.search(r'upgradable (from|to):\s*([^, ]+)', status)
            rows.append((fields[0].split('/')[0], fields[1], fields[2],
                         'installed' if status.startswith('installed') else 'upgradable' if change else '',
                         tuple(change.groups()) if change else ()))
    return sorted(rows)


def dpkg_rows(text):
    rows = {}
    for line in text.splitlines():
        fields = line.split()
        if len(fields) >= 4 and fields[1].split(':')[0] in PACKAGES:
            name = fields[1].split(':')[0]
            if name in rows: return None
            rows[name] = fields[:1] + fields[2:4]
    return rows


def prepare_retired():
    """A separate real, tiny conffile package makes review outcomes coexist."""
    run('dpkg', '--purge', RETIRED)
    with tempfile.TemporaryDirectory(prefix='shellground-retired-package-') as folder:
        root = Path(folder)
        package = root / 'package'
        (package / 'DEBIAN').mkdir(parents=True)
        (package / 'DEBIAN/control').write_text('Package: ' + RETIRED + '\nVersion: 1.0\nArchitecture: all\n'
            'Maintainer: Shellground <training@example.invalid>\nDescription: Retired configuration exercise\n')
        (package / 'DEBIAN/conffiles').write_text(str(RETIRED_CONF) + '\n')
        (package / 'etc').mkdir()
        (package / 'etc' / RETIRED_CONF.name).write_bytes(RETIRED_TEXT)
        deb = root / 'retired.deb'
        run('dpkg-deb', '--build', '--root-owner-group', str(package), str(deb))
        run('dpkg', '-i', str(deb))
        run('dpkg', '--remove', RETIRED)


def prepare(mission):
    require_guest()
    plan = mission['review']
    start = Path(mission['start'])
    if not re.fullmatch(r'/home/learner/packages/session[0-9]+', str(start)):
        raise ValueError('Invalid package exercise path')
    # Refuse missing fixtures before modifying any package. These tiny debs
    # already belong to the published offline image; do not contact the host.
    for name in PACKAGES:
        for version in ('1.0', '2.0'):
            if not (REPOSITORY / f'{name}_{version}_all.deb').is_file():
                raise RuntimeError('Offline package fixture missing: ' + name)
    # Package exercise, not a service restart exercise. Keep needrestart's
    # real analysis visible but list-only in this disposable guest; do not
    # restart the app's control/fixture services as an incidental APT hook.
    needrestart = Path('/etc/needrestart/conf.d')
    if needrestart.is_dir():
        (needrestart / 'shellground-apt.conf').write_text("$nrconf{restart} = 'l';\n")
    run('dpkg', '--purge', NOTE, HELPER)
    run('apt-get', 'update')
    run('dpkg', '-i', str(REPOSITORY / f'{HELPER}_1.0_all.deb'),
        str(REPOSITORY / f'{NOTE}_1.0_all.deb'))
    if plan['helper'] == '2.0':
        run('dpkg', '-i', str(REPOSITORY / f'{HELPER}_2.0_all.deb'))
    if plan['note'] == '2.0':
        run('dpkg', '--unpack' if plan['broken'] else '-i', str(REPOSITORY / f'{NOTE}_2.0_all.deb'))
    if plan['helper'] is None:
        # Deliberately break only the two named fixture packages, never an OS
        # dependency. Students repair with normal APT, not this setup command.
        run('dpkg', '--remove', '--force-depends', HELPER)
    CONF.write_text(plan['config'])
    CONF.chmod(0o644)
    if plan['removed']: run('apt-get', 'remove', '-y', NOTE)
    if plan.get('retired'): prepare_retired()
    start.mkdir(parents=True, exist_ok=True)
    for path in (start.parent, start): os.chown(path, 1100, 1100)
    for name, content in (('personal.txt', PERSONAL), ('packages.txt', STALE),
                          ('installed.txt', STALE), ('updates.txt', STALE)):
        if name == 'packages.txt' and plan.get('stale_removed_report'):
            content = b'rc  shellground-note 2.0 all Note\nii  shellground-helper 2.0 all Helper\n'
        path = start / name
        path.write_bytes(content)
        os.chown(path, 1100, 1100)
    return {'ready': True, 'reference': {'apt_outside': outside(package_states(), plan.get('retired', False))}}


def grade(mission):
    require_guest()
    plan, start = mission['review'], Path(mission['start'])
    states = package_states()
    checks = []
    def check(label, passed): checks.append(dict(label=label, passed=bool(passed)))
    def status(name): return states.get(name, ['', 'unknown ok not-installed'])
    note_version, note_state = status(NOTE)
    if plan['expected_note'] == 'absent':
        check('note · 패키지와 잔여 설정 상태 제거',
              note_state.split()[-1] == 'not-installed' and not CONF.exists() and not CONF.is_symlink())
    else:
        check('note · ' + plan['expected_note'] + ' / ' + plan['expected_version'],
              note_state.split()[-1] == plan['expected_note'] and note_version == plan['expected_version'])
    helper_version, helper_state = status(HELPER)
    check('helper · 설치 완료 / ' + plan['expected_helper'],
          helper_state.split()[-1] == 'installed' and helper_version == plan['expected_helper'] and
          read('/usr/share/' + HELPER + '/version.txt') == (plan['expected_helper'] + '\n').encode())
    expected_payload = ((plan['expected_version'] + '\n').encode() if plan['expected_note'] == 'installed' else None)
    note_path = Path('/usr/share/' + NOTE + '/version.txt')
    check('note · 설치 파일 상태', read(note_path) == expected_payload if expected_payload is not None else
          not note_path.exists() and not note_path.is_symlink())
    if plan['preserve_config']:
        check('/etc/shellground-note.conf · 원래 설정 유지', read(CONF) == plan['config'].encode())
    if plan['backup']:
        check('note config backup.txt · 원래 설정 보관', read(start / 'note config backup.txt') == plan['config'].encode())
    if plan.get('backup_report'):
        check('installed backup.txt · 기존 보고서 보관', read(start / 'installed backup.txt') == STALE)
    if plan.get('retired'):
        check('retired-note · 패키지 관리자의 잔여 설정 정리', status(RETIRED)[1].split()[-1] == 'not-installed')
        check('retired-note · 원래 설정 경로 제거', not RETIRED_CONF.exists() and not RETIRED_CONF.is_symlink())
        check('retired config backup.txt · 폐기 전 설정 보관', read(start / 'retired config backup.txt') == RETIRED_TEXT)
    check('personal.txt · 개인 문서 유지', read(start / 'personal.txt') == PERSONAL)
    check('다른 패키지 · 설치 상태와 버전 유지', outside(states, plan.get('retired', False)) == mission['_reference']['apt_outside'])
    for filename, kind in plan['reports'].items():
        content = read(start / filename)
        text = content.decode(errors='replace') if content is not None else ''
        if kind in ('installed', 'upgradable'):
            expected = run('apt', 'list', '--' + kind, *PACKAGES).stdout
            rows = apt_rows(expected)
            passed = bool(text.strip()) and apt_rows(text) == rows
            # Explicit empty-list representation; no hidden heading requirement.
            if not rows: passed = content is not None and (not text.strip() or text.strip() == expected.strip())
        else:
            expected = run('dpkg', '-l', *PACKAGES, required=False).stdout
            passed = bool(text.strip()) and dpkg_rows(text) == dpkg_rows(expected)
        check(filename + ' · 작업 후 조회 결과', passed)
    return {'passed': all(c['passed'] for c in checks), 'checks': checks}


if __name__ == '__main__':
    import json
    import sys
    require_guest()
    operation = {'prepare': prepare, 'grade': grade}[sys.argv[1]]
    print(json.dumps(operation(json.load(sys.stdin))))
