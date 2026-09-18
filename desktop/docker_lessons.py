"""Real Docker exercises: declarative fixtures and outcome requirements, not a mock CLI."""
import random
import shlex
from docker_guides import expanded_explanation

IMAGE = 'localhost:5000/training/alpine:latest'


def write_lines(path, text):
    """One physical shell line even for a multi-line Dockerfile."""
    return "printf '%s\\n' " + ' '.join(shlex.quote(line) for line in text.splitlines()) + ' > ' + shlex.quote(path)


def protection_goal(seed):
    return f'keep.txt와 보호용 sgd{seed}-keep 컨테이너·sgd{seed}-keep-data 볼륨·sgd{seed}-keep-net 네트워크를 보존하세요.'


SPECS = (
    ('bind', '읽기 전용 입력과 쓰기 가능한 결과', 'docker run --mount · -v · ro/rw · -u',
     'bind mount는 Docker 호스트의 폴더를 컨테이너 경로에 연결합니다. 여기서 호스트는 앱 전용 Linux이며 사용자 PC가 아닙니다.\n'
     '--mount type=bind,src=절대경로,dst=/input,readonly는 읽기 전용입니다. -v "절대경로:/input:ro"도 가능합니다.\n'
     '출력 폴더는 별도로 읽기·쓰기 연결하세요. readonly를 생략하면 기본값은 쓰기 가능입니다.\n'
     '-u 1100:1100은 숫자 UID/GID입니다. 컨테이너의 계정 이름이 없어도 지정할 수 있으며, 호스트 파일 권한도 이 숫자로 적용됩니다.\n'
     '공백이 있는 전체 마운트 인자는 따옴표로 묶습니다. docker inspect의 Mounts에서 Source, Destination, RW를 확인합니다. -v는 없는 원본 경로를 디렉터리로 만들 수 있지만 --mount는 기본적으로 오류를 냅니다.'),
    ('volume', '컨테이너를 바꿔도 데이터 보존', 'docker volume create/ls/inspect/rm · --mount type=volume',
     '이름 있는 volume은 Docker가 관리하는 저장 공간입니다. bind와 달리 호스트 경로 대신 볼륨 이름을 사용합니다.\n'
     'docker volume create notes\n--mount type=volume,src=notes,dst=/data\n'
     '컨테이너를 삭제해도 이름 있는 볼륨은 남습니다. 새 컨테이너에 같은 이름을 연결하면 데이터를 다시 읽습니다.\n'
     'docker volume inspect notes로 확인하고, 불필요해진 볼륨만 docker volume rm notes로 삭제합니다. 사용 중이면 삭제가 거절됩니다.\n'
     '이름을 생략한 익명 볼륨과 다른 이름의 빈 볼륨은 기존 저장소가 아닙니다. --rm은 종료된 일회성 컨테이너를 정리하며 기반 이미지를 삭제하지 않습니다. 백업은 별도 읽기 전용 원본과 쓰기 가능한 목적지를 연결해 수행합니다.'),
    ('network', '컨테이너 이름으로 연결하고 복구', 'docker network create/inspect/connect/disconnect · --network-alias',
     '사용자 정의 bridge 네트워크에서는 컨테이너 이름과 별칭을 DNS 이름으로 사용합니다. 기본 bridge와 구분하세요.\n'
     'docker network create teamnet\ndocker run --network teamnet --network-alias api ...\n'
     '실행 중인 컨테이너도 docker network connect teamnet 이름으로 연결하고 disconnect로 특정 연결만 끊을 수 있습니다.\n'
     '기존 컨테이너를 지우지 않고 연결만 복구할 때 유용합니다. docker network inspect로 실제 참가 컨테이너와 주소를 확인합니다.\n'
     '같은 네트워크의 이름 기반 통신에는 -p가 필요하지 않습니다. -p는 호스트로의 포트 공개이며 별도 개념입니다. 여기서는 외부 인터넷 없이 게스트 안의 컨테이너끼리만 통신합니다.'),
    ('build', 'Dockerfile로 재현 가능한 이미지 만들기', 'docker build -t · FROM/COPY/RUN/WORKDIR/USER/CMD',
     'Dockerfile은 이미지를 만드는 절차입니다. FROM은 기반 이미지, COPY는 빌드 문맥의 파일 복사, RUN은 빌드 중 실행입니다.\n'
     'WORKDIR은 이후 작업 경로, USER는 기본 사용자, CMD는 컨테이너를 시작할 때의 기본 명령입니다. RUN과 CMD의 실행 시점은 다릅니다. ENV APP_MODE=ready는 이미지의 기본 환경변수 설정입니다.\n'
     'docker build --network=none -t training/report:v1 app\n마지막 app은 빌드 문맥입니다. COPY는 그 문맥 안의 파일을 찾습니다.\n'
     'docker run --rm training/report:v1로 기본 실행을 확인합니다. 새 태그로 다시 빌드해도 이전 이미지와 실행 중 컨테이너가 자동으로 갱신되지는 않습니다.\n'
     '이 과정의 기반 이미지는 게스트 내부 저장소에 준비되어 있어 인터넷 다운로드나 패키지 설치 없이 빌드합니다.'),
    ('diagnose', '실패한 컨테이너의 원인을 찾아 복구', 'docker logs · inspect --format · start · stderr',
     'docker ps -a로 종료된 컨테이너도 확인합니다. docker logs 이름은 애플리케이션의 표준 출력/오류 기록입니다.\n'
     "docker inspect --format '{{.State.ExitCode}}' 이름은 종료 코드를 보여 줍니다. 0이 아니면 실패 원인을 조사하세요.\n"
     'docker logs 이름 > failure.log 2>&1은 두 출력 스트림을 같은 파일에 보관합니다. >만 사용하면 표준 오류가 빠질 수 있습니다.\n'
     '설정·입력 파일·숫자 UID 권한을 확인해 고친 뒤 docker start로 같은 컨테이너를 다시 실행합니다. 삭제 후 새로 생성하는 것과 다릅니다.\n'
     '아무 로그나 만들거나 실행 중이라는 표시만 맞추지 말고 실제 출력과 원본 보존까지 확인하세요.'),
)


def units(Unit):
    return tuple(Unit('docker_' + key, 6, title, commands, expanded_explanation(key, explanation),
                      'inspect로 현재 설정과 상태를 확인하고 목표 조건과 비교하세요.')
                 for key, title, commands, explanation in SPECS)


def make_docker_mission(kind, seed=None, practice=0):
    from missions import Mission
    seed = seed if seed is not None else random.SystemRandom().randrange(1000, 9999)
    key = kind.removeprefix('docker_')
    if key not in {s[0] for s in SPECS} | {'review'}: raise ValueError(kind)
    if practice not in (0, 1, 2): raise ValueError(practice)
    start = f'/home/learner/docker/session{seed}'
    name, peer, volume, network = (f'sgd{seed}-{s}' for s in ('worker', 'peer', 'data', 'net'))
    image = f'training/report{seed}:v1'
    q = shlex.quote
    plan = {'docker_real': key, 'files': {'keep.txt': 'unrelated document\n'},
            'initial_volumes': {}, 'initial_networks': [], 'initial_containers': [],
            'containers': [], 'file_goals': {}, 'image_goals': [], 'volume_goals': {},
            'connections': [], 'absent_containers': [], 'preserve_containers': [],
            'preserve_volumes': [], 'initial_images': []}
    goals, solution = [], []
    def file(path, text, **meta):
        plan['files'][path] = {'text': text, **meta} if meta else text
    def container(n, **spec):
        plan['containers'].append(dict(name=n, running=True, **spec))
    def initial(n, args, command, **extra):
        plan['initial_containers'].append(dict(name=n, args=args, command=command, **extra))
    def bind(src, dst, rw): return dict(type='bind', source=start + '/' + src, destination=dst, rw=rw)
    def vol(v, dst, rw=True): return dict(type='volume', source=v, destination=dst, rw=rw)
    def mount(m):
        return '--mount ' + q(f'type={m["type"]},src={m["source"]},dst={m["destination"]}' + ('' if m['rw'] else ',readonly'))
    def start_container(n, mounts=(), options='', img=IMAGE, command='sleep 3600'):
        return f'docker run --name {n} -d {options} ' + ' '.join(mount(m) for m in mounts) + f' {img} {command}'
    def dockerfile(message='message.txt'):
        return f'FROM {IMAGE}\nWORKDIR /app\nCOPY {message} message.txt\nRUN printf "built\\n" > /build-stamp\nUSER 1100:1100\nCMD ["cat", "message.txt"]\n'
    if key == 'bind':
        file('input data/message.txt', f'release {seed}\n')
        file('output/.keep', 'keep output\n')
        mounts = [bind('input data', '/input', False), bind('output', '/output', True)]
        container(name, mounts=mounts, user='1100:1100', image=IMAGE)
        goals = [f'{name}을 {IMAGE}로 UID/GID 1100:1100에서 실행 상태로 유지하세요.',
                 '현재 폴더의 input data는 /input에 읽기 전용으로, output은 /output에 쓰기 가능하게 연결하세요.',
                 '/input/message.txt를 /output/result.txt로 복사하고 원본과 output/.keep은 보존하세요.']
        if practice == 1:
            initial(name, ['--user', '1100:1100', '-v', start + '/input data:/input:rw', '-v', start + '/output:/output:ro'], ['sleep', '3600'])
            goals.insert(0, '준비된 컨테이너는 입력/출력의 마운트 권한이 뒤바뀌어 있습니다. 올바른 설정으로 교체하세요.')
            solution += [f'docker inspect {name}', f'docker rm -f {name}']
        elif practice == 2:
            file('output/.keep', 'keep output\n', uid=0, gid=0, mode=0o644)
            plan['directory_modes'] = {'output': {'uid': 0, 'gid': 0, 'mode': 0o755}}
            goals.insert(0, 'output 폴더는 현재 root 소유라 UID 1100이 쓸 수 없습니다. 폴더 소유권을 1100:1100으로 고치되 권한은 755로 유지하세요.')
            plan['directory_goals'] = {'output': {'uid': 1100, 'gid': 1100, 'mode': 0o755}}
            solution += ['sudo chown 1100:1100 output']
        solution += [start_container(name, mounts, '--user 1100:1100'), f'docker exec {name} cp /input/message.txt /output/result.txt']
        plan['file_goals'] = {'input data/message.txt': f'release {seed}\n', 'output/result.txt': f'release {seed}\n', 'output/.keep': 'keep output\n'}
    elif key == 'volume':
        mounts = [vol(volume, '/data')]
        text = f'preserved {seed}\n'
        if practice == 0:
            goals = [f'{volume} 이름의 볼륨을 만들고 /data/note.txt에 preserved {seed} 한 줄을 저장하세요.',
                     f'작성용 일회성 컨테이너 {name}-writer는 남기지 말고, {name}은 같은 볼륨을 /data에 연결해 실행 상태로 유지하세요.']
            solution = [f'docker volume create {volume}', f'docker run --name {name}-writer --rm {mount(mounts[0])} {IMAGE} sh -c ' + q(f'printf "preserved {seed}\\n" > /data/note.txt')]
            plan['absent_containers'] = [name + '-writer']
        elif practice == 1:
            plan['initial_volumes'][volume] = {'note.txt': text}
            plan['preserve_volumes'] = [volume]
            initial(name, ['-v', volume + '-empty:/data'], ['sleep', '3600'])
            goals = [f'{name}에서 기존 note.txt가 보이지 않습니다. {volume}에 보관된 자료를 잃지 않고 올바른 볼륨에 다시 연결해 실행 상태로 유지하세요.',
                     f'잘못 연결된 {volume}-empty 볼륨은 제거하세요. 기존 자료의 내용은 수정하지 마세요.']
            plan['absent_volumes'] = [volume + '-empty']
            solution = [f'docker inspect {name}', f'docker volume inspect {volume}', f'docker rm -f {name}', f'docker volume rm {volume}-empty']
        else:
            original = volume + '-original'
            plan['initial_volumes'][original] = {'note.txt': text}
            plan['preserve_volumes'] = [original]
            plan['volume_goals'][original] = {'note.txt': text}
            file('backup files/.keep', 'backup folder\n')
            goals = [f'기존 {original} 볼륨의 note.txt를 현재 폴더의 backup files/note.txt에 백업하세요. 원본 볼륨은 유지하세요.',
                     f'새 {volume} 볼륨으로 백업을 복원하고, {name}을 새 볼륨이 /data에 연결된 실행 상태로 유지하세요.']
            backup = bind('backup files', '/backup', True)
            solution = [f'docker run --rm {mount(vol(original, "/from", False))} {mount(backup)} {IMAGE} cp /from/note.txt /backup/note.txt',
                        f'docker volume create {volume}', f'docker run --rm {mount(vol(volume, "/data"))} {mount(bind("backup files", "/backup", False))} {IMAGE} cp /backup/note.txt /data/note.txt']
            plan['file_goals']['backup files/note.txt'] = text
        solution += [start_container(name, mounts), f'docker exec {name} cat /data/note.txt']
        goals.append(f'{name}의 이미지는 {IMAGE}이며 볼륨은 /data에 읽기·쓰기 연결합니다.')
        container(name, mounts=mounts, image=IMAGE)
        plan['volume_goals'][volume] = {'note.txt': text}
    elif key == 'network':
        plan['networks'] = [network]
        container(name, network=network, image=IMAGE)
        container(peer, network=network, alias='api', image=IMAGE)
        plan['connections'] = [{'from': name, 'to': 'api'}]
        goals = [f'사용자 정의 bridge 네트워크 {network}에서 {name}과 {peer}를 실행하세요.',
                 f'{peer}는 api 별칭으로 찾을 수 있어야 하며, {name}에서 api로 통신할 수 있어야 합니다. 호스트 포트 공개는 필요하지 않습니다.']
        if practice == 0:
            solution = [f'docker network create {network}', start_container(peer, options=f'--network {network} --network-alias api'), start_container(name, options=f'--network {network}')]
        else:
            plan['initial_networks'] = [network]
            initial(peer, ['--network', network, '--network-alias', 'api'], ['sleep', '3600'])
            if practice == 1:
                initial(name, [], ['sleep', '3600'])
                solution = [f'docker network connect {network} {name}', f'docker network disconnect bridge {name}']
                goals.insert(0, f'{name}만 잘못된 기본 bridge에 있습니다. 두 컨테이너를 삭제하지 말고 연결을 고치고 {name}의 기본 bridge 연결은 제거하세요.')
                plan['forbidden_networks'] = {name: ['bridge']}
            else:
                wrong = network + '-old'
                plan['initial_networks'].append(wrong)
                initial(name, ['--network', wrong], ['sleep', '3600'])
                solution = [f'docker network connect {network} {name}', f'docker network disconnect {wrong} {name}', f'docker network rm {wrong}']
                goals.insert(0, f'이전 네트워크 {wrong}에서 새 네트워크로 이관하세요. 두 컨테이너의 ID를 유지하고 이관이 끝난 이전 네트워크는 제거하세요.')
                plan['absent_networks'] = [wrong]
            plan['preserve_containers'] = [name, peer]
        solution += [f'docker exec {name} ping -c 1 -W 2 api']
    elif key == 'build':
        text = f'build {seed}\n'
        file('app/message.txt', text)
        expected = dockerfile()
        goals = [f'app 폴더를 빌드 문맥으로 사용해 {image} 이미지를 만드세요. 기반 이미지는 {IMAGE}입니다.',
                 '기본 작업 폴더 /app, 사용자 1100:1100, /app/message.txt와 built 한 줄을 담은 /build-stamp를 이미지에 포함하세요.',
                 f'추가 명령 없이 실행하면 build {seed} 한 줄을 출력하고 정상 종료해야 합니다. 결과를 build-result.txt에 보관하세요.']
        if practice == 1:
            file('app/Dockerfile', dockerfile('missing.txt').replace('USER 1100:1100', 'USER 0'))
            goals.insert(0, '준비된 Dockerfile은 COPY 경로와 기본 사용자 설정이 잘못되어 있습니다. 문제를 고쳐 재현 가능한 빌드를 만드세요.')
        if practice == 2:
            file('app/Dockerfile', expected)
            plan['initial_images'] = [{'tag': image, 'context': 'app'}]
            plan['preserve_images'] = [image]
            plan['image_goals'].append({'tag': image, 'output': text})
            image = f'training/report{seed}:v2'
            text = f'updated {seed}\n'
            goals = [f'기존 v1 이미지의 내용을 유지하고 app/message.txt를 updated {seed} 한 줄로 수정해 {image}를 새로 빌드하세요.',
                     '새 이미지도 기본 사용자 1100:1100, 작업 폴더 /app, /build-stamp의 built 한 줄을 유지해야 합니다.',
                     '새 이미지의 기본 실행 결과를 build-result.txt에 저장하세요. 기존 v1은 예전 내용을 출력해야 합니다.']
            solution = [write_lines('app/message.txt', text)]
        else:
            solution = [write_lines('app/Dockerfile', expected)]
        solution += [f'docker build --network=none -t {image} app', f'docker run --rm {image} > build-result.txt']
        plan['image_goals'].append({'tag': image, 'output': text, 'user': '1100:1100', 'workdir': '/app', 'stamp': 'built\n'})
        plan['file_goals']['build-result.txt'] = text
    elif key == 'diagnose':
        code = (42, 44, 13)[practice]
        error = f'ERROR incident-{seed} code={code}'
        config = bind('config', '/config', False)
        file('config/.keep', 'preserve configuration directory\n')
        script = '#!/bin/sh\n'
        if practice == 0:
            file('config/settings.txt', 'MODE=draft\n')
            script += f'if ! grep -qx MODE=ready /config/settings.txt; then echo "{error}" >&2; exit 42; fi\n'
            repair = ["printf 'MODE=ready\\n' > config/settings.txt"]
            target = '설정 파일 config/settings.txt의 MODE를 ready로 고치세요.'
            plan['file_goals']['config/settings.txt'] = 'MODE=ready\n'
        elif practice == 1:
            file('message template.txt', f'message {seed}\n')
            script += f'if ! test -f /config/message.txt; then echo "{error}" >&2; exit 44; fi\n'
            repair = ['cp "message template.txt" config/message.txt']
            target = '누락된 config/message.txt를 message template.txt 원본에서 복구하세요. 원본도 유지하세요.'
            plan['file_goals']['config/message.txt'] = f'message {seed}\n'
            plan['file_goals']['message template.txt'] = f'message {seed}\n'
        else:
            file('config/settings.txt', 'MODE=ready\n', uid=0, gid=0, mode=0o600)
            script += f'if ! cat /config/settings.txt >/dev/null; then echo "{error}" >&2; exit 13; fi\n'
            repair = ['sudo chown 1100:1100 config/settings.txt', 'chmod 640 config/settings.txt']
            target = '읽을 수 없는 config/settings.txt의 소유권을 1100:1100, 권한을 640으로 고치세요. 내용은 유지하세요.'
            plan['metadata_goals'] = {'config/settings.txt': {'uid': 1100, 'gid': 1100, 'mode': 0o640}}
            plan['file_goals']['config/settings.txt'] = 'MODE=ready\n'
        script += 'echo service-ready\nexec sleep 3600\n'
        file('service.sh', script)
        plan['file_goals'].update({'service.sh': script, 'config/.keep': 'preserve configuration directory\n'})
        initial(name, ['--user', '1100:1100', '-v', start + '/config:/config:ro', '-v', start + '/service.sh:/service.sh:ro'], ['sh', '/service.sh'], wait_exit=True)
        goals = [f'실패해 종료된 {name}의 로그를 failure.log에, 종료 코드를 exit-code.txt에 보관하세요. 원인 조사 후 {target}',
                 '같은 컨테이너를 다시 실행해 service-ready 로그가 나오고 실행 상태가 유지되게 하세요. 컨테이너 ID, service.sh와 무관한 파일은 보존하세요.']
        solution = [f'docker logs {name} > failure.log 2>&1', f'docker inspect --format ' + q('{{.State.ExitCode}}') + f' {name} > exit-code.txt', *repair, f'docker start {name}']
        plan['preserve_containers'] = [name]
        plan['file_goals']['exit-code.txt'] = str(code) + '\n'
        plan['contains_goals'] = {'failure.log': error}
        plan['log_goals'] = {name: 'service-ready'}
        container(name, mounts=[config], user='1100:1100', image=IMAGE)
    else:
        return make_docker_review(seed)
    plan['file_goals']['keep.txt'] = 'unrelated document\n'
    goals.append(protection_goal(seed))
    return Mission(kind, seed, start, start, start + '/result.txt', start, '', '',
                   '\n\n'.join(goals), '\n'.join(solution), practice=practice, review=plan)


def make_docker_review(seed):
    """One deployment task using storage, build, networking and diagnostics."""
    from missions import Mission
    q = shlex.quote
    start = f'/home/learner/docker/session{seed}'
    name, peer, volume, network = (f'sgd{seed}-{s}' for s in ('worker', 'peer', 'data', 'net'))
    tag = f'training/report{seed}:ready'
    text = f'handoff {seed}\n'
    script = '#!/bin/sh\nif [ "$APP_MODE" != ready ]; then echo "ERROR APP_MODE" >&2; exit 42; fi\ncat /input/message.txt > /data/result.txt || exit 13\necho report-ready\nexec sleep 3600\n'
    dockerfile = f'FROM {IMAGE}\nWORKDIR /app\nCOPY run.sh run.sh\nENV APP_MODE=ready\nUSER 1100:1100\nCMD ["sh", "run.sh"]\n'
    plan = {'docker_real': 'review', 'files': {'keep.txt': 'unrelated document\n', 'input data/message.txt': text,
            'app/run.sh': script, 'app/Dockerfile': dockerfile.replace('APP_MODE=ready', 'APP_MODE=draft')},
            'initial_volumes': {volume: {'history.txt': 'previous release\n'}}, 'preserve_volumes': [volume],
            'initial_networks': [], 'initial_images': [], 'initial_containers': [
                {'name': name, 'args': [], 'command': ['sh', '-c', 'echo "ERROR APP_MODE" >&2; exit 42'], 'wait_exit': True}],
            'file_goals': {'keep.txt': 'unrelated document\n', 'input data/message.txt': text, 'exit-code.txt': '42\n'},
            'contains_goals': {'failure.log': 'ERROR APP_MODE'}, 'log_goals': {name: 'report-ready'},
            'volume_goals': {volume: {'history.txt': 'previous release\n', 'result.txt': text}},
            'networks': [network], 'connections': [{'from': peer, 'to': 'writer'}],
            'image_goals': [{'tag': tag, 'user': '1100:1100', 'workdir': '/app', 'environment': 'APP_MODE=ready'}],
            'containers': [dict(name=name, running=True, image=tag, user='1100:1100', network=network, alias='writer', mounts=[
                dict(type='bind', source=start + '/input data', destination='/input', rw=False),
                dict(type='volume', source=volume, destination='/data', rw=True)]),
                dict(name=peer, running=True, image=IMAGE, network=network, mounts=[dict(type='volume', source=volume, destination='/data', rw=False)])]}
    prompt = (f'실패한 {name}의 로그와 종료 코드를 failure.log와 exit-code.txt에 보관하세요.\n\n'
        f'app/Dockerfile의 APP_MODE를 ready로 고쳐 {tag} 이미지를 빌드하세요. 기본 사용자 1100:1100과 작업 폴더 /app을 유지하세요.\n\n'
        f'사용자 정의 bridge {network}를 만들고 기존 실패 컨테이너를 새 이미지로 교체하세요. 이름은 {name}, 네트워크 별칭은 writer입니다. '
        f'input data는 /input에 읽기 전용으로, 기존 {volume} 볼륨은 /data에 쓰기 가능하게 연결하세요.\n\n'
        f'{peer}는 {IMAGE}로 같은 네트워크에서 실행하고 같은 볼륨을 /data에 읽기 전용 연결하세요. writer 이름으로 통신할 수 있어야 합니다.\n\n'
        '새 작업 컨테이너는 report-ready 로그를 남기고 실행 상태여야 합니다. 볼륨의 result.txt는 입력 문서와 같아야 하며 기존 history.txt와 입력 원본은 유지하세요. '
        + protection_goal(seed))
    solution = f'docker logs {name} > failure.log 2>&1\ndocker inspect --format ' + q('{{.State.ExitCode}}') + f' {name} > exit-code.txt\n'
    solution += write_lines('app/Dockerfile', dockerfile) + f'\ndocker build --network=none -t {tag} app\ndocker rm {name}\ndocker network create {network}\n'
    solution += f'docker run --name {name} -d --network {network} --network-alias writer --mount ' + q(f'type=bind,src={start}/input data,dst=/input,readonly') + f' --mount type=volume,src={volume},dst=/data {tag}\n'
    solution += f'docker run --name {peer} -d --network {network} --mount type=volume,src={volume},dst=/data,readonly {IMAGE} sleep 3600\ndocker exec {peer} ping -c 1 -W 2 writer\ndocker exec {peer} cat /data/result.txt'
    return Mission('docker_review', seed, start, start, start + '/result.txt', start, '', '', prompt, solution, review=plan)
