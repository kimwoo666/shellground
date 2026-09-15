"""Offline training backend; all execution and files stay in Python memory."""
import base64
import codecs
import io
import json
import posixpath as p
import queue
import shlex
import tarfile
import time
import threading
from wcwidth import wcswidth
from types import FunctionType, SimpleNamespace
import zipfile
from sim_fs import FS, Node, VPath
from sim_shell import Shell, Result
from sim_docker import Docker
from lab import lab


def base_filesystem():
    fs = FS(); fs.uid = 0
    for path in ('/home/learner', '/root', '/tmp', '/usr/bin', '/bin', '/etc', '/var/log', '/srv/fixtures'):
        fs.mkdir(path, True, True)
    fs.get('/home/learner').uid = 1100
    fs.get('/tmp').mode = 0o777
    fs.write('/etc/passwd', b'root:x:0:0:root:/root:/bin/bash\nlearner:x:1100:1100::/home/learner:/bin/bash\n')
    fs.write('/etc/group', b'root:x:0:\nlearner:x:1100:\nsudo:x:27:learner\n')
    fs.write('/tmp/shellground.pid', b'100')
    fs.uid = 1100
    return fs


def fixtures(fs):
    data = {'setup.sh': lab.SCRIPT}
    content = {'README.txt': lab.README, 'bin/hello.sh': lab.HELLO}
    stream = io.BytesIO()
    with tarfile.open(fileobj=stream, mode='w:gz') as archive:
        for path, value in content.items():
            member = tarfile.TarInfo(path); member.size = len(value); member.mode = 0o755 if path.endswith('.sh') else 0o644
            archive.addfile(member, io.BytesIO(value))
    data['bundle.tar.gz'] = stream.getvalue()
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, 'w') as archive:
        for path, value in content.items(): archive.writestr(path, value)
    data['bundle.zip'] = stream.getvalue()
    # Explicitly simulated package; never fed to a host package manager.
    data['toolkit.deb'] = b'!<arch>\nShellground simulated Debian package\nPackage: shellground-toolkit\nVersion: 1.0\n' + lab.MESSAGE
    uid = fs.uid; fs.uid = 0
    for name, value in data.items(): fs.write('/srv/fixtures/' + name, value)
    fs.uid = uid


def lab_adapter(shell):
    """Reuse goal rules, with every filesystem/OS operation explicitly virtual."""
    fs = shell.fs
    globals_ = dict(vars(lab))
    def check_output(argv, **kwargs):
        result = shell.command(list(argv), redirected=True)
        if result.code: raise ValueError(result.err.decode())
        return result.out.decode()
    globals_.update(Path=lambda path: VPath(fs, path), FIXTURES=VPath(fs, '/srv/fixtures'),
        os=SimpleNamespace(utime=lambda *args: None, path=SimpleNamespace(lexists=lambda path: fs.exists(str(path), False)),
                           readlink=lambda path: fs.resolve(shell.cwd)),
        shutil=SimpleNamespace(copyfile=lambda src, dst: fs.write(str(dst), fs.read(str(src)))),
        subprocess=SimpleNamespace(check_output=check_output))
    for name in ('read_regular', 'long_records', 'prepare', 'grade_base', 'grade'):
        fn = getattr(lab, name)
        globals_[name] = FunctionType(fn.__code__, globals_, name, fn.__defaults__)
    return globals_


class OutputQueue:
    def __init__(self): self.queue = queue.Queue()
    def __iter__(self): return self
    def __next__(self):
        value = self.queue.get()
        if value is None: raise StopIteration
        return value


class SimProcess:
    def __init__(self):
        self.stdout = OutputQueue(); self.stderr = io.BytesIO(); self.returncode = None
    def output(self, data):
        if self.returncode is None:
            self.stdout.queue.put(json.dumps({'output': base64.b64encode(data).decode()}) + '\n')
    def poll(self): return self.returncode
    def close(self):
        if self.returncode is None: self.returncode = 0; self.stdout.queue.put(None)
    terminate = kill = close
    def wait(self, timeout=None): self.close(); return 0


class SimEngine:
    def __init__(self):
        self.name = None; self.bridge = None; self.shell = None; self.reference = {}
        self.observe_terminal = False
        self.rows, self.cols = 24, 100
        self.line = ''; self.cursor = 0; self.history_index = 0
        self.decoder = codecs.getincrementaldecoder('utf-8')('replace')
        self.pending = ''; self.paste = False; self.sessions = []
        self.lock = threading.RLock()
        self.rendered_prefix = ''

    def status(self): return '오프라인 Linux·Docker 시뮬레이터 준비됨 · 설치·VM·WSL 불필요'
    def build(self, on_line=lambda line: None): return self.status()
    def start(self, mission):
        self.close()
        self.shell = Shell(base_filesystem()); self.shell.docker = Docker(self.shell)
        fixtures(self.shell.fs)
        self.shell.cwd = mission.start; self.shell.env['PWD'] = mission.start
        self.name = 'simulation'
        self.reference = lab_adapter(self.shell)['prepare'](mission.payload())['reference']
        if mission.kind.startswith('sim_'):
            from sim_lessons import prepare_extension
            prepare_extension(self.shell, mission)
        self.shell.output = b''
        self.line = ''; self.cursor = 0; self.pending = ''; self.paste = False; self.sessions = []
        self.decoder.reset()

    def rpc(self, action, mission):
        with self.lock: return self._rpc(action, mission)

    def _rpc(self, action, mission):
        if not self.shell: raise ValueError('실습이 시작되지 않았습니다.')
        if action != 'grade': raise ValueError('unsupported simulator action')
        if mission.kind.startswith('sim_'):
            from sim_lessons import grade_extension
            return grade_extension(self.shell, mission)
        payload = mission.payload()
        payload.update(_reference=self.reference, _terminal_output=self.shell.output.decode(errors='replace'))
        result = lab_adapter(self.shell)['grade'](payload)
        if self.active.editor:
            result['checks'].append({'label': '편집기를 종료하고 셸로 복귀', 'passed': False}); result['passed'] = False
        return result

    @property
    def active(self): return self.sessions[-1][0]['shell'] if self.sessions else self.shell

    def open_terminal(self, mission):
        self.bridge = SimProcess()
        self.shell.interactive = True
        self.emit('Shellground offline simulator — 실제 호스트에는 명령을 실행하지 않습니다.\n')
        self.prompt(); return self.bridge

    def observe_output(self, data): pass  # Only executed command output is grading evidence.
    def resize(self, rows, cols): self.rows, self.cols = rows, cols
    def tick(self):
        if self.bridge and self.shell and self.active.foreground and time.monotonic() >= self.active.foreground['until']:
            self.active.foreground['state'] = 'Done'; self.active.foreground = None; self.emit('\n'); self.prompt()
    def close(self):
        if self.bridge: self.bridge.close()
        self.bridge = None; self.name = None; self.shell = None

    def emit(self, value):
        if not self.bridge: return
        data = value if isinstance(value, bytes) else value.encode()
        self.bridge.output(data.replace(b'\r\n', b'\n').replace(b'\n', b'\r\n'))

    def prompt(self):
        shell = self.active
        home = shell.env.get('HOME', '/home/learner')
        cwd = '~' + shell.cwd[len(home):] if shell.cwd == home or shell.cwd.startswith(home + '/') else shell.cwd
        host = self.sessions[-1][0]['id'][:12] if self.sessions else 'lab'
        self.prompt_text = f'{shell.env.get("USER", "learner")}@{host}:{cwd}{"#" if shell.fs.uid == 0 else "$"} '
        self.emit('\x1b[?2004h\x1b[32m' + self.prompt_text + '\x1b[0m')
        self.rendered_prefix = ''
        self.history_index = len(shell.history)

    def redraw(self):
        def position(text):
            row, column = 0, 0
            for part in text.splitlines(keepends=True):
                column += max(0, wcswidth(part.rstrip('\r\n')))
                row += column // self.cols; column %= self.cols
                if part.endswith(('\n', '\r')): row += 1; column = 0
            return row, column
        old_row, _ = position(self.prompt_text + self.rendered_prefix)
        self.emit('\r' + (f'\x1b[{old_row}A' if old_row else '') + '\x1b[J\x1b[32m' + self.prompt_text + '\x1b[0m' + self.line)
        end_row, _ = position(self.prompt_text + self.line)
        cursor_row, column = position(self.prompt_text + self.line[:self.cursor])
        if end_row > cursor_row: self.emit(f'\x1b[{end_row - cursor_row}A')
        self.emit(f'\x1b[{column + 1}G')
        self.rendered_prefix = self.line[:self.cursor]

    def send(self, data):
        with self.lock: self._send(data)

    def _send(self, data):
        if not self.bridge or self.bridge.poll() is not None: return
        self.pending += self.decoder.decode(data)
        keys = {'\x1b[A': 'up', '\x1b[B': 'down', '\x1b[C': 'right', '\x1b[D': 'left', '\x1b[H': 'home', '\x1b[F': 'end', '\x1b[3~': 'delete', '\x1b[200~': 'paste_start', '\x1b[201~': 'paste_end'}
        while self.pending:
            if self.pending[0] == '\x1b':
                match = next((k for k in keys if self.pending.startswith(k)), None)
                if match: key = keys[match]; self.pending = self.pending[len(match):]
                elif any(k.startswith(self.pending) for k in keys): break
                else: self.pending = self.pending[1:]; continue
            else: key, self.pending = self.pending[0], self.pending[1:]
            if key == 'paste_start': self.paste = True; continue
            if key == 'paste_end': self.paste = False; continue
            try: self.key(key)
            except (ValueError, OSError) as exc:
                self.emit('\n' + str(exc) + '\n'); self.line = ''; self.cursor = 0; self.prompt()
            if not self.bridge or self.bridge.poll() is not None: break

    def key(self, key):
        shell = self.active
        if shell.foreground:
            if key == '\x03':
                shell.foreground['state'] = 'Terminated'; shell.foreground = None; shell.status = 130; self.emit('^C\n'); self.prompt()
            elif key == '\x1a':
                job = shell.foreground; job['state'] = 'Stopped'; shell.foreground = None
                if job not in shell.jobs.values(): shell.jobs[shell.next_job] = job; shell.next_job += 1
                self.emit('^Z\nStopped\n'); self.prompt()
            return
        if shell.input_capture is not None:
            capture = shell.input_capture
            if key in ('\x04', '\x03'):
                shell.input_capture = None; self.emit('\n'); self.prompt(); return
            if len(key) == 1:
                if key in ('\r', '\n'):
                    data = (capture['buffer'] + '\n').encode(); capture['buffer'] = ''
                    targets = [(op, path) for op, path in capture['redirects'] if op in ('>', '>>', '1>', '1>>')]
                    for op, path in targets: shell.fs.write(path, data, append=True)
                    self.emit('\n')
                    if not targets: self.emit(data); shell.output += data
                elif key in ('\x7f', '\x08'): capture['buffer'] = capture['buffer'][:-1]; self.emit('\b \b')
                elif key >= ' ': capture['buffer'] += key; self.emit(key)
            return
        if shell.editor: self.editor_key(key); return
        if shell.pager is not None:
            if key == 'q': shell.pager = None; self.prompt()
            elif key in (' ', '\r', '\n'): self.page()
            return
        if key == '\x03':
            self.line = ''; self.cursor = 0; shell.status = 130; self.emit('^C\n'); self.prompt(); return
        if key == '\x04' and not self.line: self.exit_shell(); return
        if key == '\x0c': self.emit('\x1b[2J\x1b[H'); self.redraw(); return
        if key in ('\r', '\n') and not self.paste:
            command = self.line; self.line = ''; self.cursor = 0; self.emit('\n')
            if command.strip(): shell.history.append(command); del shell.history[:-500]
            result = shell.execute(command)
            self.emit(result.out); self.emit(result.err)
            if shell.docker and shell.docker.session:
                session = shell.docker.session; shell.docker.session = None
                session[0]['shell'].exited = False; session[0]['shell'].interactive = True; self.sessions.append(session)
            if self.active.editor: self.render_editor(); return
            if self.active.pager is not None: self.page(); return
            if self.active.input_capture is not None or self.active.foreground: return
            if shell.exited: self.exit_shell(); return
            self.prompt(); return
        if key in ('up', 'down'):
            self.history_index = max(0, min(len(shell.history), self.history_index + (-1 if key == 'up' else 1)))
            self.line = shell.history[self.history_index] if self.history_index < len(shell.history) else ''; self.cursor = len(self.line)
        elif key in ('left', 'right'): self.cursor = max(0, min(len(self.line), self.cursor + (-1 if key == 'left' else 1)))
        elif key in ('home', '\x01'): self.cursor = 0
        elif key in ('end', '\x05'): self.cursor = len(self.line)
        elif key in ('\x7f', '\x08'):
            if self.cursor: self.line = self.line[:self.cursor - 1] + self.line[self.cursor:]; self.cursor -= 1
        elif key == 'delete': self.line = self.line[:self.cursor] + self.line[self.cursor + 1:]
        elif key == '\x15': self.line = self.line[self.cursor:]; self.cursor = 0
        elif key == '\t':
            prefix = self.line[:self.cursor]; start = prefix.rfind(' ') + 1; word = prefix[start:]
            if start == 0: matches = [c for c in shell.commands() if c.startswith(word)]
            else:
                hits = shell.fs.glob(shell.path(word + '*'))
                matches = [(h if word.startswith('/') else p.relpath(h, shell.cwd)) + ('/' if shell.fs.get(h).kind == 'dir' else '') for h in hits]
            if len(matches) == 1:
                value = shlex.quote(matches[0]) + ('' if matches[0].endswith('/') else ' ')
                self.line = self.line[:start] + value + self.line[self.cursor:]; self.cursor = start + len(value)
            elif matches: self.emit('\n' + '  '.join(matches) + '\n')
        elif len(key) == 1 and (key >= ' ' or self.paste and key in '\r\n'):
            if len(self.line) < 32768:
                at_end = self.cursor == len(self.line)
                self.line = self.line[:self.cursor] + key + self.line[self.cursor:]; self.cursor += 1
                if at_end:
                    self.emit(key); self.rendered_prefix = self.line; return
        else: return
        self.redraw()

    def exit_shell(self):
        self.emit('exit\n')
        if self.sessions:
            container, is_exec = self.sessions.pop()
            if not is_exec: self.shell.docker.finish(container)
            self.prompt()
        else: self.bridge.close()

    def page(self):
        lines = self.active.pager
        count = max(1, self.rows - 3)
        self.emit('\n'.join(lines[:count]) + '\n'); del lines[:count]
        self.emit('--More-- (q to quit)')

    def render_editor(self):
        e = self.active.editor
        lines = e['text'].split('\n'); before = e['text'][:e['cursor']]
        row, col = before.count('\n'), len(before.rsplit('\n', 1)[-1])
        top = max(0, row - max(1, self.rows - 5))
        self.emit('\x1b[2J\x1b[H' + '  nano (Shellground simulation)  ' + e['path'] + (' *' if e['dirty'] else '') + '\n')
        self.emit('\n'.join(lines[top:top + max(1, self.rows - 3)]))
        footer = 'File Name to Write: ' + e.get('filename', e['path']) if e['mode'] == 'save' else 'Save modified buffer? Y Yes / N No / Ctrl+C Cancel' if e['mode'] == 'confirm' else '^O Write Out   ^X Exit   ^K Cut line'
        self.emit(f'\x1b[{max(2, self.rows - 1)};1H\x1b[2K' + footer)
        if e['mode'] == 'edit': self.emit(f'\x1b[{row - top + 2};{col + 1}H')

    def editor_key(self, key):
        e = self.active.editor
        if e['mode'] == 'help':
            if key in ('\x18', '\x03'): e['mode'] = 'edit'; self.render_editor()
            return
        if e['mode'] == 'save':
            if key in ('\r', '\n'):
                text = e['text']
                if text and not text.endswith('\n'): text += '\n'
                self.active.fs.write(self.active.path(e.get('filename', e['path'])), text.encode())
                e.update(text=text, dirty=False, mode='edit')
                if e.pop('exit_after', False): self.active.editor = None; self.emit('\x1b[2J\x1b[H'); self.prompt(); return
            elif key == '\x03': e['mode'] = 'edit'
            elif key in ('\x7f', '\x08'): e['filename'] = e.get('filename', e['path'])[:-1]
            elif len(key) == 1 and key >= ' ': e['filename'] = e.get('filename', e['path']) + key
        elif e['mode'] == 'confirm':
            if key.lower() == 'y': e.update(mode='save', filename=e['path'], exit_after=True)
            elif key.lower() == 'n': self.active.editor = None; self.emit('\x1b[2J\x1b[H'); self.prompt(); return
            elif key == '\x03': e['mode'] = 'edit'
        elif key == '\x0f': e.update(mode='save', filename=e['path'])
        elif key == '\x07':
            e['mode'] = 'help'
            self.emit('\x1b[2J\x1b[Hnano learning editor\nCtrl+K cut line, Ctrl+U paste cut line\nCtrl+O save, Ctrl+X exit\nArrow keys/Home/End move cursor\nCtrl+X return to editor'); return
        elif key == '\x15':
            value = e.get('cut', ''); n = e['cursor']; e['text'] = e['text'][:n] + value + e['text'][n:]; e['cursor'] += len(value); e['dirty'] |= bool(value)
        elif key == '\x18':
            if e['dirty']: e['mode'] = 'confirm'
            else: self.active.editor = None; self.emit('\x1b[2J\x1b[H'); self.prompt(); return
        elif key == '\x0b':
            start = e['text'].rfind('\n', 0, e['cursor']) + 1
            end = e['text'].find('\n', e['cursor']); end = len(e['text']) if end == -1 else end + 1
            e['cut'] = e['text'][start:end]
            e['text'] = e['text'][:start] + e['text'][end:]; e['cursor'] = start; e['dirty'] = True
        elif key in ('left', 'right'): e['cursor'] = max(0, min(len(e['text']), e['cursor'] + (-1 if key == 'left' else 1)))
        elif key in ('home', '\x01'): e['cursor'] = e['text'].rfind('\n', 0, e['cursor']) + 1
        elif key in ('end', '\x05'):
            end = e['text'].find('\n', e['cursor']); e['cursor'] = len(e['text']) if end == -1 else end
        elif key in ('up', 'down'):
            lines = e['text'].split('\n'); before = e['text'][:e['cursor']]; row = before.count('\n'); col = len(before.rsplit('\n', 1)[-1])
            row = max(0, min(len(lines) - 1, row + (-1 if key == 'up' else 1)))
            e['cursor'] = sum(len(line) + 1 for line in lines[:row]) + min(col, len(lines[row]))
        elif key in ('\x7f', '\x08') and e['cursor']:
            n = e['cursor']; e['text'] = e['text'][:n - 1] + e['text'][n:]; e['cursor'] -= 1; e['dirty'] = True
        elif len(key) == 1 and (key >= ' ' or key in '\r\n\t'):
            value = '\n' if key == '\r' else key
            n = e['cursor']; e['text'] = e['text'][:n] + value + e['text'][n:]; e['cursor'] += 1; e['dirty'] = True
        self.render_editor()
