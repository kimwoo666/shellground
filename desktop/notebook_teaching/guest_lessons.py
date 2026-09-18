"""Teaching state inspection, executed as learner inside our disposable guest.

Actual package commands and a separate real replay kernel. No expected answers
are injected into the learner's namespace; errors do not reset that namespace.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import zipfile
from guest_service import ENVS, KERNELS, WORK


def run(env, *args):
    environment = {k:v for k,v in os.environ.items() if k not in ('PYTHONPATH','PYTHONHOME')}
    result = subprocess.run([str(ENVS/env/'bin/python'), *args], env=environment,
                            cwd=WORK, capture_output=True, text=True, timeout=25)
    if result.returncode: raise RuntimeError((result.stderr or result.stdout)[-2000:])
    return result.stdout


def numpy_state(env):
    # Fresh interpreter, isolated import path; a stale import or a local
    # numpy.py shadowing the actual distribution cannot satisfy this check.
    info = json.loads(run(env, '-I', '-c',
        'import importlib.util,json; s=importlib.util.find_spec("numpy"); '
        'print(json.dumps(None if s is None else {"file":s.origin}))'))
    if info is None: return dict(present=False, official=False)
    path = Path(info['file'])
    site = ENVS/env/'lib/python3.12/site-packages'
    if path != site/'numpy/__init__.py' or path.is_symlink():
        return dict(present=True, official=False, file=str(path))
    wheels = list(Path('/opt/shellground/wheels').glob('numpy-2.3.5-*.whl'))
    if len(wheels) != 1: raise RuntimeError('Verified NumPy wheel unavailable')
    with zipfile.ZipFile(wheels[0]) as wheel:
        for entry in wheel.infolist():
            if entry.is_dir() or not entry.filename.startswith(('numpy/', 'numpy.libs/')): continue
            target = site/entry.filename
            if (target.is_symlink() or not target.is_file() or
                hashlib.sha256(target.read_bytes()).digest() != hashlib.sha256(wheel.read(entry)).digest()):
                return dict(present=True, official=False, file=str(path))
    version = run(env, '-I', '-c', 'import numpy; print(numpy.__version__)').strip()
    return dict(present=True, official=version=='2.3.5', version=version, file=str(path))


def installed(env):
    return json.loads(run(env,'-I','-c',
        'import importlib.metadata as m,json,re; '
        'print(json.dumps(sorted((re.sub(r"[-_.]+","-",d.metadata["Name"].lower()),d.version) for d in m.distributions())))'))


def prepare(notebook, problem):
    notebook.stop(); notebook.cells.clear()
    for name in ('basic','data'):
        wanted = name=='data' or problem.get('both_numpy', False)
        state = numpy_state(name)
        if wanted and not state['official']:
            run(name, '-m','pip','install','--no-index','--no-cache-dir','--force-reinstall',
                '--find-links','/opt/shellground/wheels','numpy==2.3.5')
        if not wanted and state['present']:
            run(name,'-m','pip','uninstall','-y','numpy')
    # Only names reserved by this course; unrelated student registrations are
    # not recursively removed. No host Jupyter registry is involved.
    for name in ('sg-basic','sg-data','analysis-project','report-project'):
        path = KERNELS/name
        if path.is_symlink(): path.unlink()
        elif path.is_dir(): shutil.rmtree(path)
    for name in ('basic','data'):
        if name=='data' and problem.get('hidden_data'): continue
        run(name,'-m','ipykernel','install','--prefix','/home/learner/notebook-jupyter',
            '--name','sg-'+name,'--display-name','Python ('+name+')')
    if problem.get('misregistered'):
        run('basic','-m','ipykernel','install','--prefix','/home/learner/notebook-jupyter',
            '--name','analysis-project','--display-name','분석 Python')
    for name in ('source.txt','report.ipynb'):
        path=WORK/name
        if path.is_symlink() or path.is_file(): path.unlink()
        elif path.exists(): raise RuntimeError('실습 파일 자리에 폴더가 있습니다. 실습 전체 초기화가 필요합니다.')
    for name,text in problem.get('files',{}).items():
        if Path(name).name!=name: raise ValueError('Invalid fixture path')
        (WORK/name).write_text(text)
    identity=notebook.select(problem['start'])
    if problem.get('seed'):
        response=notebook.exchange(problem['seed'],history=False)
        if not response['ok']: raise RuntimeError('Notebook fixture failed')
    return dict(identity=identity, packages={n:numpy_state(n) for n in ('basic','data')},
                installed={n:installed(n) for n in ('basic','data')})


def values(notebook, problem):
    expressions={key:key for key in problem['expected']}
    expressions.update({key:f'{key!r} not in globals()' for key in problem.get('absent',[])})
    if problem.get('numpy_result'): expressions['_numpy_path']='__import__("numpy").__file__'
    if problem.get('module_path'): expressions['module_path']='module_path'
    return notebook.snapshot(expressions)


def expected_matches(state, problem):
    found=state['values']
    return all(key in found and found[key]==expected for key,expected in problem['expected'].items())


def replay(notebook, problem, document):
    # Grade in a different working directory and a different actual kernel.
    # Running a saved document must not silently restart the student's kernel
    # or repeat file writes in their work directory.
    from guest_service import Notebook
    with tempfile.TemporaryDirectory(prefix='.replay-',dir=WORK) as directory:
        for name in problem.get('files',{}):
            path=WORK/name
            if path.is_file() and not path.is_symlink(): shutil.copyfile(path,Path(directory)/name)
        observer=Notebook(workdir=directory)
        try:
            observer.select(notebook.selected)
            code=[cell for cell in document if cell['type']=='code']
            deadline=time.monotonic()+20
            for cell in code:
                remaining=deadline-time.monotonic()
                if remaining<=0: return False,'문서 재실행 제한 시간 초과'
                response=observer.exchange(cell['source'],timeout=min(10,remaining))
                if not response['ok']: return False,response['reply'].get('ename','실행 오류')+': '+response['reply'].get('evalue','')
            if not code or not expected_matches(values(observer,problem),problem):
                return False,'새 커널에서 문서 순서대로 목표 값을 만들지 못했습니다.'
            if problem.get('repeat_cells'):
                # A trailing print is not necessarily the calculation cell.
                # Verify the explicitly taught whole-document repeat policy
                # in another fresh namespace, without guessing source intent.
                observer.stop();observer.select(notebook.selected)
                deadline=time.monotonic()+20
                for cell in code:
                    for _ in range(2):
                        remaining=deadline-time.monotonic()
                        if remaining<=0:return False,'셀 반복 재실행 제한 시간 초과'
                        response=observer.exchange(cell['source'],timeout=min(10,remaining))
                        if not response['ok']:return False,'셀을 연속 두 번 실행할 때 오류가 발생했습니다.'
                if not expected_matches(values(observer,problem),problem):
                    return False,'각 코드 셀을 연속 두 번씩 실행하자 최종 원본 또는 결과가 달라졌습니다.'
            return True,'새 커널에서 재현 확인'
        finally: observer.stop()


def grade(notebook, problem, baseline, document):
    checks=[]
    def add(label,passed,detail): checks.append(dict(label=label,passed=bool(passed),detail=detail))
    identity=notebook.identity(); state=values(notebook,problem)
    prefix=str(ENVS/problem['target'])
    allowed=[str(ENVS/name) for name in problem.get('allowed_environments',(problem['target'],))]
    add('선택한 커널의 Python 환경', identity['values']['prefix'] in allowed,
        '허용 환경: '+', '.join(allowed)+' · 현재: '+identity['values']['prefix'])
    for key, expected in problem['expected'].items():
        found=state['values'].get(key)
        add(key+' 현재 값', key in state['values'] and found==expected,
            f'목표 {expected!r} · 현재 '+(repr(found) if key in state['values'] else '정의되지 않음'))
    for key in problem.get('absent',[]): add(key+' 임시 값 제거',state['values'].get(key) is True,'새 커널에 문서 밖 임시 변수가 남아 있습니다.')
    if problem.get('restart'):
        old=baseline['identity']
        changed=identity['generation']!=old['generation']
        # Count verified real starts in the target environment, not which UI
        # button was used. Target->other->target also replaces its process.
        # If the fixture started elsewhere, one first selection is NOT yet
        # a restart of the target; it must have started at least twice.
        required=1 if old['values']['prefix']==prefix else 2
        restarted=identity['starts'].get(prefix,0)-old['starts'].get(prefix,0)>=required
        add('새 커널에서 실행',changed and restarted,'출력 지우기와 변수 삭제는 커널 재시작이 아닙니다.')
    actual={item['name']:item['executable'] for item in notebook.kernels()}
    if problem.get('registration'):
        name=problem['registration']
        add('프로젝트 등록·선택',actual.get(name)==prefix+'/bin/python' and notebook.selected==name,
            name+' 등록의 실제 실행 경로를 확인하고 해당 커널을 선택하세요.')
    for name in problem['preserve']:
        add(name+' 등록 보존',actual.get(name)==str(ENVS/name.removeprefix('sg-')/'bin/python'),'기존 기본 등록이 없거나 다른 환경을 가리킵니다.')
    for name in ('basic','data'):
        current=installed(name);original=baseline['installed'][name]
        if name=='basic' and problem.get('install_basic'):
            current=[p for p in current if p[0]!='numpy'];original=[p for p in original if p[0]!='numpy']
        add(name+' 기존 패키지 목록·버전 보존',current==original,'허용된 NumPy 설치 외의 기존 패키지를 제거하거나 버전을 바꾸지 마세요.')
        packages=numpy_state(name)
        wanted=name=='data' or problem.get('both_numpy') or (name=='basic' and problem.get('install_basic'))
        add(name+' NumPy 상태',packages['official'] if wanted else not packages['present'],
            '공식 NumPy 2.3.5가 필요합니다.' if wanted else '이 환경에는 NumPy를 설치하지 않는 목표입니다.')
    if problem.get('numpy_result'):
        add('현재 커널의 NumPy 위치', str(state['values'].get('_numpy_path','')).startswith(prefix+'/lib/'), '다른 환경이나 작업 폴더의 모듈이 아닙니다.')
    if problem.get('module_path'):
        add('기록한 설치 경로',state['values'].get('module_path')==state['values'].get('_numpy_path'), 'module_path를 현재 커널의 np.__file__로 확인하세요.')
    for name,text in problem.get('files',{}).items():
        path=WORK/name
        add(name+' 원본 보존',path.is_file() and not path.is_symlink() and path.read_text()==text,'원본 파일 내용이 다르거나 없습니다.')
    if problem.get('markdown'):
        add('Markdown 메모',any(c['type']=='markdown' and c['source'].strip() not in ('','실습 메모') for c in document), '기본 메모를 분석 목적 설명으로 바꾸세요. 설명 내용의 의미를 자동 평가하지는 않습니다.')
    if problem.get('save'):
        import nbformat
        path=WORK/problem['save']; valid=False
        try:
            if not path.is_symlink():
                saved=nbformat.read(path,as_version=4); nbformat.validate(saved)
                valid=[(c.cell_type,c.source) for c in saved.cells]==[(c['type'],c['source']) for c in document]
                valid=valid and saved.metadata.kernelspec.name==notebook.selected
        except (OSError,ValueError,AttributeError): pass
        add('현재 문서 저장',valid,'report.ipynb의 코드·설명·커널 정보가 현재 문서와 같아야 합니다. 이전 출력만으로 통과하지 않습니다.')
    if problem.get('replay'):
        ok,detail=replay(notebook,problem,document)
        add('별도 새 커널의 문서 재현'+(' · 각 셀 두 번' if problem.get('repeat_cells') else ''),ok,detail)
    return dict(passed=all(item['passed'] for item in checks),checks=checks,identity=identity)
