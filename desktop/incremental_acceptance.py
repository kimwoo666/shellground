"""Immutable, explicitly reviewed evidence reuse; never rewrites old proof stamps.

The manifest is a release review artifact, not a claim that old cases were run
again. Missing cases, stale source bindings and failed cleanup block packaging.
"""
import hashlib
import json
from pathlib import Path
import re

SCHEMA = 1
ROS_NEGATIVE = {'unfiltered_bag_playback_rejected', 'wrong_service_orientation_repaired',
                'stale_parameter_report_repaired'}


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def source_snapshot(root):
    names = {'missions.py', 'practice.py', 'practice_variants.py', 'real_lessons.py', 'real_vm.py',
             'mode_curriculum.py', 'course_topics.py', 'checkpoints.py', 'real_course_checks.py',
             'linux_learning.py', 'learning_steps.py', 'real_acceptance.py', 'incremental_acceptance.py',
             'verify_ros_acceptance.py'}
    paths = {root / name for name in names if (root / name).is_file()}
    for pattern in ('*_lessons.py', '*_course.py', '*_guides.py', 'guest/*.py', 'lab/*.py', 'guest/bashrc'):
        paths.update(p for p in root.glob(pattern) if p.is_file() and not p.name.startswith('test_'))
    return {path.relative_to(root).as_posix(): digest(path) for path in sorted(paths)}


def definitions():
    from real_acceptance import expected_cases
    from mode_curriculum import curriculum
    from real_course_checks import make_review
    expected = expected_cases() | expected_cases(True)
    aliases = {}
    for checkpoint in curriculum('real')[1]:
        kind = make_review(checkpoint, 7251).kind
        # A local block verifier calls its review by mission kind, while the
        # registered full-course verifier uses the stable checkpoint key.
        for alias in (kind, kind + ':0'):
            if alias in aliases and aliases[alias] != checkpoint.key:
                aliases[alias] = None  # generic linux_review is ambiguous
            else: aliases[alias] = checkpoint.key
    return expected, {k: v for k, v in aliases.items() if v is not None}


def canonical(case, expected, aliases):
    if case in expected: return case
    if case in aliases and aliases[case] in expected: return aliases[case]
    raise RuntimeError('Unregistered or ambiguous evidence case: ' + str(case))


def _bound_file(directory, record):
    if not isinstance(record, dict) or not isinstance(record.get('file'), str):
        raise RuntimeError('Evidence file binding is required')
    relative = Path(record['file'])
    if relative.is_absolute() or '..' in relative.parts: raise RuntimeError('Evidence path escapes its directory')
    path = directory / relative
    if not path.resolve().is_relative_to(directory.resolve()) or not path.is_file():
        raise RuntimeError('Evidence file missing or outside its directory')
    if record.get('sha256') != digest(path): raise RuntimeError('Evidence changed: ' + record['file'])
    return path


def _reason(value):
    if not isinstance(value, str) or len(value.strip()) < 20:
        raise RuntimeError('A concrete review/reuse explanation is required')


def _provenance(report):
    hashes = report.get('source_hashes')
    if isinstance(hashes, dict) and hashes and all(isinstance(k, str) and isinstance(v, str) and
                                                 re.fullmatch('[0-9a-f]{64}', v) for k, v in hashes.items()):
        return hashes
    if isinstance(report.get('source_fingerprint'), str) and re.fullmatch('[0-9a-f]{64}', report['source_fingerprint']):
        return report['source_fingerprint']
    raise RuntimeError('Original source provenance is missing')


def _is_current(report, root):
    provenance = _provenance(report)
    if isinstance(provenance, dict):
        for name, stamp in provenance.items():
            path = root / name
            if Path(name).is_absolute() or '..' in Path(name).parts or not path.is_file(): return False
            if not path.resolve().is_relative_to(root.resolve()) or digest(path) != stamp: return False
        return True
    from verify_real_course import fingerprint
    return provenance == fingerprint()


def passed_cases(report):
    values = report.get('passed')
    if not isinstance(values, (dict, list)) or any(not isinstance(v, str) for v in values):
        raise RuntimeError('Explicit passed case IDs are required')
    result = set(values)
    if len(result) != len(values): raise RuntimeError('Duplicate passed case')
    return result


def validate(manifest, directory, root):
    expected, aliases = definitions()
    if manifest.get('schema') != SCHEMA or manifest.get('kind') != 'reviewed-incremental-course-evidence':
        raise RuntimeError('Unsupported incremental course manifest')
    if manifest.get('source_snapshot') != source_snapshot(root):
        raise RuntimeError('Sources changed since the incremental coverage review')
    if set(manifest.get('expected', [])) != expected or len(manifest['expected']) != len(expected):
        raise RuntimeError('Current registered coverage is not bound exactly')
    _bound_file(directory, manifest.get('review'))
    if not isinstance(manifest.get('requires_fresh'), list): raise RuntimeError('Explicit changed-case review is required')
    required_fresh = set(manifest['requires_fresh'])
    if required_fresh - expected: raise RuntimeError('Unknown changed case')
    records = manifest.get('evidence')
    if not isinstance(records, list) or not records: raise RuntimeError('No evidence records')
    covered, fresh, negative, carried = set(), set(), set(), set()
    for record in records:
        path = _bound_file(directory, record)
        report = json.loads(path.read_text())
        _provenance(report)
        if report.get('vm_stopped') is not True or report.get('overlay_removed') is not True:
            raise RuntimeError('Evidence cleanup incomplete: ' + record['file'])
        selection = record.get('cases')
        if (not isinstance(selection, list) or not selection or any(not isinstance(c, str) for c in selection) or
                len(selection) != len(set(selection)) or set(selection) - passed_cases(report)):
            raise RuntimeError('Selected evidence case did not pass: ' + record['file'])
        failures = report.get('failures', {})
        if report.get('state') == 'complete':
            if failures: raise RuntimeError('Complete report contains failures')
        elif report.get('state') in ('failed', 'cancelled'):
            # Earlier successful cases can survive a later failure/cancellation,
            # but that decision and the excluded failing tail must be explicit.
            _reason(record.get('partial_review'))
            if isinstance(failures, dict) and set(selection) & set(failures):
                raise RuntimeError('A failed case cannot be carried forward')
        else: raise RuntimeError('Evidence is still running or has unknown state')
        ids = {canonical(case, expected, aliases) for case in selection}
        if len(ids) != len(selection) or covered & ids:
            raise RuntimeError('Each registered case must have one chosen baseline')
        basis = record.get('basis')
        if basis == 'current':
            if not _is_current(report, root): raise RuntimeError('Old evidence may not be labelled current')
            fresh.update(ids)
        elif basis == 'reviewed-carry':
            _reason(record.get('reason')); carried.update(ids)
        else: raise RuntimeError('Specify current evidence or reviewed carry-forward')
        covered.update(ids)
        values = report.get('negative', []) or []
        if not isinstance(values, list) or any(not isinstance(v, str) for v in values):
            raise RuntimeError('Invalid negative evidence IDs')
        negative.update(values)
    if covered != expected:
        raise RuntimeError('Unverified registered cases: ' + ', '.join(sorted(expected - covered)))
    if required_fresh - fresh:
        raise RuntimeError('Changed cases need current evidence: ' + ', '.join(sorted(required_fresh - fresh)))
    if not ROS_NEGATIVE <= negative: raise RuntimeError('Required ROS negative/recovery evidence missing')
    return {'registered': len(expected), 'current': len(fresh), 'reviewed_carry': len(carried),
            'negative_evidence': sorted(negative), 'reran_entire_course': False}


def validate_file(path, root=None):
    path = Path(path); root = Path(root) if root is not None else Path(__file__).parent
    return validate(json.loads(path.read_text()), path.parent, root)


def inventory(paths):
    """Read-only candidate inventory, deliberately not an acceptance manifest."""
    expected, aliases = definitions(); observed = set(); rows = []
    for path in paths:
        report = json.loads(path.read_text()); passed = passed_cases(report)
        known = set()
        for case in passed:
            try: known.add(canonical(case, expected, aliases))
            except RuntimeError: pass
        observed.update(known)
        rows.append({'file': str(path), 'state': report.get('state'), 'recorded_passes': len(known),
                     'vm_stopped': report.get('vm_stopped'), 'overlay_removed': report.get('overlay_removed')})
    return {'accepted': False, 'reason': 'Inventory only; source/change review and selected baselines are still required',
            'reports': rows, 'registered': len(expected), 'observed': len(observed), 'missing': sorted(expected - observed)}


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--inventory', nargs='+', type=Path)
    parser.add_argument('--manifest', type=Path)
    args = parser.parse_args()
    if bool(args.inventory) == bool(args.manifest): parser.error('Choose --inventory or --manifest')
    print(json.dumps(inventory(args.inventory) if args.inventory else validate_file(args.manifest), ensure_ascii=False, indent=2))
