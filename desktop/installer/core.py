"""Single-download Linux setup. Only verified, pinned release data is installed."""
import contextlib
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import tarfile
import threading
import urllib.request

OWNER = 'shellground-setup-v1'


class Cancelled(Exception):
    pass


def checksum(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def atomic_json(path, value):
    temporary = path.with_name(path.name + '.new')
    if temporary.is_symlink():
        raise ValueError('Unsafe temporary file')
    with temporary.open('w', encoding='utf-8') as stream:
        json.dump(value, stream)
        stream.flush()
        os.fsync(stream.fileno())
    temporary.replace(path)


def safe_file(path):
    if path.is_symlink() or (path.exists() and not path.is_file()):
        raise ValueError('설치 경로에 안전하지 않은 파일이 있습니다: ' + str(path))


class Setup:
    def __init__(self, root, manifest, progress=lambda *args: None, cancel=None, opener=None):
        self.root = Path(root)
        self.manifest = manifest
        self.progress = progress
        self.cancel = cancel or threading.Event()
        self.opener = opener or urllib.request.urlopen
        self.version = manifest['version']
        if self.version != '4.7.4':
            raise ValueError('Unsupported setup version')
        self.base_url = manifest['base_url']
        if self.base_url != 'https://github.com/kimwoo666/shellground/releases/download/v4.7.4-preview/':
            raise ValueError('Untrusted release endpoint')

    def check_cancel(self):
        if self.cancel.is_set():
            raise Cancelled('취소했습니다. 다음 실행 때 확인된 지점부터 이어 받습니다.')

    @contextlib.contextmanager
    def locked(self):
        if self.root.is_symlink():
            raise ValueError('설치 폴더는 링크일 수 없습니다.')
        self.root.mkdir(parents=True, exist_ok=True)
        owner = self.root / '.shellground-installer'
        if owner.exists():
            safe_file(owner)
            if owner.read_text() != OWNER:
                raise ValueError('다른 프로그램의 설치 폴더입니다.')
        elif any(self.root.iterdir()):
            raise ValueError('비어 있는 설치 폴더를 사용하세요.')
        else:
            owner.write_text(OWNER)
        lock = self.root / '.setup.lock'
        safe_file(lock)
        with lock.open('a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('다른 Shellground 설치창이 이미 실행 중입니다.')
            yield

    def receive(self, record, target, offset=0, overall=0, total=None):
        """Stream into the final disk: never keep a second 8 GB set of chunks."""
        self.check_cancel()
        safe_file(target)
        request = urllib.request.Request(self.base_url + record['name'],
            headers={'User-Agent': 'Shellground-Setup/4.7.4'})
        digest = hashlib.sha256()
        used = 0
        with target.open('r+b' if target.exists() else 'w+b') as output:
            output.truncate(offset)
            output.seek(offset)
            try:
                with self.opener(request, timeout=15) as response:
                    while True:
                        self.check_cancel()
                        block = response.read(256 * 1024)
                        if not block:
                            break
                        used += len(block)
                        if used > record['bytes']:
                            raise ValueError('다운로드 크기가 예상과 다릅니다.')
                        output.write(block)
                        digest.update(block)
                        self.progress('실습 자료 내려받는 중', overall + used,
                            total or record['bytes'])
                if used != record['bytes'] or digest.hexdigest() != record['sha256']:
                    raise ValueError('다운로드 검증 실패. 다시 시작하면 해당 자료만 다시 받습니다.')
                output.flush()
                os.fsync(output.fileno())
            except BaseException:
                output.truncate(offset)
                raise

    def download_disk(self, destination):
        spec = self.manifest['disk']
        pending = destination.with_name('base.qcow2.partial')
        checkpoint = destination.with_name('download-state.json')
        for path in (destination, pending, checkpoint):
            safe_file(path)
        if destination.is_file():
            self.progress('기존 실습 자료 확인 중', 0, 0)
            if destination.stat().st_size == spec['bytes'] and checksum(destination) == spec['sha256']:
                return
            raise ValueError('기존 실습 자료가 변경됐습니다. 다른 빈 폴더에 설치하세요.')
        done = 0
        if checkpoint.exists() and pending.exists():
            state = json.loads(checkpoint.read_text())
            if state.get('sha256') == spec['sha256']:
                done = int(state.get('completed', 0))
        if not 0 <= done <= len(spec['parts']):
            done = 0
        offset = sum(p['bytes'] for p in spec['parts'][:done])
        if not pending.exists() or pending.stat().st_size < offset:
            done = offset = 0
        if shutil.disk_usage(destination.parent).free < spec['bytes'] - offset + 256 * 1024**2:
            raise ValueError('설치에는 약 9GB의 여유 공간이 필요합니다.')
        for index, part in enumerate(spec['parts'][done:], done):
            self.receive(part, pending, offset, offset, spec['bytes'])
            offset += part['bytes']
            atomic_json(checkpoint, {'sha256': spec['sha256'], 'completed': index + 1})
        self.check_cancel()
        self.progress('다운로드 완료 · 전체 파일 확인 중', spec['bytes'], spec['bytes'])
        if pending.stat().st_size != spec['bytes'] or checksum(pending) != spec['sha256']:
            atomic_json(checkpoint, {'sha256': spec['sha256'], 'completed': 0})
            raise ValueError('전체 파일 검증에 실패했습니다. 다시 시도하세요.')
        pending.replace(destination)
        checkpoint.unlink(missing_ok=True)

    def install(self):
        with self.locked():
            final = self.root / ('app-' + self.version)
            receipt = final / 'installed.json'
            if final.is_symlink():
                raise ValueError('Unsafe application directory')
            if receipt.exists() and json.loads(receipt.read_text()).get('disk_sha256') == self.manifest['disk']['sha256']:
                if not (final / 'Shellground').is_file():
                    raise ValueError('설치 실행파일이 없습니다.')
                return final
            if final.exists():
                raise ValueError('같은 버전의 기존 폴더가 있습니다. 빈 설치 폴더를 선택하세요.')
            incoming = self.root / '.incoming-4.7.4'
            if incoming.is_symlink():
                raise ValueError('Unsafe installation staging')
            incoming.mkdir(exist_ok=True)
            app = incoming / 'Shellground-Linux'
            ready = incoming / 'app-ready.json'
            record = self.manifest['linux']
            if not ready.exists():
                payload = self.root / 'application.tar.partial'
                if not (payload.is_file() and checksum(payload) == record['sha256']):
                    self.receive(record, payload)
                self.check_cancel()
                self.progress('프로그램 설치 중', 0, 0)
                with tarfile.open(payload) as archive:
                    for member in archive:
                        self.check_cancel()
                        if not member.name.startswith('Shellground-Linux/'):
                            raise ValueError('Unexpected application archive path')
                        archive.extract(member, incoming, filter='data')
                atomic_json(ready, {'sha256': record['sha256']})
                payload.unlink()
            elif json.loads(ready.read_text()).get('sha256') != record['sha256']:
                raise ValueError('설치 자료 버전이 다릅니다.')
            self.download_disk(app / 'runtime/linux-x86_64/base.qcow2')
            self.check_cancel()
            (app / 'Shellground').chmod(0o755)
            atomic_json(app / 'installed.json', {'owner': OWNER, 'version': self.version,
                'disk_sha256': self.manifest['disk']['sha256']})
            app.rename(final)
            ready.unlink(missing_ok=True)
            incoming.rmdir()
            return final


def register_launcher(app, icon, data_root):
    """A normal per-user applications-menu entry, never a root install."""
    applications = Path(data_root) / 'applications'
    icons = Path(data_root) / 'icons/hicolor/scalable/apps'
    applications.mkdir(parents=True, exist_ok=True)
    icons.mkdir(parents=True, exist_ok=True)
    icon_target = icons / 'shellground.svg'
    safe_file(icon_target)
    shutil.copyfile(icon, icon_target)
    executable = str(app / 'Shellground')
    if '\n' in executable or '\r' in executable:
        raise ValueError('Unsupported launcher path')
    quoted = executable.replace('\\', '\\\\').replace('"', '\\"').replace('`', '\\`').replace('$', '\\$').replace('%', '%%')
    desktop = applications / 'shellground.desktop'
    safe_file(desktop)
    desktop.write_text('[Desktop Entry]\nType=Application\nName=Shellground\n'
        'Comment=Linux, Docker, ROS 2 and Python practice\n'
        'Comment[ko]=Linux · Docker · ROS 2 · Python 학습\n'
        'Exec="' + quoted + '"\nIcon=shellground\nTerminal=false\nCategories=Education;Development;\n', encoding='utf-8')
    return desktop
