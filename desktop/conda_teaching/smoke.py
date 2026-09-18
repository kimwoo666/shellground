"""Opt-in acceptance through the distributed binary and its actual Conda pack."""
import json
import sys
import time

from conda_teaching.course_smoke import drain_until, execute_reference
from conda_teaching.engine import CondaEngine, course


def main():
    spec = course()
    unit = next(unit for unit in spec['units'] if unit['key'] == 'conda_activate')
    problem = unit['problems'][1]
    engine = CondaEngine()
    process = session = None
    started = time.monotonic()
    try:
        terminal = engine.start_problem(problem, spec['observer_contract']['module_probes'])
        process, session = engine.process, engine.session_dir
        drain_until(terminal, b'$ ', timeout=30)
        initial = engine.grade_problem({})
        if initial['passed']:
            raise AssertionError('Initial Conda practice must be unsolved')
        execute_reference(engine.channel, terminal, problem['reference_commands'])
        result = engine.grade_problem({})
        if not result['passed']:
            raise AssertionError(json.dumps(result, ensure_ascii=False))
        if engine.bridge is not terminal:
            raise AssertionError('Grading replaced the learner terminal')
        # Exercise the packaged read-only file helper as well as guest grading.
        execute_reference(engine.channel, terminal, [
            'conda export -n sg-writing --from-history --format=environment-yaml --file writing.yml'])
        files = engine.inspect_files()
        if 'writing.yml' not in files.get('files', []):
            raise AssertionError('Packaged guest file listing failed: ' + repr(files))
        contents = engine.inspect_files('writing.yml')
        if 'name: sg-writing' not in contents.get('text', ''):
            raise AssertionError('Packaged guest file helper failed: ' + repr(contents))
        print('PACKAGED_REAL_CONDA_OK', json.dumps({
            'conda_version': engine.ready['runtime']['conda_version'],
            'platform': engine.ready['runtime']['platform'],
            'frozen_application': bool(getattr(sys, 'frozen', False)),
            'same_terminal_retry': True, 'real_export_read': True,
            'elapsed_seconds': round(time.monotonic() - started, 2)}, ensure_ascii=False), flush=True)
    finally:
        engine.close()
        if process is not None and process.poll() is None:
            raise AssertionError('Owned VM supervisor survived self-test close')
        if session is not None and session.exists():
            raise AssertionError('Owned temporary overlay survived self-test close')
    print('PACKAGED_CONDA_CLEANUP_OK', flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
