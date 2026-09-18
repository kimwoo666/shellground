"""Copy the pinned official wheel into an owned, disposable Linux guest.

The existing control protocol has a 4 MiB line limit. Transfer bounded chunks,
then verify the whole SHA before atomically publishing the read-only asset.
This never installs a package on the host or modifies the immutable VM image.
"""
import base64
from pathlib import Path
import sys

from engine import LabError, resource_path
from .pip_wheel import NUMPY_WHEEL, load_numpy_wheel


def wheel_path():
    packaged=resource_path('conda_teaching/wheels')/NUMPY_WHEEL['filename']
    if packaged.is_file():return packaged
    if not getattr(sys,'frozen',False):
        source=Path(__file__).resolve().parents[1]/'.conda-build'/NUMPY_WHEEL['filename']
        if source.is_file():return source
    raise LabError('이 배포본에 검증된 NumPy 설치 파일이 없습니다. 개인 Python이나 온라인 설치로 대신하지 않습니다.')


TRANSFER = '''import hashlib, os, sys
from pathlib import Path
sys.path.insert(0, '/opt/shellground')
from agent import require_guest
require_guest()
assert os.getuid() == 0
directory = Path('/opt/shellground/wheels')
directory.mkdir(mode=0o755, exist_ok=True)
assert not directory.is_symlink() and directory.stat().st_uid == 0
assert not directory.stat().st_mode & 0o022
action, name, expected = sys.argv[1:4]
assert Path(name).name == name and name.endswith('.whl')
target = directory / name
temporary = directory / ('.' + name + '.upload')
def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''):
            value.update(block)
    return value.hexdigest()
if action == 'check':
    valid = target.is_file() and not target.is_symlink() and target.stat().st_uid == 0
    valid = valid and not target.stat().st_mode & 0o022
    if valid: valid = digest(target) == expected
    print('ready' if valid else 'missing')
elif action == 'begin':
    assert not temporary.is_symlink()
    with temporary.open('wb'):
        temporary.chmod(0o600)
elif action == 'chunk':
    assert temporary.is_file() and not temporary.is_symlink()
    assert temporary.stat().st_uid == 0 and not temporary.stat().st_mode & 0o077
    assert temporary.stat().st_size == int(sys.argv[4])
    chunk = sys.stdin.buffer.read(1024 * 1024 + 1)
    assert len(chunk) <= 1024 * 1024
    with temporary.open('ab') as stream:
        stream.write(chunk)
elif action == 'finish':
    assert temporary.is_file() and not temporary.is_symlink()
    assert digest(temporary) == expected
    temporary.chmod(0o644)
    temporary.replace(target)
else:
    raise ValueError('Unknown wheel transfer action')
'''


def install_assets(channel):
    path=wheel_path()
    # Validate metadata and every RECORD hash, not just a filename.
    load_numpy_wheel(path)
    def call(action,data=b'',offset=0):
        result=channel.request('exec',timeout=25,run_timeout=20,root=True,cwd='/tmp',
            argv=['python3','-c',TRANSFER,action,NUMPY_WHEEL['filename'],NUMPY_WHEEL['sha256'],str(offset)],
            input=base64.b64encode(data).decode())
        if result['code']:raise LabError('NumPy 설치 파일 준비 실패: '+base64.b64decode(result['err']).decode(errors='replace')[-1000:])
        return base64.b64decode(result['out']).decode().strip()
    if call('check')=='ready':return
    call('begin')
    with path.open('rb') as stream:
        offset=0
        for chunk in iter(lambda:stream.read(1024*1024),b''):
            call('chunk',chunk,offset);offset+=len(chunk)
    call('finish')
    if call('check')!='ready':raise LabError('NumPy 설치 파일 검증에 실패했습니다.')
