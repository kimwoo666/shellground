"""Private worker lifecycle: no polling loop, no execution on the Qt UI thread."""
import json
import os
from pathlib import Path
import queue
import subprocess
import sys
import tempfile
import threading


def worker_environment(desktop):
    """Minimal environment for OUR interpreter, not a host shell command.

    A frozen worker reuses the extracted bundle. On Linux it must also have
    that bundle's loader path; retaining _PYI_* while dropping the loader path
    makes numpy/OpenBLAS and Qt native imports fail. Do not inherit the user's
    arbitrary loader paths, Python paths, Conda variables, or credentials.
    """
    env = {k: v for k, v in os.environ.items() if k in ('PATH', 'SYSTEMROOT', 'WINDIR', 'TMP', 'TEMP', 'LANG', 'LC_ALL')}
    if getattr(sys, 'frozen', False):
        env.update({k: v for k, v in os.environ.items() if k.startswith('_PYI_')})
        if sys.platform.startswith('linux'):
            env['LD_LIBRARY_PATH'] = str(sys._MEIPASS)
    env.update(PYTHONPATH=os.pathsep.join([str(desktop / '.python-runtime'), str(desktop)]),
               PYTHONIOENCODING='utf-8', PYTHONUNBUFFERED='1', PYTHONNOUSERSITE='1',
               OPENBLAS_NUM_THREADS='1', OMP_NUM_THREADS='1', MKL_NUM_THREADS='1',
               NUMEXPR_NUM_THREADS='1', MPLBACKEND='Agg')
    return env


class PythonEngine:
    def __init__(self, timeout=8):
        self.timeout = timeout
        self.process = None
        self.workspace = None
        self.messages = queue.Queue()
        self.lock = threading.Lock()
        self.stderr = ''

    def start(self, initial='', files=None):
        self.close()
        self.workspace = tempfile.TemporaryDirectory(prefix='shellground-python-')
        root = Path(self.workspace.name)
        (root / '.shellground-python-session').write_text('1')
        for name, spec in (files or {}).items():
            path = (root / name).resolve()
            if not path.is_relative_to(root) or path == root: raise ValueError('실습 파일 경로 오류')
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(spec['text'], encoding=spec.get('encoding', 'utf-8'))
        desktop = Path(__file__).resolve().parent.parent
        argv = ([sys.executable, '--internal-python-worker', str(root)] if getattr(sys, 'frozen', False)
                else [sys.executable, '-u', str(desktop / 'shellground.py'), '--internal-python-worker', str(root)])
        env = worker_environment(desktop)
        options = {'creationflags': subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {'start_new_session': True}
        self.messages = queue.Queue()
        self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                        text=True, encoding='utf-8', cwd=root, env=env, **options)
        process, messages = self.process, self.messages
        def read():
            try:
                for line in process.stdout:
                    try: messages.put(json.loads(line))
                    except ValueError: messages.put({'ok': False, 'error': 'Python 응답 형식 오류'})
            finally: messages.put({'ok': False, 'error': 'Python 작업 프로세스가 종료되었습니다.'})
        def errors():
            self.stderr = process.stderr.read(65536)
        threading.Thread(target=read, daemon=True).start()
        threading.Thread(target=errors, daemon=True).start()
        try:
            ready = self.messages.get(timeout=30)
            if not ready.get('ready'): raise RuntimeError(ready.get('error', '') + '\n' + self.stderr)
            result = self.execute(initial) if initial else {'ok': True, 'output': ''}
            if not result['ok']: raise RuntimeError('실습 준비 실패: ' + result.get('error', ''))
        except BaseException:
            self.close()
            raise
        return result

    def request(self, action, **payload):
        with self.lock:
            if not self.process or self.process.poll() is not None: raise RuntimeError('Python 실습을 먼저 시작하세요.')
            self.process.stdin.write(json.dumps(dict(action=action, **payload), ensure_ascii=False) + '\n')
            self.process.stdin.flush()
            try: return self.messages.get(timeout=self.timeout)
            except queue.Empty:
                self.cancel()
                raise TimeoutError('제한 시간을 초과해 Python 작업을 중단했습니다. 코드는 편집창에 남아 있습니다. 새 실습에서 다시 실행하세요.')

    def execute(self, code): return self.request('execute', code=code)
    def inspect(self, names, probes=None): return self.request('inspect', names=list(names), probes=probes or {})

    def cancel(self):
        process = self.process
        if process and process.poll() is None:
            process.terminate()
            try: process.wait(timeout=2)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=2)

    def close(self):
        self.cancel()
        if self.process:
            for stream in (self.process.stdin, self.process.stdout, self.process.stderr):
                if stream: stream.close()
        self.process = None
        if self.workspace:
            self.workspace.cleanup()
            self.workspace = None
