"""Real-Linux teaching sequence. No simulated command implementation lives here."""
from dataclasses import replace
import shlex

# Stable old keys retain earned completion; each new concept gets a new key.
LINUX_ORDER = (
    'navigate', 'pwdpaths', 'lsintro', 'linux_ls_detail', 'read',
    'report', 'list', 'long', 'linux_ls_sizes', 'linux_ls_order',
    'lsoptions', 'recursive', 'mkdir', 'touch', 'edit',
    'duplicate', 'rename', 'remove', 'workspace', 'copy',
    'mixed', 'linux_grep_basic', 'linux_head', 'linux_tail', 'linux_line_count',
    'linux_pipe', 'grep', 'find', 'permissions', 'curl',
    'wget', 'linux_tar_list', 'archive', 'script', 'linux_deb_info',
    'deb', 'sim_env', 'sim_author', 'sim_jobs', 'sim_apt',
    'admin_uid', 'admin_group_ids', 'admin_passwd', 'admin_identity', 'admin_mode_symbols',
    'admin_mode_numbers', 'admin_modes', 'admin_chown', 'admin_chgrp', 'admin_owners',
    'admin_group_create', 'admin_user_uid', 'admin_user_home', 'admin_user_shell', 'admin_user_primary',
    'admin_user_extra', 'admin_users', 'admin_group_append', 'admin_group_primary', 'admin_groups',
)

SPECS = (
    ('linux_ls_detail', 1, '목록의 상세 정보 읽기', 'ls -l · -al',
     'ls -l은 이름뿐 아니라 권한, 링크 수, 소유자, 그룹, 크기, 수정 시각을 보여 줍니다. 첫 글자가 d이면 폴더, -이면 일반 파일입니다.\n이미 배운 -a와 합친 -al은 숨김 항목과 .·..도 자세히 보여 줍니다. 이번에는 화면 조회만 합니다.'),
    ('linux_ls_sizes', 2, '파일 크기를 읽기 쉽게 표시', 'ls -lh · -alh',
     '-l의 크기는 기본적으로 바이트입니다. -h를 더하면 1024 단위 K/M/G처럼 읽기 쉽게 표시합니다. 파일 내용이나 실제 크기는 바뀌지 않습니다.\n이번에는 -h만 새로 익힙니다. 숨김 항목을 포함할 때는 이미 배운 -a도 함께 씁니다.'),
    ('linux_ls_order', 2, '큰 파일부터 정렬하기', 'ls -S · -1',
     '-S는 이름순 대신 큰 크기순으로 정렬합니다. 대문자 S입니다. -1은 숫자 1이며 이름을 한 줄에 하나씩 표시합니다. -l(소문자 L)의 상세 정보와 다릅니다.\n먼저 -lS로 크기를 확인하고, 인계용 이름 목록은 -1S로 저장합니다.'),
    ('linux_grep_basic', 3, '문자열이 있는 줄 찾기', 'grep 패턴 파일',
     'grep은 파일 이름을 찾는 명령이 아니라 내용에서 일치하는 줄을 고릅니다. 기본적으로 대소문자를 구분합니다.\ngrep ERROR app.log는 ERROR가 들어간 줄 전체를 원래 순서로 출력합니다. >로 저장할 수 있습니다. -i와 파이프는 뒤에서 따로 배웁니다.'),
    ('linux_head', 3, '파일 앞부분만 읽기', 'head -n',
     'head -n 3 파일은 첫 3줄을 출력합니다. 파일 전체가 길어도 처음 부분을 빠르게 확인합니다. -n 뒤 숫자는 줄 수입니다.\n원본을 자르거나 수정하지 않습니다. >를 붙이면 선택한 줄을 다른 파일로 저장합니다.'),
    ('linux_tail', 3, '파일 뒷부분만 읽기', 'tail -n',
     'tail -n 3 파일은 마지막 3줄을 출력합니다. 앞부분의 head와 비교해 끝에 추가된 로그를 확인합니다.\n원본을 수정하지 않으며 선택된 줄들의 순서는 원래 파일과 같습니다. 계속 기다리는 -f는 이번 단원에서 사용하지 않습니다.'),
    ('linux_line_count', 3, '내용과 줄 수 구분하기', 'wc -l · <',
     'wc -l 파일은 줄바꿈 수와 파일 이름을 출력합니다. wc -l < 파일은 파일 내용을 입력으로 주므로 이름 없이 개수만 출력합니다.\n<는 파일을 표준 입력으로 읽고, >는 결과를 파일로 저장하는 셸 기호입니다. 마지막 줄에 줄바꿈이 없으면 화면의 줄 수와 다를 수 있습니다.'),
    ('linux_pipe', 3, '명령의 출력을 다음 명령에 연결', '|',
     '|는 앞 명령의 표준 출력을 뒤 명령의 표준 입력으로 연결합니다. 파일 이름을 전달하는 기호가 아닙니다.\ngrep ERROR app.log | wc -l은 선택한 줄만 셉니다. 중간 파일 없이 연결하지만 원본은 유지됩니다. 최종 결과의 저장은 >로 합니다.'),
    ('linux_tar_list', 4, '압축을 풀기 전에 내부 경로 확인', 'tar -tzf',
     'tar -tzf 파일은 gzip으로 압축된 tar의 내부 이름을 조회합니다. -t는 목록, -z는 gzip, -f 바로 다음은 아카이브 파일입니다.\n조회는 압축 해제가 아닙니다. README.txt와 bin/hello.sh 같은 내부 상대경로를 먼저 확인하고, 다음 단원에서 -x와 -C로 풉니다.'),
    ('linux_deb_info', 4, 'Debian 패키지 정보만 확인', 'dpkg-deb --info',
     '.deb는 패키지 파일입니다. dpkg-deb --info 파일은 Package·Version·Architecture 등의 메타데이터를 보여 줍니다.\n정보 조회는 설치도 압축 해제도 아닙니다. 관리자 권한 없이 확인할 수 있고 파일 확장자를 바꾼다고 형식이 바뀌지 않습니다.'),
    ('admin_uid', 5, '사용자 이름과 UID', 'whoami · id -u',
     'whoami는 현재 사용자 이름, id -u는 숫자 UID입니다. 이름과 번호는 같은 종류의 값이 아닙니다.\nid -u 이름은 그 사용자의 UID를 조회합니다. 이름을 생략하면 현재 사용자입니다. 그룹 옵션은 다음 단원에서 배웁니다.'),
    ('admin_group_ids', 5, '기본 그룹과 보조 그룹 조회', 'id -g · -G · -n · groups',
     'id -g는 기본 그룹 번호 하나, id -G는 기본·보조 그룹 번호 전부입니다. -n을 결합한 -gn/-Gn은 번호 대신 이름을 출력합니다.\ngroups 이름으로 그룹 이름을 확인할 수도 있습니다. 대문자 G와 소문자 g를 구별하고, 목록의 순서보다 포함된 그룹을 비교하세요.'),
    ('admin_passwd', 5, '계정 레코드에서 홈과 셸 읽기', 'getent passwd',
     'getent passwd 이름은 계정 레코드 한 줄을 조회합니다. 이름:암호표시:UID:GID:설명:홈:셸 순서입니다. x는 실제 암호가 아닙니다.\n앞에서 배운 id와 달리 홈과 로그인 셸도 확인할 수 있습니다. 조회 결과를 저장해 인계합니다.'),
    ('admin_mode_symbols', 5, '대상별 권한을 기호로 지정', 'chmod u= · g= · o=',
     'u는 소유자, g는 그룹, o는 나머지 사용자입니다. r/w/x는 읽기/쓰기/실행입니다.\nchmod u=rw,g=r,o= 파일은 소유자 읽기·쓰기, 그룹 읽기, 나머지 접근 불가로 교체합니다. =는 지정, +는 추가, -는 제거입니다. 숫자 표기는 다음 단원에서 배웁니다.'),
    ('admin_mode_numbers', 5, '같은 권한을 숫자로 표현', 'chmod 640 · 600 · 644',
     'r=4, w=2, x=1을 더합니다. 세 자리의 순서는 소유자·그룹·나머지입니다. 6은 읽기+쓰기, 4는 읽기만, 0은 권한 없음입니다.\n640은 앞서 배운 u=rw,g=r,o=와 같습니다. 이번에는 일반 파일에서 기호와 숫자를 비교하고, 폴더 권한은 다음 단원에서 다룹니다.'),
    ('admin_chown', 5, '관리자 권한으로 소유자 변경', 'sudo · chown',
     'sudo는 허용된 명령을 관리자 권한으로 실행하도록 요청합니다. 이 앱에서는 전용 실습 Linux에만 적용됩니다.\nchown 이름 파일은 소유자만 바꿉니다. chmod의 읽기·쓰기 권한 변경과 다릅니다. ls -l로 변경 전후 소유자와 기존 그룹을 함께 확인하세요.'),
    ('admin_chgrp', 5, '소유자를 유지하며 그룹만 변경', 'sudo chgrp',
     'chgrp 그룹 파일은 소유 그룹만 바꾸고 사용자 소유자는 유지합니다. 그룹이 먼저 존재해야 합니다.\nchown 사용자:그룹 파일은 둘을 함께 바꾸는 조합입니다. 이번에는 chgrp로 그룹만 바꾸는 작업에 집중합니다.'),
    ('admin_group_create', 5, 'GID를 지정해 그룹 생성', 'groupadd -g · getent group',
     'sudo groupadd -g 번호 이름은 지정한 GID로 그룹을 만듭니다. -g는 여기서 그룹 번호를 지정하는 옵션입니다.\ngetent group 이름으로 이름:x:GID:구성원을 확인합니다. 이미 쓰는 이름이나 GID로 새 그룹을 만들면 오류입니다. 사용자를 그룹에 넣는 일은 별도입니다.'),
    ('admin_user_uid', 5, 'UID를 지정해 계정 생성', 'useradd -u',
     'sudo useradd -u 번호 이름으로 새 계정을 만듭니다. -u는 UID이며 사용자의 이름과 구분합니다.\n이미 있는 이름/UID는 오류입니다. id -u 이름으로 실제 UID를 확인하세요. 이 단계에서는 홈 생성·셸·그룹을 한꺼번에 지정하지 않습니다.'),
    ('admin_user_home', 5, '홈 경로 지정과 실제 폴더 생성', 'useradd -d · -m',
     '-d 경로는 계정에 홈 주소를 기록하고, -m은 그 폴더를 실제로 만듭니다. -d만 쓰는 것과 다릅니다.\n이미 배운 -u에 두 옵션을 추가합니다. getent passwd로 기록된 경로, ls -ld로 폴더 존재와 소유자를 따로 확인하세요.'),
    ('admin_user_shell', 5, '새 계정의 로그인 셸 지정', 'useradd -s',
     '-s /bin/bash는 새 계정의 로그인 셸을 지정합니다. 지금 터미널의 셸을 바꾸거나 해당 사용자로 로그인하는 명령이 아닙니다.\nUID·홈 설정은 앞 단원의 복습입니다. getent passwd의 마지막 필드로 셸 경로를 확인합니다.'),
    ('admin_user_primary', 5, '새 계정의 기본 그룹 지정', 'useradd -g',
     'useradd -g 그룹은 새 계정의 기본 그룹 하나를 지정합니다. 그룹은 먼저 있어야 합니다. groupadd -g 번호와 같은 문맥이 아닙니다.\nid -gn 이름으로 기본 그룹 이름을 확인하세요. 여러 그룹 목록을 -g에 넣지 않습니다. 보조 그룹은 다음 단원입니다.'),
    ('admin_user_extra', 5, '새 계정의 보조 그룹 지정', 'useradd -G',
     '대문자 -G는 보조 그룹 목록입니다. 여러 개면 공백 없이 쉼표로 구분합니다. 소문자 -g의 기본 그룹 하나와 구별합니다.\n이번에는 앞서 배운 계정 설정에 -G만 추가합니다. id -Gn 이름에는 기본 그룹도 함께 나오므로 두 종류를 구분해서 확인하세요.'),
    ('admin_group_append', 5, '기존 보조 그룹을 유지하며 추가', 'usermod -a -G',
     'useradd는 새 계정 생성, usermod는 이미 있는 계정 변경입니다. -a -G 그룹은 기존 보조 그룹을 유지하며 추가합니다.\n-a 없이 -G만 쓰면 목록을 교체합니다. 현재 그룹을 먼저 조회하고, 복구 후에도 기존 그룹이 남았는지 확인하세요.'),
    ('admin_group_primary', 5, '기존 계정의 기본 그룹 변경', 'usermod -g',
     'usermod -g 그룹 이름은 이미 있는 계정의 기본 그룹을 바꿉니다. 보조 그룹 추가인 -a -G와 다릅니다.\nid -gn과 -Gn으로 기본 그룹 변경과 보조 그룹 보존을 각각 확인하세요. 실행 중인 로그인 셸은 재로그인 전까지 이전 그룹 정보를 사용할 수 있습니다.'),
)
NEW_KEYS = frozenset(s[0] for s in SPECS)


def units(Unit, existing):
    result = {u.key: u for u in existing}
    result.update({key: Unit(key, level, title, commands, explanation,
                            '목표의 대상·조건을 확인하고 F3에서 이번 기능의 예시를 확인하세요.')
                   for key, level, title, commands, explanation in SPECS})
    # The ls cluster deliberately needs only read and redirection between
    # screen inspection and reports. Copy/create are taught in the next block.
    result['list'] = replace(result['list'], title='숨김 목록을 파일로 저장', commands='ls -1a · >',
        explanation='새 조회 옵션을 다시 배우는 단원이 아닙니다. 이미 배운 숨김 목록을 파일로 인계합니다.\n-1(숫자 1)은 한 줄에 한 항목, >는 덮어쓰기입니다. cat으로 저장 결과를 확인합니다. 원본 폴더는 변경하지 않습니다.')
    result['long'] = replace(result['long'], title='상세 목록과 작업 경로 인계',
        explanation='앞에서 화면으로 읽은 -l/-al 상세 목록을 보고서로 저장합니다.\n목록과 현재 디렉터리의 경로는 다른 정보입니다. 목록은 ls로, 경로는 pwd로 얻어 각각 요구한 파일에 저장합니다.')
    result['lsoptions'] = replace(result['lsoptions'], explanation=
        '이번에 새로 비교할 것은 -a와 -A입니다. 둘 다 숨김 항목을 포함하지만 -A는 .과 ..를 제외합니다.\n이미 배운 -1/-l/-h/-S를 보고서의 목적에 맞게 조합합니다. 이름 목록, 읽기 쉬운 크기의 상세 목록, 큰 크기순 목록은 서로 다른 결과입니다.')
    result['navigate'] = replace(result['navigate'], explanation=result['navigate'].explanation +
        '\n\n오류 읽기: cd는 폴더 경로 하나를 받습니다. too many arguments는 인자가 너무 많다는 뜻입니다. '
        'Not a directory는 파일을 폴더처럼 이동하려 했다는 뜻, No such file or directory는 그 경로가 없다는 뜻입니다. '
        '공백 경로는 따옴표로 한 인자로 묶으세요. cd는 복사가 아니며 원본·대상 두 경로를 받지 않습니다.')
    result['duplicate'] = replace(result['duplicate'], explanation=result['duplicate'].explanation +
        '\n\ncd 원본 대상은 복사가 아니므로 too many arguments가 납니다. cp 원본 대상 순서로 쓰세요. '
        '목적지 폴더가 없으면 먼저 mkdir로 만듭니다. cp의 missing destination file operand는 목적지를 빠뜨렸다는 뜻입니다.')
    return tuple(result[key] for key in LINUX_ORDER)


def make_linux_mission(kind, seed=None, practice=0):
    from missions import make_mission
    m = make_mission('long', seed, 0)
    s, t, r, q = m.source, m.target, m.report, shlex.quote
    setup, goals = [], []
    def file(path, text): return {'type': 'file', 'path': path, 'text': text}
    def listing(options, path=r): return {'type': 'listing', 'path': path, 'source': s, 'options': options}
    if kind == 'linux_ls_detail':
        hidden = practice != 0
        option = '-al' if hidden else '-l'
        prompt = f'{s}의 바로 아래 항목을 권한·소유자·그룹·크기·수정 시각이 보이는 상세 형식으로 화면에 표시하세요.'
        if hidden: prompt += ' 숨김 항목과 .·..도 포함하세요.'
        solution = f'ls {option} {q(s)}'
        if practice == 2:
            prompt += ' 조회한 폴더로 이동한 뒤 그 위치에 머무세요.'
            solution = f'cd {q(s)}\nls {option}'
            goals.append({'type': 'cwd', 'path': s})
        goals.append({'type': 'output_listing', 'source': s, 'options': option})
    elif kind in ('linux_ls_sizes', 'linux_ls_order'):
        setup = [file(s + '/large-sample.bin', 'X' * 16384)]
        if kind.endswith('sizes'):
            options = '-alh' if practice != 1 else '-lh'
            prompt = f'{s}의 바로 아래 상세 목록을 K/M 등 읽기 쉬운 크기 단위로 {r}에 저장하세요. '
            prompt += '숨김 항목과 .·..도 포함하세요.' if practice != 1 else '숨김 항목은 제외하세요.'
        else:
            options = '-1S' if practice != 1 else '-lS'
            prompt = f'{s}의 숨김 항목을 제외한 바로 아래 목록을 큰 크기순으로 {r}에 저장하세요. '
            prompt += '이름만 한 줄에 하나씩 기록하세요.' if practice != 1 else '크기와 권한 등 상세 정보도 포함하세요.'
        solution = f'ls {options} {q(s)} > {q(r)}'
        goals = [listing(options)]
        if practice == 2:
            setup.append(file(r, 'outdated inventory\n'))
            prompt = '기존 보고서는 잘못된 내용입니다. 덧붙이지 말고 올바른 결과로 덮어쓰세요.\n' + prompt
            prompt += f'\n대상 폴더로 이동한 뒤 현재 디렉터리의 절대경로를 {r}.where에 저장하세요.'
            solution += f'\ncd {q(s)}\npwd > {q(r + ".where")}'
            goals.append(file(r + '.where', s + '\n'))
    elif kind in ('linux_grep_basic', 'linux_head', 'linux_tail', 'linux_line_count', 'linux_pipe'):
        log = 'INFO start\nERROR disk full\nwarning warm\nerror timeout\nINFO ready\nError network\n'
        source = s + '/app.log'
        if kind == 'linux_grep_basic':
            pattern = 'ERROR' if practice != 1 else 'INFO'
            prompt = f'{source}에서 대소문자를 구분해 {pattern}가 포함된 줄만 {r}에 저장하세요.'
            solution = f'grep {pattern} {q(source)} > {q(r)}'
            expected = ''.join(line + '\n' for line in log.splitlines() if pattern in line)
        elif kind in ('linux_head', 'linux_tail'):
            count = 2 if practice != 1 else 3
            command = 'head' if kind.endswith('head') else 'tail'
            prompt = f'{source}의 {"첫" if command == "head" else "마지막"} {count}줄만 원래 순서대로 {r}에 저장하세요.'
            solution = f'{command} -n {count} {q(source)} > {q(r)}'
            lines = log.splitlines()[:count] if command == 'head' else log.splitlines()[-count:]
            expected = '\n'.join(lines) + '\n'
        elif kind == 'linux_line_count':
            prompt = f'{source}의 줄 수를 {r}에 저장하세요. 파일 이름 없이 숫자만 있어야 합니다.'
            solution = f'wc -l < {q(source)} > {q(r)}'
            expected = '6'
        else:
            pattern = 'ERROR' if practice != 1 else 'INFO'
            prompt = f'{source}에서 대소문자를 구분해 {pattern}가 포함된 줄의 개수만 {r}에 저장하세요.'
            solution = f'grep {pattern} {q(source)} | wc -l > {q(r)}'
            expected = str(sum(pattern in line for line in log.splitlines()))
        goals = [dict(file(r, expected), type='stripped_file') if kind in ('linux_line_count', 'linux_pipe') else file(r, expected), file(source, log)]
        if practice == 2:
            prompt += f'\n{r}을 {t}/review copy.txt로 복사해 인계하세요. 로그 원본과 두 결과 파일을 모두 유지하세요.'
            solution += f'\ncp {q(r)} {q(t + "/review copy.txt")}'
            target_goal = dict(goals[0], path=t + '/review copy.txt')
            goals.append(target_goal)
    elif kind == 'linux_tar_list':
        path = s + '/bundle.tar.gz'
        prompt = f'{path}를 풀지 않고 내부 경로 목록을 {r}에 저장하세요. 원본 아카이브는 보존하세요.'
        solution = f'tar -tzf {q(path)} > {q(r)}'
        goals = [file(r, 'README.txt\nbin/\nbin/hello.sh\n')]
        if practice == 1:
            prompt += f'\n목록의 줄 수만 {r}.count에 저장하세요.'
            solution += f'\nwc -l < {q(r)} > {q(r + ".count")}'
            goals.append({'type': 'stripped_file', 'path': r + '.count', 'text': '3'})
        if practice == 2:
            prompt += f'\n조회 결과 중 bin/이 포함된 줄만 {r}.bin에 별도로 저장하세요.'
            solution += f'\ngrep bin/ {q(r)} > {q(r + ".bin")}'
            goals.append(file(r + '.bin', 'bin/\nbin/hello.sh\n'))
    elif kind == 'linux_deb_info':
        path = s + '/toolkit.deb'
        prompt = f'{path}의 패키지 정보를 조회해 {r}에 저장하세요. 패키지는 설치하지 마세요.'
        solution = f'dpkg-deb --info {q(path)} > {q(r)}'
        goals = [{'type': 'file_contains', 'path': r, 'text': text} for text in ('Package: shellground-toolkit', 'Version: 1.0', 'Architecture: all')]
        if practice == 1:
            prompt += f'\n정보에서 Package:가 포함된 줄만 {r}.name에 별도로 저장하세요.'
            solution += f'\ngrep Package: {q(r)} > {q(r + ".name")}'
            goals.append({'type': 'file_contains', 'path': r + '.name', 'text': 'Package: shellground-toolkit'})
        if practice == 2:
            prompt += f'\n공백이 있는 {t}/package info.txt로 정보 파일의 복사본을 남기세요.'
            solution += f'\ncp {q(r)} {q(t + "/package info.txt")}'
            goals.extend(dict(g, path=t + '/package info.txt') for g in list(goals))
    else:
        raise ValueError(kind)
    return replace(m, kind=kind, prompt=prompt, solution=solution, practice=practice,
                   review={'setup': setup, 'goals': goals, 'keep_base': False, 'title': '작은 기능과 이전 학습 조합'})


def adjust_early_mission(m):
    """Real course prerequisites: no cp/mkdir before the file-work block."""
    if m.practice != 2 or m.kind not in ('list', 'recursive'): return m
    from missions import make_mission
    base = make_mission(m.kind, m.seed, 0)
    if m.kind == 'list':
        prompt = f'{m.report}에는 오래된 잘못된 목록이 있습니다. {m.source} 바로 아래의 숨김 항목과 .·..를 포함한 이름 목록으로 덮어쓰세요. 한 줄에 하나씩 기록하세요.'
        review = {'setup': [{'type': 'file', 'path': m.report, 'text': 'obsolete inventory\n'}],
                  'goals': [{'type': 'listing', 'source': m.source, 'options': '-1a', 'path': m.report}], 'keep_base': False}
        solution = f'ls -1a {shlex.quote(m.source)} > {shlex.quote(m.report)}\ncat {shlex.quote(m.report)}'
    else:
        prompt = (f'{m.source}의 바로 아래 숨김 포함 상세 목록은 {m.report}.top에, '
                  f'모든 하위 폴더까지의 숨김 포함 상세 목록은 {m.report}에 저장하세요. 두 파일은 서로 다른 범위를 담아야 합니다.')
        review = {'setup': [], 'goals': [{'type': 'listing', 'source': m.source, 'options': opt, 'path': path}
                   for opt, path in [('-al', m.report + '.top'), ('-alR', m.report)]], 'keep_base': False}
        solution = f'ls -al {shlex.quote(m.source)} > {shlex.quote(m.report + ".top")}\nls -alR {shlex.quote(m.source)} > {shlex.quote(m.report)}'
    return replace(base, prompt=prompt, solution=solution, practice=2, review=dict(review, real_course_v2=True))
