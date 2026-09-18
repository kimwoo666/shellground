"""Runs ONLY in Shellground's disposable guest, never on the user's host.

The host talks through a virtio serial channel, not an exposed network service.
Each terminal owns a real PTY and an independent Bash process/environment.
"""
import base64
import fcntl
import json
import os
from pathlib import Path
import pty
import select
import signal
import struct
import subprocess
import sys
import termios
import threading

PORT = '/dev/virtio-ports/org.shellground.agent'
MARKER = Path('/opt/shellground/guest-owned')


def require_guest():
    if not Path(PORT).exists() or not MARKER.is_file() or MARKER.read_text().strip() != 'shellground-disposable-guest-v1':
        raise RuntimeError('This agent may run only inside the dedicated Shellground VM.')


def learner(groups):
    # Resolve supplementary groups in the parent, before a multithreaded fork.
    os.setgroups(groups)
    os.setgid(1100)
    os.setuid(1100)


class Agent:
    def __init__(self, stream):
        self.stream = stream
        self.lock = threading.Lock()
        self.sessions = {}
        self.serial = 0
        self.reference = {}
        self.stopped = threading.Event()
        self.ros_lab = None
        self.extension_lab = None
        self.admin_lab = None
        self.docker_lab = None
        self.conda_lab = None

    def emit(self, message):
        data = (json.dumps(message) + '\n').encode()
        with self.lock:
            view = memoryview(data)
            while view:
                written = self.stream.write(view)
                if not written:
                    raise OSError('Guest control channel disconnected during write')
                view = view[written:]
            self.stream.flush()

    def run(self, argv, data=None, root=False, cwd='/home/learner', timeout=30):
        credentials = {} if root else {'user': 1100, 'group': 1100, 'extra_groups': os.getgrouplist('learner', 1100)}
        process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            cwd=cwd, start_new_session=True, **credentials,
            env={**os.environ, 'HOME': '/home/learner', 'USER': 'learner', 'LOGNAME': 'learner',
                 'LANG': 'C.UTF-8', 'LC_ALL': 'C.UTF-8', 'TERM': 'xterm', 'DISPLAY': ':0'})
        try:
            out, err = process.communicate(data, timeout=timeout)
        except subprocess.TimeoutExpired:
            # Kill the owned process group, not just Bash; otherwise a child
            # can keep the captured pipes open and prevent bounded cancellation.
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.communicate(timeout=2)
            raise
        return {'code': process.returncode, 'out': base64.b64encode(out).decode(),
                'err': base64.b64encode(err).decode()}

    def close_session(self, sid):
        session = self.sessions.get(sid)
        if not session:
            return
        # Bash and its foreground children live in the dedicated guest only.
        try:
            os.killpg(session['pid'], signal.SIGHUP)
        except ProcessLookupError:
            pass
        try:
            os.close(session['fd'])
        except OSError:
            pass

    def open_session(self, cwd):
        if len(self.sessions) >= 8:
            raise ValueError('Maximum 8 terminals')
        if not Path(cwd).is_dir():
            raise ValueError('Terminal working directory does not exist')
        self.serial += 1
        sid = str(self.serial)
        for name in ('env', 'jobs'):
            Path('/tmp/shellground-' + name + '-' + sid + '.json').unlink(missing_ok=True)
        preseed = bool(self.extension_lab and self.extension_lab.key == 'jobs' and
                       self.extension_lab.mission.get('practice') == 2 and not getattr(self.extension_lab, 'jobs_seeded', False))
        if preseed:
            self.extension_lab.jobs_seeded = True
        groups = os.getgrouplist('learner', 1100)
        pid, fd = pty.fork()
        if pid == 0:
            learner(groups)
            os.chdir(cwd)
            os.environ.update(HOME='/home/learner', USER='learner', LOGNAME='learner',
                TERM='xterm', LANG='C.UTF-8', LC_ALL='C.UTF-8', DISPLAY=':0',
                SG_SESSION=sid,
                SG_PRESEEDED='1' if preseed else '0',
                HISTFILE='/dev/null', PS1=r'\[\e[32m\]\u@lab:\w\$ \[\e[0m\]')
            if self.extension_lab and self.extension_lab.key in ('env', 'review30'):
                os.environ['OLD_TEAM'] = 'obsolete'
            os.execv('/bin/bash', ['bash', '--noprofile', '--rcfile', '/opt/shellground/bashrc', '-i'])
        self.sessions[sid] = {'pid': pid, 'fd': fd}
        Path('/tmp/shellground.pid').write_text(str(pid))
        def read_output():
            try:
                while True:
                    data = os.read(fd, 32768)
                    if not data:
                        break
                    self.emit({'session': sid, 'output': base64.b64encode(data).decode()})
            except OSError:
                pass
            finally:
                self.sessions.pop(sid, None)
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
                self.emit({'session': sid, 'ended': True})
        # Start after response is sent so host can register the output queue.
        return sid, read_output

    def dispatch(self, message):
        action = message['action']
        if action == 'status':
            return {'protocol': 1, 'guest': 'shellground',
                    'adapters': ['linux', 'ros'] + (['docker_real'] if Path('/opt/shellground/docker_lab.py').is_file() and Path('/opt/shellground/registry-fixtures.json').is_file() else []) + (['admin'] if Path('/opt/shellground/admin_lab.py').is_file() else []) + (['extensions'] if
                        Path('/opt/shellground/registry-fixtures.json').is_file() and
                        Path('/opt/shellground/apt-repo/Packages').is_file() else []),
                    'provisioned': Path('/opt/shellground/provisioned.json').exists(),
                    'nano': Path('/usr/bin/nano').exists(), 'docker': Path('/usr/bin/docker').exists(),
                    'ros': Path('/opt/ros/humble/setup.bash').exists()}
        if action == 'exec':
            return self.run(message['argv'], base64.b64decode(message.get('input', '')),
                            message.get('root', False), message.get('cwd', '/home/learner'),
                            min(120, message.get('run_timeout', 30)))
        if action == 'prepare':
            payload = message['mission']
            self.conda_lab = None
            if self.docker_lab:
                self.docker_lab.close()
                self.docker_lab = None
            if self.admin_lab:
                self.admin_lab.close()
                self.admin_lab = None
            if self.extension_lab:
                self.extension_lab.close()
                self.extension_lab = None
            if self.ros_lab:
                self.ros_lab.close()
                self.ros_lab = None
            for sid in list(self.sessions):
                self.close_session(sid)
            self.sessions.clear()
            # UID 1100 belongs exclusively to the learner in this owned guest.
            # Includes detached ROS nodes/daemons and background shell jobs.
            self.run(['/usr/bin/pkill', '-TERM', '-u', '1100'], root=True, cwd='/')
            # ROS CLI's daemon can keep its XML-RPC port after rclpy shutdown.
            # A reset must not reuse that half-stopped daemon in the next task.
            threading.Event().wait(.15)
            self.run(['/usr/bin/pkill', '-KILL', '-u', '1100'], root=True, cwd='/')
            # No host filesystem is mounted in the guest. Root marker was checked
            # before opening this control channel. Reset only the training home.
            import shutil
            root = Path('/home/learner')
            if root.is_symlink():
                root.unlink()
            elif root.exists():
                shutil.rmtree(root)
            root.mkdir(mode=0o755)
            os.chown(root, 1100, 1100)
            if payload['kind']=='conda':
                from conda_lab import CondaLab
                self.conda_lab=CondaLab(self)
                return self.conda_lab.prepare(payload)
            if payload['kind'].startswith('docker_'):
                from docker_lab import DockerLab
                self.docker_lab = DockerLab(self)
                return self.docker_lab.prepare(payload)
            if payload['kind'].startswith('admin_'):
                from admin_lab import AdminLab
                self.admin_lab = AdminLab(self)
                return self.admin_lab.prepare(payload)
            if payload['kind'].startswith('sim_'):
                from extension_lab import ExtensionLab
                self.extension_lab = ExtensionLab(self)
                return self.extension_lab.prepare(payload)
            if payload['kind'].startswith('ros_'):
                from ros_lab import RosLab
                self.ros_lab = RosLab(self)
                return self.ros_lab.prepare(payload)
            response = self.run(['python3', '/opt/shellground/lab.py', 'prepare'], json.dumps(payload).encode())
            if response['code']:
                raise RuntimeError(base64.b64decode(response['err']).decode())
            prepared = json.loads(base64.b64decode(response['out']))
            self.reference = prepared.get('reference', {})
            return prepared
        if action == 'grade':
            payload = message['mission']
            if payload['kind']=='conda':
                if not self.conda_lab:raise ValueError('Conda problem is not prepared')
                return self.conda_lab.grade(payload,message.get('session'),message.get('answers',{}))
            if payload['kind'].startswith('docker_'):
                if not self.docker_lab or self.docker_lab.mission != payload:
                    raise ValueError('Docker mission is not prepared')
                return self.docker_lab.grade(payload)
            if payload['kind'].startswith('admin_'):
                if not self.admin_lab or self.admin_lab.mission != payload:
                    raise ValueError('Administration mission is not prepared')
                return self.admin_lab.grade(payload)
            if payload['kind'].startswith('sim_'):
                if not self.extension_lab or self.extension_lab.mission != payload:
                    raise ValueError('Extension mission is not prepared')
                return self.extension_lab.grade(payload, message.get('session'))
            if payload['kind'].startswith('ros_'):
                if not self.ros_lab or self.ros_lab.mission != payload:
                    raise ValueError('ROS mission is not prepared')
                return self.ros_lab.grade(payload, message.get('session'))
            payload['_reference'] = self.reference
            payload['_terminal_output'] = message.get('output', '')
            sid = message.get('session')
            if sid in self.sessions:
                Path('/tmp/shellground.pid').write_text(str(self.sessions[sid]['pid']))
            response = self.run(['python3', '/opt/shellground/lab.py', 'grade'], json.dumps(payload).encode())
            if response['code']:
                raise RuntimeError(base64.b64decode(response['err']).decode())
            result = json.loads(base64.b64decode(response['out']))
            if sid in self.sessions:
                session = self.sessions[sid]
                foreground = os.tcgetpgrp(session['fd'])
                if foreground != session['pid']:
                    result['checks'].append({'label': '실행 중인 편집기/작업을 종료하고 셸로 복귀', 'passed': False})
                    result['passed'] = False
            return result
        if action == 'close':
            self.close_session(message['session'])
            return True
        raise ValueError('Unknown action: ' + action)

    def serve(self):
        while not self.stopped.is_set():
            line = self.stream.readline(4 * 1024 * 1024)
            if not line:
                # A disconnected virtio port returns EOF immediately. Retrying
                # without a wait burns an entire vCPU while nobody is using it.
                # poll/select also report persistent HUP, so they alone are not
                # a blocking wait here. Allow reconnection with bounded delay.
                self.stopped.wait(0.25)
                continue
            message = {}
            try:
                message = json.loads(line)
                action = message['action']
                if action == 'open':
                    sid, reader = self.open_session(message['cwd'])
                    self.emit({'id': message['id'], 'result': {'session': sid}})
                    threading.Thread(target=reader, daemon=True).start()
                    continue
                if action in ('input', 'resize'):
                    session = self.sessions.get(message['session'])
                    if session:
                        if action == 'input':
                            os.write(session['fd'], base64.b64decode(message['data']))
                        else:
                            rows, cols = message['size']
                            fcntl.ioctl(session['fd'], termios.TIOCSWINSZ,
                                struct.pack('HHHH', max(2, min(200, rows)), max(10, min(500, cols)), 0, 0))
                    continue
                result = self.dispatch(message)
                self.emit({'id': message['id'], 'result': result})
            except Exception as exc:
                self.emit({'id': message.get('id'), 'error': str(exc)})


if __name__ == '__main__':
    require_guest()
    with open(PORT, 'r+b', buffering=0) as stream:
        Agent(stream).serve()
