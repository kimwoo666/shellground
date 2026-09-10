# 개발 및 빌드

## 구성

| 파일 | 역할 |
| --- | --- |
| `desktop/native_app.py` | Qt 네이티브 화면, 학습 단계, 진도 저장 |
| `desktop/terminal_widget.py` | PTY 바이트를 ANSI/VT 화면으로 표시, 키 입력 전달 |
| `desktop/engine.py` | Docker 이미지 확인·빌드, 실습 컨테이너 수명과 통신 |
| `desktop/missions.py` | 단원, 무작위 경로와 목표 생성 |
| `desktop/lab/bridge.py` | Linux PTY와 bash 실행, 표준 입출력 전송 |
| `desktop/lab/lab.py` | 실습 파일 준비, 내부 HTTP 서버, 실제 결과 채점 |
| `desktop/lab/Dockerfile` | Ubuntu 24.04 실습 이미지 |

공개 소스에는 예전 웹 앱·GTK 문자열 시뮬레이터, 개인 절대 경로가 든 바로가기, 가상환경, 빌드 캐시, 진도 파일을 포함하지 않습니다.

## Linux 테스트

저장소 루트에서 다음을 실행합니다. Docker 통합 검사는 Docker를 실행하고 현재 사용자로 접근 가능한 상태에서 수행하세요.

```sh
cd desktop
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
docker build -t shellground-lab:3 lab
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest test_real_lab test_native_ui -v
```

환경에 따라 Qt 시스템 라이브러리가 필요합니다. Ubuntu에서는 `libxcb-cursor0`와 `python3-venv` 설치를 확인하세요. 통합 검사는 앱 전용 라벨의 임시 컨테이너를 만들고 정리합니다. 준비된 Docker 이미지는 남습니다.

Docker 없이 기본 검사만 하려면:

```sh
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest test_real_lab test_native_ui -v
```

이 경우 Docker 관련 검사는 skip이며, 전체 통합 테스트 통과로 보고하면 안 됩니다. `shellground.py --self-test`도 리소스/단원 검사일 뿐 Linux 실행 검사의 대체가 아닙니다.

## Windows 테스트와 빌드

Python 3.12, Docker Desktop의 WSL 2/Linux containers 모드가 필요합니다. `desktop` 폴더에서 PowerShell로 실행합니다.

```powershell
./build-windows.ps1
docker build -t shellground-lab:3 lab
$env:SHELLGROUND_INTEGRATION = '1'
$env:QT_QPA_PLATFORM = 'offscreen'
.\.venv\Scripts\python.exe -m unittest test_real_lab test_native_ui -v
Remove-Item Env:QT_QPA_PLATFORM
Remove-Item Env:SHELLGROUND_INTEGRATION
```

GUI를 직접 실행할 때는 `QT_QPA_PLATFORM=offscreen` 설정을 제거해야 창이 표시됩니다. Windows 빌드와 실기기 실행은 이 버전에서 미검증입니다.

## 패키징

Linux는 `bash build.sh`, Windows는 `./build-windows.ps1`을 사용합니다. 실행 파일은 `desktop/dist/`에 생성되며 Python/Qt·한글 글꼴·실습 이미지 빌드 자료를 포함합니다. Docker와 Linux 커널은 포함하지 않습니다. 대상 운영체제에서 빌드하세요.

미리 만든 실행 파일은 Git 이력에 넣지 않는 구성이며, 바이너리를 배포하려면 별도 릴리스 자산으로 제공할 수 있습니다. 외부 라이브러리의 고지·라이선스 및 소스/재링크 요구 조건은 배포 방식에 맞게 별도로 확인해야 합니다.

명령 문자열을 정답으로 비교하는 코드를 추가하지 마세요. 새 단원은 `missions.py`에 목표와 안내 예시를 정의하고, `lab.py`에서 실제 파일 상태를 검증한 뒤 정상·오답 사례를 테스트에 추가하는 방식으로 확장합니다.
