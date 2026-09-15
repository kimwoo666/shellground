# Shellground 4 개발 구조

현재 GUI는 `desktop/native_app.py`의 Qt 창이며 `SimEngine`만 사용합니다. 사용자 입력을 호스트 명령·네트워크에 전달하지 않습니다. Windows와 Linux 모두 동일한 Python 상태 모델을 사용합니다.

| 파일 | 역할 |
| --- | --- |
| sim_fs.py | 메모리 내부 POSIX 경로·파일·심볼릭 링크·권한 |
| sim_shell.py | 인용을 보존한 토큰화·확장·파이프·리다이렉션·명령 의미·종료 코드 |
| sim_docker.py | 이미지와 컨테이너 별도 상태, 생성/시작/종료/삭제·태그·스냅샷 |
| sim_engine.py | 기존 Qt 터미널 연결·입력 편집·nano·작업 제어·실습 생명주기 |
| sim_lessons.py | 신규 Linux/Docker 과제와 상태 기반 채점 |
| missions.py / practice_variants.py | 기존 26단원과 활용 변형, 신규 단원 연결 |
| checkpoints.py | 5단원마다 별도 종합 과제 |
| terminal_widget.py | 네이티브 터미널 렌더링·키 전달·스크롤 기록 |
| memory_notes.py | 명시적으로 저장하는 학습 노트 |

기존 `lab/lab.py`의 파일 결과 채점 규칙은 가상 Path·OS 어댑터를 통해 재사용합니다. 어댑터는 파일 작업·현재 위치·목록 조회를 메모리 모델로 교체합니다. 실제 컨테이너용 fixtures/serve 진입점은 실행하지 않습니다. `engine.py`는 이전 백엔드 보관 및 리소스 경로 함수 제공용입니다.

## 테스트

desktop 폴더에서:

```sh
QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:. python3 -m unittest test_simulator test_native_ui test_terminal_scrollback test_memory_notes test_checkpoints test_path_practice test_shutdown -q
QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime:.:.. python3 -m unittest discover -q
```

설치된 Python 환경에 의존성이 있으면 PYTHONPATH의 .runtime 부분은 불필요합니다. Windows에서는 해당 환경에 패키지를 설치한 뒤 `python -m unittest test_simulator`를 실행할 수 있습니다. Linux에서만 고정된 안전한 명령의 bash/GNU 대조 검사를 수행합니다.

이전 Docker 통합 검사는 기본적으로 건너뜁니다. 현재 앱 검증에 Docker 설치를 요구하지 않습니다. 명령 비교의 참조 bash 실행은 테스트 코드의 정해진 리터럴에 한정되며 앱 실행 경로와 분리됩니다.

## 확장 규칙

- 명령을 받았다는 이유만으로 통과 처리하지 말고 상태 변경과 실패 조건을 모델링합니다.
- 아직 지원하지 않는 문법·옵션은 명시적으로 오류를 반환합니다.
- 가상 경로를 host pathlib/subprocess에 넘기지 않습니다.
- 기존 단원·완료 키·기억노트를 유지합니다.
- 테스트에서 왼쪽 학습 목록을 가려 힌트를 자동 노출하지 않습니다.
- 루트/권한·프로세스·이미지/컨테이너 차이와 부작용을 회귀 검사합니다.
- 완전한 Linux 동작과 다른 부분은 README에 명시합니다.
