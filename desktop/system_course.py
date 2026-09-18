"""Read actual Linux identity, virtual interfaces and clocks; never emulate them."""
import random

SPECS = (
    ('system_identity', '커널·배포판·호스트 구분', 'uname · hostname · os-release',
     'uname -s는 커널 이름, -r은 커널 릴리스, -m은 머신 종류입니다. hostname은 현재 환경의 이름을 읽습니다. 커널 릴리스와 Ubuntu 같은 배포판 버전은 다릅니다.\n'
     'uname -a는 여러 커널·머신 정보를 한 줄로 보여 줍니다. -p/-i는 unknown이면 생략될 수 있으므로 필드 수를 외우지 않습니다. 배포판은 /etc/os-release의 ID·VERSION_ID·PRETTY_NAME을 읽습니다.\n'
     '호스트 이름이 나온다고 DNS 등록이나 다른 기기의 접속 성공이 증명되지는 않습니다. 이름 변경 없이 조회만 합니다.'),
    ('system_links', '인터페이스 존재와 상태 조사', 'ip link · -brief · ifconfig -a',
     'ip link show는 인터페이스와 링크 정보를 읽습니다. ip -brief link show는 짧은 표입니다. <…> 안의 UP는 관리자가 사용을 허용한 상태이며, 뒤의 state는 링크의 동작 상태입니다.\n'
     '관리 UP라도 상대 연결이 끊어지면 실제 통신이 안 될 수 있습니다. UNKNOWN 역시 모든 기능의 고장을 뜻하지 않습니다. 인터페이스 이름은 항상 eth0인 것이 아닙니다.\n'
     'ifconfig -a는 내려간 인터페이스까지 보여 줍니다. -a 없는 ifconfig는 일부를 생략합니다. 오래된 문서를 읽을 때 유용하며 새 조사에는 ip를 우선 사용할 수 있습니다. 준비된 veth 쌍은 실제 Linux 가상 인터페이스이고 외부 인터넷 연결이 아닙니다.'),
    ('system_addresses', '주소 종류와 조회 대상 구분', 'ip address · -4 · -6 · dev',
     'ip address show는 인터페이스별 주소를 읽습니다. -4는 IPv4, -6는 IPv6이고 dev 이름은 조사할 인터페이스 하나를 고릅니다. /24 같은 접두 길이는 주소와 함께 기록합니다.\n'
     '한 인터페이스에 여러 주소가 있을 수 있습니다. 주소가 설정되어 있어도 인터페이스가 DOWN이거나 경로·서비스가 없으면 통신 성공을 뜻하지 않습니다.\n'
     'ip -4 -brief address show dev 이름처럼 보기 형식과 주소 종류·대상을 조합합니다. 이 과정은 설정을 바꾸는 add/del/flush가 아니라 show로 읽는 조사입니다.'),
    ('system_time', '현재 시각·표시·파일 시각', 'date +%s · -u · -d · -r',
     'date +%s는 Epoch(일반적인 POSIX 시간의 1970-01-01 00:00:00 UTC) 기준 초 수입니다. 부팅 뒤 경과 시간이 아닙니다. -u는 UTC 표시를 고릅니다.\n'
     '+%FT%TZ는 UTC에서 날짜T시각Z로 출력하는 형식입니다. -d @숫자는 그 epoch를, -d "시간 문자열"은 지정한 시각을 표시합니다. -d는 조회이고 -s는 시스템 시계 변경이므로 이번에는 쓰지 않습니다.\n'
     '$(명령)은 그 명령의 출력을 가져옵니다. 따옴표 안에 넣어 공백을 한 인자로 유지합니다. 두 시각 조회 사이 시간이 흐르므로 같은 순간의 표현을 비교할 때는 먼저 저장한 epoch를 재사용합니다. -r 파일은 그 파일의 마지막 수정 시각을 읽습니다. 생성 시각이 아닙니다.'),
    ('system_clock', '시계와 동기화 상태의 근거', 'timedatectl · hwclock --show · 종료 상태',
     'date의 시스템 시계, 하드웨어 시계 RTC, NTP 동기화 서비스는 다른 대상입니다. timedatectl status는 사람이 읽는 상태이고 show는 이름=값 형식입니다.\n'
     '-p 속성으로 Timezone(표시 시간대), LocalRTC(RTC를 로컬 시각으로 취급하는지), NTP(동기화 서비스 활성), NTPSynchronized(실제 동기화 여부)를 따로 읽습니다. NTP=yes만으로 동기화 성공은 아닙니다.\n'
     'sudo hwclock --show는 이 전용 guest의 RTC 조회만 시도합니다. 장치가 없으면 관리자여도 실패합니다. > 파일 2>&1은 표준 출력과 오류를 함께 저장하고 바로 다음 $?는 종료 상태입니다. 0은 명령 성공, 나머지는 실패입니다.\n'
     'RTC 오류를 성공 출력으로 바꾸지 마세요. 이 단원 완료는 현재 지원 상태를 올바르게 조사했다는 뜻이며 RTC 읽기·NTP 동기화 성공을 보장하지 않습니다. 호스트 시계·시간대·NTP 설정을 바꾸지 않습니다.'),
)
KEYS = tuple(row[0] for row in SPECS)


def units(Unit):
    return tuple(Unit(key, 3, title, command, text, '실제 관찰과 추측을 구별하고 설정·원본을 유지하세요.') for key, title, command, text in SPECS)


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    if kind not in (*KEYS, 'system_review') or practice not in (0, 1, 2): raise ValueError('Unknown system exercise')
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    start = f'/home/learner/system/session{seed}'; active, spare = f'sgsi{seed}a', f'sgsi{seed}b'
    plan = dict(system_course=1, interfaces=[active, spare], identity=[], links={}, addresses={},
                time='', clock=False, rtc=False, verdict=False, backup=False, incident_copy=False)
    descriptions = []; actions = []
    identity_commands = dict(kernel='uname -s', release='uname -r', machine='uname -m', host='hostname',
                             all='uname -a', os_release='cat /etc/os-release', distro="grep '^VERSION_ID=' /etc/os-release")
    def identity(names):
        plan['identity'] = names
        for name in names: actions.append(identity_commands[name] + ' > ' + name + '.txt')
    def link(name, targets, legacy=False):
        plan['links'][name] = targets
        actions.append(('ifconfig -a' if legacy else 'ip -brief link show' + (' dev ' + targets[0] if targets else '')) + ' > ' + name)
    def address(name, interface, families):
        plan['addresses'][name] = dict(interface=interface, families=families)
        flag = '-4 ' if families == ['inet'] else '-6 ' if families == ['inet6'] else ''
        actions.append(f'ip {flag}address show dev {interface} > {name}')
    def time_report(mode):
        plan['time'] = mode
        if mode == 'now':
            actions.extend(['date +%s > epoch.txt', 'date -u -d "@$(cat epoch.txt)" +%FT%TZ > utc.txt'])
        elif mode == 'event':
            actions.extend(['date -d "$(cat \'event time.txt\')" +%s > event-epoch.txt',
                            'date -u -d "$(cat \'event time.txt\')" +%FT%TZ > event-utc.txt'])
        else:
            actions.extend(['date -r "source notes.txt" +%s > modified-epoch.txt',
                            'date -u -r "source notes.txt" +%FT%TZ > modified-utc.txt', 'date +%s > epoch.txt'])
    def clocks(rtc=False, verdict=False):
        plan.update(clock=True, rtc=rtc, verdict=verdict)
        actions.append('timedatectl show -p Timezone -p LocalRTC -p NTP -p NTPSynchronized > clock-state.txt')
        if rtc:
            actions.extend(['sudo hwclock --show > rtc.txt 2>&1', 'rtc_code=$?', 'printf "%s\\n" "$rtc_code" > rtc-exit.txt'])
        if verdict:
            actions.extend(['if [ "$rtc_code" -eq 0 ]; then printf "rtc=available\\n" > conclusion.txt; else printf "rtc=unavailable\\n" > conclusion.txt; fi',
                            'sync_state=$(timedatectl show -p NTPSynchronized --value)',
                            'printf "synchronized=%s\\n" "$sync_state" >> conclusion.txt'])
    if kind == 'system_identity':
        if practice == 0:
            descriptions.append('커널 이름·커널 릴리스·머신 종류·호스트 이름을 각각 kernel.txt, release.txt, machine.txt, host.txt에 한 줄씩 기록하세요.')
            identity(['kernel', 'release', 'machine', 'host'])
        elif practice == 1:
            plan['backup'] = True
            descriptions.append('all.txt에는 이전 장비의 보고가 있습니다. "previous report.txt"로 보존한 뒤 현재 환경의 전체 uname 정보를 all.txt에 갱신하세요. 배포판 원문은 os_release.txt에 별도로 보관하세요.')
            actions.append('cp all.txt "previous report.txt"'); identity(['all', 'os_release'])
        else:
            descriptions.append('"received notes.txt"는 커널과 배포판 버전을 혼동한 인계입니다. 원문을 보존하고, 현재 커널 릴리스를 release.txt에, 배포판 VERSION_ID= 줄을 distro.txt에 기록하세요. 현재 호스트 이름도 host.txt에 기록하세요.')
            identity(['release', 'distro', 'host'])
    elif kind == 'system_links':
        if practice == 0:
            descriptions.append('현재 인터페이스 전체를 관리 UP 여부를 알 수 있는 목록으로 links.txt에 저장하세요. 내려간 인터페이스도 포함하세요. 상태는 바꾸지 마세요.')
            link('links.txt', [])
        elif practice == 1:
            descriptions.append('옛 운영 문서와 대조할 수 있게 현재 인터페이스 전체의 ifconfig 형식 상세 목록을 legacy.txt에 저장하세요. 내려간 인터페이스도 빠지면 안 됩니다. 같은 환경의 ip 링크 목록도 links.txt에 저장하세요.')
            link('legacy.txt', [], True); link('links.txt', [])
        else:
            descriptions.append(f'{spare}만의 링크 보고서를 spare-link.txt에 저장하세요. 관리 상태는 UP이면 UP, 아니면 DOWN 한 줄을 state.txt에 적으세요. 연결을 활성화하라는 요청이 아닙니다. 호스트 이름도 host.txt에 남기세요.')
            link('spare-link.txt', [spare]); actions.append('printf "DOWN\\n" > state.txt'); identity(['host'])
    elif kind == 'system_addresses':
        descriptions.append(f'{active}의 IPv4 주소와 접두 길이가 드러나는 인터페이스별 보고서를 ipv4.txt에 저장하세요. 주소를 변경하지 마세요.')
        address('ipv4.txt', active, ['inet'])
        if practice == 1:
            descriptions.append(f'IPv4 보고서에 IPv6를 섞지 말고, {active}의 IPv6 주소·접두 길이만 별도 ipv6.txt에 저장하세요.')
            address('ipv6.txt', active, ['inet6'])
        elif practice == 2:
            descriptions = [f'{active}와 {spare}를 각각 조사해 IPv4·IPv6 주소와 접두 길이를 active-addresses.txt, spare-addresses.txt에 분리하세요. 내려간 인터페이스의 설정 주소도 조사 대상입니다. "received notes.txt" 원문을 reports/"received notes.txt"로도 복사해 인계하세요.']
            plan['addresses'] = {}; actions = []; plan['incident_copy'] = True
            address('active-addresses.txt', active, ['inet', 'inet6']); address('spare-addresses.txt', spare, ['inet', 'inet6'])
            actions.append('cp "received notes.txt" reports/')
    elif kind == 'system_time':
        if practice == 0:
            descriptions.append('조사 시점의 epoch 초 수를 epoch.txt에 저장하세요. 그 파일에 저장된 같은 순간을 UTC의 YYYY-MM-DDTHH:MM:SSZ 형식으로 utc.txt에 표현하세요. 시계를 변경하지 마세요.')
            time_report('now')
        elif practice == 1:
            descriptions.append('"event time.txt"에는 시간대가 붙은 예정 시각이 있습니다. 그 순간의 epoch 초 수를 event-epoch.txt, UTC의 YYYY-MM-DDTHH:MM:SSZ 표현을 event-utc.txt에 기록하세요. 현재 시계를 그 예정 시각으로 맞추는 작업이 아닙니다.')
            time_report('event')
        else:
            descriptions.append('"source notes.txt"의 마지막 수정 시각을 epoch 초 수로 modified-epoch.txt, UTC의 YYYY-MM-DDTHH:MM:SSZ 형식으로 modified-utc.txt에 기록하세요. 지금 조사한 현재 epoch는 epoch.txt에 별도로 저장하세요. 파일 수정 시각을 현재 시각이나 생성 시각과 혼동하지 마세요.')
            time_report('mtime')
    elif kind == 'system_clock':
        descriptions.append('현재 Timezone, LocalRTC, NTP, NTPSynchronized 네 속성을 이름=값으로 clock-state.txt에 기록하세요. 속성 순서는 자유입니다. 활성 서비스와 실제 동기화 여부를 구별하고 설정은 유지하세요.')
        if practice:
            descriptions.append('이 전용 guest의 RTC 조회를 시도하고 표준 출력·오류를 함께 rtc.txt에, 실제 종료 상태 숫자를 rtc-exit.txt에 저장하세요. 조회 실패도 그대로 보고해야 하며 성공으로 꾸미면 안 됩니다.')
        if practice == 2:
            descriptions.append('조사 결론 conclusion.txt에 RTC 조회 성공이면 rtc=available, 실패면 rtc=unavailable을 첫 줄에, 실제 동기화 속성을 synchronized=값으로 둘째 줄에 쓰세요. 호스트 이름도 host.txt에 인계하세요.')
        clocks(bool(practice), practice == 2)
        if practice == 2: identity(['host'])
    else:
        descriptions.append(f'환경 인계: 커널 릴리스·호스트 이름은 release.txt·host.txt에, 내려간 항목도 포함한 링크 전체는 links.txt에 기록하세요. {active}의 IPv4 주소/접두 길이는 ipv4.txt에, 조사 순간의 epoch는 epoch.txt에, 같은 순간의 UTC(YYYY-MM-DDTHH:MM:SSZ)는 utc.txt에 기록하세요. 네 시계 속성(Timezone/LocalRTC/NTP/NTPSynchronized)은 clock-state.txt에 이름=값으로 기록하고 RTC 조회 출력·오류는 rtc.txt, 종료 상태는 rtc-exit.txt에 보관하세요. 조회 실패를 성공으로 바꾸지 마세요.')
        identity(['release', 'host']); link('links.txt', []); address('ipv4.txt', active, ['inet']); time_report('now'); clocks(True)
    prompt = '\n'.join(descriptions) + '\n지정된 변경 대상 외의 준비된 원본 파일은 내용·권한·수정 시각을 보존하세요. 호스트 이름·네트워크·시계 설정도 유지하세요. 여기서 호스트는 전용 실습 guest이며 개인 PC 설정을 바꾸지 않습니다.'
    return Mission(kind, seed, start, start, start + '/reports', start + '/reports', '', '', prompt,
                   '\n'.join(actions), practice=practice, review=plan)


def steps(unit, m):
    from learning_steps import LearningStep as S
    key = unit.key; a, b = m.review['interfaces']; parts = unit.explanation.split('\n')
    if key == 'system_identity':
        return (S('커널 정보 세 항목', parts[0], 'uname -s\nuname -r\nuname -m', '각 숫자·이름이 가리키는 대상을 구별합니다.'),
                S('이름과 통신은 별개', parts[2], 'hostname', '현재 이름만 조회하며 DNS 등록을 주장하지 않습니다.'),
                S('배포판과 전체 정보', parts[1], 'uname -a\ncat /etc/os-release', 'VERSION_ID와 커널 릴리스가 다른 칸입니다.'),
                S('조사 결과 인계', '보고서 파일을 항목별로 나누어 저장합니다.', m.solution, '원 시스템 정보 파일은 변경하지 않습니다.'))
    if key == 'system_links':
        return (S('상세와 요약', parts[0], 'ip link show\nip -brief link show', '관리 UP와 동작 상태를 구별합니다.'),
                S('상대 연결과 관리 상태', parts[1], f'ip link show dev {a}\nip link show dev {b}', '한쪽 관리 UP가 상대 연결 성공을 보장하는지 봅니다.'),
                S('내려간 항목도 보기', parts[2], 'ifconfig\nifconfig -a', '두 목록의 차이를 확인합니다.'),
                S('전체 상태 인계', '이번에는 조회만 수행합니다.', m.solution, '인터페이스를 올리거나 삭제하지 않습니다.'))
    if key == 'system_addresses':
        return (S('대상 하나 고르기', parts[0], f'ip address show dev {a}', 'inet과 inet6, / 뒤 접두 길이를 읽습니다.'),
                S('주소 종류 분리', parts[2], f'ip -4 -brief address show dev {a}\nip -6 address show dev {a}', '옵션 -4/-6는 인터페이스 개수가 아닙니다.'),
                S('내려간 장치의 주소', parts[1], f'ip address show dev {b}', '주소 존재를 통신 성공으로 확대하지 않습니다.'),
                S('요청 범위 저장', '대상과 주소 종류를 각각 확인합니다.', m.solution, '다른 인터페이스의 주소가 섞이지 않게 합니다.'))
    if key == 'system_time':
        return (S('현재 초와 UTC', parts[0], 'date\ndate +%s\ndate -u', '조회 사이 흐르는 시간과 표시 시간대 차이를 구별합니다.'),
                S('같은 순간 변환', parts[1] + '\n$(cat 파일)은 저장한 내용을 가져오며 따옴표로 한 인자를 유지합니다.',
                  'date +%s > scratch-epoch.txt\ndate -u -d "@$(cat scratch-epoch.txt)" +%FT%TZ', '시계를 변경하지 않고 이미 저장한 순간을 표현합니다.'),
                S('파일 수정 시각', parts[2], 'date -u -r "source notes.txt" +%FT%TZ', '수정 시각을 읽어도 파일 내용/mtime은 바뀌지 않습니다.'),
                S('목표 시각 인계', '현재·예정·수정 시각 중 무엇을 요청했는지 구분합니다.', m.solution, '원본과 시계 설정을 그대로 둡니다.'))
    return (S('현재 상태 읽기', parts[0], 'timedatectl status', '서비스 활성과 동기화 결과를 각각 봅니다.'),
            S('필요 속성만 저장', parts[1], 'timedatectl show -p Timezone -p LocalRTC -p NTP -p NTPSynchronized', '네 속성의 의미를 구분합니다.'),
            S('RTC 조회와 오류 근거', parts[2] + '\n' + parts[3],
              'sudo hwclock --show > scratch-rtc.txt 2>&1\nprintf "%s\\n" "$?"\ncat scratch-rtc.txt', '이 환경의 실제 실패/성공을 그대로 읽습니다.'),
            S('관찰한 범위만 보고', '동기화 활성화나 시간대 변경은 이번 목표가 아닙니다.', m.solution, '지원되지 않는 기능을 성공으로 기록하지 않습니다.'))
