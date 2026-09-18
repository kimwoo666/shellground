"""Second practices change the task, not merely the randomized path names."""
from dataclasses import replace
from pathlib import PurePosixPath
import shlex


def review_mission(m):
    s, t, r = m.source, m.target, m.report
    q = shlex.quote
    setup, goals = [], []
    keep_base = False
    def file(path, text): return {'type': 'file', 'path': path, 'text': text}
    def directory(path): return {'type': 'dir', 'path': path}
    def absent(path): return {'type': 'absent', 'path': path}
    def copy(path, source): return {'type': 'copy', 'path': path, 'source': source}
    def cwd(path): return {'type': 'cwd', 'path': path}
    def output(text, count=1): return {'type': 'output', 'text': text, 'count': count}
    def listing(path, options): return {'type': 'listing', 'path': path, 'source': s, 'options': options}
    kind = m.kind
    title = '이전 기능 조합'
    if kind == 'navigate':
        title = '절대 경로에서 상대 경로로'
        prompt = '현재 폴더에서 바로 위 부모 폴더로 돌아가세요. 긴 절대 경로 대신 cd ..를 사용할 수 있습니다. 이동 후 위치를 확인하세요.'
        solution = 'pwd\ncd ..\npwd'
        goals = [cwd(str(PurePosixPath(m.start).parent))]
    elif kind == 'lsintro':
        prompt = f'{s}/docs로 직접 이동한 뒤 그 안의 목록을 화면에 표시하세요. 공백이 들어간 파일 이름도 확인하고 그 폴더에 머무세요.'
        solution = f'cd {s}/docs\nls'
        goals = [cwd(s + '/docs'), {'type': 'output_contains', 'text': 'read me.txt'}]
    elif kind == 'mkdir':
        prompt = f'{t}로 이동한 뒤 incoming과 outgoing 폴더를 각각 만드세요. 그 위치에 머무세요.'
        solution = f'cd {t}\nmkdir incoming\nmkdir outgoing'
        goals = [cwd(t), directory(t + '/incoming'), directory(t + '/outgoing')]
    elif kind == 'touch':
        prompt = f'{t}/checks 폴더를 먼저 만들고 그 안에 빈 one.txt와 two.txt를 만드세요.'
        solution = f'mkdir {t}/checks\ntouch {t}/checks/one.txt {t}/checks/two.txt'
        goals = [directory(t + '/checks'), file(t + '/checks/one.txt', ''), file(t + '/checks/two.txt', '')]
    elif kind == 'read':
        prompt = f'{s}/guide.txt와 {s}/docs/read me.txt 두 파일을 읽으세요. 공백이 있는 경로는 따옴표로 묶어야 합니다. 원본은 유지하세요.'
        solution = f'cat {s}/guide.txt\ncat {q(s + "/docs/read me.txt")}'
        goals = [output(f'Release {m.seed} user guide'), output('A file name with spaces'),
                 file(s + '/guide.txt', f'Release {m.seed} user guide\n'), file(s + '/docs/read me.txt', 'A file name with spaces\n')]
    elif kind == 'edit':
        title = '설정 복구와 내용 보존'
        setup = [file(t + '/note.txt', 'status=broken\nowner=learner\n')]
        prompt = f'{t}/note.txt의 status를 ready로 고치세요. owner=learner 줄은 보존하고 마지막에 reviewed=yes 줄을 추가해 저장하세요.'
        solution = f'nano {t}/note.txt'
        goals = [file(t + '/note.txt', 'status=ready\nowner=learner\nreviewed=yes\n')]
    elif kind == 'duplicate':
        prompt = f'{t}/backup 폴더를 만들고 원본을 보존하며 {s}/guide.txt를 guide.txt로, {s}/docs/read me.txt를 notes.txt로 복사하세요.'
        solution = f'mkdir {t}/backup\ncp {s}/guide.txt {t}/backup/guide.txt\ncp {q(s + "/docs/read me.txt")} {t}/backup/notes.txt'
        goals = [copy(t + '/backup/guide.txt', s + '/guide.txt'), copy(t + '/backup/notes.txt', s + '/docs/read me.txt'),
                 file(s + '/guide.txt', f'Release {m.seed} user guide\n'), file(s + '/docs/read me.txt', 'A file name with spaces\n')]
    elif kind == 'rename':
        prompt = f'{t}/draft.txt를 backup.txt로 복사해 보관하세요. approved 폴더를 만든 뒤 원래 draft.txt를 그 안으로 옮기면서 final.txt로 이름을 바꾸세요.'
        solution = f'cp {t}/draft.txt {t}/backup.txt\nmkdir {t}/approved\nmv {t}/draft.txt {t}/approved/final.txt'
        goals = [copy(t + '/backup.txt', t + '/draft.txt'), copy(t + '/approved/final.txt', t + '/draft.txt'), absent(t + '/draft.txt')]
    elif kind == 'remove':
        prompt = f'{t}/keep 폴더를 만들고 draft.txt를 그 안으로 옮겨 보존하세요. obsolete.txt만 삭제하세요.'
        solution = f'mkdir {t}/keep\nmv {t}/draft.txt {t}/keep/draft.txt\nrm {t}/obsolete.txt'
        goals = [copy(t + '/keep/draft.txt', t + '/draft.txt'), absent(t + '/draft.txt'), absent(t + '/obsolete.txt')]
    elif kind == 'report':
        title = '잘못된 보고서 덮어쓰기'
        setup = [file(r, '/wrong/old/location\n')]
        prompt = f'{s}로 이동하세요. 예전 위치가 적힌 {r}을 현재 위치로 덮어쓰고 내용을 확인하세요. 덧붙이면 안 됩니다.'
        solution = f'cd {s}\npwd > {r}\ncat {r}'
        goals = [cwd(s), file(r, s + '\n')]
    elif kind == 'workspace':
        title = '폴더 생성을 막는 파일 해결'
        keep_base = True
        setup = [file(t + '/daily notes', 'Keep this old note\n')]
        prompt = f'{t}/daily notes는 폴더가 아니라 파일입니다. 내용을 old-note.txt로 보존한 뒤 이 파일을 없애고 같은 이름의 폴더를 만들어 그 안에 빈 done.txt를 만드세요.'
        solution = f'cp {q(t + "/daily notes")} {t}/old-note.txt\nrm {q(t + "/daily notes")}\n' + m.solution
        goals = [file(t + '/old-note.txt', 'Keep this old note\n')]
    elif kind == 'copy':
        title = '손상된 복사본 복구와 백업'
        keep_base = True
        setup = [file(t + '/manual.txt', 'CORRUPTED\n')]
        prompt = (f'{t}/draft.txt를 {t}/draft-backup.txt로 먼저 보존하세요.\n'
                  f'복구 기준 파일은 {s}/guide.txt입니다. 이 파일의 내용으로 손상된 {t}/manual.txt를 덮어쓰세요. '
                  '파일 이름이 서로 다른 것은 정상입니다. guide.txt는 변경하지 마세요.\n'
                  f'{t}/draft.txt를 같은 폴더의 {t}/final.txt로 이름을 바꾸세요.\n'
                  f'{t}/obsolete.txt만 삭제하세요.')
        solution = f'cp {t}/draft.txt {t}/draft-backup.txt\n' + m.solution
        goals = [copy(t + '/draft-backup.txt', t + '/draft.txt')]
    elif kind == 'list':
        title = '기존 보고서 보존 후 재작성'
        keep_base = True
        setup = [file(r, 'Old incomplete inventory\n')]
        prompt = f'기존 {r}을 {r}.bak에 보존한 뒤 빠진 숨김 항목을 포함하도록 다시 작성하세요.\n' + m.prompt
        solution = f'cp {r} {r}.bak\n' + m.solution
        goals = [file(r + '.bak', 'Old incomplete inventory\n')]
    elif kind == 'long':
        keep_base = True
        prompt = (f'{s}로 이동하세요. 이동한 뒤의 현재 디렉터리 절대경로를 한 줄로 '
                  f'{r}.where 파일에 저장하세요. 이 파일에는 파일 목록이 아니라 현재 디렉터리 경로만 담으세요.\n'
                  + m.prompt + '\n작업을 마친 뒤에도 이동한 폴더에 머무세요.')
        solution = f'cd {s}\nls -al > {r}\npwd > {r}.where'
        goals = [cwd(s), file(r + '.where', s + '\n')]
    elif kind == 'mixed':
        keep_base = True
        prompt = (f'원본 파일은 {s}/guide.txt입니다.\n'
                  f'{t} 안에 backup 폴더를 새로 만드세요. 원본을 변경하지 않고 '
                  f'{t}/backup/guide.txt로 복사하세요.\n' + m.prompt)
        solution = f'mkdir {t}/backup\ncp {s}/guide.txt {t}/backup/guide.txt\n' + m.solution
        goals = [copy(t + '/backup/guide.txt', s + '/guide.txt'),
                 file(s + '/guide.txt', f'Release {m.seed} user guide\n')]
    elif kind == 'pwdpaths':
        title = '두 경로가 같아지는 경우 비교'
        prompt = f'이번에는 바로가기를 거치지 말고 실제 경로 {s}/docs로 들어가세요. pwd -L과 pwd -P를 각각 실행하면 같은 경로가 두 번 나와야 합니다. 그 위치에 머무세요.'
        solution = f'cd {s}/docs\npwd -L\npwd -P'
        goals = [cwd(s + '/docs'), output(s + '/docs', 2)]
    elif kind == 'lsoptions':
        title = '여러 조건을 보고서 하나에 조합'
        prompt = f'{s}의 숨김 항목과 .·..를 포함한 상세 목록을 읽기 쉬운 크기 단위로, 큰 크기순으로 정렬해 {r} 하나에 저장하세요. 따로 세 파일을 만드는 문제가 아닙니다.'
        solution = f'ls -alhS {s} > {r}\ncat {r}'
        goals = [listing(r, '-alhS')]
    elif kind == 'recursive':
        keep_base = True
        prompt = f'전체 구조 보고서를 만든 뒤 {t}/handover 폴더를 만들어 inventory.txt로 사본도 전달하세요.\n' + m.prompt
        solution = m.solution + f'\nmkdir {t}/handover\ncp {r} {t}/handover/inventory.txt'
        goals = [listing(t + '/handover/inventory.txt', '-alR')]
    elif kind == 'grep':
        title = '두 로그를 합쳐 필터·집계'
        setup = [file(t + '/other.log', 'INFO connected\nERROR remote\n')]
        prompt = f'{s}/app.log 다음에 {t}/other.log를 이어서 읽으세요. 대소문자와 관계없이 error 줄만 {r}에, 총 줄 수를 {r}.count에 저장하세요.'
        solution = f'cat {s}/app.log {t}/other.log | grep -i error > {r}\ncat {r} | wc -l > {r}.count'
        goals = [file(r, 'ERROR disk full\nerror timeout\nError network\nERROR remote\n'), {'type': 'stripped_file', 'path': r + '.count', 'text': '4'}]
    elif kind == 'find':
        title = '파일과 같은 확장자의 폴더 구별'
        prompt = f'{s} 아래에서 이름이 .deb로 끝나는 일반 파일이 아닌 디렉터리만 찾아 절대 경로를 {r}에 저장하세요. -type d는 디렉터리 조건입니다.'
        solution = f"find {s} -type d -name '*.deb' > {r}\ncat {r}"
        goals = [file(r, s + '/folder.deb\n')]
    elif kind == 'permissions':
        prompt = f'{t}/local.sh 원본은 실행 불가능한 그대로 보존하세요. ready 폴더를 만들어 run.sh로 복사하고 복사본에만 소유자 실행 권한을 추가하세요.'
        solution = f'mkdir {t}/ready\ncp {t}/local.sh {t}/ready/run.sh\nchmod u+x {t}/ready/run.sh\nls -l {t}/local.sh {t}/ready/run.sh'
        goals = [copy(t + '/ready/run.sh', t + '/local.sh'), {'type': 'executable', 'path': t + '/ready/run.sh', 'value': True}, {'type': 'executable', 'path': t + '/local.sh', 'value': False}]
    elif kind == 'curl':
        title = '손상된 다운로드 재시도'
        keep_base = True
        downloaded = t + '/received-' + m.artifact
        setup = [file(downloaded, 'INTERRUPTED DOWNLOAD\n')]
        prompt = f'손상된 {downloaded}를 failed-download.txt로 보존한 뒤 원래 URL에서 정상 파일로 다시 받으세요.\n' + m.prompt
        solution = f'cp {downloaded} {t}/failed-download.txt\n' + m.solution
        goals = [file(t + '/failed-download.txt', 'INTERRUPTED DOWNLOAD\n')]
    elif kind == 'wget':
        keep_base = True
        prompt = f'{t}/incoming 폴더를 만들고 wget -P로 URL의 원래 파일명으로 받으세요. 그 파일을 최종 이름으로 옮기세요. incoming에는 원래 파일이 남으면 안 됩니다.\n' + m.prompt
        solution = f'mkdir {t}/incoming\nwget -P {t}/incoming {m.url}\nmv {t}/incoming/{m.artifact} {t}/received-{m.artifact}'
        goals = [directory(t + '/incoming'), absent(t + '/incoming/' + m.artifact)]
    elif kind == 'archive':
        title = '이전 압축 해제 결과 보존'
        keep_base = True
        setup = [file(t + '/unpacked/README.txt', 'Previous installation notes\n')]
        prompt = f'기존 unpacked 폴더를 {t}/previous로 옮겨 보존한 뒤 새 압축 파일을 받아 깨끗하게 풀어 주세요.\n' + m.prompt
        solution = f'mv {t}/unpacked {t}/previous\n' + m.solution
        goals = [file(t + '/previous/README.txt', 'Previous installation notes\n')]
    elif kind == 'script':
        title = '기존 실행 결과 보존 후 재실행'
        keep_base = True
        setup = [file(t + '/receipt.txt', 'Previous execution\n')]
        prompt = f'이전 receipt.txt를 previous-receipt.txt로 먼저 보존하고 새 스크립트의 결과를 만드세요.\n' + m.prompt
        solution = f'cp {t}/receipt.txt {t}/previous-receipt.txt\n' + m.solution
        goals = [file(t + '/previous-receipt.txt', 'Previous execution\n')]
    elif kind == 'deb':
        keep_base = True
        prompt = m.prompt + f'\n추출만 하지 말고 패키지 메타데이터도 {r}에 보고서로 저장하세요.'
        solution = m.solution + f'\ndpkg-deb --info {t}/received-{m.artifact} > {r}'
        goals = [{'type': 'file_contains', 'path': r, 'text': 'Package: shellground-toolkit'}]
    else:
        raise ValueError('No review scenario for ' + kind)
    return replace(m, prompt=title + '\n' + prompt, solution=solution,
                   review={'title': title, 'setup': setup, 'goals': goals, 'keep_base': keep_base})
