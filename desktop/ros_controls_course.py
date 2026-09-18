"""Real Humble keyboard practice, appended after the preserved ROS 01–20."""
import random

SPECS = (
    ('teleop', '키보드로 올바른 거북이 제어', 'turtle_teleop_key · 방향키 · namespace', (
        'turtle_teleop_key는 별도 입력 노드입니다. 실제 turtlesim은 준비되어 있습니다. ros2 run turtlesim turtle_teleop_key를 실행한 터미널을 선택하세요. 그림 창에 키를 누르는 것과 다릅니다.',
        '↑/↓는 현재 거북이 방향 기준 전진/후진, ←/→는 제자리 회전입니다. 화면 위쪽/아래쪽 이동이라는 뜻이 아닙니다. 키를 짧게 누르세요. 키를 놓아도 즉시 0 명령이 나가는 것은 아니며 turtlesim은 명령 시간초과 뒤 멈춥니다.',
        '입력 노드는 상대 이름 turtle1/cmd_vel로 발행합니다. --ros-args -r __ns:=/team이면 /team/turtle1/cmd_vel에 연결됩니다. __node는 노드 이름만 바꾸므로 제어 대상 토픽을 바꾸는 옵션이 아닙니다. 전체 토픽 remap도 가능합니다.',
        '두 번째 터미널에서 같은 실습 폴더의 control-status.txt를 읽으면 실제 메시지 수와 pose 관측을 볼 수 있습니다. 이 파일은 앱 관측 결과이므로 수정하지 마세요. 조작 후 잠시 정지를 관찰하고 입력 터미널에서 Ctrl+C로 끝냅니다. turtlesim은 유지합니다.')),
    ('pause', '기록 재생 정지·재개·한 메시지', 'bag play --start-paused · Space · →', (
        'ros2 bag play control_bag --start-paused --topics /turtle1/cmd_vel은 선택한 토픽을 처음부터 일시정지 상태로 엽니다. --start-paused는 키 입력과 구독 연결을 준비할 시간을 줍니다. 원본 bag은 바꾸지 않습니다.',
        '두 번째 터미널에서 cat control-status.txt로 실제 player의 paused, rate, messages를 확인합니다. observer_ready=true와 paused=true가 보인 뒤 조작하세요. 준비 중이라면 기다리거나 연결을 조사하세요. 다른 터미널에서 조회해도 player 입력 터미널은 계속 열어 둡니다.',
        'player 터미널의 Space는 정지/재개 토글입니다. →는 paused 상태에서 선택한 재생 흐름의 다음 메시지 하나만 발행합니다. 1초 건너뛰기나 거북이 한 걸음이 아닙니다. 키를 길게 누르면 반복되어 여러 메시지가 나갈 수 있습니다.',
        'Space로 멈춰도 이미 받은 이동 명령을 취소하지 않으며 pose는 계속 발행될 수 있습니다. 실제 paused와 선택 토픽의 메시지 수로 확인합니다. Ctrl+C는 일시정지가 아니라 종료입니다. 단계 관찰 후 player만 종료하세요.')),
    ('rate', '재생 배율과 메시지 값 구별', '--rate · ↑/↓ · 내용 보존', (
        '--rate 1.0은 처음 재생 배율입니다. 0.5는 절반, 2.0은 두 배 시간 배율이며 Twist의 linear.x 값을 곱하는 옵션이 아닙니다. 유효 배율은 양수입니다. --start-paused로 먼저 멈춘 채 시작합니다.',
        '이 실습의 Humble에서 ↑는 현재 배율+0.1, ↓는 −0.1입니다. 1.0→1.1→1.0으로 돌아옵니다. 콘솔의 “10%”를 현재 값×1.1/0.9로 해석하지 마세요. 다른 배포판에서는 동작을 확인해야 합니다.',
        '키는 player 터미널에 보냅니다. 두 번째 터미널의 cat control-status.txt로 실제 rate와 paused를 확인하고 다음 키를 누르세요. 배율을 바꿔도 paused는 유지됩니다. 배율0으로 정지를 대신하지 않습니다.',
        '→로 다음 메시지 하나를 확인하면 배율과 내용이 별개라는 것을 볼 수 있습니다. 준비된 첫 두 linear.x 값은 0.25, 0.26이며 angular.z는 0입니다. 짧은 벽시계 측정이나 거북이 위치를 정확한 시간 배율의 증거로 삼지 않습니다. player를 종료하고 bag을 보존합니다.')),
)
KEYS = tuple('ros_controls_' + s[0] for s in SPECS)


def units(Unit):
    return tuple(Unit('ros_controls_' + key, 7, title, commands, '\n'.join(parts),
                      '키 입력 터미널과 관측 터미널을 구별하세요.') for key, title, commands, parts in SPECS)


def make_mission(kind, seed=None, practice=0):
    from missions import Mission
    if kind not in KEYS or practice not in (0, 1, 2): raise ValueError(kind)
    seed = random.SystemRandom().randrange(1000, 9999) if seed is None else seed
    start = f'/home/learner/ros/controls{seed}'
    key = kind.removeprefix('ros_controls_')
    prefix = '/team' if key == 'teleop' and practice == 2 else ''
    setup = 'source /opt/ros/humble/setup.bash'
    play = 'ros2 bag play control_bag --start-paused --topics /turtle1/cmd_vel'
    status = f'# 두 번째 터미널: cd {start} && cat control-status.txt'
    ready = '# observer_ready=true, paused=true를 관찰한 뒤 player 터미널에서 조작합니다.'
    if key == 'teleop':
        command = 'ros2 run turtlesim turtle_teleop_key' + (' --ros-args -r __ns:=/team' if prefix else '')
        goal = (
            '준비된 turtle1을 키보드 입력 노드로 앞으로 이동시키세요. 입력을 놓은 뒤 실제 정지를 관찰하고 입력 노드만 종료하세요.',
            '준비된 turtle1을 먼저 제자리 왼쪽 회전시킨 다음, 바뀐 방향으로 전진시키세요. 입력을 놓아 정지를 관찰한 뒤 입력 노드만 종료하세요.',
            '입력 노드의 제어 대상을 /team/turtle1로 맞춰 전진시키고 정지 관찰 후 입력 노드를 종료하세요. /guard/turtle1의 위치·방향은 계속 보존하세요. 노드 이름만 바꾸는 것과 제어 대상을 바꾸는 것을 구별하세요.',
        )[practice]
        keys = '# ←를 짧게 한 번 누르고 회전·정지를 관찰합니다.\n' if practice == 1 else ''
        solution = setup + '\n' + command + '\n' + status + '\n' + keys + '# ↑를 짧게 한 번 누릅니다. 이동 후 2초 이상 놓아 정지를 관찰합니다.\n# 입력 터미널에서 Ctrl+C로 종료합니다.'
    elif key == 'pause':
        goal = (
            'control_bag의 /turtle1/cmd_vel만 재생 대상으로 여세요. 처음 paused 상태에서 재개하여 실제 메시지를 받은 뒤 다시 일시정지하세요. messages가 더 늘지 않는 것을 관찰한 후 player를 종료하세요.',
            'control_bag에서 /turtle1/cmd_vel만 선택하세요. 처음부터 paused 상태를 유지하면서 첫 메시지 하나(linear.x=0.25, angular.z=0)만 조사한 뒤 player를 종료하세요. 자동 재생은 하지 마세요.',
            'control_bag의 혼합 기록에서 /turtle1/cmd_vel만 선택하세요. paused를 유지하며 첫 명령 하나를 조사하고, 그 뒤 다음 명령 하나를 따로 조사하세요. 순서는 linear.x=0.25, 0.26입니다. /training/notes는 발행하지 말고 player를 종료하세요.',
        )[practice]
        actions = ('# Space → messages 증가 관찰 → Space → paused=true·메시지 수 안정 확인',
                   '# → 한 번 → messages=1·paused=true 확인',
                   '# → 한 번 → messages=1·paused=true 확인 → → 한 번 → messages=2·paused=true 확인')[practice]
        solution = '\n'.join((setup, play, status, ready, actions, '# player 터미널에서 Ctrl+C로 종료합니다.'))
    else:
        goal = (
            'control_bag의 /turtle1/cmd_vel만 1.0배·paused로 여세요. 같은 player에서 paused를 유지하며 1.1배를 관찰한 뒤 1.0배로 되돌리세요. 실제 재생하여 메시지를 받은 다음 일시정지·안정 관찰 후 종료하세요.',
            'control_bag의 /turtle1/cmd_vel만 1.2배·paused로 여세요. 첫 메시지 하나를 조사한 뒤 같은 player를 재시작하지 않고 1.0배로 고치세요. paused를 유지하며 바로 다음 메시지 하나를 조사하고 종료하세요. 처음부터 다시 읽는 것은 복구가 아닙니다.',
            'control_bag의 /turtle1/cmd_vel만 1.0배·paused로 여세요. 같은 player를 paused 상태에서 1.2배로 올리고 다음 메시지 하나만 조사하세요. handoff.txt의 잘못된 linear_x 값을 실제 첫 메시지 값으로 고치세요. timing=1.2, linear_x=실제값, angular_z=실제값 세 줄을 남기고 종료하세요.',
        )[practice]
        actions = ('# ↑ → rate=1.1 확인 → ↓ → rate=1.0 확인\n# Space → messages 증가 확인 → Space → paused=true·메시지 수 안정 확인',
                   '# → → messages=1 확인 → ↓ → rate=1.1 확인 → ↓ → rate=1.0 확인\n# → → messages=2·paused=true 확인',
                   '# ↑ → rate=1.1 확인 → ↑ → rate=1.2 확인\n# → → messages=1·paused=true 확인')[practice]
        solution = '\n'.join((setup, play + (' --rate 1.2' if practice == 1 else ' --rate 1.0'), status, ready, actions,
                              '# player 터미널에서 Ctrl+C로 종료합니다.'))
        if practice == 2: solution += '\nprintf "timing=1.2\\nlinear_x=0.25\\nangular_z=0.0\\n" > handoff.txt'
    if key != 'teleop': goal += '\n각 단계의 paused·rate·messages를 관찰하고 다음 조작으로 넘어가세요. 마지막에는 paused=true, stable=true(선택 메시지 수 안정)를 확인한 뒤 player를 종료하세요.'
    goal += '\n관측 파일: 시작 폴더의 control-status.txt(자동 갱신). 준비된 turtlesim·keep.txt와 원본 bag을 보존하세요. 종료는 입력 노드/player만 하며 실습 환경 전체를 종료하지 마세요.'
    return Mission(kind, seed, start, start, start + '/handoff.txt', start, '', '', goal, solution,
                   practice=practice, review=dict(ros_controls=key, ros=[], domain=0, prefix=prefix))


def steps(unit, m):
    from learning_steps import LearningStep
    key = m.review['ros_controls']; parts = unit.explanation.split('\n')
    start = m.start
    status = f'# 새 터미널에서\ncd {start}\ncat control-status.txt'
    if key == 'teleop':
        titles = ['입력 노드와 터미널', '전진과 회전', '제어 대상 이름', '정지 관찰과 종료']
        commands = ['source /opt/ros/humble/setup.bash\nros2 run turtlesim turtle_teleop_key', '', '', status]
        observations = ['입력 안내가 보이는 터미널을 선택합니다.', '↑를 짧게 누르고 이동 후 놓습니다. 왼쪽 회전은 ←입니다.', '이번 예시는 기본 turtle1이며 /team 옵션을 추가하지 않습니다. 활용에서 이름공간을 바꿉니다.', '이동 뒤 2초 이상 기다리고 입력 터미널에서 Ctrl+C를 누릅니다.']
    else:
        titles = ['정지 상태로 열기', '관측 준비 확인' if key == 'pause' else '한 단계 올리기', '다음 조작' if key == 'pause' else '배율 되돌리기', '상태와 종료 구별']
        commands = ['source /opt/ros/humble/setup.bash\nros2 bag play control_bag --start-paused --topics /turtle1/cmd_vel --rate 1.0', status, '', status]
        observations = ['player를 실행한 터미널을 유지합니다.', 'observer_ready=true, paused=true를 확인합니다.' + (' ↑ 뒤 rate=1.1을 확인합니다.' if key == 'rate' else ''),
                        'Space로 재개해 messages 증가를 본 뒤 Space로 멈춥니다. →는 별도 활용 문제에서 연습합니다.' if key == 'pause' else '↓ 뒤 rate=1.0을 확인합니다. Space로 재개해 실제 messages 증가를 본 뒤 다시 Space로 멈춥니다.',
                        'paused=true이며 messages가 1초 이상 늘지 않으면 player 터미널에서 Ctrl+C로 종료합니다.']
    return tuple(LearningStep(t, p, c, o) for t, p, c, o in zip(titles, parts, commands, observations))
