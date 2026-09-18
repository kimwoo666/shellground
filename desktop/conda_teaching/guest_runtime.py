"""Actual Conda fixture/inspection/grading, executed ONLY in the owned guest.

No shell parsing or command emulation. Conda creates every environment; fresh
learner-owned Python processes prove interpreter and installed module behavior.
This is an educational outcome checker, not an adversarial examination sandbox.
"""
import hashlib
import json
import os
import posixpath
from pathlib import Path
import re
import signal
import subprocess
import sys

BASE=Path('/opt/shellground/miniconda')
ENVROOT=Path('/home/learner/conda-envs')
WORK=Path('/home/learner/conda-work')
STATE=Path('/opt/shellground/conda-attempt.json')
CONFIG='/opt/shellground/condarc'
CHANNEL='file:///opt/shellground/conda-channel'


def prefix(name):
    if name=='base':return BASE
    if not isinstance(name,str) or not re.fullmatch(r'sg-[a-z0-9-]+',name):
        raise ValueError('Invalid course environment name')
    path=ENVROOT/name
    if path.is_symlink() or path.resolve()!=path:raise ValueError('Environment is not a distinct owned prefix')
    return path


def artifact(relative):
    if not isinstance(relative,str) or Path(relative).is_absolute() or '..' in Path(relative).parts:
        raise ValueError('Artifact outside assigned workspace')
    path=WORK/relative
    if not path.resolve().is_relative_to(WORK.resolve()):raise ValueError('Artifact escaped workspace')
    return path


def answer_matches(actual,expected,names=()):
    """Normalize only known answer types, never arbitrary fuzzy strings."""
    if type(actual) is not type(expected):return False
    if not isinstance(expected,str):return actual==expected
    actual=actual.strip()
    if expected.startswith('/'):
        return actual.startswith('/') and posixpath.normpath(actual)==posixpath.normpath(expected)
    if expected in names and actual.startswith('/'):
        return posixpath.normpath(actual)==str(prefix(expected))
    if expected=='Conda':return actual.casefold()=='conda'
    if expected=='Linux guest':
        return actual.casefold() in ('linux guest','linux vm','리눅스 게스트','리눅스 가상머신','리눅스 가상 머신')
    return actual==expected


def preserved_snapshot(current,original,strict=False):
    # Learner mistakes may be repaired through real package transactions.
    # History remains evidence for requested specs but its timestamps/log lines
    # are not the final installed state. The management base stays strict.
    if strict:return current==original
    if current is None or original is None:return False
    return {k:v for k,v in current.items() if k!='history'}=={k:v for k,v in original.items() if k!='history'}


def environment():
    return dict(PATH='/usr/bin:/bin',HOME='/home/learner',USER='learner',LOGNAME='learner',
                LANG='C.UTF-8',LC_ALL='C.UTF-8',CONDARC=CONFIG,CONDA_OFFLINE='true',
                CONDA_SOLVER='classic',CONDA_NO_PLUGINS='true',CONDA_REPORT_ERRORS='false',
                PYTHONDONTWRITEBYTECODE='1',OPENBLAS_NUM_THREADS='1',OMP_NUM_THREADS='1')


def run(argv,timeout=45,input=None):
    process=subprocess.Popen(argv,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE,
        user=1100,group=1100,extra_groups=[],env=environment(),cwd=WORK,
        start_new_session=True,text=True)
    try:out,err=process.communicate(input,timeout=timeout)
    except subprocess.TimeoutExpired:
        os.killpg(process.pid,signal.SIGKILL);process.communicate(timeout=3)
        raise RuntimeError('Actual Conda/Python operation timed out')
    if process.returncode:raise RuntimeError((err or out)[-3000:])
    return out


def conda(*args,timeout=45):return run([str(BASE/'bin/conda'),*args],timeout)


def digest(path):
    value=hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda:stream.read(1024*1024),b''):value.update(block)
    return value.hexdigest()


def snapshot(name,pip_names=()):
    target=prefix(name)
    if not (target/'conda-meta/history').is_file():return None
    records={}
    for path in sorted((target/'conda-meta').glob('*.json')):
        record=json.loads(path.read_text());records[record['name']]=record
    listed={r['name']:r for r in json.loads(conda('list','--prefix',str(target),'--json'))}
    validate_package_roster(records,listed,pip_names)
    for name_,record in records.items():
        if any(record.get(key)!=listed[name_].get(key if key!='build' else 'build_string') for key in ('version','build')):
            raise ValueError('Conda package identity disagrees: '+name_)
    from conda.history import History
    requested=History(str(target)).get_requested_specs_map()
    contents={}
    # Verify teaching modules against their package-supplied path hashes.
    for record in records.values():
        if record['name'] not in ('training-math','training-text'):continue
        import tarfile
        module=record['name'].replace('-','_')
        archive_path=Path('/opt/shellground/conda-channel/noarch')/(record['name']+'-'+record['version']+'-'+record['build']+'.tar.bz2')
        with tarfile.open(archive_path) as archive:
            original=archive.extractfile('site-packages/'+module+'/__init__.py').read()
        module_path=target/'lib/python3.12/site-packages'/module/'__init__.py'
        if module_path.resolve()!=module_path or digest(module_path)!=hashlib.sha256(original).hexdigest():
            raise ValueError('Installed teaching module differs from immutable package')
        contents[str(module_path.relative_to(target))]=digest(module_path)
        # noarch link records retain source paths (site-packages/...), while
        # installation relocates them into lib/python3.12/site-packages.
        # The immutable archive-to-installed-file comparison above verifies
        # content without pretending the source paths are final prefix paths.
    essential={key:{k:r.get(k) for k in ('name','version','build','build_number','subdir','channel','url')} for key,r in records.items()}
    return {'prefix':str(target),'packages':essential,'history':digest(target/'conda-meta/history'),
            'requested':{key:str(value) for key,value in requested.items()},'contents':contents,
            'python_hash':digest(target/'bin/python') if (target/'bin/python').is_file() else None}


def validate_package_roster(records,listed,pip_names=()):
    extras=set(listed)-set(records)
    if (set(records)-set(listed) or not extras.issubset(pip_names) or any(
            listed[name].get('channel')!='pypi' or listed[name].get('build_string')!='pypi_0'
            for name in extras)):
        raise ValueError('Conda list and package metadata disagree')


def pip_helper():
    # The guest runs this file as a script; host tests import it as a package.
    if __package__:
        from . import pip_runtime
    else:
        import pip_runtime
    return pip_runtime


def python_probe(name,probe=None,absent=None):
    target=prefix(name)
    request={'prefix':str(target),'probe':probe,'absent':absent}
    code='''import importlib, importlib.util, json, pathlib, sys
r=json.load(sys.stdin); p=pathlib.Path(r['prefix'])
assert pathlib.Path(sys.prefix).resolve()==p
assert pathlib.Path(sys.executable).resolve().is_relative_to(p)
result={'executable':sys.executable,'prefix':sys.prefix,'series':list(sys.version_info[:2])}
if r['absent']:
    assert importlib.util.find_spec(r['absent']) is None
if r['probe']:
    q=r['probe']; m=importlib.import_module(q['module'])
    assert pathlib.Path(m.__file__).resolve().is_relative_to(p)
    assert m.__version__==q['version']
    for a in q['assertions']: assert getattr(m,a['call'])(*a['args'])==a['expected']
    result['module']=m.__file__
print(json.dumps(result))
'''
    return json.loads(run([str(target/'bin/python'),'-I','-c',code],timeout=8,input=json.dumps(request)))


def roster():
    values=json.loads(conda('env','list','--json'))['envs']
    return sorted(str(Path(p).resolve()) for p in values)


def read_manifest(relative):
    path=artifact(relative)
    if not path.is_file() or path.stat().st_size>1024*1024:raise ValueError('YAML artifact missing or too large')
    from ruamel.yaml import YAML
    value=YAML(typ='safe').load(path.read_text())
    if not isinstance(value,dict):raise ValueError('Environment YAML must be a mapping')
    if value.get('channels')!=[CHANNEL]:raise ValueError('Use only the supplied offline channel')
    dependencies=value.get('dependencies')
    if not isinstance(dependencies,list) or not dependencies or not all(isinstance(x,str) for x in dependencies):
        raise ValueError('Only Conda dependencies are in scope; no pip or YAML objects')
    from conda.models.match_spec import MatchSpec
    specs=[MatchSpec(x) for x in dependencies]
    if len({x.name for x in specs})!=len(specs):raise ValueError('Duplicate dependency')
    return value,specs


def exported_requests(target):
    # Conda's YAML exporter may normalize ==1.0 to =1.0. Observe its real
    # output rather than requiring the history file's spelling in a YAML file.
    from ruamel.yaml import YAML
    value=YAML(typ='safe').load(conda('env','export','--prefix',target,'--from-history'))
    dependencies=value['dependencies']
    if not all(isinstance(x,str) for x in dependencies):raise ValueError('Unexpected requested package export')
    return dependencies


def manifest_matches(relative,source,mode,requested_export=None):
    from conda.models.match_spec import MatchSpec
    from conda.models.records import PackageRecord
    value,specs=read_manifest(relative)
    if value.get('name')!=Path(source['prefix']).name:return False
    if value.get('prefix',source['prefix'])!=source['prefix']:return False
    if mode=='intent':
        exported=requested_export if requested_export is not None else exported_requests(source['prefix'])
        canonical={s.name:s for s in map(MatchSpec,exported)}
        requested={s.name:s for s in map(MatchSpec,source['requested'].values())}
        return {s.name for s in specs}==set(requested)==set(canonical) and all(
            s in (requested[s.name],canonical[s.name]) for s in specs)
    records=source['packages']
    return {s.name for s in specs}==set(records) and all(
        s.get_exact_value('version')==records[s.name]['version'] and
        s.get_exact_value('build')==records[s.name]['build'] and
        s.match(PackageRecord(**records[s.name])) for s in specs)


def prepare(problem):
    fixture=problem['initial_fixture']
    WORK.mkdir(parents=True,exist_ok=True);os.chown(WORK,1100,1100)
    for path in (ENVROOT,Path('/home/learner/.conda'),Path('/home/learner/conda-cache')):
        path.mkdir(exist_ok=True);os.chown(path,1100,1100)
    info=json.loads(conda('info','--json'))
    if info['root_prefix']!=str(BASE) or not info['offline'] or not info['platform'].startswith('linux-'):
        raise RuntimeError('Unexpected actual Conda runtime')
    if info['channels']!=[CHANNEL+'/'+info['platform'],CHANNEL+'/noarch']:
        raise RuntimeError('Unexpected Conda channel configuration')
    if info['envs_dirs'][0]!=str(ENVROOT):raise RuntimeError('Environment root is not configured')
    if any(p!=str(BASE) for p in roster()):raise RuntimeError('Prepare requires freshly reset guest learner home')
    for entry in fixture['environments']:
        target=prefix(entry['name'])
        if target.exists():raise RuntimeError('Fixture target already exists')
        conda('create','--prefix',str(target),*entry['requested_specs'],'-y')
        python_probe(entry['name'])
    pip=pip_helper() if any('pip_distributions' in entry for entry in fixture['environments']) else None
    pip_before=pip.prepare(sys.modules[__name__],problem) if pip and pip.uses_pip(problem) else {}
    prepared_files={}
    for entry in fixture.get('files',[]):
        path=artifact(entry['path']);path.parent.mkdir(parents=True,exist_ok=True)
        if entry['kind']=='directory':path.mkdir(exist_ok=True)
        elif entry['kind']=='real_export':
            args=['env','export','--prefix',str(prefix(entry['source_env']))]
            if entry['mode']=='intent':args.append('--from-history')
            path.write_text(conda(*args));prepared_files[entry['path']]=digest(path)
        else:raise ValueError('Unknown fixture file kind')
    for path in WORK.rglob('*'):os.chown(path,1100,1100)
    names=['base',*(x['name'] for x in fixture['environments'])]
    before={name:snapshot(name,pip_names=('numpy',) if name in pip_before else ()) for name in names}
    exports={entry['arguments'][1]:exported_requests(str(prefix(entry['arguments'][1])))
             for entry in problem['grade_criteria'] if entry['operation']=='manifest_intent_before'}
    state={'problem':problem,'before':before,'roster':roster(),'files':prepared_files,
           'requested_exports':exports,'pip_before':pip_before,
           'runtime':{key:info[key] for key in ('root_prefix','conda_version','platform')}}
    STATE.write_text(json.dumps(state));STATE.chmod(0o600)
    active=fixture.get('active_env')
    Path('/opt/shellground/conda-initial-env').write_text(str(prefix(active)) if active else '')
    return {'ready':True,'runtime':state['runtime'],'start':str(WORK)}


def grade(request):
    state=json.loads(STATE.read_text());problem=state['problem']
    if request['problem_id']!=problem['id']:raise ValueError('Attempt does not match prepared problem')
    sid=str(request.get('session',''))
    if not sid.isdigit():raise ValueError('A real terminal is required')
    shell=json.loads(Path('/tmp/shellground-env-'+sid+'.json').read_text())
    answers=request.get('answers',{});fixture=problem['initial_fixture'];before=state['before'];checks=[];cache={}
    pip_before=state.get('pip_before',{})
    pip=pip_helper() if pip_before else None
    manifest=pip.asset()[1] if pip else None
    pip_cache={};tools_cache={}
    def observe(name):
        if name not in cache:cache[name]=snapshot(name,pip_names=('numpy',) if name in pip_before else ())
        return cache[name]
    def observe_numpy(name,absent=False):
        if name not in pip_before:raise ValueError('Environment is not a prepared pip exercise')
        key=(name,absent)
        if key not in pip_cache:pip_cache[key]=pip.numpy_observation(sys.modules[__name__],name,manifest,absent)
        return pip_cache[key]
    def preserved_tools(name):
        if name not in tools_cache:
            tools_cache[name]=(preserved_snapshot(observe(name),before[name]) and
                pip.preserved_tools(sys.modules[__name__],name,pip_before[name]))
        return tools_cache[name]
    def preserved_environment(name):
        if name in pip_before:
            return preserved_tools(name) and bool(observe_numpy(name,absent=not pip_before[name]['numpy_present']))
        return preserved_snapshot(observe(name),before[name],strict=name=='base')
    def check(label,operation):
        try:passed=bool(operation());detail='' if passed else '실제 환경·경로·결과를 다시 확인하세요.'
        except (OSError,ValueError,RuntimeError,KeyError,TypeError) as error:passed=False;detail=str(error)[:600]
        checks.append({'label':label,'passed':passed,'detail':detail})
    def actual_python():
        active=shell.get('CONDA_PREFIX')
        if not active:return None
        name='base' if active==str(BASE) else Path(active).name
        try:
            if str(prefix(name))!=active:return None
        except ValueError:return None
        import shutil
        path=shutil.which('python',path=shell.get('PATH',''))
        if not path or Path(path).resolve()!= (prefix(name)/'bin/python').resolve():return None
        return python_probe(name)
    def criterion(op,args):
        if op=='answer':return answer_matches(answers.get(args[0]),args[1],before)
        if op=='answer_ref':
            parts=args[1].split('.')
            if parts[0]=='runtime':value=state['runtime'];parts=parts[1:]
            elif parts[0]=='envs':
                name=parts[1]
                value=({'pip':{'numpy':observe_numpy(name)}} if parts[2:4]==['pip','numpy'] else observe(name))
                parts=parts[2:]
            elif parts[0]=='shell':value={'python':actual_python()};parts=parts[1:]
            else:raise ValueError('Unknown answer observation')
            for part in parts:value=value[part]
            return answer_matches(answers.get(args[0]),value,before)
        if op=='env_exists':return observe(args[0]) is not None and str(prefix(args[0])) in roster()
        if op=='env_absent':return args[0] in before and observe(args[0]) is None and str(prefix(args[0])) not in roster()
        if op=='active':
            expected=str(prefix(args[0])) if args[0] else None
            return (shell.get('CONDA_PREFIX') or None)==expected and (expected is not None or shell.get('CONDA_SHLVL','0')=='0')
        if op=='shell_python':return (actual_python() or {}).get('prefix')==str(prefix(args[0]))
        if op=='python':
            p=observe(args[0])['packages']['python'];return p['version'].startswith('.'.join(map(str,args[1]))+'.') and python_probe(args[0])['series']==args[1]
        if op=='distinct_prefix':return prefix(args[0])!=prefix(args[1]) and observe(args[0]) is not None and observe(args[1]) is not None
        if op=='unchanged':return preserved_environment(args[0])
        if op=='numpy_present':return observe_numpy(args[0])['version']==args[1]
        if op=='numpy_absent':return bool(observe_numpy(args[0],absent=True))
        if op=='preserved_except_numpy':return preserved_tools(args[0])
        if op=='environment_preserved':return preserved_environment(args[0])
        if op in ('package','package_present'):
            p=observe(args[0])['packages'].get(args[1]);return p is not None and (op=='package_present' or p['version']==args[2])
        if op=='package_absent':return args[1] not in observe(args[0])['packages'] and bool(python_probe(args[0],absent=args[1].replace('-','_')))
        if op=='module':
            probe=dict(request['probes'][args[1]]);meta=observe(args[0])['packages'][probe['package']]
            if probe.get('require_version') and meta['version']!=probe['require_version']:return False
            probe['version']=meta['version'];return bool(python_probe(args[0],probe=probe))
        if op.startswith('manifest_'):
            source=before[args[1]] if op.endswith('_before') else observe(args[1])
            exported=state.get('requested_exports',{}).get(args[1]) if op.endswith('_before') else None
            return manifest_matches(args[0],source,'intent' if 'intent' in op else 'snapshot',exported)
        if op=='same_packages':return observe(args[0])['packages']==observe(args[1])['packages'] and bool(python_probe(args[0])) and bool(python_probe(args[1]))
        if op=='env_satisfies_spec':
            from conda.models.records import PackageRecord
            _,specs=read_manifest(args[1]);packages=observe(args[0])['packages']
            return args[0] not in before and all(s.name in packages and s.match(PackageRecord(**packages[s.name])) for s in specs) and bool(python_probe(args[0]))
        raise ValueError('Unsupported criterion: '+op)
    for entry in problem['grade_criteria']:
        op,args=entry['operation'],entry['arguments']
        labels={
            'answer':lambda:'답 확인 · '+next(f['label'] for f in problem['answer_fields'] if f['key']==args[0]),
            'answer_ref':lambda:'실제 출력과 답 일치 · '+next(f['label'] for f in problem['answer_fields'] if f['key']==args[0]),
            'env_exists':lambda:args[0]+' 환경 생성', 'env_absent':lambda:args[0]+' 환경 제거',
            'python':lambda:args[0]+'의 실제 Python '+'.'.join(map(str,args[1])),
            'active':lambda:'현재 활성 환경: '+(args[0] or '없음'),
            'shell_python':lambda:'현재 셸에서 '+args[0]+'의 Python 실행',
            'distinct_prefix':lambda:args[0]+' / '+args[1]+'의 환경 경로 분리',
            'unchanged':lambda:args[0]+'의 기존 설치·내용 보존',
            'numpy_present':lambda:args[0]+'의 NumPy '+args[1]+' 설치·배열 계산',
            'numpy_absent':lambda:args[0]+'에서 NumPy만 제거',
            'preserved_except_numpy':lambda:args[0]+'의 Python·pip·기존 도구 보존',
            'environment_preserved':lambda:args[0]+'의 기존 환경·NumPy 보존',
            'package':lambda:args[0]+'에 '+args[1]+' '+args[2]+' 설치',
            'package_present':lambda:args[0]+'에 '+args[1]+' 설치',
            'package_absent':lambda:args[0]+'에서 '+args[1]+'만 제거',
            'module':lambda:args[0]+'의 패키지 실제 import·함수 결과',
            'manifest_intent':lambda:args[0]+'에 직접 요청한 패키지 기록',
            'manifest_intent_before':lambda:args[0]+'에 삭제 전 요청 기록 보존',
            'manifest_snapshot':lambda:args[0]+'에 전체 버전·빌드 기록',
            'manifest_snapshot_before':lambda:args[0]+'에 삭제 전 전체 설치 기록 보존',
            'same_packages':lambda:args[0]+' / '+args[1]+'의 설치 버전·빌드 일치',
            'env_satisfies_spec':lambda:args[0]+' 환경이 '+args[1]+'의 요구 충족'}
        label=entry.get('label') or (labels[op]() if op in labels else '지원되지 않는 평가: '+op)
        check(label,lambda op=op,args=args:criterion(op,args))
    mutable=set(fixture['mutable_envs']);removed=set(fixture['removed_envs'])
    created=set(fixture.get('created_envs',[]))
    expected=set(state['roster'])|{str(prefix(n)) for n in created}
    expected-={str(prefix(n)) for n in removed}
    check('지정한 환경만 생성·제거',lambda:set(roster())==expected)
    for name in before:
        if name not in mutable and name not in removed:check(name+' 원본 환경 보존',lambda name=name:preserved_environment(name))
    for relative,expected_digest in state['files'].items():check('제공된 '+relative+' 보존',lambda r=relative,d=expected_digest:digest(artifact(r))==d)
    return {'passed':all(c['passed'] for c in checks),'checks':checks}


def main():
    sys.path.insert(0,'/opt/shellground')
    from agent import require_guest
    require_guest()
    if os.getuid()!=0:raise RuntimeError('Guest grader requires owned control channel')
    request=json.load(sys.stdin)
    if sys.argv[1]=='prepare':result=prepare(request)
    elif sys.argv[1]=='grade':result=grade(request)
    else:raise ValueError('Unknown Conda lab action')
    print(json.dumps(result,ensure_ascii=False))


if __name__=='__main__':main()
