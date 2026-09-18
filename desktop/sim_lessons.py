"""Small Linux/Docker state-based lessons, never command-string grading."""
import random
from docker_guides import expanded_explanation


SPECS = (
    ('env', '환경변수와 자식 셸', 'export · unset · printenv', '변수는 값을 붙인 이름입니다. export NAME=value는 자식 셸에도 전달할 환경변수로 등록합니다.\nprintenv NAME으로 확인하고 unset NAME으로 제거합니다. bash -c 뒤의 명령은 별도 셸에서 실행됩니다.'),
    ('author', '셸 스크립트 직접 작성', 'printf · bash · $1', 'printf로 파일 내용을 작성하고 bash 파일 인자로 실행합니다. 스크립트의 $1은 첫 번째 인자입니다.\n작은따옴표는 현재 셸의 변수 확장을 막습니다. "$1"은 공백이 들어간 인자도 하나로 유지합니다.'),
    ('jobs', '백그라운드 작업과 시그널', 'sleep & · jobs · kill', 'sleep 300 &는 백그라운드 작업을 만듭니다. jobs는 현재 셸의 작업을 보여 줍니다.\n%1은 첫 번째 작업 번호이며 PID와 다릅니다. kill -STOP %1은 중지, kill -CONT %1은 재개, kill %1은 종료 요청입니다.'),
    ('apt', '패키지 목록 갱신과 설치', 'sudo apt update · install · list', 'apt update는 패키지 목록을 갱신하고 설치된 프로그램 자체를 업그레이드하지 않습니다.\napt install 이름은 설치, apt upgrade는 설치된 패키지 갱신, apt remove 이름은 제거입니다. 관리자 작업에는 sudo를 붙입니다.\n시뮬레이터는 준비된 가상 저장소만 사용합니다.'),
    ('images', '이미지 받기와 목록', 'docker pull · images', '이미지는 컨테이너 생성에 사용하는 틀입니다. docker pull ubuntu:24.04로 받고 docker images로 목록을 확인합니다.\n태그를 생략하면 latest를 사용합니다. latest가 항상 가장 최신 버전이라는 보장은 없습니다.'),
    ('run', '컨테이너 만들고 실행', 'docker run · ps · ps -a', 'docker run --name box -d ubuntu:24.04 sleep 300은 이미지에서 새 컨테이너를 만들고 백그라운드로 실행합니다.\ndocker ps는 실행 중, docker ps -a는 종료된 컨테이너도 보여 줍니다. --name은 이름, -d는 분리 실행입니다.'),
    ('lifecycle', '중지와 재시작', 'docker stop · start · restart', 'stop은 컨테이너를 종료 상태로 남깁니다. start는 같은 컨테이너를 다시 실행합니다. 파일은 유지됩니다.\nrun은 새 컨테이너 생성이므로 이미 사용하는 이름으로 다시 run하면 충돌합니다.'),
    ('exec', '실행 중인 컨테이너에서 작업', 'docker exec · -it', 'docker exec 이름 명령은 실행 중인 컨테이너에서 새 프로세스를 실행합니다.\ndocker exec -it 이름 bash는 입력 가능한 셸을 엽니다. 셸 안의 파일은 실습 호스트와 분리됩니다. exec 셸에서 exit해도 원래 컨테이너는 계속 실행됩니다.'),
    ('cleanup', '컨테이너와 이미지 삭제', 'docker rm · rmi', 'rm은 컨테이너, rmi는 이미지를 삭제합니다. 실행 중인 컨테이너는 먼저 stop하세요.\n컨테이너가 참조하는 마지막 이미지 태그는 컨테이너를 지운 뒤 제거합니다. 다른 실습 자원까지 지우지 않도록 대상을 확인합니다.'),
    ('update', '이미지 갱신과 컨테이너 교체', 'docker pull · stop · rm · run', '같은 태그를 다시 pull하면 가상 저장소의 갱신 이미지를 받습니다. 이미 실행 중인 컨테이너는 자동으로 새 이미지로 바뀌지 않습니다.\n기존 컨테이너를 정리하고 같은 이름으로 새 컨테이너를 만들어야 새 이미지를 사용합니다.'),
    ('tag', '이미지 이름과 태그', 'docker tag · images', 'docker tag 원본 새이름:태그는 같은 이미지에 이름을 더 붙입니다. 이미지 파일을 통째로 복사하지 않습니다.\n하나의 태그를 지워도 다른 태그가 남아 있으면 이미지는 유지됩니다.'),
    ('commit', '변경 파일을 이미지로 보관', 'docker commit', '컨테이너에 파일을 만든 뒤 docker commit 이름 새이미지:v1로 이미지에 보관합니다.\n그 이미지로 새 컨테이너를 만들어 파일을 확인하세요. 실행 중인 프로그램의 RAM 상태를 저장하는 기능은 아닙니다.'),
    ('save', '이미지 아카이브와 복원', 'docker save · load', 'docker save -o 파일.tar 이미지:태그는 이미지 아카이브를 만듭니다. docker load -i 파일.tar로 복원합니다.\nload < 파일.tar도 가능합니다. 실습 아카이브는 가상 파일이며 실제 Docker와 교환하는 파일이 아닙니다.'),
    ('limits', '환경변수·포트·자원 옵션', 'docker run -e -p --memory --cpus', '-e KEY=value는 컨테이너 환경변수, -p 8080:80은 호스트 포트:컨테이너 포트입니다.\n--memory 128m과 --cpus 1은 자원 제한 설정입니다. inspect로 설정을 확인합니다. 시뮬레이터 수치는 실제 CPU/GPU 벤치마크가 아닙니다.'),
)


def units(Unit):
    return tuple(Unit('sim_' + key, 5 if i < 4 else 6, title, commands, expanded_explanation(key, explanation),
                      '필요하면 F3에서 설명과 예시를 확인하세요.') for i, (key, title, commands, explanation) in enumerate(SPECS))


def make_extension(kind, seed=None, practice=0):
    from missions import Mission
    seed = seed if seed is not None else random.SystemRandom().randrange(1000, 9999)
    start = f'/home/learner/labs/session{seed}'
    report = start + '/result.txt'
    name = f'box{seed}'
    other = f'keep{seed}'
    key = kind.removeprefix('sim_')
    targets = {
        'env': (f'환경변수 TEAM을 team{seed}로 등록하고 자식 셸에서 그 값을 {report}에 저장하세요. OLD_TEAM 변수는 제거하세요.', f'export TEAM=team{seed}\nunset OLD_TEAM\nbash -c \'printenv TEAM\' > result.txt'),
        'author': ('현재 폴더에 write.sh를 작성해 첫 번째 인자 경로에 ready 한 줄을 쓰도록 하세요. 공백이 들어간 result file.txt를 인자로 실행하세요.', "printf 'printf \"ready\\n\" > \"$1\"\\n' > write.sh\nbash write.sh 'result file.txt'"),
        'jobs': ('sleep 300을 백그라운드 작업 두 개로 실행하세요. 첫 번째는 종료하고 두 번째는 중지 상태로 남기세요.', 'sleep 300 &\nsleep 300 &\nkill %1\nkill -STOP %2\njobs'),
        'apt': ('패키지 목록을 갱신하고 tree를 설치하세요. 목록 갱신만으로 설치가 되지 않는 점을 확인하세요.', 'sudo apt update\nsudo apt install tree\napt list --installed'),
        'images': ('ubuntu:24.04와 alpine:latest 이미지를 받으세요. 컨테이너는 만들지 마세요.', 'docker pull ubuntu:24.04\ndocker pull alpine\ndocker images'),
        'run': (f'ubuntu:24.04로 {name} 컨테이너를 만들고 sleep 300을 분리 실행하세요. 컨테이너가 실행 상태여야 합니다.', f'docker run --name {name} -d ubuntu:24.04 sleep 300\ndocker ps'),
        'lifecycle': (f'준비된 {name}을 실행 상태로, {other}는 종료 상태로 만드세요. 둘 다 삭제하거나 새로 만들면 안 됩니다.', f'docker start {name}\ndocker stop {other}\ndocker ps -a'),
        'exec': (f'실행 중인 {name} 안의 /tmp/note.txt에 ready 한 줄을 저장하세요. 실습 호스트에 같은 이름 파일을 만드는 것은 다른 작업입니다.', f'docker exec {name} bash -c \'printf "ready\\n" > /tmp/note.txt\'\ndocker exec {name} cat /tmp/note.txt'),
        'cleanup': (f'{name} 컨테이너와 ubuntu:24.04 이미지를 제거하세요. {other}와 alpine:latest 이미지는 보존하세요.', f'docker stop {name}\ndocker rm {name}\ndocker rmi ubuntu:24.04\ndocker ps -a'),
        'update': (f'가상 저장소에 ubuntu:24.04 갱신 버전이 있습니다. {name}을 최신 이미지로 교체하고 실행 상태로 두세요. pull만으로 기존 컨테이너가 갱신되지는 않습니다.', f'docker pull ubuntu:24.04\ndocker stop {name}\ndocker rm {name}\ndocker run --name {name} -d ubuntu:24.04 sleep 300'),
        'tag': ('ubuntu:24.04와 동일한 이미지를 training:v1으로도 부를 수 있게 하세요. 원래 태그는 유지하세요.', 'docker tag ubuntu:24.04 training:v1\ndocker images'),
        'commit': (f'{name} 안의 /tmp/note.txt에 ready 한 줄을 저장하고 training:v1 이미지로 보관하세요. 이 이미지로 verify{seed} 컨테이너를 분리 실행해 파일이 복원되었는지 확인하세요.', f'docker exec {name} bash -c \'printf "ready\\n" > /tmp/note.txt\'\ndocker commit {name} training:v1\ndocker run --name verify{seed} -d training:v1 sleep 300\ndocker exec verify{seed} cat /tmp/note.txt'),
        'save': ('ubuntu:24.04 이미지를 images.tar에 보관하세요. 이미지를 로컬에서 제거한 뒤 파일로부터 복원하세요. 네트워크에서 다시 pull하지 않아도 복원할 수 있어야 합니다.', 'docker save -o images.tar ubuntu:24.04\ndocker rmi ubuntu:24.04\ndocker load < images.tar\ndocker images'),
        'limits': (f'{name}을 ubuntu:24.04로 만들어 sleep 300을 분리 실행하세요. APP_MODE=training 환경변수, 8080:80 포트, 메모리 128m, CPU 1을 설정하세요.', f'docker run --name {name} -d -e APP_MODE=training -p 8080:80 --memory 128m --cpus 1 ubuntu:24.04 sleep 300\ndocker inspect {name}'),
    }
    if key.startswith('review'):
        if key == 'review30':
            prompt = '환경변수 TEAM=review를 자식 셸에 전달해 result.txt로 저장하세요. 패키지 목록을 갱신하고 tree를 설치하세요. sleep 300 작업을 중지 상태로 하나 남기세요.'
            solution = "export TEAM=review\nbash -c 'printenv TEAM' > result.txt\nsudo apt update\nsudo apt install tree\nsleep 300 &\nkill -STOP %1"
        elif key == 'review35':
            prompt = f'ubuntu:24.04로 {name}을 분리 실행하고 안의 /tmp/note.txt에 ready 한 줄을 저장하세요. 준비된 {other}는 삭제하고 alpine 이미지는 남기세요.'
            solution = f'docker run --name {name} -d ubuntu:24.04 sleep 300\ndocker exec {name} bash -c \'printf "ready\\n" > /tmp/note.txt\'\ndocker stop {other}\ndocker rm {other}'
        else:
            prompt = f'갱신된 ubuntu:24.04를 받아 training:v1 태그를 붙이고 images.tar에 보관하세요. {name}을 그 이미지로 분리 실행하되 APP_MODE=training, 8080:80 포트, 메모리 128m, CPU 1을 설정하세요.'
            solution = f'docker pull ubuntu:24.04\ndocker tag ubuntu:24.04 training:v1\ndocker save -o images.tar training:v1\ndocker run --name {name} -d -e APP_MODE=training -p 8080:80 --memory 128m --cpus 1 training:v1 sleep 300'
    else: prompt, solution = targets[key]
    if practice == 2:
        # A second outcome, not merely different names or locations.
        if key in ('env', 'author', 'apt'):
            prompt += '\n추가 인계: 현재 폴더의 위치를 location.txt에 기록하고 result.txt가 있다면 backup.txt로 보존하세요.'
            solution += '\npwd > location.txt' + ('\ncp result.txt backup.txt' if key == 'env' else '')
        elif key == 'jobs':
            prompt = '이미 중지된 첫 번째 작업을 재개하고, 두 번째 작업만 종료하세요. 새 작업은 만들지 마세요.'
            solution = 'kill -CONT %1\nkill %2\njobs'
        else:
            prompt += '\n추가 조사: 전체 컨테이너 목록을 containers.txt에, 이미지 목록을 images.txt에 저장하세요. 작업 후의 상태여야 합니다.'
            solution += '\ndocker ps -a > containers.txt\ndocker images > images.txt'
    return Mission(kind, seed, start, start + '/source', report, start + '/target', '', '', prompt, solution, practice=practice,
                   review={'title': '상태를 조사하고 목표 달성', 'extension': key})


def prepare_extension(shell, m):
    key = m.kind.removeprefix('sim_'); d = shell.docker
    name, other = f'box{m.seed}', f'keep{m.seed}'
    shell.env['OLD_TEAM'] = 'obsolete'
    def run(command):
        result = shell.execute(command, False)
        if result.code: raise ValueError(result.err.decode())
    if key not in ('env', 'author', 'jobs', 'apt', 'images', 'run', 'limits', 'review30', 'review35'):
        run('docker pull ubuntu:24.04')
    if key in ('exec', 'lifecycle', 'cleanup', 'update', 'commit'):
        run(f'docker run --name {name} -d ubuntu:24.04 sleep 300')
    if key == 'lifecycle': run(f'docker stop {name}')
    if key in ('lifecycle', 'cleanup', 'review35'): run(f'docker run --name {other} -d alpine sleep 300')
    if key in ('update', 'review40'): d.remote['ubuntu:24.04'] = '24.04-v2'
    if key == 'jobs' and m.practice == 2: run('sleep 300 &\nsleep 300 &\nkill -STOP %1')
    shell.initial_ids = {k: v['id'] for k, v in d.containers.items()}
    shell.initial_images = {k: v['id'] for k, v in d.images.items()}


def grade_extension(s, m):
    key = m.kind.removeprefix('sim_'); d = s.docker; name = f'box{m.seed}'; other = f'keep{m.seed}'
    checks = []
    def check(label, value): checks.append({'label': label, 'passed': bool(value)})
    def content(path):
        try: return s.fs.read(s.path(path))
        except OSError: return None
    def ready(container):
        try: return d.containers[container]['shell'].fs.read('/tmp/note.txt') == b'ready\n'
        except (OSError, KeyError): return False
    def running(container): return d.containers.get(container, {}).get('state') == 'running'
    if key in ('env', 'review30'):
        expected = 'review' if key == 'review30' else f'team{m.seed}'
        check('환경변수 TEAM 등록', s.env.get('TEAM') == expected and 'TEAM' in s.exported)
        check('변수 값을 파일로 전달', content('result.txt') == (expected + '\n').encode())
        if key == 'env': check('OLD_TEAM 제거', 'OLD_TEAM' not in s.env)
    if key == 'author':
        check('스크립트 작성', content('write.sh') is not None)
        check('공백 경로 결과 파일', content('result file.txt') == b'ready\n')
    if key in ('apt', 'review30'):
        check('패키지 목록 갱신', s.updated); check('tree 설치', 'tree' in s.packages)
    if key in ('jobs', 'review30'):
        states = {i: j['state'] for i, j in s.jobs.items()}
        target = {1: 'Stopped'} if key == 'review30' else {1: 'Running', 2: 'Terminated'} if m.practice == 2 else {1: 'Terminated', 2: 'Stopped'}
        check('지정 작업의 상태와 나머지 작업 보존', states == target)
    if key == 'images':
        check('Ubuntu 이미지', 'ubuntu:24.04' in d.images); check('Alpine 이미지', 'alpine:latest' in d.images); check('컨테이너를 만들지 않음', not d.containers)
    if key in ('run', 'exec', 'lifecycle', 'update', 'limits', 'review35', 'review40'): check('목표 컨테이너 실행', running(name))
    if key == 'lifecycle':
        check('보존 컨테이너 종료', d.containers.get(other, {}).get('state') == 'exited')
        check('새로 만들지 않고 기존 컨테이너 유지', {k: v['id'] for k, v in d.containers.items()} == s.initial_ids)
    if key in ('exec', 'commit', 'review35'): check('컨테이너 안의 파일 내용', ready(name))
    if key == 'cleanup':
        check('지정 컨테이너 삭제', name not in d.containers); check('지정 이미지 삭제', 'ubuntu:24.04' not in d.images)
    if key in ('cleanup', 'review35'):
        check('Alpine 이미지 보존', 'alpine:latest' in d.images)
        check('다른 컨테이너 보존' if key == 'cleanup' else '기존 컨테이너 정리', running(other) if key == 'cleanup' else other not in d.containers)
    if key in ('update', 'review40'):
        image = d.images.get('ubuntu:24.04', {})
        check('가상 저장소의 갱신 버전 받음', image.get('revision') == '24.04-v2')
        check('컨테이너가 갱신 이미지를 사용', bool(image) and d.containers.get(name, {}).get('image') == image.get('id'))
    if key in ('tag', 'review40'):
        check('동일 이미지에 두 태그', 'training:v1' in d.images and 'ubuntu:24.04' in d.images and d.images['training:v1']['id'] == d.images['ubuntu:24.04']['id'])
    if key == 'commit':
        check('변경 이미지 생성', 'training:v1' in d.images)
        check('새 컨테이너에 파일 복원', ready(f'verify{m.seed}') and running(f'verify{m.seed}'))
    if key in ('save', 'review40'):
        check('이미지 아카이브 생성', bool(content('images.tar')))
        check('이미지 사용 가능', 'ubuntu:24.04' in d.images)
        if key == 'save': check('원래 이미지 ID 보존', d.images.get('ubuntu:24.04', {}).get('id') == s.initial_images.get('ubuntu:24.04'))
        if key == 'save': check('아카이브에서 이미지 복원 완료', s.initial_images.get('ubuntu:24.04') in d.loaded_images)
    if key in ('limits', 'review40'):
        c = d.containers.get(name, {}); opts = c.get('options', {})
        check('환경변수', bool(c) and c['shell'].env.get('APP_MODE') == 'training')
        check('포트 매핑', opts.get('publish') == ['8080:80'])
        check('메모리와 CPU 설정', opts.get('memory') == '128m' and opts.get('cpus') == '1')
    if m.practice == 2:
        if key in ('env', 'author', 'apt'):
            check('현재 위치 인계', content('location.txt') == (m.start + '\n').encode())
            if key == 'env': check('결과 백업', content('backup.txt') == content('result.txt') and content('backup.txt') is not None)
        elif key != 'jobs':
            check('컨테이너 현황 보고서', content('containers.txt') == d.command(['ps', '-a']).out)
            check('이미지 현황 보고서', content('images.txt') == d.command(['images']).out)
    return {'passed': bool(checks) and all(c['passed'] for c in checks), 'checks': checks}
