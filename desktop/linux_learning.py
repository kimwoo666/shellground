"""Concept-sized real-Linux demonstrations, including interpreting common errors."""
import shlex


def steps(unit, m):
    if unit.key.startswith('system_'):
        from system_course import steps as system_steps
        return system_steps(unit, m)
    if unit.key.startswith('io_'):
        from io_course import steps as io_steps
        return io_steps(unit, m)
    if unit.key.startswith('process_'):
        from process_course import steps as process_steps
        return process_steps(unit, m)
    if unit.key.startswith('shell_'):
        from shell_course import steps as shell_steps
        return shell_steps(unit, m)
    if unit.key.startswith('auth_'):
        from auth_course import steps as auth_steps
        return auth_steps(unit, m)
    if unit.key.startswith('apt_'):
        from apt_course import steps as apt_steps
        return apt_steps(unit, m)
    from learning_steps import LearningStep
    key, s, t, r, q = unit.key, m.source, m.target, m.report, shlex.quote
    result = []
    def add(title, why, command, check): result.append(LearningStep(title, why, command, check))
    if key == 'navigate':
        add('현재 위치부터 확인', 'pwd는 현재 디렉터리의 절대경로를 출력합니다. /로 시작하는 경로는 현재 위치와 관계없고, 상대경로는 현재 위치를 기준으로 해석합니다.',
            'pwd', '문제의 시작 위치와 현재 위치를 비교합니다.')
        add('폴더 하나로 이동', 'cd는 디렉터리 경로 하나를 받습니다. cd 원본 대상은 too many arguments(인자가 너무 많음) 오류입니다. 복사가 필요할 때 사용하는 cp와 다릅니다.',
            f'cd {q(s)}\npwd', '오류가 나면 그대로 다음 명령을 치지 말고 현재 위치부터 다시 확인합니다.')
        add('파일과 폴더·공백 경로 구분', 'cd guide.txt는 일반 파일에 들어가려는 것이므로 Not a directory입니다. No such file or directory는 경로가 없다는 뜻입니다. 공백이 있는 경로는 전체를 따옴표로 묶어 한 인자로 전달합니다.',
            'cd docs\npwd\ncd ..\ncd docs', '상대경로 docs는 이동할 때마다 현재 위치 기준입니다. 마지막 위치는 원본 폴더의 docs입니다.')
    elif key == 'pwdpaths':
        add('바로가기 이름을 따른 경로', 'shortcut은 준비된 심볼릭 링크입니다. cd로 따라 들어간 뒤 pwd -L은 들어올 때 사용한 논리 경로를 표시합니다.',
            f'cd {q(m.start + "/shortcut")}\npwd -L', '출력 끝에 shortcut이 남습니다. 링크를 만드는 작업은 이번 목표가 아닙니다.')
        add('실제로 가리키는 경로', 'pwd -P는 링크를 해석한 실제 디렉터리 경로를 표시합니다. 같은 장소라도 표시 문자열이 다를 수 있습니다.',
            'pwd -P', f'{s}/docs인지 확인합니다. -L/-P는 대문자입니다.')
    elif key == 'lsintro':
        add('기본 이름 목록', 'ls 경로는 그 폴더의 바로 아래 이름을 조회합니다. 조회만으로 현재 위치가 바뀌지는 않습니다.',
            f'ls {q(s)}', '이름 앞에 .이 있는 숨김 항목은 기본 목록에서 보이지 않습니다.')
        add('숨김 항목까지 보기', '-a는 숨김 항목과 .(현재 폴더), ..(부모 폴더)를 포함합니다. 같은 폴더를 조회해 두 결과를 비교합니다.',
            f'ls -a {q(s)}', '.env 등 기본 목록에 없던 이름을 확인합니다.')
    elif key == 'linux_ls_detail':
        add('이름에 상세 정보 더하기', '-l(소문자 L)은 권한·링크 수·소유자·그룹·바이트 크기·수정 시각·이름을 표시합니다. 첫 글자 d는 폴더, -는 일반 파일입니다.',
            f'ls -l {q(s)}', 'guide.txt는 파일이고 docs는 폴더인지 첫 열을 읽습니다.')
        add('이미 배운 숨김 옵션 조합', '-a와 -l은 함께 쓸 수 있습니다. -al과 -la는 이 조회에서 같은 의미입니다. 옵션 순서를 외우기보다 결과 조건을 읽습니다.',
            f'ls -al {q(s)}', '숨김 항목과 .·..에도 상세 정보가 생겼는지 확인합니다.')
    elif key in ('linux_ls_sizes', 'linux_ls_order'):
        option = '-alh' if key.endswith('sizes') else '-lS'
        add('새 출력 조건 비교', unit.explanation, f'ls -l {q(s)}\nls {option} {q(s)}',
            '크기의 표시 단위 또는 항목 순서만 달라지고 파일 내용은 그대로입니다.')
        add('조회 결과 인계', '이미 배운 >로 결과를 파일에 저장합니다. 조회 대상 바깥에 보고서를 두어 보고서 자체가 조사 항목에 끼지 않게 합니다.',
            m.solution + f'\ncat {q(r)}', '문제의 조건과 저장한 목록이 일치하는지 확인합니다.')
    elif key == 'lsoptions':
        add('숨김 포함과 .·.. 제외 구분', '-a는 .과 ..도 포함하고 -A는 둘을 제외합니다. -1은 이름을 한 줄에 하나씩 나열합니다. 이미 배운 출력 형식과 숨김 조건을 조합합니다.',
            f'ls -1a {q(s)}\nls -1A {q(s)} > {q(r + ".names")}\ncat {q(r + ".names")}', '숨김 파일은 남고 .·..만 빠져야 합니다.')
        add('크기 단위가 있는 상세 보고서', '이미 배운 -a/-l/-h의 조합입니다. 정렬 조건과 상세 정보의 포함 여부는 별개입니다.',
            f'ls -alh {q(s)} > {q(r + ".sizes")}', '상세 열과 읽기 쉬운 크기 단위를 확인합니다.')
        add('큰 파일부터 이름만 인계', '-S는 큰 크기순, -1은 이름 한 줄씩입니다. 숨김 포함 옵션을 넣지 않았으므로 숨김 항목은 제외됩니다.',
            f'ls -1S {q(s)} > {q(r + ".largest")}\ncat {q(r + ".largest")}', '이름순이 아니라 크기순이며 상세 열은 없어야 합니다.')
    elif key == 'recursive':
        add('바로 아래와 하위 전체의 차이', '-R은 대문자이며 하위 폴더를 재귀적으로 조회합니다. -r(역순)과 다릅니다.',
            f'ls -al {q(s)}\nls -alR {q(s)}', 'docs와 더 깊은 폴더의 제목·내용이 별도 구역으로 나오는지 봅니다.')
        add('전체 구조 보고서 저장', '출력 파일을 조회 대상 바깥에 둡니다. 현재 위치는 바꾸지 않아도 절대경로로 조회할 수 있습니다.',
            f'ls -alR {q(s)} > {q(r)}\ncat {q(r)}', '최상위뿐 아니라 여러 폴더의 구역이 저장되어야 합니다.')
    elif key == 'find':
        add('탐색 시작점과 이름 조건', 'find는 하위 폴더를 탐색합니다. -name 패턴을 따옴표로 묶어 셸이 먼저 *를 펼치지 않게 합니다.',
            f'find {q(s)} -name "*.deb"', '이름이 .deb로 끝나는 폴더도 결과에 섞일 수 있습니다.')
        add('일반 파일만 선택', '-type f는 일반 파일 조건, -type d는 디렉터리 조건입니다. 이름과 종류 조건을 둘 다 만족해야 합니다.',
            f'find {q(s)} -type f -name "*.deb"', 'folder.deb 같은 폴더가 제외되고 숨김 폴더 안의 파일은 포함됩니다.')
        add('경로 목록 저장', '절대경로로 시작하면 결과 경로도 절대경로입니다. 결과의 순서보다 빠짐없이 같은 파일을 찾았는지가 중요합니다.',
            m.solution, '목표 보고서에 일반 .deb 파일의 경로가 한 줄씩 남아야 합니다.')
    elif key == 'grep':
        add('대소문자 조건 하나 추가', '기본 grep은 대소문자를 구분합니다. 이번 새 옵션 -i는 ERROR/error/Error를 함께 찾습니다.',
            f'grep ERROR {q(s + "/app.log")}\ngrep -i error {q(s + "/app.log")}', '일치하는 줄이 1개에서 3개로 늘어나는 이유를 확인합니다.')
        add('일치한 줄 보관', '이미 배운 출력 저장입니다. 개수 파일과 내용 파일의 목적을 구별합니다.',
            f'grep -i error {q(s + "/app.log")} > {q(r)}', '일치한 줄의 내용과 순서가 유지되어야 합니다.')
        add('배운 파이프와 줄 수 조합', 'grep의 출력만 wc -l로 보내면 원본 전체가 아니라 일치한 줄만 셉니다.',
            f'grep -i error {q(s + "/app.log")} | wc -l > {q(r + ".count")}', '결과는 파일 이름 없이 숫자 3입니다.')
    elif key in ('curl', 'wget'):
        downloaded = t + '/received-' + m.artifact
        if key == 'curl':
            add('URL과 저장 경로 구별', '-o 뒤는 저장할 파일 경로, URL은 자료를 받을 주소입니다. 확장자는 파일 형식 설명일 뿐 명령어가 아닙니다.',
                f'curl -o {q(downloaded)} {m.url}', '지정한 파일 이름으로 받았는지 ls -l로 확인합니다.')
            add('실패와 주소 이동 처리', '-f는 HTTP 오류를 실패로 처리하고 -L은 리다이렉트를 따라갑니다. -o의 저장 이름 지정과 서로 다른 역할입니다. -O(대문자)는 URL의 원래 이름을 쓰는 별도 선택입니다.',
                f'curl -fL -o {q(downloaded)} {m.url}', '같은 파일에 다시 받아 정상 내용으로 덮어씁니다. 이 URL은 게스트 내부 실제 HTTP 서버입니다.')
        else:
            add('출력 파일 이름 지정', 'wget의 -O는 대문자 O입니다. curl -o와 대소문자가 다릅니다. 뒤에 저장 파일을 쓰고 URL을 넣습니다.',
                f'wget -O {q(downloaded)} {m.url}', '목표 이름으로 파일이 생겼는지 확인합니다.')
            add('디렉터리만 정하기', '-P는 디렉터리를 지정하고 파일 이름은 URL에서 가져옵니다. 필요하면 이미 배운 mv로 최종 이름을 바꿉니다.',
                f'mkdir {q(t + "/incoming")}\nwget -P {q(t + "/incoming")} {m.url}', 'incoming 안의 파일 이름이 URL의 마지막 부분과 같습니다.')
        add('다운로드 결과 확인', '다운로드 성공 표시와 원하는 위치에 파일이 있는지는 따로 확인합니다. 바이너리 파일을 무조건 cat으로 출력하지 않습니다.',
            f'ls -lh {q(downloaded)}', '권한·크기·경로를 확인하고 다음 단원에서 형식에 맞는 도구를 선택합니다.')
    elif key == 'archive':
        downloaded = t + '/received-' + m.artifact
        zipped = m.artifact.endswith('.zip')
        add('아카이브 내려받기', '이미 배운 curl을 사용합니다. 다운로드는 압축 해제가 아니므로 내부 파일이 바로 생기지 않습니다.',
            f'curl -fL -o {q(downloaded)} {m.url}', '원래 아카이브 파일도 보존합니다.')
        add('내부 경로 먼저 확인', 'zip은 unzip -l, tar.gz는 앞에서 배운 tar -tzf로 조회합니다. 확장자만 바꾸어 다른 형식의 도구로 읽을 수는 없습니다.',
            f'unzip -l {q(downloaded)}' if zipped else f'tar -tzf {q(downloaded)}', 'README.txt와 bin/hello.sh의 내부 상대경로를 찾습니다.')
        add('대상 폴더로 압축 해제', 'tar -x는 해제, -C는 해제할 디렉터리입니다. unzip에서는 -d가 대상 디렉터리입니다. 저장 이름 지정 옵션과 혼동하지 마세요.',
            f'mkdir -p {q(t + "/unpacked")}\n' + (f'unzip {q(downloaded)} -d {q(t + "/unpacked")}' if zipped else f'tar -xzf {q(downloaded)} -C {q(t + "/unpacked")}'),
            'unpacked 아래의 내부 경로 구조가 복원되어야 합니다.')
        add('복원 결과 읽기', '해제 명령이 끝났다고 다른 위치에 생긴 파일을 답으로 생각하지 않습니다. 목표 위치를 직접 확인합니다.',
            f'cat {q(t + "/unpacked/README.txt")}', 'Shellground training bundle 내용인지 확인합니다.')
    elif key in ('script', 'deb'):
        downloaded = t + '/received-' + m.artifact
        add('실제 파일 준비', '다운로드는 앞에서 배운 기능의 복습입니다. 사용자 개인 파일이나 외부 코드를 가져오는 문제가 아닙니다.',
            f'curl -fL -o {q(downloaded)} {m.url}', '지정한 파일 형식에 맞는 다음 조작을 선택합니다.')
        if key == 'script':
            add('실행 전에 내용 확인', '.sh 파일은 셸 스크립트입니다. 실행 전 내용을 읽어 어떤 파일을 쓰는지 확인합니다.',
                f'cat {q(downloaded)}', '첫 번째 인자를 결과 파일의 경로로 사용한다는 내용을 확인합니다.')
            add('권한과 실행 경로', 'chmod u+x는 소유자 실행 권한만 추가합니다. 실행하려는 프로그램의 경로를 명시해야 하며 현재 폴더라면 ./를 씁니다.',
                f'chmod u+x {q(downloaded)}\n{q(downloaded)} {q(t + "/receipt.txt")}', 'receipt.txt가 결과 경로이고 스크립트 원본의 경로와 다릅니다.')
        else:
            add('정보 조회 복습', '이미 배운 --info는 메타데이터 조회입니다. 다음 단계의 --extract는 설치가 아니라 내용 풀기입니다.',
                f'dpkg-deb --info {q(downloaded)}', 'Package 이름을 확인합니다.')
            add('패키지 내용만 추출', '--extract 파일 폴더 순서입니다. 관리자 권한이나 패키지 설치 없이 내부 파일을 풉니다.',
                f'dpkg-deb --extract {q(downloaded)} {q(t + "/unpacked")}', 'unpacked/usr/share/shellground/message.txt가 생겨야 합니다.')
    elif key == 'sim_env':
        add('현재 셸에서 환경변수 등록', 'export NAME=value는 자식 프로세스에도 전달할 변수를 등록합니다. = 양옆에는 공백을 넣지 않습니다.',
            f'export TEAM=team{m.seed}\nprintenv TEAM', '현재 셸에서 값이 보이는지 확인합니다.')
        add('자식 셸로 전달', 'bash -c 뒤는 별도 셸에서 실행할 명령 문자열입니다. 작은따옴표로 묶으면 현재 셸에서 먼저 펼치지 않습니다.',
            "bash -c 'printenv TEAM' > result.txt\ncat result.txt", '별도 셸에도 TEAM이 전달되었는지 확인합니다.')
        add('불필요한 변수 제거', 'unset은 현재 셸의 변수를 제거합니다. 결과 파일 삭제와는 다른 작업입니다.',
            'unset OLD_TEAM', 'TEAM은 유지하고 OLD_TEAM만 제거합니다.')
    elif key == 'sim_author':
        add('인자를 받을 스크립트 작성', '$1은 스크립트의 첫 인자입니다. 바깥 작은따옴표는 파일 작성 시 현재 셸이 $1을 먼저 바꾸지 않게 합니다. 안쪽 "$1"은 공백 경로 하나를 보존합니다.',
            m.solution.splitlines()[0] + '\ncat write.sh', 'write.sh 안에 $1이 그대로 남아 있어야 합니다.')
        add('공백 경로를 한 인자로 실행', 'bash 파일 인자는 새 셸에서 스크립트를 실행합니다. bash로 읽어 실행하는 경우 파일 자체의 실행 권한은 필수가 아닙니다.',
            m.solution.splitlines()[1] + '\ncat "result file.txt"', '공백 때문에 두 경로로 갈라지지 않고 ready 한 줄이 저장되어야 합니다.')
    elif key == 'sim_jobs':
        add('백그라운드 작업과 번호', '&는 명령을 백그라운드로 시작합니다. jobs는 현재 셸의 작업 목록입니다. %1 같은 작업 번호와 PID는 다릅니다.',
            'sleep 300 &\nsleep 300 &\njobs', '두 작업의 번호와 Running 상태를 확인합니다.')
        add('지정한 작업만 종료', 'kill %1은 첫 작업에 종료 요청을 보냅니다. 작업 목록 전체를 정리하라는 명령이 아닙니다.',
            'kill %1\njobs', '다른 작업은 계속 실행되어야 합니다.')
        add('종료하지 않고 중지', '-STOP은 일시 중지, -CONT는 재개 신호입니다. 종료된 작업을 재개하는 것과는 다릅니다.',
            'kill -STOP %2\njobs', '두 번째가 Stopped이며 종료되지는 않았는지 확인합니다.')
        add('재개해 본 뒤 목표 상태로', '같은 작업 번호에 -CONT를 보내 재개합니다. 새로운 sleep을 만들면 다른 작업이므로 목표와 달라집니다.',
            'kill -CONT %2\njobs\nkill -STOP %2', '마지막에는 두 번째 작업을 다시 중지 상태로 둡니다.')
    elif key == 'sim_apt':
        add('저장소 목록 갱신', 'sudo는 관리자 권한이 필요한 명령 앞에 붙입니다. apt update는 설치 가능한 목록을 갱신하며 프로그램 설치/업그레이드와 다릅니다.',
            'sudo apt update', '게스트 내부 교육용 패키지 저장소에서 목록을 받습니다.')
        add('패키지 하나 설치', 'apt install 이름은 실제 프로그램을 설치합니다. 확인 질문이 나오면 내용을 읽고 응답합니다. -y를 쓰면 확인을 자동 승인합니다.',
            'sudo apt install tree', '목록 갱신만 했을 때와 달리 tree 프로그램이 설치됩니다.')
        add('설치된 상태 조회', '--installed는 설치된 패키지 목록입니다. update/install/upgrade/remove는 서로 다른 목적이며 설치 여부를 추측하지 말고 조회합니다.',
            'apt list --installed\ntree --version', 'tree의 설치 상태와 실제 실행 결과를 확인합니다.')
    elif key.startswith('admin_'):
        user = 'sguser' + str(m.seed)
        if key == 'admin_users':
            add('이미 배운 계정 조건 정리', '여기는 UID·홈·셸·기본 그룹·보조 그룹의 조합 단원입니다. 새 옵션을 한꺼번에 소개하는 단계가 아닙니다. 먼저 사용할 그룹이 있는지 확인합니다.',
                f'getent group sgdev{m.seed}\ngetent group sgaudit{m.seed}', '계정을 만들기 전에 두 그룹이 존재해야 합니다.')
            add('배운 옵션을 한 명령으로 조합', '각 옵션의 뒤에 어떤 값을 넣는지 목표와 대조합니다. -d는 홈 주소, -m은 폴더 생성입니다. 같은 이름을 반복 생성하면 오류가 납니다.',
                m.solution, '성공 후에는 useradd를 다시 입력하지 말고 조회 명령으로 확인합니다.')
        elif key == 'admin_modes':
            add('폴더 권한은 파일과 다릅니다', '폴더의 r은 이름 목록 읽기, x는 경로 탐색, w+x는 항목 생성·삭제에 필요합니다. ls -ld는 폴더 안이 아니라 폴더 자체의 정보를 봅니다.',
                'ls -l notes.txt\nls -ld private', 'private의 d와 rwx 자리들을 읽습니다.')
            add('알고 있는 권한 표기로 지정', '기호·숫자 표기는 앞 단원의 복습입니다. 750은 소유자 rwx, 그룹 r-x, 나머지 권한 없음입니다.',
                m.solution, '파일 내용·소유자와 관계없는 파일은 보존합니다.')
        elif key == 'admin_groups':
            add('새 그룹 준비', '그룹 생성과 기존 계정 변경을 조합합니다. 앞에서 배운 groupadd -g의 번호를 계정 UID와 혼동하지 않습니다.',
                m.solution.splitlines()[0], '지정한 이름과 GID로 새 그룹이 생겼는지 확인합니다.')
            add('기존 보조 그룹 유지하며 변경', '-a -G 추가와 -g 기본 그룹 변경을 이미 따로 배웠습니다. 이번 목표가 어느 변경인지 읽고 적용합니다.',
                '\n'.join(m.solution.splitlines()[1:]), '새 그룹뿐 아니라 원래 그룹도 남아 있어야 합니다.')
        else:
            add('이번 기능만 적용', unit.explanation, m.solution,
                '예시를 실행한 뒤 같은 생성 명령을 반복하지 말고 결과를 조회합니다. 오류면 대상·이름·경로부터 확인합니다.')
        if key == 'admin_uid': verify = 'cat name.txt uid.txt'
        elif key == 'admin_group_ids': verify = 'cat primary.txt all.txt'
        elif key == 'admin_passwd': verify = 'cat account.txt'
        elif key in ('admin_mode_symbols', 'admin_mode_numbers'): verify = 'ls -l notes.txt'
        elif key == 'admin_modes': verify = 'ls -l notes.txt\nls -ld private'
        elif key in ('admin_chown', 'admin_chgrp', 'admin_owners'): verify = 'ls -l handoff.txt\nls -ld tray'
        elif key == 'admin_group_create': verify = f'getent group sgops{m.seed}'
        elif key == 'admin_user_uid': verify = f'id -u {user}'
        else: verify = f'id {user}\ngetent passwd {user}'
        add('실제 결과 확인', '변경 명령이 성공했어도 목표의 모든 조건이 맞는지 확인합니다. 조회는 새 계정을 다시 만들거나 기존 상태를 초기화하지 않습니다.',
            verify, '목표와 실제 조회 값을 비교하고 다른 파일·계정의 보존 조건도 확인합니다.')
    else:
        return ()
    return tuple(result)
