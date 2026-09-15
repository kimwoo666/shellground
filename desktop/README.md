# Shellground Desktop 4.0.0

Linux·Docker 명령어를 연습하는 **오프라인 네이티브 시뮬레이터**입니다. 웹뷰가 아니며 Docker, WSL, Hyper-V, 가상머신 설치가 필요하지 않습니다. 명령은 프로그램 메모리 안의 파일·경로·권한·작업·이미지·컨테이너 상태에만 적용됩니다. 사용자 입력을 호스트 셸에 실행하거나 외부 네트워크로 보내지 않습니다.

## 실행

- Linux: `dist/Shellground` 실행. 기존 실행 중인 버전은 종료한 뒤 새 파일을 실행하세요.
- Windows: Windows에서 `build-windows.ps1`로 빌드한 `dist/Shellground.exe` 사용. Python 3.12 및 패키지 다운로드는 **소스에서 빌드할 때만** 필요합니다.
- 소스 실행: Python 3.12 환경에서 `pip install -r requirements.txt` 후 `python shellground.py`.
- 버전 확인: `Shellground --version`. 리소스 검사: `Shellground --self-test`.
- 이번 릴리스는 Linux x86-64에서 빌드·검사했습니다. Windows 공용 코드는 제공하지만 Windows exe 산출물과 실기기 검증은 아직 없습니다.

3.x에서 사용했던 Docker 이미지·컨테이너는 더 이상 사용하지 않으며 이 버전이 기존 Docker 자원을 임의 삭제하지 않습니다. 별도 환경 준비 없이 바로 예시나 자유 연습을 시작하세요.

## 학습 흐름

짧은 설명과 자유 연습 → 예시 직접 입력 → 활용 1 → 활용 2 → 단원 완료.
기존 26개 단원을 유지하고 Linux 환경/작업/패키지와 Docker 과정을 더해 **40개 단원**, 05·10·15·20·25·30·35·40 뒤에 **8개 종합 복습**을 배치했습니다. 완료한 범위는 올랜덤으로 다시 연습할 수 있습니다.

파일 경로·이름·내용·권한·현재 위치와 가상 Docker 상태로 채점합니다. 정답 문자열 하나만 허용하지 않습니다. 가까운 파일은 상대경로, 먼 대상은 절대경로를 사용할 수 있습니다. 명령의 전체 동작을 완전히 구현한 Linux 커널/셸은 아니므로 지원 범위는 아래를 확인하세요.

**활용 1·2, 종합 테스트, 올랜덤에서는 왼쪽 목록의 명령어와 단원명을 숨깁니다.** 단계 번호·난이도·완료 여부는 유지합니다. 배우기·예시·복습 준비 화면으로 돌아가면 복원합니다. 명시적으로 여는 F1 힌트와 F3 설명은 유지합니다.

**미완료 채점 후 재시작하지 마세요.** 터미널로 입력 초점이 돌아오며 현재 파일·경로·셸 상태를 유지한 채 수정하고 F5로 재채점할 수 있습니다. 결과 목록이 길면 결과 영역 안에서 스크롤합니다. F2는 파일을 초기화하는 기능입니다.

## 키 조작

| 키 | 동작 |
| --- | --- |
| F1 | 힌트 |
| F2 | 현재 문제 초기화, 확인 후 실행 |
| F3 | 옵션 설명 |
| F4 | 배우기 화면에서 설명 보며 자유 연습 |
| F5 | 결과 채점 |
| F6 | 예시 시작 / 통과 후 다음 문제 |
| F7 / F8 | 기억해두기 / 기억노트 검색·수정 |
| Tab / ↑↓ | 기본 자동 완성 / 입력 기록 |
| Ctrl+C / Ctrl+L | 작업 중단 / 화면 정리 |
| Ctrl+Shift+C/V | 복사 / 붙여넣기 |
| Shift+PageUp/PageDown / Shift+End | 이전 기록 / 최신 출력 |

nano 학습 편집기: Ctrl+K 줄 잘라내기, Ctrl+U 붙이기, Ctrl+O → Enter 저장, Ctrl+X 종료, Ctrl+G 도움말. 저장 전 종료 시 저장 여부를 묻습니다. 활용·종합·랜덤 문제에는 이 조작법을 자동 표시하지 않습니다.

기록을 위로 스크롤하면 새 출력이 와도 열람 위치가 유지됩니다. 실제 입력을 시작하면 최신 입력 위치로 돌아갑니다. 입력 기록은 현재 실습에서만 유지합니다.

## 구현 범위

- 가상 POSIX 경로와 심볼릭 링크, 공백 따옴표, 기본 변수 확장·와일드카드.
- `pwd/cd/ls/mkdir/touch/cat/cp/mv/rm/rmdir/chmod/ln`, ls 옵션 조합·재귀 목록.
- `>`, `>>`, `<`, `2>`, 파이프, `;`, `&&`, `||`, 종료 코드 `$?`.
- `grep/head/tail/wc/find`, `echo/printf`, 제한된 텍스트 스크립트, 환경변수·자식 셸.
- nano 학습 편집기, cat 입력과 Ctrl+D, more/less의 기본 페이지 이동.
- sleep 작업·jobs·PID/job ID·STOP/CONT/TERM/KILL, Ctrl+Z/C·fg/bg.
- 가상 패키지 목록·설치·업그레이드·제거. 실제 패키지를 설치하지 않음.
- 가상 URL에서 curl/wget, 메모리 내 tar/zip 추출, 준비된 가상 deb의 정보·추출.
- Docker pull/images/run/create/ps/start/stop/restart/exec/attach/rm/rmi/tag/commit/save/load/inspect/logs/container prune.
- Docker 이미지 갱신과 기존 컨테이너 분리, 파일 보존·새 컨테이너 복원, 이름 충돌·실행 중 삭제 거부, `--rm`.
- Docker `-d/-i/-t/--name/-e/-p/-u/--memory/--cpus` 설정과 제한적인 stats 표시.

`help`와 지원되는 명령의 `--help`, F3에서 참고하세요. F3에는 아직 미구현된 심화 옵션 설명도 남겨 두었으며, 해당 옵션은 오류로 표시합니다. 기존 교육 내용을 삭제하지 않았습니다.

## 정확성의 한계

전체 GNU/bash/Docker 호환 제품이 아닙니다. 현재 구현하지 않은 옵션·서브명령은 명시적으로 실패합니다. 일부 명령의 출력 정렬·시간·크기·진행 표시·상호작용은 단순화되어 있습니다.

- 임의 바이너리 실행, 명령 치환, 복잡한 셸 제어문, 모든 정규식/자동 완성/터미널 기능은 지원하지 않습니다.
- 실제 계정 추가·sudo 인증/정책·모든 패키지 의존성·snap/systemd·하드웨어 장치는 구현되지 않았습니다.
- Docker 호스트 볼륨/네트워크 구축·Dockerfile 빌드·GPU/privileged/device 옵션은 아직 지원하지 않습니다.
- 가상 registry는 준비된 이미지/버전만, 다운로드는 문제의 가상 URL만 지원합니다.
- Docker 이미지 아카이브 및 deb는 학습 전용 형식입니다. 실제 Docker/dpkg와 교환하거나 설치하는 산출물이 아닙니다.
- 자원 옵션은 설정 상태를 연습하는 기능이지 실제 CPU·메모리 사용량 측정이 아닙니다. stats의 가상 수치를 실제 성능으로 해석하지 마세요.
- 메모리 보호를 위해 파일당 2 MB, 가상 파일 시스템 데이터 8 MB·10,000항목, 동시에 16개 컨테이너 등의 제한이 있습니다.
- 강의자료의 모든 명령·옵션을 숙달할 수 있는 전체 확장은 **아직 완료되지 않았습니다**. [범위와 남은 항목](MATERIAL_COVERAGE.md)을 참고하세요.

## 저장과 검증

완료한 단원·종합 복습만 자동 저장합니다. 이전 버전의 완료 키와 기억노트를 유지합니다. 입력·터미널 화면·풀던 가상 파일과 컨테이너는 종료 후 복원하지 않습니다. F7/F8로 직접 저장한 기억노트는 별도 보존합니다.

`progress-v3.json`, `memory-v1.json`은 Qt의 Shellground 사용자 데이터 폴더에 저장합니다. 가상 /home/learner 경로는 호스트의 실제 경로가 아닙니다.

[학습 순서](LEARNING_PATH.md) · [검증 기록](VERIFICATION.md)

현재 시뮬레이터 검사:

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:. python3 -m unittest test_simulator test_native_ui test_terminal_scrollback test_memory_notes test_checkpoints test_path_practice test_shutdown -q
```

`engine.py`와 `test_real_lab.py`의 실제 Docker 백엔드는 이전 버전 참고용입니다. 4.x GUI는 `sim_engine.py`를 사용합니다. `legacy_gtk.py`와 문자열 정답표 역시 현재 앱에서 사용하지 않습니다.
