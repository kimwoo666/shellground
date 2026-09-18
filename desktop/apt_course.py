"""Outcome-based APT lessons for the disposable real Linux guest only."""
import random

NOTE = 'shellground-note'
HELPER = 'shellground-helper'
CONF = '/etc/shellground-note.conf'
RETIRED = 'shellground-retired-note'
RETIRED_CONF = '/etc/shellground-retired-note.conf'
PAIR = NOTE + ' ' + HELPER
STATUS = 'dpkg -l ' + PAIR + ' > packages.txt'
INSTALLED = 'apt list --installed ' + PAIR + ' > installed.txt'
UPDATES = 'apt list --upgradable ' + PAIR + ' > updates.txt'
SPECS = (
    ('apt_inspect', '설치 목록과 갱신 후보 구분', 'apt list --installed · --upgradable',
     'update는 저장소의 목록을 갱신할 뿐 설치된 프로그램을 바꾸지 않습니다. --installed는 설치된 버전, --upgradable은 더 새 버전이 있는 패키지를 보여 줍니다.\n'
     'apt list --installed shellground-note shellground-helper처럼 패키지를 지정하면 그 두 개만 조회합니다. 목록의 / 앞은 이름, 뒤쪽은 저장소·버전·아키텍처·상태입니다. '
     '갱신 후보의 버전과 [upgradable from: …] 안의 현재 버전을 구분하세요. 후보가 없으면 제목만 나올 수도 있습니다.\n'
     '이 실습의 note 프로그램은 helper 패키지에 의존합니다. 게스트 내부 오프라인 저장소에 1.0과 2.0이 준비되어 있습니다.'),
    ('apt_upgrade', '목록 갱신과 실제 업그레이드', 'apt update · upgrade · dpkg -l',
     'apt upgrade는 설치된 패키지를 새 후보 버전으로 올립니다. 실행 전 목록과 변경 계획을 읽고 승인합니다. '
     'apt update만 성공한 것은 업그레이드가 아닙니다. 특정 패키지만 올릴 때는 apt install 패키지로 대상을 좁힐 수도 있습니다.\n'
     'dpkg -l 이름은 로컬 설치 상태를 보여 줍니다. ii는 설치 요청·설치 완료, iU는 설치 요청·압축만 풀림, rc는 제거 요청·설정만 남음입니다. '
     '두 글자 다음 열은 패키지 이름, 버전, 아키텍처입니다.\n'
     '이 앱에서는 작은 교육용 패키지만 갱신 가능합니다. 실제 PC에서 upgrade는 더 넓은 변경이므로 동일한 범위라고 가정하지 마세요. '
     '실습 게스트의 서비스 재시작 안내는 조회 전용으로 설정되어 있습니다. 일반 PC에서는 별도 재시작 질문이 나올 수도 있습니다.'),
    ('apt_remove', '프로그램을 제거하고 설정 유지', 'apt remove',
     'apt remove 이름은 프로그램의 설치 파일을 제거하지만 패키지가 관리하는 설정(conffile)은 남길 수 있습니다. '
     '이 교육 패키지의 설정은 /etc/shellground-note.conf입니다. 설치 파일은 /usr/share/shellground-note/version.txt입니다.\n'
     '제거 후 dpkg -l에서 note의 rc(설정만 남음)와 파일 내용을 확인합니다. '
     '의존 패키지 helper를 지우라는 뜻은 아닙니다. 실제로 더는 필요 없는 의존 패키지의 정리는 별도 판단입니다.'),
    ('apt_purge', '남은 패키지 설정까지 정리', 'apt purge',
     'apt purge 이름은 패키지 제거에 더해 그 패키지가 관리하는 설정도 정리합니다. '
     '이미 remove되어 rc인 패키지에도 사용할 수 있습니다. 보관할 설정은 먼저 작업 폴더에 복사하세요.\n'
     '사용자 홈의 개인 문서까지 모두 삭제한다는 뜻은 아닙니다. 이 실습에서는 personal.txt와 helper를 보존합니다. '
     'rm으로 설정 파일만 지우는 것은 패키지 데이터베이스를 purge 상태로 만드는 것과 다릅니다.\n'
     '넓은 * 패턴보다 정확한 패키지 이름을 지정하고 삭제 목록을 확인합니다.'),
    ('apt_repair', '풀렸지만 설치되지 않은 패키지 복구', 'dpkg --audit · apt --fix-broken install',
     'dpkg -i 파일.deb는 로컬 패키지를 설치하려고 하지만 빠진 의존 패키지를 저장소에서 자동으로 받지는 않습니다. '
     '의존성이 맞지 않으면 압축은 풀렸어도 설정 완료가 되지 않을 수 있습니다. dpkg --audit와 dpkg -l을 함께 읽으세요.\n'
     'apt --fix-broken install은 의존성이 맞도록 복구 계획을 계산합니다. 상황에 따라 설치·갱신뿐 아니라 제거를 제안할 수도 있으므로 '
     '무조건 승인하지 말고 필요한 프로그램을 유지하는 계획인지 확인하세요.\n'
     '여기서는 note 2.0이 helper 2.0 이상을 요구하고 저장소에 둘 다 있습니다. 복구 후 두 패키지의 ii·2.0과 빈 audit 결과를 확인합니다. '
     '성공 문구나 빈 보고서만으로 실제 설치 상태가 바뀌지는 않습니다.'),
)
KEYS = tuple(s[0] for s in SPECS)


def units(Unit):
    return tuple(Unit(key, 6, title, commands, text,
        '설치 상태·버전과 설정 보존 조건을 구분해 확인하세요.') for key, title, commands, text in SPECS)


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    if kind not in (*KEYS, 'apt_review') or practice not in (0, 1, 2):
        raise ValueError('Unknown APT exercise')
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    start = f'/home/learner/packages/session{seed}'
    config = f'status=ready\nteam=team{seed % 7 + 1}\n'
    plan = dict(apt_course=1, key=kind, note='1.0', helper='1.0', broken=False,
                removed=False, config=config, expected_note='installed', expected_version='1.0',
                expected_helper='1.0', preserve_config=True, reports={}, backup=False)
    intro = '대상은 교육용 shellground-note와 shellground-helper입니다. '
    actions = []
    if kind == 'apt_inspect':
        if practice == 1:
            plan.update(note='2.0', helper='2.0', expected_version='2.0', expected_helper='2.0')
        elif practice == 2:
            plan.update(helper='2.0', expected_helper='2.0')
        goal = '두 패키지의 설치 목록을 installed.txt, 갱신 가능한 목록을 updates.txt에 저장하세요. 설치 버전과 설정은 바꾸지 마세요.'
        if practice == 1: goal = '두 보고서에는 이전 버전 정보가 남아 있습니다. 현재 상태를 조사해 바로잡으세요.\n' + goal
        if practice == 2:
            goal += '\n기존 installed.txt는 "installed backup.txt"로 먼저 보관하세요.'
            plan['backup_report'] = True
            actions.append('cp installed.txt "installed backup.txt"')
        plan['reports'] = {'installed.txt': 'installed', 'updates.txt': 'upgradable'}
        actions += [INSTALLED, UPDATES]
    elif kind == 'apt_upgrade':
        if practice == 1: plan.update(helper='2.0')
        goal = 'note와 helper를 모두 저장소의 2.0으로 업그레이드하세요. 현재 설정 내용은 유지하세요. '
        goal += '작업 후 두 패키지의 설치 상태·버전을 packages.txt, 남은 갱신 후보를 updates.txt에 저장하세요.'
        if practice == 1: goal = 'helper는 이미 2.0인데 note만 1.0으로 남았습니다.\n' + goal
        plan.update(expected_version='2.0', expected_helper='2.0', reports={'packages.txt': 'status', 'updates.txt': 'upgradable'})
        actions += ['sudo apt update', 'sudo apt upgrade', STATUS, UPDATES]
    elif kind in ('apt_remove', 'apt_purge'):
        purge = kind == 'apt_purge'
        if practice == 1:
            if purge: plan['removed'] = True
            else: plan.update(note='2.0', helper='2.0', expected_version='2.0', expected_helper='2.0', stale_removed_report=True)
        goal = ('note 프로그램과 패키지가 관리하는 /etc/shellground-note.conf 설정을 모두 제거하세요.' if purge else
                'note 프로그램은 제거하되 /etc/shellground-note.conf 설정 내용은 그대로 남기세요.')
        if purge and practice == 1: goal = '프로그램은 앞서 제거했지만 설정만 남아 있습니다.\n' + goal
        if not purge and practice == 1:
            goal = 'packages.txt는 note가 제거되었다고 적혀 있지만 실제 설치 상태와 다릅니다. 보고서만 고치지 말고 실제 상태도 바로잡으세요.\n' + goal
        goal += '\nhelper의 설치와 버전은 유지하고, 작업 후 두 패키지의 상태 목록을 packages.txt에 저장하세요.'
        plan.update(expected_note='absent' if purge else 'config-files', preserve_config=not purge, reports={'packages.txt': 'status'})
        actions += ['sudo apt ' + ('purge' if purge else 'remove') + ' ' + NOTE, STATUS]
    else:
        review = kind == 'apt_review'
        plan.update(note='2.0', helper='1.0' if practice or review else None, broken=True,
                    expected_version='2.0', expected_helper='2.0', reports={'packages.txt': 'status'})
        goal = ('note 2.0은 압축만 풀려 있으며 helper가 없거나 요구 버전보다 오래되어 설정되지 않았습니다. '
                'note를 없애지 말고 두 패키지가 모두 2.0으로 설치 완료되게 복구하세요. 설정 내용은 유지하세요. '
                '복구 후 두 패키지의 상태를 packages.txt에 저장하세요.')
        actions += ['dpkg --audit', 'sudo apt --fix-broken install', STATUS]
        if practice == 1: goal = '기존 packages.txt는 실제 상태와 다른 낡은 보고서입니다.\n' + goal
        if review:
            goal = ('복구할 프로그램과 폐기할 설정 구분\n'
                    'note 2.0의 깨진 의존성을 복구해 note와 helper를 모두 2.0 설치 완료 상태로 남기세요. '
                    '/etc/shellground-note.conf의 내용은 유지하세요.\n'
                    '별도의 shellground-retired-note는 이미 제거되어 설정만 남았습니다. '
                    '/etc/shellground-retired-note.conf를 "retired config backup.txt"로 먼저 보관한 뒤 '
                    '이 폐기 패키지의 잔여 설정을 패키지 관리자에서 완전히 정리하세요.\n'
                    '작업 후 note와 helper의 상태 목록은 packages.txt, 두 패키지의 갱신 후보 목록은 updates.txt에 저장하세요.')
            actions = ['cp ' + RETIRED_CONF + ' "retired config backup.txt"', 'dpkg --audit',
                       'sudo apt --fix-broken install', 'sudo apt purge ' + RETIRED, STATUS, UPDATES]
            plan['retired'] = True
            plan['reports']['updates.txt'] = 'upgradable'
    if practice == 2 and kind != 'apt_inspect':
        goal = '/etc/shellground-note.conf를 "note config backup.txt"로 먼저 보관하세요.\n' + goal
        actions.insert(0, 'cp ' + CONF + ' "note config backup.txt"')
        plan['backup'] = True
    goal += '\npersonal.txt와 다른 패키지는 변경하지 마세요. 모든 파일명은 시작 위치 기준입니다.'
    if 'upgradable' in plan['reports'].values():
        goal += '\n갱신 후보가 없으면 updates.txt는 빈 파일이어도 됩니다.'
    return Mission(kind, seed, start, CONF, start + '/packages.txt', start, '', '',
                   intro + goal, '\n'.join(actions), practice=practice, review=plan)


def steps(unit, mission):
    from learning_steps import LearningStep as S
    key = unit.key
    first = S('설치된 것과 후보 구분',
        '목록 조회는 설치·제거가 아닙니다. note가 요구하는 helper도 같이 읽습니다. 실습은 이미 준비된 오프라인 저장소만 사용합니다.',
        'apt list --installed ' + PAIR + '\napt list --upgradable ' + PAIR,
        '현재 버전과 새 후보가 같지 않을 수 있습니다. helper가 없으면 설치 목록에도 없습니다.')
    if key == 'apt_inspect':
        return (first, S('두 종류의 조회 결과 저장', '>는 화면 출력을 파일로 저장합니다. stderr의 APT 안내 문구는 파일에 들어가지 않을 수 있습니다.',
                        mission.solution, 'installed.txt는 설치 목록, updates.txt는 갱신 후보입니다. 제목만 남는 경우도 정상입니다.'))
    return (first, S('변경 전 상태 해석', unit.explanation,
                    'dpkg -l ' + PAIR + '\ncat ' + CONF + ('\ndpkg --audit' if key == 'apt_repair' else ''),
                    'ii/iU/rc와 버전을 구분하고 설정 내용을 확인합니다.'),
            S('목표에 맞는 변경', '아래 명령은 한 줄씩 실행합니다. APT의 변경 계획을 읽고 목표에 맞을 때 y로 승인합니다. '
              '이미 성공한 제거·설치 명령을 다시 반복할 필요는 없습니다.', mission.solution,
              '필요한 패키지와 보존할 설정이 계획에 맞는지 확인합니다.'),
            S('결과와 보존 조건 확인', '메시지가 아니라 설치 상태와 파일을 함께 확인합니다.',
              'cat packages.txt\nls -l /etc/shellground-note.conf\ncat personal.txt',
              'purge 뒤 설정 경로가 없다는 오류는 목표에 맞습니다. remove 뒤에는 설정이 남아야 합니다.'))
