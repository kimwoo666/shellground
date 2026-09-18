"""Versioned evidence for the newly connected concept catalog and native UI only."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import time
import unittest

FILES = ('system_concepts.py', 'system_concept_progress.py', 'system_concept_dialog.py', 'native_app.py',
         'mode_curriculum.py', 'build.py', 'test_system_concepts.py', 'test_system_concept_ui.py',
         'python_teaching/linux_docker_concept_draft.json', 'python_teaching/shell_concept_draft.json',
         'python_teaching/process_concept_draft.json', 'python_teaching/io_concept_draft.json',
         'python_teaching/system_info_concept_draft.json', 'verify_system_concepts.py')


def verify(destination, names):
    if not names or any(name.split('.')[0] not in ('test_system_concepts', 'test_system_concept_ui') for name in names):
        raise ValueError('Only new concept checks are allowed here')
    root = Path(__file__).parent
    hashes = lambda: {name: hashlib.sha256((root / name).read_bytes()).hexdigest() for name in FILES}
    before = hashes(); started = time.monotonic()
    suite = unittest.defaultTestLoader.loadTestsFromNames(names)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    unchanged = before == hashes()
    success = result.wasSuccessful() and unchanged and not result.skipped
    report = dict(scope='new-system-concepts-data-and-native-ui-only', state='complete' if success else 'failed',
                  selected=names, tests_run=result.testsRun, seconds=round(time.monotonic() - started, 2),
                  skipped=result.skipped, failures=[(str(test), error) for test, error in result.failures + result.errors],
                  source_hashes=before, sources_unchanged=unchanged,
                  engine_execution=False, old_course_reexecution=False,
                  screenshots=os.environ.get('SHELLGROUND_CONCEPT_CAPTURE', ''))
    destination.parent.mkdir(parents=True, exist_ok=True)
    temporary = destination.with_suffix('.tmp')
    temporary.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    temporary.replace(destination)
    print(json.dumps({k: v for k, v in report.items() if k not in ('source_hashes', 'failures')}, ensure_ascii=False), flush=True)
    return success


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--tests', nargs='+', default=['test_system_concepts', 'test_system_concept_ui'])
    arguments = parser.parse_args()
    raise SystemExit(0 if verify(arguments.report, arguments.tests) else 1)
