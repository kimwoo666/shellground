"""New binary integrity/import/worker checks; not another execution of the course."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
import time

RESOURCES = ('lab/lab.py', 'guest/bashrc', 'guest/shell_snapshot.py', 'guest/ros_lab.py', 'guest/ros_observer.py', 'guest/ros_controls_lab.py',
             'guest/apt_lab.py', 'guest/auth_lab.py', 'guest/shell_lab.py', 'guest/process_lab.py', 'guest/io_lab.py',
             'guest/system_lab.py', 'guest/docker_lab.py', 'guest/docker_sessions_lab.py', 'guest/docker_runtime_lab.py',
             'conda_teaching/course_spec.json', 'conda_teaching/pip_course_spec.json',
             'python_teaching/linux_docker_concept_draft.json', 'python_teaching/shell_concept_draft.json',
             'python_teaching/process_concept_draft.json', 'python_teaching/io_concept_draft.json',
             'python_teaching/system_info_concept_draft.json')


def catalog():
    from mode_curriculum import curriculum
    from system_concepts import load_catalog
    from python_teaching.course import lessons
    units, reviews = curriculum('real')
    return dict(units=[u.key for u in units], reviews=[r.key for r in reviews],
                python=[u.key for u in lessons()], concepts=[q['id'] for topic in ('linux', 'docker') for q in load_catalog(topic)])


def manifest(root):
    return dict(schema=1, resources={name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in RESOURCES}, catalog=catalog())


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    if not getattr(sys, 'frozen', False): raise RuntimeError('This check requires the new executable, not development Python')
    if args.report.exists(): raise FileExistsError('Preserve previous binary evidence')
    from engine import resource_path
    from python_teaching.engine import PythonEngine
    expected = json.loads(resource_path('release-bundle-manifest.json').read_text())
    started = time.monotonic(); report = dict(scope='new-binary-integrity-worker-only', frozen=True, state='in_progress', full_course_rerun=False)
    engine = PythonEngine(timeout=30); process = workspace = None
    try:
        if expected != manifest(Path(sys._MEIPASS)): raise AssertionError('Bundled resources/catalog differ from build manifest')
        for name in RESOURCES:
            if name.endswith('.py'): compile(resource_path(name).read_bytes(), name, 'exec')
        engine.start(); process = engine.process; workspace = Path(engine.workspace.name)
        code = '''import sys
from pathlib import Path
import numpy as np, pandas as pd, matplotlib, seaborn, sklearn
assert sys.frozen
assert sys._MEIPASS == __BUNDLE__
for module in (np, pd, matplotlib, seaborn, sklearn):
    assert Path(module.__file__).resolve().is_relative_to(Path(sys._MEIPASS))
assert np.arange(4).sum() == 6
assert pd.Series([1, 3]).mean() == 2
import matplotlib.pyplot as plt
fig, ax = plt.subplots()
ax.plot([0, 1], [1, 2])
fig.savefig('bundle-chart.png')
assert Path('bundle-chart.png').stat().st_size > 100
plt.close('all')
'''.replace('__BUNDLE__', repr(sys._MEIPASS))
        result = engine.execute(code)
        if not result['ok']: raise AssertionError(result)
        report.update(state='complete', resource_count=len(RESOURCES), unit_count=len(expected['catalog']['units']), scientific_worker=True)
    except BaseException as error:
        report.update(state='failed', error=repr(error)); raise
    finally:
        engine.close()
        report.update(seconds=round(time.monotonic() - started, 2), worker_stopped=process is None or process.poll() is not None,
                      workspace_removed=workspace is None or not workspace.exists())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); print(json.dumps(report), flush=True)
    return 0
