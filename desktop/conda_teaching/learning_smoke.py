"""Replay authored microsteps in real persistent Bash, then grade the result."""
import hashlib
import json
from pathlib import Path
import time
from conda_teaching.course_smoke import (ROOT,install_grader,drain_until,
    execute_reference,reference_answers,source_fingerprint)
from conda_teaching.learning_steps import STEPS
from conda_teaching.validation_progress import checkpoint
from conda_teaching.engine import course


def learning_fingerprint():
    return hashlib.sha256(Path(__file__).with_name('learning_steps.py').read_bytes()+
                          Path(__file__).with_name('pip_course_spec.json').read_bytes()).hexdigest()


def check_learning(channel,unit_filter=None,report_path=None):
    install_grader(channel)
    spec=course()
    fingerprint=learning_fingerprint();course_hash=source_fingerprint();passed=[]
    report=Path(report_path) if report_path is not None else ROOT/'.conda-build/learning-validation.json'
    current=None;phase='start'
    def save(state='in_progress',**extra):
        if (fingerprint,course_hash)!=(learning_fingerprint(),source_fingerprint()):
            raise RuntimeError('Learning steps or course changed during validation')
        return checkpoint(report,{'fingerprint':fingerprint,'course_fingerprint':course_hash},
            {'passed':passed},state=state,current_unit=current,phase=phase,**extra)
    save()
    try:
        for unit in spec['units']:
            if unit_filter and unit['key'] not in unit_filter:continue
            current=unit['key'];phase='prepare';save(invalidate=[current])
            print('REAL_CONDA_LEARNING_START '+current,flush=True)
            problem=unit['problems'][0]
            mission={'kind':'conda','problem':problem,'probes':spec['observer_contract']['module_probes']}
            ready=channel.request('prepare',timeout=125,mission=mission)
            terminal=channel.open_terminal(ready['start']);drain_until(terminal,b'$ ')
            for index,part in enumerate(unit.get('learning_steps') or STEPS[unit['key']]):
                phase='step_'+str(index+1)
                if part['commands']:execute_reference(channel,terminal,part['commands'],part.get('actions'))
            answers=reference_answers(channel,problem,ready,terminal)
            phase='grade'
            grade=channel.request('grade',timeout=125,mission=mission,session=terminal.sid,answers=answers)
            if not grade['passed']:raise AssertionError(json.dumps({'unit':unit['key'],'grade':grade},ensure_ascii=False))
            passed.append(unit['key']);save()
            print('REAL_CONDA_LEARNING_PASS '+unit['key'],flush=True)
        phase='clean_fixture'
        channel.request('prepare',timeout=125,mission={'kind':'conda','problem':spec['units'][0]['problems'][0],
            'probes':spec['observer_contract']['module_probes']})
        result=save('complete')
    except BaseException as error:
        if (fingerprint,course_hash)==(learning_fingerprint(),source_fingerprint()):
            save('failed',error=str(error)[-2000:])
        raise
    print('Actual Conda learning sequences verified: '+str(result['count']),flush=True)
