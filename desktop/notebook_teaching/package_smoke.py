"""One actual selected kernel in the new executable, not all 18 course cases."""
import argparse
import json
from pathlib import Path
import sys
import time
from .course import lessons
from .engine import NotebookEngine
from .verify_course import solve


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--runtime', type=Path, required=True); parser.add_argument('--report', type=Path, required=True)
    args = parser.parse_args(argv)
    if not getattr(sys, 'frozen', False): raise RuntimeError('Requires the newly built executable')
    if args.report.exists(): raise FileExistsError('Preserve prior packaged evidence')
    engine = NotebookEngine(args.runtime); started = time.monotonic()
    report = dict(scope='new-binary-one-real-notebook-kernel', state='in_progress', frozen=True, full_course_rerun=False)
    try:
        problem = next(u for u in lessons() if u['key'] == 'jupyter_select')['problems'][0]
        engine.start_problem(problem)
        if engine.grade_problem(problem, problem['cells'])['passed']: raise AssertionError('Unsolved problem passed')
        document = solve(engine, problem)
        if not engine.grade_problem(problem, document)['passed']: raise AssertionError('Bundled kernel or grading failed')
        engine.perform('save', filename='package-smoke.ipynb', cells=document)
        report.update(state='complete', selected=['jupyter_select:0'], identity=engine.perform('identity'))
    except BaseException as error:
        report.update(state='failed', error=repr(error)); raise
    finally:
        process, directory = engine.process, engine.session_dir; engine.close()
        report.update(seconds=round(time.monotonic() - started, 2), vm_stopped=process is None or process.poll() is not None,
                      overlay_removed=directory is None or not directory.exists())
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n'); print(json.dumps(report), flush=True)
    return 0
