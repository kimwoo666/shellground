"""Docker lifecycle and real Linux PTY bridge, shared by Windows and Linux."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

IMAGE = 'shellground-lab:3'
LABEL = 'com.shellground.owner'


def resource_path(relative):
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / relative


def process_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


class LabError(RuntimeError):
    pass


class LabEngine:
    def __init__(self):
        self.docker = shutil.which('docker')
        self.owner = uuid.uuid4().hex
        self.name = None
        self.bridge = None
        self.reference = {}

    def command(self, *args, input=None, timeout=30):
        if not self.docker:
            raise LabError('Docker가 없습니다. Linux는 Docker Engine, Windows는 Docker Desktop(WSL 2/Linux containers)을 설치하고 실행하세요.')
        try:
            result = subprocess.run([self.docker, *args], input=input, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=timeout, **process_options())
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LabError(str(exc)) from exc
        if result.returncode:
            raise LabError((result.stderr or result.stdout).strip()[-4000:])
        return result.stdout

    def status(self):
        operating_system = self.command('info', '--format', '{{.OSType}}', timeout=15).strip()
        if operating_system != 'linux':
            raise LabError('Docker를 Linux containers 모드로 전환하세요. 이 실습은 실제 Linux bash를 사용합니다.')
        try:
            self.command('image', 'inspect', IMAGE, timeout=10)
        except LabError as exc:
            raise LabError('실습 이미지가 없습니다. «최초 실습 환경 준비»를 먼저 눌러 주세요.') from exc
        return '실제 Ubuntu Linux · bash · GNU 도구 준비됨'

    def build(self, on_line=lambda line: None):
        self.command('info', '--format', '{{.OSType}}', timeout=15)
        with subprocess.Popen([self.docker, 'build', '-t', IMAGE, str(resource_path('lab'))],
                              stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True,
                              encoding='utf-8', errors='replace', **process_options()) as process:
            for line in process.stdout:
                on_line(line.rstrip())
            if process.wait():
                raise LabError('실습 환경 준비에 실패했습니다. Docker 상태와 인터넷 연결을 확인하세요.')
        return self.status()

    def start(self, mission):
        self.close()
        self.status()
        name = 'shellground-' + self.owner[:12] + '-' + uuid.uuid4().hex[:8]
        try:
            self.command('run', '-d', '--pull=never', '--name', name, '--label', f'{LABEL}={self.owner}',
                         '--network', 'none', '--read-only', '--cap-drop', 'ALL',
                         '--security-opt', 'no-new-privileges', '--memory', '256m', '--cpus', '1',
                         '--pids-limit', '96', '--tmpfs', '/home/learner:rw,exec,uid=1100,gid=1100,size=64m',
                         '--tmpfs', '/tmp:rw,noexec,nosuid,size=16m', IMAGE)
            self.name = name
            self.rpc('prepare', mission)
        except Exception:
            self.close()
            raise

    def rpc(self, action, mission):
        if not self.name:
            raise LabError('실습 환경이 시작되지 않았습니다.')
        payload = mission.payload()
        if action == 'grade': payload['_reference'] = self.reference
        output = self.command('exec', '-i', self.name, 'python3', '/opt/shellground/lab.py', action,
                              input=json.dumps(payload), timeout=15)
        result = json.loads(output)
        if action == 'prepare': self.reference = result.get('reference', {})
        return result

    def open_terminal(self, mission):
        if not self.name:
            raise LabError('실습 환경이 없습니다.')
        self.bridge = subprocess.Popen([self.docker, 'exec', '-i', self.name, 'python3', '-u',
                                        '/opt/shellground/bridge.py', mission.start],
                                       stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                       **process_options())
        return self.bridge

    def send(self, data):
        self._send({'input': base64.b64encode(data).decode()})

    def resize(self, rows, cols):
        self._send({'resize': [rows, cols]})

    def _send(self, value):
        if self.bridge and self.bridge.poll() is None:
            try:
                self.bridge.stdin.write((json.dumps(value) + '\n').encode())
                self.bridge.stdin.flush()
            except (BrokenPipeError, OSError):
                pass

    def close(self):
        if self.bridge:
            bridge, self.bridge = self.bridge, None
            if bridge.poll() is None:
                try:
                    bridge.stdin.close()
                    bridge.wait(timeout=3)
                except (OSError, subprocess.TimeoutExpired):
                    bridge.terminate()
                    try:
                        bridge.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        bridge.kill()
            for pipe in (bridge.stdin, bridge.stdout, bridge.stderr):
                if pipe: pipe.close()
        if self.name:
            name = self.name
            try:
                # Only remove a container whose unguessable owner label matches this instance.
                owner = self.command('inspect', '--format', '{{index .Config.Labels "' + LABEL + '"}}', name, timeout=10).strip()
                if owner == self.owner:
                    self.command('rm', '-f', name, timeout=15)
            except LabError:
                raise LabError(f'실습 컨테이너 정리 실패: {name}. Docker를 다시 시작한 후 이 컨테이너만 정리하세요.')
            finally:
                self.name = None
