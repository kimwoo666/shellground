"""Verified offline assets, copied only into our disposable Linux guest."""
import base64
import hashlib
import json
from pathlib import Path
import sys
from engine import LabError, resource_path


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(chunk)
    return value.hexdigest()


def assets():
    manifest = json.loads(resource_path('notebook_teaching/assets-linux-x86_64.json').read_text())
    if manifest.get('schema') != 1 or manifest.get('platform') != 'linux-x86_64':
        raise LabError('검증된 Jupyter 설치 자료가 없습니다.')
    directory = resource_path('notebook_teaching/wheels-linux-x86_64')
    if not directory.is_dir() and not getattr(sys, 'frozen', False):
        directory = Path(__file__).resolve().parents[1] / '.jupyter-build/wheels-linux-x86_64'
    names = set()
    for wheel in manifest['wheels']:
        name = wheel['filename']
        if name in names or Path(name).name != name or not name.endswith('.whl'):
            raise LabError('Jupyter 설치 파일 목록 오류')
        names.add(name)
        path = directory / name
        if path.is_symlink() or not path.is_file() or path.stat().st_size != wheel['size'] or digest(path) != wheel['sha256']:
            raise LabError('Jupyter 설치 파일이 없거나 변경되었습니다: ' + name)
    return directory, manifest


TRANSFER = '''import hashlib, os, re, sys
from pathlib import Path
sys.path.insert(0, '/opt/shellground')
from agent import require_guest
require_guest()
assert os.getuid() == 0
directory = Path('/opt/shellground/notebook-assets')
directory.mkdir(mode=0o755, exist_ok=True)
assert not directory.is_symlink() and directory.stat().st_uid == 0
assert not directory.stat().st_mode & 0o022
action, name, expected = sys.argv[1:4]
assert re.fullmatch(r'[A-Za-z0-9_.-]+', name) and name not in ('.', '..')
target = directory / name
temporary = directory / ('.' + name + '.upload')
def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): value.update(block)
    return value.hexdigest()
if action == 'check':
    valid = target.is_file() and not target.is_symlink() and target.stat().st_uid == 0
    valid = valid and not target.stat().st_mode & 0o022
    print('ready' if valid and digest(target) == expected else 'missing')
elif action == 'begin':
    assert not temporary.is_symlink()
    with temporary.open('wb'): temporary.chmod(0o600)
elif action == 'chunk':
    assert temporary.is_file() and not temporary.is_symlink() and temporary.stat().st_uid == 0
    assert temporary.stat().st_size == int(sys.argv[4]) and not temporary.stat().st_mode & 0o077
    chunk = sys.stdin.buffer.read(1024 * 1024 + 1)
    assert len(chunk) <= 1024 * 1024
    with temporary.open('ab') as stream: stream.write(chunk)
elif action == 'finish':
    assert not temporary.is_symlink() and digest(temporary) == expected
    temporary.chmod(0o644); temporary.replace(target)
else: raise ValueError('Unknown transfer action')
'''


def upload(channel, name, content):
    sha = hashlib.sha256(content).hexdigest()
    def call(action, data=b'', offset=0):
        result = channel.request('exec', timeout=20, run_timeout=15, root=True, cwd='/tmp',
            argv=['python3', '-c', TRANSFER, action, name, sha, str(offset)],
            input=base64.b64encode(data).decode())
        if result['code']:
            raise LabError('노트북 자산 준비 실패: ' + base64.b64decode(result['err']).decode(errors='replace')[-1200:])
        return base64.b64decode(result['out']).decode().strip()
    if call('check') == 'ready':
        return
    call('begin')
    for offset in range(0, len(content), 1024 * 1024):
        call('chunk', content[offset:offset + 1024 * 1024], offset)
    call('finish')


def install_assets(channel, status=lambda value: None):
    directory, manifest = assets()
    for i, wheel in enumerate(manifest['wheels'], 1):
        status(f'Jupyter 실행 파일 준비 {i}/{len(manifest["wheels"])}')
        upload(channel, wheel['filename'], (directory / wheel['filename']).read_bytes())
    upload(channel, 'manifest.json', json.dumps(manifest).encode())
    for name in ('guest_setup.py', 'guest_service.py', 'guest_lessons.py'):
        upload(channel, name, resource_path('notebook_teaching/' + name).read_bytes())
    from conda_teaching.pip_assets import install_assets as numpy_assets
    numpy_assets(channel)
