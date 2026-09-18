"""Process inspection and job control in the real Linux guest."""
import random

SPECS = (
    ('process_list', '프로세스 목록과 대상 선택', 'ps -U · ps -p',
     'ps -U learner는 실제 UID(RUID)가 learner인 프로세스를 조회합니다. PID는 프로세스 번호, TTY는 연결된 터미널, '
     'TIME은 누적 CPU 사용 시간, CMD는 프로그램 이름입니다. TIME은 실행한 뒤 흐른 시간이 아닙니다. '
     '터미널이 없는 서비스는 TTY가 ?로 나올 수 있습니다.\n'
     'ps -p 번호는 특정 PID를 조회합니다. PID는 실행할 때 달라지므로 문제의 .pid 파일을 읽으세요. '
     '$(cat main.pid)는 cat의 출력을 명령 인자에 넣는 명령 치환입니다. 숫자를 직접 확인하고 입력해도 됩니다. '
     'kill 전에 이름과 대상을 확인하는 습관을 익힙니다.'),
    ('process_threads', '부모 프로세스와 스레드 조사', 'ps -Lf · pstree -p -u',
     'ps -Lf -p 번호는 대상 프로세스의 스레드별 행을 보여 줍니다. PID는 프로세스, PPID는 부모 프로세스, '
     'LWP는 스레드 ID, NLWP는 스레드 수입니다. 같은 PID의 여러 LWP를 서로 다른 프로세스라고 세면 안 됩니다. '
     '스레드는 주소 공간을 공유하지만 각자의 스택·레지스터 문맥을 갖습니다. 스레드가 많다고 항상 빨라지는 것은 아닙니다.\n'
     'pstree -p -u 번호는 그 프로세스 아래의 부모·자식 구조를 보여 줍니다. -p는 PID, -u는 부모와 달라진 UID 표시입니다. '
     '여기서는 root 감독 아래 learner 작업이 있어 사용자 전환이 보입니다.\n'
     'ps -L -p 번호 -o lwp=는 스레드 ID 열만 제목 없이 출력합니다. 이미 배운 wc -l과 연결해 행 개수를 셀 수 있습니다.'),
    ('process_stop', '전경 작업을 멈추고 셸로 돌아오기', 'jobs -l · fg · Ctrl+Z',
     'jobs -l은 현재 셸의 작업 번호와 PID를 보여 줍니다. %1은 작업 번호이고 숫자 PID와 다릅니다. '
     '파이프로 연결된 여러 프로세스가 한 작업일 수도 있습니다.\n'
     'fg %번호는 그 작업을 전경으로 가져옵니다. 실행 중에는 셸 프롬프트가 나오지 않습니다. '
     'Ctrl+Z는 전경 작업에 SIGTSTP를 보내 중지하고 셸로 돌아옵니다. 종료가 아닙니다. '
     'jobs의 Stopped, ps의 T는 중지입니다. S는 CPU를 기다리는 정상 대기 상태라 T와 다릅니다.\n'
     '%?job-main처럼 명령행의 고유한 일부로 작업을 선택할 수도 있습니다. 둘 이상 일치하면 모호하다는 오류가 납니다. '
     'PID를 새로 만든 다른 프로세스로 바꾸지 말고 같은 작업을 유지합니다.'),
    ('process_resume', '중지한 작업을 백그라운드에서 재개', 'bg · & · wait',
     'bg %번호는 중지한 작업을 백그라운드에서 계속 실행합니다. 새 프로세스를 만드는 것이 아닙니다. '
     'fg는 전경에서 계속하므로 그 작업이 끝나거나 중지되기 전까지 셸 입력을 기다리게 합니다.\n'
     '명령 끝의 &는 새 백그라운드 작업을 시작합니다. $!는 가장 최근 백그라운드 작업의 PID이고 '
     'wait "$!"는 그 작업이 끝날 때까지 기다립니다. 보고서를 만드는 작업은 완료되기 전에 파일을 읽지 마세요. '
     '실습 폴더만 조회하며 / 전체를 재귀 조회해 노트북에 부하를 주지 않습니다.'),
    ('process_signals', '정상 종료 요청과 강제 종료 구분', 'kill -TERM · kill -KILL',
     'kill은 이름과 달리 시그널을 보내는 명령이며 기본값은 SIGTERM입니다. 프로그램이 처리·지연·무시할 수 있습니다. '
     'SIGKILL은 처리하거나 무시할 수 없어 정리 동작을 실행하지 못합니다. 무조건 -9부터 쓰지 마세요.\n'
     '이번 main 서비스는 TERM을 받으면 정리 후 정상 상태 0으로 끝나며 blocker는 TERM을 무시하도록 준비됐습니다. '
     '감독이 실제 종료 상태를 기록하므로 정리 보고서만 위조해서 통과할 수 없습니다. '
     '중지된 프로세스의 TERM 처리는 재개 후 진행될 수 있습니다. 이미 배운 CONT와 함께 상태를 판단하세요.\n'
     '잘못 종료해 복구가 필요하면 준비된 ./restart-services.sh로 서비스 세 개만 새로 시작할 수 있습니다. '
     '같은 터미널·파일을 유지하며 PID 파일이 갱신됩니다. 이 스크립트는 실습용 도구이지 일반 Linux 명령이 아닙니다.'),
)
KEYS = tuple(s[0] for s in SPECS)


def units(Unit):
    return tuple(Unit(k, 6, title, commands, explanation,
                      'PID·작업 번호·스레드 ID를 구분하고 무관한 서비스는 보존하세요.') for k, title, commands, explanation in SPECS)


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    if kind not in (*KEYS, 'process_review') or practice not in (0, 1, 2): raise ValueError('Unknown process exercise')
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    start = f'/home/learner/process/session{seed}'
    plan = dict(process_course=1, jobs=kind in ('process_stop', 'process_resume'),
                initial_stopped=[], reports={}, inventory=False, backup=False)
    names = f'sgm{seed}, sgs{seed}, sgb{seed}'
    actions = []
    if kind == 'process_list':
        prompt = f'준비된 learner 서비스 {names}가 포함된 프로세스 목록을 processes.txt에 저장하세요. PID·TTY·누적 CPU 시간·프로그램 이름 열을 포함하세요. 서비스는 모두 실행 가능한 상태로 유지하세요.'
        actions = ['ps -U learner > processes.txt']
        plan['reports']['processes.txt'] = 'processes'
        if practice == 1:
            prompt += '\n기존 processes.txt는 이전 작업의 목록입니다. "previous processes.txt"로 보관한 뒤 갱신하세요.'
            plan['backup'] = True
            actions.insert(0, 'cp processes.txt "previous processes.txt"')
        if practice == 2:
            prompt += '\nmain.pid의 PID에 해당하는 프로세스만 같은 열 형식으로 subject.txt에 별도 저장하세요.'
            plan['reports']['subject.txt'] = 'subject'
            actions.append('ps -p "$(cat main.pid)" > subject.txt')
    elif kind == 'process_threads':
        prompt = ('main.pid 대상의 전체 스레드 목록을 threads.txt에 저장하세요. UID·PID·PPID·LWP·NLWP 열을 포함하세요. '
                  'supervisor.pid 아래 프로세스 트리를 PID와 사용자 전환 표시를 포함해 tree.txt에 저장하세요. 서비스는 모두 실행 가능한 상태로 유지하세요.')
        plan['reports'] = {'threads.txt': 'threads', 'tree.txt': 'tree'}
        actions = ['ps -Lf -p "$(cat main.pid)" > threads.txt', 'pstree -p -u "$(cat supervisor.pid)" > tree.txt']
        if practice == 1:
            prompt += '\nspare.pid 대상도 같은 스레드 열 형식으로 spare-threads.txt에 저장해 두 서비스의 스레드 구성을 비교하세요.'
            plan['reports']['spare-threads.txt'] = 'spare_threads'
            actions.append('ps -Lf -p "$(cat spare.pid)" > spare-threads.txt')
        if practice == 2:
            prompt += '\nmain 대상의 스레드 개수만 thread-count.txt에 숫자로 기록하세요. PID를 중복 제거한 개수가 아닙니다.'
            plan['reports']['thread-count.txt'] = 'count'
            actions.append('ps -L -p "$(cat main.pid)" -o lwp= | wc -l > thread-count.txt')
    elif plan['jobs']:
        stop = kind == 'process_stop'
        if not stop: plan['initial_stopped'] = ['main']
        if practice == 1: plan['initial_stopped'].append('spare')
        prompt = ('현재 셸에 준비된 job-main 작업을 ' + ('중지 상태로 남기세요. 종료하지 마세요.' if stop else '백그라운드에서 다시 실행되게 하세요.') +
                  ' job-spare와 job-blocker는 실행 가능한 상태로 유지하세요. 처음 작업들의 PID를 유지하고 learner 셸로 돌아와 있어야 합니다.')
        if practice == 1: prompt += '\njob-spare도 잘못 중지되어 있습니다. 이 작업도 재개하세요.'
        actions = ['jobs -l']
        if stop:
            actions += ['fg %?job-main', '# Ctrl+Z: 전경 작업 중지']
            if practice == 1: actions += ['kill -CONT %?job-spare']
        else:
            actions += ['bg %?job-main']
            if practice == 1: actions += ['bg %?job-spare']
        if practice == 2:
            prompt += '\n준비된 inventory의 숨김 항목 포함 전체 하위 목록을 상세 형식으로 inventory.txt에 저장하세요. 원본은 보존하세요.'
            plan['inventory'] = True
            actions += ['ls -alR inventory > inventory.txt' + ('' if stop else ' &')]
            if not stop: actions += ['wait "$!"']
        actions += ['jobs -l']
    else:
        plan['initial_stopped'] = ['main'] if practice == 1 else ['spare'] if practice == 2 else []
        prompt = ('main.pid 서비스는 정리 동작을 마치고 정상 종료 상태 0이 되게 종료하세요. '
                  'TERM을 무시하는 blocker.pid 서비스는 강제 종료하세요. spare.pid는 PID를 바꾸지 말고 ' +
                  ('중지 상태를 유지하세요.' if practice == 2 else '실행 가능한 상태로 유지하세요.'))
        if practice == 1: prompt += '\nmain은 현재 중지 상태입니다. 종료 요청을 처리할 수 있는 상태로 만들어야 합니다.'
        if kind == 'process_review':
            prompt = ('종료 작업 전에 main의 스레드 목록을 threads.txt, 감독 아래 프로세스 트리를 PID·사용자 전환 포함 tree.txt에 저장하세요.\n' + prompt)
            plan['reports'] = {'threads.txt': 'threads', 'tree.txt': 'tree'}
            actions += ['ps -Lf -p "$(cat main.pid)" > threads.txt', 'pstree -p -u "$(cat supervisor.pid)" > tree.txt']
        if practice == 1: actions += ['kill -CONT "$(cat main.pid)"']
        actions += ['kill -TERM "$(cat main.pid)"', 'kill -KILL "$(cat blocker.pid)"']
        prompt += '\n복구가 필요하면 ./restart-services.sh로 연습 서비스만 다시 시작할 수 있습니다. 기존 파일·터미널은 유지되고 PID 파일은 갱신됩니다.'
    prompt += '\n이름과 PID는 별개입니다. personal.txt와 inventory의 자료, 준비된 실행 스크립트와 PID 파일은 보존하세요. 서비스 재시작 도구에 의한 PID 갱신은 허용합니다.'
    return Mission(kind, seed, start, start + '/inventory', start + '/processes.txt', start,
                   '', '', prompt, '\n'.join(actions), practice=practice, review=plan)


def steps(unit, m):
    from learning_steps import LearningStep as S
    key = unit.key
    if key == 'process_list':
        return (S('사용자 기준 목록 읽기', unit.explanation, 'ps -U learner', 'PID·TTY·TIME·CMD를 서로 구분합니다.'),
                S('한 프로세스 선택', 'cat으로 확인한 PID를 직접 입력해도 됩니다. 명령 치환은 숫자를 복사하는 편의 문법입니다.',
                  'cat main.pid\nps -p "$(cat main.pid)"', '새로 시작할 때 PID가 달라지는 이유를 생각합니다.'),
                S('현재 목록 보관', '조회만 하고 서비스를 중지하거나 종료하지 않습니다.', m.solution, '세 서비스 이름과 PID가 모두 포함되어야 합니다.'))
    if key == 'process_threads':
        return (S('스레드별 행 읽기', unit.explanation, 'cat main.pid\nps -Lf -p "$(cat main.pid)"',
                  '같은 PID의 서로 다른 LWP와 NLWP를 비교합니다.'),
                S('부모·자식 트리', '감독은 root, 작업은 learner입니다. -u는 이 UID 전환을 표시합니다.',
                  'pstree -p -u "$(cat supervisor.pid)"', '감독 PID와 자식 PID를 구분합니다.'),
                S('두 관점 저장', '스레드 목록과 프로세스 트리는 서로 대체되지 않습니다.', m.solution, '원본 서비스가 실행 중이어야 합니다.'))
    if key in ('process_stop', 'process_resume'):
        return (S('작업 번호와 현재 상태', unit.explanation, 'jobs -l', '작업 명령행의 job-main·job-spare·job-blocker를 찾습니다.'),
                S('중지 또는 재개 조작', 'fg 뒤 프롬프트가 없을 때 Ctrl+Z를 누릅니다. bg는 즉시 셸로 돌아옵니다.',
                  m.solution, 'Running/S는 정상 대기일 수 있고 Stopped/T는 중지입니다.'))
    return (S('종료 대상 조사', unit.explanation, 'ps -U learner\ncat main.pid\ncat blocker.pid', 'spare는 보존할 대상입니다.'),
            S('정상 요청과 강제 종료', '같은 kill 명령이라도 전달한 시그널에 따라 정리 기회가 다릅니다.', m.solution,
              '감독이 실제 종료 상태를 확인합니다. 잘못 종료했다면 실습용 재시작 스크립트로 새 서비스를 준비할 수 있습니다.'))
