# Conda 환경 관리 과정 — Linux 실검증, 다른 플랫폼 확장 중

실제 Conda와 실제 Python을 앱 전용 Linux VM 안에서 실행한다. 개인 컴퓨터의 Conda, Python, 셸 설정, Docker 소켓을 사용하지 않는다. 명령 문자열을 흉내 내는 시뮬레이터가 아니다. 네 운영체제의 최종 지원 완료를 뜻하지 않는다.

## 배우는 범위

**Linux 검토판4.7.3 추가:** 아래 기존15단원 뒤에 pip16·17단원(6문제/8소단계)을 연결했다. 현재 소스로 실제60문제·20학습·설치12검사를 통과했고 새 `dist-linux-pip-review/Shellground`에서도 설치10흐름·pip11흐름과 종료를 검증했다. [pip 검토 안내](../LINUX_PIP_REVIEW.md)를 참고한다. 기존4.7.2에는 pip 과정이 없고, Android 자료·이전 배포본의 지원 범위도 자동으로 늘어나지 않는다.

기존15단원·3종합복습의54문제를 유지하고 pip2단원·6문제를 더해 총17단원·3복습·60문제다. 세부 설계와 강의·공식 출처는 `course_spec.json`, `pip_course_spec.json`, `DESIGN.md`에 있다.

- 01–05: 실행 장소·버전, 환경 목록, 생성, 활성화/해제, 실제 Python 경로 확인.
- 06–10: 패키지 목록, 설치, 요청 버전, 선택 업데이트, 패키지만 제거.
- 11–15: 프로젝트별 환경 분리, 직접 요청한 패키지 내보내기, 새 환경 재구성, 전체 설치 기록과의 차이, 환경 제거.
- 16–17: 선택한 Python으로 pip 설치, 설치 위치·버전 읽기, 패키지만 제거, 잘못된 환경과 손상된 설치 복구.

소스에는 별도 **설치 준비·실습** 진입점도 있다. 기존 01–15와 복습 번호를 바꾸지 않는다. Anaconda/Miniconda/Conda 구분 → 공식 파일·아키텍처·새 prefix 확인 → `-b`/`-p` 설치 → 새 Conda와 Python 소속 확인의4소단계다. 마지막 설치 평가는 같은 터미널에서 진행하며 「설치 설명으로 돌아가기」도 세션을 유지한다. 설치 완료 기록은 일반54문제와 구분하여 저장한다.

이 실습은 **설치 파일이 포함된 새 런타임이 필요**하다. 기존 `Shellground-unified` 배포 파일을 열었다고 신규 설치 실습까지 포함된 것으로 보아서는 안 된다. 새 런타임/실행파일 배포와 전체 회귀 검증은 별도 작업이다.

「설치 파일·라이선스」는 해시 검증된 공식 설치 파일의 원문 약관·출처·해시를 표시한다. 창을 여는 행위는 설치나 동의가 아니다. `-b`는 약관을 읽고 동의한 경우에만 학습자가 직접 실행한다. `-b`를 뺀 대화형 설치도 같은 실제 결과를 만들면 허용하며, 이 실습에서는 셸 초기화 질문에 `no`를 선택한다. 개인 PC나 외부 저장소의 약관을 앱이 대신 수락하지 않는다.

설치는 guest의 `/home/learner/setup-practice/miniconda-…` 새 경로에만 한다. 다시 시작은 이전 경로를 덮어쓰지 않는다. 임시 설치와 입력 기록은 앱 종료/일반 단원 실습 초기화 후 남지 않지만, 소단계·완료 진도는 남는다.

각 단원은 설명을 보며 조작하는 소단계 → 예시 실습 → 목적이 다른 활용 두 문제로 진행한다. 테스트에서는 옆 목록의 학습 제목을 숨긴다. 소단계·활용 통과 여부는 별도 `conda-progress-v1.json`에 저장하고 코드 입력·임시 파일은 진도로 저장하지 않는다. 기존 Linux/Python 진도는 변경하지 않는다.

## 네이티브 화면

소스의 `CondaWindow`는 문제·채점·실습 파일 탭, 실제 Bash 터미널, 출력에서 읽은 값을 답하는 칸을 제공한다. 파일 탭은 guest 실습 폴더의 실제 파일을 읽기 전용으로 보여 준다(목록200항목/본문128KiB상한, 링크·폴더 밖 접근 제외). F1힌트/F2초기화/F3전체 설명/F4설명 보며 실습/F5채점/F6다음. 실패한 채점은 세션을 초기화하지 않는다. 문제 탭과 터미널로 돌아가 고쳐서 다시 채점할 수 있다. 올랜덤에서 이전 학습으로 돌아갈 수 있다.

배우기에서는 실제 준비된 환경 이름에 맞춘 현재 소단계 하나만 보여 준다. F3의 전체 설명은 스크롤 가능한 별도 창이다. 같은 세션의 소단계 이동과 F4는 기존 실습 상태를 유지한다. 중간 소단계에서 앱을 다시 열거나 F2를 누르면 **학습 위치는 유지하지만 실습 환경은 초기화**된다. 이때 `이전 소단계 준비 보기`에서 앞선 명령과 관찰 내용을 확인할 수 있다. 안내는 명령을 자동 실행하거나 완료 처리하지 않으며, 활성 세션에서는 이미 수행한 생성·삭제·활성화를 중복 실행하지 않도록 경고한다.

모드 선택과 Python 화면에서 진입한다. 검증된 런타임이 없으면 실제 실습을 시작하지 않으며 개인 Conda나 가짜 결과로 대체하지 않는다. 설치되어 있다는 배지는 실제 VM 준비·설정 확인 후에만 표시한다.

## 채점과 한계

설치 목록 JSON, 실제 `conda-meta`, Python 실행 경로·버전, 새 프로세스의 모듈 import·함수 결과, YAML 내용을 비교한다. 교육용 패키지의 설치 코드는 읽기 전용 원본 아카이브와 대조한다. 같은 결과의 다른 명령·옵션 순서는 허용한다. 읽기 문제는 실제 값과 답칸을 비교하며 학생이 과거에 특정 읽기 명령을 입력했다는 이력을 증명하지는 않는다.

`training-math`와 `training-text`는 설치·업데이트·제거를 직접 연습하기 위한 작은 **실제 Conda 패키지**다. NumPy 등을 가짜로 대체하는 패키지가 아니다. NumPy·Matplotlib·pandas 등의 실제 계산은 별도 Python 과정에서 수행한다.

이것은 학습용 상태 채점이며 악의적인 수험자의 조작까지 방어하는 시험 보안 장치는 아니다. 실행 중인 셸의 상태는 기존 실제 Linux 과정과 같은 prompt 관찰을 사용한다. 임의의 외부 코드는 실행하지 않는다.

설치 평가는 처음에 없던 새 경로, 공식 설치와 일치하는 Conda/Python metadata·launcher·Conda 모듈, 새 Python의 실행 위치·버전·Conda import, 관리용 base와 셸 설정 보존을 확인한다. Python ELF의 설치 경로 차이는 보호된 Conda의 `binary_replace`로 메모리 안에서만 정규화하여 나머지 바이트를 대조한다([Conda 공식 구현](https://github.com/conda/conda/blob/main/conda/core/portability.py)). 빈 폴더·기존 base 링크·성공 문구만 출력하는 스크립트는 설치 결과가 아니다. 수동 셸의 과거 installer 종료 코드는 관측하지 않으므로 증명했다고 표시하지 않는다.

## 런타임 및 검증

**최신 소스와 이전 검증팩 구분(2026-09-17):** 설치 실습 추가 이전의 x86 빌더에서54문제·오답 복구4개·답안 변형13개·18학습 시퀀스 검증을 완료했습니다. 당시 course fingerprint는 `8e5592f2d0cbfd1c460bc094f2d0e988069e22b76aecc44f4da7a4dd53cc8040`, learning fingerprint는 `f7d7279eb8b2c7864577525c77c61d1cc7dd96f2cea6e586e8e8fd8d6174d02c`입니다. **설치 실습과 provision 소스 변경 후에는 이전 보고서가 현재 소스 전체 검증의 증거가 아니며 새 전체 회귀가 필요합니다.** 기존 배포팩은 덮어쓰지 않았습니다. Linux 기능 완성 → Windows → Android → macOS 순서를 유지하며 Android/ARM 추가 개발은 보류합니다.

- 후보: 공식 Miniconda3-py312_26.7.1-1, 실제 Conda26.7.1/Python3.12.14, Linux x86_64.
- 공식 설치 파일 SHA256: `b27f60ab63e77eeab50a5417c989120f767e863df32400190d4c7262369f8695`.
- 관리용 설치 `/opt/shellground/miniconda`, 환경 `/home/learner/conda-envs`, 문제 `/home/learner/conda-work`.
- 외부 네트워크 없이 `file:///opt/shellground/conda-channel`에서154개 공식 의존성 아카이브와3개 교육 패키지를 사용한다. 설치 파일의 원본 아카이브·라이선스를 보존하며, 의존성은 설치에 실제 사용된 공식 보정 메타데이터를 따른다.
- 계정/외부 저장소 플러그인은 이 오프라인 과정에서 사용하지 않는다. 외부 저장소 약관에 대신 동의하거나 외부 패키지 서버에 접속하지 않는다.
- 생성·활성화·설치·업데이트·내보내기·복원·제거와54문제 전체, 대표 오답 후 복구4개, 동등/잘못된 답안13개,18단원의 연속 소단계 실행이 실제 guest에서 통과했다. 보고서는 `.conda-build/course-validation.json`과 `learning-validation.json`이며 현재 소스 fingerprint와 일치해야 한다.
- 실제 Qt 앱 검사도 통과했다(26.872초): 오답 채점→같은 PTY에서 수정→통과, 실제 YAML 파일 탭 표시, 다음 활용 문제, 완료 진도 저장, 닫기 후 VM·읽기 스레드·임시 overlay 정리. 이는 Linux x86_64 결과이며 Windows/macOS/Android 실검증을 대신하지 않는다.
- 개발용 VM은2vCPU/2GiB/낮은 우선순위, 호스트 폴더 공유 없음. 기본4.6 런타임을 덮어쓰지 않는다. 종료 시 전용 프로세스를 정리한다.

### 개발 명령 (Linux 개발 호스트에서만)

```sh
PYTHONPATH=. python3 -m conda_teaching.build_runtime
PYTHONPATH=. python3 -m conda_teaching.build_runtime --course-test
PYTHONPATH=. python3 -m conda_teaching.build_runtime --learning-test
PYTHONPATH=. python3 -m conda_teaching.build_runtime --setup-test
PYTHONPATH=. python3 -m conda_teaching.build_runtime --setup-test-only
PYTHONPATH=. QT_QPA_PLATFORM=offscreen python3 -m conda_teaching.build_runtime --setup-ui-test
PYTHONPATH=. python3 -m conda_teaching.export_runtime
```

기존팩이 있을 때는 새 버전 경로를 명시한다. 기존 폴더를 지우거나 덮어쓰지 않으며, 모든 검증 게이트는 그대로 적용된다. Linux 검토판 예: `python3 -m conda_teaching.export_runtime --destination dist-linux-review/runtime/linux-x86_64`, 이어서 `bash build.sh --with-conda-runtime --runtime-source dist-linux-review/runtime/linux-x86_64 --dist-dir dist-linux-review`. 새 배포 폴더에 직접 내보내면 같은 큰 이미지를 중간 폴더와 배포 폴더에 두 번 저장하지 않는다. 이는 개발 명령 예시이며 해당 경로의 검토판이 이미 완성됐다는 뜻은 아니다.

Conda 포함 빌드는 새 실행파일에서 `--self-test-conda`와 `--self-test-conda-setup`을 직렬로 실행한다. 후자는 실제 설치 UI·오답 후 같은 터미널 재시도·완료/소단계 복원·숨은 실습 종료를 검사하고 검사용 이미지를 `verification` 폴더에 저장한다. 모두 임시 진도를 사용하며 기존 사용자 완료 기록을 수정하지 않는다.

내보내기는 현재 소스 fingerprint에 대한54문제·대표 오답 수정4개·동등/오답 답안13개·18단원 소단계 검사와 별도 새 설치 검사가 모두 있어야 허용한다. 결과는 별도 `.vm-runtime-conda/linux-x86_64`이며 기존 팩을 덮어쓰지 않는다. 패키지 다운로드/SDK 설치나 개인 설정 변경은 이 명령에 없다. 검증된 공식 설치 파일과 기존 프로젝트 전용 QEMU 팩이 개발 준비물이다. 검사 목록은 요구 조건이며, 현재 통과 범위는 실제 보고서를 확인해야 한다.

Windows/macOS 실제 Conda 런타임 팩, Android 내부 Linux 실행, ARM 게스트, 새 설치 실습의 배포 통합과 정식 배포/라이선스 목록 검증은 남아 있다. 현재 APK에는 이 Conda VM 과정이 들어 있지 않다.

ARM64 준비에는 공식 `Miniconda3-py312_26.7.1-1-Linux-aarch64.sh`를 사용한다. 다운로드 SHA256은 `f6d64a1565e713429683720f59dd6661f5131c2f959a4830438eb1969cde23f7`이다. `android/runtime/build_conda_guest.py`가 기존 검증 Linux 이미지를 읽기 전용 기반으로 삼아 별도 `conda-arm64` overlay와 보고서를 생성한다. 이 개발 호스트 검사가 성공하더라도 Android 앱 연결·실휴대폰 검증을 대신하지 않는다. 가짜 Conda는 사용하지 않는다.

### 실제 출력에서 확인할 점

경로로 활성화한 환경은 프롬프트에 `(sg-name)` 대신 `(/home/learner/conda-envs/sg-name)`으로 보일 수 있다. 표시만 줄이려고 실제 환경 상태를 바꾸지는 않는다. 목록의 현재 선택 표시와 실제 Python 경로를 함께 확인한다.

현재 내장 Conda26.7.1에서는 export 파일명으로 형식을 추론한다. 수업의 `environment.yml` 대신 임의 이름을 쓴다면 `conda export -n 환경이름 --from-history --format=environment-yaml --file writing.yml`처럼 형식과 대상을 명시할 수 있다. 이 명령으로 실제 파일을 만들고 앱의 파일 탭에서 읽는 것까지 검사했다. `--file`의 부모 폴더는 미리 있어야 한다.
