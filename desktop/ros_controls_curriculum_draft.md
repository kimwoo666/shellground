# ROS 21–23 키보드 제어 보충 초안

범위: 기존 ROS 1–20·복습·진도를 보존하고 3단원/9문제를 뒤에 추가하는 설계이며, 아직 구현·실행 완료가 아니다. PDF 25쪽·45쪽은 부모가 확인한 범위 정보를 사용했으며 이 작업에서 원문을 다시 읽지는 않았다.
공식 Humble 소스를 확인했다. 부모의 실제 환경 조회 결과는 rosbag2_transport/interfaces 0.15.17, turtlesim 1.4.3이다. 아래 서비스 관측은 채점 내부용이며 학습자에게 새 서비스 호출 문법을 암기시키지 않는다.

## 공통 준비·판정 계약

- 앱 전용 guest의 실제 turtlesim/teleop/rosbag2만 사용한다. 터미널·노드·도메인·네임스페이스를 화면에 표시하고, 준비 실패를 키 조작 성공으로 처리하지 않는다.
- 키는 **해당 프로그램이 전경 실행 중인 터미널**에 전달한다. 그림 창·다른 셸·스크롤 영역의 포커스와 구분한다. 방향키를 앱 단축키가 가로채면 미완료 안내이지 학습자 오답이 아니다.
- 실제 DDS 메시지·발행자 식별·pose·player 서비스 상태를 관측한다. 문구 출력, 입력 문자열 또는 최종 그림만으로 키 제어 성공을 추정하지 않는다.
- 상태 전환 문제는 목표에 중간 관찰 단계를 명시한다. 관측 준비 완료→조작→상태 확인 순서이며, 마지막에는 학습자 프로세스를 종료하고 셸로 돌아온다. 종료 자체를 pause 성공으로 세지 않는다.
- 현재 상태만으로 키와 동등 서비스 조작의 과거 경로를 구별할 수는 없다. 기본 채점은 올바른 실제 도구·상태 전환을 허용하고, 키 실습 검증은 별도 실제 PTY 입력 증거로 구분한다. 숨은 키 문자열 강제는 금지한다.
- 원본 bag·보호 노드/거북이·환경을 보존한다. 관측은 타임아웃이 있는 짧은 대기로 하고 busy loop·긴 반복 재생·기존 ROS64 재실행은 요구하지 않는다.

## 21. teleop: 입력 창과 제어 대상을 맞추기 (`ros_teleop` 제안)

선수: run, nodes/topics, domain/namespace. 설명: teleop은 `turtle1/cmd_vel`에 Twist를 발행하는 별도 노드다. ↑/↓는 전진/후진, ←/→는 회전이다. 화면 위쪽으로 이동한다는 뜻이 아니라 현재 거북이 방향 기준이다.[T1,T2]
준비: 중앙의 실제 거북이, 다른 발행자 없음, pose/발행자 관측 준비. 예시는 기본 이름공간, 활용2만 `/team`과 `/guard`의 서로 다른 실제 turtlesim을 제공한다.

1. **대상 확인:** 준비된 노드·토픽 전체 이름과 시작 pose를 본다. 새 터미널도 같은 ROS 환경·도메인을 사용한다.
2. **입력 노드 시작:** `ros2 run turtlesim turtle_teleop_key`로 시작하고 그 터미널을 선택한다. 안내문이 떠 있는 것만으로 이동 완료가 아니다.
3. **짧은 입력 관찰:** ↑를 짧게 누른 뒤 놓는다. 실제 Twist와 이동을 확인한다. ←를 누르면 회전임을 구별하며 정확한 픽셀·고정 이동 거리를 요구하지 않는다.
4. **범위·종료 확인:** `/team` 대상에는 `--ros-args -r __ns:=/team`을 붙이는 이유를 설명한다. 노드 이름만 바꾸어도 토픽 대상이 바뀌는 것은 아니다. 끝에는 `q` 또는 Ctrl+C로 종료한다.[T1,T2]

| 문제 | 서로 다른 목표·준비 | 실제 판정·대표 오답 |
| --- | --- | --- |
| 예시 | 기본 거북이를 앞으로 움직이고 입력을 놓은 뒤 정지 관찰, teleop 종료 | teleop 발행자의 양의 linear.x·회전 없는 명령, 실제 전진 및 이후 속도 0, 종료 확인. 그림 창에만 키 입력/명령 없는 pose 조작은 불충족. |
| 활용1 | 같은 거북이를 먼저 제자리 왼쪽 회전시킨 뒤 바뀐 방향으로 전진하고 종료 | angular.z>0·linear.x=0 단계 뒤 linear.x>0 단계와 실제 방향/위치 변화. 전진만 한 풀이·두 명령을 동시에 섞은 것만으로 대체 불가. 정확한 각도·거리 대신 방향·순서 판정. |
| 활용2 | 기본 이름공간의 teleop 초안은 `/team` 거북이와 연결되지 않음. 제어 대상을 고쳐 `/team`만 이동, `/guard` 보존 | 대상 전체 토픽 경로와 실제 publisher 연결, team 이동·guard 위치/방향 유지. `__node`만 변경, 다른 도메인, guard를 움직인 뒤 되돌리기는 불충족. 올바른 토픽 remap도 동등 허용. |

주의: 키를 놓을 때 teleop이 즉시 0 Twist를 발행한다고 설명하지 않는다. turtlesim의 명령 시간초과로 잠시 뒤 정지하므로, 정지 판정은 충분한 관찰 여유를 둔다.[T2,T3]

## 22. bag: 일시정지·재개와 다음 메시지 하나 (`ros_bag_control` 제안)

선수: bag info/play/--topics, 21의 터미널 포커스. 설명: Space는 player 시간의 정지/재개 토글이다. →는 **일시정지 상태에서 선택된 재생 흐름의 다음 메시지 하나**를 발행하며, 시간 1초 이동이나 거북이 한 걸음 보장이 아니다.[B1,B2]
준비: 알려진 순서·서로 구별되는 내용·충분한 남은 메시지를 가진 유한 bag. 활용2만 cmd_vel과 보조 토픽이 섞인 bag. 앱 관측 구독자의 DDS 연결 완료를 먼저 확인한다.

1. **정지 상태로 시작:** `ros2 bag play control_bag --start-paused --topics /turtle1/cmd_vel`을 설명·실행한다. `--start-paused`는 입력 시간을 확보하고 처음 메시지를 놓치지 않게 한다.[B3]
2. **재개 후 다시 정지:** player 터미널에서 Space→실제 메시지 수 증가 확인→Space. 앱은 실제 `IsPaused`와 안정된 메시지 수를 함께 보여 준다.
3. **하나만 진행:** paused 확인 뒤 →를 짧게 한 번 누른다. 다음 내용 한 개를 확인하고 paused가 유지되는지 본다. 키를 길게 누르면 반복 입력될 수 있다.
4. **범위와 종료:** 선택 토픽과 전체 bag을 구별하고 Ctrl+C로 종료한다. 종료 전에 관찰 단계가 완료되어야 하며 bag 원본은 수정하지 않는다.

| 문제 | 서로 다른 목표·준비 | 실제 판정·대표 오답 |
| --- | --- | --- |
| 예시 | 초기 paused→재생 중 실제 메시지 수 증가→다시 paused로 멈춘 뒤 종료 | 같은 player의 true→false→true와 수신 증가/안정 구간을 확인. 프로세스 종료·EOF·토픽 불일치로 메시지가 안 오는 상태는 pause가 아님. |
| 활용1 | 처음부터 paused인 재생에서 다음 cmd_vel 딱 한 개만 조사하고 종료 | 연결 완료 기준선 뒤 기대한 첫 내용 정확히 1개, paused 유지, 추가 발행 없음. Space로 잠깐 전체 재생, → 반복, 보고서만 작성은 불충족. |
| 활용2 | 혼합 bag에서 cmd_vel만 골라 앞 두 명령을 한 개씩 조사하고 보조 토픽은 재생하지 않기 | 첫 관찰 Δ1·다음 관찰 Δ1과 내용 순서, player에서 보조 토픽 발행 없음. 전체 bag의 첫 두 레코드를 무조건 정답으로 삼지 않음. |

주의: pause는 이미 수신한 이동 명령을 취소하지 않는다. turtlesim pose는 계속 발행될 수 있으므로 전체 토픽 수나 pose 정지만으로 판정하지 않는다. DDS 전달 중인 메시지는 정지 직후 유예 뒤 기준선을 확정하고, 재생 완료 뒤에는 PlayNext를 요구하지 않는다.[T3,B2]

## 23. bag: 배율 조정과 메시지 내용 구별 (`ros_bag_rate` 제안)

선수: 22. 설명: `--rate 0.5`는 시작 배율, ↑/↓는 실행 중 배율 조정이다. 확인한 Humble 코드는 **현재 배율±0.1**이다. 화면의 “10%”를 현재값×1.1/0.9로 가르치지 않는다. 이 수정은 0.15.9 변경 기록에 있다.[B2,B3,B4]
준비: 표준 속도 1.0, 유한 bag과 남은 메시지, 관측 가능한 player. 활용1은 1.2배로 잘못 설정되어 중간 위치에서 paused인 같은 player를 제공한다.

1. **처음 배율 이해:** 예시 `ros2 bag play control_bag --start-paused --rate 1.0 --topics /turtle1/cmd_vel`. 1.0/0.5/2.0은 재생 시간의 배율이지 Twist 속도 필드 값이 아니다.
2. **올리기:** paused 상태에서 ↑ 한 번. 앱의 실제 `GetRate`가 약 1.1인지 확인한다. pause는 유지되고 자동 발행은 늘지 않아야 한다.
3. **내리기:** ↓ 한 번으로 약 1.0을 확인한다. 0 이하로 내려 pause를 대신하려 하지 않는다. 유효 배율은 양수이며 부동소수점 값은 문자열 완전 일치로 비교하지 않는다.[B5]
4. **효과 구별·종료:** 정한 배율에서 Space로 재개하여 실제 메시지를 관찰한 뒤 멈추고 종료한다. 내용은 그대로이며, 짧은 구간의 벽시계 측정이 정확한 비율을 보장하지는 않는다.

| 문제 | 서로 다른 목표·준비 | 실제 판정·대표 오답 |
| --- | --- | --- |
| 예시 | 같은 player에서 1.0→1.1→1.0을 관찰한 뒤 실제 재생·종료 | 실제 rate 전환(허용오차 예: 1e-6), paused 유지 구간과 이후 실제 발행 확인. 로그 숫자만 수정하거나 1.1→0.99를 정답으로 삼지 않음. |
| 활용1 | 중간까지 읽은 1.2배 player를 재시작하지 않고 1.0으로 복구한 뒤 이어서 재생 | 같은 프로세스·player 연결, 1.0 상태와 저장된 다음 내용부터 연속 발행. `--rate 1.0`으로 새 실행하여 처음부터 되풀이하는 것은 복구 목표 미달. |
| 활용2 | “재생을 빠르게 하면 Twist 값도 커진다”는 잘못된 인계를 실제로 조사: paused에서 1.0→1.2, →로 다음 한 개를 확인하고 설명 수정 | rate≈1.2·paused·정확히 다음 1개·원본 Twist와 동일한 내용. 원본 bag/메시지 값을 1.2배로 고치거나 단순 보고서만 바꾸면 실패. 설명은 시간 배율과 내용 보존의 의미를 평가. |

속도 제어 성공은 실제 rate 상태+재생 가능으로 판정한다. 처리량/정확한 벽시계 시간/거북이 최종 좌표는 속도 정답 조건으로 쓰지 않는다. 설치 버전이 바뀌면 공식 구현과 기대 전환을 재확인한다.

## 공식 근거와 검증 경계

- [T1 Humble turtlesim 공식 튜토리얼 원본](https://github.com/ros2/ros2_documentation/blob/humble/source/Tutorials/Beginner-CLI-Tools/Introducing-Turtlesim/Introducing-Turtlesim.rst): teleop 터미널 포커스, 짧은 이동, remap, 종료.
- [T2 Humble teleop 소스](https://github.com/ros/ros_tutorials/blob/humble/turtlesim/tutorials/teleop_turtle_key.cpp): 상대 토픽, 방향별 Twist, 키를 놓을 때 0 명령을 자동 발행하지 않는 구조.
- [T3 Humble turtle 소스](https://github.com/ros/ros_tutorials/blob/humble/turtlesim/src/turtle.cpp): 이동 명령 수신·시간초과·pose 발행.
- [B1 Humble PlayOptions](https://github.com/ros2/rosbag2/blob/humble/rosbag2_transport/include/rosbag2_transport/play_options.hpp): Space/→/↑/↓ 기본 매핑.
- [B2 Humble player 구현](https://github.com/ros2/rosbag2/blob/humble/rosbag2_transport/src/rosbag2_transport/player.cpp): pause, play_next, ±0.1, IsPaused/GetRate 서비스.
- [B3 Humble play CLI](https://github.com/ros2/rosbag2/blob/humble/ros2bag/ros2bag/verb/play.py): --start-paused/--rate/--topics/--disable-keyboard-controls.
- [B4 Humble 변경 기록](https://github.com/ros2/rosbag2/blob/humble/rosbag2_transport/CHANGELOG.rst): 0.15.9의 키보드 rate 수정. [B5 시계 구현](https://github.com/ros2/rosbag2/blob/humble/rosbag2_cpp/src/rosbag2_cpp/clocks/time_controller_clock.cpp): 양수 배율·paused 시간 처리.
- 이 문서는 설계/공식 소스 확인만 수행했다. DDS 연결·포커스·동시 관측·일시정지 직후 전달 여유의 실제 검증과 채점 구현은 부모 작업이며, 이 초안만으로 키 입력 검증 완료를 주장하지 않는다.
