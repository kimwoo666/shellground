"""Small real-account exercises using the existing state-based guest grader."""
from copy import deepcopy
from dataclasses import replace
import shlex


def make_focused_admin(kind, seed=None, practice=0):
    from admin_lessons import make_admin_mission
    key = kind.removeprefix('admin_')
    base_key = ('users' if key.startswith('user_') else 'groups' if key.startswith('group_') and key != 'group_ids'
                else 'modes' if key.startswith('mode_') else 'owners' if key in ('chown', 'chgrp') else 'identity')
    m = make_admin_mission('admin_' + base_key, seed, 0)
    p = deepcopy(m.review)
    seed = m.seed
    user, dev, audit, ops = (prefix + str(seed) for prefix in ('sguser', 'sgdev', 'sgaudit', 'sgops'))
    uid, gid = 20000 + seed, 10000 + seed * 3
    home = m.start + '/homes/' + user
    q = shlex.quote
    p['reports'] = {}
    if key == 'uid':
        if practice == 0:
            prompt = '현재 사용자 이름은 name.txt에, 숫자 UID는 uid.txt에 저장하세요.'
            solution = 'whoami > name.txt\nid -u > uid.txt'
            p['reports'] = {'name.txt': 'learner\n', 'uid.txt': '1100\n'}
        else:
            prompt = f'현재 사용자와 {user}의 UID를 각각 self.txt와 member.txt에 저장하세요. 두 계정의 값을 바꾸어 적지 마세요.'
            solution = f'id -u > self.txt\nid -u {user} > member.txt'
            p['reports'] = {'self.txt': '1100\n', 'member.txt': f'{uid}\n'}
            if practice == 2:
                prompt += ' member.txt를 member backup.txt로 복사해 두 파일을 유지하세요.'
                solution += '\ncp member.txt "member backup.txt"'
                p['reports']['member backup.txt'] = f'{uid}\n'
    elif key == 'group_ids':
        names = practice != 1
        prompt = f'{user}의 기본 그룹 {"이름" if names else "번호"}은 primary.txt에, 기본·보조 그룹 전체의 {"이름" if names else "번호"}은 all.txt에 저장하세요.'
        solution = f'id -g{"n" if names else ""} {user} > primary.txt\nid -G{"n" if names else ""} {user} > all.txt'
        p['reports'] = {'primary.txt': (dev if names else str(gid)) + '\n', 'all.txt': {'tokens': [dev, audit] if names else [str(gid), str(gid + 1)]}}
        if practice == 2:
            prompt += ' all.txt를 groups backup.txt로 복사해 보관하세요.'
            solution += '\ncp all.txt "groups backup.txt"'
            p['reports']['groups backup.txt'] = p['reports']['all.txt']
    elif key == 'passwd':
        name = 'learner' if practice == 1 else user
        prompt = f'{name}의 계정 레코드 전체를 account.txt에 저장하세요. UID·기본 GID·홈·셸을 포함한 원래 콜론 구분 형식이어야 합니다.'
        solution = f'getent passwd {name} > account.txt'
        p['reports'] = {'account.txt': {'account': name}}
        if practice == 2:
            prompt += ' 조사 결과는 account backup.txt에도 복사하고 두 파일을 유지하세요.'
            solution += '\ncp account.txt "account backup.txt"'
            p['reports']['account backup.txt'] = {'account': name}
    elif key in ('mode_symbols', 'mode_numbers'):
        if practice == 2:
            m = make_admin_mission('admin_modes', seed, 2)
            p = deepcopy(m.review)
            prompt = 'source note.txt를 shared copy.txt로 복사하세요. 복사본만 소유자 읽기·쓰기, 그룹과 나머지는 읽기만 가능하게 하세요. 원본과 private 폴더는 그대로 두세요.'
            mode = 'u=rw,g=r,o=r' if key == 'mode_symbols' else '644'
            solution = f'cp "source note.txt" "shared copy.txt"\nchmod {mode} "shared copy.txt"'
        else:
            mode = 0o640 if practice == 0 else 0o600
            p['expected_files']['notes.txt']['mode'] = mode
            p['expected_files']['private'] = p['files']['private'].copy()
            if practice == 1:
                p['files']['notes.txt']['mode'] = 0o777
            prompt = 'notes.txt의 소유자에게 읽기·쓰기를 허용하고, ' + ('그룹에는 읽기만 허용하며 나머지 사용자는 접근하지 못하게 하세요.' if practice == 0 else '그룹과 나머지는 접근하지 못하게 하세요. 잘못 켜진 실행 권한도 없어야 합니다.') + ' 내용·소유자·다른 파일과 폴더는 보존하세요.'
            spec = ('u=rw,g=r,o=' if practice == 0 else 'u=rw,g=,o=') if key == 'mode_symbols' else f'{mode:o}'
            solution = 'chmod ' + spec + ' notes.txt'
    elif key in ('chown', 'chgrp'):
        target_user, target_uid = (user, uid) if practice == 1 else ('learner', 1100)
        for path in ('handoff.txt', 'tray'):
            p['expected_files'][path] = p['files'][path].copy()
        if key == 'chown':
            targets = ['handoff.txt', 'tray'] if practice == 2 else ['handoff.txt']
            prompt = f'{"와 ".join(targets)}의 소유자를 {target_user}로 바꾸세요. 기존 소유 그룹·권한·내용은 바꾸지 마세요.'
            solution = f'sudo chown {target_user} ' + ' '.join(targets)
            for path in targets: p['expected_files'][path]['uid'] = target_uid
        else:
            targets = ['handoff.txt', 'tray'] if practice == 2 else ['tray'] if practice == 1 else ['handoff.txt']
            prompt = f'{"와 ".join(targets)}의 소유 그룹만 {dev}로 바꾸세요. 기존 소유자·권한·내용은 보존하세요.'
            solution = f'sudo chgrp {dev} ' + ' '.join(targets)
            for path in targets: p['expected_files'][path]['gid'] = gid
    elif key == 'group_create':
        p['expected_users'] = deepcopy(p['users'])
        p['expected_groups'] = dict(p['groups'], **{ops: gid + 2})
        prompt = f'GID가 {gid + 2}인 {ops} 그룹을 만드세요. 기존 그룹과 계정은 바꾸지 마세요.'
        solution = f'sudo groupadd -g {gid + 2} {ops}'
        if practice == 1:
            other = ops + 'backup'
            prompt += f' 백업용으로 GID={gid + 3}인 별도 그룹 {other}도 만드세요.'
            solution += f'\nsudo groupadd -g {gid + 3} {other}'
            p['expected_groups'][other] = gid + 3
        if practice == 2:
            prompt += f' 새 그룹의 전체 레코드를 group.txt에 저장하세요.'
            solution += f'\ngetent group {ops} > group.txt'
            p['reports']['group.txt'] = f'{ops}:x:{gid + 2}:\n'
    elif key.startswith('user_'):
        # Only fields already introduced become goals; unrelated defaults are
        # deliberately not required. The owned guest tracks the explicit UID.
        p['expected_files'] = {name: value for name, value in p['expected_files'].items() if not name.startswith('homes/')}
        expected = {'uid': uid}
        solution = f'sudo useradd -u {uid}'
        prompt = f'UID={uid}인 새 사용자 {user}를 만드세요.'
        if key == 'user_uid' and practice == 1:
            taken = user + 'taken'
            p['users'][taken] = {'uid': uid - 1, 'gid': gid, 'home': m.start + '/homes/' + taken,
                                'shell': '/bin/bash', 'groups': [dev, audit]}
            p['expected_users'][taken] = deepcopy(p['users'][taken])
            prompt = f'{taken}가 UID={uid - 1}을 사용 중입니다. 기존 계정을 보존하고 별도 사용자 {user}를 UID={uid}로 만드세요.'
        if key != 'user_uid':
            if practice == 1: home = m.start + '/homes/team member'
            prompt += f' 홈 경로를 {home}로 기록하고 실제 홈 폴더도 해당 사용자 소유로 만드세요.'
            solution += f' -d {q(home)} -m'
            expected['home'] = home
            p['expected_files'][home[len(m.start) + 1:]] = {'type': 'dir', 'uid': uid}
        if key in ('user_shell', 'user_primary', 'user_extra'):
            shell = '/bin/sh' if practice == 1 else '/bin/bash'
            prompt += f' 로그인 셸은 {shell}이어야 합니다.'
            solution += ' -s ' + shell
            expected['shell'] = shell
        if key in ('user_primary', 'user_extra'):
            prompt += f' 기본 그룹은 준비된 {dev}입니다.'
            solution += ' -g ' + dev
            expected['gid'] = gid
        if key == 'user_extra':
            extra = [audit]
            if practice == 1:
                extra.append(ops)
                p['groups'][ops] = gid + 2
                p['expected_groups'][ops] = gid + 2
            prompt += ' 보조 그룹은 ' + ', '.join(extra) + '입니다.'
            solution += ' -G ' + ','.join(extra)
            expected['groups'] = [dev, *extra]
        solution += ' ' + user
        p['expected_users'][user] = expected
        if practice == 2:
            if key == 'user_uid':
                prompt += ' 새 계정 레코드를 account.txt에 저장하세요.'
                solution += f'\ngetent passwd {user} > account.txt'
                p['reports']['account.txt'] = {'account': user}
            else:
                prompt += ' source note.txt를 새 홈의 handoff.txt로 복사하고 복사본의 소유자를 새 사용자로 바꾸세요. 원본은 보존하세요.'
                destination = home + '/handoff.txt'
                solution += f'\nsudo cp "source note.txt" {q(destination)}\nsudo chown {user} {q(destination)}'
                p['expected_files'][destination[len(m.start) + 1:]] = {'type': 'file', 'text': 'team=training\n', 'uid': uid}
        prompt += ' 별도 지시가 없는 계정 설정은 기본값이어도 됩니다.'
    elif key in ('group_append', 'group_primary'):
        original_practice = (2 if practice == 2 else 0) if key == 'group_append' else 1
        m = make_admin_mission('admin_groups', seed, original_practice)
        p = deepcopy(m.review)
        p['groups'][ops] = gid + 2
        solution = '\n'.join(line for line in m.solution.splitlines() if 'groupadd' not in line)
        if key == 'group_append':
            prompt = (f'{user}의 기존 보조 그룹을 보존하면서 {ops}를 추가하세요. 기본 그룹 {dev}는 바꾸지 마세요.' if practice != 2 else
                      f'{user}의 보조 그룹에서 빠진 {audit}를 복구하세요. 현재 {ops}와 기본 그룹 {dev}는 유지하세요.')
        else:
            prompt = f'{user}의 기본 그룹을 준비된 {ops}로 바꾸세요. 기존 보조 그룹 {audit}는 유지하세요.'
        prompt += ' 변경 후 기본·보조 그룹의 모든 이름을 groups.txt에 저장하세요.'
        if practice == 1:
            prompt += ' 같은 결과를 groups backup.txt로 복사해 보관하세요.'
            solution += '\ncp groups.txt "groups backup.txt"'
            p['reports']['groups backup.txt'] = p['reports']['groups.txt']
        if key == 'group_primary' and practice == 2:
            prompt += ' 변경된 계정의 전체 레코드도 account.txt에 저장하세요.'
            solution += f'\ngetent passwd {user} > account.txt'
            p['reports']['account.txt'] = {'account': user}
    else:
        raise ValueError(kind)
    p['focus'] = key
    return replace(m, kind=kind, prompt=prompt, solution=solution, practice=practice, review=p)
