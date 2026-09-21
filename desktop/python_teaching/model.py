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
class GuidedStep:
    """An independent, runnable worked example, not a scored application task."""
    title: str
    explanation: str
    observation: str
    practice: Problem

    @property
    def description(self):
        return (self.explanation + '\n\n직접 해볼 코드\n' + self.practice.solution
                + '\n\n결과 읽기\n' + self.observation
                + '\n\n각 소단계 코드는 독립 실행할 수 있습니다. 값을 바꾸어 다시 실행해 보세요.')


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
    guided_steps: tuple = ()

    @property
    def learning_steps(self):
        if self.guided_steps:
            steps = [(step.title, step.description) for step in self.guided_steps]
            title, description = steps[-1]
            steps[-1] = (title, description + '\n\n단원 정리\n' + self.explanation
                         + '\n\n주의할 점\n' + self.pitfall)
            return tuple(steps)
        return (
            ('개념과 인자', self.explanation + '\n\n기본 형태\n' + self.syntax),
            ('작게 실행하고 해석', self.problems[0].goal + '\n\n직접 해볼 코드\n' + self.problems[0].solution + '\n\n주의할 점\n' + self.pitfall),
        )

    def clamp_step(self, value):
        return min(max(value, 0), len(self.learning_steps)-1) if type(value) is int else 0


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
