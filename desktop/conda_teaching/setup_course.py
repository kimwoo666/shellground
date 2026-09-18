"""Progressive installation teaching; actual paths arrive from the Linux guest."""
import shlex

KEY = 'conda_install_once'
TITLES = ('Anaconda·Miniconda·Conda 구분', '설치 파일과 새 경로',
          '설치 명령의 두 옵션', '새 설치의 Python 확인')


def steps(ready=None):
    target = ready['prefix'] if ready else '<실습을 열면 새 설치 경로가 표시됩니다>'
    installer = ready['installer']['path'] if ready else '<검증된 설치 파일>'
    q = shlex.quote
    return [
        dict(title=TITLES[0], explanation=(
            'Anaconda와 Miniconda는 Python·Conda를 설치하는 배포판입니다. Conda는 그 안에서 환경과 패키지를 관리하는 도구입니다. '
            'Miniconda는 작은 구성으로 시작하므로 여기서는 두 배포판을 반복 설치하지 않고 Miniconda로 배웁니다.\n\n'
            'Python은 코드를 실행하고, 편집기는 코드를 쓰며, Jupyter는 셀 단위로 실행합니다. 설치했다고 모든 프로그램의 Python이 자동으로 바뀌지는 않습니다.\n\n'
            '지금 터미널은 앱 전용 Linux입니다. PC가 Windows여도 여기서 받는 파일은 Linux용입니다. 개인 PC에 직접 설치할 때는 그 PC의 OS·CPU에 맞는 파일을 선택해야 합니다.'),
            commands=['uname -s', 'uname -m'], observe='Linux와 guest CPU 아키텍처를 확인하세요. 설치 파일 이름의 Linux·x86_64 또는 aarch64와 연결합니다.'),
        dict(title=TITLES[1], explanation=(
            '공식 출처와 SHA-256 검증을 통과한 파일만 제공합니다. 다운로드와 설치는 다릅니다. 파일을 받았다고 Python이 설치된 것은 아닙니다.\n\n'
            '설치할 위치(prefix)는 새 폴더여야 합니다. 미리 mkdir로 만들지 않습니다. 기존 관리용 /opt/shellground/miniconda는 건드리지 않습니다.\n'
            '이번 새 설치 경로: '+target+'\n\n'
            '설치 파일에 포함된 라이선스를 「설치 파일·라이선스」에서 읽으세요. 일괄 설치는 약관을 확인하고 동의한 경우에만 선택합니다. 앱은 대신 설치하거나 동의하지 않습니다.'),
            commands=(['sha256sum '+q(installer), 'ls -ld '+q(target)] if ready else []),
            observe='해시를 제공된 검증값과 대조합니다. 새 경로의 ls가 No such file or directory인 것은 이 단계에서는 정상입니다.'),
        dict(title=TITLES[2], explanation=(
            'bash 설치파일은 실제 설치 스크립트를 실행합니다. -b는 질문 없는 일괄 설치이며 라이선스에 동의했다는 전제입니다. '
            '-p 뒤에는 새 설치 경로를 한 개 줍니다. 옵션을 Python 코드 입력창에 쓰는 것이 아니라 아래 Bash 터미널에서 실행합니다.\n\n'
            '동의하지 않으면 실행하지 않고 다른 단원으로 이동할 수 있습니다. 직접 약관을 보며 대화형으로 설치하려면 -b를 빼고, 마지막 셸 초기화 질문에는 no를 선택합니다. '
            'conda init은 셸 시작 파일을 바꾸므로 이 실습에서는 사용하지 않습니다.\n\n'
            '파일 추출이 끝나 프롬프트가 돌아올 때까지 기다립니다. 같은 경로에 설치를 반복하거나 -f/-u로 덮어쓰지 마세요. '
            '중단된 설치를 새로 해보려면 다시 시작으로 별도 새 경로를 받습니다.'),
            commands=([f'bash {q(installer)} -b -p {q(target)}'] if ready else []),
            observe='새 설치가 생기는지 확인합니다. 완료 문구만으로 채점하지 않으며, 실제 실행 결과를 다음 단계에서 확인합니다.'),
        dict(title=TITLES[3], explanation=(
            '기존 conda --version만 실행하면 관리용 Conda를 확인할 수 있습니다. 반드시 이번에 설치한 경로의 실행 파일을 지정하세요.\n\n'
            'conda info의 base environment(root_prefix)는 새 설치 위치여야 합니다. sys.executable은 지금 실행한 Python 파일, sys.prefix는 그 Python이 속한 환경입니다. '
            '셸 PATH에 새 경로를 등록하지 않아도 전체 경로를 지정하면 실행할 수 있습니다.\n\n'
            '이 설치는 앱의 임시 실습 디스크에 있습니다. 완료 진도는 자동 저장하지만 설치 파일·입력 기록 자체는 앱 종료 또는 일반 단원의 실습 초기화 후 유지하지 않습니다.'),
            commands=([q(target+'/bin/conda')+' --version', q(target+'/bin/conda')+' info --json',
                q(target+'/bin/python')+' -c "import sys; print(sys.executable); print(sys.prefix)"'] if ready else []),
            observe='새 Conda와 Python이 모두 이번 경로를 사용해야 합니다. 기존 base가 유지되었는지도 채점합니다.'),
    ]


def goal(ready=None):
    target = ready['prefix'] if ready else '실습을 열면 배정되는 새 경로'
    return ('제공된 공식 Miniconda 설치 파일을 '+target+'에 설치하고, 그 경로의 Conda와 Python이 동작하도록 만드세요. '
            '관리용 base와 셸 시작 설정은 유지하세요. 이미 설치를 끝냈다면 다시 설치하지 않아도 됩니다.')
