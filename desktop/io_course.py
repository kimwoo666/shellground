"""Actual stdin/paging/hierarchy/program execution; no shell simulation."""
import random

SPECS = (
    ('io_input', '키보드 입력을 파일로 마치기', 'cat > · Ctrl+D · >>',
     '파일 인자 없는 cat은 표준 입력을 읽습니다. cat > 파일은 키보드로 입력한 내용을 파일에 저장하며 셸 명령을 기다리는 상태가 아닙니다. '
     '내용의 마지막 줄에서 Enter를 누르고, 새 빈 줄에서 Ctrl+D로 입력을 마칩니다. 보통 터미널에서 입력 버퍼가 비었을 때 EOF가 전달되는 것이며 ^D 두 글자를 파일에 적는 것이 아닙니다.\n'
     '입력 중 Ctrl+D는 남은 입력을 먼저 전달할 수 있습니다. Ctrl+C는 중단이며 이미 쓴 파일이 자동으로 되돌아가지는 않습니다. '
     '셸 프롬프트에서 Ctrl+D를 누르면 셸을 종료할 수 있으니 현재 어느 프로그램에 입력하는지 확인하세요. >는 기존 내용을 비우고, >>는 뒤에 이어 씁니다.'),
    ('io_pager', '긴 문서를 페이지로 읽고 돌아오기', 'more · Space · Enter · /검색 · q',
     'more 파일은 한 화면씩 읽습니다. Space는 다음 화면, Enter는 한 줄, /단어 다음 Enter는 검색, n은 다음 일치를 찾습니다. '
     'q는 more를 닫고 셸로 돌아옵니다. more 안의 Ctrl+D는 스크롤 동작이므로 cat의 입력 종료와 같지 않습니다.\n'
     'cat 파일 | more는 파이프로 내용을 전달합니다. 파이프에서는 뒤로 이동이 제한될 수 있어 다시 검색할 문서는 more 파일처럼 직접 여는 편이 편합니다. '
     'more -12 파일은 화면당 12줄을 지정하는 예시입니다. 실제 창 크기와 무관하게 작은 페이지로 연습할 때 쓸 수 있습니다. '
     '여기서는 찾은 값과 원본 보존, 셸 복귀를 채점하며 특정 조회 명령만 정답으로 강제하지 않습니다.'),
    ('io_tree', '목록을 부모·자식 구조로 읽기', 'tree · -a · -d · -L',
     'tree 폴더는 들여쓰기와 연결선으로 계층을 보여 줍니다. -a는 점으로 시작하는 숨김 항목도 포함하지만 ls -a와 달리 .과 ..는 표시하지 않습니다. '
     '-d는 디렉터리만, -L 2는 지정한 루트 아래 두 단계까지만 보여 줍니다. -L은 대문자입니다.\n'
     'tree -ad -L 2 폴더처럼 조건을 조합할 수 있습니다. 마지막 합계는 화면에 표시한 범위의 합계입니다. '
     '보고서는 조회 대상 밖에 저장해야 보고서 자체가 목록에 섞이지 않습니다. 파일 확장자만으로 파일과 폴더를 판단하지 마세요.'),
    ('io_binary', '복사한 실행파일을 경로로 실행하기', 'cp /bin/ls · ./ls · 실행 권한',
     'cp /bin/ls .은 실제 실행파일을 현재 폴더에 복사합니다. ./ls는 그 복사본을 지정하지만 ls만 쓰면 별칭·PATH 규칙에 따라 다른 프로그램이 선택될 수 있습니다. '
     './는 현재 위치이므로 이동했다면 복사본까지의 상대경로를 다시 생각해야 합니다.\n'
     '일반적인 복사는 현재 사용자 소유의 새 파일을 만듭니다. 실행파일에는 내용뿐 아니라 실행 권한도 필요합니다. '
     'Permission denied이면 ls -l로 권한을 보고 필요한 소유자 실행 권한을 chmod u+x로 복구할 수 있습니다. '
     '실행파일 하나만 복사한다고 다른 OS나 CPU에서 실행되는 것은 아닙니다. 이 예는 같은 Linux 안의 동일 실행 환경입니다.'),
    ('io_shebang', '스크립트의 해석기와 직접 실행', '#!/bin/bash · chmod u+x · ./파일',
     '첫 줄의 #! 뒤 경로는 스크립트를 직접 실행할 때 사용할 해석기를 지정합니다. #!/bin/bash는 Bash를 선택합니다. '
     '직접 실행에는 파일의 실행 권한과 존재하는 해석기 경로가 필요합니다. bash 파일은 Bash를 직접 실행해 읽게 하므로 스크립트 실행 비트가 없어도 동작할 수 있습니다.\n'
     'Bash가 해석기 없는 텍스트를 대신 해석하는 경우도 있어 #! 없는 파일이 모든 상황에서 반드시 실패한다고 단정하지 마세요. '
     '이번에는 다른 호출 프로그램에서도 직접 실행되도록 Bash 해석기를 명시합니다. #! 앞의 빈 줄이나 잘못된 경로는 피하세요. '
     '이미 배운 "$1"로 공백 경로 하나를 전달하고, 다른 폴더에서도 같은 도구를 재사용합니다.'),
)
KEYS = tuple(row[0] for row in SPECS)


def units(Unit):
    return tuple(Unit(k, 3, title, commands, explanation,
                      '입력하는 프로그램과 셸 프롬프트를 구분하고 원본을 유지하세요.') for k, title, commands, explanation in SPECS)


def input_block(command, text):
    return command + '\n' + text.rstrip('\n') + '\n# Ctrl+D (새 빈 줄에서 키 입력)'


def script_lines():
    return ['#!/bin/bash', 'printf "directory=%s\\n" "$1"', '/bin/ls -1a -- "$1"']


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    from shell_course import write_script
    if kind not in (*KEYS, 'io_review') or practice not in (0, 1, 2): raise ValueError('Unknown I/O exercise')
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    start = f'/home/learner/io/session{seed}'
    code, destination = f'R{seed}-READY', f'dock-{seed % 5 + 1}'
    plan = dict(io_course=1, code=code, destination=destination, reports={}, backup='',
                move=False, binary='', script='', files={})
    if kind == 'io_input':
        content = f'team=alpha\nrelease={seed}\n'
        plan['files']['entry.txt'] = content
        prompt = 'entry.txt에 아래 두 줄을 순서대로 저장하고 셸로 돌아오세요. 각 줄 끝에는 줄바꿈이 있어야 합니다.\n' + content
        actions = [input_block('cat > entry.txt', content)]
        if practice == 1:
            plan['backup'] = 'entry.txt'
            prompt = 'entry.txt에는 이전 인계 내용이 있습니다. 기존 내용을 "previous entry.txt"로 보관한 뒤 새 내용으로 교체하세요.\n' + prompt
            actions.insert(0, 'cp entry.txt "previous entry.txt"')
        if practice == 2:
            prompt = ('entry.txt의 기존 두 줄은 유지하고 status=ready 한 줄만 뒤에 추가하세요. '
                      '원본 "source notes.txt"의 복사본도 reports 아래 같은 파일 이름으로 보관하세요. 셸로 돌아와 있어야 합니다.')
            plan['files']['entry.txt'] = content + 'status=ready\n'
            actions = [input_block('cat >> entry.txt', 'status=ready\n'), 'cp "source notes.txt" reports/']
            plan['files']['reports/source notes.txt'] = 'Original handover notes.\n'
    elif kind == 'io_pager':
        prompt = ('"long notes.txt"의 RELEASE CHECKPOINT 부분에서 code= 줄을 찾아 answer.txt에 그 한 줄을 저장하세요. '
                  '문서는 수정하지 말고 셸로 돌아오세요.')
        plan['files']['answer.txt'] = 'code=' + code + '\n'
        actions = ['more -12 "long notes.txt"', '# more: Space, Enter, /RELEASE CHECKPOINT, Enter, q',
                   input_block('cat > answer.txt', plan['files']['answer.txt'])]
        if practice == 1:
            plan['backup'] = 'answer.txt'
            prompt = ('answer.txt는 낡은 인계 값입니다. "previous answer.txt"로 보관한 뒤 갱신하세요. '
                      '문서의 RELEASE CHECKPOINT에서 code=, destination= 두 줄을 이 순서대로 저장하세요. 문서 원본을 보존하고 셸로 돌아오세요.')
            plan['files']['answer.txt'] += 'destination=' + destination + '\n'
            actions = ['cp answer.txt "previous answer.txt"', *actions[:2], input_block('cat > answer.txt', plan['files']['answer.txt'])]
        if practice == 2:
            prompt += '\n별도 "correction notes.txt"의 정정 사항을 읽고 answer.txt 두 번째 줄에 그 파일의 destination= 값을 추가하세요. 오래된 본문 위치 값을 그대로 쓰지 마세요.'
            plan['files']['answer.txt'] += f'destination=revised-{seed % 7}\n'
            actions = ['cat "long notes.txt" | more -12', actions[1], 'cat "correction notes.txt"',
                       input_block('cat > answer.txt', plan['files']['answer.txt'])]
    elif kind == 'io_tree':
        prompt = 'inventory의 숨김 항목을 포함한 전체 부모·자식 구조를 tree.txt에 저장하세요. 파일과 폴더 이름, 연결선이 드러나는 트리 형식이어야 합니다.'
        plan['reports']['tree.txt'] = dict(dirs=False, depth=None)
        actions = ['tree -a inventory > tree.txt']
        if practice == 1:
            prompt += '\n추가로 숨김 폴더를 포함하되 inventory 아래 두 단계까지의 디렉터리만 dirs.txt에 저장하세요. 두 보고서의 범위는 다릅니다.'
            plan['reports']['dirs.txt'] = dict(dirs=True, depth=2)
            actions += ['tree -ad -L 2 inventory > dirs.txt']
        if practice == 2:
            plan['move'] = True
            prompt = ('잘못 배치된 inventory/src/guide.txt를 inventory/docs/"handover guide.txt"로 옮기고, '
                      'inventory/docs/review 폴더를 만드세요. 옮긴 문서의 내용은 유지하세요. 정리 후의 상태로 아래 보고서를 작성하세요.\n') + prompt
            actions = ['mv inventory/src/guide.txt "inventory/docs/handover guide.txt"', 'mkdir inventory/docs/review', *actions]
    elif kind == 'io_binary':
        plan['binary'] = 'ls'
        prompt = ('/bin/ls를 시작 폴더의 ls로 복사해 learner 소유의 실행 가능한 파일로 만드세요. '
                  '그 복사본으로 inventory 바로 아래 이름을 숨김 항목과 .·..까지 한 줄에 하나씩 조회한 결과를 names.txt에 저장하세요.')
        actions = ['cp /bin/ls .', './ls -1a inventory > names.txt']
        if practice == 1:
            plan['backup'] = 'ls'
            prompt = '기존 ls는 손상된 실행파일이며 소유자 실행 권한도 없습니다. "previous tool"로 보관한 뒤 복구하세요.\n' + prompt
            actions = ['cp ls "previous tool"', 'cp /bin/ls ./ls', 'chmod u+x ./ls', actions[-1]]
        if practice == 2:
            plan['binary'] = 'tools/local ls'
            prompt = ('/bin/ls를 tools/"local ls"로 복사해 learner 소유의 실행 가능한 파일로 만드세요. reports로 이동해 그 복사본으로 '
                      '../inventory의 바로 아래 이름을 숨김 항목과 .·..까지 한 줄에 하나씩 조회하고, reports/names.txt에 저장하세요. reports에 머무세요.')
            actions = ['cp /bin/ls "tools/local ls"', 'cd reports', '"../tools/local ls" -1a ../inventory > names.txt']
    elif kind == 'io_shebang':
        plan['script'] = 'show-files.sh'
        prompt = ('show-files.sh를 직접 실행 가능한 learner 소유 Bash 스크립트로 작성하세요. 첫 줄에 Bash 해석기를 명시하세요. '
                  '기존 폴더 경로 하나를 인자로 받아 첫 줄에 directory=입력받은경로를 출력하고, 그 폴더 바로 아래 이름을 .·..와 숨김 항목까지 한 줄씩 출력해야 합니다. '
                  '공백 경로와 다른 폴더도 처리해야 하며 채점에서 직접 실행합니다. inventory를 인자로 실행한 결과는 run.txt에 저장하세요.')
        actions = [write_script('show-files.sh', script_lines()), 'chmod u+x show-files.sh', './show-files.sh inventory > run.txt']
        if practice == 1:
            plan['backup'] = 'show-files.sh'
            prompt = '기존 show-files.sh는 첫 줄의 해석기 경로가 잘못되었습니다. "previous script.txt"로 보관하고 복구하세요.\n' + prompt
            actions.insert(0, 'cp show-files.sh "previous script.txt"')
        if practice == 2:
            prompt += '\nreports로 이동한 뒤 ../show-files.sh에 "../inventory/docs"를 전달한 결과도 reports/docs.txt에 저장하세요. reports에 머무세요.'
            actions += ['cd reports', '../show-files.sh ../inventory/docs > docs.txt']
    else:
        plan.update(binary='ls', script='show-files.sh', files={'entry.txt': f'code={code}\n'})
        plan['reports']['tree.txt'] = dict(dirs=False, depth=None)
        prompt = ('"long notes.txt"의 RELEASE CHECKPOINT에서 code= 줄을 찾아 entry.txt에 저장하세요. '
                  'inventory의 숨김 항목 포함 전체 트리는 tree.txt에 저장하세요. /bin/ls 복사본을 ./ls에 learner 소유의 실행파일로 두세요. '
                  'show-files.sh에는 Bash 해석기를 명시하고 직접 실행 가능하게 만드세요. 경로 하나를 인자로 받으면 directory=입력받은경로 한 줄 뒤에 '
                  '그 폴더의 숨김 항목과 .·..를 포함한 이름을 한 줄씩 출력해야 합니다. inventory로 실행한 결과는 run.txt, ./ls로 같은 목록만 출력한 결과는 names.txt에 저장하세요. '
                  '문서 조회를 끝내고 learner 셸로 돌아와 있어야 합니다.')
        actions = ['more -12 "long notes.txt"', '# more: Space, Enter, /RELEASE CHECKPOINT, Enter, q',
                   input_block('cat > entry.txt', f'code={code}\n'), 'tree -a inventory > tree.txt', 'cp /bin/ls .',
                   './ls -1a inventory > names.txt', write_script('show-files.sh', script_lines()),
                   'chmod u+x show-files.sh', './show-files.sh inventory > run.txt']
    prompt += '\n지정한 변경 대상 외의 준비 자료와 personal.txt는 내용·권한을 보존하세요. /bin/ls 원본을 수정하지 마세요.'
    return Mission(kind, seed, start, start + '/inventory', start + '/run.txt', start + '/reports', '', '',
                   prompt, '\n'.join(actions), practice=practice, review=plan)


def steps(unit, m):
    from learning_steps import LearningStep as S
    key = unit.key
    if key == 'io_input':
        return (S('키보드 입력 받기', unit.explanation, input_block('cat > scratch.txt', 'first line\nsecond line\n'),
                  'Ctrl+D 표시는 명령으로 입력하지 말고 실제 키를 누릅니다. 다시 프롬프트가 보이면 cat scratch.txt로 확인합니다.'),
                S('기존 내용 뒤에 추가', '>>는 기존 두 줄을 지우지 않습니다. 입력한 마지막 줄 뒤 Enter, 빈 줄에서 Ctrl+D입니다.',
                  input_block('cat >> scratch.txt', 'third line\n') + '\ncat scratch.txt', '첫 두 줄이 남아 있는지 확인합니다.'),
                S('인계 파일 완성', '이번 목표의 파일과 줄을 확인하고 직접 입력합니다.', m.solution, '파일 내용과 셸 복귀를 확인합니다.'))
    if key == 'io_pager':
        return (S('한 화면과 한 줄 넘기기', unit.explanation, 'more -12 "long notes.txt"\n# Space → Enter (키 입력)',
                  '셸 프롬프트 대신 more 표시가 보입니다. 이 상태를 유지해 다음 설명을 봅니다.'),
                S('문서에서 찾고 종료', '/ 뒤 검색어를 쓰고 Enter를 누릅니다. q로 닫기 전까지는 셸 명령을 입력하는 상태가 아닙니다.',
                  '# /RELEASE CHECKPOINT → Enter → q (키 입력)', 'code=와 destination=을 읽고 q 뒤 셸 프롬프트를 확인합니다.'),
                S('찾은 값만 인계', '예시의 값을 먼저 읽은 문서 내용과 대조합니다.',
                  input_block('cat > answer.txt', f'code={m.review["code"]}\n'), '원본 긴 문서는 그대로 두고 결과 파일만 만듭니다.'))
    if key == 'io_tree':
        return (S('기본 트리와 숨김 항목', unit.explanation, 'tree inventory\ntree -a inventory', '숨김 항목은 추가되지만 .·..는 나오지 않습니다.'),
                S('대상 종류와 깊이 제한', '-d는 폴더만, -L 2는 두 단계까지만 보여 줍니다. 전체 파일이 사라진 것으로 오해하지 않습니다.',
                  'tree -ad -L 2 inventory', 'folder.deb는 확장자와 관계없이 실제 폴더라 표시됩니다.'),
                S('전체 계층 저장', '보고서를 inventory 밖에 두면 자기 자신이 목록에 들어오지 않습니다.', m.solution, '서로 다른 부모 아래 이름을 연결선으로 구분합니다.'))
    if key == 'io_binary':
        return (S('프로그램 복사', unit.explanation, 'cp /bin/ls .\nls -l ./ls /bin/ls', '크기와 소유자를 비교합니다. 실행 권한도 읽습니다.'),
                S('복사본을 직접 지정', '이름 ls 대신 ./ls로 현재 폴더의 파일을 실행합니다.', './ls -1a inventory', '복사본으로 실제 목록을 조회합니다.'),
                S('결과 인계', '조회 도구와 조회 대상, 저장할 보고서를 각각 구분하세요.', './ls -1a inventory > names.txt', '목록 보고서는 원본 inventory 밖에 둡니다.'))
    return (S('해석기 명시해 작성', unit.explanation, input_block('cat > show-files.sh', '\n'.join(script_lines()) + '\n'),
              '첫 바이트가 #!인지, 경로와 따옴표가 맞는지 확인합니다.'),
            S('읽어 실행과 직접 실행 비교', 'bash로 읽는 경우와 실행 비트를 부여한 직접 실행을 비교합니다. 이번 문서는 신뢰하는 실습 파일입니다.',
              'bash show-files.sh inventory\nchmod u+x show-files.sh\n./show-files.sh inventory', '실행 비트와 첫 줄의 해석기는 서로 다른 조건입니다.'),
            S('다른 경로에도 사용할 도구', '고정 목록을 출력하지 말고 전달받은 폴더를 실제 조회합니다.',
              './show-files.sh "probe samples/two words"\n./show-files.sh inventory > run.txt', '공백을 포함한 다른 경로로도 동작해야 합니다.'))
