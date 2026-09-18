"""Fixture-compatible, sequential learning steps for the real Conda course.

This file does not provision a guest, execute commands, modify course_spec.json,
or grant progress. Start each unit with its example fixture; keep the same Bash
session between steps. Empty command tuples mean inspect the read-only file tab.
Transactions ask the learner to check the real plan and confirm interactively;
the string 'y' is intentionally never supplied as a command.

These are statically audited proposals. The parent integration must replay all
18 sequences in the actual Conda 26.7.1 guest before marking them verified.
"""


STEPS: dict[str, tuple[dict, ...]] = {
    'conda_identity': (
        {
            'title': '실행 장소를 확인하기',
            'explanation': 'F4로 실습을 열고 상단의 실제 guest ID와 Linux guest 표시를 확인합니다. 이미 열려 있으면 F4는 터미널로 돌아가기만 합니다. 아래 정보는 이 guest의 실제 Conda가 알려 주는 값입니다.',
            'commands': ('conda info',),
            'observe': 'platform과 base environment를 찾습니다. 손에 든 기기의 OS와 명령을 실행하는 Linux guest를 구별합니다. base는 보호하는 관리용 설치이므로 바꾸지 않습니다.',
        },
        {
            'title': 'Conda 관리 도구의 버전 읽기',
            'explanation': '--version은 앞에 적은 프로그램의 버전을 묻습니다. 이번에는 Python이 아니라 Conda를 확인합니다.',
            'commands': ('conda --version',),
            'observe': 'Conda 뒤에 나온 버전 문자열을 읽습니다. 예시 단계의 관리 도구 버전 칸에는 이 실제 값을 적으며 미리 정한 숫자를 외우지 않습니다.',
        },
        {
            'title': '설치 장소와 버전 구별하기',
            'explanation': '같은 정보를 다시 읽어도 설치 상태는 바뀌지 않습니다. base environment는 폴더 주소이고 Conda 버전은 프로그램의 버전입니다.',
            'commands': ('conda info',),
            'observe': 'base 경로와 platform을 다시 찾고 방금 읽은 버전과 구별합니다. 앱의 기존 Python 실습 실행기가 작동한다는 사실만으로 새 Conda 환경이 생긴 것은 아닙니다.',
        },
    ),
    'conda_env_list': (
        {
            'title': '준비된 환경 찾기',
            'explanation': '이 예시에는 sg-notes가 실제로 준비되어 있습니다. 목록은 환경의 이름과 경로를 보여 줍니다.',
            'commands': ('conda env list',),
            'observe': 'sg-notes 행과 그 경로를 찾습니다. base와 sg-notes를 같은 환경으로 읽지 않습니다.',
        },
        {
            'title': '존재와 활성을 구별하기',
            'explanation': '환경이 존재하는 것과 지금 선택되어 있는 것은 다릅니다. 이 예시는 활성 환경이 없는 상태로 시작합니다. 다른 목록 명령으로도 확인할 수 있습니다.',
            'commands': ('conda info --envs',),
            'observe': '활성 표시인 별표가 없는지 봅니다. base가 목록에 보인다는 이유만으로 활성이라고 답하지 않습니다.',
        },
        {
            'title': '경로와 현재 상태 정리하기',
            'explanation': '이번 단원은 조사만 합니다. 생성·활성화·삭제 명령을 실행할 필요가 없습니다.',
            'commands': ('conda env list',),
            'observe': 'sg-notes의 실제 경로와 현재 활성 환경 없음이라는 두 정보를 구분합니다. 예시 단계에서 각각의 답칸에 옮길 수 있어야 합니다.',
        },
    ),
    'conda_create': (
        {
            'title': '새 이름이 아직 없는지 확인하기',
            'explanation': '이 예시의 새 환경 이름은 sg-analysis입니다. 준비된 학습 환경이 없다는 안내는 정상이며 생성할 대상이 아직 없다는 뜻입니다.',
            'commands': ('conda env list',),
            'observe': 'sg-analysis가 아직 없는지 확인합니다. 앞서 같은 단계를 실행해 이미 있다면 무작정 덮어쓰지 말고 다음 확인 단계로 가거나 F2로 이 예시를 다시 시작합니다.',
        },
        {
            'title': 'Python 3.12 계열 환경 만들기',
            'explanation': '--name은 새 이름, python=3.12는 Python 계열, --offline은 인터넷을 쓰지 않는 옵션입니다. 실제 계획의 대상이 sg-analysis인지 읽고 문제가 없을 때 확인 질문에 y로 응답합니다.',
            'commands': ('conda create --name sg-analysis python=3.12 --offline',),
            'observe': '설치가 실제로 완료되는지 확인합니다. Python의 자동 의존 패키지가 함께 설치되는 것은 정상이며 계획 출력만 나온 상태와 완료를 구별합니다.',
        },
        {
            'title': '생성과 활성화의 차이 확인하기',
            'explanation': '생성만으로 현재 환경이 바뀌지는 않습니다. 아직 배우지 않은 활성화 명령을 추가하지 않고 목록으로 결과를 확인합니다.',
            'commands': ('conda env list',),
            'observe': 'sg-analysis가 새로 존재하지만 활성 별표는 없는지 확인합니다. 이 예시의 마지막 상태는 활성 환경 없음입니다.',
        },
    ),
    'conda_activate': (
        {
            'title': '준비된 작업 환경 선택하기',
            'explanation': '이미 존재하는 sg-work를 현재 Bash에서 선택합니다. 새 환경을 만들거나 다른 터미널을 열 필요가 없습니다.',
            'commands': ('conda activate sg-work', 'conda env list'),
            'observe': 'sg-work에 활성 표시가 붙었는지 확인합니다. 이름을 화면에 출력하는 것과 실제 활성화는 다릅니다.',
        },
        {
            'title': '활성화 직전 상태로 돌아가기',
            'explanation': 'deactivate는 가장 최근 활성화 직전 상태로 돌아갑니다. 이 예시는 비활성에서 sg-work를 한 번 활성화했으므로 한 번 해제하면 비활성입니다. 환경을 삭제하는 명령이 아닙니다.',
            'commands': ('conda deactivate', 'conda env list'),
            'observe': 'sg-work는 목록에 남아 있지만 활성 별표는 사라졌는지 확인합니다. A에서 B로 연속 활성화한 경우라면 해제 한 번은 A로 돌아가므로 언제나 전체 해제를 뜻하지는 않습니다.',
        },
        {
            'title': '예시의 목표 상태로 다시 선택하기',
            'explanation': '이번 예시의 최종 목표는 sg-work를 활성으로 남기는 것입니다. 방금 해제를 연습했으므로 다시 선택합니다.',
            'commands': ('conda activate sg-work', 'conda env list'),
            'observe': '최종 활성 환경이 sg-work이고 그 설치 상태는 그대로인지 확인합니다.',
        },
    ),
    'conda_interpreter': (
        {
            'title': 'Python을 확인할 환경 선택하기',
            'explanation': '이 예시는 sg-code가 존재하지만 아직 활성은 아닙니다. Python을 실행하기 전에 이 환경을 선택합니다.',
            'commands': ('conda activate sg-code', 'conda env list'),
            'observe': '활성 표시가 sg-code에 붙었는지 확인합니다. 비활성 상태의 python 결과를 목표 환경의 결과로 오해하지 않습니다.',
        },
        {
            'title': '실행된 Python 버전 읽기',
            'explanation': 'python --version은 Conda가 아니라 실행된 Python의 버전입니다. 이번 목표는 3.12 계열이며 정확한 patch 숫자는 외우지 않습니다.',
            'commands': ('python --version',),
            'observe': '출력이 Python 3.12 계열인지 읽습니다. 같은 버전이 다른 환경에도 있을 수 있으므로 이것만으로 소속을 확정하지 않습니다.',
        },
        {
            'title': '실제 실행 파일과 소속 경로 확인하기',
            'explanation': '-c는 제공한 짧은 Python 코드를 실행합니다. 첫 줄은 실행 파일, 둘째 줄은 그 Python의 환경 경로입니다. 진단식을 그대로 실행해도 됩니다.',
            'commands': ('python -c "import sys; print(sys.executable); print(sys.prefix)"',),
            'observe': 'sys.prefix가 sg-code의 환경 경로와 일치하는지 확인합니다. 실행 파일 경로와 환경 경로를 각각 읽어 예시의 두 답칸에 구분하여 옮깁니다.',
        },
    ),
    'review_conda_01': (
        {
            'title': '보존할 환경과 새 환경 구별하기',
            'explanation': 'sg-notebook은 이미 존재하고 활성입니다. 새로 만들 대상은 sg-lab이며 기존 환경은 보존합니다. 새 명령은 없습니다.',
            'commands': ('conda env list',),
            'observe': 'sg-notebook의 활성 표시와 sg-lab의 부재를 확인합니다.',
        },
        {
            'title': '새 실험 환경 준비하기',
            'explanation': 'sg-lab에 Python 3.12 계열을 만듭니다. 실제 설치 계획이 새 환경을 대상으로 하는지 확인하고 승인 질문에 y로 응답합니다.',
            'commands': ('conda create -n sg-lab python=3.12 --offline',),
            'observe': '생성이 완료되어도 현재 sg-notebook의 선택은 자동으로 바뀌지 않는다는 점을 확인합니다.',
        },
        {
            'title': '선택한 환경과 실행된 Python 연결하기',
            'explanation': '새 환경으로 전환하고 제공된 Python 진단식을 실행합니다. 현재 선택과 실제 실행 장소가 같아야 합니다.',
            'commands': ('conda activate sg-lab', 'python -c "import sys; print(sys.executable); print(sys.prefix)"', 'conda env list'),
            'observe': 'sg-lab이 활성이고 Python 경로도 sg-lab에 속하며 sg-notebook은 목록에 남아 있는지 봅니다. 지금 해제하면 이전 sg-notebook으로 돌아갑니다.',
        },
    ),
    'conda_package_list': (
        {
            'title': '어느 환경을 조사하는지 확인하기',
            'explanation': '이 예시에서는 sg-calc가 이미 활성입니다. 환경 목록은 환경의 존재와 현재 선택을 보여 줍니다.',
            'commands': ('conda env list',),
            'observe': '조사 대상이 sg-calc인지 확인합니다. 다음 단계의 패키지 목록과 지금의 환경 목록은 서로 다릅니다.',
        },
        {
            'title': '현재 환경의 패키지 읽기',
            'explanation': 'conda list는 현재 환경의 설치된 패키지를 나열합니다. Name과 Version 열을 구별합니다.',
            'commands': ('conda list',),
            'observe': 'training-math의 설치 버전을 찾습니다. Python과 Conda의 버전, 채널에 있는 최신 버전과 혼동하지 않습니다.',
        },
        {
            'title': '대상을 명시해서 다시 조사하기',
            'explanation': '--name으로 같은 sg-calc를 지정하면 현재 환경 선택에 의존하지 않고 조사할 수 있습니다. 설치 상태는 바꾸지 않습니다.',
            'commands': ('conda list --name sg-calc',),
            'observe': '앞 단계와 같은 실제 설치 버전이 보이는지 확인합니다. 예시 답칸에는 해당 행에서 읽은 버전을 적습니다.',
        },
    ),
    'conda_install': (
        {
            'title': '추가 전 설치 상태 조사하기',
            'explanation': 'sg-sum에는 Python이 준비되어 있고 계산 도구는 아직 없습니다. 먼저 대상 환경의 목록을 봅니다.',
            'commands': ('conda list --name sg-sum',),
            'observe': 'Python은 있지만 training-math는 없는지 확인합니다. 패키지가 채널에 있다는 사실과 설치되었다는 사실은 다릅니다.',
        },
        {
            'title': '계산 도구 추가하기',
            'explanation': '설치 대상을 sg-sum으로 명시합니다. 실제 계획의 환경과 패키지를 확인한 뒤 승인 질문에 y로 응답합니다.',
            'commands': ('conda install --name sg-sum training-math --offline',),
            'observe': '설치가 실제로 완료되는지 봅니다. 이번에는 특정 버전 암기보다 패키지가 대상 환경에 준비되었는지가 중요합니다.',
        },
        {
            'title': '설치한 환경에서 실제로 사용하기',
            'explanation': '설치와 import는 다릅니다. sg-sum을 선택하고 제공된 진단식으로 계산 도구를 사용합니다.',
            'commands': ('conda activate sg-sum', 'python -c "import training_math; print(training_math.total([2, 5]))"'),
            'observe': '2와 5의 합 7이 출력되는지 확인합니다. 설치 이름 training-math와 import 이름 training_math의 표기가 다릅니다.',
        },
    ),
    'conda_versions': (
        {
            'title': '이번 설치의 버전 요청하기',
            'explanation': 'sg-classic에 계산 도구의 정확한 1.0 버전을 요청합니다. ==1.0은 이번 설치 조건이지 이후 변경을 영구히 금지하는 설정은 아닙니다. 계획을 확인한 뒤 y로 승인합니다.',
            'commands': ('conda install -n sg-classic training-math==1.0 --offline',),
            'observe': '계획의 대상이 sg-classic이고 요청 버전이 1.0인지 읽고 실제 완료까지 확인합니다.',
        },
        {
            'title': '실제 설치된 버전 확인하기',
            'explanation': '요청한 문자열이 아니라 설치 목록을 읽습니다. 대상을 명시한 목록 확인은 활성화 없이도 가능합니다.',
            'commands': ('conda list -n sg-classic',),
            'observe': 'training-math 행의 Version이 1.0인지 확인합니다.',
        },
        {
            'title': '모듈이 보고하는 버전과 비교하기',
            'explanation': '이 예시는 처음에 비활성이므로 Python 진단 전 sg-classic을 선택해야 합니다. __version__은 이 교육 패키지가 제공하는 실제 버전 문자열입니다.',
            'commands': ('conda activate sg-classic', 'python -c "import training_math; print(training_math.__version__)"'),
            'observe': '실제 모듈 버전과 패키지 목록의 버전이 1.0으로 일치하는지 봅니다. 다른 환경의 Python을 실행하지 않습니다.',
        },
    ),
    'conda_update': (
        {
            'title': '업데이트 전 상태 읽기',
            'explanation': 'sg-average는 이미 활성이고 training-math 1.0이 설치되어 있습니다. 현재 상태를 먼저 확인합니다.',
            'commands': ('conda list -n sg-average',),
            'observe': '계산 도구의 현재 버전이 1.0인지 봅니다. 이때는 아직 1.1의 mean 기능을 확인할 단계가 아닙니다.',
        },
        {
            'title': '선택한 패키지만 갱신하기',
            'explanation': 'sg-average의 계산 도구만 호환되는 최신 버전으로 요청합니다. 실제 변경 계획을 읽고 y로 승인합니다. 관리용 base나 Conda 자체를 갱신하지 않습니다.',
            'commands': ('conda update -n sg-average training-math --offline',),
            'observe': '동결된 이 교육 채널에서는 계산 도구 1.1이 대상입니다. 인터넷 전체의 최신 버전이라는 뜻이 아닙니다.',
        },
        {
            'title': '새 버전의 기능 실행하기',
            'explanation': '같은 활성 환경의 Python에서 새 버전과 추가된 평균 기능을 확인합니다.',
            'commands': ('python -c "import training_math; print(training_math.__version__); print(training_math.mean([2, 8]))"',),
            'observe': '버전 1.1과 평균 5.0이 실제로 출력되는지 확인합니다. 숫자를 직접 출력하는 것과 새 함수를 실행하는 것은 다릅니다.',
        },
    ),
    'conda_remove_package': (
        {
            'title': '뺄 도구와 남길 도구 정하기',
            'explanation': 'sg-clean은 활성 상태이며 계산 도구 1.1과 문장 도구 1.0이 있습니다. 이번에는 문장 도구만 제거합니다.',
            'commands': ('conda list -n sg-clean',),
            'observe': '제거할 training-text와 보존할 training-math·Python을 구별합니다.',
        },
        {
            'title': '패키지 하나만 제거하기',
            'explanation': '계획의 대상과 제거 목록을 확인한 뒤 y로 승인합니다. remove에 패키지 이름을 주는 작업이며 환경 전체 제거가 아닙니다.',
            'commands': ('conda remove -n sg-clean training-text --offline',),
            'observe': '문장 도구가 제거되고 환경 자체는 남아 있어야 합니다. --all을 덧붙이지 않습니다.',
        },
        {
            'title': '남은 도구의 동작 확인하기',
            'explanation': '목록에서 제거 결과를 보고 같은 환경의 Python과 계산 도구도 확인합니다.',
            'commands': ('conda list -n sg-clean', 'python --version', 'python -c "import training_math; print(training_math.total([2, 5]))"'),
            'observe': 'training-text는 없고 training-math 1.1과 Python 3.12 계열은 남아 있으며 합계 7이 실행되는지 확인합니다.',
        },
    ),
    'review_conda_02': (
        {
            'title': '현재와 목표의 차이 읽기',
            'explanation': '활성 환경 sg-analysis에는 계산 도구 1.0과 문장 도구가 있습니다. 목표는 평균 계산 기능을 가진 계산 전용 환경입니다.',
            'commands': ('conda list -n sg-analysis',),
            'observe': '갱신할 계산 도구와 제거할 문장 도구를 나누어 생각합니다.',
        },
        {
            'title': '필요한 변경 두 가지 수행하기',
            'explanation': '첫 명령은 계산 도구 갱신, 둘째 명령은 문장 도구 제거입니다. 각각의 실제 계획을 확인하고 각 승인 질문에 y로 응답합니다.',
            'commands': ('conda update -n sg-analysis training-math --offline', 'conda remove -n sg-analysis training-text --offline'),
            'observe': '두 작업의 대상은 모두 sg-analysis입니다. 패키지 변경을 위해 환경 전체를 지울 필요는 없습니다.',
        },
        {
            'title': '정리된 환경을 실제로 사용하기',
            'explanation': '목록과 실제 함수 실행을 함께 봅니다. 새 명령 없이 앞의 다섯 단원을 연결합니다.',
            'commands': ('conda list -n sg-analysis', 'python -c "import training_math; print(training_math.mean([2, 8]))"'),
            'observe': '계산 도구 1.1이 있고 문장 도구는 없으며 평균 5.0이 실행되는지 확인합니다.',
        },
    ),
    'conda_isolation': (
        {
            'title': '두 환경의 시작 상태 비교하기',
            'explanation': '실제 환경 이름은 sg-reference와 sg-research입니다. 둘 다 계산 도구 1.0으로 준비되었으며 현재는 비활성입니다.',
            'commands': ('conda list -n sg-reference', 'conda list -n sg-research'),
            'observe': '두 환경의 계산 도구 버전이 같아도 서로 다른 설치 공간임을 구별합니다.',
        },
        {
            'title': '실험 환경만 변경하기',
            'explanation': 'sg-reference는 보존하고 sg-research만 갱신합니다. 실제 계획이 실험 환경을 대상으로 하는지 확인한 뒤 y로 승인합니다.',
            'commands': ('conda update -n sg-research training-math --offline',),
            'observe': '원본 환경을 변경하는 작업이 아닙니다. 실험 환경의 목표 버전은 이 채널의 1.1입니다.',
        },
        {
            'title': '각 환경의 모듈 소속 확인하기',
            'explanation': '각 환경을 선택한 뒤 같은 모듈 이름의 버전과 __file__을 확인합니다. 두 번째 활성화 이후에는 sg-research가 현재 환경이며, 한 번 해제하면 이전 sg-reference로 돌아갑니다.',
            'commands': ('conda activate sg-reference', 'python -c "import training_math; print(training_math.__version__); print(training_math.__file__)"', 'conda activate sg-research', 'python -c "import training_math; print(training_math.__version__); print(training_math.__file__)"'),
            'observe': '각각 1.0과 1.1이 나오고 모듈 경로도 각각의 환경에 속하는지 봅니다. 한 환경의 변경이 다른 환경에 자동 적용되지 않습니다.',
        },
    ),
    'conda_export_intent': (
        {
            'title': '원본과 저장 폴더 확인하기',
            'explanation': '원본은 sg-share이고 share 폴더가 이미 준비되어 있습니다. 파일 탭에서 폴더를 확인합니다. 새 디렉터리를 만드는 명령은 필요 없습니다.',
            'commands': ('conda list -n sg-share',),
            'observe': '전체 설치 목록에는 자동 의존 패키지도 포함됩니다. 다음 단계에서는 직접 요청한 조건만 따로 저장합니다.',
        },
        {
            'title': '직접 요청 기록 내보내기',
            'explanation': '--from-history는 직접 요청한 조건을, --file은 저장할 파일을 지정합니다. 이번 예시에 배정된 새 파일만 사용합니다.',
            'commands': ('conda env export -n sg-share --from-history --file share/environment.yml',),
            'observe': '정상 내보내기는 터미널에 긴 결과를 출력하지 않을 수 있습니다. 파일 탭에서 새로고침하여 실제 파일을 확인합니다.',
        },
        {
            'title': '파일 내용과 설치를 구별하기',
            'explanation': '읽기 전용 파일 탭에서 share/environment.yml을 선택합니다. name·channels·dependencies를 읽습니다. 추가 터미널 명령은 필요 없습니다.',
            'commands': (),
            'observe': '원본 이름과 Python·계산 도구 요청을 확인합니다. Conda가 ==1.0 요청을 =1.0으로 내보내는 것은 이 설치본의 정상 정규화이며 글자 수만 비교하지 않습니다. 이 파일 저장만으로 새 환경이 생성된 것은 아닙니다.',
        },
    ),
    'conda_recreate': (
        {
            'title': '제공된 요청 파일 읽기',
            'explanation': '파일 탭에 이미 준비된 share/environment.yml을 읽습니다. 이것은 sg-source에서 실제로 내보낸 파일입니다. 파일을 고치거나 다시 만들지 않습니다.',
            'commands': ('conda env list',),
            'observe': 'sg-source는 있고 새 이름 sg-rebuilt는 없는지 확인합니다. 파일의 원본 이름과 이번에 새로 만들 이름은 다릅니다.',
        },
        {
            'title': '새 이름으로 재구성하기',
            'explanation': '제공 파일의 요구를 읽어 sg-rebuilt를 만듭니다. 실제 계획이 원본이 아니라 새 경로를 대상으로 하는지 확인하고 승인 질문에 y로 응답합니다.',
            'commands': ('conda env create -n sg-rebuilt --file share/environment.yml --offline',),
            'observe': '파일 속 원본 name/prefix 때문에 sg-source를 덮어쓰지 않아야 합니다. 같은 guest의 오프라인 채널에서 실제 생성이 끝나는지 확인합니다.',
        },
        {
            'title': '재구성한 환경의 Python 확인하기',
            'explanation': '새 환경을 선택하고 그 Python과 계산 도구를 실제로 실행합니다.',
            'commands': ('conda activate sg-rebuilt', 'python -c "import sys, training_math; print(sys.prefix); print(training_math.__version__); print(training_math.total([2, 5]))"'),
            'observe': '새 환경 경로, 계산 도구 1.0, 합계 7을 확인합니다. 파일 존재나 환경 이름만으로 재구성 성공을 판단하지 않습니다.',
        },
    ),
    'conda_export_snapshot': (
        {
            'title': '간결한 요청 기록 만들기',
            'explanation': '원본은 sg-capture이고 intent 폴더가 준비되어 있습니다. 직접 요청한 조건을 이 폴더의 환경 파일에 저장합니다.',
            'commands': ('conda env export -n sg-capture --from-history --file intent/environment.yml',),
            'observe': '파일 탭에서 요청 기록이 만들어졌는지 확인합니다. 이 예시에는 새 환경 생성 대상이 배정되어 있지 않습니다.',
        },
        {
            'title': '전체 설치 기록 만들기',
            'explanation': '같은 원본에서 --from-history를 빼면 전체 설치 기록을 얻습니다. 준비된 full 폴더를 사용하여 앞 파일을 덮어쓰지 않습니다.',
            'commands': ('conda env export -n sg-capture --file full/environment.yml',),
            'observe': 'full/environment.yml의 실제 의존 패키지 버전·빌드 정보를 봅니다. 파일 이름이 아니라 내용을 비교합니다.',
        },
        {
            'title': '두 기록의 목적 비교하기',
            'explanation': '읽기 전용 파일 탭에서 intent/environment.yml과 full/environment.yml을 번갈아 읽습니다. 전체 기록으로 새 환경을 재구성하는 연습은 이 단원의 활용 1에서 배정된 별도 fixture로 이어갑니다.',
            'commands': (),
            'observe': '요청 조건과 구체적 설치 결과의 차이를 설명해 봅니다. 전체 YAML이 모든 OS/CPU에서 무조건 성공하는 잠금 파일은 아닙니다. 지금은 파일 두 개와 원본 보존까지만 수행합니다.',
        },
    ),
    'conda_remove_environment': (
        {
            'title': '삭제 대상과 보존 대상을 확인하기',
            'explanation': 'sg-finished는 현재 활성이고 정리할 대상입니다. sg-keep은 보존할 다른 환경입니다.',
            'commands': ('conda env list',),
            'observe': '두 이름을 구별하고 현재 활성 표시가 sg-finished에 있는지 봅니다.',
        },
        {
            'title': '삭제할 환경에서 먼저 벗어나기',
            'explanation': '이 예시는 비활성에서 sg-finished 하나만 활성화한 상태로 준비되었습니다. 한 번 해제한 뒤 실제 현재 상태를 다시 확인합니다.',
            'commands': ('conda deactivate', 'conda env list'),
            'observe': 'sg-finished는 아직 존재하지만 현재 활성 환경은 없어야 합니다. 해제는 삭제가 아닙니다.',
        },
        {
            'title': '정확한 환경만 제거하기',
            'explanation': '실제 제거 계획에서 sg-finished가 대상인지 확인하고 승인 질문에 y로 응답합니다. Conda 26.7.1의 env remove에는 --offline을 덧붙이지 않습니다. 이 guest 자체는 오프라인으로 설정되어 있습니다.',
            'commands': ('conda env remove --name sg-finished', 'conda env list'),
            'observe': 'sg-finished는 환경 목록에서 사라지고 sg-keep은 남았으며 최종 활성 환경은 없는지 확인합니다. 남은 사용자 폴더를 손으로 재귀 삭제하지 않습니다.',
        },
    ),
    'review_conda_03': (
        {
            'title': '보존할 원본의 요청 기록 만들기',
            'explanation': 'sg-source는 계산 도구 1.0 상태로 보존합니다. share 폴더에 요청 파일을 만들고 파일 탭에서 내용을 읽습니다.',
            'commands': ('conda env export -n sg-source --from-history --file share/environment.yml',),
            'observe': '원본 이름과 Python·계산 도구 요청을 확인합니다. 새로 만들 환경은 sg-copy이며 정리할 별도 임시 환경은 sg-obsolete입니다.',
        },
        {
            'title': '복사본만 재구성하고 확장하기',
            'explanation': '파일로 sg-copy를 만든 뒤 복사본에만 문장 도구를 추가합니다. 생성과 설치의 실제 계획을 각각 확인하고 각 승인 질문에 y로 응답합니다. 완료 후 복사본을 선택하여 두 도구를 실행합니다.',
            'commands': ('conda env create -n sg-copy --file share/environment.yml --offline', 'conda install -n sg-copy training-text --offline', 'conda activate sg-copy', 'python -c "import training_math, training_text; print(training_math.total([2, 5])); print(training_text.normalize(\'  draft  \'))"'),
            'observe': '합계 7과 정리된 문자열 DRAFT가 출력되는지 봅니다. 문장 도구를 원본 sg-source에 설치하지 않습니다.',
        },
        {
            'title': '분리 상태를 확인하고 임시 환경 정리하기',
            'explanation': '두 환경의 목록을 비교한 뒤 sg-obsolete만 제거합니다. 실제 제거 대상과 계획을 확인하고 승인 질문에 y로 응답합니다. 현재 sg-copy와 원본은 보존합니다.',
            'commands': ('conda list -n sg-source', 'conda list -n sg-copy', 'conda env remove -n sg-obsolete', 'conda env list'),
            'observe': '원본은 계산 도구 1.0만, 복사본은 계산 도구 1.0과 문장 도구를 갖는지 확인합니다. sg-obsolete만 사라지고 공유 파일과 두 환경이 남아야 합니다.',
        },
    ),
}
