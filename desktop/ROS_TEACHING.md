# ROS 2 설명 보강과 소단계 — 4.4.0-dev

## 2026-09-18 증분 마감

기존 통과를 반복하지 않고 남은domain/action6문제·복습4개와 변경된play3개만 실행했다. `.jupyter-build/ros-uncovered-delta.json` **13/13 PASS,210.31초**, VM/임시 디스크 정리true,38674 exit0. CPUQuota60%/nice15,검사 중49–50°C·종료 뒤42°C. 원래49개 통과는 완료된 실행 이벤트47798에서 복구하여 원 실패 상태·지문·실행 시각을 보존했다. `ros-focused`의9개와 새13개 등 선택된 버전별 증거로 등록64사례를 연결했으며 전수 재실행은 하지 않았다. [증거 연결 방식](INCREMENTAL_ACCEPTANCE.md). 새 배포/타 OS 완료는 별도다.

## 2026-09-18 실제 문제 감사 보완

- bag 기록 예시는 발행자가 없는 cmd_vel의 구독 로그를 먼저 기다리지 않는다. pose 구독 확인 → 다른 터미널의 주기 발행 → cmd_vel 구독 확인 → 발행 중단 → 기록 종료 순서다.
- 짧은 bag 재생 예시에 `--delay 2`를 추가하고 DDS 상대 발견과 발행 시작의 시간 차이를 설명한다. CLI 앞에서 단순히 기다리는 것과 다르며, 2초가 모든 환경에서 수신을 보장한다고 가르치지 않는다.
- 기존 8개 수신 판정은 줄이지 않았다. 문제에 메시지 수를 명시하고 채점 목록에 관측한 수신 수를 표시한다. 누락 시 같은 환경에서 재생할 수 있다.
- [ROS 2 Humble rosbag2의 공식 옵션 정의](https://github.com/ros2/rosbag2/blob/humble/ros2bag/ros2bag/verb/play.py)와 실제 VM에서 옵션을 확인했다. 전체 등록 문제의 최종 재검증은 진행 중이다.

## 기존 설명·소단계 구성

20개 기존 단원의 목표·완료 키를 유지하며 `ros_guides.py`에 전체 해설을 보강했다. 추가 피드백에 따라 `learning_steps.py`에서 개념별 설명/실습을 직접 나눴다. 배우기에는 현재 소단계만 표시하고 전체 해설은 F3에서 제공한다. Docker 15개·ROS 20개 단원 모두 3~6개 소단계다. 글자 수에 따라 문단만 잘라 넘기는 방식이 아니라 별도 목적/실행 명령/확인 항목을 갖는다.

기존 번호를 유지하고 내부 소단계를 필수 진행 흐름에 넣어 달라는 사용자 선택을 반영했다. 이번에는 3~6개 소단계로 조절 가능하여 큰 단원 번호를 추가하지 않았다. 소단계 이동은 실습을 재생성하지 않는다. 읽거나 F6을 누른 것을 채점 통과로 기록하지 않으며 전체 조합 예시·활용의 실제 상태 판정을 유지한다.

- 환경/오버레이: source의 목적, 현재 셸과 새 셸, 설치 경로·작업공간, setup/local_setup, pkg prefix.
- 실행/조사: 패키지·실행파일·노드·이름공간·토픽·타입, 준비된 노드와 직접 실행하는 문제 구분.
- 토픽: list -t/info -v, YAML의 따옴표·콜론·중첩, --once/-w와 --rate/--times, echo/hz의 관찰 의미.
- 파라미터: 노드별 설정과 환경변수 차이, 타입·변경 거절, dump/load와 영구 저장의 차이, 읽기 전용 항목의 부분 실패.
- bag: 토픽 선택·기록 폴더·실제 메시지·정상 종료·info 필드·선택 재생. 기록/재생은 노드 전체 상태 복원이 아님을 구분.
- 도메인/서비스/액션: 42의 의미, remap의 :=, 요청/응답과 목표/피드백/결과, 접수와 완료 구분.
- 활용 2의 사전 설명: reports 사본 인계와 find 인자, 작업 후 nodes-after.txt, 같은 도메인·새 터미널 source·저장 폴더·리다이렉션.
- echo/record의 예시와 힌트에는 중단·터미널 전환 주석을 추가했다. 시험 본문에는 해설을 자동 삽입하지 않는다.

## 대조한 공식 자료

앱에 포함된 Humble 기준. 공식 문서 사이트 렌더링이 차단되어 공식 저장소의 공개 Humble 문서/소스를 확인했다.

- [환경](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Configuring-ROS2-Environment.rst), [오버레이](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-Client-Libraries/Creating-A-Workspace/Creating-A-Workspace.rst)
- [노드](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Nodes/Understanding-ROS2-Nodes.rst), [토픽](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Topics/Understanding-ROS2-Topics.rst), [pub 옵션 구현](https://github.com/ros2/ros2cli/blob/humble/ros2topic/ros2topic/verb/pub.py)
- [파라미터](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Parameters/Understanding-ROS2-Parameters.rst), [bag](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Recording-And-Playing-Back-Data/Recording-And-Playing-Back-Data.rst)
- [서비스](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Services/Understanding-ROS2-Services.rst), [액션](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Understanding-ROS2-Actions/Understanding-ROS2-Actions.rst)

## 검증 범위

`test_ros_guides.py`: 20단원의 해설 연결·기존 요약 유지·추가 목표의 사전 설명·시험 해설 비노출·실제 Qt 배우기/F3/활용 화면. 파일 인계 예시는 임시 폴더에서 실제 Bash/find/cp로 공백 이름·숨김 파일·원본 보존·얕은 탐색·재실행을 검사한다. `test_learning_steps.py`는 소단계 수/길이, 실습별 이름/경로, 모의 Docker 10개 순서 실행, 이동 중 파일/터미널 보존과 미완료 상태를 검사한다. `test_learning_steps_live.py`는 명시적으로 켠 전용 KVM 게스트에서 실제 Docker 옵션/마운트/볼륨/네트워크/빌드/진단 소단계 실행과 원래 목표 채점을 검사한다. ROS 런타임과 채점 규칙은 바꾸지 않았으며 ROS 모든 활용·복습 및 Windows 전체 검증 완료를 뜻하지 않는다.
