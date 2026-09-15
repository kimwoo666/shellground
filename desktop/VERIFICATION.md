# 검증 범위

## 4.0.0 오프라인 상태 시뮬레이터 (2026-09-15)

실제 Docker 실행 백엔드 대신 메모리 내부 POSIX 파일/셸·작업·패키지·Docker 상태 모델로 전환했습니다. 사용자 입력을 호스트 셸에 실행하지 않습니다. Linux 빌드에서 검증하며 Windows 실행 파일 빌드·실기기 검증은 수행하지 않았습니다.

Linux 4.0.0 단일 실행 파일을 재빌드했습니다. 패키징된 실행 파일의 자체 검사에서 가상 폴더 생성과 Docker commit→새 컨테이너 파일 복원 과제를 직접 실행·채점해 통과했습니다. 외부 Docker 데몬이나 네트워크는 사용하지 않았습니다.

- 현재 앱을 대상으로 한 **54개 테스트 모두 통과**, skip 없음(약 8초).
- 전체 발견 검사 **84개 중 69개 통과, 이전 실제 Docker 백엔드 통합 검사 15개 건너뜀**. 이전 문자열 퀴즈·Docker 백엔드는 보관용이며 현재 GUI 경로가 아닙니다.
- 40단원 × 3개 seed × 3개 변형 = 360개 과제의 초기 미완료와 풀이 후 통과를 검사. 8개 종합 복습도 별도 검사. 이 조합 수는 테스트 메서드 개수와 다릅니다.
- 가상 FS 경로·파일·링크·권한, 따옴표·환경변수·파이프·리다이렉션·종료 코드, nano 저장/종료, Ctrl+D 파일 입력·Ctrl+Z/C 작업 제어, 가상 컨테이너 셸 진입/종료 검사.
- Docker 사용 중 삭제 거부, 이미지 pull 후 기존 컨테이너가 자동 갱신되지 않음, stop/start 후 파일 유지, commit/save/load 후 새 컨테이너에 파일 복원, --rm은 컨테이너만 정리하는 동작 검사.
- 고정된 안전한 명령 9개 조합을 실제 bash/GNU와 비교해 stdout/stderr/종료 코드 일치 확인. 참조 명령은 테스트 전용 임시 폴더에서만 실행하며 앱이 학습자 명령을 실제 bash로 실행하는 것은 아닙니다.
- subprocess와 네트워크 소켓을 사용하면 실패하도록 모킹한 상태에서도 Docker 및 압축 과제 통과. 전체 GNU/Docker 구현과 같다는 보장은 아닙니다.
- 활용·랜덤·종합 테스트에서 왼쪽 명령어/단원명을 숨기고 배우기·예시에서 복원. 단계·난이도·완료 기록·명시적 F1/F3은 유지.
- 실제 Qt 입력 → 시뮬레이터 → 미완료 두 번 → 이어서 조작 → 통과 → 진도 저장 흐름, 종료·기억노트·스크롤 회귀 유지.
- 1220×880 offscreen 앱 화면에서 테스트 목록 숨김·배우기 복원·한글·터미널·긴 결과 스크롤·버튼 배치 확인.

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:. python3 -m unittest test_simulator test_native_ui test_terminal_scrollback test_memory_notes test_checkpoints test_path_practice test_shutdown -q
QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:.:.. python3 -m unittest discover -q
```

지원하지 않는 옵션, 실제 패키지/이미지 아카이브와의 차이, 미완료된 강의 범위는 README.md와 MATERIAL_COVERAGE.md에 명시했습니다. 4.0에서 별도 VM 설치 계획은 취소했습니다.

## 3.6.1 미완료 채점 후 이어서 조작 (2026-09-15)

전체 70개 테스트가 실제 Docker 통합 모드에서 통과했습니다(158초, skip 없음). Linux 실행 파일 3.6.1 빌드 및 리소스 자체 검사도 통과했습니다. Windows exe 빌드와 Windows 실기기 검사는 수행하지 않았습니다.

- 마우스로 채점한 뒤 입력 초점을 터미널로 복원. 예시·활용·랜덤·종합 복습에서 미완료여도 F5 재채점 가능, F6 건너뛰기는 불가.
- 채점 오류 시에도 실습을 초기화하지 않고 연결된 터미널로 입력 초점 복원.
- 40개 결과를 넣어도 결과 패널 높이는 130px 이하이며 내부 스크롤로 읽기 가능. 1220×880 offscreen 렌더에서 한글, 입력 커서와 터미널·버튼 표시 확인.
- 실제 Linux 셸에서 미완료 채점 두 번 후 동일 컨테이너·PTY 유지, 현재 경로·파일·환경변수 보존, 곧바로 추가 명령 입력 후 통과 및 학습 흐름 진행 검증.
- 기존 26단원·5종합 복습·완료 진도·기억노트·스크롤·종료·격리 검사 유지. 실습 이미지 3.3은 변경하지 않음.

강의자료 대조는 `MATERIAL_COVERAGE.md`에 기록했습니다. **분석 문서이며 새 관리자·Docker·자율주행 확장 과정을 구현하거나 검증한 것은 아닙니다.**

```sh
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:. /usr/bin/python3 -m unittest test_checkpoints test_terminal_scrollback test_path_practice test_memory_notes test_backend test_shutdown test_real_lab test_native_ui -q
```

## 3.6.0 5개 단원마다 종합 복습 (2026-09-15)

최종 전체 68개 테스트가 Docker 통합 모드에서 모두 통과했습니다(149초, skip 없음).

Linux 3.6.0 실행 파일 빌드와 리소스 자체 검사를 통과했습니다. 기존 26개 단원에 종합 복습 5개를 별도 삽입했습니다. 실습 이미지 3.3은 그대로 사용하며 Windows exe 빌드·실기기 검증은 이번에도 수행하지 않았습니다.

- 05·10·15·20·25 뒤 목록 삽입, 기존 단원 번호 보존, 구간 완료 후 테스트 연결 및 미통과 시 다음 미완료 단원 잠금.
- F3은 해당 다섯 단원 설명, F1은 명시적 힌트. 자동 풀이·편집기 조작 안내는 테스트 화면에 표시하지 않음.
- schema 3 진도에 선택적 checkpoints 목록 추가. 기존 completed 기록 보존, 미완료 복습 재개, 완료 복습 재응시 검사.
- 5개 과제 × 3개 seed의 실제 Linux 실행 검증: 초기·부분 상태 거부, 완성 결과 통과, 필수 결과 삭제 후 다시 거부. nano의 실제 키 입력·저장·종료도 포함.
- 생성된 종합 과제에 아직 배우지 않은 명령이 없는지 검사하고 1220×880 offscreen 화면에서 목록·테스트 준비 화면을 확인.

```sh
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:. /usr/bin/python3 -m unittest test_checkpoints test_terminal_scrollback test_path_practice test_memory_notes test_backend test_shutdown test_real_lab test_native_ui -v
```

## 3.5.1 터미널 스크롤 위치 유지 (2026-09-15)

전체 60개 테스트가 Docker 통합 모드에서 모두 통과했습니다(132초, skip 없음). Linux 3.5.1 실행 파일 빌드 및 리소스 자체 검사도 통과했습니다.

출력 파서의 실제 화면과 기록 열람 위치를 분리했습니다. 기록을 읽는 동안 새 출력·커서 표시 변경이 도착해도 동일한 줄을 유지합니다. 맨 아래에서만 출력을 따라가며, Shift+End/우클릭 또는 실제 입력 시 최신 화면으로 돌아갑니다.

- 스크롤 회귀 검사 6개: 연속 출력·제어 시퀀스 중 위치 유지, 기록 선택·복사, Shift+PageUp/PageDown·Shift+End, 일반/한글/붙여넣기 입력 복귀, 3,000줄 제한·오래된 줄 폐기, 초기화·기록 삭제, 창 크기 변경·터치패드 입력.
- 스크롤은 파서 화면을 과거 페이지로 바꾸지 않으므로 실제 Linux 입력·출력 처리는 계속 최신 상태로 유지됩니다.
- 학습 내용, 진도·기억노트 형식, 실습 이미지 3.3은 변경하지 않았습니다. Windows 실기기·exe 빌드는 이번에도 수행하지 않았습니다.

```sh
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:. /usr/bin/python3 -m unittest test_terminal_scrollback test_path_practice test_memory_notes test_backend test_shutdown test_real_lab test_native_ui -v
```

## 3.5.0 상황별 절대·상대경로 실습 (2026-09-15)

최종 전체 54개 테스트가 Docker 통합 모드에서 모두 통과했습니다(122초, skip 없음).

Linux 3.5.0 실행 파일 빌드와 리소스 자체 검사를 통과했습니다. Windows용 코드는 POSIX 경로 계산을 사용하지만 Windows 실행 파일 빌드·실기기 검증은 수행하지 않았습니다. 실습 이미지 3.3과 진도 저장 형식은 변경하지 않았습니다.

- 26개 단원 및 기존 옵션·활용 조건을 유지하면서 현재/인접/먼 작업 위치를 생성합니다. 가까운 파일은 상대경로, 먼 곳에서 반복 작업은 이동 후 처리하도록 예시를 표시합니다.
- 26단원 × 12개 seed × 3개 유형의 명령을 검사해 각 실행 시점의 경로가 원래 목표를 가리키는지 확인합니다. 공백 인용·파이프·리다이렉션·./스크립트 실행 및 find의 절대경로 출력 조건도 검사합니다.
- 실제 Linux에서 인접/먼 위치의 파일 작업·목록·다운로드·압축·스크립트·패키지 문제 28개 조합과 절대/상대경로 대체 답안을 검사합니다.
- 첫 통합 실행은 샌드박스의 Docker 소켓 접근 제한으로 실패해, Docker 접근 승인을 받아 다시 실행했습니다.

```sh
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:. /usr/bin/python3 -m unittest test_path_practice test_memory_notes test_backend test_shutdown test_real_lab test_native_ui -v
```

## 3.4.1 평가 화면 안내 정리 (2026-09-15)

Linux 3.4.1 실행 파일 재빌드 및 리소스 자체 검사를 통과했습니다.

활용 1·2와 올랜덤의 문제 안내에서 nano 조작 순서를 숨겼습니다. 배우기·예시와 사용자가 직접 여는 힌트·옵션 설명은 유지합니다. 입문 목록 및 경로 비교 설명에서 불필요한 저장 불필요 문구를 삭제했으며, 편집 문제의 저장 조건과 읽기 문제의 원본 보존 조건은 유지합니다.

선택한 회귀 검사 35개 중 33개 통과, Docker가 필요한 2개는 건너뛰었습니다. 이번 변경은 안내 표시와 문구에 한정하며 Docker 통합 검사는 다시 실행하지 않았습니다. Windows 실행 파일 빌드와 실기기 검증도 수행하지 않았습니다.

- Qt 화면에서 배우기·예시·활용·올랜덤 및 두 편집 문제 변형을 검사: 평가 안내에 조작 키와 풀이가 없고, 목표·시작 위치 및 명시적 힌트는 유지.
- 입문 설명·힌트·문제 문구 회귀 검사, 기존 학습 순서·진도 저장·기억노트·종료·단축키 검사 통과.

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:. /usr/bin/python3 -m unittest test_memory_notes test_backend test_shutdown test_real_lab.CurriculumTests test_native_ui -v
```

## 3.4.0 내 기억노트 (2026-09-14)

기억노트 검사 8개를 추가해 최종 전체 45개 테스트가 Docker 통합 모드에서 통과했습니다(skip 없음). Linux 3.4.0 실행 파일 빌드와 리소스 자체 검사도 통과했습니다. Windows 실기기 검증 범위는 변경되지 않았습니다.

- F7 규칙·예시 추천 및 설명 선택 텍스트 보존, F8 목록 열기, 터미널 초점에서 단축키 동작.
- Ctrl+S 저장, 재생성한 저장소·노트 창에서 복원, 제목·내용 검색, 중복 저장 방지, 수정과 삭제.
- 닫기·다른 노트 이동 시 저장/취소 확인, 삭제 확인, 저장 실패 시 미저장 내용 유지.
- 손상된 원본 파일 덮어쓰기 방지, 원자적 교체 실패 시 기존 노트 보존.
- 기억노트 JSON과 완료 진도 JSON 분리, 작업 중 단축키 제한, 한글 노트 화면 offscreen 렌더 확인.

```sh
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen python3 -m unittest test_memory_notes test_backend test_shutdown test_real_lab test_native_ui -v
```

## 3.3.0 학습 순서 재구성·조합 과제·설명 화면 실습 (2026-09-14)

최종 전체 37개 테스트가 Docker 통합 모드에서 통과했습니다(skip 없음, 107초). Linux 3.3.0 실행 파일 빌드 및 리소스 자체 검사도 통과했습니다.

- 기존 15개 단원 키와 상세 옵션 설명을 유지하면서 기본 작업을 분리해 26개 단원으로 재배치했습니다. 명령 도입 순서 검사로 예시·활용 1·활용 2에서 아직 소개하지 않은 명령을 사용하는 회귀를 방지합니다.
- 폴더·파일 생성, cat 읽기, 실제 GNU nano 수정·저장, 개별 cp/mv/rm, 실행 권한 단원을 추가했습니다. 기본 화면은 짧은 설명만 표시하고 F3 전체 참고 내용을 유지합니다.
- 화면 실습은 pwd/ls/cat의 실제 PTY 출력으로 검사합니다. 이 출력은 현재 문제의 메모리에만 보관하며 진도 JSON에 저장하지 않습니다.
- 활용 2는 26개 단원마다 조합·복구 조건을 정의합니다. 같은 seed의 활용 1과 비교해 목표가 달라지는지, 실제 해결 결과가 통과하는지, 기본 풀이 반복으로 조합 과제가 통과하지 않는지 검사합니다.
- nano에서 수정하지 않은 상태와 저장 전 상태 거부, 실제 키 입력으로 한 줄 수정 및 기존 설정 보존·세 줄 저장을 검사합니다.
- F4로 설명을 유지한 자유 연습 시작, F4 재입력 시 초기화 방지, 자유 연습 채점/완료 처리 차단, F6 예시 전환을 Qt 테스트와 실제 Linux 학습 흐름에서 확인합니다.
- 종료·진도 보존, 한글 렌더링, Docker 격리, Linux PTY, 파일 형식별 다운로드 검사를 유지합니다. 1220×880 offscreen 화면에서 안내·버튼 표시도 확인했습니다.

```sh
docker build -t shellground-lab:3.3 lab
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen python3 -m unittest test_backend test_shutdown test_real_lab test_native_ui -v
```

Linux 실행 파일 버전은 3.3.0입니다. Windows Hyper-V 실기기 및 Windows exe 빌드는 여전히 미검증입니다. 전체 옵션 설명이 모두 독립된 채점 문제인 것은 아닙니다.

## 3.1.1 완료 진도 자동 저장 표시 (2026-09-14)

Docker 통합 검사를 포함한 전체 27개 테스트 통과(skip 없음). Linux 실행 파일을 3.1.1로 다시 빌드했습니다. Windows 실기기 검증 범위는 변경되지 않았습니다.

단원 목록에서 완료/미완료를 명시하고 상단에 완료 진도 자동 저장 안내를 표시합니다. 저장 성공과 실패를 구분하며 기존 `schema: 3, completed: [...]` 저장 형식을 유지합니다. 명령 입력·터미널 화면·실습 파일은 저장하지 않습니다.

Qt 검사에서 예시만 통과/활용 1개 통과 상태가 미완료로 남고, 활용 2개 통과 시 즉시 완료 기록만 저장되는 것을 확인했습니다. 별도 프로세스의 실제 Qt 종료 이벤트 뒤 새 창을 만들어 완료/미완료 표시 복원, 첫 미완료 단원 선택, 빈 터미널 복원을 확인했습니다. 저장 실패 경고와 재시도 성공도 검사합니다.

## 3.1.0 옵션 교육·단축키·Windows 비 WSL 정책 (2026-09-14)

Linux에서 `test_backend`, `test_shutdown`, `test_real_lab`, `test_native_ui` 총 **25개 테스트 통과**, Docker 통합 검사 포함, skip 없음.

- 15개 단원: pwd 링크의 논리/물리 경로 보고서 및 ls -A/-alh/-1S 보고서 추가. 미해결 상태 거부·실제 해답 통과 확인.
- pwd -L/-P를 뒤바꾼 보고서, ls -a/-A 혼동, -h 누락, 크기 정렬 역순을 거부. ls 비교 문제는 3개 seed로 검사.
- Qt 터미널 초점에서 F1/F2/F3/F5/F6 작동, 비활성·작업 중 동작 방지, 미통과 단계 건너뛰기 방지, 다시 시작 취소/승인 확인.
- 단원 추가·재배치 후 기존 완료 기록 보존 및 새 미완료 단원 안내.
- Windows 정책은 Docker 정보 모킹으로 검사: LinuxKit 허용, WSL/Microsoft/알 수 없는 커널 및 Windows containers 차단. WSL에서 이미지 빌드·실습 시작 호출이 진행되지 않음.
- 실제 Linux PTY·파일 결과·다운로드·격리·정상 종료 회귀 검사 유지.

```sh
docker build -t shellground-lab:3.1 lab
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen python3 -m unittest test_backend test_shutdown test_real_lab test_native_ui -v
```

Windows Hyper-V 설치·실행 및 Windows exe 빌드는 **실기기 미검증**입니다. LinuxKit 식별 정책은 지원 환경 확인이며 임의로 변조된 서버를 판별하는 보안 장치가 아닙니다. Home/ARM Windows와 미확인 커널은 지원하지 않습니다. 전체 옵션 설명이 모두 독립된 채점 문제로 구현된 것은 아닙니다.

## 3.0.1 종료 수정 (2026-09-14)

정리 완료 후 Qt의 후속 종료 이벤트를 다시 거부해 정리 작업을 반복하던 오류를 수정했습니다. 종료 중과 정리 완료 상태를 구분하고, 정리 실패 시 오류를 표시하며 재시도를 허용합니다.

`test_shutdown` 4개를 추가했습니다: 정리 후 정상 종료, 종료 연속 클릭 시 중복 방지, 정리 실패 시 반복 방지, 실제 실습 컨테이너 삭제 후 앱 종료. 기존 검사와 함께 Docker 통합 모드에서 **17개 테스트가 통과**했습니다.

```sh
SHELLGROUND_INTEGRATION=1 QT_QPA_PLATFORM=offscreen python3 -m unittest test_shutdown test_real_lab test_native_ui -v
```

## 3.0.0 초기 검증 (2026-09-10)

Ubuntu 24.04 x86-64, Python 3.12, Docker 29.1.3에서 검사.

- 13개 단원의 미해결 상태 거부와 실제 파일 결과 성공 검사 (현재 위치 문제는 PTY 검사에 포함).
- 옵션 순서 변경, 상대/절대 경로, 재귀·숨김 옵션 누락, 원본 삭제 후 불완전한 목록 거부.
- 실제 deb/sh/zip/tar.gz HTTP 다운로드 및 잘못된 저장 이름·손상 내용 거부.
- 압축 해제, Debian 패키지 추출, 권한과 스크립트 결과, 로그 필터, 파이프, 검색 결과 검사.
- PTY의 경로 유지, Tab 자동 완성, 위 화살표 기록, 오류 출력, Ctrl+C, 터미널 크기 변경.
- 컨테이너 비관리자 실행, 읽기 전용 루트, 네트워크 차단, 호스트 bind mount 없음.
- Qt 한글 글리프, ANSI와 한글 셀 너비, 키 전달, bracketed paste, 진도 잠금과 저장, 오류 복구.
- 실제 Qt 화면 위젯 → Linux → 채점 → 활용 문제 2개 → 진도 저장의 연동 검사.

`test_real_lab` 8개 + `test_native_ui` 5개 = 13개 테스트. 일부 테스트는 여러 단원·파일 형식·명령 변형을 반복 검사합니다. Qt 검사는 offscreen 테스트로 수행하며 사용자의 실제 데스크톱 화면을 캡처하지 않습니다.

## 미검증 / 제한

- Windows 실기기 빌드 및 실행: 미검증. Windows exe 산출물은 이 Linux 환경에서 생성하지 않았습니다. `build-windows.ps1`과 공용 소스 제공.
- 다른 Linux 배포판, 모든 xterm 기능, 모든 Linux 명령/옵션: 보장하지 않음.
- 외부 인터넷 다운로드와 관리자/커널/하드웨어 관리: 실습 범위에서 제외.
- 컨테이너는 가상 머신과 동일한 보안 경계가 아님. 개인 파일을 연결하지 않으며 악성 코드 분석 용도가 아님.
