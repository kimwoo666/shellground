# Docker16–20: 대화형 수명·이미지 인계·선별 정리

2026-09-18 · 기존15단원과 진도 키를 유지하고 다섯 단원·복습을 추가했다. 개인 Docker나 자작 CLI가 아니라 전용 guest의 실제 Docker를 사용한다. 새 배포 실행파일 검증은 아직이다.

| 단원 | 소단계 | 서로 다른 활용 목표 |
| --- | --- | --- |
| 16 주 셸 | -i/-t/-d 역할, 내부 기록, exit, start -ai | 실제 종료된 같은 컨테이너 재시작·추가 / 이전 bind 학습과 출력 인계 |
| 17 attach | 기존 프로세스, 비공개 변수, 이탈 키, 재접속 | 이전 보고 보존 / 종료된 셸 재시작 후 명시적 종료 코드 |
| 18 exec | 별도 셸, 파일/변수 차이, 보조 셸 exit, -w/-e/-u | 프로세스 환경·작업 위치 / 숫자 사용자와 공백 경로 파일 소유권 |
| 19 압축 인계 | save, gzip, 형식 검사/load, 공유 태그 | 준비 아카이브 복원·ID 확인 / 두 태그와 이전 목록 보관 |
| 20 선별 정리 | 전체 목록, label 후보, 삭제 전 cp, prune | 영수증 구조 / 실패 로그·종료 상태 인계와 성공 컨테이너 보존 |

attach는 새 셸이 아니며 Ctrl+P 다음 Ctrl+Q는 연결 이탈, exit는 주 셸 종료다. exec는 별도 프로세스다. 실제 PTY에서 이를 조작하고, 주 컨테이너 ID·StartedAt·실행/종료 상태·파일과 셸 복귀를 확인한다. 새 입력 터미널 문제는 Tty/OpenStdin·기반 이미지·bind/RW 설정도 확인한다. 소단계는 생성 전 inspect를 하지 않고 실제 입력 순서를 나눈다.

--rm 뒤 사라진 설정을 추측해 완료 처리하지 않도록 Docker16 활용2는 검사용 종료 컨테이너를 남기는 bind 조합으로 설계했다. --rm 의미는 보존과 대비하며 기존 볼륨 단원의 실행 평가를 유지한다. 파일/환경 과제는 결과 상태를 평가하므로 모든 가능한 명령 이력을 강제하지 않는다. 프로세스의 일시적 -e/-w 선택 이력을 완전 추적한 것으로 표시하지 않는다.

gzip 아카이브는 실제 압축 헤더·tar manifest·설정·레이어 내용과 지정 태그를 비교한다. 제출 경로를 추출하거나 제출 이미지를 실행하지 않으며 읽기 크기·항목 수를 제한한다. 복원은 현재 Docker 이미지 ID를 확인한다. prune은 다른 라벨의 종료 컨테이너, 같은 라벨의 실행 컨테이너, 원래 이미지 태그/ID, 볼륨·네트워크와 /keep-me.txt를 보존한다. 실패 후 같은 상태에서 보완 가능하다. 모든 복습 평가도 7항목 이내다.

## 증분 검증

- `.jupyter-build/docker-sessions-new.json`: 신규15변형+복습 **16/16 PASS**, 오답/복구7묶음, **222.91초**, 소스 해시 전후 일치. 기존 통과 과정 재실행 없음.
- 거부: 호스트 출력 파일만 생성, attach 상태에서 미복귀, 잘못된 주 셸 관측값, 요청 소유권 불일치, .gz 이름만 붙인 비압축 tar, 잘못된 복원 ID, 보호용 종료 컨테이너 파일 변조, 영수증 구조 없이 삭제. 모두 같은 실습에서 복구 확인.
- 재시작 문제 준비가 실제 exited임을 별도 확인했다. Ctrl+P/Q·attach·exec·exit와 prune 확인 질문은 실제 PTY에 입력했다. 실제 셸 대신 출력 문자열을 흉내 내지 않는다.
- 55612 exit0, scope `docker-sessions-new-20260918`, invocation `5a4434960cda4d41ae5249e486cd85a9`. VM 종료/overlay 제거 true, scope inactive/dead. CPU60%/nice15, 수행 중 QEMU 약59%·온도41–43°C·scope 메모리 약878MiB. 시작 전54°C, 종료 후42–43°C. 한 번에 VM 하나만 실행했다.
- 새 계약3+직접 영향 등록/업로드/인수3 PASS0.063초. 감사 수정 뒤 새 순서/보존 계약1 PASS0.002초. 기존 전수 회귀는 실행하지 않았다.

## 자료 대조와 남은 범위

사용자 appendix 인쇄22–27쪽 대화형/정리/인계 부분을 대조했다. 원문은 재배포하지 않는다. 연결·새 프로세스의 의미는 [attach](https://docs.docker.com/reference/cli/docker/container/attach/), [exec](https://docs.docker.com/reference/cli/docker/container/exec/), 압축 이미지 인계는 [save](https://docs.docker.com/reference/cli/docker/image/save/), 종료 후보 필터링은 [container prune](https://docs.docker.com/reference/cli/docker/container/prune/)를 따른다.

실제 공개 포트 HTTP·stats/cgroup·cpuset·I/O 지원·최소 권한 실행 스크립트는 다음 묶음이다. 이 단원 통과를 GPU/X11/모든 자원 제약 실행 성공으로 확대하지 않는다.
