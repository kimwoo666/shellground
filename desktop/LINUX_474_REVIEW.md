# Shellground 4.7.4-dev — Linux 검토판

2026-09-18. 새 Linux x86_64 실행파일을 만들고 배포 검사를 마쳤다. Windows·Android는 이 파일의 지원 플랫폼이 아니며 다음 포팅 단계다. 기존4.7.3 실행파일·바로가기·진도는 지우지 않았다.

## 실행

- 새 바로가기: [Shellground Linux 검토판4.7.4](../Shellground-Linux-4.7.4-Review.desktop)
- 실행파일: [Shellground](dist-linux-4.7.4-review/Shellground)
- 실행파일 옆의 `runtime` 폴더도 반드시 함께 있어야 한다. 실행파일 하나만 복사하면 실제 Linux/Conda/Jupyter 환경이 빠진다. 개인 PC의 Conda·Docker·WSL을 대신 사용하지 않는다.

터미널에서 직접 실행하려면:

```bash
"/home/pigeon/문서/ChatGPT/playground/desktop/dist-linux-4.7.4-review/Shellground" --mode real
```

Linux·Docker·ROS 2는 첫 모드 안의 분야 탭에서 선택한다. Python·데이터와 Conda·환경 관리는 같은 창 위쪽 모드로 이동한다. Jupyter는 Python 모드 안에서 노트북 과정을 선택한다. 설치 준비/실습 열기 뒤 최초 환경 준비에는 시간이 필요하다. 일반 화면 전환만으로 실습 VM을 새로 띄우지 않는다.

학습 완료와 소단계 진도는 자동 저장한다. 연습 입력 내용이나 실습 VM 파일 전체의 영구 저장과는 다르다. 이전 저장 키를 유지하며 완료 내역을 지우는 마이그레이션을 하지 않았다.

## 이번 범위

- Linux90단원·18복습, Docker25단원·5복습, ROS23단원·4복습. 등록441사례는 기존432개 증거를 검토 재사용하고 새ROS9개만 실행해 연결했다.
- ROS21–23: 입력 터미널/제어 대상, 실제 teleop, bag 일시정지·다음 메시지 하나, ±0.1 배율과 메시지 내용 구별. 12소단계 및 서로 다른9문제다.
- Python95항목285문제, Conda·pip60문제와 설치 과정, 실제 Jupyter5단원·1복습18문제의 기존 증거는 보존한다. 이 수치가 모든 문제를 이번에 다시 실행했다는 뜻은 아니다.
- 문제/개념/관련 실습의 완료를 서로 혼동하지 않는다. 단순 설명 이동은 명령을 실행하거나 완료를 부여하지 않는다.

전체 범위와 조건부 항목은 [현재 범위](CURRENT_COVERAGE.md), 새ROS의 실제 관측 한계는 [ROS 제어 학습](ROS_CONTROLS_TEACHING.md)을 따른다. GPU·장치·외부 NTP/RTC 기능을 실제 성공으로 표시하지 않는다. 이 노트북의 Linux 실행을 검증했으며 다른 Linux 배포판/CPU 아키텍처 전체의 실행을 검증했다고 주장하지 않는다.

## 새 파일에서 확인한 것

1. 22개 포함 자료와138단원 카탈로그 무결성, 포함된 과학 라이브러리의 실제 Python worker 계산·그림 출력·종료: PASS2.32초.
2. 한 창 내 모드 전환, Shift+Enter, 해당 화면의 F6, 퀴즈→pip 설명 이동 및 숨은 프로세스 정리: PASS. 캡처 두 장을 직접 확인했다.
3. 실제 Conda 활성화/같은 터미널 재채점/환경 내보내기·파일 확인: PASS61.9초, VM/overlay 정리.
4. 실제 Jupyter data 커널 선택·실행·채점·ipynb 저장: PASS96.73초, VM/overlay 정리.
5. 새ROS helper의 배포 경로 한 개(정지 상태에서 실제 오른쪽 키로 메시지 하나·채점·종료): PASS22.5초, VM/overlay 정리.

원60문제 Conda 검증과 현재 공통 셸의 차이는 두 파일뿐임을 원실행파일의 원문으로 재구성해 확인했다. 변경 영향5검사만 추가26.52초 PASS했으며 원runtime metadata의 fingerprint를 새 값으로 덮어쓰지 않았다. 관련 증거: `.jupyter-build/conda-shared-shell-carry.json`, `incremental-course-manifest-441.json`. 배포 보고서와 캡처는 `dist-linux-4.7.4-review/verification/`에 있다.

빌드와 실제 검사는 하나씩 CPUQuota60%/nice15로 실행했다. 관측 최고54°C, 마지막41°C였고, 검사 후 전용VM과 임시overlay를 정리했다. 약16GB의 불변runtime은 같은 디스크의 기존 파일과 inode를 공유해 중복 복사를 피했다. 해당 base 파일을 직접 수정하지 말고 새 버전으로 교체해야 한다.

## 파일 식별

- 크기:198,019,384바이트
- 새 SHA-256:`fbb2205e000f16af78b601a458411340de6a068270a28c2106fda74040c9755e`
- 기존4.7.3 SHA-256:`2e5fdcf539802a257466d6b686a8a41a59e24592876dea8af0bf832b39503735` — 변경 없음

이 문서는 Linux 마일스톤 당시의 검증 기록이다. 최신 배포와 플랫폼별 확인 범위는 [플랫폼 안내](../docs/PLATFORMS.md)를 따른다. 과거 컴퓨터 종료 요청은 철회되었으며 배포 작업은 컴퓨터를 종료하지 않는다.
