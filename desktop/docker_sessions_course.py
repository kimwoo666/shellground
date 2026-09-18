"""Real Docker terminal lifetime, image transfer and scoped cleanup lessons."""
import random
import shlex
from docker_lessons import IMAGE

SPECS = (
    ('interactive', '컨테이너 셸과 종료 상태', 'run -it · start -ai · --rm',
     '-i는 표준 입력을 열어 두고 -t는 터미널을 할당합니다. -d는 화면 연결 없이 실행합니다. 세 옵션은 서로 다른 역할입니다. 이 이미지에는 /bin/sh가 있습니다. bash가 모든 이미지에 있는 것은 아닙니다.\n'
     'run은 새 컨테이너를 만들지만 start -ai는 같은 컨테이너를 다시 시작하며 입력/출력에 연결합니다. 셸이 주 프로세스라면 exit로 컨테이너도 종료됩니다. 종료된 것과 삭제된 것은 다릅니다.\n'
     'exit 7은 셸을 종료하고 상태7을 남깁니다. inspect의 State.ExitCode로 확인합니다. 컨테이너 파일은 stop/start 뒤 남지만 rm하면 사라집니다.\n'
     '--rm은 종료 시 일회성 컨테이너를 지웁니다. 필요한 결과를 bind mount로 외부에 남기세요. 여기서 Docker 호스트는 전용 Linux guest이며 개인 PC가 아닙니다.'),
    ('attach', '기존 셸에 연결하고 살아 있게 이탈', 'attach · Ctrl+P, Ctrl+Q · exit',
     'attach는 컨테이너의 주 프로세스 입출력에 연결합니다. 새 셸을 만드는 명령이 아닙니다. 주 프로세스가 셸일 때만 셸 명령을 입력할 수 있습니다.\n'
     '-it로 만든 셸에서 Ctrl+P를 누른 뒤 Ctrl+Q를 누르면 연결만 이탈합니다. 두 키를 동시에 누르지 않습니다. exit는 셸 자체를 끝내므로 결과가 다릅니다. Ctrl+C도 일반적인 이탈 키가 아닙니다.\n'
     '준비된 주 셸의 SESSION_CODE는 export하지 않은 변수입니다. "$SESSION_CODE"를 주 셸 안에서 읽어 기록합니다. 호스트 셸의 변수나 새 exec 셸의 변수와 혼동하지 마세요.\n'
     '다시 attach해도 같은 주 셸의 상태가 이어집니다. 종료된 컨테이너는 먼저 start해야 합니다. 재시작은 파일은 보존하지만 이전 프로세스와 그 메모리를 이어 붙이는 것은 아닙니다.'),
    ('exec', '주 프로세스를 유지하며 별도 작업', 'exec -it · -e · -w · -u',
     'exec는 실행 중인 컨테이너 안에 새 프로세스를 만듭니다. exec -it 이름 sh의 exit는 이 보조 셸만 끝내며 기존 주 프로세스는 유지합니다. 종료된 컨테이너에는 exec할 수 없습니다.\n'
     '-w는 보조 프로세스의 작업 폴더, -e 이름=값은 그 프로세스의 환경입니다. 컨테이너 생성 설정이나 다른 프로세스의 환경을 영구 변경하는 옵션이 아닙니다.\n'
     '-u 1100:1100은 UID/GID를 지정합니다. 대상 폴더에 실제 쓰기 권한이 있어야 합니다. root로 파일을 만들고 이름만 보고 성공했다고 판단하지 않습니다.\n'
     '${SESSION_CODE-unset}은 변수가 설정되지 않았을 때 unset을 표시합니다. 주 셸의 비공개 변수가 새 exec 셸에 전달되지 않는 것을 확인합니다. 파일은 공유되지만 셸 변수는 같은 것이 아닙니다.'),
    ('archive', '압축 이미지 인계와 복원', 'save | gzip · gzip -t · load -i',
     'docker save 이미지:태그는 이미지 설정·레이어·태그를 tar로 내보냅니다. 실행 중인 프로세스 메모리나 볼륨 백업은 아닙니다. | gzip > 파일.tar.gz로 압축할 수 있습니다.\n'
     'gzip -t 파일은 압축 스트림 손상 여부를 검사합니다. 이미지 구조가 맞는지는 별도입니다. 이름만 .gz로 바꾼 tar는 gzip이 아닙니다. gzip 기존.tar는 기본적으로 원래 tar를 없애므로 보존하려면 -c를 씁니다.\n'
     'docker load -i 파일.tar.gz는 압축된 이미지 아카이브를 읽고 태그를 복원합니다. 파일 확장자 대신 실제 형식이 중요합니다. load와 컨테이너 파일시스템을 이미지로 만드는 import는 다릅니다.\n'
     'save에 여러 이미지:태그를 지정할 수 있습니다. 같은 레이어를 공유하므로 표시 SIZE를 모두 더한 값이 실제 중복 없는 저장량은 아닙니다. 복원 후 inspect로 원래 이미지 ID도 확인합니다.'),
    ('prune', '남길 자료를 구별하는 일괄 정리', 'ps --filter · container prune --filter',
     'container prune은 종료된 컨테이너를 삭제합니다. 필터가 없으면 무관한 종료 컨테이너도 대상이므로 먼저 범위를 조사합니다. 실행 중인 컨테이너·이미지·이름 있는 볼륨 정리는 별도입니다.\n'
     '--filter label=키=값으로 지정된 라벨만 고릅니다. ps -a --filter label=키=값으로 후보를 보고, container prune --filter label=키=값으로 종료된 후보만 지웁니다. 라벨은 생성 시 부여된 분류 값입니다.\n'
     '삭제 뒤 컨테이너의 쓰기 레이어는 되돌릴 수 없습니다. 먼저 docker cp 이름:/파일 목적지로 필요한 자료를 꺼냅니다. 중지된 컨테이너에서도 cp는 가능합니다.\n'
     '-f는 확인 질문만 생략하며 삭제 범위를 안전하게 좁혀 주지 않습니다. system prune·image prune·volume prune과 대상을 혼동하지 않습니다. 이 연습은 개인 Docker가 아닌 전용 guest에서 수행합니다.'),
)
KEYS = tuple('docker_sessions_' + row[0] for row in SPECS)


def units(Unit):
    return tuple(Unit('docker_sessions_' + key, 6, title, commands, explanation,
                      '연결된 셸과 실제 컨테이너 상태·남길 자료를 구분하세요.') for key, title, commands, explanation in SPECS)


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    if kind not in (*KEYS, 'docker_sessions_review') or practice not in (0, 1, 2): raise ValueError(kind)
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    start = f'/home/learner/docker/session{seed}'
    name, label, tag = f'sgs{seed}-shell', f'shellground.cleanup={seed}', f'training/handover{seed}:v1'
    key = kind.removeprefix('docker_sessions_'); q = shlex.quote
    plan = dict(docker_sessions=key, name=name, label=label, tag=tag)
    goals = []; actions = []
    def inside(opening, commands, leave='exit'):
        actions.extend([opening, '# 아래 명령은 컨테이너 셸에서 입력', *commands, leave, '# 여기부터 전용 Linux 셸'])
    if key == 'interactive':
        if practice == 0:
            goals = [f'{IMAGE}의 /bin/sh를 입력 가능한 터미널로 새 {name} 컨테이너에 실행하세요. 내부 /note.txt에 hello {seed} 한 줄을 남기고 주 셸을 상태0으로 종료하세요. 컨테이너는 삭제하지 마세요.']
            inside(f'docker run -it --name {name} {IMAGE} /bin/sh', [f'printf "hello {seed}\\n" > /note.txt'])
        elif practice == 1:
            goals = [f'종료되어 있는 {name}을 같은 ID로 다시 시작하세요. 기존 /note.txt 첫 줄을 보존하고 resumed {seed}를 다음 줄에 추가한 뒤 주 셸을 상태7로 종료하세요.']
            inside(f'docker start -ai {name}', [f'printf "resumed {seed}\\n" >> /note.txt'], 'exit 7')
        else:
            goals = [f'{IMAGE}로 새 {name}의 입력 가능한 /bin/sh 터미널을 실행하세요. 현재 폴더 output을 /out에 쓰기 가능한 bind로 연결하고 export {seed} 한 줄을 /out/"daily note.txt"에 저장하세요. 주 셸을 상태0으로 종료하되 연결 설정을 조사할 수 있도록 컨테이너는 남겨 두세요. output/.keep은 보존하세요.']
            inside(f'docker run -it --name {name} --mount ' + q(f'type=bind,src={start}/output,dst=/out') + f' {IMAGE} /bin/sh', [f'printf "export {seed}\\n" > "/out/daily note.txt"'])
    elif key == 'attach':
        if practice == 2:
            goals = [f'종료되어 있는 {name}을 삭제하지 말고 다시 시작하세요. 주 셸의 SESSION_CODE 값을 /session.txt에 한 줄로 보관하고 주 셸을 상태9로 종료하세요. 기존 /note.txt는 유지하세요.']
            actions.append(f'docker start {name}')
        else:
            goals = [f'실행 중인 {name}의 주 셸에 연결해 그 셸의 SESSION_CODE 값을 /session.txt에 한 줄로 기록하세요. 기존 컨테이너와 주 프로세스를 재시작·종료하지 말고, 연결에서 빠져나와 전용 Linux 셸로 돌아오세요.']
            if practice == 1: goals.append('이전 /session.txt 내용은 /previous-session.txt로 먼저 보존하세요. /note.txt도 유지하세요.')
        commands = (['cp /session.txt /previous-session.txt'] if practice == 1 else []) + ['printf "%s\\n" "$SESSION_CODE" > /session.txt']
        inside(f'docker attach {name}', commands, 'exit 9' if practice == 2 else '# 키 입력: Ctrl+P 다음 Ctrl+Q (Enter 없이)')
    elif key == 'exec':
        goals = [f'{name}의 기존 주 프로세스·컨테이너 ID와 /note.txt를 유지하세요. 별도 셸 작업을 마친 뒤 전용 Linux 셸로 돌아오세요.']
        if practice == 0:
            goals.append('별도 /bin/sh에서 /work/child.txt에 child 한 줄, /work/private.txt에 주 셸의 비공개 SESSION_CODE가 전달되지 않았음을 뜻하는 unset 한 줄을 기록하세요.')
            inside(f'docker exec -it {name} /bin/sh', ['printf "child\\n" > /work/child.txt', 'printf "%s\\n" "${SESSION_CODE-unset}" > /work/private.txt'])
        elif practice == 1:
            goals.append('별도 셸은 /work에서 시작하고 그 프로세스에만 TASK_MODE=review를 전달하세요. /work/mode.txt에 실제 TASK_MODE, /work/location.txt에 실제 현재 절대경로를 저장하세요. 컨테이너 생성 환경은 바꾸지 마세요.')
            inside(f'docker exec -it -w /work -e TASK_MODE=review {name} /bin/sh', ['printf "%s\\n" "$TASK_MODE" > mode.txt', 'pwd > location.txt'])
        else:
            goals.append('UID/GID 1100:1100인 별도 셸의 시작 위치는 /work notes입니다. /note.txt를 ./copied note.txt로 복사하고 위치를 ./location.txt에 저장하세요. 두 결과 파일 소유자/그룹도 1100:1100이어야 합니다.')
            inside(f'docker exec -it -u 1100:1100 -w "/work notes" {name} /bin/sh', ['cp /note.txt "copied note.txt"', 'pwd > location.txt'])
    elif key == 'archive':
        if practice == 1:
            goals = [f'준비된 "received image.tar.gz"를 보존하고 그 안의 {tag} 태그를 원래 이미지 ID로 복원하세요. 컨테이너는 만들지 마세요. 복원된 ID를 restored-id.txt에 기록하세요.']
            actions = ['gzip -t "received image.tar.gz"', 'docker load -i "received image.tar.gz"', f"docker image inspect --format '{{{{.Id}}}}' {tag} > restored-id.txt"]
        else:
            tags = tag + (f' training/handover{seed}:v2' if practice == 2 else '')
            goals = [f'{tags} 이미지의 설정·레이어·지정 태그를 gzip 압축 이미지 아카이브 "image backup.tar.gz"로 보관하세요. 원래 이미지/태그는 유지하고 컨테이너는 만들지 마세요.']
            actions = [f'docker save {tags} | gzip > "image backup.tar.gz"', 'gzip -t "image backup.tar.gz"']
            if practice == 2:
                goals.append('이전 image inventory.txt는 previous inventory.txt로 보존한 뒤, 두 태그의 전체 이미지 ID를 v1/v2 순서로 image inventory.txt에 한 줄씩 갱신하세요.')
                actions += ['cp "image inventory.txt" "previous inventory.txt"', "docker image inspect --format '{{.Id}}' " + tags + ' > "image inventory.txt"']
    elif key == 'prune':
        group = label + ('-failed' if practice == 2 else '')
        goals = [f'{group} 라벨이 붙은 종료된 컨테이너만 정리하세요. 같은 라벨이어도 실행 중인 것은 유지하고, 다른 종료 컨테이너도 ID·상태·자료를 보존하세요. sgs{seed}-running과 sgs{seed}-finished의 /keep-me.txt는 보존 대상입니다. 이미지·볼륨·네트워크를 지우는 작업이 아닙니다.']
        actions = [f'docker ps -a --filter label={group}']
        if practice == 1:
            goals.append(f'삭제 전 sgs{seed}-discard0의 /receipt.txt를 현재 폴더 receipt backup.txt로 꺼내 보관하세요.')
            actions += [f'docker cp sgs{seed}-discard0:/receipt.txt "receipt backup.txt"']
        if practice == 2:
            goals.append(f'실패한 sgs{seed}-discard0의 로그 두 출력 스트림과 종료 코드를 failure.log, failure-exit.txt에 먼저 기록하세요. 성공해 종료된 sgs{seed}-finished는 보존 대상입니다.')
            actions += [f'docker logs sgs{seed}-discard0 > failure.log 2>&1', f"docker inspect --format '{{{{.State.ExitCode}}}}' sgs{seed}-discard0 > failure-exit.txt"]
        actions += [f'docker container prune --filter label={group}', '# 확인 질문에서 범위를 읽고 y, Enter']
    else:
        goals = [f'{name}의 주 셸 SESSION_CODE를 /session.txt에 기록한 뒤 주 프로세스를 유지한 채 이탈하세요. 별도 셸로 /work/child.txt에 child 한 줄을 쓰고 종료하세요.',
                 f'{tag}를 "image backup.tar.gz"로 gzip 이미지 보관하고 원래 태그를 유지하세요. {label} 라벨의 종료 컨테이너만 지우되 실행 중이거나 다른 라벨인 것은 보존하세요. sgs{seed}-running과 sgs{seed}-finished의 /keep-me.txt도 보존하세요.']
        inside(f'docker attach {name}', ['printf "%s\\n" "$SESSION_CODE" > /session.txt'], '# 키 입력: Ctrl+P 다음 Ctrl+Q (Enter 없이)')
        inside(f'docker exec -it {name} /bin/sh', ['printf "child\\n" > /work/child.txt'])
        actions += [f'docker save {tag} | gzip > "image backup.tar.gz"', f'docker container prune --filter label={label}', '# 확인 질문에서 범위를 읽고 y, Enter']
    goals.append(f'keep.txt, output/.keep 및 보호용 sgd{seed}-keep 컨테이너·볼륨·네트워크는 유지하세요. 지정된 결과 외의 기존 자료를 바꾸지 마세요.')
    return Mission(kind, seed, start, start, start + '/report.txt', start, '', '', '\n'.join(goals), '\n'.join(actions), practice=practice, review=plan)


def steps(unit, m):
    from learning_steps import LearningStep as S
    parts = unit.explanation.split('\n'); key = m.review['docker_sessions']; name = m.review['name']
    if key == 'interactive':
        return (S('입력 가능한 새 셸', parts[0], m.solution.splitlines()[0], '프롬프트가 컨테이너의 / # 로 바뀝니다. 아직 종료하지 않습니다.'),
                S('컨테이너 안에 기록', parts[1], f'printf "hello {m.seed}\\n" > /note.txt\ncat /note.txt', '이 명령은 전용 Linux 셸이 아니라 컨테이너 셸에서 실행합니다.'),
                S('주 셸 종료와 조사', parts[2], f"exit\ndocker inspect --format '{{{{.State.ExitCode}}}}' {name}", '전용 Linux 셸로 돌아오고 종료0이 기록됩니다.'),
                S('같은 자료로 다시 시작', parts[3], f'docker start -ai {name}\ncat /note.txt\nexit', '같은 파일이 남습니다. --rm이었다면 이 재시작 대상이 남지 않습니다.'))
    if key == 'attach':
        return (S('기존 주 프로세스 조사', parts[0], f'docker ps --filter name={name}', '주 셸이 이미 실행 중입니다.'),
                S('주 셸의 상태 읽기', parts[2], f'docker attach {name}\nprintf "%s\\n" "$SESSION_CODE" > /session.txt', '새 exec 셸이 아니라 기존 주 셸입니다.'),
                S('프로세스를 살려 두고 이탈', parts[1], '# 키 입력: Ctrl+P 다음 Ctrl+Q (Enter 없이)\ndocker ps', '주 셸과 컨테이너가 계속 실행 중인지 확인합니다.'),
                S('다시 연결해 확인', parts[3], f'docker attach {name}\ncat /session.txt\n# 키 입력: Ctrl+P 다음 Ctrl+Q (Enter 없이)', '이미 적은 파일과 기존 셸 상태가 이어집니다.'))
    if key == 'exec':
        return (S('별도 셸 시작', parts[0], f'docker exec -it {name} /bin/sh', '주 셸과 다른 프로세스입니다.'),
                S('공유 파일과 별도 변수', parts[3], 'printf "child\\n" > /work/child.txt\nprintf "%s\\n" "${SESSION_CODE-unset}" > /work/private.txt', '파일은 공유하지만 비공개 셸 변수는 전달되지 않습니다.'),
                S('보조 셸만 종료', parts[1], f'exit\ndocker ps --filter name={name}', 'exit 뒤에도 원래 컨테이너는 실행 중입니다.'),
                S('작업 위치와 사용자 지정', parts[2], f'docker exec -w /work -e TASK_MODE=review {name} sh -c \'pwd; printenv TASK_MODE\'\ndocker exec -u 1100:1100 {name} id', '-w/-e/-u는 새 exec 프로세스의 범위를 지정합니다.'))
    if key == 'archive':
        return (S('보관 대상 조사', parts[0], f'docker image inspect {m.review["tag"]}', '이미지와 컨테이너·볼륨 백업을 구분합니다.'),
                S('tar를 gzip으로 저장', parts[1], m.solution.splitlines()[0], '파일 이름이 아니라 실제 gzip 스트림을 만듭니다.'),
                S('압축 검사와 복원 방법', parts[2], 'gzip -t "image backup.tar.gz"\nls -lh "image backup.tar.gz"', 'gzip 검사 성공만으로 모든 이미지 의미를 검증한 것은 아닙니다.'),
                S('태그와 공유 이미지 확인', parts[3], f"docker image inspect --format '{{{{.Id}}}}' {m.review['tag']}", '원래 태그도 유지합니다. 복원은 다음 활용의 준비 아카이브로 연습합니다.'))
    label = m.review['label']
    return (S('전체 상태와 후보 조사', parts[0], 'docker ps -a', '종료된 것 중에도 보존 대상이 있습니다.'),
            S('라벨로 범위 좁히기', parts[1], f'docker ps -a --filter label={label}', '목록에는 실행 중인 후보도 보일 수 있습니다.'),
            S('삭제 전에 자료 읽기', parts[2], f'docker cp sgs{m.seed}-discard0:/receipt.txt inspection-copy.txt\ncat inspection-copy.txt', '중지된 컨테이너에서도 파일을 꺼낼 수 있습니다.'),
            S('종료된 후보만 정리', parts[3], f'docker container prune --filter label={label}\n# 확인 질문의 범위를 읽고 y, Enter\ndocker ps -a', '실행 중인 것과 다른 라벨의 종료 컨테이너는 남아야 합니다.'))
