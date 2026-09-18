"""All authored notebook variants against actual kernels and real packages."""
import argparse
import base64
from copy import deepcopy
import json
from pathlib import Path
import time
from .course import lessons
from .engine import NotebookEngine
from .proof import fingerprint


def command(engine, source):
    result=engine.channel.request('exec',root=False,cwd='/home/learner/notebook-work',
        argv=['/bin/bash','-c',source],timeout=35,run_timeout=30)
    assert result['code']==0,base64.b64decode(result['err']).decode()
    return base64.b64decode(result['out']).decode()+base64.b64decode(result['err']).decode()


def solve(engine, problem):
    for source in problem.get('commands',[]): command(engine,source)
    engine.perform('select',name=problem.get('registration','sg-'+problem['target']))
    if problem.get('restart'): engine.perform('restart')
    document=deepcopy(problem['solution'])
    for cell in document:
        if cell['type']=='code':
            result=engine.perform('execute',cell_id=cell['id'],code=cell['source'])
            assert result['ok'],result
    if problem.get('save'): engine.perform('save',filename=problem['save'],cells=document)
    return document


def check(engine, report, checkpoint=lambda: None):
    for unit in lessons():
        for index,problem in enumerate(unit['problems']):
            label=unit['key']+':'+str(index)
            engine.start_problem(problem)
            before=engine.grade_problem(problem,problem['cells'])
            assert not before['passed'],('unsolved fixture passed',label,before)
            document=solve(engine,problem)
            generation=engine.perform('identity')['generation']
            result=engine.grade_problem(problem,document)
            assert result['passed'],(label,result)
            assert engine.perform('identity')['generation']==generation,'grading reset learner kernel'
            if problem.get('replay'):
                stale=deepcopy(document)
                next(c for c in reversed(stale) if c['type']=='code')['source']='raise ValueError("not reproducible")'
                assert not engine.grade_problem(problem,stale)['passed'],'stale outputs accepted'
                assert engine.perform('identity')['generation']==generation
                assert engine.grade_problem(problem,document)['passed'],'same-kernel repair failed'
            if unit['key']=='jupyter_order' and index==1:
                unordered=deepcopy(document);unordered[1:]=reversed(unordered[1:])
                assert not engine.grade_problem(problem,unordered)['passed'],'hidden namespace dependency accepted'
            if unit['key']=='jupyter_order' and index==2:
                duplicate=deepcopy(document)
                duplicate[-1]['source']='items.append(7)\nresult=items\ntotal=sum(result)'
                assert not engine.grade_problem(problem,duplicate)['passed'],'repeated append accepted'
                trailing=deepcopy(document)
                trailing[1]['source']='items=[2,5]\nresult=items.copy()'
                trailing[2]['source']='result.append(7)\ntotal=sum(result)'
                trailing.append(dict(id='diagnostic',type='code',source='print(total)'))
                assert not engine.grade_problem(problem,trailing)['passed'],'trailing output masked repeated mutation'
                equivalent=deepcopy(document)
                equivalent.append(dict(id='diagnostic',type='code',source='print(total)'))
                assert engine.grade_problem(problem,equivalent)['passed'],'harmless trailing output rejected'
                report.setdefault('negative',[]).append('repeat_mutation_with_trailing_output_rejected')
            if unit['key']=='jupyter_order':
                engine.perform('select',name='sg-data')
                for cell in document:
                    if cell['type']=='code':
                        assert engine.perform('execute',cell_id=cell['id'],code=cell['source'])['ok']
                assert engine.grade_problem(problem,document)['passed'],'equivalent data kernel rejected'
                if index==2:report.setdefault('negative',[]).append('order_in_both_environments_accepted')
            if unit['key']=='jupyter_select' and index==0:
                engine.perform('execute',cell_id='cell2',code='import numpy as np\ntotal=np.sum([2,5])')
                assert engine.grade_problem(problem,document)['passed'],'NumPy scalar equivalent rejected'
                assert any(p[0]=='packaging' for p in engine.lesson_baseline['installed']['data'])
                removed=command(engine,'/home/learner/notebook-envs/data/bin/python -m pip uninstall -y packaging')
                assert 'Successfully uninstalled packaging-' in removed,removed
                after_remove=engine.grade_problem(problem,document)
                assert not after_remove['passed'],('removed package accepted',removed,engine.lesson_baseline,after_remove)
                command(engine,'/home/learner/notebook-envs/data/bin/python -m pip install --no-index --find-links /opt/shellground/notebook-assets packaging')
                assert engine.grade_problem(problem,document)['passed'],'package repair failed'
                report.setdefault('negative',[]).extend(['numpy_scalar_equivalent','package_removal_and_repair'])
            if unit['key']=='jupyter_restart' and index==2:
                direct=deepcopy(document);direct[-1]['source']="from pathlib import Path\nresult=len(Path('source.txt').read_text())"
                engine.perform('restart')
                engine.perform('execute',cell_id=direct[-1]['id'],code=direct[-1]['source'])
                engine.perform('save',filename=problem['save'],cells=direct)
                assert engine.grade_problem(problem,direct)['passed'],'unrequested text variable required'
                edited=deepcopy(direct);edited[-1]['source']='result=999'
                engine.perform('save',filename='stale.ipynb',cells=edited)
                command(engine,"/home/learner/notebook-envs/basic/bin/python -c \"import nbformat; n=nbformat.read('stale.ipynb',as_version=4); assert not n.cells[-1].outputs\"")
                engine.perform('restart');engine.perform('save',filename='stale.ipynb',cells=direct)
                command(engine,"/home/learner/notebook-envs/basic/bin/python -c \"import nbformat; n=nbformat.read('stale.ipynb',as_version=4); assert not n.cells[-1].outputs\"")
                report.setdefault('negative',[]).extend(['direct_file_read_equivalent','edited_and_old_kernel_outputs_not_saved'])
            if unit['key']=='review_jupyter_01' and index==0:
                engine.start_problem(problem);engine.perform('restart')  # wrong environment (basic)
                for source in problem.get('commands',[]):command(engine,source)
                engine.perform('select',name=problem['registration'])
                for cell in document:
                    if cell['type']=='code':engine.perform('execute',cell_id=cell['id'],code=cell['source'])
                engine.perform('save',filename=problem['save'],cells=document)
                assert not engine.grade_problem(problem,document)['passed'],'wrong environment restart accepted'
                first_generation=engine.perform('identity')['generation']
                engine.perform('select',name='sg-basic')
                engine.perform('select',name=problem['registration'])
                assert engine.perform('identity')['generation']!=first_generation
                for cell in document:
                    if cell['type']=='code':engine.perform('execute',cell_id=cell['id'],code=cell['source'])
                engine.perform('save',filename=problem['save'],cells=document)
                assert engine.grade_problem(problem,document)['passed'],'real target process recreation rejected'
                report.setdefault('negative',[]).append('target_kernel_recreation_equivalent')
                document=solve(engine,problem)
                assert engine.grade_problem(problem,document)['passed'],'target restart repair failed'
                report.setdefault('negative',[]).append('restart_in_wrong_environment_rejected')
            report['passed'].append(label);checkpoint()
            print('NOTEBOOK_COURSE_PASS '+label,flush=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime',type=Path,required=True)
    parser.add_argument('--report',type=Path,required=True)
    args=parser.parse_args();engine=NotebookEngine(args.runtime)
    report=dict(state='in_progress',passed=[],fingerprint=fingerprint());started=time.monotonic()
    def checkpoint():
        args.report.parent.mkdir(parents=True,exist_ok=True)
        temporary=args.report.with_suffix('.tmp')
        temporary.write_text(json.dumps(report,indent=2)+'\n');temporary.replace(args.report)
    try:
        check(engine,report,checkpoint);report['state']='complete'
    except BaseException as error:
        report.update(state='failed',error=str(error)[-6000:]);raise
    finally:
        process,session=engine.process,engine.session_dir
        engine.close()
        report.update(seconds=round(time.monotonic()-started,2),
            vm_stopped=process is None or process.poll() is not None,
            overlay_removed=session is None or not session.exists())
        checkpoint();print(json.dumps(report),flush=True)


if __name__=='__main__': main()
