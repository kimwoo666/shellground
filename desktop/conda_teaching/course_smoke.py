"""Explicit developer test: real PTY solutions and actual guest state checks."""
import base64
import json
from pathlib import Path
import queue
import re
import shlex
import time
import hashlib
import secrets

ROOT=Path(__file__).resolve().parents[1]
from conda_teaching.engine import SHELL_INIT as RC, course, configure
from conda_teaching.validation_progress import checkpoint


def source_fingerprint():
    value=hashlib.sha256()
    for relative in ('conda_teaching/course_spec.json','conda_teaching/guest_runtime.py',
                     'conda_teaching/pip_course_spec.json','conda_teaching/pip_runtime.py',
                     'conda_teaching/pip_wheel.py','conda_teaching/pip_assets.py','conda_teaching/engine.py',
                     'conda_teaching/pip_acceptance.py',
                     'conda_teaching/verify_runtime.py',
                     'conda_teaching/channel.py','conda_teaching/provision.py',
                     'conda_teaching/logged_command.py',
                     'conda_teaching/installer_sources.py',
                     'conda_teaching/setup_runtime.py',
                     'conda_teaching/validation_progress.py',
                     'conda_teaching/learning_smoke.py',
                     'conda_teaching/runtime_smoke.sh','conda_teaching/course_smoke.py',
                     'guest/agent.py','guest/conda_lab.py','guest/shell_snapshot.py','guest/bashrc'):
        value.update(relative.encode());value.update((ROOT/relative).read_bytes())
    value.update(RC.encode())
    return value.hexdigest()


def exec_guest(channel,argv,data=None):
    result=channel.request('exec',timeout=125,root=True,run_timeout=120,cwd='/tmp',argv=argv,
                           input=base64.b64encode(data or b'').decode())
    if result['code']:raise RuntimeError(base64.b64decode(result['err']).decode(errors='replace'))
    return base64.b64decode(result['out']).decode()


def install_grader(channel):
    from types import SimpleNamespace
    configure(SimpleNamespace(channel=channel),pip=True)


def drain_until(terminal,needle,timeout=100):
    deadline=time.monotonic()+timeout;out=b''
    while time.monotonic()<deadline:
        try:item=terminal.queue.get(timeout=.2)
        except queue.Empty:continue
        if item is None:raise RuntimeError('Real Bash exited')
        out+=base64.b64decode(json.loads(item)['output'])
        clean=re.sub(rb'\x1b\[[0-?]*[ -/]*[@-~]',b'',out)
        if needle.search(clean) if hasattr(needle,'search') else needle in clean:return clean
    raise TimeoutError(out.decode(errors='replace')[-2000:])


def send(channel,terminal,text):
    channel.send({'action':'input','session':terminal.sid,'data':base64.b64encode(text.encode()).decode()})


def execute_reference(channel,terminal,commands,actions=None):
    if actions is not None:
        if [a['command'] for a in actions]!=commands:raise ValueError('Reference actions do not match commands')
        execute_reference(channel,terminal,[])
        for action in actions:
            if action['exit_codes']!=[0] and not action.get('expectation_reason'):
                raise ValueError('Expected failure needs an explicit observation reason')
            marker='__SG_ACTION_'+secrets.token_hex(8)
            completed=re.compile(rb'(?:^|\n)'+marker.encode()+rb'_(\d+)__\r?\n')
            command='eval '+shlex.quote(action['command'])+"; printf '\\n"+marker+"_%s__\\n' \"$?\"\r"
            send(channel,terminal,command)
            for response in action.get('responses',[]):
                expected=response['prompt'].encode()
                out=drain_until(terminal,re.compile(re.escape(expected)+b'|'+completed.pattern))
                if expected not in out or completed.search(out):
                    raise RuntimeError('Command finished without its expected real question: '+out.decode(errors='replace')[-1500:])
                send(channel,terminal,response['reply']+'\r')
            out=drain_until(terminal,completed)
            code=int(completed.search(out).group(1))
            if code not in action['exit_codes']:
                raise RuntimeError('Unexpected exit '+str(code)+' for '+action['command']+'\n'+out.decode(errors='replace')[-1800:])
            if not out.rstrip().endswith(b'$'):drain_until(terminal,b'$ ',timeout=15)
        return
    script='export CONDA_ALWAYS_YES=true\n'+' &&\n'.join(commands)
    command='eval '+shlex.quote(script)+"; printf '\\n__SG_REFERENCE_%s__\\n' \"$?\"\r"
    send(channel,terminal,command)
    completed=re.compile(rb'(?:^|\n)__SG_REFERENCE_(\d+)__\r?\n')
    out=drain_until(terminal,completed,timeout=100)
    if completed.search(out).group(1)!=b'0':
        raise RuntimeError('Actual reference command failed:\n'+out.decode(errors='replace')[-2000:])
    if not out.rstrip().endswith(b'$'):drain_until(terminal,b'$ ',timeout=15)


def wrong_then_repair(channel,terminal,mission,answers):
    key=mission['problem']['id'];pairs=[]
    if key=='conda_install_example':
        # Replace the learner's directory entry like an atomic-save editor.
        # Writing through Conda's default hardlink would also damage the
        # extracted package cache and make --force-reinstall reuse bad bytes.
        pairs=[(['python -c "import training_math,pathlib; p=pathlib.Path(training_math.__file__); t=p.with_suffix(\'.damaged\'); t.write_text(\'__version__=\\\"1.1\\\"\\ndef total(values): return 7\\n\'); t.replace(p)"'],
                ['conda install -n sg-sum training-math --force-reinstall -y'])]
    elif key=='conda_export_intent_example':
        pairs=[(['conda env export -n sg-share --file share/environment.yml'],mission['problem']['reference_commands'])]
    elif key=='conda_activate_example':
        pairs=[(['conda deactivate'],mission['problem']['reference_commands'])]
    elif key=='conda_update_preserve':
        pairs=[(['conda install -n sg-stable training-math==1.1 --offline -y'],
                ['conda install -n sg-stable training-math==1.0 --offline -y'])]
    for wrong,repair in pairs:
        execute_reference(channel,terminal,wrong)
        bad=channel.request('grade',timeout=125,mission=mission,session=terminal.sid,answers=answers)
        if bad['passed']:raise AssertionError('Incorrect state accepted: '+key)
        execute_reference(channel,terminal,repair)
        fixed=channel.request('grade',timeout=125,mission=mission,session=terminal.sid,answers=answers)
        if not fixed['passed']:raise AssertionError('Same-session repair rejected: '+key+' '+json.dumps(fixed,ensure_ascii=False))
    return len(pairs)


def reference_answers(channel,problem,ready,terminal):
    values={}
    for field in problem['answer_fields']:
        if 'expected' in field:values[field['key']]=field['expected'];continue
        parts=field['expected_ref'].split('.')
        if parts[0]=='runtime':value=ready['runtime'][parts[1]]
        elif parts[0]=='envs':
            prefix='/home/learner/conda-envs/'+parts[1]
            if parts[2]=='prefix':value=prefix
            elif parts[2:4]==['pip','numpy']:
                code="import importlib.metadata as m;d=m.distribution('numpy');print(d.version if __import__('sys').argv[1]=='version' else str(d.locate_file('')))"
                value=exec_guest(channel,['runuser','-u','learner','--',prefix+'/bin/python','-I','-c',code,parts[4]]).strip()
            else:
                code="import glob,json,sys;print(json.load(open(glob.glob(sys.argv[1]+'/conda-meta/'+sys.argv[2]+'-*.json')[0]))['version'])"
                value=exec_guest(channel,['/usr/bin/python3','-c',code,prefix,parts[3]]).strip()
        elif field['expected_ref']=='shell.python.executable':
            code="import json;print(json.load(open('/tmp/shellground-env-"+terminal.sid+".json'))['CONDA_PREFIX']+'/bin/python')"
            value=exec_guest(channel,['/usr/bin/python3','-c',code]).strip()
        else:raise ValueError('Unknown test answer observation')
        values[field['key']]=value
    return values


def answer_variants(channel,terminal,mission,answers):
    """Prove accepted equivalent answers and reject stale or wrong facts."""
    key=mission['problem']['id'];passed=[]
    def expect(values,expected,label):
        result=channel.request('grade',timeout=125,mission=mission,session=terminal.sid,answers=values)
        if result['passed'] is not expected:
            raise AssertionError('Answer variant '+label+': '+json.dumps(result,ensure_ascii=False))
        passed.append(label)
    if key=='conda_identity_example':
        execute_reference(channel,terminal,['conda activate base'])
        expect(answers,True,'runtime_answer_with_base_active')
        execute_reference(channel,terminal,['conda deactivate'])
    elif key=='conda_identity_root':
        equivalent=dict(answers,base_path=answers['base_path']+'/./',tool='conda')
        expect(equivalent,True,'normalized_root_path')
        expect(dict(answers,base_path='/tmp/miniconda'),False,'unrelated_root_path_rejected')
    elif key=='conda_env_list_example':
        expect(dict(answers,notes_path=answers['notes_path']+'/'),True,'normalized_environment_path')
        execute_reference(channel,terminal,['conda activate sg-notes'])
        expect(answers,False,'stale_inactive_answer_rejected')
        execute_reference(channel,terminal,['conda deactivate'])
        expect(answers,True,'inactive_state_repaired')
    elif key=='conda_env_list_active':
        equivalent={name:'/home/learner/conda-envs/'+value+'/' for name,value in answers.items()}
        expect(equivalent,True,'environment_name_or_full_path')
        expect(dict(equivalent,active='/tmp/sg-draft'),False,'same_basename_wrong_path_rejected')
        execute_reference(channel,terminal,['conda activate sg-publish'])
        expect(answers,False,'stale_active_answer_rejected')
        execute_reference(channel,terminal,['conda activate sg-draft'])
        expect(answers,True,'active_state_repaired')
    elif key=='conda_env_list_missing':
        expect(dict(answers,share_exists=True),False,'absent_environment_wrong_answer_rejected')
        expect(dict(answers,share_exists=0),False,'boolean_type_preserved')
    elif key=='conda_export_intent_example':
        execute_reference(channel,terminal,['conda export -n sg-share --from-history --format=environment-yaml --file share/environment.yml'])
        expect(answers,True,'explicit_target_new_exporter')
    return passed


def check_course(channel,unit_filter=None,report_path=None):
    install_grader(channel)
    spec=course();count=0
    started=time.monotonic();fingerprint=source_fingerprint();passed=[];negatives=[];answer_cases=[]
    report=Path(report_path) if report_path is not None else ROOT/'.conda-build/course-validation.json'
    architecture=exec_guest(channel,['uname','-m']).strip()
    current=None;phase='start'
    def save(state='in_progress',**extra):
        if fingerprint!=source_fingerprint():
            raise RuntimeError('Course or grader changed during validation; rerun before exporting')
        return checkpoint(report,{'fingerprint':fingerprint},
            {'passed':passed,'negative_repair':negatives,'answer_cases':answer_cases},state=state,
            execution='actual guest Bash/Conda/Python',guest_architecture=architecture,
            current_problem=current,phase=phase,**extra)
    save()
    try:
        for unit in spec['units']:
            if unit_filter and unit['key'] not in unit_filter:continue
            for problem in unit['problems']:
                current=problem['id'];phase='prepare';save(invalidate=[current])
                print('REAL_CONDA_START '+current,flush=True)
                mission={'kind':'conda','problem':problem,'probes':spec['observer_contract']['module_probes']}
                ready=channel.request('prepare',timeout=125,mission=mission)
                terminal=channel.open_terminal(ready['start'])
                drain_until(terminal,b'$ ')
                phase='initial_grade'
                initial=channel.request('grade',timeout=125,mission=mission,session=terminal.sid,answers={})
                if initial['passed']:raise AssertionError('Already solved at start: '+problem['id'])
                # Always-yes belongs only to this automated verification attempt;
                # the learner sees real Conda transaction confirmation prompts.
                phase='reference'
                execute_reference(channel,terminal,problem['reference_commands'],problem.get('reference_actions'))
                answers=reference_answers(channel,problem,ready,terminal)
                phase='final_grade'
                result=channel.request('grade',timeout=125,mission=mission,session=terminal.sid,answers=answers)
                if not result['passed']:raise AssertionError(json.dumps({'problem':problem['id'],'grade':result},ensure_ascii=False))
                phase='negative_and_equivalent'
                if wrong_then_repair(channel,terminal,mission,answers):
                    negatives.append(problem['id']);print('REAL_CONDA_REPAIR_PASS '+problem['id'],flush=True)
                variants=answer_variants(channel,terminal,mission,answers);answer_cases.extend(variants)
                if variants:print('REAL_CONDA_ANSWER_VARIANTS_PASS '+problem['id']+' '+str(len(variants)),flush=True)
                from conda_teaching.pip_acceptance import check_variants
                answer_cases.extend(check_variants(channel,terminal,mission,answers))
                count+=1;passed.append(problem['id']);save()
                print('REAL_CONDA_PASS '+problem['id'],flush=True)
        # Export is allowed only after the last learner's scratch files are reset.
        phase='clean_fixture'
        channel.request('prepare',timeout=125,mission={'kind':'conda','problem':spec['units'][0]['problems'][0],
            'probes':spec['observer_contract']['module_probes']})
        save('complete')
    except BaseException as error:
        if fingerprint==source_fingerprint():save('failed',error=str(error)[-2000:])
        raise
    print(json.dumps({'real_conda_problems':count,'seconds':round(time.monotonic()-started,2)},ensure_ascii=False),flush=True)
