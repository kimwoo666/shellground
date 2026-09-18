"""Miniconda installation outcome checks, only inside the owned Linux guest.

This observes a newly allocated installation, not the learner's command history.
All new executables run as learner, never as the root inspection process.
"""
import hashlib
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import uuid

BASE = Path('/opt/shellground/miniconda')
ASSETS = Path('/opt/shellground/conda-setup')
WORK = Path('/home/learner/setup-practice')
STATE = Path('/opt/shellground/conda-setup-attempt.json')
PROFILES = ('.bashrc', '.bash_profile', '.profile', '.condarc')


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            value.update(block)
    return value.hexdigest()


def files_identity(paths):
    result = {}
    for path in paths:
        # Configuration symlinks are changes too; do not follow unexpected ones.
        result[str(path)] = ('symlink:' + os.readlink(path) if path.is_symlink()
                             else digest(path) if path.is_file() else None)
    return result


def base_identity():
    return files_identity([BASE/'bin/python', BASE/'bin/python3.12', BASE/'bin/conda',
                           BASE/'conda-meta/history', BASE/'.condarc',
                           *sorted((BASE/'conda-meta').glob('*.json'))])


def profiles_identity():
    return files_identity([Path('/home/learner')/name for name in PROFILES])


def package_identity(prefix):
    records={}
    for path in (prefix/'conda-meta').glob('*.json'):
        if not contained_file(path,prefix):continue
        value=json.loads(path.read_text())
        if value.get('name') in ('conda','python'):
            records[value['name']]={key:value.get(key) for key in ('name','version','build','subdir')}
    return records


def conda_sources():
    return {str(path.relative_to(BASE)):digest(path)
            for path in (BASE/'lib/python3.12/site-packages/conda').rglob('*.py')}


def installed_conda_matches(target,state):
    if not state['conda_sources']:return False
    launcher=target/'bin/conda'
    if not contained_file(launcher,target):return False
    expected=(BASE/'bin/conda').read_text().replace(str(BASE),str(target))
    if launcher.read_text()!=expected:return False
    return all(contained_file(target/name,target) and digest(target/name)==checksum
               for name,checksum in state['conda_sources'].items())


def python_binary_matches(target):
    original=(BASE/'bin/python').read_bytes()
    installed=(target/'bin/python').read_bytes()
    if original==installed:return True
    # Conda relocates embedded prefixes in ELF files and preserves NUL padding.
    # Use the protected installed Conda's own relocation routine in memory,
    # never alter either binary, and compare all remaining bytes unchanged.
    # API reference: conda/core/portability.py::binary_replace.
    from conda.core.portability import binary_replace
    return (binary_replace(original,str(BASE).encode(),b'/sg',subdir='linux-64') ==
            binary_replace(installed,str(target).encode(),b'/sg',subdir='linux-64'))


def environment():
    return dict(PATH='/usr/bin:/bin', HOME='/home/learner', USER='learner', LOGNAME='learner',
                LANG='C.UTF-8', LC_ALL='C.UTF-8', CONDA_OFFLINE='true', CONDA_NO_PLUGINS='true',
                CONDA_REPORT_ERRORS='false', CONDA_SOLVER='classic',
                CONDARC='/opt/shellground/condarc', OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1')


def run(argv):
    process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, text=True, cwd='/tmp', env=environment(),
        user=1100, group=1100, extra_groups=[], start_new_session=True)
    try:
        out, err = process.communicate(timeout=35)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid, signal.SIGKILL)
        process.communicate(timeout=3)
        raise ValueError('새 설치의 실행 확인 시간이 초과됐습니다.')
    if process.returncode:
        raise ValueError((err or out or '실행 실패')[-1000:])
    return out


def assets():
    from installer_sources import installer_for
    spec = installer_for()
    installer = ASSETS/spec['name']
    if (ASSETS.resolve() != ASSETS or installer.is_symlink() or
            not installer.is_file() or digest(installer) != spec['sha256']):
        raise ValueError('이 런타임에는 검증된 설치 실습 파일이 없습니다. 설치 실습을 지원하는 런타임이 필요합니다.')
    if installer.stat().st_uid != 0 or installer.stat().st_mode & 0o022:
        raise ValueError('설치 파일은 학습자가 변경할 수 없는 읽기 전용 자료여야 합니다.')
    return dict(spec, path=str(installer), license=(ASSETS/'LICENSE.txt').read_text())


def prepare():
    spec = assets()
    if WORK.resolve() != WORK:
        raise ValueError('설치 실습 폴더가 다른 위치를 가리킵니다.')
    WORK.mkdir(mode=0o755, exist_ok=True)
    os.chown(WORK, 1100, 1100)
    target = WORK/('miniconda-'+uuid.uuid4().hex[:10])
    if target.exists() or target.is_symlink():
        raise ValueError('새 설치 대상이 이미 존재합니다. 덮어쓰지 않습니다.')
    info = json.loads(run([str(BASE/'bin/conda'), 'info', '--json']))
    if info['root_prefix'] != str(BASE) or info['platform'] != spec['subdir']:
        raise ValueError('관리용 Conda와 설치 파일의 실제 플랫폼이 일치하지 않습니다.')
    state = dict(prefix=str(target), installer=spec, base=base_identity(), profiles=profiles_identity(),
                 packages=package_identity(BASE), conda_sources=conda_sources())
    STATE.write_text(json.dumps(state, ensure_ascii=False))
    STATE.chmod(0o600)
    # Clear only our fixed shell-initialization directive, not a user's profile.
    Path('/opt/shellground/conda-initial-env').write_text('')
    return dict(start=str(WORK), prefix=str(target), installer=spec, runtime=info)


def contained_file(path, prefix):
    return path.is_file() and path.resolve().is_relative_to(prefix) and path.resolve() != prefix


def grade(expected_prefix):
    state = json.loads(STATE.read_text())
    target = Path(state['prefix'])
    if expected_prefix != str(target):
        raise ValueError('현재 설치 실습의 대상과 채점 요청이 다릅니다.')
    checks = []

    def check(label, passed, detail=''):
        checks.append(dict(label=label, passed=bool(passed), detail=detail))

    distinct = (target.parent == WORK and target.resolve() == target and not target.is_symlink()
                and target.is_dir() and target != BASE)
    check('배정된 새 경로에 독립 설치', distinct, str(target))
    metadata = False
    if distinct:
        try:
            records = package_identity(target)
            metadata = (set(records)=={'conda','python'} and records==state['packages'] and
                        contained_file(target/'conda-meta/history', target))
        except (OSError, ValueError, KeyError):
            pass
    check('Conda·Python 설치 기록 존재', metadata, '빈 폴더나 출력 문구만으로는 완료되지 않습니다.')
    binary = distinct and all(contained_file(target/'bin'/name, target) for name in ('conda', 'python'))
    python_identity = False
    if binary:
        # A copied wrapper around the old Python must not count as a new Python.
        try:binary = python_binary_matches(target) and installed_conda_matches(target,state)
        except (OSError,ValueError):binary=False
    info_ok = False
    detail = '새 설치의 실행 파일이 아직 준비되지 않았습니다.'
    if binary and metadata:
        try:
            info = json.loads(run([str(target/'bin/conda'), 'info', '--json']))
            info_ok = (info.get('root_prefix') == str(target) and
                       info.get('platform') == state['installer']['subdir'] and bool(info.get('conda_version')))
            code = 'import json,sys,conda;print(json.dumps(dict(prefix=sys.prefix, executable=sys.executable, version=list(sys.version_info[:2]), conda_file=conda.__file__, conda_version=conda.__version__)))'
            observed = json.loads(run([str(target/'bin/python'), '-I', '-c', code]))
            python_identity = (observed['prefix'] == str(target) and
                Path(observed['executable']).resolve().is_relative_to(target) and observed['version'] == [3, 12] and
                Path(observed['conda_file']).resolve().is_relative_to(target) and
                observed['conda_version']==state['packages']['conda']['version'])
            detail = 'root_prefix='+str(info.get('root_prefix'))+'\nsys.prefix='+str(observed.get('prefix'))
        except (OSError, ValueError, KeyError) as error:
            detail = str(error)
    check('새 경로의 Conda 실행·플랫폼 일치', info_ok, detail)
    check('새 경로의 Python 실행·소속 일치', python_identity, detail)
    check('관리용 base 보존', base_identity() == state['base'])
    check('셸 시작 설정 보존', profiles_identity() == state['profiles'], '이 실습에서는 conda init이 필요하지 않습니다.')
    return dict(passed=all(c['passed'] for c in checks), checks=checks,
                evidence='new-installation-state; not command-history or historical installer exit status')


def main():
    sys.path.insert(0, '/opt/shellground')
    from agent import require_guest
    require_guest()
    if os.getuid() != 0:
        raise RuntimeError('Guest inspector requires root; learner executables never run as root')
    os.environ.update(environment())
    payload = json.load(sys.stdin)
    result = prepare() if sys.argv[1] == 'prepare' else grade(payload['prefix'])
    print(json.dumps(result, ensure_ascii=False))


if __name__ == '__main__':
    main()
