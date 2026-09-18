# Docker 21–25 — 실제 통신·자원·최소 권한

Linux 소스 구현·새16문제의 실제 검증을 완료했다. 새 실행파일이나 다른 OS 완료 증거가 아니다. 기존 1–20의 키와 진도는 유지하며 전수 실행을 반복하지 않는다.

| 단원 | 설명과 소단계 | 서로 다른 활용 |
| --- | --- | --- |
| 21 HTTP | 제공된 서버 → loopback 매핑 → 실제 헤더 → 본문 저장 | 같은 서비스의 404 복구 / 잘못된 공개 범위만 재생성 |
| 22 stats | 순간 표본 → 바이트 한도 → 각 열의 의미 → 정지 상태 | 사용량이 아닌 한도로 대상 선택 / 정지=한도0이라는 보고 수정 |
| 23 CPU | 시간 상한 → quota/period → 실제 CPU 번호 → 유효 집합 | affinity만 적용 / 시간 상한과 affinity를 함께 복구 |
| 24 I/O | 상대 가중치 → 지원 관측 → 실제 제어 파일 → 효과 미측정 | 두 요청의 적용 구별 / MB/s 보장이라는 잘못된 주장 수정 |
| 25 시작 스크립트 | UID·경로 계약 → capability → rootfs → 권한 추가 금지 → 통합 | 위험한 초안 수정·이전 결과 보존 / 장비 미실행과 CPU 작업 인계 |

예시15개가 아니라 각 단원의 예시·활용1·활용2 총15문제와 종합1문제다. 소단계는 4개씩, 안전 스크립트는 5개다. 활용 목표에 정답 명령이나 채점 단축키를 끼워 넣지 않는다. 파일 역할·목적지·보존 요구는 명시한다. 복습 평가는 최대7개다.

## 실제 실행과 채점 범위

- 앱 전용 Linux VM 안의 실제 Docker daemon만 사용한다. 개인 호스트의 Docker socket·장치·X11 소켓은 연결하지 않는다.
- 실제 Alpine BusyBox `nc -lk`와 제공된 작은 응답 스크립트가 TCP/HTTP를 처리한다. 가짜 Docker 출력이나 가짜 HTTP 응답 transcript가 아니다. 구현 범위는 `GET /health.txt`뿐이며 범용 웹 서버라고 표시하지 않는다. 요청이 없으면 서버는 기다린다.
- HTTP는 Docker의 실제 이미지·실행 상태·공개 주소/포트·읽기 전용 bind와 독립 GET의 상태/본문을 함께 검사한다. 404 복구 문제는 컨테이너 ID와 시작 시각도 보존해야 한다.
- stats는 제출 표본의 실제 대상 ID·이름·설정 한도·열의 유효한 형식을 확인한다. 사용량 숫자를 이후 새 표본과 일치시키지 않는다. **보고서만으로 과거 stats 명령 실행 이력을 증명하지 않는다.** 컨테이너 상태와 한도는 별도로 실제 daemon에서 읽는다. CPU/PID/누적 I/O를 성능 보장으로 해석하지 않는다.
- CPU는 실제 PID의 `/proc/PID/cgroup`으로 찾아간 cgroup v2에서 `cpu.max`와 `cpuset.cpus.effective`를 읽는다. quota/period 비율·동등 집합 표기는 인정한다. 컨테이너 자체의 quota 없음과 상위 제한 없음을 혼동하지 않는다. 코어 번호를 문제에 하드코딩하지 않는다.
- I/O는 현재 확인한 runc1.3.4 계열에서 BFQ 인터페이스가 있으면 요청 원값, 없으면 io.weight 변환값을 확인한다. 지원되지 않거나 확인되지 않은 runtime은 준비 오류이지 실행 성공이 아니다. [세부 조사](docker_io_weight_research.md). 현재 실제 요청300/600은2930/5960으로 관측됐다. 이 관측을 디스크 성능 효과로 바꾸지 않는다.
- 스크립트는 learner 권한·12초 제한으로 다른 공백 경로와 새 입력에도 실제 실행한다. 이미지/사용자/보안 설정/마운트/종료 상태/결과 소유권을 검사한다. Created만 된 컨테이너는 실행으로 인정하지 않는다. 입력 부재에서 기존 출력 파일 전체를 보존하는지도 확인한다. 임시 probe 컨테이너는 항상 정리한다.
- 교재 목표의 장치/GPU/X11은 별도 성공 범위다. 이 묶음에서 장치 접근은 미확인, GPU 계산·X11 표시는 미실행으로 명시한다. CPU 파일 처리 성공이나 DISPLAY 존재를 그 기능의 성공으로 표시하지 않는다.
- 채점은 상태와 결과 중심이며 완전한 명령 이력/악의적 guest root 변조 감사기가 아니다. 자작 Linux 시뮬레이터를 확장하지 않았다.

## 자원과 증분 검증

대기 컨테이너 위주이며 CPU 사용 루프·dd/fio 벤치마크·GPU 계산을 하지 않는다. 실습 VM 하나를 CPU 총합60%·nice15로 실행한다. 검증 중에만 절전 방지 요청을 유지한다. 같은 테스트를 반복하는 대신 완료 보고서와 소스 해시를 버전별로 남긴다.

환경 조사 두 번(15.18초,17.09초)은 필요한 미확인 인터페이스만 조회했고 각각 VM/임시 overlay를 정리했다. 실제 단계 검증과 분리된 준비 조사다. 신규 정적/직접 영향 검사는8개 중7개 즉시 통과, 활용 구분 보완 뒤 남은1개 통과했다. 후속 감사 경계1개도 통과했다.

실제 `.jupyter-build/docker-runtime-new.json`: **16문제 PASS, 오답/동등풀이9묶음,225.8초**,22909 exit0. scope `docker-runtime-new-20260918`, invocation `3ea3325b692f4b1d8d14ade82e0f5c02`. 시작/종료 소스 해시 동일, VM 종료·overlay 제거 true. 같은 본문이지만 전체 주소 공개, 불필요한 서비스 재생성, 사용량/한도 혼동, 정지=한도0, 잘못된 CPU/IO 설정, 가중치=처리량 보장, Created만 된 컨테이너, 원래 경로를 고정한 스크립트를 거부한다. 동등 quota/period도 통과한다.

CPUQuotaPerSecUSec=600ms를 실제 확인했고 QEMU nice15/약59.5%,scope메모리 약750MiB,당시 온도45°C였다. 종료 후46–47°C,디스크5.5GiB. 새 concept 링크 정적4검사0.031초·UI1검사0.045초도 PASS이며 VM/기존 퀴즈 채점을 재실행하지 않았다. `.jupyter-build/incremental-course-manifest-432.json`은 현재16+검토 재사용416을 묶으며 원416 자료는 보존한다.

## 공식 참고

소단계에서만 새로 실행하는 cpuset 조회·비root id·CapEff·읽기 전용 오류·NoNewPrivs 5명령도 별도 증분 PASS27.79초(24399 exit0,VM/overlay정리true)다. 참조 풀이16개는 반복하지 않았다. 보고서 `.jupyter-build/docker-runtime-microstep-delta.json`에 실제 출력·종료 코드와 동일 소스 해시를 보존했다.

- [Docker port publishing](https://docs.docker.com/engine/network/port-publishing/): loopback 공개와 버전별 주의.
- [Docker stats](https://docs.docker.com/reference/cli/docker/container/stats/): 일회 조회·캐시 처리·PIDS 의미.
- [Docker resource constraints](https://docs.docker.com/engine/containers/resource_constraints/): CPU 시간·CPU 집합과 메모리.
- [Linux cgroup v2](https://docs.kernel.org/admin-guide/cgroup-v2.html): 실제 CPU/IO 인터페이스.
- [Docker run](https://docs.docker.com/reference/cli/docker/container/run/): rootfs·capability·security-opt.
- [BusyBox](https://busybox.net/downloads/BusyBox.html): 실제 네트워크 도구. 현재 이미지의 `nc` 도움말도 직접 확인했다.
