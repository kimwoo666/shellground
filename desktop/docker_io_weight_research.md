# Docker 29.1.3 / runc 1.3.4 / cgroup v2 I/O 가중치 조사

공식 태그 소스와 Linux 문서를 읽은 정적 조사다. VM·컨테이너·벤치마크를 실행하지 않았으며, 아래 채점은 구현 제안이지 실행 통과 증거가 아니다. 배포판 패치가 있으면 실제 바이너리의 소스 버전도 별도로 확인해야 한다.

## 1. 요청 값이 전달되는 경로

- Docker CLI는 `--blkio-weight`를 부호 없는 정수로 받고 기본값은 `0`이다. `0`은 미지정이며, 명시하는 유효 범위는 `10–1000`이다. 이를 무조건 기본 가중치 500으로 설명하면 안 된다.[S1]
- Moby `docker-v29.1.3`은 0이 아닌 `HostConfig.BlkioWeight`를 OCI `Linux.Resources.BlockIO.Weight`에 그대로 복사한다. 여기서는 1–10000 변환을 하지 않는다.[S2]
- runc `v1.3.4`도 이 OCI 값을 `Resources.BlkioWeight`에 그대로 옮긴다. 해당 태그의 의존성은 `github.com/opencontainers/cgroups v0.0.4`다.[S3]
- Docker의 cgroup v2 `BlkioWeight` 지원 표시는 `io` 컨트롤러가 있는지를 기준으로 설정된다. 특정 장치의 BFQ/IOCOST 활성 여부를 확인한 결과가 아니다.[S4]
- 데몬이 지원하지 않는다고 판단하면 경고 후 요청 가중치를 0으로 버릴 수 있다. CLI 종료 상태 0만으로 적용 성공을 판정하지 않는다.[S5]

## 2. 실제 파일 선택과 변환

`opencontainers/cgroups v0.0.4/fs2/io.go`의 `setIo`가 결정한다.[S6]

1. 가중치 요청이 있으면 해당 cgroup의 `io.bfq.weight`를 읽기/쓰기 모드로 연다.
2. 열기에 성공하면 **요청 원값**을 `io.bfq.weight`에 쓴다.
3. 그 파일이 **없다는 오류(ENOENT)** 일 때만 `io.weight`로 전환하고 아래 정수 변환을 적용한다.
4. 권한 오류 등 다른 열기 오류는 실패다. BFQ 쓰기 실패도 `io.weight`로 자동 우회하지 않는다.

`io.weight` 기대값 = `1 + ((w - 10) * 9999) // 990` (`w`는 10–1000, `//`는 정수 나눗셈).[S7]

| Docker 요청 w | BFQ 파일에 쓰는 값 | BFQ 파일이 없을 때 io.weight 값 |
| --- | ---: | ---: |
| 10 | 10 | 1 |
| 100 | 100 | 910 |
| 300 | 300 | 2930 |
| 500 | 500 | 4950 |
| 600 | 600 | 5960 |
| 1000 | 1000 | 10000 |

두 파일이 모두 있으면 BFQ 파일이 우선이다. 두 파일 모두 같은 값이어야 한다는 채점은 잘못이다. 미지정 `0`은 이 변환으로 파일에 0을 쓰라는 뜻이 아니다. systemd cgroup 드라이버도 이 버전의 `UnifiedManager.Set`에서 최종적으로 fs2 관리자의 `Set`을 호출하므로 동일 경로를 사용한다.[S6–S8]

## 3. 설정 반영과 장치 효과는 다른 사실

- **BFQ:** 문서는 대상 블록 장치에서 BFQ가 활성 스케줄러여야 비례 배분을 얻는다고 명시한다. cgroup에 `io.bfq.weight`가 존재하고 값이 기록되었다고 해서 모든 디스크가 BFQ인 것은 아니다. BFQ의 기본 가중치는 100이며 자동 가중치 조정 같은 정책도 있으므로 단순 처리량 비율을 보장하지 않는다.[S9]
- **io.weight/IOCOST:** 커널 문서는 `CONFIG_BLK_CGROUP_IOCOST`와 장치별 `io.cost.qos`의 `enable`을 설명한다. IOCOST 제어는 기본 비활성이다. 파일의 값만으로 대상 장치의 IOCOST가 활성이라고 주장할 수 없다.[S10]
- 실제 효과 판단에는 컨테이너 파일시스템의 실제 저장 장치, 활성 스케줄러/제어기, 같은 장치의 경쟁 I/O 등 별도 조건이 필요하다. `io.stat`의 바이트 증가도 비례 배분 효과의 증명은 아니다.
- 가중치는 상대 우선순위이며 고정 MB/s 보장이 아니다. `600`이 `300`보다 항상 두 배 빠르다는 목표·정답·측정 수치를 만들지 않는다. io.weight 변환 결과 자체도 이 두 입력에서 정확한 2:1이 아니다.

## 4. 저부하 채점 제안 — 실제 설정까지만 완료 판정

1. 짧은 `sleep` 중심의 학습 컨테이너를 사용한다. 실제 ID, 실행 중 PID, `HostConfig.BlkioWeight`를 데몬에서 읽어 대상과 요청 값부터 확인한다. 학습자가 작성한 보고서는 적용 증거를 대신하지 않는다.
2. 게스트의 해당 PID에 대한 `/proc/<pid>/cgroup`과 cgroup2 마운트를 기준으로 실제 cgroup 경로를 찾는다. 컨테이너 이름을 붙여 경로를 추측하거나 다른 컨테이너 값을 읽지 않는다.
3. 실제 적용 경로에 맞춰 BFQ는 원값, 일반 io.weight는 변환값을 비교한다. 파일은 읽기만 하며 기본 항목의 `default N`/BFQ 단일 숫자 표현과 공백을 정규화한다. 장치별 항목을 기본 항목으로 오인하지 않는다.
4. 요청·실행·파일값이 모두 맞으면 **가중치 설정 확인**을 통과시킨다. 장치 효과는 별도 `미측정`/`지원 조건 불충족`/`확인 불가`로 표시한다. 장치 효과가 없다는 이유만으로 올바른 설정 실습을 오답 처리하지 않는다.
5. `io` 없음, 파일 부재/접근 실패, 요청 무시 경고 또는 잘못된 값은 설정 성공이 아니다. 지원 조건을 정확히 진단한 개념 문제는 별도로 완료할 수 있지만, 실행 완료 진도를 대신 부여하지 않는다.
6. 대표 오답: 요청 300인데 io.weight가 300, BFQ가 2930, 다른 컨테이너만 수정, inspect 값만 맞고 실제 파일값은 다름. 대표 동등 상태: BFQ 우선 경로에서 io.weight가 기존값인 상태, cgroupfs/systemd의 서로 다른 실제 경로.
7. 비파괴 범위: 스케줄러·컨트롤러·sysfs 설정 변경, 모듈 적재, 호스트 장치 접근, 성능 부하 실험은 하지 않는다. 채점이 지원 상태를 바꾸어서 성공을 만들어 내지 않는다.

## 공식 근거

- [S1 Docker CLI v29.1.3 opts.go](https://github.com/docker/cli/blob/v29.1.3/cli/command/container/opts.go): `blkio-weight` 선언과 Resources 전달.
- [S2 Moby docker-v29.1.3 oci_linux.go](https://github.com/moby/moby/blob/docker-v29.1.3/daemon/oci_linux.go): `WithResources`의 BlockIO.Weight.
- [S3 runc v1.3.4 go.mod](https://github.com/opencontainers/runc/blob/v1.3.4/go.mod) / [spec_linux.go](https://github.com/opencontainers/runc/blob/v1.3.4/libcontainer/specconv/spec_linux.go): 의존 버전과 OCI 값 복사.
- [S4 Moby cgroup2_linux.go](https://github.com/moby/moby/blob/docker-v29.1.3/pkg/sysinfo/cgroup2_linux.go): `applyIOCgroupInfoV2`.
- [S5 Moby daemon_unix.go](https://github.com/moby/moby/blob/docker-v29.1.3/daemon/daemon_unix.go): 미지원 요청 폐기와 범위 검사.
- [S6 cgroups v0.0.4 fs2/io.go](https://github.com/opencontainers/cgroups/blob/v0.0.4/fs2/io.go): `setIo`의 파일 선택·쓰기.
- [S7 cgroups v0.0.4 utils.go](https://github.com/opencontainers/cgroups/blob/v0.0.4/utils.go): `ConvertBlkIOToIOWeightValue`.
- [S8 cgroups v0.0.4 systemd/v2.go](https://github.com/opencontainers/cgroups/blob/v0.0.4/systemd/v2.go): `UnifiedManager.Set`의 fs2 위임.
- [S9 Linux BFQ documentation](https://docs.kernel.org/block/bfq-iosched.html): 활성 스케줄러, 가중치와 정책 조건.
- [S10 Linux cgroup v2 documentation](https://docs.kernel.org/admin-guide/cgroup-v2.html#io-interface-files): io.weight와 io.cost.qos/IOCOST 조건.
