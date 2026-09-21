"""Small, private learning snapshots. No VM, source code, settings or credentials.

Every device owns one snapshot, so concurrent computers never overwrite each
other. Version vectors distinguish a later edit from a concurrent edit. Earned
completion is monotonic; concurrently edited notes are kept as separate notes.
"""
from copy import deepcopy
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading
import time
import uuid

FILES = {'progress-v3.json': 3, 'progress-v3-real.json': 3,
         'progress-v3-simulation.json': 3, 'python-progress-v1.json': 1,
         'conda-progress-v1.json': 1, 'notebook-progress-v1.json': 1,
         'system-concepts-v1.json': 1, 'memory-v1.json': 1}
FIELDS = {'completed', 'passed', 'checkpoints', 'learning', 'last_learning',
          'positions', 'concept_positions', 'setup_completed', 'quiz', 'resume'}
SETS = {'completed', 'passed', 'checkpoints', 'setup_completed'}
LIMIT = 4 * 1024 * 1024
DEVICE = re.compile(r'^[0-9a-f]{32}$')
MARKER = 'shellground-profile.json'


@contextmanager
def local_lock(directory):
    Path(directory).mkdir(parents=True, exist_ok=True)
    with (Path(directory) / 'nas-sync.lock').open('a+b') as stream:
        if sys.platform == 'win32':
            import msvcrt
            if stream.tell() == 0: stream.write(b'0'); stream.flush()
            stream.seek(0)
            try: msvcrt.locking(stream.fileno(), msvcrt.LK_NBLCK, 1)
            except OSError as exc: raise OSError('다른 Shellground 창에서 진도를 동기화 중입니다.') from exc
            try: yield
            finally:
                stream.seek(0); msvcrt.locking(stream.fileno(), msvcrt.LK_UNLCK, 1)
        else:
            import fcntl
            try: fcntl.flock(stream, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError as exc: raise OSError('다른 Shellground 창에서 진도를 동기화 중입니다.') from exc
            try: yield
            finally: fcntl.flock(stream, fcntl.LOCK_UN)


def encode(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def read_json(path):
    with Path(path).open('rb') as stream:
        raw = stream.read(LIMIT + 1)
    if len(raw) > LIMIT: raise ValueError('진도 파일 크기 제한을 초과했습니다.')
    return json.loads(raw)


def atomic_json(path, value):
    path = Path(path)
    raw = encode(value).encode('utf-8')
    if len(raw) > LIMIT: raise ValueError('진도 파일 크기 제한을 초과했습니다.')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as stream:
            stream.write(raw); stream.flush(); os.fsync(stream.fileno())
        os.replace(name, path)
    finally:
        Path(name).unlink(missing_ok=True)


def flatten(documents):
    result = {}
    def walk(name, path, value):
        if len(path) > 8: raise ValueError('진도 구조가 너무 깊습니다.')
        if isinstance(value, dict):
            for key, child in value.items():
                if not isinstance(key, str) or len(key) > 300: raise ValueError('잘못된 진도 키')
                walk(name, path + [key], child)
        elif isinstance(value, list):
            if path[0] not in SETS and path[-1] != 'confirmed':
                raise ValueError('지원하지 않는 진도 목록')
            for item in value:
                if not isinstance(item, str): raise ValueError('잘못된 완료 기록')
                result[encode(['set', name, *path, item])] = True
        elif value is None or isinstance(value, (str, int, float, bool)):
            result[encode(['value', name, *path])] = value
        else: raise ValueError('지원하지 않는 진도 값')
    for name, data in documents.items():
        if name not in FILES or not isinstance(data, dict) or data.get('schema') != FILES[name]:
            raise ValueError('지원하지 않는 진도 파일 형식: ' + name)
        if name == 'memory-v1.json':
            notes = data.get('notes', [])
            if not isinstance(notes, list): raise ValueError('기억노트 형식 오류')
            for note in notes:
                if not isinstance(note, dict) or any(not isinstance(note.get(k), str) for k in ('id','title','body','unit')):
                    raise ValueError('기억노트 형식 오류')
                key = encode(['note', name, note['id']])
                if not note['id'] or key in result: raise ValueError('중복 기억노트 ID')
                result[key] = {k: note[k] for k in ('id','title','body','unit')}
        else:
            for field in FIELDS & data.keys(): walk(name, [field], data[field])
    return result


def clock_join(a, b):
    return {k: max(a.get(k, 0), b.get(k, 0)) for k in a.keys() | b.keys()}


def dominates(a, b):
    return all(a.get(k, 0) >= n for k, n in b.items())


def validate_clock(clock):
    if not isinstance(clock, dict) or len(clock) > 64: raise ValueError('기기 버전 정보 오류')
    if any(not DEVICE.fullmatch(k) or type(v) is not int or not 0 <= v <= 2**53 for k, v in clock.items()):
        raise ValueError('기기 버전 정보 오류')


def validate_snapshot(data, profile):
    if not isinstance(data, dict) or data.get('schema') != 1 or data.get('profile') != profile:
        raise ValueError('다른 사용자 또는 지원하지 않는 NAS 진도입니다.')
    validate_clock(data.get('clock'))
    records = data.get('records')
    if not isinstance(records, dict) or len(records) > 20000: raise ValueError('진도 항목 수 제한')
    for key, record in records.items():
        parts = json.loads(key)
        if not isinstance(parts, list) or not 3 <= len(parts) <= 12 or not all(isinstance(p, str) for p in parts):
            raise ValueError('진도 키 형식 오류')
        kind, name, *path = parts
        if name not in FILES or kind not in ('set','value','note'): raise ValueError('허용되지 않은 진도 항목')
        if kind == 'note':
            if name != 'memory-v1.json' or len(path) != 1: raise ValueError('기억노트 키 오류')
        elif name == 'memory-v1.json' or path[0] not in FIELDS:
            raise ValueError('허용되지 않은 진도 항목')
        if kind == 'set' and (len(path) < 2 or (path[0] not in SETS and path[-2] != 'confirmed')):
            raise ValueError('완료 항목 형식 오류')
        if kind == 'value' and (path[0] in SETS or path[-1] == 'confirmed'):
            raise ValueError('완료 목록은 스칼라 값이 될 수 없습니다.')
        if not isinstance(record, dict): raise ValueError('진도 레코드 오류')
        validate_clock(record.get('clock'))
        if not dominates(data['clock'], record['clock']): raise ValueError('진도 버전 불일치')
        value = record.get('value')
        if kind == 'set' and value is not True: raise ValueError('완료 기록은 지울 수 없습니다.')
        if kind == 'note' and value is not None:
            if (not isinstance(value, dict) or set(value) != {'id','title','body','unit'}
                    or value.get('id') != path[0] or not all(isinstance(v, str) for v in value.values())):
                raise ValueError('기억노트 값 오류')
        if kind == 'value' and isinstance(value, (dict, list)): raise ValueError('진도 값 형식 오류')
        stamp = record.get('stamp')
        if not isinstance(stamp, list) or len(stamp) != 2 or type(stamp[0]) is not int or not DEVICE.fullmatch(stamp[1]):
            raise ValueError('진도 수정 시각 오류')
    return data


def merge(left, right):
    validate_snapshot(left, left['profile']); validate_snapshot(right, left['profile'])
    out = deepcopy(left)
    out['clock'] = clock_join(left['clock'], right['clock'])
    for key, incoming in right['records'].items():
        old = out['records'].get(key)
        if old is None: out['records'][key] = deepcopy(incoming); continue
        if old == incoming: continue
        if dominates(old['clock'], incoming['clock']) and old['clock'] != incoming['clock']: continue
        if dominates(incoming['clock'], old['clock']) and old['clock'] != incoming['clock']:
            out['records'][key] = deepcopy(incoming); continue
        kind, name, *path = json.loads(key)
        winner, loser = sorted((old, incoming), key=lambda r: (r['stamp'], encode(r['value'])), reverse=True)
        joined = clock_join(old['clock'], incoming['clock'])
        if kind == 'note' and winner['value'] != loser['value'] and loser['value'] is not None:
            note = deepcopy(loser['value'])
            suffix = hashlib.sha256(encode([key, loser]).encode()).hexdigest()[:20]
            note['id'] = 'conflict-' + suffix
            note['title'] += ' [다른 기기 수정본]'
            out['records'][encode(['note', name, note['id']])] = dict(value=note, clock=joined, stamp=loser['stamp'])
        value = deepcopy(winner['value'])
        if kind == 'set' or (path[-1] == 'passed' and (old['value'] is True or incoming['value'] is True)):
            value = True
        if path[-1] == 'attempts' and all(type(r['value']) is int for r in (old, incoming)):
            value = max(old['value'], incoming['value'])
        out['records'][key] = dict(value=value, clock=joined, stamp=winner['stamp'])
    return validate_snapshot(out, left['profile'])


def project(snapshot, existing):
    documents = deepcopy(existing)
    for key, record in sorted(snapshot['records'].items()):
        kind, name, *path = json.loads(key)
        data = documents.setdefault(name, {'schema': FILES[name]})
        value = deepcopy(record['value'])
        if kind == 'note':
            notes = data.setdefault('notes', [])
            notes[:] = [n for n in notes if n['id'] != path[0]]
            if value is not None: notes.append(value)
            continue
        parent = data
        end = -2 if kind == 'set' else -1
        for p in path[:end]:
            if p in parent and not isinstance(parent[p], dict): raise ValueError('진도 항목 구조 충돌')
            parent = parent.setdefault(p, {})
        if kind == 'set':
            values = parent.setdefault(path[-2], [])
            if not isinstance(values, list): raise ValueError('완료 목록 구조 충돌')
            if path[-1] not in values: values.append(path[-1])
        else: parent[path[-1]] = value
    flatten(documents)  # Validate the projected structure before any local write.
    return documents


class FolderStore:
    def __init__(self, root): self.root = Path(root)
    def read(self, name): return read_json(self.root / name)
    def write(self, name, data): atomic_json(self.root / name, data)
    def names(self): return sorted(p.name for p in self.root.glob('device-*.json'))
    def marker(self):
        if not self.root.is_dir(): raise OSError('NAS 폴더가 연결되어 있지 않습니다.')
        return self.read(MARKER)


class RcloneStore:
    """Use an existing, locally configured NAS login; never save its secret."""
    def __init__(self, command, remote, cancelled=None):
        self.command, self.remote = command, remote.rstrip('/')
        self.cancelled = cancelled or threading.Event()
    def run(self, *args):
        if self.cancelled.is_set(): raise OSError('동기화를 중단했습니다.')
        environment = dict(os.environ)
        if getattr(sys, 'frozen', False):
            for key in ('PYTHONHOME', 'PYTHONPATH', 'TCL_LIBRARY', 'TK_LIBRARY'):
                environment.pop(key, None)
            if 'LD_LIBRARY_PATH_ORIG' in environment:
                environment['LD_LIBRARY_PATH'] = environment.pop('LD_LIBRARY_PATH_ORIG')
            else: environment.pop('LD_LIBRARY_PATH', None)
        with tempfile.TemporaryFile() as output, tempfile.TemporaryFile() as errors:
            process = subprocess.Popen([self.command, *args, '--contimeout','5s','--timeout','10s',
                '--retries','1','--low-level-retries','1'], stdout=output, stderr=errors, env=environment)
            deadline = time.monotonic() + 15
            try:
                while process.poll() is None:
                    if self.cancelled.wait(.1) or time.monotonic() > deadline:
                        raise OSError('NAS 연결이 지연되어 로컬 진도를 유지했습니다.')
                if process.returncode: raise OSError('NAS 연결·권한을 확인하세요. 로컬 진도는 유지됩니다.')
                output.seek(0); raw = output.read(LIMIT + 1)
                if len(raw) > LIMIT: raise ValueError('NAS 응답 크기 제한')
                return raw
            finally:
                if process.poll() is None:
                    process.terminate()
                    try: process.wait(timeout=1)
                    except subprocess.TimeoutExpired: process.kill(); process.wait()
    def read(self, name): return json.loads(self.run('cat', self.remote + '/' + name))
    def write(self, name, data):
        with tempfile.TemporaryDirectory(prefix='shellground-sync-') as folder:
            path = Path(folder) / name; atomic_json(path, data)
            self.run('copyto', str(path), self.remote + '/' + name)
    def names(self):
        return self.run('lsf', self.remote, '--files-only', '--max-depth', '1').decode().splitlines()
    def marker(self): return self.read(MARKER)


class Synchronizer:
    def __init__(self, local, config, store=None, cancelled=None):
        self.local = Path(local); self.config = config
        self.state_path = self.local / 'nas-sync-state-v1.json'
        self.store = store or (RcloneStore(config['command'], config['remote'], cancelled)
            if config['transport'] == 'rclone' else FolderStore(config['folder']))
    def documents(self):
        return {name: read_json(self.local / name) for name in FILES if (self.local / name).is_file()}
    def synchronize(self, apply=False):
        with local_lock(self.local): return self._synchronize(apply)

    def _synchronize(self, apply):
        marker = self.store.marker()
        profile = self.config['profile']
        if marker != {'schema': 1, 'profile': profile}: raise ValueError('선택한 NAS 프로필이 다릅니다.')
        docs = self.documents(); current = flatten(docs)
        if self.state_path.exists():
            state = read_json(self.state_path)
            if state.get('profile') != profile: raise ValueError('다른 NAS 프로필로 자동 병합할 수 없습니다.')
        else:
            state = dict(profile=profile, device=uuid.uuid4().hex, observed={},
                         snapshot=dict(schema=1, profile=profile, clock={}, records={}))
        device = state['device']
        if not DEVICE.fullmatch(device): raise ValueError('로컬 기기 ID 오류')
        snapshot = validate_snapshot(state['snapshot'], profile)
        changed = {key: value for key, value in current.items() if key not in state['observed'] or value != state['observed'][key]}
        for key in state['observed'].keys() - current.keys():
            parts = json.loads(key)
            if parts[0] == 'note' and parts[1] in docs: changed[key] = None
        if changed:
            snapshot['clock'][device] = snapshot['clock'].get(device, 0) + 1
            for key, value in changed.items():
                parts = json.loads(key)
                previous = snapshot['records'].get(key, {}).get('value')
                if parts[-1] == 'passed' and previous is True: value = True
                if parts[-1] == 'attempts' and type(value) is int and type(previous) is int:
                    value = max(value, previous)
                snapshot['records'][key] = dict(value=value, clock=dict(snapshot['clock']), stamp=[time.time_ns(), device])
        state['observed'] = current
        # Preserve edits locally even if reading or writing the NAS later fails.
        state['snapshot'] = snapshot; atomic_json(self.state_path, state)
        names = [name for name in self.store.names() if re.fullmatch(r'device-[0-9a-f]{32}\.json', name)]
        if len(names) > 64: raise ValueError('NAS 연결 기기 수 제한')
        for name in names: snapshot = merge(snapshot, self.store.read(name))
        desired = project(snapshot, docs)
        # Startup only: never overwrite a currently running editor's in-memory
        # learning cursor. During a session we publish and queue remote changes.
        if apply:
            if self.documents() != docs: raise OSError('진도가 변경 중입니다. 다시 동기화하세요.')
            backup = self.local / 'nas-sync-backup'
            for name, data in desired.items():
                if data == docs.get(name): continue
                if name in docs: atomic_json(backup / name, docs[name])
                atomic_json(self.local / name, data)
            state['observed'] = flatten(desired)
        state['snapshot'] = snapshot
        atomic_json(self.state_path, state)
        self.store.write('device-' + device + '.json', snapshot)
        return {'remote_changes': desired != docs, 'applied': apply, 'records': len(snapshot['records'])}


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(description='Synchronize learning metadata only')
    parser.add_argument('--profile-dir', type=Path, required=True)
    parser.add_argument('--apply', action='store_true', help='Apply received progress; use only before opening study pages')
    args = parser.parse_args(argv)
    config = read_json(args.profile_dir / 'nas-sync-config-v1.json')
    if not config.get('enabled'): raise ValueError('NAS 동기화가 꺼져 있습니다.')
    print(encode(Synchronizer(args.profile_dir,config).synchronize(apply=args.apply)))
    return 0
