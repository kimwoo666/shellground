"""Android packaging adapter for the existing desktop teaching/grading sources.

No alternate shell, Conda or Jupyter implementation. Only the ARM wheel identity
and mobile display controls differ. The ARM NumPy wheel used as grading evidence
is checked against PyPI's published SHA256 before it enters the offline guest.
"""
import argparse
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import shutil
import sys
import urllib.request
import zipfile
from email.parser import Parser

ROOT = Path(__file__).resolve().parents[2]
DESKTOP = ROOT / 'desktop'
sys.path.insert(0, str(DESKTOP))


# These are execution budgets only. Keep exact replacements so any upstream
# change requires review rather than silently modifying teaching/grade logic.
MOBILE_NOTEBOOK_BUDGETS = {
    'guest_service.py': {
        'self.client.wait_for_ready(timeout=20)': 'self.client.wait_for_ready(timeout=120)',
        "def exchange(self, code='', expressions=None, timeout=10, history=True):":
            "def exchange(self, code='', expressions=None, timeout=30, history=True):",
    },
    'guest_lessons.py': {
        'text=True, timeout=25)': 'text=True, timeout=120)',
        'time.monotonic()+20': 'time.monotonic()+60',
        'timeout=min(10,remaining)': 'timeout=min(30,remaining)',
    },
}
MOBILE_CONDA_BUDGETS = {
    'guest_runtime.py': {
        'def run(argv,timeout=45,input=None):':'def run(argv,timeout=120,input=None):',
        'def conda(*args,timeout=45):':'def conda(*args,timeout=120):',
        'timeout=8,input=json.dumps(request)':'timeout=30,input=json.dumps(request)',
    },
}


def mobile_notebook_source(name, text):
    for old, new in MOBILE_NOTEBOOK_BUDGETS.get(name, {}).items():
        expected = 2 if old in ('time.monotonic()+20', 'timeout=min(10,remaining)') else 1
        if text.count(old) != expected:
            raise ValueError('Review changed mobile execution budget: '+name+' '+old)
        text = text.replace(old, new)
    return text


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')


def conda_data():
    from conda_teaching.engine import course
    from conda_teaching.mobile_course import mobile_steps, PROVIDED_DIAGNOSTICS
    spec = course()
    diagnostics = PROVIDED_DIAGNOSTICS | {
        'python -m pip --version', 'python -m pip show numpy',
        'python -c "import numpy as np; print(np.__version__); print(np.__file__); print(np.array([2, 5]).sum())"',
    }
    units = []
    number = 0
    for source in spec['units']:
        if source['kind'] != 'review': number += 1
        steps = deepcopy(source.get('learning_steps')) or mobile_steps(source['key'])
        problems = []
        for problem in source['problems']:
            problems.append(dict(id=problem['id'], goal=problem['goal'], hint=problem['hint'],
                role=problem['role'],
                answer_fields=[dict(key=f['key'], label=f['label'],
                    input='boolean' if isinstance(f.get('expected'), bool) else 'text')
                    for f in problem['answer_fields']],
                example_commands=problem['reference_commands'] if problem['role']=='example' else [],
                provided_diagnostics=[c for c in problem['reference_commands'] if c in diagnostics],
                diagnostic_notice='목표에 맞는 환경을 직접 선택한 터미널에서 확인하세요. 진단식은 설치나 활성화를 대신하지 않습니다.',
                initial_fixture=deepcopy(problem['initial_fixture']),
                mission=dict(kind='conda', problem=deepcopy(problem),
                    probes=deepcopy(spec['observer_contract']['module_probes']))))
        units.append(dict(key=source['key'], title=source['title'], kind=source['kind'], topic='Conda · pip',
            number=number, prerequisites=source['prerequisites'], explanation=source['explanation'],
            syntax=source['syntax'], pitfall=source['pitfall'], learning_steps=steps, problems=problems))
    return dict(schema=2, execution='real-guest', course='conda', bootstrap=spec['bootstrap'],
        counts=spec['counts'], official_sources=spec['official_sources'], units=units)


def arm_wheel_identity(wheels, verify_online=False):
    filename='numpy-2.3.5-cp312-cp312-manylinux_2_27_aarch64.manylinux_2_28_aarch64.whl'
    path=wheels/filename
    checksum=hashlib.sha256(path.read_bytes()).hexdigest()
    receipt=wheels/'numpy-official.json'
    if verify_online:
        with urllib.request.urlopen('https://pypi.org/pypi/numpy/2.3.5/json', timeout=30) as response:
            records=json.load(response)['urls']
        record=next(r for r in records if r['filename']==filename)
        if checksum!=record['digests']['sha256']: raise ValueError('Official ARM NumPy hash mismatch')
        write_json(receipt, dict(filename=filename, sha256=checksum, url=record['url']))
    record=json.loads(receipt.read_text())
    if record['filename']!=filename or checksum!=record['sha256']:
        raise ValueError('ARM NumPy differs from verified official asset')
    return dict(name='numpy', version='2.3.5', **record,
        tags=('cp312-cp312-manylinux_2_27_aarch64','cp312-cp312-manylinux_2_28_aarch64'))


def export(destination, wheels, verify_online=False, reuse_wheel_identity=False):
    from conda_teaching.engine import SHELL_INIT
    from notebook_teaching.course import lessons, ENV_GUIDE
    destination.mkdir(parents=True, exist_ok=True)
    write_json(destination/'conda-course.json', conda_data())
    notebook_units=[]
    for index,unit in enumerate(lessons(),1):
        notebook_units.append(dict(unit,topic='Jupyter',number=index,
            learning_steps=[dict(title=title,explanation=explanation,commands='',observation='') for title,explanation in unit['steps']]))
    write_json(destination/'notebook-course.json', dict(schema=1, environment=ENV_GUIDE, units=notebook_units))
    if reuse_wheel_identity:
        # Allowed only for a source-only update using the separately pinned APK.
        # No wheel is installed or replaced in this path.
        identity=json.loads((wheels/'numpy-official.json').read_text())
        if identity.get('version')!='2.3.5' or identity.get('name')!='numpy' or not identity.get('sha256'):
            raise ValueError('Missing previously verified ARM wheel identity')
    else:identity=arm_wheel_identity(wheels, verify_online)
    sources={}
    real=destination/'real-guest'; real.mkdir(exist_ok=True)
    for source in sorted((DESKTOP/'guest').glob('*.py')):
        text=source.read_text()
        if source.name=='conda_lab.py':
            # Keep the same observed-state grader. The outer Android request
            # includes slow serial framing; allow 300s inside its 360s bound.
            if text.count('timeout=115)')!=1:raise ValueError('Review changed Conda guest execution budget')
            text=text.replace('timeout=115)','timeout=300)')
        (real/source.name).write_text(text)
        sources['guest/'+source.name]=hashlib.sha256(source.read_bytes()).hexdigest()
    shutil.copy2(DESKTOP/'lab/lab.py', real/'lab.py')
    shutil.copy2(DESKTOP/'guest/bashrc', real/'bashrc')
    conda=destination/'conda-guest'; conda.mkdir(exist_ok=True)
    mapping={'conda_runtime.py':'guest_runtime.py', 'conda_setup.py':'setup_runtime.py',
        'installer_sources.py':'installer_sources.py', 'pip_runtime.py':'pip_runtime.py',
        'pip_wheel.py':'pip_wheel.py', 'guest_files.py':'guest_files.py'}
    for target,name in mapping.items():
        source=DESKTOP/'conda_teaching'/name
        text=source.read_text(encoding='utf-8')
        for old,new in MOBILE_CONDA_BUDGETS.get(name,{}).items():
            if text.count(old)!=1:raise ValueError('Review changed Conda subprocess budget')
            text=text.replace(old,new)
        if name=='pip_wheel.py':
            assignment=next(n for n in ast.parse(text).body if isinstance(n,ast.Assign)
                and any(isinstance(t,ast.Name) and t.id=='NUMPY_WHEEL' for t in n.targets))
            lines=text.splitlines(keepends=True)
            # Preserve every observation/check. Replace only the signed asset's
            # architecture, tags, download URL and digest, not the scoring code.
            lines[assignment.lineno-1:assignment.end_lineno]=['NUMPY_WHEEL = '+repr(identity)+'\n']
            text=''.join(lines)
        compile(text,target,'exec'); (conda/target).write_text(text,encoding='utf-8')
        sources['conda_teaching/'+name]=hashlib.sha256(source.read_bytes()).hexdigest()
    shutil.copy2(DESKTOP/'guest/shell_snapshot.py',conda/'shell_snapshot.py')
    (conda/'bashrc').write_text((DESKTOP/'guest/bashrc').read_text()+SHELL_INIT,encoding='utf-8')
    notebook=destination/'notebook-guest'; notebook.mkdir(exist_ok=True)
    for name in ('guest_setup.py','guest_service.py','guest_lessons.py'):
        original=DESKTOP/'notebook_teaching'/name
        text=mobile_notebook_source(name, original.read_text())
        (notebook/name).write_text(text)
        sources['notebook_teaching/'+name]=hashlib.sha256(original.read_bytes()).hexdigest()
    # Stored beside, not inside, the APK assets: wheels are installed in the
    # bundled guest once, instead of shipping them twice in the Android app.
    records=[]
    for path in sorted(wheels.glob('*.whl')):
        if path.name==identity['filename']:continue
        with zipfile.ZipFile(path) as archive:
            metadata=Parser().parsestr(archive.read(next(n for n in archive.namelist() if n.endswith('.dist-info/METADATA'))).decode())
        records.append(dict(filename=path.name,sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            size=path.stat().st_size,name=metadata['Name'],version=metadata['Version']))
    if not reuse_wheel_identity:
        write_json(wheels/'manifest.json',dict(schema=1,platform='linux-aarch64',python='3.12',
            requirements=['ipykernel==7.3.0','jupyter-client==8.10.0','nbformat==5.11.1'],wheels=records))
    write_json(destination/'port-source-manifest.json',dict(schema=1,sources=sources,
        architecture_adapter=identity,conda_problems=60,notebook_problems=18,
        mobile_execution_budgets=dict(conda_guest_seconds=300,conda=MOBILE_CONDA_BUDGETS,notebook=MOBILE_NOTEBOOK_BUDGETS)))
    print('Android shared course export: Conda/pip 60; Jupyter 18; current real guest graders',flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--destination',type=Path,required=True)
    parser.add_argument('--wheels',type=Path,default=ROOT/'android/.native-runtime/port-assets/wheels')
    parser.add_argument('--verify-online',action='store_true')
    parser.add_argument('--reuse-wheel-identity',action='store_true')
    args=parser.parse_args();export(args.destination,args.wheels,args.verify_online,args.reuse_wheel_identity)
