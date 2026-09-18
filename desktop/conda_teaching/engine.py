"""Use the existing real-VM transport for the Conda course, never host Conda."""
import base64
import json
from pathlib import Path
import sys

from engine import LabError, resource_path
from platform_runtime import runtime_tag
from real_vm import RealEngine, runtime_info, runtime_root

SHELL_INIT='''
export CONDARC=/opt/shellground/condarc CONDA_OFFLINE=true CONDA_NO_PLUGINS=true
export CONDA_SOLVER=classic CONDA_REPORT_ERRORS=false
unset PYTHONPATH PYTHONHOME PIP_TARGET PIP_PREFIX PIP_USER PIP_REQUIRE_VIRTUALENV
export PYTHONNOUSERSITE=1 PIP_CONFIG_FILE=/dev/null PIP_NO_INDEX=1 PIP_DISABLE_PIP_VERSION_CHECK=1
source /opt/shellground/miniconda/etc/profile.d/conda.sh
if [[ -s /opt/shellground/conda-initial-env ]]; then
    conda activate "$(</opt/shellground/conda-initial-env)"
fi
'''


def course(include_pip=True):
    value=json.loads(resource_path('conda_teaching/course_spec.json').read_text(encoding='utf-8'))
    if value.get('schema')!=1 or value.get('kind')!='conda-course-spec':raise ValueError('Conda course data is invalid')
    if include_pip:
        pip=pip_course()
        if [unit['key'] for unit in value['units']]!=pip['append_contract']['existing_order']:
            raise ValueError('Existing Conda lesson keys changed before pip append')
        value['units'].extend(pip['units'])
        for name in ('numpy_present','numpy_absent'):
            value['grading_operations'][name]=pip['observer_contract'][name]
        for name in ('preserved_except_numpy','environment_preserved'):
            value['grading_operations'][name]={'args':['environment'],'meaning':pip['observer_contract']['preservation']}
        value['counts'].update(lessons=17,problems=60)
    return value


def pip_course():
    value=json.loads(resource_path('conda_teaching/pip_course_spec.json').read_text(encoding='utf-8'))
    if value.get('schema')!=1 or value.get('kind')!='conda-pip-course-spec':raise ValueError('pip course data is invalid')
    return value


def conda_runtime():
    candidates=[runtime_root()]
    if not getattr(sys,'frozen',False):candidates.insert(0,Path(__file__).resolve().parents[1]/'.vm-runtime-conda'/runtime_tag())
    for root in candidates:
        try:
            root,spec=runtime_info(root)
            if spec.get('conda_course') is True:return root
        except LabError:pass
    raise LabError('검증된 실제 Conda 런타임이 이 배포본에 없습니다. 개인 Conda를 대신 실행하지 않습니다.')


def available():
    try:conda_runtime();return True
    except LabError:return False


def configure(engine,setup=False,pip=False):
    files={'conda_runtime.py':resource_path('conda_teaching/guest_runtime.py').read_bytes(),
           'conda_setup.py':resource_path('conda_teaching/setup_runtime.py').read_bytes(),
           'installer_sources.py':resource_path('conda_teaching/installer_sources.py').read_bytes(),
           'shell_snapshot.py':resource_path('guest/shell_snapshot.py').read_bytes(),
           'bashrc':(resource_path('guest/bashrc').read_text()+('' if setup else SHELL_INIT)).encode()}
    if pip:
        for name in ('pip_runtime.py','pip_wheel.py'):
            files[name]=resource_path('conda_teaching/'+name).read_bytes()
    for name,data in files.items():
        script="import sys;from pathlib import Path;sys.path.insert(0,'/opt/shellground');from agent import require_guest;require_guest();Path('/opt/shellground/'+sys.argv[1]).write_bytes(sys.stdin.buffer.read())"
        result=engine.channel.request('exec',timeout=10,root=True,cwd='/tmp',argv=['python3','-c',script,name],input=base64.b64encode(data).decode())
        if result['code']:raise LabError(base64.b64decode(result['err']).decode(errors='replace'))
    if pip:
        from .pip_assets import install_assets
        install_assets(engine.channel)


class CondaEngine(RealEngine):
    def __init__(self,root=None):
        super().__init__(root)
        self.mission=None;self.ready=None

    def start_problem(self,problem,probes):
        if self.root is None:self.root=conda_runtime()
        self.boot();configure(self,pip=any('pip_distributions' in entry for entry in problem['initial_fixture']['environments']))
        self.mission={'kind':'conda','problem':problem,'probes':probes}
        self.ready=self.channel.request('prepare',timeout=125,mission=self.mission)
        self.bridge=self.channel.open_terminal(self.ready['start'])
        return self.bridge

    def grade_problem(self,answers):
        if not self.bridge or not self.mission:raise LabError('먼저 실제 실습을 시작하세요.')
        return self.channel.request('grade',timeout=125,mission=self.mission,session=self.bridge.sid,answers=answers)

    def setup_call(self,action,payload):
        result=self.channel.request('exec',timeout=100,run_timeout=95,root=True,cwd='/tmp',
            argv=['/opt/shellground/miniconda/bin/python','-I','/opt/shellground/conda_setup.py',action],
            input=base64.b64encode(json.dumps(payload).encode()).decode())
        if result['code']:raise LabError(base64.b64decode(result['err']).decode(errors='replace')[-2000:])
        return json.loads(base64.b64decode(result['out']))

    def start_setup(self):
        if self.root is None:self.root=conda_runtime()
        # The installer has its own constructor plugin. Inheriting the normal
        # room's CONDA_NO_PLUGINS or manager shell variables breaks bootstrap.
        self.boot();configure(self,setup=True)
        self.mission=None
        self.ready=self.setup_call('prepare',{})
        self.bridge=self.channel.open_terminal(self.ready['start'])
        return self.bridge

    def grade_setup(self):
        if not self.bridge or not self.ready or 'prefix' not in self.ready:
            raise LabError('먼저 설치 실습을 여세요.')
        return self.setup_call('grade',{'prefix':self.ready['prefix']})

    def inspect_files(self,relative=None):
        if not self.channel or not self.ready:raise LabError('먼저 실제 실습을 시작하세요.')
        argv=['/usr/bin/python3','-c',resource_path('conda_teaching/guest_files.py').read_text(),
              'list' if relative is None else 'read']
        if relative is not None:argv.append(relative)
        result=self.channel.request('exec',timeout=8,run_timeout=5,root=False,
                                    cwd='/home/learner/conda-work',argv=argv)
        if result['code']:raise LabError(base64.b64decode(result['err']).decode(errors='replace')[-800:])
        return json.loads(base64.b64decode(result['out']))
