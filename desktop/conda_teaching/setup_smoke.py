"""Explicit acceptance: install the pinned Miniconda in actual guest Bash."""
import hashlib
import json
from pathlib import Path
import shlex
import time
from conda_teaching.engine import CondaEngine
from conda_teaching.course_smoke import drain_until, execute_reference

ROOT=Path(__file__).resolve().parents[1]
CASES={'absent_target','empty_directory','base_symlink','actual_new_install',
       'same_terminal_retry','shell_profile_change','shell_profile_repair','new_attempt_no_overwrite',
       'changed_launcher','launcher_repair','changed_python','python_repair'}


def inspect_setup(channel):
    from conda_teaching.course_smoke import exec_guest
    code='''import sys,json
sys.path.insert(0,'/opt/shellground')
import conda_setup as s
state=json.loads(s.STATE.read_text());target=s.Path(state['prefix'])
result={'target':str(target),'grade':s.grade(str(target)),
 'python_hash_equal':s.digest(target/'bin/python')==s.digest(s.BASE/'bin/python'),
 'launcher_new':(target/'bin/conda').read_text(), 'launcher_base':(s.BASE/'bin/conda').read_text(),
 'changed_sources':[name for name,checksum in state['conda_sources'].items()
     if not s.contained_file(target/name,target) or s.digest(target/name)!=checksum]}
print(json.dumps(result,ensure_ascii=False,indent=2))
'''
    from conda_teaching.engine import configure
    engine=CondaEngine();engine.channel=channel;configure(engine,setup=True)
    print(exec_guest(channel,['/opt/shellground/miniconda/bin/python','-I','-c',code]),flush=True)


def setup_fingerprint():
    value=hashlib.sha256()
    for relative in ('conda_teaching/setup_runtime.py','conda_teaching/setup_course.py',
                     'conda_teaching/setup_smoke.py','conda_teaching/installer_sources.py',
                     'conda_teaching/provision.py','conda_teaching/engine.py'):
        value.update(relative.encode());value.update((ROOT/relative).read_bytes())
    return value.hexdigest()


def check_setup(channel,report_path=None):
    started=time.monotonic();engine=CondaEngine();engine.channel=channel
    bridge=engine.start_setup();sid=bridge.sid;ready=engine.ready
    target=shlex.quote(ready['prefix']);passed=[]
    def expect(case,expected):
        result=engine.grade_setup()
        if result['passed'] is not expected:raise AssertionError((case,result))
        passed.append(case);print('SETUP '+case+' OK',flush=True)
    try:
        drain_until(bridge,b'$ ',timeout=20)
        expect('absent_target',False)
        execute_reference(channel,bridge,['mkdir '+target])
        expect('empty_directory',False)
        # This directory was just made empty by this test, not learner data.
        execute_reference(channel,bridge,['rmdir '+target,'ln -s /opt/shellground/miniconda '+target])
        expect('base_symlink',False)
        execute_reference(channel,bridge,['unlink '+target])
        command='bash '+shlex.quote(ready['installer']['path'])+' -b -p '+target
        # The acceptance harness observes this subprocess's actual zero exit.
        # The learner's grader makes no historical exit/command-history claim.
        execute_reference(channel,bridge,[command])
        expect('actual_new_install',True)
        if bridge.sid!=sid:raise AssertionError('Retry replaced the real terminal')
        passed.append('same_terminal_retry')
        # Tamper only with the installation this test just created, then
        # restore it. The protected manager and learner data are untouched.
        execute_reference(channel,bridge,[f'cp {target}/bin/conda {target}/conda-proof',
            f"printf '#!/bin/sh\\necho fake\\n' > {target}/bin/conda"])
        expect('changed_launcher',False)
        execute_reference(channel,bridge,[f'cp {target}/conda-proof {target}/bin/conda',f'unlink {target}/conda-proof'])
        expect('launcher_repair',True)
        execute_reference(channel,bridge,[f'cp -L {target}/bin/python {target}/python-proof',
            f"printf x >> {target}/bin/python"])
        expect('changed_python',False)
        execute_reference(channel,bridge,[f'cp {target}/python-proof {target}/bin/python',f'unlink {target}/python-proof'])
        expect('python_repair',True)
        execute_reference(channel,bridge,['test ! -e /home/learner/.condarc',"printf '# setup test\\n' > /home/learner/.condarc"])
        expect('shell_profile_change',False)
        execute_reference(channel,bridge,['unlink /home/learner/.condarc'])
        expect('shell_profile_repair',True)
    finally:bridge.close()
    second=engine.start_setup()
    try:
        if engine.ready['prefix']==ready['prefix']:raise AssertionError('Restart reused old install')
        drain_until(second,b'$ ',timeout=20)
        execute_reference(channel,second,['test -x '+shlex.quote(ready['prefix']+'/bin/conda'),
            'test ! -e '+shlex.quote(engine.ready['prefix'])])
        if engine.grade_setup()['passed']:raise AssertionError('New attempt must not inherit old pass')
        passed.append('new_attempt_no_overwrite')
    finally:second.close()
    report=dict(fingerprint=setup_fingerprint(),passed=passed,count=len(passed),
                installer_sha256=ready['installer']['sha256'],platform=ready['runtime']['platform'],
                actual_installer_exit=0,seconds=round(time.monotonic()-started,2))
    destination=Path(report_path) if report_path is not None else ROOT/'.conda-build/setup-validation.json'
    destination.write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report),flush=True)


def validate_setup(report):
    if report.get('fingerprint')!=setup_fingerprint() or set(report.get('passed',[]))!=CASES or report.get('count')!=len(CASES) or report.get('actual_installer_exit')!=0:
        raise RuntimeError('Current real installation setup validation is required before export')
