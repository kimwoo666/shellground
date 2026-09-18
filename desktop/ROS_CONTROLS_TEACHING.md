# ROS 21–23: 실제 키보드 조작

2026-09-18. 기존 ROS01–20의 저장 키·64사례 증거를 보존하고 3단원·12소단계·9문제를 추가했다. 단원 수를 맞추려고 두 개를 더 만들지 않는다. 기존 5단원마다 복습 네 개도 그대로다.

| 단원 | 배우기 | 서로 다른 활용 |
| --- | --- | --- |
| 21 | 입력 터미널·전진/회전·이름공간·정지와 종료 | 회전 뒤 바뀐 방향으로 전진 / team만 움직이고 guard 보존 |
| 22 | start-paused·관측 준비·Space와 다음 메시지·종료 구분 | 처음 한 메시지만 조사 / 혼합 bag에서 선택 토픽 두 메시지를 순서대로 조사 |
| 23 | 초기 배율·위/아래 ±0.1·상태 관찰·내용 보존 | 같은 player에서 1.2→1.0 복구 후 다음 기록 / 배율이 Twist 값도 바꾼다는 잘못된 인계 수정 |

## 학습과 채점

원래 실행파일 `turtle_teleop_key`와 `ros2 bag play`에 터미널 키를 전달한다. 새 명령어를 흉내 내거나 키 입력에 맞춰 결과를 생성하지 않는다. 별도 터미널의 `cat control-status.txt`는 실제 관측의 표시다. 이 표시 파일의 내용을 정답 증거로 다시 읽지 않는다.

player의 IsPaused/GetRate를 비동기 조회하고 실제 메시지·pose·실행 프로세스의 수명과 함께 확인한다. 응답은 해당 PID/starttime 및 현재 전체 노드 이름에 귀속하며 만료되거나 다른 수명에서 받은 응답을 재사용하지 않는다. 과거 종료된 성공 기록이 있어도 새 player가 남아 있으면 종료 항목이 미완료다. 채점은 실습을 끝내거나 터미널을 닫지 않는다.

Humble rclpy는 최신 배포판과 달리 구독 콜백에 메시지 GID를 전달하지 않는다. 따라서 이 구현은 단일 발행 endpoint의 GID·고유한 전체 노드 이름·실행 중인 실제 도구의 PID/starttime이 일치하는 경우만 연결한다. 중복 노드 이름/복수 발행자의 모호한 메시지는 거부한다. 이는 **앱 전용 실습 환경의 관측 규칙이지 암호학적 PID–DDS 귀속 증명이나 악의적인 root 변조 방지 장치가 아니다.** [Humble executor](https://github.com/ros2/rclpy/blob/humble/rclpy/rclpy/executors.py), [구독 메타데이터 구현](https://github.com/ros2/rclpy/blob/humble/rclpy/src/rclpy/subscription.cpp).

관측기는 Fast DDS 공유 메모리 접근을 위해 learner UID로 실행한다. 채점 자료는 부모가 미리 연 쓰기 descriptor를 통해 root 소유 `/run` 파일에 남긴다. 원본 bag/keep.txt와 준비된 turtlesim 유지도 확인한다. DDS 그래프가 준비되지 않은 상태를 자동 통과로 취급하지 않는다.

시간·픽셀·좌표의 완전 일치, 화면 로그 숫자 또는 입력 문자열 일치를 요구하지 않는다. 중간 메시지 수 관찰과 마지막 안정 관찰을 구별한다. 최종 paused/stable을 관찰한 뒤 종료하도록 목표에 명시했다. 실제 같은 상태를 만드는 동등 서비스 조작은 결과 평가에서 허용할 수 있지만, 아래 키 입력 검증은 실제 PTY에 방향키·Space·Ctrl+C를 보낸 별도 증거다.

## 실행 증거

- `.jupyter-build/ros-controls-humble.json`: 새9/9 및 초기상태/미종료·회전만 수행·두 메시지 중 하나만 수신·잘못된 Twist 인계의 미완료 확인. **82.08초, exit0(61580)**, 시작/종료 소스 해시 동일, VM/overlay 정리 true.
- 기존 `ros-controls-new.json`과 `ros-controls-repair.json`은 관측 준비/콜백 API 실패 기록이며 통과 증거로 사용하지 않는다. 기존 ROS64는 다시 실행하지 않았다.
- 추가 경계는 원보고서를 보존해 선택적으로 읽는다. `ros-controls-boundaries-v2.json`의 잘못된 실제 발행 토픽 거부1건, `ros-controls-remaining-boundaries.json`의 동명 외부 발행자 거부/새 이름·이름공간의 player 허용/이전 성공 뒤 남은 player 거부3건이 통과했다. 두 보고서는 후속 진단 꼬리에서 실패했으므로 보고서 전체를 PASS로 표시하지 않는다. 모든 VM/overlay는 정리됐다.
- 마지막 진단의 백그라운드 작업 종료는 `kill %1` 대신 실제 `fg %1`→Ctrl+C로 별도 확인했다. `ros-background-return.json` **19.4초 exit0(49539)**, 정리true이며 학습 문제 재실행0개다. 작업 종료만 했다고 메시지 조사 목표를 완료 처리하지 않는 것도 확인했다. 경계4건이나 정상9개를 다시 돌리지 않았다.
- 새 교육/판정6검사와 guarded upload1검사 통과. 후속 graph 모호성/공통 선택기2검사, Qt 실제 방향키·Space·Ctrl+C 전달1검사, 등록73사례/배포카탈로그138단원 영향2검사 통과. 클래스 이름을 잘못 지정한 빌드 검사 호출은 정확한 항목 하나만 재실행해 통과했다.
- 실제 runtime: rosbag2 0.15.17, turtlesim1.4.3. ↑/↓가 ±0.1임을 실제 조회로 확인했으며 “10%”를 곱셈으로 가르치지 않는다. [Humble player](https://github.com/ros2/rosbag2/blob/humble/rosbag2_transport/src/rosbag2_transport/player.cpp).

CPUQuota600ms/초·nice15·하나의 VM만 사용했다. 실행 중 QEMU46.9%, scope 메모리약1GB, CPU40–41°C를 확인했다. 검사 중에만 절전을 억제하고 종료 후 해제한다. 새로운 Linux 배포파일의 실행 및 Windows/Android 포팅 완료를 이 자료로 주장하지 않는다.
