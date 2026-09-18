"""Real Bash search, environment and reusable-script outcomes, in small units."""
import random
import shlex

SPECS = (
    ('shell_path', '명령 종류와 실행 파일 검색 순서', 'type · whereis · PATH',
     'type 이름은 지금 셸이 그 이름을 어떻게 해석하는지 보여 줍니다. pwd처럼 내장 명령도 있고 외부 실행 파일도 있습니다. '
     'type -P 이름은 PATH에서 외부 실행 파일 경로를 찾습니다. whereis bash는 관련 실행 파일·매뉴얼 위치를 조사하지만 지금 선택될 명령 하나를 판정하는 도구는 아닙니다.\n'
     'PATH는 콜론으로 구분한 폴더 목록이며 외부 명령은 앞쪽부터 찾습니다. export PATH="새폴더:$PATH"는 기존 목록 앞에 추가합니다. '
     '기존 /usr/bin·/bin을 지우면 다른 도구도 찾지 못할 수 있습니다. 현재 폴더를 무조건 PATH에 넣지 말고 필요한 실행 파일은 ./이름으로 지정할 수 있습니다.'),
    ('shell_source', '현재 셸에 적용할 설정과 자식 셸', 'source · bash 파일',
     'bash settings.sh는 자식 Bash에서 파일을 실행합니다. 그 안의 export나 cd는 현재 터미널 셸로 거슬러 올라오지 않습니다. '
     'source ./settings.sh 또는 . ./settings.sh는 지금 셸이 내용을 실행하므로 현재 환경과 위치도 바뀔 수 있습니다.\n'
     'source에는 파일 실행 권한이 필요하지 않습니다. 읽은 파일의 모든 명령이 지금 셸에서 실행되므로 신뢰하는 파일을 먼저 읽으세요. '
     'export한 값은 이후 자식으로 전달되지만, 같은 이름의 결과 파일이 있다고 환경까지 적용된 것은 아닙니다.'),
    ('shell_args', '스크립트 이름·개수·인자 경계', '$0 · $# · "$@" · "$*"',
     '$0은 호출된 스크립트 이름, $#은 전달된 인자의 개수입니다. "$@"는 인자를 각각 유지합니다. '
     '"$*"는 기본 IFS에서 인자들을 공백으로 연결한 한 문자열입니다. 따옴표 없는 $*는 공백 분리와 와일드카드 확장으로 원래 경계를 잃을 수 있습니다.\n'
     'printf "arg=%s\\n" "$@"는 각 인자를 한 줄씩 출력합니다. printf "joined=%s\\n" "$*"는 연결한 한 줄입니다. '
     '파일 이름에 공백이나 *가 있을 때 차이가 중요합니다. 이 단원은 인자가 하나 이상인 경우를 다룹니다.'),
    ('shell_if', '잘못된 인자를 먼저 거절하는 스크립트', 'if · [ ] · exit · >&2',
     'if [ "$#" -ne 2 ]; then ...; fi는 인자 개수가 2가 아닐 때만 분기합니다. [와 ]도 단어이므로 앞뒤 공백이 필요합니다. '
     '-ne는 정수 비교의 같지 않음입니다. exit 2는 현재 스크립트를 실패 상태 2로 끝냅니다.\n'
     'printf "usage: %s SOURCE RESULT\\n" "$0" >&2는 사용법을 표준 오류로 보냅니다. 일반 결과와 오류 안내를 분리합니다. '
     '$?는 직전 명령의 종료 상태이며 다른 명령을 실행하면 바뀝니다. 성공은 보통 0, 실패는 0이 아닙니다. '
     '인자를 검사하기 전에 >로 파일을 열면 잘못된 호출만으로 기존 파일을 지울 수 있으므로 먼저 검증합니다. '
     '인자 두 개가 올바르면 앞에서 배운 cat과 출력 저장을 조합합니다.'),
    ('shell_noclobber', '기존 파일을 덮어쓰지 않는 도구', 'set -C · bash -C · >|',
     '대문자 -C는 noclobber입니다. set -C는 현재 셸에서, bash -C 파일은 새 Bash에서 기존 일반 파일에 대한 > 덮어쓰기를 막습니다. '
     '소문자 -c는 뒤의 문자열을 명령으로 실행하므로 전혀 다릅니다.\n'
     '새 파일에는 >로 쓸 수 있지만 기존 일반 파일이면 오류와 실패 상태가 납니다. >>는 이어 쓰기이며 이 보호와 별개입니다. '
     '>|는 보호를 명시적으로 우회하므로 이번 보존 목표에는 쓰지 않습니다. set +C로 끌 수 있지만 이 단원의 스크립트는 보호를 유지해야 합니다. '
     'chmod로 읽기 전용으로 만드는 기능도 아니며 다른 프로그램의 파일 수정을 모두 차단하지 않습니다.'),
)
KEYS = tuple(row[0] for row in SPECS)


def units(Unit):
    return tuple(Unit(k, 6, title, command, explanation,
                      '파일 결과뿐 아니라 현재 셸과 다른 인자에서의 동작도 확인하세요.')
                 for k, title, command, explanation in SPECS)


def write_script(path, lines):
    # Each reference command is one PTY input line. Quotes preserve $ until
    # script execution, not while the parent Bash writes the file.
    return "printf '%s\\n' " + ' '.join(shlex.quote(s) for s in lines) + ' > ' + shlex.quote(path)


def reference_script(kind):
    if kind == 'shell_args':
        return ['#!/bin/bash', 'printf "script=%s\\ncount=%s\\n" "$0" "$#"',
                'printf "arg=%s\\n" "$@"', 'printf "joined=%s\\n" "$*"']
    if kind == 'shell_if':
        return ['#!/bin/bash', 'if [ "$#" -ne 2 ]; then',
                '  printf "usage: %s SOURCE RESULT\\n" "$0" >&2', '  exit 2', 'fi', 'cat -- "$1" > "$2"']
    if kind == 'shell_noclobber':
        return ['#!/bin/bash', 'set -C', 'printf "ready\\n" > "$1"']
    raise ValueError(kind)


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    if kind not in (*KEYS, 'shell_review') or practice not in (0, 1, 2): raise ValueError('Unknown shell exercise')
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    start = f'/home/learner/shell/session{seed}'
    plan = dict(shell_course=1, project=f'team-{seed}', mode=kind, reports={}, script='', backup=False)
    actions = []
    if kind == 'shell_path':
        desired = 'green' if practice != 1 else 'blue'
        plan['desired'] = desired
        prompt = (f'tools/{desired}의 sgtool을 이름만으로 실행할 수 있도록 현재 셸의 검색 순서를 설정하세요. '
                  '기존 /usr/bin·/bin은 검색 가능하게 유지하세요. 선택된 외부 실행 파일 경로를 selected.txt, '
                  'sgtool 실행 결과를 result.txt, pwd의 명령 종류 조회를 kind.txt, bash 관련 위치 조회를 locations.txt에 저장하세요.')
        if practice == 1:
            prompt += '\n기존 selected.txt와 result.txt는 이전 설치 경로를 가리킵니다. tools/green도 PATH에 남겨 두되 tools/blue가 먼저 선택되게 하고, 보고서를 현재 결과로 바로잡으세요.'
        if practice == 2:
            prompt += '\n설정 후 reports 폴더로 이동하세요. 그 위치에서도 같은 명령이 선택되어야 합니다. 네 보고서는 시작 폴더에 두세요.'
        actions = [f'export PATH="{start}/tools/{desired}:$PATH"']
        if practice == 1: actions = [f'export PATH="{start}/tools/blue:{start}/tools/green:$PATH"']
        if practice == 2: actions += ['cd reports']
        out = '../' if practice == 2 else ''
        actions += [f'type -P sgtool > {out}selected.txt', f'sgtool > {out}result.txt',
                    f'type pwd > {out}kind.txt', f'whereis bash > {out}locations.txt']
    elif kind in ('shell_source', 'shell_review'):
        prompt = ('settings.sh의 내용을 읽고 현재 learner 셸에 적용하세요. LAB_PROJECT를 내보내고 설정에 지정된 reports 폴더로 이동한 상태여야 합니다. '
                  '그 폴더에 LAB_PROJECT 값은 project.txt, 현재 위치의 절대경로는 location.txt로 저장하세요.')
        if practice == 1:
            prompt += '\n두 보고서는 이전 프로젝트 값입니다. 기존 reports/project.txt를 시작 위치의 "previous project.txt"로 보관한 뒤 현재 셸 설정과 보고서를 바로잡으세요.'
        if practice == 2:
            prompt += '\n현재 셸의 설정을 유지하면서 child.sh를 자식 셸로 실행한 출력은 child.txt에 저장하세요. 자식의 값으로 현재 LAB_PROJECT를 바꾸지 마세요.'
        actions = ['cat settings.sh', 'source ./settings.sh', 'printenv LAB_PROJECT > project.txt', 'pwd > location.txt']
        if practice == 1: actions.insert(0, 'cp reports/project.txt "previous project.txt"')
        if practice == 2: actions += ['bash ../child.sh > child.txt']
        if kind == 'shell_review':
            prompt += ('\nreports 안에 guard.sh를 작성하세요. 경로 인자 하나를 받아 새 일반 파일에는 ready 한 줄을 저장하고, '
                       '기존 일반 파일이면 내용을 유지하며 표준 오류와 0이 아닌 종료 상태를 내야 합니다. 이 도구로 fresh.txt를 만들고 ../personal.txt는 덮어쓰지 마세요. '
                       '채점에서도 다른 공백 경로와 기존 파일로 도구를 실행합니다.')
            plan['script'] = 'reports/guard.sh'
            actions += [write_script('guard.sh', reference_script('shell_noclobber')),
                        'bash guard.sh fresh.txt', 'bash guard.sh ../personal.txt']
    else:
        name = {'shell_args': 'arguments.sh', 'shell_if': 'handover.sh', 'shell_noclobber': 'guard.sh'}[kind]
        plan['script'] = name
        if kind == 'shell_args':
            prompt = ('arguments.sh를 작성하세요. 하나 이상의 임의 인자를 받으면 script=호출된이름, count=인자개수를 첫 두 줄로 출력하고, '
                      '각 인자를 arg=값 한 줄씩, 마지막에는 기본 IFS로 연결한 joined=값 한 줄을 출력하세요. '
                      '공백·빈 문자열·*도 인자 그대로 보존해야 합니다. 도구는 다른 인자로도 채점합니다. '
                      '시작 위치에서 "daily notes"와 "*.txt" 두 인자로 실행한 결과를 result.txt에 저장하세요.')
            invocation = 'bash arguments.sh "daily notes" "*.txt" > result.txt'
        elif kind == 'shell_if':
            prompt = ('handover.sh를 작성하세요. 인자가 정확히 두 개면 첫 번째 파일의 내용을 두 번째 경로에 저장하세요. '
                      '다른 개수면 파일을 건드리지 말고 표준 오류에 usage: 호출된이름 SOURCE RESULT 한 줄을 출력하며 상태 2로 끝나야 합니다. '
                      '인자 두 개인 검사에서는 읽을 수 있는 원본과 쓸 수 있는 대상 경로를 제공하며, 두 경로는 같은 실제 파일을 가리키지 않습니다. '
                      '"source notes.txt"를 "received notes.txt"로 인계하세요. 원본은 보존하세요. 다른 경로·내용·인자 개수로도 채점합니다.')
            invocation = 'bash handover.sh "source notes.txt" "received notes.txt"'
        else:
            prompt = ('guard.sh를 작성하세요. 경로 인자 하나를 받아 새 파일에는 ready 한 줄을 저장하되, 기존 일반 파일이면 내용을 보존하고 '
                      '표준 오류와 0이 아닌 종료 상태를 내야 합니다. 다른 공백 경로와 기존 파일로도 채점합니다. '
                      '이 도구로 fresh.txt를 만들고 personal.txt는 덮어쓰지 마세요.')
            invocation = 'bash guard.sh fresh.txt'
        if practice == 1:
            defect = {'shell_args': '기존 도구는 인자들을 하나로 합쳐 공백 경로·빈 인자의 경계를 잃습니다.',
                      'shell_if': '기존 도구는 인자 개수를 확인하지 않아 잘못된 호출에도 파일을 쓰려고 합니다.',
                      'shell_noclobber': '기존 도구는 새 파일에는 쓰지만 이미 있는 파일까지 덮어씁니다.'}[kind]
            prompt = defect + ' 결함을 고쳐 아래 계약을 충족하게 하세요.\n' + prompt
        if practice == 2:
            plan['backup'] = True
            prompt = '기존 broken.sh를 보존하고 새 도구를 작성하세요. broken.sh의 복사본도 "original script.txt"로 보관하세요.\n' + prompt
            actions.append('cp broken.sh "original script.txt"')
        actions += [write_script(name, reference_script(kind)), invocation]
        if kind == 'shell_noclobber': actions.append('bash guard.sh personal.txt')
    prompt += '\n준비된 settings.sh·child.sh·broken.sh·tools의 실행 파일, personal.txt와 "source notes.txt"는 보존하세요.'
    return Mission(kind, seed, start, start + '/source notes.txt', start + '/result.txt', start + '/reports',
                   '', '', prompt, '\n'.join(actions), practice=practice, review=plan)


def steps(unit, mission):
    from learning_steps import LearningStep as S
    key = unit.key
    if key == 'shell_path':
        return (S('내장 명령과 외부 파일 조사', unit.explanation,
                  'type pwd\ntype -a bash\nwhereis bash', '같은 이름의 관련 경로와 실제 셸 선택을 구분합니다.'),
                S('검색 순서 적용과 결과 확인', 'tools의 프로그램은 준비된 실제 스크립트입니다. 절대경로를 PATH에 넣으면 위치를 바꿔도 선택이 유지됩니다.',
                  mission.solution, 'selected.txt 경로와 result.txt의 버전을 함께 확인합니다.'))
    if key == 'shell_source':
        return (S('자식에서만 바뀌는 상태', unit.explanation,
                  'cat settings.sh\nbash settings.sh\nprintenv LAB_PROJECT\npwd', '자식의 export·cd가 현재 셸에는 적용되지 않습니다.'),
                S('현재 셸에 적용', 'source 뒤에는 현재 위치도 바뀝니다. 다음 상대경로의 기준이 reports가 됩니다.',
                  mission.solution, '현재 환경값과 위치, 보고서가 함께 맞아야 합니다.'))
    script = mission.review['script']
    lines = reference_script(key)
    return (S('작은 스크립트의 계약 읽기', unit.explanation + '\n\n작성할 예시:\n' + '\n'.join(lines),
              'cat ' + script, '처음에는 실행할 수 있는 작은 초안만 있습니다. 여기에 새 동작을 작성합니다.'),
            S('작성하고 실제 인자로 실행', 'nano로 같은 내용을 작성해도 됩니다. 아래 printf는 작은따옴표로 각 줄을 보존해 파일에 쓰는 예시입니다.',
              mission.solution, '오류 안내는 실패 조건에서 정상적인 결과입니다. 같은 도구를 다른 인자에도 사용해 봅니다.'),
            S('다른 조건도 비교', '한 번의 정답 파일보다 재사용 가능한 동작이 중요합니다. $?는 직전 명령의 종료 상태이므로 다른 명령 전에 읽습니다.',
              ('bash arguments.sh "" "a b" "*"' if key == 'shell_args' else
               'bash handover.sh\nprintf "status=%s\\n" "$?"' if key == 'shell_if' else
               'bash -C guard.sh personal.txt\nprintf "status=%s\\n" "$?"'),
              '빈 인자는 개수에 포함됩니다.' if key == 'shell_args' else '잘못된 입력·기존 파일에는 실패 상태가 나와야 합니다.'))
