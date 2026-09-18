"""Serializable, UI-independent teaching contract shared by desktop/mobile."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Problem:
    goal: str
    initial: str
    solution: str
    checks: tuple
    files: dict = field(default_factory=dict)
    starter: str = ''
    probes: dict = field(default_factory=dict)
    # A lesson may prepare observation helpers which are not learner tasks.
    # Keep actual setup intact while showing only the documented input data.
    display_initial: str | None = None

    @property
    def prepared_code(self):
        return self.initial if self.display_initial is None else self.display_initial

    @property
    def targets(self): return tuple(dict.fromkeys(c['target'] for c in self.checks))


@dataclass(frozen=True)
class Lesson:
    key: str
    topic: str
    title: str
    explanation: str
    syntax: str
    pitfall: str
    source: str
    pages: tuple
    problems: tuple
    prerequisites: tuple = ()
    provenance_note: str = ''

    @property
    def learning_steps(self):
        return (
            ('개념과 인자', self.explanation + '\n\n기본 형태\n' + self.syntax),
            ('작게 실행하고 해석', self.problems[0].goal + '\n\n직접 해볼 코드\n' + self.problems[0].solution + '\n\n주의할 점\n' + self.pitfall),
        )


def check(target, expected, path=(), label=None, feedback=None):
    return {'target': target, 'expected': expected, 'path': list(path),
            'label': label or target + ' 결과',
            'feedback': feedback or '목표 값과 형태·축·라벨을 다시 확인하세요.'}


def array(name, data, shape, dtype=None):
    checks = [check(name, 'array', ['kind'], name + ' 배열 형식'),
              check(name, data, ['data'], name + ' 원소 값'),
              check(name, list(shape), ['shape'], name + ' shape')]
    if dtype: checks.append(check(name, dtype, ['dtype'], name + ' dtype'))
    return tuple(checks)


def frame(name, data, index, columns):
    return (check(name, 'frame', ['kind'], name + ' DataFrame'),
            check(name, data, ['data'], name + ' 셀 값'),
            check(name, index, ['index'], name + ' 행 라벨'),
            check(name, columns, ['columns'], name + ' 열 라벨'))


def series(name, data, index):
    return (check(name, 'series', ['kind']), check(name, data, ['data'], name + ' 값'),
            check(name, index, ['index'], name + ' 라벨'))


def problem(goal, initial, solution, checks, **kwargs):
    return Problem(goal, initial, solution, tuple(checks), **kwargs)
