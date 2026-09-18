"""ROS 2 Humble learning goals; shared descriptions, backend-specific execution."""
import random
from ros_guides import expanded_explanation, REPORT_KEYS


SPECS = (
    ('env', 'ROS 환경 활성화', 'source · printenv', '새 터미널마다 source /opt/ros/humble/setup.bash로 ROS 환경을 활성화합니다.\nprintenv ROS_DISTRO와 printenv ROS_VERSION으로 배포판과 버전을 확인합니다. 환경변수는 터미널마다 독립적입니다.'),
    ('overlay', '언더레이와 오버레이', 'source setup.bash · local_setup.bash', '/opt/ros/humble은 기본 언더레이입니다. 추가 작업공간은 오버레이입니다.\ninstall/local_setup.bash는 현재 작업공간만, install/setup.bash는 빌드 당시 연결한 언더레이도 함께 활성화합니다. 이 실습의 오버레이는 실제 colcon으로 빌드한 작은 패키지입니다.'),
    ('run', '노드를 실행하고 유지하기', 'ros2 run', 'ros2 run 패키지 실행파일로 프로그램을 실행합니다. 하나의 실행파일이 여러 노드를 만들 수도 있습니다.\nros2 run turtlesim turtlesim_node를 실행하면 터미널은 실행 중인 프로그램에 연결됩니다. 조회는 새 터미널에서 하고 Ctrl+C는 해당 작업을 중단합니다.'),
    ('nodes', '노드 목록과 연결 조사', 'ros2 node list · info', 'ros2 node list는 실행 중인 노드 이름을 보여 줍니다.\nros2 node info /이름은 발행·구독 토픽, 서비스, 액션을 조사합니다. 실행파일 이름과 노드 이름은 다를 수 있습니다.'),
    ('launch', '여러 노드와 이름공간', 'ros2 launch · namespace', 'ros2 launch 패키지 런치파일은 여러 노드를 함께 시작할 수 있습니다.\nros2 launch turtlesim multisim.launch.py는 서로 다른 이름공간의 turtlesim 노드를 만듭니다. 같은 노드 이름도 이름공간이 다르면 전체 경로가 달라집니다.'),
    ('topics', '토픽 목록·타입·연결 수', 'ros2 topic list -t · type · info', '토픽은 같은 타입의 메시지를 발행·구독하는 통신 경로입니다.\nros2 topic list -t는 타입을 함께 표시합니다. topic type 이름은 타입, topic info 이름은 타입과 발행자·구독자 수를 보여 줍니다. 목록에 있다고 항상 메시지가 흐르는 것은 아닙니다.'),
    ('interface', '메시지 구조 확인', 'ros2 interface show', 'ros2 interface show geometry_msgs/msg/Twist로 메시지 필드를 확인합니다.\nTwist의 linear.x는 전진 속도, angular.z는 평면 회전 속도에 사용됩니다. 메시지 타입 이름과 필드 경로를 확인하고 YAML로 값을 지정합니다.'),
    ('echo', '흐르는 메시지 관찰', 'ros2 topic echo · hz', 'ros2 topic echo /turtle1/pose는 수신한 메시지를 계속 출력합니다. Ctrl+C로 중단합니다.\nros2 topic hz /turtle1/pose는 수신 주기를 관찰합니다. 출력이 없으면 발행 노드와 토픽 이름·도메인·QoS를 조사합니다. 실측 주파수는 부하와 실행 환경의 영향을 받습니다.'),
    ('once', 'YAML 메시지 한 번 발행', 'ros2 topic pub --once', 'ros2 topic pub --once 토픽 타입 YAML로 메시지를 한 번 발행합니다.\n예: ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 1.0}, angular: {z: 0.0}}"\nHumble에서는 기본적으로 일치하는 구독자가 생길 때까지 기다립니다. 공백이 있는 YAML은 하나의 인자로 묶으세요.'),
    ('rate', '주기적 발행과 중단', 'ros2 topic pub --rate', 'ros2 topic pub --rate 2는 초당 2회 발행을 요청합니다. 계속 실행되므로 다른 터미널에서 관찰하고 Ctrl+C로 종료합니다.\n--once와 --rate는 실행 수명과 발행 주기를 다르게 지정합니다. 단일 발행 후 출력만 반복하는 것이 아닙니다.'),
    ('params', '파라미터 조회와 타입', 'ros2 param list · describe · get', '파라미터는 노드 내부의 설정 값이며 셸 환경변수와 다릅니다.\nros2 param list /turtlesim, describe /turtlesim background_r, get /turtlesim background_r로 목록·설명·값을 확인합니다. 노드별로 값·타입·읽기 전용 조건이 다릅니다.'),
    ('set', '파라미터 값 변경', 'ros2 param set', 'ros2 param set /turtlesim background_r 150으로 빨강 배경 성분을 변경합니다.\n정수·실수·문자열 등 타입이 맞아야 하며 노드가 변경을 거절할 수 있습니다. set의 성공 여부와 get으로 읽은 실제 값을 확인하세요.'),
    ('dump', '설정을 YAML로 저장', 'ros2 param dump · >', 'ros2 param dump /turtlesim은 설정을 YAML로 출력합니다.\nros2 param dump /turtlesim > turtle.yaml로 파일에 저장합니다. 이 파일은 해당 노드 경로와 ros__parameters 구조를 포함합니다.'),
    ('load', '저장한 설정 복원', 'ros2 param load', 'ros2 param load /turtlesim turtle.yaml로 파일의 설정을 읽습니다.\n일부 읽기 전용 파라미터는 복원이 거절될 수 있으므로 전체 성공이라고 가정하지 말고 실제 값을 조회하세요. 파일을 수정할 때 YAML 들여쓰기를 유지합니다.'),
    ('record', '토픽 기록 시작·종료', 'ros2 bag record -o', 'ros2 bag record -o session /turtle1/cmd_vel /turtle1/pose로 메시지를 기록합니다.\n-o 뒤는 결과 디렉터리 이름입니다. 다른 터미널에서 메시지를 발행하고 Ctrl+C로 기록을 정상 종료합니다. metadata.yaml과 저장 파일이 생깁니다.'),
    ('baginfo', '기록 데이터 조사', 'ros2 bag info', 'ros2 bag info 디렉터리로 토픽·타입·메시지 수·기간·저장 형식을 확인합니다.\n파일이 존재하는 것과 필요한 메시지가 실제로 기록된 것은 다릅니다. .db3는 SQLite 저장 파일이며 모든 bag의 형식이 반드시 .db3인 것은 아닙니다.'),
    ('play', '선택한 토픽 재생', 'ros2 bag play --topics', 'ros2 bag play 디렉터리 --topics /turtle1/cmd_vel로 선택한 토픽만 재생합니다.\n원래 발행 프로그램 대신 기록된 메시지를 발행합니다. 재생만으로 기록 당시 시스템 전체가 복원되는 것은 아닙니다. Space는 일시정지/재개, ↑/↓는 재생 속도 조정입니다.'),
    ('domain', '환경 차이로 연결되지 않는 노드', 'ROS_DOMAIN_ID · --ros-args -r', '같은 실습이라도 ROS_DOMAIN_ID가 다르면 서로 다른 ROS 도메인입니다. 노드를 시작하기 전에 각 터미널에서 설정합니다.\n--ros-args -r __node:=이름은 노드 이름을, -r __ns:=/이름공간은 이름공간을 변경합니다. 실행 중인 노드의 환경이 다른 터미널의 export로 바뀌지는 않습니다.'),
    ('service', '서비스 요청과 응답', 'ros2 service list · type · call', '서비스는 요청에 대한 응답을 받는 방식입니다. service list와 type으로 대상을 조사하고 interface show로 요청 필드를 확인합니다.\nros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 3.0, theta: 0.0, name: helper}"는 새 거북이를 생성합니다.'),
    ('action', '진행되는 작업 요청', 'ros2 action list · info · send_goal', '액션은 목표 요청, 진행 피드백, 최종 결과를 갖습니다.\nros2 action send_goal /turtle1/rotate_absolute turtlesim/action/RotateAbsolute "{theta: 1.57}" --feedback으로 회전을 요청하고 과정을 관찰합니다. 명령이 접수된 것과 목표가 성공한 것은 다릅니다.'),
)


# Application 1 reuses one earlier capability, in an order that leaves both
# observable goals satisfied. In particular, load must not be combined with
# set/dump: their required final background_r values differ (120 versus 150).
_APPLICATIONS = {
    'overlay': (('env', 'overlay'), '기본 ROS 환경과 추가 작업공간을 구별해 인계합니다. 배포판·버전과 추가 패키지의 설치 위치를 각각 확인하세요.'),
    'run': (('env', 'run'), '실행 환경을 기록한 뒤 노드를 시작합니다. 환경 보고서가 있어도 노드가 실행 중이라는 뜻은 아니므로 두 상태를 모두 확인하세요.'),
    'launch': (('overlay', 'launch'), '추가 패키지를 사용할 수 있는 터미널에서 다중 노드를 실행합니다. 오버레이의 설치 위치를 기록하고 두 이름공간의 노드를 유지하세요.'),
    'topics': (('nodes', 'topics'), '노드의 연결 정보와 토픽의 정보를 함께 조사합니다. 같은 통신 경로가 노드 보고서와 토픽 보고서에서 어떻게 나타나는지 비교하세요.'),
    'interface': (('topics', 'interface'), '실행 중인 토픽의 타입을 조사한 뒤 그 타입의 필드 구조를 확인합니다. 타입 이름만 저장한 결과와 메시지 구조를 저장한 결과를 구별하세요.'),
    'echo': (('topics', 'echo'), '목록에 존재하는 토픽과 실제 메시지가 흐르는 토픽을 구별합니다. 먼저 타입·연결 정보를 기록한 뒤 메시지 내용과 수신 주기를 관찰하세요.'),
    'once': (('interface', 'once'), '메시지 구조를 확인한 뒤 그 필드에 맞는 이동 메시지를 한 번 보냅니다. 구조를 남긴 파일과 실제 발행 결과가 모두 필요합니다.'),
    'rate': (('interface', 'rate'), '반복 발행할 메시지의 필드 구조를 먼저 기록합니다. 이어서 지정한 속도를 주기적으로 발행하고 작업을 종료하세요.'),
    'set': (('set', 'params'), '설정 변경을 마친 뒤 인계 보고서를 갱신합니다. 조회 파일에는 변경 전 값이 아니라 변경 후 실제 값이 담겨야 합니다.'),
    'dump': (('set', 'dump'), '빨강과 파랑 설정을 함께 조정한 뒤 현재 설정을 보관합니다. 저장을 위해 한 값을 준비하는 것과 두 설정을 동시에 유지하는 것을 구별하세요.'),
    'load': (('load', 'params'), '준비된 설정을 복원한 뒤 노드에서 읽은 값으로 복원 결과를 확인합니다. 입력 YAML을 읽는 것만으로 실제 노드의 값 조회를 대신하지 마세요.'),
    'record': (('dump', 'record'), '기록 당시의 설정과 시간에 따른 메시지를 따로 남깁니다. 먼저 현재 설정을 YAML에 보관하고, 이어서 이동 명령과 위치 메시지를 기록하세요.'),
    'play': (('baginfo', 'play'), '기록의 내용을 조사한 뒤 필요한 입력 토픽만 재생합니다. 조사 보고서를 남기고 원본 기록은 그대로 유지하세요.'),
    'domain': (('env', 'domain'), 'ROS 배포판·버전과 통신 도메인을 구별합니다. 이 터미널의 환경을 보고서로 남긴 뒤 지정한 도메인과 이름으로 노드를 실행하세요.'),
    'service': (('params', 'service'), '노드의 설정 조사와 새 거북이를 만드는 요청을 구별합니다. 현재 설정을 기록한 뒤 서비스를 요청하고 기존 거북이는 유지하세요.'),
    'action': (('service', 'action'), '새 거북이를 만드는 서비스와 시간이 걸리는 회전 액션을 차례로 수행합니다. helper를 만든 뒤 turtle1에 회전을 요청해 두 요청의 대상을 구별하세요.'),
}

# These are intentionally incorrect learner-owned reports, not fabricated ROS
# command output. The guest seeds them; the learner replaces them by querying
# the real environment/node/bag. Never apply this metadata to examples/reviews.
_STALE_REPORTS = {
    'env': {'distro.txt': 'foxy\n', 'version.txt': '1\n'},
    'nodes': {
        'nodes.txt': '/retired_node\n',
        'node-info.txt': '/retired_node\n  Subscribers:\n    /retired/input: std_msgs/msg/String\n  Publishers:\n    /retired/output: std_msgs/msg/String\n',
    },
    'params': {
        'params.txt': '  retired_setting\n',
        'description.txt': 'Parameter name: retired_setting\n  Type: string\n',
        'value.txt': 'Integer value is: 999\n',
    },
    'baginfo': {
        'bag-info.txt': 'Files: missing.db3\nStorage id: sqlite3\nMessages: 0\nTopic information: no recorded topics\n',
    },
}


def units(Unit):
    return tuple(Unit('ros_' + key, 7 + i // 10, title, commands, expanded_explanation(key, explanation),
                      'F3에서 개념과 예시를 확인하고 실행 상태를 조사하세요.')
                 for i, (key, title, commands, explanation) in enumerate(SPECS))


def make_ros_mission(kind, seed=None, practice=0):
    from missions import Mission
    seed = seed if seed is not None else random.SystemRandom().randrange(1000, 9999)
    key = kind.removeprefix('ros_')
    start = f'/home/learner/ros/session{seed}'
    setup = 'source /opt/ros/humble/setup.bash'
    ready_node = 'ros2 run turtlesim turtlesim_node'
    velocity = '"{linear: {x: 1.0}, angular: {z: 0.5}}"'
    publish = 'ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist ' + velocity
    rate = 'ros2 topic pub --rate 2 /turtle1/cmd_vel geometry_msgs/msg/Twist ' + velocity
    node = 'turtle' + str(seed)
    goals = {
        'env': ('이 터미널에서 ROS Humble 환경을 활성화하고 ROS_DISTRO와 ROS_VERSION을 각각 distro.txt와 version.txt에 저장하세요.', setup + '\nprintenv ROS_DISTRO > distro.txt\nprintenv ROS_VERSION > version.txt'),
        'overlay': ('준비된 ~/training_ws 오버레이를 활성화하고 shellground_demo 패키지의 설치 경로를 package.txt에 저장하세요.', setup + '\nsource ~/training_ws/install/local_setup.bash\nros2 pkg prefix shellground_demo > package.txt'),
        'run': ('TurtleSim의 기본 노드를 실행 상태로 유지하고 노드가 존재하는지 확인하세요.', setup + '\n' + ready_node),
        'nodes': ('준비된 TurtleSim 노드의 목록을 nodes.txt에, /turtlesim의 연결 정보를 node-info.txt에 저장하세요.', setup + '\nros2 node list > nodes.txt\nros2 node info /turtlesim > node-info.txt'),
        'launch': ('turtlesim의 multisim.launch.py를 실행해 turtlesim1과 turtlesim2 이름공간의 노드를 함께 유지하세요.', setup + '\nros2 launch turtlesim multisim.launch.py'),
        'topics': ('토픽과 타입 목록을 topics.txt에, /turtle1/cmd_vel의 타입을 type.txt에, 연결 정보를 topic-info.txt에 저장하세요.', setup + '\nros2 topic list -t > topics.txt\nros2 topic type /turtle1/cmd_vel > type.txt\nros2 topic info /turtle1/cmd_vel > topic-info.txt'),
        'interface': ('geometry_msgs/msg/Twist의 메시지 구조를 twist.txt에 저장하세요. linear와 angular의 필드를 확인하세요.', setup + '\nros2 interface show geometry_msgs/msg/Twist > twist.txt'),
        'echo': ('/turtle1/pose 메시지를 pose.txt에, 수신 주기 관찰 결과를 hz.txt에 저장하세요. 관찰을 마치면 두 수신 작업을 종료하세요.', setup + '\nros2 topic echo /turtle1/pose > pose.txt\n# 몇 개 수신한 뒤 Ctrl+C를 눌러 프롬프트로 돌아옵니다.\nros2 topic hz /turtle1/pose > hz.txt\n# 통계가 쌓인 뒤 Ctrl+C로 종료하고 cat으로 두 파일을 확인합니다.'),
        'once': ('/turtle1/cmd_vel에 전진 속도 1.0, 회전 속도 0.5의 Twist 메시지를 발행하세요. 거북이의 반응을 확인하세요.', setup + '\n' + publish),
        'rate': ('/turtle1/cmd_vel에 전진 속도 1.0, 회전 속도 0.5를 초당 2회로 3초 이상 발행한 뒤 발행을 중단하세요.', setup + '\n' + rate),
        'params': ('/turtlesim의 파라미터 목록을 params.txt에, background_r의 설명과 값을 각각 description.txt와 value.txt에 저장하세요.', setup + '\nros2 param list /turtlesim > params.txt\nros2 param describe /turtlesim background_r > description.txt\nros2 param get /turtlesim background_r > value.txt'),
        'set': ('/turtlesim의 배경 빨강 성분을 정수 150으로, 파랑 성분을 정수 80으로 바꾸세요. 실제 화면과 값을 확인하세요.', setup + '\nros2 param set /turtlesim background_r 150\nros2 param set /turtlesim background_b 80'),
        'dump': ('/turtlesim의 빨강 성분을 150으로 바꾼 뒤 현재 파라미터를 turtle.yaml에 보관하세요.', setup + '\nros2 param set /turtlesim background_r 150\nros2 param dump /turtlesim > turtle.yaml'),
        'load': ('준비된 restore.yaml의 설정을 /turtlesim에 복원하세요. 빨강 120, 파랑 90이 실제 값이어야 합니다. 파일은 보존하세요.', setup + '\nros2 param load /turtlesim restore.yaml\nros2 param get /turtlesim background_r'),
        'record': ('/turtle1/cmd_vel과 /turtle1/pose를 capture 디렉터리에 기록하세요. 이동 메시지를 발행한 뒤 기록을 종료하세요. 두 토픽 모두 실제 메시지가 있어야 합니다.', '# 터미널 A: 기록을 시작하고 pose 구독 로그를 확인합니다.\n' + setup + '\nros2 bag record -o capture /turtle1/cmd_vel /turtle1/pose\n# 터미널 B: 환경 활성화 후 이동 메시지를 계속 발행합니다.\n' + setup + '\n' + rate + '\n# 터미널 A의 cmd_vel 구독 로그를 확인한 뒤 몇 개 더 발행합니다.\n# 터미널 B에서 Ctrl+C로 발행을 중단합니다.\n# 터미널 A로 돌아와 Ctrl+C로 기록을 종료합니다.\nros2 bag info capture'),
        'baginfo': ('준비된 sample_bag 기록의 정보를 bag-info.txt에 저장하세요. 토픽·타입·메시지 수를 확인하고 원본은 보존하세요.', setup + '\nros2 bag info sample_bag > bag-info.txt'),
        'play': ('sample_bag에서 /turtle1/cmd_vel만 재생하세요. 재생이 끝난 뒤 거북이가 움직인 상태를 확인하세요. (준비된 기록의 이동 메시지 8개 수신)', setup + '\nros2 bag play sample_bag --delay 2 --topics /turtle1/cmd_vel'),
        'domain': (f'ROS 도메인 42에서 TurtleSim을 /team/{node} 이름으로 실행하세요. 노드 조회도 같은 도메인에서 수행하세요.', setup + f'\nexport ROS_DOMAIN_ID=42\nros2 run turtlesim turtlesim_node --ros-args -r __node:={node} -r __ns:=/team'),
        'service': ('서비스를 조사하고 helper라는 새 거북이를 x=2.0, y=3.0, theta=0.0에 생성하세요. 기존 turtle1은 유지하세요.', setup + '\nros2 service list\nros2 service type /spawn\nros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 3.0, theta: 0.0, name: helper}"'),
        'action': ('turtle1에 절대 각도 1.57 라디안 회전 목표를 요청하고 완료 결과를 확인하세요. 기존 노드는 유지하세요.', setup + '\nros2 action list -t\nros2 action send_goal /turtle1/rotate_absolute turtlesim/action/RotateAbsolute "{theta: 1.57}" --feedback'),
    }
    stale_reports = {}
    if key.startswith('review'):
        end = int(key[6:])
        components = {45: ['env', 'overlay', 'launch'], 50: ['topics', 'interface', 'rate'],
                      55: ['set', 'dump', 'record'], 60: ['baginfo', 'play', 'service', 'action']}[end]
        prompt = '이전 5개 단원의 기능을 조합하세요.\n\n' + '\n\n'.join(goals[c][0] for c in components)
        solution = '\n\n'.join(goals[c][1] for c in components)
    elif practice == 1:
        if key in _APPLICATIONS:
            ordered, context = _APPLICATIONS[key]
            components = list(ordered)
            prompt = context + '\n\n' + '\n\n'.join(
                f'{i}. {goals[c][0]}' for i, c in enumerate(components, 1))
            solution = '\n\n'.join(goals[c][1] for c in components)
        else:
            components = [key]
            stale_reports = dict(_STALE_REPORTS[key])
            initial = '\n\n'.join(name + '의 준비된 잘못된 내용:\n' + text.rstrip('\n')
                                    for name, text in stale_reports.items())
            prompt = ('이전 실습에서 남은 보고서가 현재 실행 상태와 맞지 않습니다. '
                      '아래 파일을 실제 조회 결과로 새로 저장해 바로잡으세요. '
                      '틀린 보고서에 맞추려고 환경·노드·원본 기록을 바꾸지 마세요.\n\n'
                      + initial + '\n\n수정 후 목표:\n' + goals[key][0])
            solution = goals[key][1]
    else:
        components = [key]
        prompt, solution = goals[key]
    handoff = ''
    if practice == 2 and not key.startswith('review'):
        if key in REPORT_KEYS:
            handoff = 'reports'
            prompt += '\n추가 인계: reports 폴더를 만들고 현재 폴더의 .txt/.yaml 결과 파일을 복사해 보관하세요. 원본도 유지하세요.'
            solution += '\nmkdir -p reports\nfind . -maxdepth 1 -type f \\( -name "*.txt" -o -name "*.yaml" \\) -exec cp {} reports/ \\;'
        else:
            handoff = 'nodes'
            prompt += '\n추가 조사: 작업 후 노드 목록을 nodes-after.txt에 저장하세요. 도메인과 터미널 환경에 주의하세요.'
            solution += '\n# 실행 작업과 별도의, 같은 도메인 터미널에서\nros2 node list > nodes-after.txt'
    review = {'ros': components, 'domain': 42 if key == 'domain' else 0, 'handoff': handoff}
    if stale_reports:
        review['stale_reports'] = stale_reports
    return Mission(kind, seed, start, start + '/source', start + '/result.txt', start + '/target', '', '',
                   prompt, solution, practice=practice, review=review)
