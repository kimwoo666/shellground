"""Host adapter for actual Jupyter running entirely inside the private VM."""
import base64
import json
import threading
import time
from engine import LabError
from real_vm import RealEngine
from conda_teaching.engine import conda_runtime
from .assets import install_assets

SERVICE = '/opt/shellground/notebook-assets/guest_service.py'


class NotebookEngine(RealEngine):
    def __init__(self, root=None):
        super().__init__(root)
        self.operation_lock = threading.Lock()
        self.notebook_ready = False
        self.lesson_baseline = None

    def start_notebook(self, status=lambda value: None):
        if self.root is None: self.root = conda_runtime()
        self.boot(status)
        if self.notebook_ready: return self.call('ping')
        install_assets(self.channel, status)
        status('두 Python 환경에 Jupyter 커널을 준비합니다.')
        result = self.channel.request('exec', timeout=125, run_timeout=120, root=True, cwd='/tmp',
            argv=['python3', '/opt/shellground/notebook-assets/guest_setup.py'])
        if result['code']:
            raise LabError('Jupyter 환경 준비 실패: ' + base64.b64decode(result['err']).decode(errors='replace')[-3000:])
        self.notebook_ready = True
        deadline = time.monotonic() + 15
        while time.monotonic() < deadline:
            try: return self.call('ping')
            except (LabError, OSError): time.sleep(.15)
        self.notebook_ready = False
        raise LabError('실제 Jupyter 서비스가 시작되지 않았습니다.')

    def call(self, action, **arguments):
        if not self.channel: raise LabError('노트북 실습을 먼저 여세요.')
        payload = json.dumps(dict(action=action, **arguments), ensure_ascii=False).encode()
        result = self.channel.request('exec', timeout=8, run_timeout=5, root=False,
            cwd='/home/learner/notebook-work', argv=['python3', SERVICE, 'client'],
            input=base64.b64encode(payload).decode())
        if result['code']:
            raise LabError(base64.b64decode(result['err']).decode(errors='replace')[-1800:])
        response = json.loads(base64.b64decode(result['out']))
        if not response.get('ok'): raise LabError(response.get('error', 'Jupyter 응답 오류'))
        return response['value']

    def perform(self, operation, **arguments):
        with self.operation_lock:
            job = self.call('begin', request=dict(operation=operation, **arguments))['job']
            deadline = time.monotonic() + 45
            while time.monotonic() < deadline:
                response = self.call('poll', job=job)
                if response['done']: return response['result']
            self.interrupt()
            raise TimeoutError('Jupyter 작업 제한 시간을 초과했습니다. 입력 코드는 유지됩니다.')

    def interrupt(self):
        if self.notebook_ready and self.channel:
            return self.call('interrupt')

    def start_problem(self, problem, status=lambda value: None):
        self.start_notebook(status)
        status('커널·패키지·문서의 시작 상태를 준비합니다.')
        self.lesson_baseline = self.perform('prepare', problem=problem)
        status('커널 준비 완료 · Bash를 연결합니다.')
        return self.lesson_baseline

    def grade_problem(self, problem, cells):
        if self.lesson_baseline is None: raise LabError('실습을 먼저 여세요.')
        return self.perform('grade', problem=problem, baseline=self.lesson_baseline, cells=cells)

    def open_bash(self):
        if self.bridge: self.bridge.close()
        # Bash and the selected kernel are intentionally separate environments.
        script = ('import sys; from pathlib import Path; p=Path("/opt/shellground/bashrc"); '
                  'p.write_bytes(sys.stdin.buffer.read())')
        from engine import resource_path
        rc = resource_path('guest/bashrc').read_bytes() + b'''\nsource /opt/shellground/miniconda/etc/profile.d/conda.sh
export CONDARC=/opt/shellground/condarc CONDA_OFFLINE=true CONDA_SOLVER=classic
export JUPYTER_DATA_DIR=/home/learner/notebook-jupyter/share/jupyter
export PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1
export OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1
conda activate /home/learner/notebook-envs/data
'''
        result = self.channel.request('exec', root=True, cwd='/tmp', argv=['python3','-c',script],
                                      input=base64.b64encode(rc).decode())
        if result['code']: raise LabError('노트북 Bash 초기화 실패')
        self.bridge = self.channel.open_terminal('/home/learner/notebook-work')
        return self.bridge

    def close(self):
        try:
            if self.notebook_ready and self.channel and not self.channel.closed.is_set():
                try: self.interrupt()
                except (LabError, OSError, TimeoutError): pass
        finally:
            self.notebook_ready = False
            self.lesson_baseline = None
            super().close()
