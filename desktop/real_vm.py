"""Private, bundled Linux runtime. No host shell, Docker socket or mounts.

The command protocol is transported over an app-owned QEMU virtio serial port.
The shipped base disk is read-only; each app run uses its own disposable overlay.
"""
import base64
import io
import json
import os
from pathlib import Path
import platform
import queue
import shutil
import socket
import subprocess
import sys
import tempfile
import threading
import time

from engine import LabError, process_options, resource_path
from vm_resources import accelerator_args, lower_priority, vcpu_count, vm_process_options
from real_lessons import adapt_real_mission
from vm_supervisor import create_session, reap_abandoned_sessions


def runtime_root():
    from platform_runtime import runtime_tag
    from build_layout import runtime_directory
    name = runtime_tag()
    candidates = [runtime_directory(Path(sys.executable).resolve()) / name,
                  resource_path('runtime/' + name)]
    if not getattr(sys, 'frozen', False):
        # Source runs share the current pack; do not require a second old disk.
        candidates.append(resource_path('.vm-runtime-conda/' + name))
    candidates.append(resource_path('.vm-runtime/' + name))
    return next((p for p in candidates if (p / 'runtime.json').is_file()), candidates[0])


def runtime_info(root=None):
    root = Path(root) if root is not None else runtime_root()
    try:
        data = json.loads((root / 'runtime.json').read_text(encoding='utf-8'))
        if data.get('protocol') != 1 or data.get('provisioned') is not True:
            raise ValueError('runtime is not provisioned')
        for name in ('qemu', 'qemu_img', 'image'):
            path = (root / data[name]).resolve()
            if not path.is_relative_to(root.resolve()) or not path.is_file():
                raise ValueError('runtime file missing or outside bundle: ' + name)
        for name in ('firmware', 'bios'):
            if name not in data:
                continue
            path = (root / data[name]).resolve()
            valid = path.is_dir() if name == 'firmware' else path.is_file()
            if not path.is_relative_to(root.resolve()) or not valid:
                raise ValueError('runtime firmware missing or outside bundle: ' + name)
        return root, data
    except (OSError, ValueError, KeyError, TypeError) as exc:
        raise LabError('실제 Linux 런타임이 이 배포본에 포함되어 있지 않거나 손상되었습니다. '
                       '시뮬레이션으로 대신 실행하지 않습니다. ' + str(exc)) from exc


def available():
    try:
        runtime_info()
        return True
    except LabError:
        return False


class TerminalProcess:
    """Same line transport used by TerminalReader, one queue per real PTY."""
    def __init__(self, sid):
        self.sid = sid
        self.queue = queue.Queue(maxsize=128)
        self.stdout = self
        self.stderr = io.BytesIO()
        self.returncode = None

    def __iter__(self):
        return self

    def __next__(self):
        value = self.queue.get()
        if value is None:
            raise StopIteration
        return value

    def emit(self, data):
        if self.returncode is not None:
            return
        line = json.dumps({'output': data}) + '\n'
        try:
            self.queue.put_nowait(line)
        except queue.Full:
            # Bound unconsumed terminal output; don't block control RPC replies.
            self.queue.get_nowait()
            self.queue.put_nowait(line)

    def close(self):
        self.returncode = 0
        try:
            self.queue.put_nowait(None)
        except queue.Full:
            self.queue.get_nowait()
            self.queue.put_nowait(None)

    def poll(self):
        return self.returncode


class GuestChannel:
    def __init__(self, connection):
        self.connection = connection
        self.write_lock = threading.Lock()
        self.state_lock = threading.Lock()
        self.requests = {}
        self.sessions = {}
        self.serial = 0
        self.closed = threading.Event()
        self.thread = threading.Thread(target=self._read, daemon=True)
        self.thread.start()

    def _read(self):
        try:
            with self.connection.makefile('rb') as stream:
                while not self.closed.is_set():
                    line = stream.readline(4 * 1024 * 1024)
                    if not line:
                        break
                    message = json.loads(line)
                    sid = message.get('session')
                    if sid is not None:
                        with self.state_lock:
                            terminal = self.sessions.setdefault(sid, TerminalProcess(sid))
                        if 'output' in message:
                            terminal.emit(message['output'])
                        if message.get('ended'):
                            terminal.close()
                    else:
                        with self.state_lock:
                            waiter = self.requests.get(message.get('id'))
                        if waiter:
                            waiter.put(message)
        except (OSError, ValueError):
            pass
        finally:
            self.closed.set()
            with self.state_lock:
                for waiter in self.requests.values():
                    waiter.put({'error': '실제 Linux 연결이 종료되었습니다.'})
                for terminal in self.sessions.values():
                    terminal.close()

    def send(self, message):
        if self.closed.is_set():
            raise LabError('실제 Linux 연결이 종료되었습니다.')
        with self.write_lock:
            self.connection.sendall((json.dumps(message) + '\n').encode())

    def request(self, action, timeout=30, **payload):
        with self.state_lock:
            self.serial += 1
            request_id = self.serial
            waiter = queue.Queue()
            self.requests[request_id] = waiter
        try:
            self.send(dict(payload, action=action, id=request_id))
            response = waiter.get(timeout=timeout)
            if 'error' in response:
                raise LabError(response['error'])
            return response['result']
        except queue.Empty as exc:
            raise LabError('실제 Linux 응답 시간 초과: ' + action) from exc
        finally:
            with self.state_lock:
                self.requests.pop(request_id, None)

    def open_terminal(self, cwd):
        value = self.request('open', cwd=cwd)
        sid = value['session']
        with self.state_lock:
            return self.sessions.setdefault(sid, TerminalProcess(sid))

    def close(self):
        self.closed.set()
        try:
            self.connection.shutdown(socket.SHUT_RDWR)
        except OSError:
            pass
        self.connection.close()
        self.thread.join(timeout=2)
        for terminal in self.sessions.values():
            terminal.close()


class RealEngine:
    def __init__(self, root=None):
        self.root = root
        self.name = None
        self.process = None
        self.channel = None
        self.bridge = None
        self.session_dir = None
        self.observed_output = bytearray()
        self.cancelled = threading.Event()
        self.shutdown_requested = False
        self.rows, self.cols = 24, 100
        self.start_seconds = None
        self.log_file = None
        self.guest_status = {}
        self.supervised = False

    def status(self):
        runtime_info(self.root)
        if self.channel:
            status = self.channel.request('status', timeout=5)
            return '실제 Linux · Bash/nano · Docker/ROS 준비 상태: ' + json.dumps(status, ensure_ascii=False)
        return '내장 실제 Linux 런타임 확인됨 · 실습 시작 시 자동 기동'

    def build(self, on_line=lambda line: None):
        return self.status()

    def configure_shell(self):
        """Update only our private guest's rc file, before opening any PTYs.

        Ship this tiny configuration with the app so colour fixes do not require
        repacking a multi-gigabyte base image. The immutable base is untouched.
        """
        script = (
            "import sys; from pathlib import Path; "
            "sys.path.insert(0, '/opt/shellground'); "
            "from agent import require_guest; require_guest(); "
            "p = Path('/opt/shellground/bashrc'); "
            "p.write_bytes(sys.stdin.buffer.read()); p.chmod(0o644)"
        )
        result = self.channel.request('exec', timeout=10, run_timeout=5,
            root=True, cwd='/tmp', argv=['/usr/bin/python3', '-c', script],
            input=base64.b64encode(resource_path('guest/bashrc').read_bytes()).decode())
        if result['code']:
            raise LabError('실습 터미널 색상 설정 실패: ' +
                           base64.b64decode(result['err']).decode(errors='replace'))

    def boot(self, on_line=lambda line: None):
        if self.shutdown_requested:
            raise LabError('앱 종료 요청으로 실제 Linux 시작이 취소되었습니다.')
        if self.channel and not self.channel.closed.is_set():
            return
        if self.process or self.session_dir:
            # Recover a broken transport without orphaning the previous guard.
            self.close()
        self.cancelled.clear()
        root, spec = runtime_info(self.root)
        acceleration = accelerator_args()
        recovered = reap_abandoned_sessions()
        if recovered:
            on_line(f'이전 비정상 종료의 임시 실습 디스크 {len(recovered)}개 정리')
        self.session_dir, token = create_session()
        env = dict(os.environ)
        if os.name != 'nt':
            env.update(LD_LIBRARY_PATH=str(root / 'usr/lib/x86_64-linux-gnu'),
                       QEMU_MODULE_DIR=str(root / 'usr/lib/x86_64-linux-gnu/qemu'))
        overlay = self.session_dir / 'practice.qcow2'
        listener = None
        try:
            subprocess.run([str(root / spec['qemu_img']), 'create', '-f', 'qcow2', '-F', 'qcow2',
                            '-b', str((root / spec['image']).resolve()), str(overlay)],
                           env=env, check=True, capture_output=True, timeout=15, **process_options())
            # QEMU connects to an already-bound loopback socket: no port selection
            # race and no guest service is exposed on the user's network.
            listener = socket.socket()
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(1)
            port = listener.getsockname()[1]
            overlay_option = str(overlay)
            serial_option = 'file:' + str(self.session_dir / 'console.log')
            if os.name == 'nt':
                # QEMU's Windows option paths are not reliably Unicode-safe.
                # CreateProcessW sets the Unicode working directory; all QEMU
                # option-list filenames then stay ASCII and session-relative.
                overlay_option = 'practice.qcow2'
                serial_option = 'file:console.log'
            command = [str(root / spec['qemu']), '-name', 'shellground-private-lab',
                '-machine', 'q35', *acceleration, '-smp', str(vcpu_count()), '-m', '2048',
                '-display', 'none', '-vga', 'none', '-monitor', 'none',
                '-serial', serial_option,
                '-drive', f'file={overlay_option},format=qcow2,if=virtio', '-nic', 'none',
                '-device', 'virtio-serial-pci',
                '-chardev', f'socket,id=sg,host=127.0.0.1,port={port},' +
                    ('reconnect-ms=1000' if os.name == 'nt' else 'reconnect=1'),
                '-device', 'virtserialport,chardev=sg,name=org.shellground.agent', '-no-reboot']
            if os.name != 'nt':
                command += ['-L', str(root / 'usr/share/qemu'), '-bios', str(root / 'usr/share/seabios/bios-256k.bin')]
            elif 'firmware' in spec and 'bios' in spec:
                shutil.copy2(root / spec['bios'], self.session_dir / 'qemu-bios.bin')
                vapic = root / spec['firmware'] / 'kvmvapic.bin'
                if vapic.is_file():
                    shutil.copy2(vapic, self.session_dir / 'kvmvapic.bin')
                command += ['-L', '.', '-bios', 'qemu-bios.bin']
            if os.name == 'nt':
                from windows_vm import supervisor_output
                self.log_file = supervisor_output()
            else:
                self.log_file = (self.session_dir / 'qemu.log').open('w+b')
            if getattr(sys, 'frozen', False):
                supervisor = [sys.executable, '--internal-vm-supervisor']
            else:
                supervisor = [sys.executable, str(Path(__file__).with_name('vm_supervisor.py'))]
            supervisor += ['--session', str(self.session_dir), '--token', token]
            if os.name != 'nt':
                supervisor += ['--library-dir', env['LD_LIBRARY_PATH'], '--module-dir', env['QEMU_MODULE_DIR']]
            # Independent frozen extraction: app crash may remove its _MEIPASS.
            guard_env = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
            self.process = subprocess.Popen(supervisor + ['--', *command], stdin=subprocess.PIPE,
                stdout=self.log_file, stderr=subprocess.STDOUT, env=guard_env,
                cwd=root if os.name == 'nt' else None, **vm_process_options())
            self.supervised = True
            lower_priority(self.process)
            boot_seconds = 120
            if os.name == 'nt':
                from windows_vm import boot_timeout, startup_description
                boot_seconds = boot_timeout(acceleration)
                on_line(startup_description(acceleration, vcpu_count()))
            else:
                on_line(f'하드웨어 가속: {acceleration[1]} · 가상 CPU {vcpu_count()}개 · 메모리 2 GiB')
            started = time.monotonic()
            deadline = started + boot_seconds
            try:
                while time.monotonic() < deadline:
                    if self.cancelled.is_set():
                        raise LabError('실제 Linux 시작이 취소되었습니다.')
                    if self.process.poll() is not None:
                        # Supervisor may already have removed its temporary disk.
                        try:
                            error = (self.session_dir / 'qemu.log').read_text(errors='replace')[-3000:]
                        except FileNotFoundError:
                            self.log_file.seek(0)
                            error = self.log_file.read().decode(errors='replace')[-3000:]
                        error = error or '실제 Linux 관리 프로세스가 종료되었습니다.'
                        raise LabError(error)
                    try:
                        connection, _ = listener.accept()
                        self.channel = GuestChannel(connection)
                        break
                    except socket.timeout:
                        pass
                if not self.channel:
                    raise LabError('실제 Linux 제어 채널 연결 시간 초과')
                while time.monotonic() < deadline:
                    if self.cancelled.is_set():
                        raise LabError('실제 Linux 시작이 취소되었습니다.')
                    try:
                        status = self.channel.request('status', timeout=2)
                        if status.get('protocol') != 1 or not status.get('provisioned'):
                            raise LabError('실제 Linux 이미지가 완전히 준비되지 않았습니다.')
                        self.configure_shell()
                        self.configure_grader()
                        self.name = 'private-linux'
                        self.guest_status = status
                        self.start_seconds = time.monotonic() - started
                        return
                    except LabError as exc:
                        if '시간 초과' not in str(exc):
                            raise
                        on_line('실제 Linux 시작 중…')
                raise LabError('실제 Linux 준비 시간 초과')
            finally:
                listener.close()
        except Exception:
            self.close()
            raise
        finally:
            if listener is not None:
                listener.close()

    def configure_grader(self):
        """Ship the course's real-file/output grader, not a shell emulator.

        Only replace the known grader in the verified, disposable guest. This
        keeps question/grading changes independent of the large OS base image.
        """
        for source, name in (('lab/lab.py','lab.py'), ('guest/ros_lab.py','ros_lab.py'),
                             ('guest/ros_controls_lab.py','ros_controls_lab.py'),
                             ('guest/ros_observer.py','ros_observer.py'), ('guest/apt_lab.py','apt_lab.py'),
                             ('guest/auth_lab.py','auth_lab.py'), ('guest/shell_lab.py','shell_lab.py'),
                             ('guest/process_lab.py','process_lab.py'), ('guest/io_lab.py','io_lab.py'),
                             ('guest/system_lab.py','system_lab.py'),
                             ('guest/docker_lab.py','docker_lab.py'), ('guest/docker_sessions_lab.py','docker_sessions_lab.py'),
                             ('guest/docker_runtime_lab.py','docker_runtime_lab.py'),
                             ('guest/shell_snapshot.py','shell_snapshot.py')):
            script = ("import sys; from pathlib import Path; sys.path.insert(0, '/opt/shellground'); "
                      "from agent import require_guest; require_guest(); "
                      "name=sys.argv[1]; assert name in ('lab.py','ros_lab.py','ros_controls_lab.py','ros_observer.py','apt_lab.py','auth_lab.py','shell_lab.py','process_lab.py','io_lab.py','system_lab.py','docker_lab.py','docker_sessions_lab.py','docker_runtime_lab.py','shell_snapshot.py'); "
                      "data=sys.stdin.buffer.read(); compile(data, name, 'exec'); "
                      "p=Path('/opt/shellground')/name; t=p.with_suffix('.new'); "
                      "t.write_bytes(data); t.chmod(0o644); t.replace(p)")
            result = self.channel.request('exec', timeout=10, run_timeout=5, root=True, cwd='/tmp',
                argv=['/usr/bin/python3', '-c', script, name],
                input=base64.b64encode(resource_path(source).read_bytes()).decode())
            if result['code']:
                raise LabError('실제 Linux 채점기 준비 실패: ' + base64.b64decode(result['err']).decode(errors='replace'))

    def start(self, mission):
        self.boot()
        if mission.kind.startswith('docker_') and 'docker_real' not in self.guest_status.get('adapters', []):
            raise LabError('이 런타임 팩에는 Docker 심화 실습이 없습니다. 최신 runtime 폴더와 함께 사용하세요. 기존 실습은 초기화하지 않았습니다.')
        if mission.kind.startswith('admin_') and 'admin' not in self.guest_status.get('adapters', []):
            raise LabError('이 실제 런타임 팩에는 계정·권한 실습이 없습니다. 실행 파일과 최신 runtime 폴더를 함께 사용하세요. 기존 실습은 초기화하지 않았습니다.')
        if mission.kind.startswith('sim_') and 'extensions' not in self.guest_status.get('adapters', []):
            raise LabError('이 실제 런타임 팩에는 패키지·Docker 교육 저장소가 없습니다. '
                           '실행 파일과 함께 제공되는 최신 runtime 폴더가 필요합니다. 기존 실습은 초기화하지 않았습니다.')
        self.observed_output.clear()
        result = self.channel.request('exec', timeout=15, run_timeout=10, root=True, cwd='/tmp',
            argv=['/usr/bin/python3', '/opt/shellground/system_lab.py', 'cleanup'])
        if result['code']:
            raise LabError('이전 시스템 조사 실습 정리 실패: ' + base64.b64decode(result['err']).decode(errors='replace'))
        result = self.channel.request('exec', timeout=15, run_timeout=10, root=True, cwd='/tmp',
            argv=['/usr/bin/python3', '/opt/shellground/process_lab.py', 'cleanup'])
        if result['code']:
            raise LabError('이전 프로세스 실습 정리 실패: ' + base64.b64decode(result['err']).decode(errors='replace'))
        result = self.channel.request('exec', timeout=15, run_timeout=10, root=True, cwd='/tmp',
            argv=['/usr/bin/python3', '/opt/shellground/auth_lab.py', 'cleanup'])
        if result['code']:
            raise LabError('이전 연습 계정 정리 실패: ' + base64.b64decode(result['err']).decode(errors='replace'))
        self.channel.request('prepare', timeout=90, mission=adapt_real_mission(mission).payload())

    def open_terminal(self, mission):
        self.bridge = self.channel.open_terminal(mission.start)
        return self.bridge

    def send(self, data):
        if self.channel and self.bridge and self.bridge.poll() is None:
            self.channel.send({'action': 'input', 'session': self.bridge.sid,
                               'data': base64.b64encode(data).decode()})

    def resize(self, rows, cols):
        self.rows, self.cols = rows, cols
        if self.channel and self.bridge:
            self.channel.send({'action': 'resize', 'session': self.bridge.sid, 'size': [rows, cols]})

    def observe_output(self, data):
        self.observed_output.extend(data)
        del self.observed_output[:-262144]

    def rpc(self, action, mission):
        if action != 'grade' or not self.channel:
            raise LabError('실제 실습이 준비되지 않았습니다.')
        return self.channel.request('grade', timeout=60, mission=adapt_real_mission(mission).payload(), session=self.bridge.sid,
                                    output=self.observed_output.decode(errors='replace'))

    def tick(self):
        pass

    def screen(self):
        if not self.channel:
            raise LabError('실제 Linux가 실행 중이 아닙니다.')
        result = self.channel.request('exec', timeout=6, run_timeout=3, cwd='/tmp',
                                      argv=['python3', '/opt/shellground/screen.py'])
        if result['code']:
            raise LabError(base64.b64decode(result['err']).decode(errors='replace'))
        return base64.b64decode(result['out'])

    def close(self):
        self.cancelled.set()
        if self.channel:
            self.channel.close()
            self.channel = None
        if self.process:
            process, self.process = self.process, None
            if process.poll() is None:
                if self.supervised:
                    process.stdin.close()
                else:
                    process.terminate()
                try:
                    process.wait(timeout=7 if self.supervised else 3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
            if self.supervised:
                process.stdin.close()
        if self.log_file:
            self.log_file.close()
            self.log_file = None
        # This directory was allocated by this instance, never a user supplied
        # cleanup target. The immutable base image and progress are not removed.
        if self.session_dir:
            directory, self.session_dir = self.session_dir, None
            try:
                shutil.rmtree(directory)
            except FileNotFoundError:
                pass  # supervisor already cleaned its owned session
        self.name = None
        self.bridge = None
        self.supervised = False

    def cancel_pending(self):
        """Nonblocking cancellation for a window close during startup/grading."""
        self.shutdown_requested = True
        self.cancelled.set()
        if self.channel:
            # Wake the RPC reader/waiters. Full thread joining and file cleanup
            # remain in close(), called by the normal cleanup worker.
            try:
                self.channel.connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
        process = self.process
        if process and process.poll() is None:
            try:
                if self.supervised:
                    process.stdin.close()
                else:
                    process.terminate()
            except (ProcessLookupError, OSError):
                pass
