"""Build-only mobile data for the same Conda problems and real guest grader.

This exports teaching data, not an Android runtime/support claim. Answers shown
to a learner are separate from the unchanged private grading payload. Do not
reimplement Conda or infer success from this export succeeding.
"""
from copy import deepcopy
import json
from pathlib import Path

from conda_teaching.learning_steps import STEPS


# Authored read-only expressions supplied for interpreting real Python output.
# This is a teaching-display allowlist, NOT a sandbox for untrusted Python.
# Keep exact strings: a prefix check could expose install/activate solutions or
# accidentally treat a compound shell command as a provided diagnostic.
PROVIDED_DIAGNOSTICS = frozenset((
    'python --version',
    'python -c "import sys; print(sys.executable); print(sys.prefix)"',
    'python -c "import training_math; print(training_math.total([2, 5]))"',
    'python -c "import training_text; print(training_text.normalize(\'  draft  \'))"',
    'python -c "import training_math, training_text; print(training_math.total([2, 5])); print(training_text.normalize(\'  draft  \'))"',
    'python -c "import training_math; print(training_math.__version__)"',
    'python -c "import training_math; print(training_math.__version__); print(training_math.mean([2, 8]))"',
    'python -c "import training_math, training_text; print(training_math.mean([2, 8])); print(training_text.normalize(\'  draft  \'))"',
    'python -c "import training_math; print(training_math.mean([2, 8]))"',
    'python -c "import training_math; print(training_math.__version__); print(training_math.__file__)"',
    'python -c "import sys, training_math; print(sys.prefix); print(training_math.__version__); print(training_math.total([2, 5]))"',
    'python -c "import sys, training_math; print(sys.prefix); print(training_math.mean([2, 8]))"',
    'python -c "import training_math; print(training_math.__version__); print(training_math.total([2, 5]))"',
))


def provided_diagnostics(commands):
    supplied = []
    for command in commands:
        if command in PROVIDED_DIAGNOSTICS:
            supplied.append(command)
        elif not command.startswith('conda '):
            raise ValueError('Review new diagnostic before mobile export: ' + command)
    # Preserve repeats: comparison tasks need the expression in each environment.
    return supplied


def mobile_steps(key):
    """Adapt UI instructions only; keep the actual practice commands intact."""
    steps = deepcopy(STEPS[key])
    if key == 'conda_identity':
        steps[0]['explanation'] = (
            '‘실습 시작’을 누르고 상단의 실제 guest ID와 Linux guest 표시를 확인합니다. '
            '이미 열려 있으면 ‘터미널’ 탭으로 돌아갑니다. '
            '아래 정보는 이 guest의 실제 Conda가 알려 주는 값입니다.')
    elif key == 'conda_create':
        steps[0]['observe'] = (
            'sg-analysis가 아직 없는지 확인합니다. 앞서 같은 단계를 실행해 이미 있다면 '
            '무작정 덮어쓰지 말고 다음 확인 단계로 가거나 메뉴의 ‘문제 다시 시작’으로 '
            '이 예시를 다시 시작합니다.')
    return steps


def course_data():
    spec = json.loads(Path(__file__).with_name('course_spec.json').read_text(encoding='utf-8'))
    if spec.get('schema') != 1 or spec.get('kind') != 'conda-course-spec':
        raise ValueError('Unsupported Conda course')
    records = []
    number = 0
    for source in spec['units']:
        review = source['kind'] == 'review'
        if not review:
            number += 1
        steps = mobile_steps(source['key'])
        if not steps:
            raise ValueError('Missing learning sequence: ' + source['key'])
        problems = []
        for problem in source['problems']:
            role = problem['role']
            if role not in ('example', 'application_1', 'application_2'):
                raise ValueError('Unsupported Conda problem role: ' + role)
            fields = [{'key': field['key'], 'label': field['label'],
                       'input': 'boolean' if isinstance(field.get('expected'), bool) else 'text'}
                      for field in problem['answer_fields']]
            problems.append({'id': problem['id'], 'goal': problem['goal'],
                             'hint': problem['hint'], 'answer_fields': fields,
                             'role': role,
                             'example_commands': deepcopy(problem['reference_commands']) if role == 'example' else [],
                             'provided_diagnostics': provided_diagnostics(problem['reference_commands']),
                             'diagnostic_notice': (
                                 '목표에 맞는 환경을 직접 선택한 같은 터미널에서 실행하세요. '
                                 '여러 환경을 비교한다면 각 환경에서 확인합니다. '
                                 '진단식은 설치나 활성화를 대신하지 않습니다.'),
                             'initial_fixture': deepcopy(problem['initial_fixture']),
                             'mission': {'kind': 'conda', 'problem': deepcopy(problem),
                                         'probes': deepcopy(spec['observer_contract']['module_probes'])}})
        records.append({'key': source['key'], 'title': source['title'],
                        'kind': source['kind'], 'topic': 'conda', 'number': number,
                        'prerequisites': deepcopy(source['prerequisites']),
                        'explanation': source['explanation'], 'syntax': deepcopy(source['syntax']),
                        'pitfall': source['pitfall'], 'learning_steps': steps, 'problems': problems})
    return {'schema': 2, 'execution': 'real-guest', 'course': 'conda',
            'status': 'teaching-export-only-runtime-integration-required',
            'runtime_integration': {
                'status': 'not-connected', 'practice_enabled': False,
                'optional_install_enabled': False,
                'notice': '학습 자료 정의입니다. Android 실제 실행 환경 연결·준비 검증 전에는 실습과 채점을 시작할 수 없습니다.',
            },
            'bootstrap': deepcopy(spec['bootstrap']),
            'official_sources': deepcopy(spec['official_sources']),
            'counts': deepcopy(spec['counts']), 'units': records}


def export(destination):
    target = Path(destination)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(course_data(), ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('destination')
    export(parser.parse_args().destination)
