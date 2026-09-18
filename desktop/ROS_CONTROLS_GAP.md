# ROS 키보드 조작 — 최종 대조에서 확인한 좁은 공백

2026-09-18 후속: 아래에서 확인한 세 공백은 [ROS21–23](ROS_CONTROLS_TEACHING.md)의 12소단계·9문제로 구현하고 실제 키 입력82.08초 PASS까지 확인했다. 기존 ROS20단원/64사례 통과는 보존한다. 아래는 구현 전 대조 근거이며 최신 실행 상태는 연결 문서를 따른다.

사용자 ROS usage PDF25쪽은 `turtlesim_node`와 `turtle_teleop_key`를 별도 터미널에서 실행한다. PDF45쪽 터미널 캡처를 렌더링해 확인했다: bag info, 선택 토픽 play 및 Space(일시정지/재개), 오른쪽(다음 메시지 하나), 위/아래(재생률) 키 안내가 있다. 현재 과정은 기본 run/pub와 선택 재생을 실행 평가하지만 teleop 조작은 별도 목표가 없고, pause/rate는 설명만 있으며 오른쪽 한 메시지 진행은 설명/평가가 부족하다. 이는 전체 ROS64를 다시 검사할 이유가 아니라 추가할 조작 범위다.

## 최소 보완안

1. 실제 `turtle_teleop_key`: 터미널 포커스, 방향 키, 명령 수명과 Ctrl+C. 실제 DDS 메시지/거북이 반응과 원래 노드 보존을 구분.
2. bag 일시정지/재개와 한 메시지 진행: 처음부터 paused로 시작해 준비 중 메시지를 놓치지 않도록 하고, 실제 player 상태와 수신 메시지를 확인. 오른쪽은 일시정지에서만 한 메시지를 보낸다.
3. 재생률: 시작 rate와 실행 중 위/아래 변경, 지연과 주기/재생률을 혼동하지 않는 과제. 같은 수치로 원본 기록을 수정했다고 판정하지 않는다.

새5개 묶음을 억지로 채우지 않는다. 기존01–20 번호/저장 키/4복습과 이미 통과한 실행을 보존하고 필요한3단원만 검토한다. 소단계 필수, 활용은 숫자만 바꾼 반복을 피한다. 채점의 서비스를 읽기 전용으로 내부 관찰하는 것과 학습자에게 새 서비스 문법을 한꺼번에 가르치는 것은 분리한다.

## 실제 설치 능력 조사

`.jupyter-build/ros-controls-capabilities.json`: **complete15.11초**,5502 exit0,VM/overlay정리true. scope `ros-controls-capabilities-20260918`,invocation `3a4fafefb7614f1783993c443fe38099`,CPU60%/nice15. 기존 문제 실행/채점은 하지 않았다.

- rosbag2_transport/interfaces **0.15.17**,turtlesim **1.4.3**.
- 실제 도움말의 `--start-paused`/`-p`, `--rate`/`-r`, `--disable-keyboard-controls` 확인.
- 실제 `turtle_teleop_key` 실행파일 등록 확인.
- IsPaused.Response.paused(bool),GetRate.Response.rate(double),SetRate.Request.rate(double)/Response.success(bool),PlayNext.Response.success(bool),Pause/Resume의 빈 요청/응답을 실제 Python 타입에서 확인.

현재 [Humble player.cpp](https://github.com/ros2/rosbag2/blob/humble/rosbag2_transport/src/rosbag2_transport/player.cpp)는 위/아래에서 `rate + 0.1`/`rate - 0.1`을 사용한다. 화면의 “10%” 문구만 보고 현재 rate의 1.1/0.9배라고 가르치지 않는다. 설치된0.15.17에 맞춰 설명·실측을 진행해야 한다. 지원 인터페이스 조회는 실제 keyboard/통신 동작 통과를 대신하지 않는다.

PDF 원본/캡처는 재배포하지 않는다. 검토용 임시 경로는 `/tmp/shellground-final-audit.BVd2Ve/ros-play.png`와 `ros.txt`; Linux/부록의 기존 추출문은 `tmp/pdfs/linux-gap-audit/`를 재사용했다. 별도 Python/Jupyter 완료 증거는 이번 좁은 ROS 대조로 무효화하거나 반복하지 않는다.
