# Linux·Docker 학습 범위 감사

후속2026-09-18: 입출력81–85/시스템86–90 및 Docker16–25까지 독립 과정·실제 증분 검증을 보완했다. 현재135단원27복습/432사례의 버전별 증거 연결은 [현재 범위](../CURRENT_COVERAGE.md),실제 HTTP·자원·스크립트는 [Docker21–25](../DOCKER_RUNTIME_TEACHING.md)를 따른다. 아래 표는 과거95단원 당시 감사이며 현재 누락 목록으로 그대로 사용하지 않는다. 장비 기능·세부 옵션 최종 대조·배포는 별도다.

후속 개념 연결: [Linux·Docker 개념 UI](../SYSTEM_CONCEPTS.md)에23카드/32문항을 등록하고 별도 진도·재시도·관련 단원 설명 이동을 검증했다. 아래 표의 개념 평가 누락 일부는 이 기록으로 보완하며, 장치·대화형 Docker 등 실제 실행 누락을 개념 정답만으로 닫지는 않는다.

후속 구현(2026-09-18): 아래는 Linux60단원 당시 감사 기록이다. 이후 APT61–65, 인증/로그인66–70, 셸 심화71–75, 프로세스76–80 및 각 복습은 실제 증분 검증까지 완료했다. [현재 범위](../CURRENT_COVERAGE.md), [APT](../APT_TEACHING.md), [인증](../AUTH_TEACHING.md), [셸](../SHELL_TEACHING.md), [프로세스](../PROCESS_TEACHING.md) 기록이 해당 누락 판정보다 우선한다. 나머지 누락이 자동으로 완료된 것은 아니다.

작성: 2026-09-18. 범위: 현재 로컬 소스의 Linux·Docker 과정과 기존 `MATERIAL_COVERAGE.md` A–P, `DEVELOPMENT_GOALS.md`의 최소 범위. **PDF 원문을 새로 읽거나 웹 조사·VM 실행·테스트를 수행하지 않았다.** ROS·Python·Conda·Jupyter 및 자율주행 개념 Q–S는 이번 판정 대상이 아니다. 아래의 “필수”는 기존 두 범위 문서에 명시된 항목이라는 뜻이며, PDF 전체 명령/옵션의 재대조 완료를 뜻하지 않는다.

결론: 현재 등록된 과제의 검증과 강의 전체 범위의 충족은 다르다. Linux·Docker에 이미 구현된 범위는 상당하지만, 셸·프로세스·계정 인증·패키지 복구·시스템 조사와 Docker의 일부 핵심 범위가 아직 독립적인 평가로 연결되지 않았다. Jupyter 완료나 등록 과제 전수 PASS만으로 이 누락을 닫아서는 안 된다.

## 1. 현재 등록 범위와 검증 근거

`mode_curriculum.py:51–62`의 실제 과정은 Linux 60 + Docker 15 + ROS 20 = **95단원·19복습**이다. 이번 대상은 Linux·Docker **75단원·15복습**이다. Linux 순서는 `linux_course.py:6–19`, 복습 편성은 `real_course_checks.py:28–41`에 있다.

### 70 → 95는 강의 누락 25개를 새로 해결한 것이 아니다

이전 70단원은 Linux 35 + Docker 15 + ROS 20이었다(`VERIFICATION.md:66`). 현재 증가한 25개는 다음 분할이다.

- 파일 조회·처리 10개: `linux_ls_detail/ls_sizes/ls_order/grep_basic/head/tail/line_count/pipe/tar_list/deb_info`.
- 계정·권한 15개: `admin_uid/group_ids/passwd/mode_symbols/mode_numbers/chown/chgrp/group_create/user_uid/user_home/user_shell/user_primary/user_extra/group_append/group_primary`.

이는 이미 복합 단원·설명에 있던 기능을 작은 설명과 평가로 분리한 개선이다(`linux_course.py:21–71`, `option_guides.py`, `admin_lessons.py:5–15`). 새 완료 키·준비 상태·조합 문제가 생겼지만, 아래의 PATH·로그인·의존성·장치 등 새 범위를 25개 채웠다는 의미는 아니다. Docker 11–15의 과거 추가는 실제 범위 확장이지만, **70→95 변경에서는 Docker가 15개로 유지**됐다.

| 현재 다루는 능력 | 실제 단원/근거 | 완료 범위를 좁혀 읽을 부분 |
| --- | --- | --- |
| 경로, 논리/물리 경로, 숨김·상세·크기순·재귀 목록, 파일 생성/편집/복사/이동/삭제 | `navigate`, `pwdpaths`, `lsintro`, `linux_ls_*`, `list/long/lsoptions/recursive`, `mkdir/touch/edit/duplicate/rename/remove/workspace/copy`; `missions.py`, `linux_course.py:99–135` | 실제 GNU nano와 목록 결과 평가가 있다. 목록의 모든 옵션이나 필드 의미를 묻는 개념 시험까지 포함하지는 않는다. |
| 문자열 선택, 앞/뒤 줄, 줄 수, 파이프, 파일 탐색, 다운로드·압축 해제·패키지 정보/추출 | `linux_grep_basic/head/tail/line_count/pipe`, `grep/find/curl/wget/archive/deb`, `linux_tar_list/deb_info`; `linux_course.py:136–190`, `linux_learning.py:50–103` | `dpkg-deb --info/--extract`는 설치/의존성 복구가 아니다. gzip 처리된 tar를 읽는 능력과 Docker 이미지를 gzip으로 보관하는 능력도 다르다. |
| 환경변수 전달, 첫 인자를 쓰는 스크립트, 작업 선택·중지/재개, APT 목록 갱신·설치 | `sim_env/author/jobs/apt`; `sim_lessons.py:37–41`, `linux_learning.py:104–131` | 실제 모드에서도 저장 키가 `sim_`일 뿐 실제 도구 경로다. 환경변수 전체·고급 셸·프로세스 조사·APT 전체를 다룬다는 뜻은 아니다. |
| UID/GID·그룹·계정 레코드, 파일/폴더 권한, 소유권, 사용자 생성, 그룹 추가·변경 | `admin_*` 20개; `admin_lessons.py:5–15`, `admin_focus.py:20–164` | `useradd -u/-g/-G/-s/-d/-m`, `groupadd -g`, `usermod -a -G/-g`는 더 이상 전부 미구현이 아니다. `admin_passwd`는 **getent passwd 조회**이지 비밀번호 설정이 아니다. |
| 이미지/컨테이너 생명주기·파일 작업·교체·태그·commit·save/load·실행 설정 | `sim_images/run/lifecycle/exec/cleanup/update/tag/commit/save/limits`; `sim_lessons.py:42–51`, `docker_guides.py:8–66` | `-e/-p/--memory/--cpus` 설정은 다룬다. 실제 포트 통신·자원 사용량/성능 해석과 구분한다. |
| bind ro/rw·숫자 사용자·권한 복구, 볼륨 보존/백업, bridge/DNS·연결 복구, Dockerfile·버전 보존, 로그/종료 코드 진단 | `docker_bind/volume/network/build/diagnose`와 `docker_review`; `docker_lessons.py:18–48,88–273` | 오래된 A–P 표의 Docker 행 전체 “없음”은 현재와 다르다. 이 다섯 단원으로 장치·GUI·모든 자원 옵션까지 대체하지 않는다. |

기존 실행 증거는 별도로 읽어야 한다. `VERIFICATION.md:14–22`에는 새 Linux 25단원×3변형 75시나리오, Linux 12복습 및 작성된 소단계의 실제 VM PASS가 기록돼 있다. `VERIFICATION.md:62–73`에는 Docker 심화 5단원×3변형, 복습·오답·대안 풀이의 실제 검사 기록이 있다. **이번 감사에서 이 검사를 재실행한 것은 아니다.**

진행 중인 Linux·Docker 240검사는 `verify_real_course.py:81–85`가 등록된 75단원×3변형 + 15복습을 선택한 것이다. seed도 그 코드의 7251이다. 성공하더라도 증명하는 범위는 해당 선택·소스 버전의 초기 미완료/참조 풀이 후 통과이며, 등록되지 않은 강의 명령이나 모든 가능한 동등 풀이·오답까지 자동으로 검증하지 않는다. 진행 중 검사를 이 문서에서 완료로 판정하지 않는다.

## 2. 확실히 남은 필수 학습·평가 범위

판정 기준은 “실제 바이너리가 게스트에 있을 수 있는가”가 아니라 **학습자가 선택할 목표·준비 자료·실습 또는 개념 답안·판정이 연결돼 있는가**다. 현재 과정 등록과 문제 생성 경로(`missions.py:121–140`, `linux_course.py`, `admin_focus.py`, `sim_lessons.py`, `docker_lessons.py`, `real_course_checks.py`), 실제 소단계와 설명을 대조했다. 아래 항목을 평가하는 별도 Linux·Docker 개념 문제도 이 경로에서 확인되지 않았다.

| 묶음 / 기존 필수 근거 | 확실히 없는 독립 목표 또는 개념 평가 | 비슷하지만 대체하지 못하는 현재 항목 |
| --- | --- | --- |
| Linux 구성·명령 종류 — A | 커널/배포판/POSIX, 터미널/셸, builtin/외부 명령의 구분과 `type` 조사, ASCII/UTF-8·텍스트/바이너리 구분 | `pwdpaths`의 builtin pwd 설명과 다운로드 시 바이너리 주의는 일부 안내다. 구성 요소·명령 종류·인코딩을 판단하는 문제는 없다. |
| 목록 해석·계층 조사 — B | `tree`로 계층을 조사하는 과제, `ls -l` 필드의 의미를 답으로 판별하는 개념 문제 | `linux_ls_detail`은 필드를 설명하고 실제 상세 목록 출력을 평가한다. `sim_apt`의 tree 설치 및 `tree --version` 확인은 계층 조사 실습이 아니다(`linux_learning.py:27–31,125–131`). |
| 입력 종료·페이지 탐색·실행 경로 — C 및 개발 목표 31행 | `cat > 파일`과 EOF/Ctrl+D, `more` 탐색·q 종료, `/bin/ls` 복사 후 `./ls` 실행, shebang의 역할을 구별하는 평가 | `report`/`linux_line_count`/`linux_pipe`에 `>`/`<`/파이프가 있고, `docker_diagnose`에 stderr `2>&1`, `docker_build` 소단계에 **`>>` 실제 사용도 있다**. 이들을 전부 없는 것으로 되돌리지 않는다. 스크립트 권한/실행은 `script`에서 평가한다. |
| 셸 검색·현재/자식 셸·인자·분기 — D 및 개발 목표 31행 | PATH 검색 순서 복구·`whereis`, `source`와 자식 셸 실행 차이, `$0`/`$#`/`$*`와 조건 분기, `bash -C`의 noclobber | `sim_env`는 export/unset/자식 전달, `sim_author`는 `"$1"`과 공백 인자를 다룬다. 준비된 Docker 검사 스크립트 내부의 `if`가 학습자의 조건문 작성 과제는 아니다. ROS/Conda의 source 실습을 Linux 셸 범위 완료로 중복 계산하지 않는다. `"$@"`는 기존 문서가 별도 보충으로 분류했다. |
| 프로세스·스레드와 작업 제어 — E/F 및 개발 목표 31행 | PID/PPID/TID·공유 메모리/스택, `ps -U`/`ps -Lf`, `pstree -p -u`, foreground/background 전환 `fg/bg`·Ctrl+Z, SIGKILL과 SIGTERM 차이, `ls -alR … > … &` 조합 | `sim_jobs`는 두 sleep 작업의 TERM/STOP/CONT와 다른 작업 보존을 다룬다(`linux_learning.py:116–124`). Linux의 프로세스 조사와 Docker `ps`는 서로 다른 범위다. |
| 인증·로그인·관리자 정책 — G/H | `passwd`로 암호 설정, `su -` 로그인 환경 비교, sudoers 정책·setuid 의미/권한 판단 | 계정/그룹 생성과 UID/GID/홈/셸·chmod/chown은 이미 있다. `admin_users` 설명도 암호 설정·로그인 전환을 별도 범위라고 명시한다(`admin_lessons.py:13`). 이름이 `admin_passwd`인 조회 문제를 암호 실습으로 세면 안 된다. |
| 패키지 갱신·제거·의존성 — I | upgrade, `apt list --upgradable`, remove/purge 설정 보존 차이, `--fix-broken`·의존성 복구, `dpkg` 설치/패키지 상태의 차이를 다루는 과제 | `sim_apt`는 update/install과 `apt list --installed` 소단계까지 있다. upgrade/remove는 설명에만 등장한다. 준비 단계의 내부 `apt-get remove tree`도 학생 과제가 아니다. snap은 아래 환경 조건도 필요하다. |
| 시스템·네트워크·시간 정보 — J | `uname`/`hostname`, `ifconfig -a`/`ip`, `date +%s`, UTC/epoch/RTC 구분, `hwclock`/`timedatectl`·NTP 상태 해석 | 현재 Linux 60개에는 해당 조사/답안 단원이 없다. Docker 내부 ping이나 pandas 날짜 API는 이 시스템 관리 범위를 대체하지 않는다. 호스트 시각 변경을 요구해서는 안 된다. |
| 컨테이너 구조·대화형 수명 — K/L | VM과 컨테이너·공유 커널·client/daemon·OCI의 구조 판단, `attach`와 `exec` 차이 및 대화형 입력/이탈·exit가 원래 프로세스에 미치는 영향 평가 | 이미지/컨테이너·태그·레지스트리와 파일/RAM의 차이는 설명·실습 일부에 있다. `sim_exec`는 `bash -c` 파일 작업을 평가하고 `-it`/exit는 설명한다(`learning_steps.py:160–163`). 대화형 접속/이탈의 결과를 구별하는 과제는 없다. |
| 이미지 보관·정리 선택 — M | Docker 이미지의 gzip 보관/복원, prune의 삭제 대상·보존 대상을 판단하는 과제, 공유 레이어와 표시 크기의 해석 문제 | `sim_save`는 비압축 tar의 save/load, `sim_cleanup`은 특정 rm/rmi를 평가한다. `prune`은 사용하지 말라는 주의이고, SIZE 중복 합산은 설명이다(`docker_guides.py:32–60`). 일반 tar.gz 해제만으로 Docker 압축 아카이브 평가를 대신하지 않는다. |
| 실제 포트 통신·자원 관측 — N/P | 공개 포트로 실제 서비스 요청/응답, cgroup 개념, cpuset과 CPU 시간 한도의 차이, I/O 가중치와 보장량 차이, `docker stats` 수치 해석·제한 전후 관측 | `sim_limits`의 실행 명령은 sleep이며 **포트 설정만 평가한다고 명시**한다(`docker_guides.py:61–66`). `docker_network`는 컨테이너 간 별칭 ping으로 다른 목표다. CPU/메모리 설정값 확인을 실제 부하/사용량 평가로 표시하면 안 된다. |
| 장치·그래픽 실행 조건 — O | privileged/device/GPU 및 X11/XAUTHORITY·SDL/Vulkan·CUDA 실행 조건/위험 판단, 실행 스크립트의 옵션 해석/수정 | `docker_build`의 Dockerfile과 준비된 `app/run.sh`는 있다. 특정 장치·디스플레이·GPU 옵션을 조합하는 `dkrun.sh` 학습을 대신하지 않는다. 실제 장비 검증 조건은 다음 절과 분리한다. |

`option_guides.py`에는 `grep -E/-F/-n/-v`, `find -size/-mtime`, `ls -t/-r`, 이어받기 등 더 넓은 참고 옵션이 있다. **설명 존재를 채점 완료로 세지 않는다.** 다만 이 추가 옵션 각각이 PDF의 필수인지 보충인지 이번 로컬 범위 문서만으로 확정하지 않았으므로, 위 확정 목록을 근거 없이 늘리는 데 사용하지 않았다.

## 3. 장비·플랫폼 또는 별도 실습 준비가 필요한 항목

| 항목 | 구분과 완료 조건 |
| --- | --- |
| GPU/CUDA·USB 등 장치, X11/XAUTHORITY·SDL/Vulkan | 현재 등록 과정에 의미·위험·요구 조건을 묻는 평가도 없다. **개념 문제는 장비 없이 보완 가능**하지만 실제 실행은 맞는 장치/드라이버/디스플레이 및 앱 전용 격리 경로가 마련된 뒤 별도로 검증해야 한다. 미지원 오류를 이해한 것과 GPU 실행 성공은 다른 완료다. 개인 호스트 장치를 연결한 것으로 가정하지 않는다. |
| privileged/device의 최소 권한 설계 | 장비가 없다는 이유로 옵션 의미·위험 비교 자체를 누락할 이유는 없다. 실제 권한/장치 실습은 폐기 가능한 앱 전용 환경에서 준비해야 하며 가짜 성공 출력으로 대체하지 않는다. |
| snap·시스템 서비스, RTC/hwclock·NTP 동기화 | 해당 서비스·시계 인터페이스가 있는지 확인할 전용 환경이 필요하다. 현재 제공 여부를 이번 감사에서 확인하지 않았다. 읽기 전용 정보 조사·출력 해석부터 분리하고, 호스트 시계 변경이나 외부 서비스 사용을 전제로 삼지 않는다. |
| cpuset·cgroup·I/O 비교 | 게스트의 CPU 구성과 커널/자원제어 조건에 맞춘 판정이 필요하다. 옵션 설정·의미 판단과 실제 효과 측정을 구분한다. 일정한 성능 배수나 가상 수치를 정답으로 약속하지 않는다. |
| 암호/로그인/sudoers, APT 의존성·설정 보존, 실제 공개 포트 | 특수 물리 장비 때문에 미루는 항목은 아니다. 다만 안전한 전용 계정·정책·오프라인 패키지·실제 서비스 준비와 상태 채점은 필요하며, 현재 그런 학생 과제가 등록됐다는 증거는 없다. |

Windows·Android·macOS 포팅은 위 학습 범위의 대체물이 아니다. 사용자 지시인 **실제 Jupyter 커널 선택과 남은 학습 범위 검증 후 포팅**을 위해서는, 최소한 이 표의 항목별로 구현·설명만 있음·평가 없음·환경 필요를 남겨야 한다. “등록된 모든 문제 PASS”를 “강의 명령 전체 구현 완료”로 바꾸지 않는다.

이번 산출물은 이 감사 문서 한 개뿐이다. 과정·문제·채점·진도·VM·검증 보고서는 변경하지 않았다.
