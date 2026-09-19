"""Repackage pinned guest wheels with current scripts, without a course rerun."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def options(bundle, output):
    source = Path(bundle) / '_internal/notebook_teaching'
    spec = json.loads((ROOT / 'notebook_teaching/assets-linux-x86_64.json').read_text())
    for wheel in spec['wheels']:
        path = source / 'wheels-linux-x86_64' / wheel['filename']
        with path.open('rb') as stream:
            digest = hashlib.file_digest(stream, 'sha256').hexdigest()
        if path.stat().st_size != wheel['size'] or digest != wheel['sha256']:
            raise ValueError('Unverified offline notebook wheel: ' + wheel['filename'])
    args = ['--add-data', str(source / 'wheels-linux-x86_64') + ':notebook_teaching/wheels-linux-x86_64']
    for name in ('assets-linux-x86_64.json', 'guest_setup.py', 'guest_service.py', 'guest_lessons.py'):
        args += ['--add-data', str(ROOT / 'notebook_teaching' / name) + ':notebook_teaching']
    from notebook_teaching.proof import source_hashes
    directory = Path(output) / 'offline-assets'
    directory.mkdir(parents=True, exist_ok=True)
    receipt = directory / 'source-hashes.json'
    receipt.write_text(json.dumps(source_hashes(), indent=2), encoding='utf-8')
    args += ['--add-data', str(receipt) + ':notebook_teaching']
    return args
