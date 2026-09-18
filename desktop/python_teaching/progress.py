"""Learning metadata only. Never serialize a Python namespace or source input."""
import json
from pathlib import Path


class PythonProgress:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {'schema': 1, 'completed': [], 'passed': [], 'learning': {}, 'quiz': {}, 'positions':{}, 'concept_positions':{}, 'setup_completed':[]}
        self.error = ''
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(data, dict): raise ValueError('진도 형식 오류')
            for key, default in self.data.items():
                if key in data and not isinstance(data[key], type(default)): raise ValueError('진도 항목 형식 오류: ' + key)
            self.data.update(data)
            if not isinstance(self.data.get('resume',{}),dict): raise ValueError('재개 위치 형식 오류')
        except FileNotFoundError: pass
        except (OSError, ValueError) as exc: self.error = str(exc)

    def save(self):
        if self.error: raise OSError('기존 진도를 읽지 못해 덮어쓰지 않습니다: ' + self.error)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temp = self.path.with_suffix('.tmp')
        temp.write_text(json.dumps(self.data, ensure_ascii=False), encoding='utf-8')
        temp.replace(self.path)

    def resume(self, key, phase, step):
        self.data['resume'] = {'unit': key, 'phase': phase, 'step': step}
        self.data['positions'][key] = {'phase':phase, 'step':step}
        if phase == 'learn': self.data['learning'][key] = step
        self.save()

    def passed(self, key, variant):
        identity = f'{key}:{variant}'
        if identity not in self.data['passed']: self.data['passed'].append(identity)
        if all(f'{key}:{v}' in self.data['passed'] for v in (1,2)) and key not in self.data['completed']:
            self.data['completed'].append(key)
        self.save()
