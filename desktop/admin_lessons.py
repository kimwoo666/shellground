"""Small identity/permission/account lessons and backend-neutral state goals."""
import random
import shlex

SPECS = (
    ('identity', '사용자·그룹 조사', 'whoami · id -u/-g/-G/-n · groups · getent',
     'whoami는 현재 사용자 이름입니다. id -u는 UID, id -g는 기본 GID, id -G는 모든 그룹 ID입니다. -n을 함께 쓰면 번호 대신 이름을 표시합니다.\nid 사용자이름은 다른 계정을 조사합니다. 그룹 순서는 달라도 같은 그룹 집합일 수 있습니다.\ngetent passwd 사용자이름의 열은 이름:암호표시:UID:GID:설명:홈:셸입니다. 실제 암호를 출력하는 명령이 아닙니다.'),
    ('modes', '파일과 폴더의 읽기·쓰기·탐색 권한', 'chmod 640/750 · u=rw,g=r,o=',
     '권한은 소유자(u), 그룹(g), 나머지(o)에 각각 적용됩니다. r=4, w=2, x=1입니다. 640은 rw-r-----, 750은 rwxr-x---입니다.\n파일의 x는 실행, 폴더의 x는 그 안의 경로를 찾아 들어가는 권한입니다. 폴더의 r은 이름 목록 읽기, w+x는 항목 생성·삭제에 필요합니다.\nchmod u=rw,g=r,o= 파일은 640과 같은 일반 권한을 설정합니다. +는 추가, -는 제거, =는 지정한 권한으로 교체합니다. 무조건 777로 풀지 마세요.'),
    ('owners', '소유자와 소유 그룹 바로잡기', 'sudo · chown 사용자:그룹 · chgrp',
     'chmod는 권한, chown은 소유자/그룹, chgrp는 그룹을 바꿉니다. 서로 대체할 수 없습니다.\nsudo chown 사용자:그룹 파일은 두 소유 정보를 함께 바꿉니다. sudo chgrp 그룹 파일은 소유자는 보존하고 그룹만 바꿉니다.\nsudo는 허용된 관리자 작업을 요청합니다. 여기서는 앱 전용 실습 환경에만 적용됩니다. 실제 시스템의 관리자 정책과 암호 요청은 다를 수 있습니다.\nls -l로 소유자·그룹·권한을 함께 확인하세요.'),
    ('users', '홈과 셸을 지정해 사용자 만들기', 'useradd -u -g -G -s -d -m',
     'sudo useradd -u UID -g 기본그룹 -G 보조그룹 -s /bin/bash -d 홈경로 -m 이름\n-u는 사용자 번호, -g는 기본 그룹 하나, -G는 쉼표로 나눈 보조 그룹, -s는 로그인 셸입니다. -d는 홈 경로를 기록하고 -m은 실제 홈 폴더도 만듭니다.\n그룹은 먼저 존재해야 합니다. UID 중복과 이미 있는 사용자 이름은 오류입니다. id와 getent passwd로 계정 정보를, ls -ld로 홈의 소유자를 확인하세요. 암호 설정과 로그인 전환은 별도 학습 범위입니다.'),
    ('groups', '그룹 추가와 기존 권한 보존', 'groupadd -g · usermod -a -G · usermod -g',
     'sudo groupadd -g GID 그룹이름은 새 그룹을 만듭니다.\nsudo usermod -a -G 새그룹 사용자: 기존 보조 그룹을 유지하면서 추가합니다. -a 없이 -G만 쓰면 보조 그룹 목록을 교체하므로 기존 권한을 잃을 수 있습니다.\nusermod -g 그룹 사용자는 기본 그룹을 바꿉니다. -g와 -G는 다른 옵션입니다. id 사용자이름으로 계정의 변경 결과를 확인하세요. 이미 실행 중인 로그인 셸의 그룹은 재로그인 전까지 그대로일 수 있습니다.'),
)


def units(Unit):
    return tuple(Unit('admin_' + key, 5, title, commands, text,
        'F3에서 옵션과 예시를 확인하고, id와 ls -l로 현재 상태를 조사하세요.') for key, title, commands, text in SPECS)


def make_admin_mission(kind, seed=None, practice=0):
    from missions import Mission
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    key = kind.removeprefix('admin_')
    start = f'/home/learner/admin/session{seed}'
    user, dev, audit, ops = (prefix + str(seed) for prefix in ('sguser', 'sgdev', 'sgaudit', 'sgops'))
    uid, gid = 20000 + seed, 10000 + seed * 3
    home = start + '/homes/' + user
    q = shlex.quote
    plan = {'admin': key, 'start': start, 'users': {}, 'groups': {dev: gid, audit: gid + 1},
            'files': {}, 'expected_files': {}, 'expected_users': {}, 'expected_groups': {}, 'reports': {}}
    account = {'uid': uid, 'gid': gid, 'home': home, 'shell': '/bin/bash', 'groups': [dev, audit]}
    def file(path, text='', mode=0o644, owner=1100, group=1100, kind='file'):
        return {'type': kind, 'text': text, 'mode': mode, 'uid': owner, 'gid': group}
    def initial(path, value, preserve=False):
        plan['files'][path] = value
        if preserve: plan['expected_files'][path] = value.copy()
    initial('keep.txt', file('keep.txt', 'unrelated file\n'), True)
    initial('source note.txt', file('', 'team=training\n', 0o644), True)
    if key not in ('users', 'review'):
        plan['users'][user] = dict(account)
        plan['expected_users'][user] = dict(account)
    if key == 'identity':
        if practice == 0:
            prompt = f'현재 사용자 이름을 name.txt, 현재 UID를 uid.txt에 기록하세요. {user}의 모든 그룹 이름은 groups.txt에 저장하세요.'
            solution = f'whoami > name.txt\nid -u > uid.txt\nid -Gn {user} > groups.txt'
            plan['reports'] = {'name.txt': 'learner\n', 'uid.txt': '1100\n', 'groups.txt': {'tokens': [dev, audit]}}
        elif practice == 1:
            prompt = f'현재 사용자가 아닌 {user}의 UID, 기본 GID, 모든 그룹 이름을 uid.txt, gid.txt, groups.txt에 각각 기록하세요.'
            solution = f'id -u {user} > uid.txt\nid -g {user} > gid.txt\nid -Gn {user} > groups.txt'
            plan['reports'] = {'uid.txt': f'{uid}\n', 'gid.txt': f'{gid}\n', 'groups.txt': {'tokens': [dev, audit]}}
        else:
            prompt = f'{user}의 계정 레코드를 account.txt에 저장하고 그 복사본을 account backup.txt로 남기세요. 해당 사용자의 기본 그룹 이름을 primary.txt에 기록하세요. 원래 자료는 보존하세요.'
            solution = f'getent passwd {user} > account.txt\ncp account.txt "account backup.txt"\nid -gn {user} > primary.txt'
            plan['reports'] = {'account.txt': {'account': user}, 'account backup.txt': {'account': user}, 'primary.txt': dev + '\n'}
    elif key == 'modes':
        initial('notes.txt', file('', 'private notes\n', 0o666))
        initial('private', file('', mode=0o600 if practice == 1 else 0o700, kind='dir'))
        if practice < 2:
            prompt = ('notes.txt는 소유자만 읽고 쓸 수 있고 그룹은 읽기만, 나머지는 접근할 수 없게 하세요. '
                      'private 폴더는 소유자 rwx, 그룹 r-x, 나머지 접근 불가로 설정하세요. 내용과 소유자는 보존하세요.')
            solution = 'chmod 640 notes.txt\nchmod 750 private' if practice == 0 else 'chmod u=rw,g=r,o= notes.txt\nchmod u=rwx,g=rx,o= private'
            if practice == 1: prompt = 'private 폴더는 현재 탐색 권한이 없어 들어갈 수 없습니다. 권한을 조사해 복구하세요.\n' + prompt
            plan['expected_files'].update({'notes.txt': file('', 'private notes\n', 0o640), 'private': file('', mode=0o750, kind='dir')})
        else:
            initial('source note.txt', file('', 'team=training\n', 0o600), True)
            prompt = 'source note.txt를 shared copy.txt로 복사하고 복사본만 소유자 읽기·쓰기, 나머지 읽기 전용으로 설정하세요. private 폴더는 소유자만 접근 가능하게 두세요. 원본 내용·권한을 바꾸지 마세요.'
            solution = 'cp "source note.txt" "shared copy.txt"\nchmod 644 "shared copy.txt"\nchmod 700 private'
            plan['expected_files'].update({'shared copy.txt': file('', 'team=training\n', 0o644), 'private': file('', mode=0o700, kind='dir')})
    elif key == 'owners':
        initial('handoff.txt', file('', 'handoff content\n', 0o600, 0, 0))
        initial('tray', file('', mode=0o700, owner=0, group=0, kind='dir'))
        target_user, target_uid = (user, uid) if practice == 1 else ('learner', 1100)
        if practice == 2:
            plan['files']['handoff.txt'] = file('', 'handoff content\n', 0o600)
            prompt = f'handoff.txt의 소유자는 그대로 두고 소유 그룹만 {dev}로 바꾸세요. 소유자 rw, 그룹 r, 나머지 접근 불가로 설정하세요. tray와 다른 파일은 그대로 두세요.'
            solution = f'sudo chgrp {dev} handoff.txt\nchmod 640 handoff.txt'
            plan['expected_files']['tray'] = plan['files']['tray'].copy()
        else:
            prompt = f'handoff.txt와 tray의 소유자를 {target_user}, 그룹을 {dev}로 바꾸세요. 파일은 640, 폴더는 750 권한으로 설정하세요. 내용과 다른 파일은 보존하세요.'
            solution = f'sudo chown {target_user}:{dev} handoff.txt tray\nsudo chmod 640 handoff.txt\nsudo chmod 750 tray'
            plan['expected_files']['tray'] = file('', mode=0o750, owner=target_uid, group=gid, kind='dir')
        plan['expected_files']['handoff.txt'] = file('', 'handoff content\n', 0o640, target_uid, gid)
    elif key in ('users', 'review'):
        if practice == 1 and key == 'users': account['shell'] = '/bin/sh'
        prompt = (f'{user} 사용자를 만드세요. UID={uid}, 기본 그룹={dev}, 보조 그룹={audit}, '
                  f'로그인 셸={account["shell"]}, 홈={home}입니다. 홈 폴더도 실제로 만들고 해당 사용자 소유로 두세요.')
        solution = f'sudo useradd -u {uid} -g {dev} -G {audit} -s {account["shell"]} -d {q(home)} -m {user}'
        plan['expected_users'][user] = account
        plan['expected_files']['homes/' + user] = {'type': 'dir', 'uid': uid, 'gid': gid}
        if practice == 2 or key == 'review':
            prompt += '\nsource note.txt를 새 홈의 handoff.txt로 인계하세요. 인계 파일의 소유자는 새 사용자, 권한은 640이어야 합니다. 원본과 keep.txt는 보존하세요.'
            group = ops if key == 'review' else dev
            if key == 'review':
                prompt += f'\nGID={gid + 2}인 {ops} 그룹을 만들고 새 사용자의 보조 그룹에 추가하세요. 기존 {audit}도 유지하세요. 인계 파일의 그룹은 {ops}, 홈 권한은 750으로 설정하세요. 새 사용자의 UID와 모든 그룹 이름을 uid.txt와 groups.txt에 기록하세요.'
                solution += f'\nsudo groupadd -g {gid + 2} {ops}\nsudo usermod -a -G {ops} {user}'
                account['groups'] = [dev, audit, ops]
                plan['expected_groups'][ops] = gid + 2
                plan['expected_files']['homes/' + user]['mode'] = 0o750
                plan['reports'] = {'uid.txt': f'{uid}\n', 'groups.txt': {'tokens': [dev, audit, ops]}}
            solution += f'\nsudo cp "source note.txt" {q(home + "/handoff.txt")}\nsudo chown {user}:{group} {q(home + "/handoff.txt")}\nsudo chmod 640 {q(home + "/handoff.txt")}'
            plan['expected_files']['homes/' + user + '/handoff.txt'] = file('', 'team=training\n', 0o640, uid, gid + (2 if key == 'review' else 0))
            if key == 'review': solution += f'\nsudo chmod 750 {q(home)}\nid -u {user} > uid.txt\nid -Gn {user} > groups.txt'
    elif key == 'groups':
        plan['expected_groups'][ops] = gid + 2
        if practice == 2:
            plan['groups'][ops] = gid + 2
            plan['users'][user]['groups'] = [dev, ops]
            prompt = f'{user}는 필요한 {audit} 보조 그룹을 잃었습니다. 현재 {ops}를 보존하며 {audit}를 복구하세요. 기본 그룹 {dev}는 바꾸지 마세요. 결과 그룹 이름을 groups.txt에 기록하세요.'
            solution = f'sudo usermod -a -G {audit} {user}'
        else:
            prompt = f'GID={gid + 2}인 {ops} 그룹을 만드세요. '
            solution = f'sudo groupadd -g {gid + 2} {ops}'
            if practice == 1:
                prompt += f'{user}의 기본 그룹을 {ops}로 바꾸되 보조 그룹 {audit}는 유지하세요. 그룹 이름을 groups.txt에 기록하세요.'
                solution += f'\nsudo usermod -g {ops} {user}'
                plan['expected_users'][user]['gid'] = gid + 2
            else:
                prompt += f'{user}의 기본 그룹 {dev}와 기존 보조 그룹 {audit}를 유지하며 {ops}를 추가하세요. 그룹 이름을 groups.txt에 기록하세요.'
                solution += f'\nsudo usermod -a -G {ops} {user}'
        groups = [ops, audit] if practice == 1 else [dev, audit, ops]
        plan['expected_users'][user]['groups'] = groups
        plan['reports'] = {'groups.txt': {'tokens': groups}}
        solution += f'\nid -Gn {user} > groups.txt'
    else:
        raise ValueError('Unknown administration lesson: ' + key)
    plan['expected_groups'].update({dev: gid, audit: gid + 1})
    return Mission(kind, seed, start, start + '/source note.txt', start + '/uid.txt', home,
                   '', '', prompt + '\n이 실습은 앱 전용 환경에서만 수행합니다.', solution, practice=practice, review=plan)


def grade_admin(plan, backend):
    checks = []
    def check(label, value): checks.append({'label': label, 'passed': bool(value)})
    for path, expected in plan['expected_files'].items():
        actual = backend.file_info(plan['start'] + '/' + path)
        check(path + ' · 내용/권한/소유 정보', actual is not None and all(actual.get(k) == v for k, v in expected.items()))
    for name, expected in plan['expected_users'].items():
        actual = backend.user_info(name)
        check(name + ' · UID/기본·보조 그룹/홈/셸', actual is not None and all(
            set(actual.get(k, [])) == set(v) if k == 'groups' else actual.get(k) == v for k, v in expected.items()))
    for name, gid in plan['expected_groups'].items():
        check(name + ' · 그룹과 GID', backend.group_id(name) == gid)
    for path, expected in plan['reports'].items():
        info = backend.file_info(plan['start'] + '/' + path)
        text = (info.get('text') or '') if info else ''
        if isinstance(expected, str): passed = text.strip() == expected.strip()
        elif 'tokens' in expected: passed = set(text.split()) == set(expected['tokens'])
        else:
            user = backend.user_info(expected['account'])
            fields = text.strip().split(':')
            passed = bool(user and len(fields) == 7 and fields[0] == expected['account'] and
                fields[2:4] == [str(user['uid']), str(user['gid'])] and fields[5:] == [user['home'], user['shell']])
        check(path + ' · 조사/인계 결과', info is not None and passed)
    return {'passed': bool(checks) and all(c['passed'] for c in checks), 'checks': checks}
