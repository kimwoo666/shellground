"""Actual Linux/Jupyter acceptance in one owned, disposable VM."""
import argparse
import base64
import json
from pathlib import Path
import threading
import time
from .engine import NotebookEngine


def check(engine):
    passed = []
    def record(name):
        passed.append(name); print('REAL_JUPYTER_PASS ' + name, flush=True)
    engine.start_notebook(lambda value: print(value, flush=True))
    kernels = engine.perform('list')['kernels']
    assert {entry['name'] for entry in kernels} == {'sg-basic', 'sg-data'}, kernels
    basic = engine.perform('select', name='sg-basic')
    assert basic['values']['prefix'] == '/home/learner/notebook-envs/basic' and not basic['values']['numpy'], basic
    record('actual_basic_kernel_identity')
    result = engine.perform('execute', cell_id='first', code='price = 3\ncount = 4\ntotal = price * count\ntotal')
    assert result['ok'] and result['execution_count'] == 1, result
    assert any(m['type'] == 'execute_result' and m['content']['data']['text/plain'] == '12' for m in result['messages']), result
    record('actual_cell_result_and_execution_count')
    result = engine.perform('execute', cell_id='missing', code='not_defined + 1')
    assert not result['ok'] and result['reply']['ename'] == 'NameError', result
    engine.perform('execute', cell_id='define', code='not_defined = 8')
    result = engine.perform('execute', cell_id='missing', code='not_defined + 1')
    assert result['ok'] and result['generation'] == basic['generation'], result
    record('same_kernel_error_repair')
    data = engine.perform('select', name='sg-data')
    assert data['values']['numpy'] and data['values']['pid'] != basic['values']['pid'], data
    assert data['values']['executable'] == '/home/learner/notebook-envs/data/bin/python', data
    snapshot = engine.perform('snapshot', expressions=dict(total='total'))
    assert snapshot['errors']['total']['ename'] == 'NameError', snapshot
    record('kernel_selection_changes_real_environment_and_state')
    result = engine.perform('execute', cell_id='array', code='import numpy as np\na = np.array([3, 5])\ntotal = int(a.sum())\ntotal')
    assert result['ok'], result
    snapshot = engine.perform('snapshot', expressions=dict(total='total', version='np.__version__'))
    assert snapshot['values'] == {'total': 8, 'version': '2.3.5'}, snapshot
    record('numpy_import_in_selected_environment')
    restarted = engine.perform('restart')
    assert restarted['values']['pid'] != data['values']['pid'] and restarted['generation'] != data['generation'], restarted
    assert engine.perform('snapshot', expressions=dict(total='total'))['errors']['total']['ename'] == 'NameError'
    result = engine.perform('execute', cell_id='array', code='import numpy as np\na = np.array([3, 5])\ntotal = int(a.sum())\ntotal')
    assert result['ok'] and result['execution_count'] == 1, result
    record('real_restart_and_clean_reexecution')
    result = engine.perform('execute', cell_id='pip', code='%pip --version')
    text = ''.join(m['content'].get('text', '') for m in result['messages'])
    assert result['ok'] and '/home/learner/notebook-envs/data/' in text, result
    record('ipython_pip_magic_uses_selected_interpreter')
    response = []
    def long_cell():
        try: response.append(engine.perform('execute', cell_id='long', code='import time\ntime.sleep(30)'))
        except Exception as error: response.append(error)
    thread = threading.Thread(target=long_cell)
    thread.start(); time.sleep(1.5)
    engine.interrupt(); thread.join(8)
    assert not thread.is_alive() and response and isinstance(response[0], dict), response
    assert not response[0]['ok'] and response[0]['reply']['ename'] == 'KeyboardInterrupt', response
    assert engine.perform('execute', cell_id='continue', code='total + 1')['ok']
    record('interrupt_and_continue_same_kernel')
    document = [dict(id='intro', type='markdown', source='# 관측 보고서\n코드와 설명은 다릅니다.'),
                dict(id='array', type='code', source='import numpy as np\na = np.array([3, 5])\ntotal = int(a.sum())\ntotal')]
    saved = engine.perform('save', filename='practice.ipynb', cells=document)
    assert saved['cells'] == 2 and saved['code_cells'] == 1, saved
    result = engine.channel.request('exec', root=False, cwd='/home/learner/notebook-work',
        argv=['/home/learner/notebook-envs/data/bin/python', '-c',
              'import nbformat; n=nbformat.read("practice.ipynb",as_version=4); nbformat.validate(n); assert n.cells[0].cell_type=="markdown"; assert n.cells[1].outputs[0].data["text/plain"]=="8"; assert n.metadata.kernelspec.name=="sg-data"; print("VALID_NOTEBOOK")'])
    assert result['code'] == 0, base64.b64decode(result['err'])
    record('actual_nbformat_save_with_kernel_outputs')
    result = engine.channel.request('exec', root=False, cwd='/home/learner/notebook-work',
        argv=['/home/learner/notebook-envs/data/bin/python', '-m', 'ipykernel', 'install',
              '--prefix', '/home/learner/notebook-jupyter', '--name', 'sg-analysis-review', '--display-name', '분석 환경'])
    assert result['code'] == 0, base64.b64decode(result['err'])
    assert 'sg-analysis-review' in {entry['name'] for entry in engine.perform('list')['kernels']}
    assert engine.perform('select', name='sg-analysis-review')['values']['prefix'].endswith('/data')
    record('actual_kernelspec_registration_and_refresh')
    return passed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True)
    parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args()
    engine = NotebookEngine(args.runtime); report = dict(state='in_progress'); started = time.monotonic()
    try:
        report['passed'] = check(engine)
        report['state'] = 'complete'
    except BaseException as error:
        report.update(state='failed', error=str(error)[-4000:]); raise
    finally:
        process, session = engine.process, engine.session_dir
        engine.close()
        report.update(seconds=round(time.monotonic() - started, 2),
                      vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=session is None or not session.exists())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + '\n')
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    main()
