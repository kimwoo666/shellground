"""Real Docker publication, resource observation and least-privilege practice."""
import random
import shlex
from docker_lessons import IMAGE

SPECS = (
    ('http', '공개 포트와 실제 HTTP 응답', 'run -p · port · curl -fSs --max-time', (
        '컨테이너에 포트 번호를 붙여도 서버가 저절로 생기지 않습니다. 제공된 http-response.sh와 Alpine의 nc가 실제 TCP 서버를 만듭니다. 서버 내부 포트는 8080, 문서 루트는 /www입니다. 이 서버는 GET /health.txt만 처리하는 작은 학습용 앱입니다.',
        '-p 127.0.0.1:호스트포트:8080은 전용 Linux guest의 loopback에서 컨테이너 8080으로 연결합니다. 개인 PC의 포트가 아닙니다. 주소를 생략하면 모든 호스트 주소에 공개될 수 있습니다. Docker port 이름으로 연결을 확인합니다.',
        'curl은 URL에 실제 요청합니다. -f는 HTTP 오류를 실패 종료로, -s는 진행 막대 숨김, -S는 실패 메시지 표시로 바꿉니다. --max-time 3은 최대 3초입니다. > 파일은 응답 본문을 저장합니다. curl -i는 헤더도 보여 주므로 본문 전용 파일에는 쓰지 않습니다.',
        '연결 거부는 접속/서버 문제, HTTP 404는 서버에 접속했지만 문서가 없는 문제입니다. 먼저 응답을 조사하고 원인을 고칩니다. 읽기 전용 bind도 호스트에서 고친 원본 파일의 변경은 반영됩니다. 포트 매핑 변경은 해당 컨테이너 재생성이 필요합니다.')),
    ('stats', '현재 사용량과 설정 한도 구별', 'stats --no-stream · inspect · State.Status', (
        'docker stats 이름은 계속 갱신합니다. --no-stream은 한 번만 출력합니다. MEM USAGE / LIMIT에서 왼쪽은 현재 사용량, 오른쪽은 한도입니다. 낮은 사용량이 낮은 한도를 뜻하지 않습니다. CPU 0.00%도 CPU 제한 실패의 증거가 아닙니다.',
        'inspect --format의 {{.HostConfig.Memory}}는 설정한 메모리 한도를 바이트로 표시합니다. 32 MiB = 32 × 1024 × 1024 = 33554432바이트입니다. 이 단원의 m 옵션은 MiB 단위입니다. 사용량은 측정마다 달라지므로 고정 숫자를 맞추지 않습니다.',
        'PIDS에는 프로세스와 커널 스레드가 포함됩니다. BLOCK I/O는 누적 전송량이지 MB/s가 아닙니다. Linux Docker CLI 메모리 사용량은 캐시를 제외하는 처리가 있어 원시 API 값과 다를 수 있습니다. stats를 성능 점수로 해석하지 않습니다.',
        '정지된 컨테이너의 0 표시/자료 부재는 메모리 한도가 0이라는 뜻이 아닙니다. State.Status와 HostConfig.Memory를 따로 읽으세요. 설정을 바꾸지 않고 요구 한도에 맞는 대상을 고르는 연습도 합니다.')),
    ('cpu', 'CPU 시간 상한과 실행 CPU 집합', '--cpus · --cpuset-cpus · cpu.max', (
        '--cpus 0.5는 CPU 시간 상한입니다. CPU 하나 분량의 절반을 넘지 못하도록 제한하지만 항상 50%를 소비하거나 CPU를 독점하는 것은 아닙니다. 대기 작업도 제한을 확인할 수 있습니다.',
        '이 guest는 cgroup v2입니다. 컨테이너의 /sys/fs/cgroup/cpu.max는 quota period 두 값입니다. 50000 100000은 비율 0.5, max 100000은 이 컨테이너 자체의 quota 없음입니다. 상위 환경의 제한까지 없다는 뜻은 아닙니다. 파일을 수정하지 않고 읽기만 합니다.',
        '--cpuset-cpus 0,1은 실행 가능한 CPU 번호 집합입니다. 시간 상한·예약·독점과 다릅니다. 실제 사용 가능한 번호는 available-cpus.txt, 이번에 고를 번호는 target-cpu.txt에 준비되어 있습니다. 다른 컴퓨터에서도 0–3이라고 가정하지 마세요.',
        'cpuset.cpus.effective는 실제 허용된 집합입니다. --cpus와 --cpuset-cpus를 함께 쓸 수 있습니다. inspect의 NanoCpus 또는 CpuQuota/CpuPeriod와 cgroup 파일을 함께 읽습니다. 같은 비율/같은 집합의 표기라면 동등한 설정입니다.')),
    ('io_weight', 'I/O 가중치와 성능 주장의 차이', '--blkio-weight · io.weight · io.bfq.weight', (
        '--blkio-weight 300은 블록 I/O 상대 가중치입니다. 300MB/s라는 속도 한도가 아니며, 600으로 올려도 두 배 속도를 보장하지 않습니다. 실제 효과는 장치·스케줄러·경쟁 작업·I/O 방식에 달려 있습니다.',
        'io-environment.txt에 실제 guest의 cgroup 버전과 장치 스케줄러를 제공합니다. 이 과정은 컨트롤러 설정까지만 확인합니다. dd/fio로 디스크를 바쁘게 만들거나 스케줄러를 바꾸지 않습니다. Docker 문서의 direct I/O 조건도 성능 해석에 중요합니다.',
        'Docker의 10–1000 요청값과 cgroup v2 값은 같지 않을 수 있습니다. 이 런타임은 io.bfq.weight가 있으면 원값을, 없으면 io.weight에 1+(요청값−10)×9999÷990의 정수 부분을 적용합니다. 300은 2930, 600은 5960이 될 수 있습니다. 제공된 실제 인터페이스를 읽으세요.',
        'inspect의 요청값, 제어 파일의 적용값, 성능 효과를 나눠 기록합니다. effect=unmeasured는 성능을 측정하지 않았다는 보고 형식입니다. 설정 적용 성공을 GPU·디스크 성능 시험 성공으로 확대하지 않습니다. 인터페이스가 없으면 준비 실패로 안내하며 자동 통과하지 않습니다.')),
    ('safe_launcher', '최소 권한 파일 처리 스크립트', '--cap-drop · --read-only · no-new-privileges', (
        '입력 한 파일을 결과 폴더로 복사하는 작업에는 네트워크·장치·root가 필요 없습니다. 이미 배운 --user 1100:1100, 입력 bind 읽기 전용, 출력 bind 쓰기 허용을 사용합니다. 인자 경로는 공백이 있어도 하나로 전달되도록 따옴표로 묶습니다.',
        '--cap-drop ALL은 Linux capability를 모두 제거합니다. UID가 비root라는 것과 별개입니다. --privileged, 추가 장치, Docker socket 공유는 이 작업의 요구 사항이 아닙니다.',
        '--read-only는 컨테이너 root 파일시스템을 읽기 전용으로 합니다. 별도 출력 bind의 쓰기 권한까지 없애지는 않습니다. 따라서 /out에는 결과를 쓸 수 있지만 임의 시스템 파일을 쓰는 설계는 피합니다.',
        '--security-opt no-new-privileges는 exec 때 setuid 같은 수단으로 추가 권한을 얻는 것을 막습니다. 기존 권한을 지우는 cap-drop과 역할이 다릅니다. 이 실습에서는 AppArmor/seccomp도 해제하지 않습니다.',
        'run-job.sh 입력절대경로 출력폴더절대경로 새컨테이너이름 계약으로 만듭니다. 입력이 없으면 컨테이너 생성 전에 비0으로 끝내고 기존 결과를 보존해야 합니다. 스크립트는 직접 실행 가능해야 합니다. 종료 컨테이너는 설정 확인을 위해 남깁니다.')),
)
KEYS = tuple('docker_runtime_' + row[0] for row in SPECS)


def units(Unit):
    return tuple(Unit('docker_runtime_' + key, 7, title, commands, '\n'.join(parts),
                      '현재 상태·적용된 설정·실행 결과를 구별하세요.') for key, title, commands, parts in SPECS)


def write_lines(path, lines):
    return "printf '%s\\n' " + ' '.join(shlex.quote(line) for line in lines) + ' > ' + shlex.quote(path)


def launcher_lines():
    return ['#!/bin/sh', 'set -eu', '[ "$#" -eq 3 ] || exit 2', '[ -f "$1" ] || exit 4', '[ -d "$2" ] || exit 5',
            'exec docker run --name "$3" --network none --user 1100:1100 --cap-drop ALL --read-only '
            '--security-opt no-new-privileges --memory 32m --cpus .25 --pids-limit 32 '
            '--mount "type=bind,src=$1,dst=/in.txt,readonly" --mount "type=bind,src=$2,dst=/out" '
            + IMAGE + " sh -c 'id -u > /out/uid.txt; id -g > /out/gid.txt; cp /in.txt /out/result.txt'"]


def http_run(start, name, port, address='127.0.0.1'):
    q = shlex.quote
    return (f'docker run -d --name {name} --memory 32m --cpus .25 --pids-limit 32 -p {address}:{port}:8080 '
            f'--mount {q("type=bind,src=" + start + "/server,dst=/srv,readonly")} '
            f'--mount {q("type=bind,src=" + start + "/www,dst=/www,readonly")} '
            f'{IMAGE} nc -lk -p 8080 -e /srv/http-response.sh')


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    if kind not in (*KEYS, 'docker_runtime_review') or practice not in (0, 1, 2): raise ValueError(kind)
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    start = f'/home/learner/docker/runtime{seed}'; name = f'sgr{seed}-task'; port = 40000 + seed
    key = kind.removeprefix('docker_runtime_'); q = shlex.quote
    plan = dict(docker_runtime=key, name=name, port=port)
    actions = []; goals = []
    wait = f'{IMAGE} sleep 3600'
    get = f'curl -fSs --max-time 3 http://127.0.0.1:{port}/health.txt > response.txt'
    if key == 'http':
        goals += [f'서비스 이름: {name}. guest의 127.0.0.1:{port} → 컨테이너 8080. 제공된 server 폴더를 /srv, www를 /www에 읽기 전용으로 연결하세요. /health.txt의 정상 HTTP 200 본문을 response.txt에 저장하세요.']
        if practice == 0:
            goals += ['제공된 실제 서버를 새 컨테이너로 시작하세요. www/health.txt와 원본 source-health.txt를 보존하세요.']
            actions += [http_run(start, name, port)]
        elif practice == 1:
            goals += ['현재 서비스는 404입니다. source-health.txt 원본으로 누락된 www/health.txt를 복구하세요. 같은 컨테이너와 시작 시각을 유지하세요.']
            actions += ['cp source-health.txt www/health.txt']
        else:
            goals += ['현재 서비스는 모든 주소에 공개되어 있습니다. 이 서비스 컨테이너만 교체하여 loopback으로 공개 범위를 좁히세요. 문서 파일은 모두 유지하세요.']
            actions += [f'docker rm -f {name}', http_run(start, name, port)]
        actions += [get]
    elif key == 'stats':
        goals += ['준비된 컨테이너의 상태·설정은 바꾸지 마세요. 통계 파일은 Docker 기본 표 형식으로 기록하세요. 순간 CPU/메모리 사용량을 고정 숫자에 맞출 필요는 없습니다.']
        if practice == 0:
            goals += [f'{name}의 한 번의 현재 통계를 stats.txt에, 설정된 메모리 한도(바이트)를 memory-limit.txt에 기록하세요.']
            actions += [f'docker stats --no-stream {name} > stats.txt', f"docker inspect --format '{{{{.HostConfig.Memory}}}}' {name} > memory-limit.txt"]
        elif practice == 1:
            goals += [f'{name}과 {name}-large 중 설정 메모리 한도가 32MiB 이하인 대상을 골라 이름만 selected.txt에 적으세요. 선택한 대상의 현재 통계를 stats.txt에 기록하세요. 지금 적게 쓰는 대상이 아니라 설정 한도로 판단하세요.']
            actions += [f"docker inspect --format '{{{{.Name}}}} {{{{.HostConfig.Memory}}}}' {name} {name}-large", write_lines('selected.txt', [name]), f'docker stats --no-stream {name} > stats.txt']
        else:
            goals += [f'정지된 {name}의 잘못된 보고를 수정하세요. status.txt에 실제 상태, memory-limit.txt에 설정 한도(바이트), usage.txt에 unobserved를 기록하세요. unobserved는 현재 실행 중 사용량을 관측하지 않았다는 인계 표기입니다. 재시작하지 마세요.']
            actions += [f"docker inspect --format '{{{{.State.Status}}}}' {name} > status.txt", f"docker inspect --format '{{{{.HostConfig.Memory}}}}' {name} > memory-limit.txt", write_lines('usage.txt', ['unobserved'])]
    elif key == 'cpu':
        goals += [f'{name}을 {IMAGE}의 sleep 3600으로 실행하세요. 메모리 32MiB, PID 한도32, 네트워크 없음도 유지하세요.']
        options = '--cpus .5' if practice == 0 else '--cpuset-cpus "$(cat target-cpu.txt)"' if practice == 1 else '--cpus .25 --cpuset-cpus "$(cat target-cpu.txt)"'
        if practice == 0: goals += ['CPU 번호를 별도로 고정하지 말고 CPU 시간 상한만 0.5로 제한하세요.']
        elif practice == 1: goals += ['target-cpu.txt의 CPU 한 개에서만 실행하게 하되 이 컨테이너 자체의 CPU 시간 quota는 추가하지 마세요.']
        else:
            goals += ['잘못된 기존 컨테이너만 교체하세요. CPU 시간 상한0.25와 target-cpu.txt의 CPU 한 개라는 두 요구를 모두 만족하세요. 단지 CPU 번호 한 개만 선택해서는 시간 상한이 생기지 않습니다.']
            actions += [f'docker rm -f {name}']
        actions += [f'docker run -d --name {name} --network none --memory 32m --pids-limit 32 {options} {wait}', f'docker exec {name} cat /sys/fs/cgroup/cpu.max /sys/fs/cgroup/cpuset.cpus.effective']
    elif key == 'io_weight':
        goals += ['설정 확인과 성능 측정을 구분하세요. effect.txt에는 effect=unmeasured라고 인계하세요. 이는 성능 효과를 측정하지 않았다는 뜻이며 효과가 없다는 단정도 아닙니다.']
        if practice == 2:
            goals += [f'기존 {name}의 “600MB/s 보장” 보고(effect.txt)를 고치세요. requested.txt에는 실제 요청 가중치만 적으세요. 컨테이너 설정과 ID는 보존하세요.']
            actions += [f"docker inspect --format '{{{{.HostConfig.BlkioWeight}}}}' {name} > requested.txt"]
        else:
            goals += [f'{name}에 I/O 가중치300을 요청해 대기 실행하세요.' + (f' {name}-high는 같은 조건에 가중치600으로 실행하세요.' if practice == 1 else '') + ' 둘 모두 메모리32MiB·CPU상한0.25·PID한도32·네트워크없음입니다.']
            for suffix, weight in [('', 300)] + ([('-high', 600)] if practice == 1 else []):
                actions += [f'docker run -d --name {name}{suffix} --network none --memory 32m --cpus .25 --pids-limit 32 --blkio-weight {weight} {wait}', f'docker exec {name}{suffix} sh -c \'if [ -f /sys/fs/cgroup/io.bfq.weight ]; then cat /sys/fs/cgroup/io.bfq.weight; else cat /sys/fs/cgroup/io.weight; fi\'']
        actions += [write_lines('effect.txt', ['effect=unmeasured'])]
    elif key == 'safe_launcher':
        goals += [f'실행 가능한 run-job.sh를 완성하고 {name}으로 실행하세요. 인자 계약: 입력절대경로 출력폴더절대경로 새컨테이너이름. 입력은 "{start}/input/source notes.txt", 출력 폴더는 "{start}/output"입니다.',
                  '새 컨테이너는 제공된 Alpine 이미지, UID/GID1100:1100, 네트워크없음, 메모리32MiB·CPU상한0.25·PID한도32, capability모두제거, rootfs읽기전용, 권한추가금지여야 합니다. 입력 한 파일은 /in.txt 읽기전용, 출력 폴더만 /out 쓰기허용으로 연결하세요.',
                  '입력 내용을 /out/result.txt로 복사하고 실행 UID/GID 숫자를 /out/uid.txt와 gid.txt에 기록하세요. 정상 종료한 컨테이너를 남기세요. 장치 추가·privileged·보안프로필 해제는 금지합니다. 입력 부재 때는 컨테이너를 만들지 않고 비0 종료하며 기존 출력을 보존하세요. 다른 공백 경로에서도 같은 계약으로 동작해야 합니다.']
        if practice == 1:
            goals += ['unsafe-draft.txt는 실행하지 마세요. 불필요한 권한과 누락된 인자 검사를 고친 뒤 새 스크립트에 반영하세요. 기존 output/result.txt를 previous-result.txt로 먼저 보존하세요. output/result.txt는 정상 입력일 때만 교체하세요.']
            actions += ['cp output/result.txt previous-result.txt']
        if practice == 2:
            goals += ['equipment.txt의 실제 장치/환경 조사를 읽고 equipment-status.txt에 device=unverified, gpu=unexecuted, x11=unexecuted 세 줄로 인계하세요. 이 과제는 CPU 파일 처리만 실행하며 장치·GPU·X11 성공을 판정하지 않습니다.']
            actions += [write_lines('equipment-status.txt', ['device=unverified', 'gpu=unexecuted', 'x11=unexecuted'])]
        actions += [write_lines('run-job.sh', launcher_lines()), 'chmod u+x run-job.sh', f'./run-job.sh {q(start + "/input/source notes.txt")} {q(start + "/output")} {name}']
    else:
        goals += [f'{name} HTTP 서버를 loopback {port}→8080, server→/srv·www→/www 읽기전용으로 실행하고 정상 /health.txt 본문을 response.txt에 저장하세요.',
                  f'{name}-worker는 대기 실행: 네트워크없음·32MiB·PID32·CPU시간0.25·target-cpu.txt의 CPU 하나·I/O가중치300. 현재 통계를 stats.txt에 기록하고 effect.txt에 effect=unmeasured를 적으세요.',
                  f'run-job.sh를 인자 계약(입력절대경로 출력폴더절대경로 새이름)으로 완성하여 "input/source notes.txt"를 output/result.txt로 처리하세요. 이름은 {name}-job입니다. UID/GID1100·네트워크없음·32MiB·CPU0.25·PID32·capability제거·rootfs읽기전용·권한추가금지·입력읽기전용·출력만쓰기허용, uid.txt/gid.txt도 기록, 정상 종료 컨테이너 유지, 입력부재시 비0·기존출력보존 조건입니다.']
        actions += [http_run(start, name, port), get, f'docker run -d --name {name}-worker --network none --memory 32m --pids-limit 32 --cpus .25 --cpuset-cpus "$(cat target-cpu.txt)" --blkio-weight 300 {wait}', f'docker stats --no-stream {name}-worker > stats.txt', write_lines('effect.txt', ['effect=unmeasured']), write_lines('run-job.sh', launcher_lines()), 'chmod u+x run-job.sh', f'./run-job.sh {q(start + "/input/source notes.txt")} {q(start + "/output")} {name}-job']
    goals += [f'keep.txt, source-health.txt, server 폴더 및 보호용 sgd{seed}-keep 컨테이너·볼륨·네트워크를 보존하세요. 준비된 조사 파일·원본 입력도 유지하세요.']
    return Mission(kind, seed, start, start, start + '/report.txt', start, '', '', '\n'.join(goals), '\n'.join(actions), practice=practice, review=plan)


def steps(unit, m):
    from learning_steps import LearningStep as S
    parts = unit.explanation.split('\n'); p = m.review; name = p['name']; key = p['docker_runtime']; lines = m.solution.splitlines()
    if key == 'http':
        commands = ['cat source-health.txt\ncat server/http-response.sh', lines[0], f'docker port {name}\ncurl -i --max-time 3 http://127.0.0.1:{p["port"]}/health.txt', lines[-1]]
        titles = ['제공된 서버와 문서', 'loopback에 서버 시작', '매핑과 응답 조사', '본문만 인계']
    elif key == 'stats':
        commands = [lines[0], lines[1], 'cat stats.txt\ncat memory-limit.txt', f"docker inspect --format '{{{{.State.Status}}}}' {name}"]
        titles = ['한 번의 사용량 표본', '설정 한도 조사', '같은 표의 서로 다른 의미', '상태도 함께 확인']
    elif key == 'cpu':
        commands = [lines[0], f'docker exec {name} cat /sys/fs/cgroup/cpu.max', 'cat available-cpus.txt\ncat target-cpu.txt\n' + f'docker run --rm --network none --cpuset-cpus "$(cat target-cpu.txt)" {IMAGE} cat /sys/fs/cgroup/cpuset.cpus.effective', lines[-1]]
        titles = ['시간 상한만 적용', 'quota 비율 읽기', '사용 가능한 CPU 조사', '현재 유효 집합 확인']
    elif key == 'io_weight':
        commands = ['cat io-environment.txt', lines[0], lines[1], lines[-1]]
        titles = ['효과와 설정 구별', '가중치 요청', '실제 제어 파일 읽기', '미측정 효과 인계']
    else:
        # Security flags are tried one at a time before the combined launcher.
        commands = [f'docker run --rm --network none --user 1100:1100 {IMAGE} id',
                    f'docker run --rm --network none --cap-drop ALL {IMAGE} sh -c \'grep CapEff /proc/self/status\'',
                    f'docker run --rm --network none --read-only {IMAGE} sh -c \'touch /not-writable\'',
                    f'docker run --rm --network none --security-opt no-new-privileges {IMAGE} sh -c \'grep NoNewPrivs /proc/self/status\'', '\n'.join(lines)]
        titles = ['사용자와 파일 계약', 'capability 제거', 'rootfs 쓰기 제한', '추가 권한 획득 제한', '전체 계약으로 실행']
    return tuple(S(title, explanation, command, '실제 출력과 설명을 비교하세요. 실패한 명령도 원인을 읽고 같은 환경에서 계속할 수 있습니다.') for title, explanation, command in zip(titles, parts, commands))
