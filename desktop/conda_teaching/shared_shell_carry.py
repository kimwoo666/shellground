"""Narrow build-time reuse for exactly two shared shell files, not a bypass.

The old frozen artifact contains the original sources. Reconstructing the
original aggregate with just those two substitutions proves that every other
Conda grading/teaching source is unchanged. A real delta must cover the shell.
"""
import hashlib
import json
from pathlib import Path
from .course_smoke import source_fingerprint, RC
from .learning_smoke import learning_fingerprint
from .engine import course
from .export_runtime import validate_report, validate_learning
from .setup_smoke import validate_setup

ALLOWED = ('guest/bashrc', 'guest/shell_snapshot.py')
CHECKS = {'base_activation_snapshot', 'deactivation_snapshot', 'shared_exports_and_cwd',
          'unseeded_shell_has_no_fixture_jobs', 'base_python_runs'}


def digest(path):
    value = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): value.update(block)
    return value.hexdigest()


def baseline_fingerprint(root, original):
    if set(original) != set(ALLOWED): raise RuntimeError('Only the two reviewed shell sources may differ')
    names = next(v for v in source_fingerprint.__code__.co_consts if isinstance(v, tuple) and 'guest/bashrc' in v)
    value = hashlib.sha256()
    for name in names:
        value.update(name.encode()); value.update(original[name] if name in original else (root / name).read_bytes())
    value.update(RC.encode()); return value.hexdigest()


def bound(root, record):
    name = record.get('file', '')
    relative = Path(name)
    if not name or relative.is_absolute() or '..' in relative.parts: raise RuntimeError('Invalid bound path')
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or digest(path) != record.get('sha256'):
        raise RuntimeError('Changed or missing bound file: ' + name)
    return path


def validate(review_path, runtime, root):
    root = Path(root).resolve(); runtime = Path(runtime).resolve()
    review = json.loads(Path(review_path).read_text())
    if review.get('kind') != 'reviewed-conda-shared-shell-only' or review.get('schema') not in (1, 2):
        raise RuntimeError('Unsupported Conda carry review')
    metadata = bound(root, review['runtime_metadata'])
    if metadata != runtime / 'runtime.json': raise RuntimeError('Review belongs to a different runtime')
    if review['schema'] == 1:
        from PyInstaller.archive.readers import CArchiveReader
        binary = bound(root, review['original_binary']); archive = CArchiveReader(binary)
        original = {name: archive.extract(name) for name in ALLOWED}
    else:
        # A tiny, checksum-bound extract replaces the retired 198MB verifier
        # executable. The reconstructed original teaching hash below still has
        # to match the untouched original course report exactly.
        records = review.get('original_sources', {})
        if set(records) != set(ALLOWED): raise RuntimeError('Incomplete baseline source extraction')
        original = {name: bound(root, records[name]).read_bytes() for name in ALLOWED}
    old = baseline_fingerprint(root, original); current = source_fingerprint()
    if review.get('baseline_fingerprint') != old or review.get('current_fingerprint') != current:
        raise RuntimeError('Conda source changes exceed this reviewed delta')
    expected = {name: dict(before=hashlib.sha256(original[name]).hexdigest(), after=digest(root / name)) for name in ALLOWED}
    if review.get('changed_sources') != expected: raise RuntimeError('Shell source binding differs')
    spec = json.loads(metadata.read_text())
    validate_report(spec.get('conda_validation', {}), course(), old)
    validate_learning(spec.get('conda_learning_validation', {}), course(), old, learning_fingerprint())
    validate_setup(spec.get('conda_setup_validation', {}))
    delta = json.loads(bound(root, review['delta']).read_text())
    if (delta.get('state') != 'complete' or set(delta.get('passed', [])) != CHECKS or
        delta.get('course_fingerprint') != current or delta.get('image_sha256') != spec.get('image_sha256') or
        delta.get('vm_stopped') is not True or delta.get('overlay_removed') is not True):
        raise RuntimeError('Current real shared-shell delta/cleanup required')
    bound(root, review['rationale'])
    return dict(course_cases=60, learning_units=20, basis='reviewed-carry', delta_checks=len(CHECKS), reran_entire_course=False)
