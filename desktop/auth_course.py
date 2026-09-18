"""Password, user-switching and least-privilege lessons in the real guest."""
import random
import shlex

SPECS = (
    ('auth_status', '계정 레코드와 암호 상태 구분', 'passwd -S',
     'getent passwd는 UID·홈·셸을 조회합니다. 계정 암호를 보여 주는 명령이 아닙니다. '
     'sudo passwd -S 이름은 다른 계정의 암호 상태를 조회합니다. 이름 다음의 P는 사용 가능한 암호 해시, L은 암호 잠금, NP는 암호 없음입니다. '
     '그 뒤는 마지막 암호 변경 날짜와 변경 주기 설정입니다.\n'
     'L은 암호 인증을 잠근 상태이며, 계정 삭제나 모든 접속 방식 차단을 뜻하지는 않습니다. P만으로 sudo 권한이나 실제 로그인이 보장되지도 않습니다.'),
    ('auth_password', '연습 계정 암호 설정·교체', 'passwd · sudo passwd 사용자',
     'sudo passwd 이름은 허용된 관리자 권한으로 그 계정의 암호를 설정합니다. passwd만 입력하면 현재 사용자의 암호를 바꾸려는 것이므로 대상을 먼저 확인하세요.\n'
     'New password:에 새 암호, Retype new password:에 같은 암호를 입력합니다. 입력 중 글자나 *가 보이지 않아도 정상입니다. '
     '두 입력이 다르면 변경되지 않습니다. 명령이 끝난 뒤 passwd -S로 상태를 확인합니다.\n'
     '문제에 제시된 암호는 폐기되는 실습 계정 전용입니다. 개인 계정의 실제 암호를 쓰지 마세요. 암호를 셸 명령행이나 보고서에 적는 방법을 연습하지 않습니다.'),
    ('auth_switch', '사용자만 바꾸고 현재 위치 유지', 'su 사용자 · exit',
     'su 이름은 다른 사용자의 셸을 엽니다. 일반 사용자로 실행하면 대상 계정의 암호를 묻습니다. '
     'sudo의 기본 인증은 보통 요청한 사용자 자신의 암호이므로 둘을 혼동하지 마세요. 정책에 따라 질문 유무가 달라질 수 있습니다.\n'
     '- 없이 전환하면 현재 디렉터리는 유지됩니다. HOME·USER 등은 대상 계정에 맞게 바뀌지만 일반 환경변수는 남을 수 있습니다. '
     '현재 폴더가 그 사용자의 쓰기 가능한 폴더라는 뜻은 아닙니다.\n'
     'whoami·id·pwd로 사용자와 위치를 각각 확인하세요. "$HOME/파일"은 대상 사용자의 홈에 저장합니다. exit는 이 셸을 끝내고 원래 learner 셸로 돌아옵니다.'),
    ('auth_login', '로그인 환경으로 사용자 전환', 'su - 사용자',
     'su - 이름은 로그인 셸로 전환합니다. 대상 홈으로 이동하고 로그인 시작 파일을 읽도록 하며 일반 환경도 재설정합니다. '
     'TERM처럼 유지되는 변수와 PAM·시작 파일이 설정하는 변수가 있으므로 모든 변수가 무조건 사라진다고 단정하지 마세요.\n'
     '이 실습 계정의 .profile에는 AUTH_TEAM이라는 연습 값을 내보내는 설정이 준비되어 있습니다. '
     '사용자 이름이 같아도 - 없이 연 셸은 로그인 환경과 다를 수 있습니다. whoami·pwd·printenv AUTH_TEAM으로 확인합니다.\n'
     'sudo su - 이름은 관리자 권한으로 전환하므로 보통 대상 암호를 묻지 않습니다. 여기서는 대상 암호로 전환하는 su -를 먼저 연습합니다. '
     '자료를 저장한 뒤 exit로 learner에 돌아옵니다.'),
    ('auth_sudo', '인증과 명령 실행 허가 구분', 'sudo -l · sudo 명령',
     'sudo -l은 현재 계정에 허용된 명령과 대상 사용자를 확인합니다. sudo 그룹 하나만이 유일한 허가 방법은 아니며 sudoers 정책이 결정합니다. '
     '암호가 올바르더라도 허가되지 않은 명령은 거절됩니다.\n'
     '이번 계정에는 특정 보호 문서를 root 권한의 cat으로 읽는 권한만 준비되어 있습니다. NOPASSWD는 그 허용 명령의 암호 질문을 생략한다는 뜻이지 모든 명령 허가가 아닙니다.\n'
     'sudo cat 보호문서 > "$HOME/결과.txt"에서 cat은 관리자 권한이지만 >는 현재 셸이 처리합니다. '
     '결과를 자신의 홈에 저장하면 자신의 소유로 남습니다. 문서 권한이나 sudoers를 넓혀서 해결하지 않습니다.'),
)
KEYS = tuple(row[0] for row in SPECS)


def units(Unit):
    return tuple(Unit(key, 6, title, commands, text,
        '지금 사용자·암호 설정 대상·작업 위치·허용 명령을 서로 구분하세요.')
        for key, title, commands, text in SPECS)


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    if kind not in (*KEYS, 'auth_review') or practice not in (0, 1, 2):
        raise ValueError('Unknown authentication exercise')
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    user, peer = f'sgauth{seed}', f'sgpeer{seed}'
    start = f'/home/learner/auth/session{seed}'
    home = start + '/homes/' + user
    uid = 35000 + 2 * seed
    password = f'Lab-{seed}-A!'
    new_password = f'Lab-{seed}-B!'
    team = f'login-team{seed % 7 + 1}'
    protected = f'/opt/shellground/auth-data/session{seed}/admin-note.txt'
    plan = dict(auth_course=1, user=user, peer=peer, uid=uid, home=home, password=password,
                new_password=new_password, team=team, protected=protected,
                set_password=False, initial_locked=False, policy=False, reports={},
                preserve_reports=False, home_copy=False, inherited=False, stale=False)
    status = f'sudo passwd -S {user} > status.txt'
    peer_status = f'sudo passwd -S {peer} > peer-status.txt'
    set_password = [f'sudo passwd {user}',
                    f'# New password: {new_password} 입력 (보이지 않아도 정상)',
                    f'# Retype new password: {new_password} 다시 입력']
    q = shlex.quote
    actions = []
    if kind == 'auth_status':
        plan['initial_locked'] = practice != 1
        plan['peer_locked'] = practice == 1
        prompt = (f'{user}의 암호 상태 조회 결과를 status.txt, {peer}의 결과를 peer-status.txt에 저장하세요. '
                  '계정 정보·암호·잠금 상태는 바꾸지 마세요.')
        plan['reports'] = {'status.txt': ('status', user), 'peer-status.txt': ('status', peer)}
        if practice == 1:
            plan['stale'] = True
            prompt = '두 보고서는 예전 상태를 담고 있습니다. 실제 암호 상태를 조사해 교체하세요.\n' + prompt
        if practice == 2:
            prompt += '\n기존 status.txt는 "status backup.txt"로 먼저 보관하세요.'
            plan['preserve_reports'] = True
            actions.append('cp status.txt "status backup.txt"')
        actions += [status, peer_status]
    elif kind == 'auth_password':
        plan.update(set_password=True, initial_locked=practice != 1)
        prompt = (f'{user}의 암호를 연습용 새 암호 {new_password}로 설정하고 암호 잠금이 없는 상태로 두세요. '
                  f'{peer}의 암호와 계정은 유지하세요. 변경 후 {user}의 암호 상태를 status.txt에 저장하세요.')
        if practice == 1: prompt = '이미 암호가 있는 계정의 암호를 교체하는 작업입니다.\n' + prompt
        if practice == 2:
            prompt = '이 계정은 기존 암호가 설정되어 있지만 암호 인증이 잠겨 있습니다. 잠금만 풀어 예전 암호로 돌아가면 안 됩니다.\n' + prompt
            prompt += f'\n변경 전 {user}의 계정 레코드를 "account backup.txt"에 보관하세요.'
            plan['reports']['account backup.txt'] = ('account', user)
            actions.append(f'getent passwd {user} > "account backup.txt"')
        plan['reports']['status.txt'] = ('status', user)
        actions += set_password + [status]
    else:
        login = kind != 'auth_switch'
        plan['policy'] = kind in ('auth_sudo', 'auth_review')
        plan['set_password'] = kind == 'auth_review'
        plan['initial_locked'] = kind == 'auth_review'
        plan['reports'] = {'who.txt': ('home_text', user + '\n'),
                           'location.txt': ('home_text', (home if login else start) + '\n')}
        prompt = (f'{user} 사용자로 ' + ('로그인 환경에서 ' if login else '현재 시작 위치를 유지하며 ') +
                  '작업하세요. 그 사용자의 홈에 현재 사용자 이름을 who.txt, 현재 디렉터리의 절대경로를 location.txt로 기록하세요.')
        if login:
            prompt += f'\n로그인 설정의 AUTH_TEAM 값 {team}을 확인하고 그 사용자의 홈에 team.txt로 저장하세요.'
            plan['reports']['team.txt'] = ('home_text', team + '\n')
        if kind == 'auth_review':
            prompt = f'{user}의 암호를 연습용 {new_password}로 설정해 암호 잠금을 해제하세요.\n' + prompt
            actions += set_password
        else:
            prompt = f'전환할 계정: {user}, 연습 암호: {password}\n' + prompt
        if kind in ('auth_switch', 'auth_login') and practice == 1:
            plan.update(home_copy=True, stale=login)
            prompt += f'\n시작 위치의 "handoff source.txt"를 {user} 홈의 handoff.txt로 복사하세요. 원본은 유지하고 복사본은 {user} 소유여야 합니다.'
            if login: prompt += '\n기존 홈의 team.txt는 이전 값입니다. 실제 로그인 설정에 맞게 교체하세요.'
        if kind == 'auth_switch' and practice == 2:
            plan['inherited'] = True
            prompt += f'\n전환 전 learner 셸에서 HANDOFF={team}을 내보내세요. 전환한 셸이 전달받은 값을 그 홈의 handoff-env.txt에 저장하세요. 복귀 후 learner의 HANDOFF는 제거하세요.'
            actions.append(f'export HANDOFF={team}')
            plan['reports']['handoff-env.txt'] = ('home_text', team + '\n')
        if kind == 'auth_login' and practice == 2:
            prompt += '\n전환 전에 learner 셸의 AUTH_TEAM을 from-parent로 내보내세요. 전환 뒤에는 부모 값이 아닌 로그인 설정 값이 저장되어야 합니다. 복귀 후 learner의 AUTH_TEAM은 제거하세요.'
            actions.append('export AUTH_TEAM=from-parent')
            plan['inherited'] = True
        actions += [f'su {"- " if login else ""}{user}',
                    '# Password: 위 연습 암호 입력 (입력 문자는 표시되지 않음)',
                    'whoami > "$HOME/who.txt"', 'pwd > "$HOME/location.txt"']
        if login: actions.append('printenv AUTH_TEAM > "$HOME/team.txt"')
        if plan['home_copy']: actions.append(f'cp {q(start + "/handoff source.txt")} "$HOME/handoff.txt"')
        if kind == 'auth_switch' and practice == 2: actions.append('printenv HANDOFF > "$HOME/handoff-env.txt"')
        if plan['policy']:
            prompt += (f'\n{user}에게 허용된 sudo 명령 목록을 그 홈의 allowed.txt에 저장하세요. '
                       f'허용된 권한만 사용해 {protected}의 내용을 그 홈의 notice.txt에 저장하세요. '
                       f'notice.txt는 {user} 소유여야 합니다. 보호 문서와 권한·정책을 바꾸지 마세요.')
            plan['reports'].update({'allowed.txt': ('policy', ''), 'notice.txt': ('protected', '')})
            actions += ['sudo -l > "$HOME/allowed.txt"', f'sudo cat {q(protected)} > "$HOME/notice.txt"']
            if practice == 1:
                plan['stale'] = True
                prompt += '\n기존 notice.txt는 이전 공지입니다. 현재 보호 문서의 내용으로 바로잡으세요.'
            if practice == 2:
                prompt += '\n읽은 공지에서 NOTICE가 들어간 줄만 그 홈의 selected.txt로 골라 저장하세요.'
                plan['reports']['selected.txt'] = ('selected', '')
                actions.append('grep NOTICE "$HOME/notice.txt" > "$HOME/selected.txt"')
        prompt += '\n작업 후 전환한 셸을 종료하고 원래 learner 셸로 돌아오세요. 홈의 보고서는 해당 사용자 소유로 남기세요.'
        actions.append('exit')
        if plan['inherited']: actions.append('unset ' + ('HANDOFF' if kind == 'auth_switch' else 'AUTH_TEAM'))
    prompt += '\npersonal.txt와 "handoff source.txt", 다른 계정·암호·그룹 구성, 대상 계정의 UID·그룹·홈·셸 및 준비된 로그인 설정과 sudo 정책은 보존하세요. 개인 암호를 사용하지 마세요.'
    return Mission(kind, seed, start, start + '/handoff source.txt', start + '/status.txt', home,
                   '', '', prompt, '\n'.join(actions), practice=practice, review=plan)


def steps(unit, mission):
    from learning_steps import LearningStep as S
    plan = mission.review
    user, peer = plan['user'], plan['peer']
    if unit.key == 'auth_status':
        return (S('계정 레코드와 상태 조회 비교', unit.explanation,
                  f'getent passwd {user}\nsudo passwd -S {user}\nsudo passwd -S {peer}',
                  'passwd 레코드의 x는 암호가 아니며 상태 조회의 P/L과 서로 다른 정보입니다.'),
                S('상태를 바꾸지 않고 인계', '조회만으로 암호를 설정하거나 잠금을 풀지 않습니다.', mission.solution,
                  '두 계정 이름과 각 상태를 보고서에서 구분하세요.'))
    if unit.key == 'auth_password':
        return (S('변경 대상 확인', '이름을 생략하면 현재 사용자가 대상입니다. 여기서는 연습 계정 이름을 확인합니다.',
                  f'whoami\ngetent passwd {user}\nsudo passwd -S {user}', 'learner 자신의 암호를 변경하지 않습니다.'),
                S('보이지 않는 암호 입력', unit.explanation, mission.solution,
                  '암호 질문에만 연습 암호를 입력합니다. 셸 프롬프트에 암호를 명령처럼 입력하지 마세요.'))
    report_commands = '\n'.join(mission.solution.splitlines()[2:-1])
    login = unit.key != 'auth_switch'
    prefix = f'su {"- " if login else ""}{user}'
    return (S('사용자 전환과 암호 질문', unit.explanation,
              prefix + f'\n# Password: {plan["password"]} 입력',
              '다른 계정의 프롬프트가 나온 뒤 다음 소단계 명령을 입력합니다.'),
            S('전환한 셸에서 결과 기록', '보고서는 전환한 사용자의 홈에 저장합니다. '+
              ('로그인 설정 값을 직접 조회합니다.' if login else '사용자는 바뀌어도 현재 폴더는 유지됩니다.'),
              report_commands, 'whoami·pwd·홈의 파일 소유자를 구분합니다.'),
            S('원래 셸로 복귀', 'exit는 현재 전환 셸 하나를 종료합니다. learner로 돌아온 뒤 다시 exit를 누르면 터미널 자체를 종료할 수 있습니다.',
              'exit\nwhoami\npwd', 'learner와 문제의 시작 위치가 다시 표시되어야 합니다.'))
