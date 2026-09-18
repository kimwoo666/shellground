"""Offline assets and evidence required by a notebook-capable release."""
import json
from pathlib import Path
from engine import resource_path
from .assets import assets
from .proof import source_hashes, validate


def options(report_directory):
    report_directory = Path(report_directory)
    for name, ui in (('course-final.json', False), ('ui-final.json', True)):
        validate(json.loads((report_directory / name).read_text()), ui=ui)
    directory, _ = assets()
    generated = report_directory / 'source-hashes.json'
    generated.write_text(json.dumps(source_hashes(), indent=2) + '\n')
    pairs = [(directory, 'notebook_teaching/wheels-linux-x86_64'),
             (generated, 'notebook_teaching')]
    pairs += [(resource_path('notebook_teaching/' + name), 'notebook_teaching') for name in (
        'assets-linux-x86_64.json', 'guest_setup.py', 'guest_service.py', 'guest_lessons.py')]
    return [part for source, destination in pairs for part in ('--add-data', f'{source}:{destination}')]
