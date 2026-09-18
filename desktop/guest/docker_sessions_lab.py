"""Outcomes from the real guest Docker daemon, including genuine interactive shells."""
import base64
import gzip
import hashlib
import io
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile
import uuid

if __package__:
    from .docker_lab import DockerLab, IMAGE
else:
    from docker_lab import DockerLab, IMAGE


def archive_signature(path, compressed=True):
    """Read bounded members; never extract submitted archive paths or run its code."""
    try:
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_size > 64 * 1024 * 1024: return None
        with path.open('rb') as source:
            if compressed and source.read(2) != b'\x1f\x8b': return None
        hashes = {}; manifest = None; total = 0
        with tarfile.open(path, 'r:gz' if compressed else 'r:') as archive:
            for index, member in enumerate(archive):
                total += member.size
                if index > 4096 or total > 64 * 1024 * 1024 or member.size < 0: return None
                if not member.isfile(): continue
                name = member.name.removeprefix('./')
                if name in hashes: return None
                stream = archive.extractfile(member)
                digest = hashlib.sha256()
                if name == 'manifest.json':
                    if member.size > 1024 * 1024: return None
                    data = stream.read(); digest.update(data); manifest = json.loads(data)
                else:
                    for chunk in iter(lambda: stream.read(65536), b''): digest.update(chunk)
                hashes[name] = digest.hexdigest()
        if not isinstance(manifest, list): return None
        result = {}
        for row in manifest:
            config = hashes[row['Config']]; layers = [hashes[name] for name in row['Layers']]
            for tag in row.get('RepoTags') or []:
                if tag in result: return None
                result[tag] = [config, layers]
        return result or None
    except (OSError, ValueError, KeyError, TypeError, tarfile.TarError, EOFError): return None


class SessionLab(DockerLab):
    def prepare(self, mission):
        from agent import require_guest
        require_guest()
        seed = mission['seed']; p = mission['review']; key = p['docker_sessions']; v = mission['practice']
        if (type(seed) is not int or not 0 <= seed <= 9999 or type(v) is not int or v not in (0, 1, 2) or
            key not in ('interactive', 'attach', 'exec', 'archive', 'prune', 'review') or
            mission['start'] != f'/home/learner/docker/session{seed}' or
            p['name'] != f'sgs{seed}-shell' or p['tag'] != f'training/handover{seed}:v1' or p['label'] != f'shellground.cleanup={seed}'):
            raise ValueError('Invalid owned Docker session fixture')
        self.base_mission = dict(mission, review={'docker_real': 'sessions', 'files': {'keep.txt': 'unrelated document\n', 'output/.keep': 'keep output\n'},
                                                'file_goals': {'keep.txt': 'unrelated document\n', 'output/.keep': 'keep output\n'}})
        super().prepare(self.base_mission)
        self.baseline_tags = {tag: self.inspect('image', tag).get('Id') for tag in self.baseline['tags'] if tag != '<none>:<none>'}
        self.mission = mission; self.key = key; self.variant = v; self.name = p['name']
        self.temp = tempfile.TemporaryDirectory(prefix='session-lab-', dir='/opt/shellground')
        self.original_files = {}; self.protected = {}; self.tags = {}; self.absent = []
        self.session_code = 'session-' + uuid.uuid4().hex
        self.note = f'original {seed}\n'
        if key in ('attach', 'exec', 'review') or key == 'interactive' and v == 1:
            bootstrap = Path(self.temp.name) / 'shell-init'
            bootstrap.write_text(f'if [ "$$" -eq 1 ]; then SESSION_CODE={self.session_code}; fi\nPS1="sg-session# "\n')
            self.docker('create', '-it', '--name', self.name, '-e', 'ENV=/shell-init',
                        '--mount', f'type=bind,src={bootstrap},dst=/shell-init,readonly', IMAGE, '/bin/sh', required=True)
            note = Path(self.temp.name) / 'note.txt'; note.write_text(self.note)
            self.docker('cp', str(note), self.name + ':/note.txt', required=True)
            if key == 'attach' and v == 1:
                previous = Path(self.temp.name) / 'session.txt'; previous.write_text('previous session\n')
                self.docker('cp', str(previous), self.name + ':/session.txt', required=True)
            self.docker('start', self.name, required=True)
            if key == 'interactive' or key == 'attach' and v == 2:
                self.docker('kill', self.name, required=True); self.docker('wait', self.name, required=True)
            else:
                self.docker('exec', self.name, 'sh', '-c', 'mkdir -p /work "/work notes"; chown 1100:1100 "/work notes"', required=True)
            self.original_shell = self.inspect('container', self.name)
        if key in ('archive', 'review'):
            tags = [p['tag']] + ([p['tag'].replace(':v1', ':v2')] if key == 'archive' and v == 2 else [])
            for tag in tags:
                # Tagging really shares an image; no synthetic layers or fake sizes.
                self.docker('tag', IMAGE, tag, required=True); self.tags[tag] = self.inspect('image', tag)['Id']
            raw = Path(self.temp.name) / 'images.tar'
            self.docker('save', '-o', str(raw), *tags, required=True)
            self.archive_expected = archive_signature(raw, compressed=False)
            if not self.archive_expected: raise RuntimeError('Actual Docker archive unavailable')
            if key == 'archive' and v == 1:
                target = self.start / 'received image.tar.gz'
                with raw.open('rb') as source, gzip.open(target, 'wb') as dest:
                    for chunk in iter(lambda: source.read(65536), b''): dest.write(chunk)
                os.chown(target, 1100, 1100); self.original_files[target] = hashlib.sha256(target.read_bytes()).hexdigest()
                self.docker('image', 'rm', p['tag'], required=True)
            if key == 'archive' and v == 2:
                target = self.start / 'image inventory.txt'; target.write_text('old inventory\n'); os.chown(target, 1100, 1100)
        if key in ('prune', 'review'):
            label = p['label'] + ('-failed' if key == 'prune' and v == 2 else '')
            for index in range(2):
                name = f'sgs{seed}-discard{index}'
                command = f'printf "receipt {seed}\\n" > /receipt.txt; printf "incident {seed}\\n" >&2; exit {33 if v == 2 else 0}'
                self.docker('run', '-d', '--name', name, '--label', label, IMAGE, 'sh', '-c', command, required=True)
                self.docker('wait', name, required=True); self.absent.append(name)
            for suffix, command, matching in (('running', 'exec sleep 3600', True), ('finished', 'exit 0', False)):
                name = f'sgs{seed}-{suffix}'
                self.docker('run', '-d', '--name', name, '--label', label if matching else 'shellground.keep=yes', IMAGE,
                            'sh', '-c', f'printf "preserve {seed}\\n" > /keep-me.txt; ' + command, required=True)
                if suffix == 'finished': self.docker('wait', name, required=True)
                info = self.inspect('container', name)
                self.protected[name] = [info['Id'], info['State']['Running'], info['State']['StartedAt'], info['State']['ExitCode']]
        return {'ready': True, 'reference': {}}

    def file_in_container(self, name, path):
        try:
            result = subprocess.run(['/usr/bin/docker', 'cp', name + ':' + path, '-'], stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, timeout=5)
            if result.returncode or len(result.stdout) > 1024 * 1024: return None
            with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
                files = [m for m in archive if m.isfile()]
                if len(files) != 1 or files[0].size > 1024 * 1024: return None
                item = files[0]
                return archive.extractfile(item).read().decode(), item.uid, item.gid
        except (OSError, ValueError, UnicodeError, tarfile.TarError, subprocess.TimeoutExpired): return None

    def grade(self, mission):
        p = mission['review']; key = self.key; v = self.variant; seed = mission['seed']; checks = []
        def check(label, value): checks.append(dict(label=label, passed=bool(value)))
        def file(path, text, owner=None):
            result = self.file_in_container(self.name, path)
            return result is not None and result[0] == text and (owner is None or result[1:] == owner)
        shell = self.inspect('container', self.name)
        state = shell.get('State', {}); config = shell.get('Config', {})
        if key == 'interactive':
            if v == 2:
                good = bool(shell) and not state.get('Running') and state.get('ExitCode') == 0 and config.get('Tty') and config.get('OpenStdin')
                good = good and shell.get('Image') == self.inspect('image', IMAGE).get('Id') and self.read(self.start / 'output/daily note.txt') == f'export {seed}\n'
                good = good and any(m.get('Type') == 'bind' and m.get('Source') == str(self.start / 'output') and m.get('Destination') == '/out' and m.get('RW') for m in shell.get('Mounts', []))
            else:
                expected = f'hello {seed}\n' if v == 0 else self.note + f'resumed {seed}\n'
                good = bool(shell) and not state.get('Running') and state.get('ExitCode') == (0 if v == 0 else 7) and file('/note.txt', expected)
                good = good and config.get('Tty') and config.get('OpenStdin') and shell.get('Image') == self.inspect('image', IMAGE).get('Id')
                if v == 1: good = good and shell.get('Id') == self.original_shell['Id'] and state.get('StartedAt') != self.original_shell['State']['StartedAt']
            check('입력 터미널·자료·주 셸 종료 및 요청한 정리', good)
        if key in ('attach', 'exec', 'review'):
            same = shell.get('Id') == self.original_shell['Id'] and file('/note.txt', self.note)
            if key == 'attach' and v == 2:
                same = same and not state.get('Running') and state.get('ExitCode') == 9 and state.get('StartedAt') != self.original_shell['State']['StartedAt']
            else:
                same = same and state.get('Running') and state.get('StartedAt') == self.original_shell['State']['StartedAt']
            check('원래 컨테이너·주 프로세스 수명과 원본 보존', same)
            if key in ('attach', 'review'):
                check('주 셸의 관측값과 이전 보고 보존', file('/session.txt', self.session_code + '\n') and
                      (key != 'attach' or v != 1 or file('/previous-session.txt', 'previous session\n')))
            if key in ('exec', 'review'):
                if key == 'review': good = file('/work/child.txt', 'child\n')
                elif v == 0: good = file('/work/child.txt', 'child\n') and file('/work/private.txt', 'unset\n')
                elif v == 1:
                    good = file('/work/mode.txt', 'review\n') and file('/work/location.txt', '/work\n') and config.get('Env') == self.original_shell['Config']['Env']
                else: good = file('/work notes/copied note.txt', self.note, (1100, 1100)) and file('/work notes/location.txt', '/work notes\n', (1100, 1100))
                check('보조 프로세스 결과·환경 범위·실제 파일 소유권', good)
        if key in ('archive', 'review'):
            restored = all(self.inspect('image', tag).get('Id') == identity for tag, identity in self.tags.items())
            if key == 'archive' and v == 1:
                good = restored and self.read(self.start / 'restored-id.txt') == self.tags[p['tag']] + '\n'
            else: good = restored and archive_signature(self.start / 'image backup.tar.gz') == self.archive_expected
            if key == 'archive' and v == 2:
                good = good and self.read(self.start / 'previous inventory.txt') == 'old inventory\n' and self.read(self.start / 'image inventory.txt') == ''.join(value + '\n' for value in self.tags.values())
            check('실제 이미지 설정·레이어·태그와 압축 인계', good)
        if key in ('prune', 'review'):
            good = all(not self.inspect('container', name) for name in self.absent)
            for name, expected in self.protected.items():
                info = self.inspect('container', name); s = info.get('State', {})
                good = good and [info.get('Id'), s.get('Running'), s.get('StartedAt'), s.get('ExitCode')] == expected
                protected_file = self.file_in_container(name, '/keep-me.txt')
                good = good and protected_file is not None and protected_file[0] == f'preserve {seed}\n'
            if key == 'prune' and v == 1: good = good and self.read(self.start / 'receipt backup.txt') == f'receipt {seed}\n'
            if key == 'prune' and v == 2: good = good and self.read(self.start / 'failure.log') == f'incident {seed}\n' and self.read(self.start / 'failure-exit.txt') == '33\n'
            check('종료된 대상만 정리·다른 작업과 인계 자료 보존', good)
        base = super().grade(self.base_mission)
        preserved = all(path.is_file() and hashlib.sha256(path.read_bytes()).hexdigest() == digest for path, digest in self.original_files.items())
        inv = self.inventory()
        preserved = preserved and self.baseline['tags'] <= inv['tags'] and self.baseline['containers'] <= inv['containers'] and self.baseline['volumes'] <= inv['volumes'] and self.baseline['networks'] <= inv['networks']
        preserved = preserved and all(self.inspect('image', tag).get('Id') == identity for tag, identity in self.baseline_tags.items())
        # Archive-only lessons must not leave newly created user containers.
        if key == 'archive': preserved = preserved and inv['containers'] == self.baseline['containers'] | {self.keep_id}
        check('무관한 파일·기존 이미지·컨테이너·저장소 보존', base['passed'] and preserved)
        try:
            returned = all(os.tcgetpgrp(session['fd']) == session['pid'] for session in self.agent.sessions.values())
        except OSError: returned = False
        check('컨테이너 연결·보조 셸에서 전용 Linux 셸로 복귀', returned)
        return dict(passed=all(row['passed'] for row in checks), checks=checks)

    def close(self):
        super().close()
        if getattr(self, 'temp', None): self.temp.cleanup(); self.temp = None
