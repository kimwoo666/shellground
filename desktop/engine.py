"""Docker lifecycle and real Linux PTY bridge, shared by Windows and Linux."""
import base64
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

IMAGE = 'shellground-lab:3.3'
LABEL = 'com.shellground.owner'


def resource_path(relative):
    return Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / relative


def process_options():
    return {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}


class LabError(RuntimeError):
    pass


def validate_backend(info, platform):
    if info.get('OSType') != 'linux':
        raise LabError('Docker를 Linux containers 모드로 전환하세요. 실습은 실제 Linux bash를 사용합니다.')
    if platform != 'win32':
        return
    kernel = str(info.get('KernelVersion', '')).lower()
    guidance = ('Windows 실습은 WSL을 사용하지 않습니다. Docker Desktop을 모든 사용자용으로 설치하고, '
                'Hyper-V를 활성화한 뒤 Settings > General에서 Use the WSL 2 based engine을 끄고 적용·재시작하세요. '
                'Windows Pro/Enterprise/Education의 Hyper-V 환경이 필요합니다.')
    if 'wsl' in kernel or 'microsoft' in kernel:
        raise LabError('현재 Docker 엔진은 WSL 기반이므로 실습을 차단했습니다. ' + guidance)
    # Check the running daemon, not a saved preference that may be unapplied.
    # Fail closed for unrecognized kernels rather than silently using WSL.
    if 'linuxkit' not in kernel:
        raise LabError('WSL 없는 Docker LinuxKit 엔진인지 확인할 수 없습니다. ' + guidance)


class LabEngine:
    def __init__(self):
        self.docker = shutil.which('docker')
        self.owner = uuid.uuid4().hex
        self.name = None
        self.bridge = None
        self.reference = {}
        self.observed_output = bytearray()
        self.observe_terminal = False

    def command(self, *args, input=None, timeout=30):
        if not self.docker:
            raise LabError('Docker가 없습니다. Linux는 Docker Engine, Windows는 Docker Desktop(Hyper-V / Linux containers)을 설치하고 실행하세요. WSL은 사용하지 않습니다.')
        try:
            result = subprocess.run([self.docker, *args], input=input, capture_output=True, text=True,
                                    encoding='utf-8', errors='replace', timeout=timeout, **process_options())
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise LabError(str(exc)) from exc
        if result.returncode:
            raise LabError((result.stderr or result.stdout).strip()[-4000:])
        return result.stdout

    def check_backend(self):
        try:
            info = json.loads(self.command('info', '--format', '{{json .}}', timeout=15))
            if not isinstance(info, dict): raise ValueError('Expected an object')
        except (ValueError, TypeError) as exc:
            raise LabError('Docker 실행 환경 정보를 읽을 수 없습니다. Docker 상태를 확인하세요.') from exc
        validate_backend(info, sys.platform)

    def status(self):
        self.check_backend()
        try:
            self.command('image', 'inspect', IMAGE, timeout=10)
        except LabError as exc:
            raise LabError('실습 이미지가 없습니다. «최초 실습 환경 준비»를 먼저 눌러 주세요.') from exc
        return '실제 Ubuntu Linux · bash · GNU 도구 준비됨' + (' · WSL 없는 LinuxKit 엔진 확인' if sys.platform == 'win32' else '')

    def build(self, on_line=lambda line: None):
        self.check_backend()
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
        self.observed_output.clear()
        self.observe_terminal = (mission.kind in ('pwdpaths', 'lsintro', 'read') or
                                 any(g['type'] in ('output', 'output_contains')
                                     for g in mission.review.get('goals', [])))
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
        if action == 'grade':
            payload['_reference'] = self.reference
            payload['_terminal_output'] = self.observed_output.decode('utf-8', errors='replace')
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

    def observe_output(self, data):
        # Transient output evidence, not saved progress or an input-command log.
        if self.observe_terminal:
            self.observed_output.extend(data)
            del self.observed_output[:-262144]

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
