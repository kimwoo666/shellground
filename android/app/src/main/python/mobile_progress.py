"""Lossless metadata bridge between Android preferences and PC progress files.

Only known learning fields are exported. Unknown PC records remain untouched;
code, addresses, credentials and editor contents never enter these documents.
"""
from copy import deepcopy
import json
from pathlib import Path
from nas_sync import FILES, atomic_json, read_json, Synchronizer

PHASES = ('learn', 'example', 'practice1', 'practice2')
SCOPES = {'python-progress-v1': 'python-progress-v1.json',
          'real-conda-progress-v1': 'conda-progress-v1.json',
          'real-notebook-progress-v1': 'notebook-progress-v1.json',
          'real-linux-progress-v1': 'progress-v3-real.json'}


def export_preferences(preferences, catalogs, existing):
    docs = deepcopy(existing)
    for scope, filename in SCOPES.items():
        prefs = preferences.get(scope, {})
        if not prefs: continue
        data = docs.setdefault(filename, {'schema': FILES[filename]})
        linux = scope == 'real-linux-progress-v1'
        python = scope == 'python-progress-v1'
        separator = '.' if python else ':'
        last = prefs.get('last')
        for unit in catalogs[scope]:
            key = unit['key']
            passed = [v for v in range(3) if prefs.get(key+(':' if python else ':done:')+str(v)) is True]
            if linux:
                if 1 in passed and 2 in passed:
                    field = 'checkpoints' if unit.get('review') else 'completed'
                    data[field] = sorted(set(data.get(field, [])) | {key})
            else:
                data['passed'] = sorted(set(data.get('passed', [])) | {f'{key}:{v}' for v in passed})
                if all(f'{key}:{v}' in data['passed'] for v in (1,2)):
                    data['completed'] = sorted(set(data.get('completed', [])) | {key})
            phase = prefs.get(key+separator+'phase')
            if type(phase) is not int or phase not in range(4): continue
            pages = unit.get('learning_steps', [])
            step = max(0, min(int(prefs.get(key+separator+'step', 0)), max(0, len(pages)-1)))
            if linux:
                if phase == 0 and pages:
                    record = data.setdefault('learning', {}).setdefault(key, {'confirmed': []})
                    record['cursor'] = pages[step]['title']
                if key == last: data['last_learning'] = key if phase == 0 else ''
            else:
                position = dict(phase=PHASES[phase], step=step)
                data.setdefault('positions', {})[key] = position
                if phase == 0: data.setdefault('learning', {})[key] = step
                if key == last: data['resume'] = dict(unit=key, **position)
        if python:
            for quiz in catalogs.get('quizzes', []):
                qid = quiz['id']
                if prefs.get('quiz.'+qid) is True:
                    data.setdefault('quiz', {}).setdefault(qid, {})['passed'] = True
                related = [c for c in catalogs.get('cards', []) if qid in c['quiz_ids']]
                at = prefs.get('card.'+qid)
                if type(at) is int and 0 <= at < len(related):
                    data.setdefault('concept_positions', {})[qid] = related[at]['id']
        if scope == 'real-conda-progress-v1' and prefs.get('conda_install_once:done') is True:
            data['setup_completed'] = sorted(set(data.get('setup_completed', [])) | {'conda_install_once'})
    return docs


def import_preferences(documents, catalogs, existing):
    preferences = deepcopy(existing)
    for scope, filename in SCOPES.items():
        data = documents.get(filename, {})
        prefs = preferences.setdefault(scope, {})
        linux = scope == 'real-linux-progress-v1'
        python = scope == 'python-progress-v1'
        separator = '.' if python else ':'
        for unit in catalogs[scope]:
            key = unit['key']
            complete = key in data.get('completed', []) or (linux and key in data.get('checkpoints', []))
            for variant in range(3):
                if (complete and variant in (1,2)) or f'{key}:{variant}' in data.get('passed', []):
                    prefs[key+(':' if python else ':done:')+str(variant)] = True
            if linux:
                record = data.get('learning', {}).get(key, {})
                titles = [page['title'] for page in unit.get('learning_steps', [])]
                if record.get('cursor') in titles:
                    prefs[key+':phase'] = 0
                    prefs[key+':step'] = titles.index(record['cursor'])
            else:
                position = data.get('positions', {}).get(key, {})
                if position.get('phase') in PHASES:
                    prefs[key+separator+'phase'] = PHASES.index(position['phase'])
                    prefs[key+separator+'step'] = max(0, min(int(position.get('step',0)), max(0,len(unit.get('learning_steps', []))-1)))
        last = data.get('last_learning') if linux else data.get('resume', {}).get('unit')
        if last in {unit['key'] for unit in catalogs[scope]}: prefs['last'] = last
        if python:
            for number, quiz in enumerate(catalogs.get('quizzes', [])):
                qid = quiz['id']
                if data.get('quiz', {}).get(qid, {}).get('passed'): prefs['quiz.'+qid] = True
                related = [c['id'] for c in catalogs.get('cards', []) if qid in c['quiz_ids']]
                current = data.get('concept_positions', {}).get(qid)
                if current in related: prefs['card.'+qid] = related.index(current)
            quizzes = catalogs.get('quizzes', [])
            prefs['quiz.position'] = next((i for i,q in enumerate(quizzes) if not prefs.get('quiz.'+q['id'])),0)
        if scope == 'real-conda-progress-v1' and 'conda_install_once' in data.get('setup_completed', []):
            prefs['conda_install_once:done'] = True
    return preferences


class JavaStore:
    def __init__(self, store): self.store = store
    def read(self, name): return json.loads(str(self.store.read(name)))
    def write(self, name, data): self.store.write(name, json.dumps(data, ensure_ascii=False))
    def names(self): return list(self.store.names())
    def marker(self): return self.read('shellground-profile.json')


def exchange(directory, preferences_json, catalogs_json, remote=None, apply=False):
    directory = Path(directory)
    preferences, catalogs = json.loads(preferences_json), json.loads(catalogs_json)
    existing = {name: read_json(directory/name) for name in FILES if (directory/name).is_file()}
    exported = export_preferences(preferences, catalogs, existing)
    for name, data in exported.items():
        if data != existing.get(name): atomic_json(directory/name, data)
    result = {'remote_changes': False}
    if remote is not None:
        store = JavaStore(remote)
        marker = store.marker()
        if marker.get('schema') != 1 or not isinstance(marker.get('profile'), str):
            raise ValueError('Shellground 진도 전용 폴더가 아닙니다.')
        result = Synchronizer(directory, {'profile': marker['profile']}, store=store).synchronize(apply=apply)
    docs = {name: read_json(directory/name) for name in FILES if (directory/name).is_file()}
    if apply: result['preferences'] = import_preferences(docs, catalogs, preferences)
    return json.dumps(result, ensure_ascii=False)
