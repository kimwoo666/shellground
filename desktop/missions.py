"""Goal-based curriculum. Solutions teach; grading never compares command strings."""
from dataclasses import dataclass, asdict
import random
import shlex


@dataclass(frozen=True)
class Unit:
    key: str
    level: int
    title: str
    commands: str
    explanation: str
    hint: str


UNITS = (
    Unit("navigate", 1, "현재 위치와 경로 이동", "pwd · ls · cd", "pwd는 현재 위치, ls는 목록을 보여 줍니다. cd 경로로 이동합니다. /로 시작하면 절대 경로, ..는 상위 폴더, ~는 홈입니다. Tab으로 경로를 완성하고 ↑로 이전 명령을 불러오세요.", "pwd와 ls로 둘러본 뒤 cd로 목표 폴더에 이동하세요."),
    Unit("workspace", 1, "작업 폴더와 빈 파일", "mkdir -p · touch", "mkdir는 폴더를 만듭니다. -p는 중간 폴더까지 만듭니다. touch는 없는 파일을 빈 파일로 만듭니다. 공백이 있는 경로는 따옴표로 묶어 한 인자로 전달합니다.", "mkdir -p로 중간 폴더를 만든 뒤 그 안에 touch로 파일을 만드세요."),
    Unit("copy", 1, "파일 복사와 이름 변경", "cp · mv · rm", "cp 원본 대상은 복사, mv 원본 대상은 이동·이름 변경입니다. rm은 파일을 지웁니다. 실제 Linux에서는 휴지통으로 가지 않으므로 대상 경로를 확인해야 합니다.", "원본은 cp로 보존하고, 임시 파일은 mv로 이름을 바꾼 뒤 불필요한 파일만 rm 하세요."),
    Unit("list", 2, "숨김 파일 목록을 보고서로", "ls -a · > · cat", "ls의 -a는 .으로 시작하는 숨김 항목도 표시합니다. > 파일은 화면 대신 파일로 표준 출력을 저장하며 기존 내용을 덮어씁니다. >>는 덧붙입니다. cat 파일로 내용을 확인합니다. 터미널 화면과 파일로 저장한 ls 출력의 열 배치는 다를 수 있습니다.", "ls -a 대상폴더 > 보고서경로 형태로 저장하세요. 저장 폴더는 이미 준비되어 있습니다."),
    Unit("long", 2, "권한과 크기까지 기록", "ls -al · -la · --all", "-l은 권한·링크 수·소유자·그룹·크기·시간을 표시하고 -a는 숨김 항목을 포함합니다. ls -al, ls -la, ls -l -a는 같은 옵션 조합입니다. 명령을 실행하는 현재 위치와 조회할 경로는 달라도 됩니다.", "숨김 포함 옵션과 자세히 표시 옵션을 함께 사용하고 결과를 파일에 저장하세요."),
    Unit("recursive", 2, "하위 폴더까지 전체 목록", "ls -alR", "-R은 하위 디렉터리까지 재귀적으로 조회합니다. -r(역순)과 다릅니다. -a, -l, -R을 합치면 숨김 항목·상세 정보·하위 구조를 한 번에 기록합니다. 출력 파일은 조회 대상 바깥에 두는 것이 좋습니다.", "대문자 R을 사용하세요. ls -alR 대상폴더 > 보고서경로"),
    Unit("grep", 3, "로그를 걸러 보고서 만들기", "grep -i · | · wc -l", "grep 패턴 파일은 일치하는 줄을 출력합니다. -i는 대소문자를 무시합니다. |는 앞 명령의 출력을 다음 명령의 입력으로 보냅니다. wc -l은 줄 수입니다. head -n 5와 tail -n 5는 앞·뒤 5줄을 확인합니다.", "grep -i로 ERROR 줄을 보고서에 저장하고, 같은 결과를 wc -l에 연결해 개수 파일도 만드세요."),
    Unit("find", 3, "깊은 경로에서 확장자 검색", "find -type f -name", "find 경로 -type f -name '*.deb'는 하위 구조에서 일반 .deb 파일을 찾습니다. 패턴을 따옴표로 감싸야 현재 셸이 먼저 *를 확장하지 않습니다. find는 숨김 폴더도 탐색합니다.", "시작 경로·일반 파일 조건·확장자 조건을 지정하고 검색 결과를 저장하세요."),
    Unit("curl", 4, "URL에서 지정한 이름으로 저장", "curl -fL -o", "curl -o 경로 URL은 다운로드 위치와 이름을 지정합니다. -f는 HTTP 오류를 실패로 처리하고 -L은 리다이렉트를 따릅니다. -O는 URL의 원래 파일명으로 현재 폴더에 저장합니다. 이 실습의 URL은 격리 환경 안의 로컬 HTTP 서버입니다.", "curl -fL -o 저장경로 URL. URL과 파일 경로를 구분하세요."),
    Unit("wget", 4, "다른 다운로드 도구와 옵션", "wget -O · -P", "wget -O 파일 URL은 출력 파일명을 지정하고 -P 폴더 URL은 저장 디렉터리를 지정합니다. curl의 -o와 wget의 -O는 대소문자가 다릅니다. .deb, .sh, .zip, .tar.gz 모두 바이트를 받는 파일이며 형식에 따라 후속 처리가 달라집니다.", "wget -O 저장경로 URL로 받으세요. 확장자를 바꾸기만 해서는 다른 형식으로 변환되지 않습니다."),
    Unit("archive", 4, "다운로드한 압축 파일 풀기", "tar -tzf · -xzf · -C · unzip", "tar -tzf 파일은 .tar.gz 내용 조회, tar -xzf 파일 -C 폴더는 지정 폴더로 압축 해제입니다. .zip은 unzip -l 파일로 조회하고 unzip 파일 -d 폴더로 풉니다. 내려받기·내용 확인·압축 풀기를 조합합니다.", "URL 확장자에 따라 tar 또는 unzip을 선택하고 목표 폴더에 README.txt가 놓이게 하세요."),
    Unit("script", 4, "스크립트 권한과 실행", "chmod u+x · ./파일.sh", ".sh는 셸 스크립트입니다. 내용을 cat으로 확인하고 chmod u+x로 소유자 실행 권한을 추가합니다. ./파일.sh는 현재 폴더의 프로그램을 실행합니다. 다운로드한 코드를 확인하지 않고 실행하는 습관은 피하세요. 여기서는 준비된 안전한 실습 스크립트만 사용합니다.", "스크립트를 받은 뒤 내용을 확인하고 실행 권한을 추가하세요. 스크립트 인자로 결과 파일 경로를 넘기세요."),
    Unit("deb", 4, "Debian 패키지 내용 확인", "dpkg-deb --info · --extract", ".deb는 Debian 계열 패키지입니다. dpkg-deb --info로 메타데이터를 보고 --extract 파일 폴더로 내용을 풀 수 있습니다. 이 실습은 설치나 관리자 권한을 요구하지 않습니다. 실행 파일·스크립트·압축 파일·패키지는 서로 다른 형식입니다.", "패키지를 받고 --info로 확인한 뒤 --extract로 지정 폴더에 풀어 보세요."),
)


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

    def payload(self):
        return asdict(self)


def make_mission(kind, seed=None):
    seed = seed if seed is not None else random.SystemRandom().randrange(1000, 9999)
    rng = random.Random(seed)
    base = "/home/learner"
    start = f"{base}/{rng.choice(['desk', 'office/sessions', 'workspace'])}/team{seed % 7 + 1}"
    source = f"{base}/{rng.choice(['data', 'projects/releases', 'archive/staging'])}/release{seed}"
    report = f"{base}/reports/{rng.choice(['audit', 'inventory', 'handover'])}-{seed}.txt"
    target = f"{base}/{rng.choice(['delivery', 'work/output', 'handovers'])}/result{seed}"
    artifact = rng.choice(["toolkit.deb", "setup.sh", "bundle.tar.gz", "bundle.zip"])
    if kind == "archive": artifact = rng.choice(["bundle.tar.gz", "bundle.zip"])
    if kind == "script": artifact = "setup.sh"
    if kind == "deb": artifact = "toolkit.deb"
    url = f"http://127.0.0.1:8765/{artifact}"
    q = shlex.quote
    downloaded = target + "/received-" + artifact
    prompts = {
        "navigate": (f"시작 위치는 {start}입니다. 주변을 확인한 뒤 {source}/docs 폴더로 이동한 상태로 채점하세요.", f"pwd\nls\ncd {source}/docs\npwd"),
        "workspace": (f"{target}/daily notes 폴더를 만들고 그 안에 빈 done.txt 파일을 만드세요.", f"mkdir -p {q(target + '/daily notes')}\ntouch {q(target + '/daily notes/done.txt')}"),
        "copy": (f"{source}/guide.txt 원본을 보존하며 {target}/manual.txt로 복사하세요. {target}/draft.txt는 final.txt로 이름을 바꾸고 {target}/obsolete.txt는 삭제하세요.", f"cp {source}/guide.txt {target}/manual.txt\nmv {target}/draft.txt {target}/final.txt\nrm {target}/obsolete.txt"),
        "list": (f"현재 위치를 바꿔도 좋습니다. {source}의 바로 아래 항목을 .과 .. 및 숨김 파일까지 모두 포함해 {report}에 한 줄에 하나씩 저장하세요. 하위 폴더 안까지 나열하지는 마세요.", f"ls -a {source} > {report}\ncat {report}"),
        "long": (f"{source}의 바로 아래 목록을 숨김 항목(.과 .. 포함), 권한·소유자·크기·시간을 포함한 상세 형식으로 {report}에 저장하세요.", f"ls -al {source} > {report}\ncat {report}"),
        "recursive": (f"{source}의 파일 목록을 모든 하위 폴더까지 재귀적으로 조사하세요. 숨김 항목(.과 .. 포함)과 권한·소유자·크기·시간이 있는 상세 목록을 {report}에 저장하세요. 현재 위치는 대상 폴더가 아닙니다.", f"ls -alR {source} > {report}\ncat {report}"),
        "grep": (f"{source}/app.log에서 대소문자와 관계없이 error가 있는 줄을 원래 순서 그대로 {report}에 저장하세요. 일치하는 줄 수만 {report}.count에 별도로 저장하세요.", f"grep -i error {source}/app.log > {report}\ngrep -i error {source}/app.log | wc -l > {report}.count"),
        "find": (f"{source} 아래에서 숨김 폴더도 포함해 모든 .deb 일반 파일의 절대 경로를 찾아 {report}에 한 줄씩 저장하세요. 이름이 .deb로 끝나는 디렉터리는 제외하세요.", f"find {source} -type f -name '*.deb' > {report}"),
        "curl": (f"{url} 파일을 {downloaded} 이름으로 내려받으세요. 현재 폴더가 아닌 지정 폴더에 원본과 동일한 내용으로 저장되어야 합니다.", f"curl -fL -o {downloaded} {url}"),
        "wget": (f"{url} 파일을 {downloaded} 이름으로 내려받으세요. 파일 형식과 내용을 유지하고 저장 위치를 확인하세요.", f"wget -O {downloaded} {url}"),
        "archive": (f"{url}을 {downloaded}에 내려받고 압축을 {target}/unpacked에 풀어 README.txt와 bin/hello.sh를 복원하세요.", f"curl -fL -o {downloaded} {url}\nmkdir -p {target}/unpacked\n" + (f"unzip {downloaded} -d {target}/unpacked" if artifact.endswith('.zip') else f"tar -xzf {downloaded} -C {target}/unpacked")),
        "script": (f"{url}을 {downloaded}에 내려받으세요. 내용을 확인하고 소유자 실행 권한을 추가하세요. 결과 파일 경로 {target}/receipt.txt를 인자로 전달해 실행하고 결과를 남기세요.", f"curl -fL -o {downloaded} {url}\ncat {downloaded}\nchmod u+x {downloaded}\n{downloaded} {target}/receipt.txt"),
        "deb": (f"{url}을 {downloaded}에 내려받으세요. 패키지 정보를 확인하고 설치하지 말고 {target}/unpacked에 내용을 풀어 usr/share/shellground/message.txt를 복원하세요.", f"curl -fL -o {downloaded} {url}\ndpkg-deb --info {downloaded}\ndpkg-deb --extract {downloaded} {target}/unpacked"),
    }
    prompt, solution = prompts[kind]
    return Mission(kind, seed, start, source, report, target, url, artifact, prompt, solution)


def random_mission(completed, previous=None):
    pool = [u.key for u in UNITS if u.key in completed]
    if not pool:
        raise ValueError("완료한 단계가 없습니다.")
    choices = [key for key in pool if key != previous] or pool
    return make_mission(random.SystemRandom().choice(choices))
