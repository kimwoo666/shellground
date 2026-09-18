"""Independent concept results, never Linux/Python practical completion."""
import json
from pathlib import Path


class ConceptProgress:
    def __init__(self, path):
        self.path = Path(path)
        self.data = {'schema': 1, 'quiz': {}, 'positions': {}}
        self.error = ''
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(value, dict) or type(value.get('schema')) is not int or value['schema'] != 1:
                raise ValueError('지원하지 않는 개념 진도 형식')
            if not isinstance(value.get('quiz'), dict) or not isinstance(value.get('positions'), dict):
                raise ValueError('개념 진도 항목 형식 오류')
            for record in value['quiz'].values():
                if (not isinstance(record, dict) or type(record.get('attempts')) is not int or
                        record['attempts'] < 0 or type(record.get('passed')) is not bool):
                    raise ValueError('개념 평가 기록 형식 오류')
            for key, position in value['positions'].items():
                if key not in ('linux', 'docker') or not isinstance(position, dict):
                    raise ValueError('개념 위치 형식 오류')
                if not isinstance(position.get('question'), str) or not isinstance(position.get('card'), str):
                    raise ValueError('개념 위치 식별자 오류')
            self.data = value
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as exc:
            self.error = str(exc)

    def save(self):
        if self.error:
            raise OSError('기존 개념 진도를 덮어쓰지 않습니다: ' + self.error)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.path.with_suffix('.tmp')
        temporary.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
        temporary.replace(self.path)

    def position(self, topic, question, card):
        self.data['positions'][topic] = {'question': question, 'card': card}
        self.save()

    def grade(self, question, passed):
        old = self.data['quiz'].get(question, {})
        self.data['quiz'][question] = {'attempts': old.get('attempts', 0) + 1,
                                     'passed': passed or old.get('passed', False)}
        self.save()
