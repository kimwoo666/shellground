# Shellground

목표를 보고 Linux 명령어·경로·옵션을 스스로 조합하는 **네이티브 데스크톱 실습 프로그램**입니다. 웹 앱이나 웹뷰가 아닙니다. Qt 화면의 터미널에서 Docker 안의 실제 Ubuntu bash와 GNU 명령을 실행합니다.

> **현재 상태:** Linux(Ubuntu 24.04, x86-64) 빌드와 통합 테스트를 확인했습니다. Windows용 공용 코드와 빌드 스크립트를 제공하지만 **Windows 실행 파일 제작·실기기 검증은 아직 완료하지 않았습니다.** Docker/WSL 없이 실행 파일 하나만으로 Linux 실습이 되는 프로그램은 아닙니다.

## 어떤 방식으로 배우나요?

1. **새 명령 배우기**: 용도, 옵션, 경로와 인용부호 설명.
2. **예시 직접 실습**: 안내 명령을 실제 터미널에 입력.
3. **활용 문제 2개**: 정답을 숨기고, 시작 위치·경로·파일 이름이 바뀐 목표 해결.
4. **배운 범위 올랜덤**: 완료한 단원 전체에서 새 문제 생성. 후반 문제에서는 다운로드·경로·압축·권한 등을 조합.

예를 들어 현재 위치가 `/home/learner/desk/team1`일 때 다른 폴더의 숨김 항목·하위 구조를 상세 목록으로 정리해 지정된 텍스트 파일에 저장합니다. 입력 문자열이 아니라 **실제로 만들어진 파일의 위치·이름·내용·권한과 현재 셸 위치**로 채점합니다. 같은 결과를 만드는 다른 명령 조합도 인정합니다.

```sh
ls -alR /home/learner/data/release4242 > /home/learner/reports/inventory-4242.txt
```

위 경로는 설명용 예시입니다. 실제 실습에서는 문제에 표시된 경로를 사용하세요.

## 학습 범위

| 난이도 | 주요 실습 |
| --- | --- |
| 1 · 입문 | `pwd`, `ls`, `cd`, `mkdir -p`, `touch`, `cp`, `mv`, `rm`, 공백이 있는 경로 |
| 2 · 목록과 보고서 | `ls -a`, `ls -al`, `ls -alR`, `>`, `cat`, 절대·상대 경로 |
| 3 · 검색과 가공 | `grep -i`, 파이프 `\|`, `wc -l`, `find -type f -name`; `head`·`tail` 사용 설명 |
| 4 · 파일 활용 | `curl`, `wget`, `.deb`·`.sh`·`.zip`·`.tar.gz` 다운로드, `tar`, `unzip`, `chmod`, 스크립트 실행, `dpkg-deb` 추출 |

총 13개 단원입니다. 모든 Linux 명령·옵션이나 시스템 관리자 전체 과정을 다루지는 않습니다.

## 빠른 시작: Linux

먼저 Python 3.12, Git, Docker Engine을 설치하고 Docker를 실행하세요. 현재 사용자로 `docker info`가 성공해야 합니다. Ubuntu에서는 Python venv 및 Qt XCB 라이브러리도 필요합니다.

```sh
# Ubuntu에서 필요한 시스템 패키지 (Docker 자체 설치는 별도)
sudo apt install python3-venv libxcb-cursor0

git clone https://github.com/kimwoo666/shellground.git
cd shellground/desktop
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python shellground.py
```

프로그램에서 **실행 환경 확인 → 최초 실습 환경 준비 → 예시 실습 시작** 순으로 진행합니다. 최초 준비에는 인터넷과 수백 MB의 공간이 필요합니다. 이미지가 이미 준비되어 있으면 다시 만들 필요가 없습니다.

단일 실행 파일로 빌드하려면 같은 `desktop` 폴더에서:

```sh
bash build.sh
./dist/Shellground
```

저장소에는 소스와 글꼴을 포함하며 빌드 캐시·가상환경·실행 파일은 커밋하지 않습니다. 배포 바이너리가 별도로 제공되지 않은 경우 위 방법으로 직접 빌드해야 합니다.

## Windows: 소스 실행 및 빌드 경로

**아래는 제공된 실행/빌드 방법이며 Windows 실기기 검증 완료를 의미하지 않습니다.** Python 3.12, Git, Docker Desktop이 필요합니다. Docker Desktop은 WSL 2 기반 **Linux containers** 모드로 실행하세요.

PowerShell에서:

```powershell
git clone https://github.com/kimwoo666/shellground.git
cd shellground\desktop
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe shellground.py
```

실행 파일 빌드는 같은 폴더에서 `./build-windows.ps1`을 실행합니다. 성공 시 `desktop/dist/Shellground.exe`가 생성됩니다. Python 의존성 설치와 빌드는 Windows에서 수행해야 합니다. Linux 바이너리의 확장자만 `.exe`로 바꿔 사용할 수 없습니다.

공식 설치 참고: [Docker Engine](https://docs.docker.com/engine/install/), [Docker Desktop for Windows](https://docs.docker.com/desktop/setup/install/windows-install/), [WSL 2 백엔드](https://docs.docker.com/desktop/features/wsl/).

## 사용설명서와 검증

- [상세 사용설명서](docs/USER_GUIDE.ko.md): 화면 조작, 예제 문제, 채점, 다운로드, 진도, 문제 해결.
- [개발·빌드 안내](docs/DEVELOPMENT.ko.md): 코드 구조, 테스트 실행, 재배포 참고.
- [검증 범위와 알려진 제한](desktop/VERIFICATION.md): 실제로 확인한 것과 아직 확인하지 못한 것.
- [외부 구성요소 안내](THIRD_PARTY_NOTICES.md): 글꼴과 Python/Qt 의존성.

## 실제 Linux와 안전 범위

Tab 자동 완성, ↑↓ 명령 기록, Ctrl+C, Ctrl+L, 파이프·리다이렉션·오류 출력은 실제 bash와 프로그램이 처리합니다. ANSI 화면을 네이티브 위젯에 표시하며, 모든 xterm 확장/TUI와의 완전한 호환을 보장하지는 않습니다.

실습 컨테이너에는 개인 폴더와 Docker 소켓을 연결하지 않습니다. 비관리자 사용자, 읽기 전용 루트, 메모리/PID 제한과 외부 네트워크 차단을 사용합니다. 다운로드는 컨테이너 안의 로컬 HTTP 서버에서 제공하는 실제 파일로 연습합니다. 일반 인터넷 다운로드, 관리자·커널·하드웨어 관리는 실습 범위가 아닙니다. 컨테이너는 가상 머신과 같은 보안 경계가 아니므로 악성 코드 실행 용도로 사용하지 마세요.
