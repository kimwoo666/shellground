"""Goal-based curriculum. Solutions teach; grading never compares command strings."""
from dataclasses import dataclass, asdict, field
import random
import shlex
from path_practice import starting_location, natural_paths
from option_guides import OPTION_GUIDES


@dataclass(frozen=True)
class Unit:
    key: str
    level: int
    title: str
    commands: str
    explanation: str
    hint: str


_BASE_UNITS = (
    Unit("navigate", 1, "현재 위치와 경로 이동", "pwd · cd", "이번에는 위치 확인과 이동만 배웁니다.\n\npwd: 현재 폴더의 경로를 표시합니다.\ncd 경로: 지정한 폴더로 이동합니다.\n\n/로 시작하면 절대경로, 그렇지 않으면 현재 위치 기준의 상대경로입니다.\n.: 현재 폴더 · ..: 부모 폴더 · docs: 현재 폴더 안의 docs.\ncd로 이동하면 상대경로의 기준도 바뀝니다.\n\n순서: pwd → cd 목표경로 → pwd. 세부 옵션은 뒤의 별도 단원에서 배웁니다.", "pwd로 위치를 확인하고 cd로 목표 폴더에 이동하세요."),
    Unit("workspace", 2, "작업 폴더와 빈 파일", "mkdir -p · touch", "mkdir는 폴더를 만듭니다. -p는 중간 폴더까지 만듭니다. touch는 없는 파일을 빈 파일로 만듭니다. 공백이 있는 경로는 따옴표로 묶어 한 인자로 전달합니다.", "mkdir -p로 중간 폴더를 만든 뒤 그 안에 touch로 파일을 만드세요."),
    Unit("copy", 2, "파일 복사와 이름 변경", "cp · mv · rm", "cp 원본 대상은 복사, mv 원본 대상은 이동·이름 변경입니다. rm은 파일을 지웁니다. 실제 Linux에서는 휴지통으로 가지 않으므로 대상 경로를 확인해야 합니다.", "원본은 cp로 보존하고, 임시 파일은 mv로 이름을 바꾼 뒤 불필요한 파일만 rm 하세요."),
    Unit("list", 2, "ls 설명과 실습 — 숨김 목록", "ls · ls -a", "이번에는 ls와 -a만 배웁니다.\n\nls 경로: 그 폴더의 항목을 표시합니다.\nls -a 경로: .으로 시작하는 숨김 항목과 .·..도 표시합니다.\n\n저장 도구: 명령 > 파일은 출력을 파일에 저장(덮어쓰기), cat 파일은 저장한 내용을 확인합니다.", "ls -a 대상폴더 > 보고서경로 형태로 저장하세요. 저장 폴더는 이미 준비되어 있습니다."),
    Unit("long", 2, "ls 설명과 실습 — 상세 목록", "ls -l · ls -al", "이번에 새로 배울 옵션은 -l 하나입니다.\n\nls -l 경로: 권한·소유자·크기·시간을 자세히 표시합니다.\nls -al 경로: 앞에서 배운 -a와 조합해 숨김 항목까지 자세히 표시합니다.\n\nls -l과 ls -al을 비교한 뒤 상세 보고서 하나를 만듭니다.", "앞에서 배운 -a와 이번에 배운 -l을 합쳐 ls -al로 저장하세요."),
    Unit("recursive", 2, "하위 폴더까지 전체 목록", "ls -alR", "-R은 하위 디렉터리까지 재귀적으로 조회합니다. -r(역순)과 다릅니다. -a, -l, -R을 합치면 숨김 항목·상세 정보·하위 구조를 한 번에 기록합니다. 출력 파일은 조회 대상 바깥에 두는 것이 좋습니다.", "대문자 R을 사용하세요. ls -alR 대상폴더 > 보고서경로"),
    Unit("grep", 3, "로그를 걸러 보고서 만들기", "grep -i · | · wc -l", "grep 패턴 파일은 일치하는 줄을 출력합니다. -i는 대소문자를 무시합니다. |는 앞 명령의 출력을 다음 명령의 입력으로 보냅니다. wc -l은 줄 수입니다. head -n 5와 tail -n 5는 앞·뒤 5줄을 확인합니다.", "grep -i로 ERROR 줄을 보고서에 저장하고, 같은 결과를 wc -l에 연결해 개수 파일도 만드세요."),
    Unit("find", 3, "깊은 경로에서 확장자 검색", "find -type f -name", "find 경로 -type f -name '*.deb'는 하위 구조에서 일반 .deb 파일을 찾습니다. 패턴을 따옴표로 감싸야 현재 셸이 먼저 *를 확장하지 않습니다. find는 숨김 폴더도 탐색합니다.", "시작 경로·일반 파일 조건·확장자 조건을 지정하고 검색 결과를 저장하세요."),
    Unit("curl", 4, "URL에서 지정한 이름으로 저장", "curl -fL -o", "curl -o 경로 URL은 다운로드 위치와 이름을 지정합니다. -f는 HTTP 오류를 실패로 처리하고 -L은 리다이렉트를 따릅니다. -O는 URL의 원래 파일명으로 현재 폴더에 저장합니다. 이 실습의 URL은 프로그램 내부의 가상 다운로드 자료입니다. 실제 네트워크 요청은 하지 않습니다.", "curl -fL -o 저장경로 URL. URL과 파일 경로를 구분하세요."),
    Unit("wget", 4, "다른 다운로드 도구와 옵션", "wget -O · -P", "wget -O 파일 URL은 출력 파일명을 지정하고 -P 폴더 URL은 저장 디렉터리를 지정합니다. curl의 -o와 wget의 -O는 대소문자가 다릅니다. .deb, .sh, .zip, .tar.gz 모두 바이트를 받는 파일이며 형식에 따라 후속 처리가 달라집니다.", "wget -O 저장경로 URL로 받으세요. 확장자를 바꾸기만 해서는 다른 형식으로 변환되지 않습니다."),
    Unit("archive", 4, "다운로드한 압축 파일 풀기", "tar -tzf · -xzf · -C · unzip", "tar -tzf 파일은 .tar.gz 내용 조회, tar -xzf 파일 -C 폴더는 지정 폴더로 압축 해제입니다. .zip은 unzip -l 파일로 조회하고 unzip 파일 -d 폴더로 풉니다. 내려받기·내용 확인·압축 풀기를 조합합니다.", "URL 확장자에 따라 tar 또는 unzip을 선택하고 목표 폴더에 README.txt가 놓이게 하세요."),
    Unit("script", 4, "스크립트 권한과 실행", "chmod u+x · ./파일.sh", ".sh는 셸 스크립트입니다. 내용을 cat으로 확인하고 chmod u+x로 소유자 실행 권한을 추가합니다. ./파일.sh는 현재 폴더의 프로그램을 실행합니다. 다운로드한 코드를 확인하지 않고 실행하는 습관은 피하세요. 여기서는 준비된 안전한 실습 스크립트만 사용합니다.", "스크립트를 받은 뒤 내용을 확인하고 실행 권한을 추가하세요. 스크립트 인자로 결과 파일 경로를 넘기세요."),
    Unit("deb", 4, "Debian 패키지 내용 확인", "dpkg-deb --info · --extract", ".deb는 Debian 계열 패키지입니다. dpkg-deb --info로 메타데이터를 보고 --extract 파일 폴더로 내용을 풀 수 있습니다. 이 실습은 설치나 관리자 권한을 요구하지 않습니다. 실행 파일·스크립트·압축 파일·패키지는 서로 다른 형식입니다.", "패키지를 받고 --info로 확인한 뒤 --extract로 지정 폴더에 풀어 보세요."),
)


_BY_KEY = {unit.key: unit for unit in _BASE_UNITS}
_BY_KEY.update({
    'mkdir': Unit('mkdir', 1, '폴더 만들기', 'mkdir',
        'mkdir 경로: 새 폴더를 만듭니다.\n\n이번에는 준비된 부모 폴더 안에 practice 폴더 하나만 만듭니다.\n중간 폴더까지 만드는 옵션은 나중에 배웁니다.', 'mkdir 목표경로로 practice 폴더 하나를 만드세요.'),
    'touch': Unit('touch', 1, '빈 파일 만들기', 'touch',
        'touch 경로: 파일이 없으면 빈 파일을 만듭니다.\n\n폴더는 mkdir, 빈 파일은 touch로 만듭니다.\n이미 있는 파일의 내용은 지우지 않습니다.', 'touch 목표파일경로로 notes.txt를 만드세요.'),
    'read': Unit('read', 1, '파일 내용 읽기', 'cat',
        'cat 파일경로: 파일 내용을 터미널에 표시합니다.\n\nls는 파일 이름을, cat은 파일 내용을 봅니다.\n이번에는 내용을 읽기만 합니다. 수정과 저장은 다음 단원에서 배웁니다.', 'cat 목표파일경로로 내용을 화면에 출력하세요.'),
    'edit': Unit('edit', 1, '파일 열고 수정·저장하기', 'nano',
        'nano 파일경로: 터미널 편집기로 파일을 엽니다.\n\nCtrl+K: 현재 줄 지우기 → 새 내용 입력\nCtrl+O → Enter: 파일 저장\nCtrl+X: 편집기 종료\n\n저장 후 cat으로 내용을 확인하세요. 저장하지 않고 종료하면 수정되지 않습니다.',
        'nano로 note.txt를 열고 첫 줄을 지운 뒤 status=ready를 입력하세요. Ctrl+O, Enter로 저장하고 Ctrl+X로 종료하세요.'),
    'duplicate': Unit('duplicate', 1, '파일 하나 복사하기', 'cp',
        'cp 원본 대상: 원본을 남겨 두고 복사본을 만듭니다.\n\n원본 경로를 먼저, 새 파일 경로를 나중에 씁니다.\n이번에는 파일 하나만 복사합니다.', 'cp 원본경로 대상경로 순서로 manual.txt를 만드세요.'),
    'rename': Unit('rename', 1, '파일 이름 바꾸기', 'mv',
        'mv 기존경로 새경로: 파일을 이동하거나 이름을 바꿉니다.\n\n같은 폴더에서 이름만 바꾸면 이름 변경입니다.\ncp와 달리 기존 이름은 남지 않습니다.', 'mv draft.txt의경로 final.txt의경로 순서로 실행하세요.'),
    'remove': Unit('remove', 1, '필요 없는 파일 삭제하기', 'rm',
        'rm 파일경로: 지정한 파일을 삭제합니다. 휴지통으로 보내지 않습니다.\n\n먼저 ls로 대상을 확인하고 obsolete.txt 하나만 삭제하세요.\n재귀·강제 삭제 옵션은 지금 사용하지 않습니다.', 'rm으로 obsolete.txt 하나만 삭제하세요. 다른 파일은 보존하세요.'),
    'permissions': Unit('permissions', 3, '실행 권한 이해하기', 'chmod u+x',
        'ls -l의 첫 열은 권한입니다. x는 실행 권한입니다.\n\nchmod u+x 파일: 소유자에게 실행 권한을 추가합니다.\ncat으로 스크립트 내용을 먼저 읽고 권한을 바꾸세요.\n이번에는 다운로드하거나 실행하지 않습니다.', 'cat으로 내용을 읽고 chmod u+x로 local.sh의 소유자 실행 권한을 추가하세요.'),
})
_BY_KEY['pwdpaths'] = Unit('pwdpaths', 2, 'pwd 옵션 설명과 실습', 'pwd -L · pwd -P',
    '이번에는 pwd의 두 옵션만 비교합니다.\n\n-L: 들어온 바로가기 이름을 유지한 경로.\n-P: 바로가기가 가리키는 실제 경로.\n\n준비된 shortcut으로 들어가 두 출력을 비교하세요.',
    'cd로 shortcut에 들어간 뒤 pwd -L과 pwd -P를 각각 실행해 두 경로를 화면에 출력하세요.')
_BY_KEY['lsintro'] = Unit('lsintro', 1, 'ls 설명과 화면 실습', 'ls · ls -a',
    '이번에는 파일 목록을 화면으로만 확인합니다.\n\nls 경로: 그 폴더의 목록을 표시합니다.\nls -a 경로: 숨김 항목과 .·..까지 포함합니다.\n\n두 출력을 비교하세요.',
    'ls -a 목표경로로 숨김 항목까지 화면에 출력하세요.')
_BY_KEY['report'] = Unit('report', 1, '출력 저장과 내용 확인', '> · cat',
    '이번에 새로 배울 것은 출력 저장입니다. cat은 앞에서 배운 내용을 복습합니다.\n\n명령 > 파일: 화면 대신 파일에 출력 저장. 기존 내용은 덮어씁니다.\ncat 파일: 저장된 내용을 화면에 표시합니다.\n\n이미 배운 pwd의 출력을 저장하고 cat으로 확인합니다.',
    'pwd > 보고서경로로 현재 위치를 저장하고 cat 보고서경로로 내용을 확인하세요.')
_BY_KEY['mixed'] = Unit('mixed', 2, '혼합 실습 — 위치와 파일 목록', 'cd · ls -al · >',
    '새 옵션은 없습니다. 앞에서 배운 것만 함께 사용합니다.\n\n① cd로 목표 폴더 이동\n② ls -al로 숨김 포함 상세 목록 저장\n\n목표 폴더에 있는 상태와 보고서 내용을 함께 채점합니다.\n현재 위치가 궁금하면 이미 배운 pwd로 확인할 수 있지만, 이번 문제의 필수 작업은 아닙니다.',
    'cd 목표폴더로 이동한 뒤 ls -al > 보고서경로로 저장하세요. 목표 폴더에 머무세요.')
_BY_KEY['lsoptions'] = Unit('lsoptions', 2, 'ls 옵션 비교와 조합', 'ls -A · -alh · -S · -1',
    '옵션은 외워서 붙이는 장식이 아니라 출력 조건입니다. -a와 -A의 차이, -l과 -h의 조합, -S 정렬을 비교하고 서로 다른 세 보고서를 만듭니다.',
    '이름 목록은 ls -1A, 숨김 포함 읽기 쉬운 상세 목록은 ls -alh, 숨김 제외 큰 크기순 이름 목록은 ls -1S입니다.')
# Teach ls before file modification. Stable keys preserve previously earned progress.
UNITS = tuple(_BY_KEY[key] for key in (
    'navigate', 'lsintro', 'mkdir', 'touch', 'read', 'edit', 'duplicate', 'rename', 'remove',
    'report', 'workspace', 'copy', 'list', 'long', 'mixed', 'pwdpaths', 'lsoptions',
    'recursive', 'grep', 'find', 'permissions', 'curl', 'wget', 'archive', 'script', 'deb'))
from sim_lessons import units as simulation_units
UNITS += simulation_units(Unit)


def lesson_text(unit, mode='simulation'):
    if unit.key.startswith(('linux_', 'apt_', 'auth_', 'shell_', 'process_', 'io_', 'system_')):
        return unit.explanation + '\n\n직접 해볼 예시:\n' + make_mission(unit.key, 4242).solution
    if unit.key.startswith(('sim_', 'ros_', 'admin_', 'docker_')):
        example = make_mission(unit.key, 4242).solution
        if mode == 'real':
            from real_lessons import real_text
            from docker_guides import REGISTRY_GUIDE
            # The registry comparison intentionally includes the short public
            # name. Convert executable examples, not that explanatory contrast.
            explanation = real_text(unit.explanation.replace(REGISTRY_GUIDE, '').rstrip())
            if unit.key == 'sim_images': explanation += '\n\n' + REGISTRY_GUIDE
            return explanation + '\n\n직접 해볼 예시:\n' + real_text(example)
        return unit.explanation + '\n\n직접 해볼 예시:\n' + example
    if mode == 'real':
        from real_lessons import real_text
        return real_text(unit.explanation + '\n\n옵션별 의미와 비교 예시\n' + OPTION_GUIDES[unit.key])
    return unit.explanation + '\n\n옵션별 의미와 비교 예시\n' + OPTION_GUIDES[unit.key] + '\n\n참고: 설명에는 아직 시뮬레이터에 구현되지 않은 심화 옵션도 포함됩니다. 지원하지 않는 옵션은 오류로 표시하며, 성공한 것처럼 처리하지 않습니다.'


@dataclass(frozen=True)
class Mission:
    kind: str
    seed: int
    start: str
    source: str
    report: str
    target: str
    url: str
    artifact: str
    prompt: str
    solution: str
    interaction: str = ''
    practice: int = 0
    review: dict = field(default_factory=dict)

    def payload(self):
        return asdict(self)


def make_mission(kind, seed=None, practice=0):
    if kind.startswith('system_'):
        from system_course import make_mission as make_system_mission
        return make_system_mission(kind, seed, practice)
    if kind.startswith('io_'):
        from io_course import make_mission as make_io_mission
        return make_io_mission(kind, seed, practice)
    if kind.startswith('process_'):
        from process_course import make_mission as make_process_mission
        return make_process_mission(kind, seed, practice)
    if kind.startswith('shell_'):
        from shell_course import make_mission as make_shell_mission
        return make_shell_mission(kind, seed, practice)
    if kind.startswith('auth_'):
        from auth_course import make_mission as make_auth_mission
        return make_auth_mission(kind, seed, practice)
    if kind.startswith('apt_'):
        from apt_course import make_mission as make_apt_mission
        return make_apt_mission(kind, seed, practice)
    if kind.startswith('linux_'):
        from linux_course import make_linux_mission
        return make_linux_mission(kind, seed, practice)
    if kind.startswith('docker_runtime_'):
        from docker_runtime_course import make_mission as make_runtime_mission
        return make_runtime_mission(kind, seed, practice)
    if kind.startswith('docker_sessions_'):
        from docker_sessions_course import make_mission as make_session_mission
        return make_session_mission(kind, seed, practice)
    if kind.startswith('docker_'):
        from docker_lessons import make_docker_mission
        return make_docker_mission(kind, seed, practice)
    if kind.startswith('admin_'):
        from linux_course import NEW_KEYS
        if kind in NEW_KEYS:
            from admin_focus import make_focused_admin
            return make_focused_admin(kind, seed, practice)
        from admin_lessons import make_admin_mission
        return make_admin_mission(kind, seed, practice)
    if kind.startswith('ros_controls_'):
        from ros_controls_course import make_mission as make_control_mission
        return make_control_mission(kind, seed, practice)
    if kind.startswith('ros_'):
        from ros_lessons import make_ros_mission
        return make_ros_mission(kind, seed, practice)
    if kind.startswith('sim_'):
        from sim_lessons import make_extension
        return make_extension(kind, seed, practice)
    seed = seed if seed is not None else random.SystemRandom().randrange(1000, 9999)
    rng = random.Random(seed)
    base = "/home/learner"
    start = f"{base}/{rng.choice(['desk', 'office/sessions', 'workspace'])}/team{seed % 7 + 1}"
    source = f"{base}/{rng.choice(['data', 'projects/releases', 'archive/staging'])}/release{seed}"
    report = f"{base}/reports/{rng.choice(['audit', 'inventory', 'handover'])}-{seed}.txt"
    target = f"{base}/{rng.choice(['delivery', 'work/output', 'handovers'])}/result{seed}"
    start = starting_location(kind, seed, start, source, target, report)
    artifact = rng.choice(["toolkit.deb", "setup.sh", "bundle.tar.gz", "bundle.zip"])
    if kind == "archive": artifact = rng.choice(["bundle.tar.gz", "bundle.zip"])
    if kind == "script": artifact = "setup.sh"
    if kind == "deb": artifact = "toolkit.deb"
    url = f"http://127.0.0.1:8765/{artifact}"
    q = shlex.quote
    downloaded = target + "/received-" + artifact
    prompts = {
        'mkdir': (f'{target}/practice 폴더를 만드세요. 부모 폴더 {target}은 이미 있습니다.', f'mkdir {target}/practice'),
        'touch': (f'{target}/notes.txt라는 빈 파일을 만드세요. 파일이 들어갈 폴더는 이미 있습니다.', f'touch {target}/notes.txt'),
        'read': (f'{source}/guide.txt 파일 내용을 화면에 출력하세요. 파일을 수정하지 마세요.', f'cat {source}/guide.txt'),
        'edit': (f'{target}/note.txt를 열어 status=draft를 status=ready로 수정하고 저장한 뒤 편집기를 종료하세요.', f'nano {target}/note.txt'),
        'duplicate': (f'{source}/guide.txt를 {target}/manual.txt로 복사하세요. 원본도 남겨 두세요.', f'cp {source}/guide.txt {target}/manual.txt'),
        'rename': (f'{target}/draft.txt를 같은 폴더의 final.txt로 이름을 바꾸세요. 내용은 그대로 유지하세요.', f'mv {target}/draft.txt {target}/final.txt'),
        'remove': (f'{target}/obsolete.txt만 삭제하세요. 같은 폴더의 draft.txt는 남겨 두세요.', f'ls {target}\nrm {target}/obsolete.txt'),
        'permissions': (f'{target}/local.sh의 내용을 읽고 소유자 실행 권한을 추가하세요. 파일 내용은 바꾸지 마세요.', f'cat {target}/local.sh\nchmod u+x {target}/local.sh\nls -l {target}/local.sh'),
        "navigate": (f"pwd로 위치를 확인하고 {source}/docs 폴더로 이동하세요. 작업을 마친 위치는 이 폴더여야 합니다.", f"pwd\ncd {source}\ncd docs\npwd"),
        "mixed": (f"{source} 폴더로 이동하세요. 그 폴더의 바로 아래 목록을 숨김 항목(.과 .. 포함)과 상세 정보까지 {report}에 저장하세요. 목표 폴더에 머무세요.", f"cd {source}\nls -al > {report}"),
        "pwdpaths": (f"{start}/shortcut은 {source}/docs를 가리키는 바로가기입니다. 이 바로가기로 들어가 논리 경로와 실제 경로를 화면에 각각 출력하세요.", f"cd {start}/shortcut\npwd -L\npwd -P"),
        "lsintro": (f"{source}의 바로 아래 목록을 숨김 항목과 .·..까지 포함해 화면에 출력하고 기본 목록과 비교하세요.", f"ls {source}\nls -a {source}"),
        "report": (f"시작 위치 {start}에서 pwd의 출력을 {report}에 저장하세요. cat으로 파일 내용을 확인하세요. 저장 폴더는 준비되어 있습니다.", f"pwd > {report}\ncat {report}"),
        "lsoptions": (f"{source}를 조회해 세 보고서를 만드세요. ① {report}.names: 숨김 항목 포함, .과 .. 제외, 이름 한 줄씩. ② {report}.sizes: .과 .. 포함 전체 상세 목록, 크기는 1024 단위 K/M 등 읽기 쉬운 형식. ③ {report}.largest: 숨김 제외 바로 아래 항목을 큰 크기순으로, 이름만 한 줄씩. 하위 폴더 안까지 펼치지 마세요.", f"ls -1A {source} > {report}.names\nls -alh {source} > {report}.sizes\nls -1S {source} > {report}.largest\ncat {report}.names {report}.sizes {report}.largest"),
        "workspace": (f"{target}/daily notes 폴더를 만들고 그 안에 빈 done.txt 파일을 만드세요.", f"mkdir -p {q(target + '/daily notes')}\ntouch {q(target + '/daily notes/done.txt')}"),
        "copy": (f"{source}/guide.txt 원본을 보존하며 {target}/manual.txt로 복사하세요.\n{target}/draft.txt를 같은 폴더의 {target}/final.txt로 이름을 바꾸세요.\n{target}/obsolete.txt만 삭제하세요.", f"cp {source}/guide.txt {target}/manual.txt\nmv {target}/draft.txt {target}/final.txt\nrm {target}/obsolete.txt"),
        "list": (f"{source}의 바로 아래 목록을 .과 .. 및 숨김 파일까지 모두 포함해 {report}에 한 줄에 하나씩 저장하세요. 하위 폴더 안까지 나열하지는 마세요.", f"ls {source}\nls -a {source} > {report}\ncat {report}"),
        "long": (f"{source}의 바로 아래 목록을 숨김 항목(.과 .. 포함), 권한·소유자·크기·시간을 포함한 상세 형식으로 {report}에 저장하세요.", f"ls -l {source}\nls -al {source} > {report}\ncat {report}"),
        "recursive": (f"{source}의 파일 목록을 모든 하위 폴더까지 재귀적으로 조사하세요. 숨김 항목(.과 .. 포함)과 권한·소유자·크기·시간이 있는 상세 목록을 {report}에 저장하세요. 현재 위치는 대상 폴더가 아닙니다.", f"ls -alR {source} > {report}\ncat {report}"),
        "grep": (f"{source}/app.log에서 대소문자와 관계없이 error가 있는 줄을 원래 순서 그대로 {report}에 저장하세요. 일치하는 줄 수만 {report}.count에 별도로 저장하세요.", f"grep -i error {source}/app.log > {report}\ngrep -i error {source}/app.log | wc -l > {report}.count"),
        "find": (f"{source} 아래에서 숨김 폴더도 포함해 모든 .deb 일반 파일의 절대 경로를 찾아 {report}에 한 줄씩 저장하세요. 이름이 .deb로 끝나는 디렉터리는 제외하세요.", f"find {source} -type f -name '*.deb' > {report}"),
        "curl": (f"{url} 파일을 {downloaded} 이름으로 내려받으세요. 지정한 위치와 이름으로 원본과 동일한 내용이 저장되어야 합니다.", f"curl -fL -o {downloaded} {url}"),
        "wget": (f"{url} 파일을 {downloaded} 이름으로 내려받으세요. 파일 형식과 내용을 유지하고 저장 위치를 확인하세요.", f"wget -O {downloaded} {url}"),
        "archive": (f"{url}을 {downloaded}에 내려받고 압축을 {target}/unpacked에 풀어 README.txt와 bin/hello.sh를 복원하세요.", f"curl -fL -o {downloaded} {url}\nmkdir -p {target}/unpacked\n" + (f"unzip {downloaded} -d {target}/unpacked" if artifact.endswith('.zip') else f"tar -xzf {downloaded} -C {target}/unpacked")),
        "script": (f"{url}을 {downloaded}에 내려받으세요. 내용을 확인하고 소유자 실행 권한을 추가하세요. 결과 파일 경로 {target}/receipt.txt를 인자로 전달해 실행하고 결과를 남기세요.", f"curl -fL -o {downloaded} {url}\ncat {downloaded}\nchmod u+x {downloaded}\n{downloaded} {target}/receipt.txt"),
        "deb": (f"{url}을 {downloaded}에 내려받으세요. 패키지 정보를 확인하고 설치하지 말고 {target}/unpacked에 내용을 풀어 usr/share/shellground/message.txt를 복원하세요.", f"curl -fL -o {downloaded} {url}\ndpkg-deb --info {downloaded}\ndpkg-deb --extract {downloaded} {target}/unpacked"),
    }
    prompt, solution = prompts[kind]
    interaction = '편집기 조작: Ctrl+K로 현재 줄 삭제 → 문제의 새 내용 입력 → Ctrl+O, Enter로 저장 → Ctrl+X로 종료.' if kind == 'edit' else ''
    mission = Mission(kind, seed, start, source, report, target, url, artifact, prompt, solution, interaction, practice)
    if practice == 2:
        from practice_variants import review_mission
        mission = review_mission(mission)
    return natural_paths(mission)


def random_mission(completed, previous=None, units=None):
    pool = [u.key for u in (UNITS if units is None else units) if u.key in completed]
    if not pool:
        raise ValueError("완료한 단계가 없습니다.")
    choices = [key for key in pool if key != previous] or pool
    return make_mission(random.SystemRandom().choice(choices), practice=random.SystemRandom().choice([1, 2]))
