"""Atomic, source-specific checkpoints for expensive real-guest verification.

Only a fully checked problem/learning sequence is added. Intermediate or
failed runs are not exportable even if a previous run had all passing IDs:
the current builder must also finish its clean-fixture preparation.
"""
import json
import os
from pathlib import Path
import tempfile
import time


def checkpoint(path, identity, evidence, *, state='in_progress', invalidate=(), **details):
    path = Path(path)
    if state not in ('in_progress', 'failed', 'complete'):
        raise ValueError('Unknown validation state')
    previous = json.loads(path.read_text()) if path.is_file() else {}
    same_source = all(previous.get(key) == value for key, value in identity.items())
    result = dict(identity)
    for key, values in evidence.items():
        before = previous.get(key, []) if same_source else []
        result[key] = sorted(set(before) | set(values))
    # A failed recheck must not keep its old passing ID and later become
    # exportable just because an unrelated filtered run completed.
    result['passed'] = sorted(set(result.get('passed', [])) - set(invalidate))
    result.update(details, count=len(result.get('passed', [])), state=state,
                  fixture_clean=state == 'complete', validated_at=time.time())
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return result
