"""Small, sequential learning tasks over one shared lab; not new completion IDs.

The full lesson remains the reference (F3). These are deliberately authored
concept-sized tasks, not paragraphs paginated by character count. Navigation
does not execute commands, recreate a lab, or certify a learner's competence.
"""
from dataclasses import dataclass
import shlex


@dataclass(frozen=True)
class LearningStep:
    title: str
    explanation: str
    commands: str
    observation: str

    @property
    def text(self):
        example = '\n\n직접 해볼 명령:\n' + self.commands if self.commands else ''
        return self.explanation + example + '\n확인할 것: ' + self.observation


def learning_steps(unit, mode, mission=None):
    from course_topics import topic_of
    from missions import make_mission
    from real_lessons import adapt_real_mission
    if topic_of(unit) == '리눅스':
        if mode != 'real': return ()
        from linux_learning import steps
        return steps(unit, adapt_real_mission(mission or make_mission(unit.key, 4242)))
    m = mission or make_mission(unit.key, 4242)
    if mode == 'real': m = adapt_real_mission(m)
    if unit.key.startswith('ros_controls_'):
        from ros_controls_course import steps
        return steps(unit, m)
    if unit.key.startswith('docker_runtime_'):
        from docker_runtime_course import steps
        return steps(unit, m)
    if unit.key.startswith('docker_sessions_'):
        from docker_sessions_course import steps
        return steps(unit, m)
    return ros_steps(m) if unit.key.startswith('ros_') else docker_steps(m, mode)


def ros_steps(m):
    from ros_guides import REPORT_KEYS
    key, seed = m.kind.removeprefix('ros_'), m.seed
    setup = 'source /opt/ros/humble/setup.bash'
    start = m.start
    velocity = '"{linear: {x: 1.0}, angular: {z: 0.5}}"'
    pub = 'ros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist ' + velocity
    steps = []
    def add(title, why, commands, check):
        steps.append(LearningStep(title, why, commands, check))
    if key == 'env':
        add('현재 셸에 ROS 환경 적용', 'source는 설치가 아니라 현재 셸의 패키지 검색 경로를 설정합니다. /opt/ros/humble은 실습 Linux의 설치 위치, setup.bash는 Bash용 설정입니다. bash로 별도 실행하는 것과 다릅니다.', setup, '성공해도 출력이 없을 수 있습니다. 오류가 없으면 다음 단계에서 값을 확인합니다.')
        add('환경변수로 활성화 확인', 'ROS_DISTRO는 배포판 이름, ROS_VERSION은 ROS 세대입니다. 버전 번호 2와 배포판 이름 humble을 구별합니다.', 'printenv ROS_DISTRO\nprintenv ROS_VERSION', '각각 humble과 2가 나오는지 봅니다. 새 터미널에는 다시 source가 필요합니다.')
        add('조회 결과를 파일로 저장', '>는 ROS 옵션이 아니라 셸의 출력 저장입니다. 기존 파일을 덮어씁니다. 파일명은 현재 폴더 기준입니다.', 'pwd\nprintenv ROS_DISTRO > distro.txt\nprintenv ROS_VERSION > version.txt\ncat distro.txt version.txt', '문제의 시작 폴더에 두 실제 조회 결과가 남아야 합니다. 값을 직접 적는 것과 환경 설정은 다릅니다.')
    elif key == 'overlay':
        add('기본 환경 위에 작업공간 추가', 'underlay는 기본 설치, overlay는 그 위에 추가하는 작업공간입니다. 준비된 ~/training_ws/install/local_setup.bash는 이 작업공간만 추가합니다. setup.bash는 연결된 underlay도 불러옵니다.', setup + '\nsource ~/training_ws/install/local_setup.bash', 'cd만 해서는 활성화되지 않습니다. 여기서는 이미 빌드된 작업공간을 사용합니다.')
        add('실제로 선택된 패키지 위치', 'pkg prefix는 패키지의 설치 위치입니다. 현재 폴더를 보는 pwd와 다릅니다. 설치 결과는 작업공간의 install 아래에 있습니다.', 'ros2 pkg prefix shellground_demo\nros2 pkg prefix shellground_demo > package.txt\ncat package.txt', 'Package not found이면 현재 터미널에서 source한 순서와 경로를 확인합니다.')
    elif key == 'run':
        add('패키지와 실행파일 구분', 'turtlesim은 패키지입니다. 그 안에 여러 실행파일이 있습니다. 아직 노드를 실행하지 않고 실행 가능한 이름을 조사합니다.', setup + '\nros2 pkg executables turtlesim', 'turtlesim_node를 찾습니다. 실행파일 이름과 실행 뒤의 노드 이름은 다를 수 있습니다.')
        add('노드 하나 실행', 'run 뒤에는 패키지와 실행파일을 넣습니다. 이 프로그램은 계속 실행되므로 프롬프트가 돌아오지 않는 것이 정상입니다.', 'ros2 run turtlesim turtlesim_node', '실제 Linux 화면의 거북이를 관찰합니다. 이 터미널을 유지한 채 다음 단계로 갑니다.')
        add('새 터미널에서 살아 있는지 조회', '앱의 새 터미널을 여세요. 파일/노드는 공유하지만 환경변수는 독립적이므로 여기서도 source합니다. 실행 터미널을 종료하지 않습니다.', setup + '\nros2 node list', '/turtlesim이 보이는지 확인합니다. 노드 이름은 turtlesim_node가 아닙니다.')
    elif key == 'nodes':
        add('노드 목록부터 보기', 'node list는 현재 발견된 노드 이름을 보여 줍니다. /turtlesim은 ROS 이름이며 Linux 디렉터리가 아닙니다. 이 단원의 노드는 미리 준비되어 있습니다.', setup + '\nros2 node list\nros2 node list > nodes.txt', '/turtlesim이 목록에 있는지 확인합니다. 조회용 노드 등이 더 보일 수 있어 총 개수를 외울 필요는 없습니다.')
        add('노드 하나의 연결 조사', 'info에는 실제 전체 노드 이름을 넣습니다. Publishers는 내보내는 토픽, Subscribers는 받는 토픽입니다.', 'ros2 node info /turtlesim\nros2 node info /turtlesim > node-info.txt', '발행/구독을 구별합니다. 목록 파일과 연결 정보 파일은 서로 다른 결과입니다.')
    elif key == 'launch':
        add('런치 파일로 함께 실행', 'run은 실행파일, launch는 시작 구성을 담은 런치 파일을 지정합니다. multisim.launch.py는 같은 프로그램을 두 이름공간에서 실행합니다.', setup + '\nros2 launch turtlesim multisim.launch.py', 'launch 터미널을 유지합니다. 하나의 기본 /turtlesim만 실행하는 것과 다릅니다.')
        add('이름공간으로 두 노드 구분', '새 터미널을 여세요. 이름공간은 ROS 이름 앞의 구분자이며 Linux 폴더나 통신 격리 장치가 아닙니다.', setup + '\nros2 node list', '/turtlesim1/turtlesim과 /turtlesim2/turtlesim을 찾습니다.')
    elif key == 'topics':
        add('토픽 이름 목록', '토픽은 메시지 흐름의 이름입니다. 이동 명령 /turtle1/cmd_vel과 위치 관측 /turtle1/pose를 먼저 구별합니다.', setup + '\nros2 topic list', '노드 이름 /turtlesim과 토픽 이름은 다릅니다.')
        add('이름과 메시지 타입 연결', '-t는 목록에 타입도 표시합니다. type 뒤에 토픽을 넣으면 그 타입만 조회합니다.', 'ros2 topic list -t > topics.txt\nros2 topic type /turtle1/cmd_vel > type.txt\ncat topics.txt type.txt', 'cmd_vel의 타입이 geometry_msgs/msg/Twist인지 확인합니다.')
        add('발행자·구독자 수 조사', 'info는 토픽에 연결된 발행자와 구독자 수를 보여 줍니다. --verbose(-v)는 연결 노드와 QoS까지 자세히 표시합니다.', 'ros2 topic info /turtle1/cmd_vel > topic-info.txt\ncat topic-info.txt', '구독자만 있어도 토픽은 보일 수 있습니다. 존재와 메시지가 흐르는 것은 다릅니다.')
    elif key == 'interface':
        add('타입 이름을 구조로 풀어 읽기', 'geometry_msgs는 패키지, msg는 메시지 정의, Twist는 타입 이름입니다. show는 현재 측정값이 아니라 필드 설계도를 읽습니다.', setup + '\nros2 interface show geometry_msgs/msg/Twist', 'linear와 angular에 각각 x/y/z 실수 성분이 있는지 봅니다.')
        add('중첩 필드와 출력 저장', '평면 TurtleSim은 linear.x를 전진 속도, angular.z를 회전 속도로 사용합니다. 회전 속도와 목표 각도는 다릅니다. YAML도 이 중첩 구조를 따라 씁니다.', 'ros2 interface show geometry_msgs/msg/Twist > twist.txt\ncat twist.txt', 'linear/angular와 그 안의 필드를 설명할 수 있는지 확인합니다. 실제 값 관찰은 echo의 역할입니다.')
    elif key == 'echo':
        add('내용을 수신하고 종료', 'echo는 메시지를 계속 받습니다. >로 저장하면 화면이 조용할 수 있습니다. 몇 개 수신한 뒤 이 작업에 Ctrl+C를 보내 프롬프트로 돌아오세요.', setup + '\nros2 topic echo /turtle1/pose > pose.txt', '종료 후 cat pose.txt로 x/y/theta와 YAML 구분 ---를 봅니다. 아직 hz는 실행하지 않습니다.')
        add('수신 빈도를 관찰하고 종료', 'hz의 average rate는 초당 수신 횟수, min/max는 관측 간격입니다. 통계가 쌓일 시간을 둔 뒤 Ctrl+C로 종료하세요.', 'ros2 topic hz /turtle1/pose > hz.txt', '종료 후 cat hz.txt로 통계를 확인합니다. 두 연속 수신 명령을 한꺼번에 붙여 넣지 않습니다.')
    elif key in ('once', 'rate'):
        add('발행할 데이터부터 해석', 'Twist는 linear와 angular를 갖습니다. YAML 전체를 따옴표로 묶고 콜론 뒤 공백을 유지합니다. linear.x=1.0과 angular.z=0.5만 지정하면 나머지 성분은 기본값 0입니다.', setup + '\nros2 interface show geometry_msgs/msg/Twist\nros2 topic info /turtle1/cmd_vel', '타입과 수신 노드를 확인합니다. {linear: {x: 1.0}, angular: {z: 0.5}}가 어떤 필드를 채우는지 읽어 봅니다.')
        if key == 'once':
            add('한 번만 발행', '--once(-1)는 한 메시지를 보내고 종료합니다. Humble은 기본적으로 일치하는 구독자 하나를 기다립니다. -w는 기다릴 구독자 수입니다.', pub, 'Waiting for ...가 계속되면 노드·타입·도메인을 확인합니다. 발행 출력과 실제 거북이 반응을 함께 봅니다.')
        else:
            add('2 Hz로 반복 발행', '--rate 2(-r 2)는 초당 2회, 약 0.5초 간격입니다. 2초마다 한 번이 아닙니다. 이 터미널에서 발행을 유지한 채 다음 단계로 갑니다.', 'ros2 topic pub --rate 2 /turtle1/cmd_vel geometry_msgs/msg/Twist ' + velocity, '거북이 반응을 봅니다. --once와 실행 수명이 다릅니다. 정해진 횟수만 보내는 옵션은 --times입니다.')
            add('다른 터미널에서 주기 확인', '새 터미널에서 관찰합니다. 3초 이상 발행한 뒤 발행 터미널의 Ctrl+C로 발행을 멈추고, 관찰 터미널의 hz도 따로 종료하세요.', setup + '\nros2 topic hz /turtle1/cmd_vel', '약 2 Hz인지 확인합니다. 관찰을 종료하는 것과 발행을 종료하는 것은 다릅니다. TurtleSim 노드는 유지합니다.')
    elif key == 'params':
        add('설정 이름 목록', '파라미터는 노드별 설정입니다. 셸 환경변수나 토픽 메시지와 다릅니다. 먼저 노드에 어떤 설정이 있는지 조사합니다.', setup + '\nros2 param list /turtlesim\nros2 param list /turtlesim > params.txt', 'background_r/g/b를 찾습니다. 다른 노드는 같은 설정을 갖지 않을 수 있습니다.')
        add('타입과 제약 조사', 'describe는 설명·자료형·읽기 전용 같은 제약을 조사합니다. 이름이 목록에 있다고 반드시 변경 가능한 것은 아닙니다.', 'ros2 param describe /turtlesim background_r\nros2 param describe /turtlesim background_r > description.txt', 'background_r이 정수형이라는 점을 확인합니다.')
        add('현재 값 조회', 'get은 현재 값과 타입을 읽습니다. 노드 이름 뒤에 파라미터 이름을 지정합니다.', 'ros2 param get /turtlesim background_r\nros2 param get /turtlesim background_r > value.txt', 'Integer value is: ...를 읽습니다. 설명과 값은 다른 조사입니다.')
    elif key == 'set':
        add('한 설정만 바꾸기', 'set의 순서는 노드 → 설정 이름 → 새 값입니다. 150은 정수, 150.0은 실수이므로 타입을 구별합니다.', setup + '\nros2 param set /turtlesim background_r 150\nros2 param get /turtlesim background_r', '성공 응답과 실제 읽은 값, 화면의 배경을 함께 확인합니다.')
        add('다른 설정에도 적용', 'background_b는 파랑 성분입니다. 실행 중 변경은 영구 기본값을 고치는 것이 아니며, 이후 dump/load로 보관·복원을 배웁니다.', 'ros2 param set /turtlesim background_b 80\nros2 param get /turtlesim background_b', '빨강 150도 유지되어야 합니다. 하나를 바꿨다고 다른 설정이 자동 변경되지는 않습니다.')
    elif key == 'dump':
        add('저장할 현재 값 준비', 'dump는 저장 순간의 설정을 읽습니다. 원하는 값으로 바꾼 뒤 저장해야 합니다.', setup + '\nros2 param set /turtlesim background_r 150\nros2 param get /turtlesim background_r', '실제 값 150을 확인한 뒤 다음 단계로 갑니다.')
        add('YAML 구조를 파일로 보관', '>는 표준출력을 파일로 저장합니다. YAML은 들여쓰기로 구조를 표현하며 파일명은 노드 이름과 달라도 됩니다.', 'ros2 param dump /turtlesim > turtle.yaml\ncat turtle.yaml', '/turtlesim → ros__parameters → background_r의 구조와 값을 확인합니다. 거북이 위치나 실행 메모리 전체를 저장하는 것은 아닙니다.')
    elif key == 'load':
        add('복원할 입력 파일 먼저 읽기', 'restore.yaml은 준비된 입력입니다. 현재 폴더 기준으로 읽으며 원본은 보존합니다. 파일의 노드 이름과 ros__parameters 구조를 확인합니다.', setup + '\ncat restore.yaml', 'background_r=120과 background_b=90, 들여쓰기를 확인합니다. 아직 노드에 적용된 것은 아닙니다.')
        add('실행 중 노드에 적용', 'load 뒤에는 대상 노드와 파일을 넣습니다. 읽기 전용 항목은 실패할 수 있어 항목별 응답을 봐야 합니다.', 'ros2 param load /turtlesim restore.yaml', '원하는 항목까지 실패했는데 단순 경고로 넘기지 않습니다.')
        add('파일이 아니라 실제 값 검증', '노드가 실제로 값을 받아들였는지 get으로 각각 다시 확인합니다. 시작부터 설정하려면 run 뒤 --ros-args --params-file을 쓰는 별도 방식이 있습니다.', 'ros2 param get /turtlesim background_r\nros2 param get /turtlesim background_b', '120과 90이어야 합니다. 파일을 다시 읽는 것으로 노드 값 조회를 대신하지 않습니다.')
    elif key == 'record':
        add('기록 시작과 토픽 선택', 'bag은 시간에 따른 메시지를 기록합니다. -o 뒤 capture는 결과 폴더, 뒤의 이름들은 선택할 토픽입니다. -a는 모든 토픽 기록이므로 여기서는 쓰지 않습니다.', setup + '\nros2 bag record -o capture /turtle1/cmd_vel /turtle1/pose', '먼저 pose 구독 로그를 확인하고 기록 터미널을 유지합니다. 아직 발행하지 않은 cmd_vel의 구독 로그까지 기다리지 않습니다. 기존 capture가 있으면 먼저 내용을 확인합니다.')
        add('새 터미널에서 기록할 입력 만들기', '앱의 새 터미널을 열고 source합니다. 앞서 배운 --rate 2로 계속 발행하여 기록기가 발행자를 발견할 시간을 줍니다. --once의 한 메시지는 구독 준비 전에 지나갈 수 있습니다.', setup + '\nros2 topic pub --rate 2 /turtle1/cmd_vel geometry_msgs/msg/Twist ' + velocity, '기록 터미널의 cmd_vel 구독 로그를 확인한 뒤 몇 개 더 발행합니다. 두 터미널은 동시에 실행 중이어야 합니다.')
        add('정상 종료하고 기록 확인', '발행 터미널에서 Ctrl+C로 중단한 뒤 기록 터미널에서도 Ctrl+C로 종료하여 메타데이터를 마무리합니다. 그런 다음 아래 명령을 실행합니다.', 'ros2 bag info capture', 'metadata.yaml과 저장 데이터가 있고 두 토픽 모두 메시지 수가 0보다 커야 합니다.')
    elif key == 'baginfo':
        add('기록 폴더와 저장 파일', 'sample_bag은 준비된 입력 폴더입니다. metadata.yaml과 데이터 파일이 함께 한 기록을 이룹니다. 파일 확장자를 바꾼다고 저장 형식이 바뀌지 않습니다.', setup + '\nls sample_bag', '원본을 수정하지 않고 구성만 확인합니다.')
        add('토픽별 메시지 수와 기간', 'info의 Files는 저장 파일, Storage id는 방식, Duration은 기록 기간, Messages는 메시지 수입니다. 토픽별 Type/Count를 따로 읽습니다.', 'ros2 bag info sample_bag\nros2 bag info sample_bag > bag-info.txt', '전체 메시지가 많아도 필요한 토픽의 Count가 0이면 부족한 기록입니다. info 자체는 재생하지 않습니다.')
    elif key == 'play':
        add('재생할 토픽 고르기', '기록에는 명령과 관측이 함께 있을 수 있습니다. 이미 실행 중인 수신 노드에 이동 입력만 보낼 것이므로 먼저 내용부터 확인합니다.', setup + '\nros2 bag info sample_bag', '/turtle1/cmd_vel과 /turtle1/pose의 역할을 구분합니다.')
        add('이동 명령만 재생', '--topics 뒤의 토픽만 발행합니다. 생략하면 다른 기록 토픽도 발행할 수 있습니다. --delay 2는 재생기가 준비된 뒤 첫 발행까지 2초 기다려 DDS 연결 시간을 줍니다. 다른 이동 발행자는 먼저 중단하되 TurtleSim은 유지합니다.', 'ros2 bag play sample_bag --delay 2 --topics /turtle1/cmd_vel', '끝날 때까지 반응을 봅니다. 준비된 이동 메시지는 8개입니다. 수신이 부족하면 대기 시간을 늘려 다시 재생할 수 있습니다. Space는 일시정지/재개, ↑/↓는 속도 조절입니다. bag은 노드나 시작 위치까지 복원하지 않습니다.')
    elif key == 'domain':
        add('실행 전에 도메인 정하기', '도메인은 서로 발견할 ROS 집단입니다. 42는 이 실습의 선택값이며 포트 번호나 항상 쓰는 값이 아닙니다. 이미 실행된 노드의 환경은 바뀌지 않습니다.', setup + '\nexport ROS_DOMAIN_ID=42\nprintenv ROS_DOMAIN_ID', '새로 실행할 프로그램이 42를 물려받도록 현재 셸에 설정합니다.')
        add('노드 이름과 이름공간 지정', '--ros-args는 ROS 인자의 시작, -r은 이름 재지정입니다. __node는 이름, __ns는 이름공간입니다. :=와 =를 혼동하지 마세요.', f'ros2 run turtlesim turtlesim_node --ros-args -r __node:=turtle{seed} -r __ns:=/team', f'실행 터미널을 유지합니다. 전체 이름은 /team/turtle{seed}입니다.')
        add('조회 터미널도 같은 도메인', '새 터미널은 환경이 독립적입니다. source와 export를 이곳에서도 해야 합니다. 이름공간만 같고 도메인이 다르면 연결되지 않습니다.', setup + '\nexport ROS_DOMAIN_ID=42\nros2 node list', f'/team/turtle{seed}를 찾습니다. 도메인/이름공간은 인증이나 보안 경계가 아닙니다.')
    elif key == 'service':
        add('서비스 이름과 타입 조사', '서비스는 요청에 대한 응답입니다. 토픽의 연속 메시지와 다릅니다. /spawn은 새 거북이 생성을 처리합니다.', setup + '\nros2 service list\nros2 service type /spawn', '서비스 이름 /spawn과 타입 turtlesim/srv/Spawn을 구별합니다.')
        add('요청과 응답 구조 읽기', 'srv는 서비스 정의입니다. interface show의 --- 앞은 요청, 뒤는 응답입니다. x/y는 위치, theta는 라디안 방향, name은 새 거북이 이름입니다.', 'ros2 interface show turtlesim/srv/Spawn', '필드 이름을 확인한 뒤 YAML을 작성합니다. 없는 필드를 추측해 넣지 않습니다.')
        add('한 번 요청하고 응답 확인', 'call 뒤에는 이름 → 타입 → 따옴표로 묶은 YAML 요청을 넣습니다. 같은 이름을 재요청하면 충돌할 수 있습니다.', 'ros2 service call /spawn turtlesim/srv/Spawn "{x: 2.0, y: 3.0, theta: 0.0, name: helper}"', '응답의 helper와 새 거북이를 봅니다. 별도 helper 노드를 만드는 것이 아니라 /turtlesim이 거북이를 추가합니다. 기존 turtle1은 유지합니다.')
    elif key == 'action':
        add('액션 이름과 서버 조사', '액션은 시간이 걸리는 작업의 목표·피드백·결과를 연결합니다. 서비스의 한 응답과 달리 진행을 관찰할 수 있습니다.', setup + '\nros2 action list -t\nros2 action info /turtle1/rotate_absolute', '액션 이름과 타입, 실행할 서버가 있는지 확인합니다.')
        add('목표·결과·피드백 구조', 'action 정의의 ---는 목표/결과/피드백을 나눕니다. theta=1.57은 약 90도의 절대 방향이지 회전 속도나 추가 회전량이 아닙니다.', 'ros2 interface show turtlesim/action/RotateAbsolute', '목표 theta, 결과 delta, 피드백 remaining의 역할을 구별합니다.')
        add('목표 접수부터 완료까지 관찰', '--feedback은 중간 피드백도 표시합니다. 다른 이동 발행이 방해하지 않는지 확인합니다.', 'ros2 action send_goal /turtle1/rotate_absolute turtlesim/action/RotateAbsolute "{theta: 1.57}" --feedback', 'Goal accepted는 접수일 뿐입니다. SUCCEEDED와 실제 방향까지 확인합니다. Ctrl+C로 클라이언트를 닫는 것이 완료/취소 확인을 대신하지 않습니다.')
    else:
        raise ValueError('Missing ROS learning steps: ' + key)
    if key in REPORT_KEYS:
        # Small concrete copies first; the general find form remains in F3.
        files = {'env': ['distro.txt', 'version.txt'], 'overlay': ['package.txt'],
                 'nodes': ['nodes.txt', 'node-info.txt'], 'topics': ['topics.txt', 'type.txt', 'topic-info.txt'],
                 'interface': ['twist.txt'], 'echo': ['pose.txt', 'hz.txt'],
                 'params': ['params.txt', 'description.txt', 'value.txt'], 'dump': ['turtle.yaml'],
                 'load': ['restore.yaml'], 'baginfo': ['bag-info.txt']}[key]
        add('결과 사본 인계', '앞에서 만든 파일을 reports 폴더에 복사해 보관합니다. 원본을 유지하므로 mv가 아니라 cp입니다. 파일 수정 후에는 사본도 다시 복사합니다. F3에는 파일을 자동 선택하는 find 방식도 있습니다.',
            'mkdir -p reports\n' + '\n'.join('cp ' + name + ' reports/' for name in files) + '\nls reports',
            '문제의 시작 폴더에서 실행합니다. 폴더 생성만이 아니라 사본의 내용도 원본과 같아야 합니다.')
    else:
        prep = setup + ('\nexport ROS_DOMAIN_ID=42' if key == 'domain' else '')
        add('작업 후 노드 목록 보관', '노드를 유지하면서 작업 후 상태를 기록합니다. 실행 중인 작업이 터미널을 사용하면 조회용 터미널을 사용하세요. 그 터미널도 source와 같은 도메인이 필요합니다.',
            prep + '\ncd ' + shlex.quote(start) + '\nros2 node list > nodes-after.txt\ncat nodes-after.txt',
            '실행 전의 낡은 목록이 아니라 현재 노드가 담겨 있어야 합니다. >는 셸의 덮어쓰기 저장이고 파일은 현재 폴더에 생깁니다.')
    return tuple(steps)


def docker_steps(m, mode):
    from real_lessons import UBUNTU
    from docker_lessons import IMAGE, write_lines
    key = m.kind.removeprefix('sim_').removeprefix('docker_')
    lines = m.solution.splitlines()
    name, keep = f'box{m.seed}', f'keep{m.seed}'
    image = UBUNTU if mode == 'real' else 'ubuntu:24.04'
    steps = []
    def add(title, why, commands, check):
        steps.append(LearningStep(title, why, commands, check))
    if key == 'images':
        if mode == 'real':
            add('이미지 주소 읽기', 'localhost:5000/training/ubuntu:24.04를 나누어 읽습니다. localhost는 앱 전용 Linux 자신, 5000은 레지스트리 접속 포트, training은 저장소 이름공간, ubuntu:24.04는 이미지:태그입니다. '
                '외부 인터넷 없이 같은 실습 자료를 받으려고 앱 내부 저장소를 사용합니다. 일반 Docker Hub 주소와의 차이는 F3에서 더 볼 수 있습니다.', 'docker images', 'training은 Linux 폴더가 아니고, 이 접두사가 모든 Docker 사용에 필수인 것도 아닙니다.')
        add('이미지 하나 받기', '이미지는 컨테이너 생성의 틀입니다. pull은 이미지를 받는 작업이며 컨테이너를 실행하지 않습니다. 콜론 뒤는 태그입니다.', lines[0], '받은 이름과 태그를 확인합니다. 이미지 받기와 실행하기는 다른 작업입니다.')
        add('다른 태그와 목록', '태그 생략 시 latest를 사용하지만 가장 최신이라는 보장은 없습니다. images는 로컬 이미지 목록입니다.', '\n'.join(lines[1:]), 'REPOSITORY, TAG, IMAGE ID를 구별합니다. 컨테이너 목록 ps와 다릅니다.')
    elif key == 'run':
        add('생성과 분리 실행', '--name은 컨테이너 이름, -d는 터미널을 점유하지 않는 분리 실행입니다. 이미지 뒤 sleep 300은 컨테이너 안에서 실행할 명령입니다.', lines[0], '컨테이너 ID가 출력됩니다. sleep이 끝나면 컨테이너도 종료되므로 뒤의 실습은 실행 중에 진행합니다.')
        add('실행 중과 전체 목록', 'ps는 실행 중만, ps -a는 종료된 컨테이너도 표시합니다. 종료와 삭제는 다릅니다.', 'docker ps\ndocker ps -a', f'{name}의 이름, 기반 이미지, STATUS를 찾습니다. docker images와 비교해 역할을 구별합니다.')
    elif key == 'lifecycle':
        add('준비된 상태 조사', '새로 만들지 않고 기존 컨테이너의 상태만 바꿉니다. 먼저 이름·ID·상태를 확인합니다.', 'docker ps -a', f'{name}과 {keep}를 구별하고 ID를 확인합니다.')
        add('같은 컨테이너 시작', 'start는 이미 존재하는 컨테이너를 시작합니다. run으로 같은 이름을 다시 만들면 이름 충돌이며 다른 작업입니다.', lines[0] + '\ndocker ps', '기존 ID가 유지되며 실행 중이어야 합니다.')
        add('다른 컨테이너만 중지', 'stop은 종료 상태로 남기며 삭제하지 않습니다. restart는 중지 후 같은 컨테이너를 다시 시작하는 명령입니다.', '\n'.join(lines[1:]), '하나는 실행 중, 다른 하나는 종료 상태이며 둘 다 목록에 남아야 합니다.')
    elif key == 'exec':
        add('안과 밖의 경로 구별', 'exec는 실행 중인 컨테이너에 새 프로세스를 실행합니다. 뒤의 pwd/ls는 컨테이너 안을 조사합니다.', f'docker exec {name} pwd\ndocker exec {name} ls /tmp', '실습 Linux의 /tmp와 컨테이너의 /tmp는 다른 위치입니다.')
        add('컨테이너 안의 셸로 파일 작성', 'bash -c 뒤 작은따옴표 안을 컨테이너 셸이 해석합니다. >를 따옴표 밖에 두면 바깥 셸이 파일을 만들므로 주의합니다.', lines[0], '리다이렉션이 어느 셸에서 실행되는지 읽어 봅니다. 대화형 셸은 exec -it 이름 bash이며 exit해도 주 프로세스는 유지됩니다.')
        add('같은 위치에서 내용 확인', '작성한 위치와 같은 컨테이너에서 cat으로 읽습니다. 이름이 같은 호스트 파일을 읽는 것으로 대신하지 않습니다.', lines[1], 'ready 한 줄이 실제로 들어 있어야 합니다.')
    elif key == 'cleanup':
        add('대상만 중지', '실행 중인 컨테이너는 먼저 중지합니다. 보존 대상과 삭제 대상을 목록에서 구분합니다.', 'docker ps -a\n' + lines[0], f'{keep}는 건드리지 않습니다. stop은 아직 삭제가 아닙니다.')
        add('컨테이너 삭제', 'rm의 대상은 컨테이너 이름/ID입니다. 이미지 이름을 넣는 명령과 구별합니다.', lines[1] + '\ndocker ps -a', f'{name}은 없어지고 {keep}는 남아야 합니다.')
        add('참조가 풀린 이미지 삭제', 'rmi의 대상은 이미지 참조입니다. 컨테이너가 사용하는 마지막 태그를 제거하려 하면 거절될 수 있습니다.', lines[2] + '\ndocker images', '지정한 Ubuntu만 제거하고 Alpine은 보존합니다. 일괄 prune으로 다른 자원까지 지우지 않습니다.')
    elif key == 'update':
        add('새 이미지만 받기', '같은 태그를 pull해도 기존 컨테이너의 내용은 자동으로 바뀌지 않습니다. 새 이미지를 받은 단계와 교체 단계는 다릅니다.', lines[0] + '\ndocker images', '목록의 이미지 ID를 확인합니다. 현재 컨테이너는 아직 예전 이미지로 실행 중입니다.')
        add('교체 대상 정리', '기존 컨테이너를 중지한 뒤 제거해야 같은 이름으로 새로 만들 수 있습니다. 볼륨과 영구 데이터 보존은 뒤의 저장소 과정에서 더 다룹니다.', '\n'.join(lines[1:3]), '지울 대상을 정확히 선택합니다. pull만으로 교체를 마쳤다고 생각하지 않습니다.')
        add('새 이미지로 다시 생성', 'run은 새로운 컨테이너를 만듭니다. 이름이 같아도 컨테이너 ID와 기반 이미지가 바뀝니다.', lines[3] + '\ndocker ps', '새 컨테이너가 실행 상태여야 합니다.')
    elif key == 'tag':
        add('추가 이름표 붙이기', 'tag는 같은 이미지에 새 참조를 추가합니다. 파일 전체 복사나 컨테이너 이름 지정 --name이 아닙니다.', lines[0], '원래 태그는 삭제하지 않습니다.')
        add('이름과 실체 구별', '이미지 목록에서 저장소/태그가 다른 두 행을 비교합니다. 같은 IMAGE ID면 같은 이미지입니다.', lines[1], '이미지 내용을 바꾸려면 tag가 아니라 commit/build가 필요합니다.')
    elif key == 'commit':
        add('컨테이너 안에 변경 만들기', '먼저 컨테이너의 쓰기 영역에 파일을 만듭니다. 아직 기반 이미지가 바뀐 것은 아닙니다.', lines[0], 'exec의 bash -c 안에서 >를 해석하는지 확인합니다.')
        add('변경을 새 이미지로 보관', 'commit은 컨테이너의 파일 변경을 새 이미지로 만듭니다. 메모리/실행 위치나 마운트 볼륨 데이터의 전체 저장이 아닙니다.', lines[1], '원본 컨테이너와 새 이미지 이름을 구별합니다.')
        add('새 컨테이너에서 검증', '원본에서만 확인하면 이미지에 들어갔는지 모릅니다. 새 이미지로 다른 컨테이너를 만들어 읽습니다.', '\n'.join(lines[2:]), '새 컨테이너에서도 ready가 나와야 합니다.')
    elif key == 'save':
        add('이미지를 파일로 보관', 'save -o 뒤는 출력 파일명, 마지막은 이미지 참조입니다. 실행 중 컨테이너나 볼륨 백업과 다릅니다.', lines[0] + '\nls -l images.tar', '파일 확장자 .tar와 이미지 태그는 별개입니다.')
        add('로컬 이미지만 제거', '복원 가능성을 시험하려고 저장한 이미지를 로컬에서 제거합니다. 아카이브는 유지합니다.', lines[1] + '\ndocker images', '이미지가 사라져도 images.tar는 남아 있어야 합니다.')
        add('파일에서 복원', '<는 파일을 명령의 입력으로 연결하는 셸 문법입니다. load -i images.tar로 지정하는 방식도 있습니다. 여기서 pull로 다시 받지 않습니다.', '\n'.join(lines[2:]), '보관한 이미지가 다시 목록에 나타나는지 확인합니다.')
    elif key == 'limits':
        base = f'docker run --name {name} -d'
        tail = f' {image} sleep 300'
        replace = f'docker stop {name}\ndocker rm {name}\n'
        add('환경변수 하나 전달', '-e APP_MODE=training은 컨테이너 환경변수입니다. 바깥 셸 변수를 바꾸지 않습니다. inspect의 Config.Env에서 확인합니다.', base + ' -e APP_MODE=training' + tail + f'\ndocker inspect {name}', 'APP_MODE=training이 있는지 봅니다. 아직 포트/자원 옵션을 넣지 않습니다.')
        port_field = 'HostConfig.PortBindings' if mode == 'real' else 'HostConfig.publish (모의 표기)'
        memory_field = 'inspect의 Memory는 바이트로 표시됩니다.' if mode == 'real' else '모의 inspect는 memory에 입력값 128m을 표시합니다. 실제 Docker의 Memory는 바이트 값입니다.'
        cpu_field = 'inspect의 NanoCpus는 10억 단위입니다.' if mode == 'real' else '모의 inspect는 cpus에 입력값을 표시합니다. 실제 Docker의 NanoCpus는 10억 단위입니다.'
        add('포트 연결만 추가', '-p 8080:80의 방향은 실습 호스트:컨테이너입니다. 실제 모드의 실습 호스트는 사용자 PC가 아니라 앱 전용 Linux입니다. 생성 설정을 바꾸려고 학습용 컨테이너만 교체합니다.', replace + base + ' -e APP_MODE=training -p 8080:80' + tail + f'\ndocker inspect {name}', port_field + '를 봅니다. sleep은 웹서버가 아니므로 포트 설정만으로 웹페이지가 생기지는 않습니다.')
        add('메모리 한도 추가', '--memory 128m은 메모리 상한입니다. 현재 사용량과 다릅니다. ' + memory_field, replace + base + ' -e APP_MODE=training -p 8080:80 --memory 128m' + tail + f'\ndocker inspect {name}', '128 MiB는 134217728바이트입니다. 환경변수/포트도 앞에서 배운 대로 유지합니다.')
        add('CPU 한도까지 조합', '--cpus 1은 CPU 한 개 분량의 시간 한도이며 특정 코어에 고정하는 뜻이 아닙니다. ' + cpu_field, replace + '\n'.join(lines), '환경변수·포트·메모리·CPU 네 항목을 각각 찾아 확인합니다. 시뮬레이션 값은 실제 자원 사용량이 아닙니다.')
    elif key == 'bind':
        worker = f'sgd{m.seed}-worker'
        add('원본과 컨테이너 경로', 'bind는 복사가 아니라 같은 자료를 다른 경로에 연결합니다. src는 실습 Linux 경로, dst는 컨테이너 안 경로입니다. input data는 공백 때문에 따옴표가 필요합니다.', 'pwd\nls -l "input data" output\ncat "input data/message.txt"', '입력 원본과 출력 폴더를 구별합니다. 아직 컨테이너는 만들지 않습니다.')
        mount = shlex.quote('type=bind,src=' + m.start + '/input data,dst=/input,readonly')
        add('입력 하나만 읽기 전용 연결', '먼저 입력 폴더 하나만 연결해 읽습니다. readonly는 컨테이너에서 쓰는 것을 막습니다. --rm은 명령을 마친 일회성 컨테이너를 정리하며 원본 폴더를 지우지 않습니다.', f'docker run --rm --mount {mount} {IMAGE} cat /input/message.txt', '바깥 input data/message.txt와 같은 내용이 /input/message.txt에서 보이는지 확인합니다.')
        add('출력 폴더와 숫자 권한', '이번에는 출력도 연결할 예정입니다. rw로 마운트해도 Linux 권한이 쓰기를 막을 수 있습니다. --user 1100:1100은 이름이 아니라 숫자 UID:GID입니다.', 'ls -ldn output', '폴더 소유권 1100:1100과 쓰기 권한을 확인한 뒤 입력/출력 연결을 조합합니다.')
        add('읽기/쓰기와 사용자 지정', '입력의 readonly는 쓰기를 막고 출력은 쓰기 가능으로 연결합니다. --user 1100:1100은 UID:GID이며 폴더 권한도 이 숫자로 적용됩니다. 긴 run을 src/dst/readonly/user 덩어리별로 읽습니다.', lines[0] + f'\ndocker inspect {worker}', 'Mounts의 Source/Destination/RW와 Config.User를 확인합니다. -v "원본:/input:ro"도 같은 목적이며 차이는 F3에서 확인할 수 있습니다.')
        add('연결된 경로로 작업', '컨테이너 안의 /input을 읽고 /output에 씁니다. 바깥 output에도 결과가 나타나야 하며 입력 원본은 유지합니다.', lines[1] + '\ncat output/result.txt', '단순 복사 성공뿐 아니라 원본과 output/.keep도 유지되는지 확인합니다.')
    elif key == 'volume':
        add('이름 있는 저장소 만들기', 'volume은 Docker가 관리하는 저장소입니다. 이름은 호스트 경로가 아닙니다. 컨테이너보다 오래 유지할 수 있습니다.', lines[0] + '\ndocker volume ls', '이번에 만든 볼륨과 보호용 볼륨을 구별합니다.')
        add('일회성 컨테이너로 쓰기', 'type=volume의 src는 볼륨 이름, dst=/data는 안에서 보일 위치입니다. --rm은 종료된 일회성 컨테이너를 정리하지만 이름 있는 볼륨은 남깁니다.', lines[1], '작성용 컨테이너가 끝난 뒤에도 볼륨은 남아 있습니다.')
        add('다른 컨테이너에 같은 볼륨 연결', '같은 이름의 볼륨을 다시 연결해야 예전 데이터가 보입니다. 비슷한 다른 이름이면 빈 저장소일 수 있습니다.', '\n'.join(lines[2:]), '새 컨테이너에서 이전 note.txt를 읽습니다. 뒤의 활용에서는 연결 복구와 백업/복원으로 확장합니다.')
        volume = f'sgd{m.seed}-data'
        backup = shlex.quote('type=bind,src=' + m.start + '/backup files,dst=/backup')
        add('볼륨에서 일반 파일로 백업', '원본 볼륨은 읽기 전용, 백업 폴더는 쓰기 가능으로 연결합니다. 원본을 바꾸지 않고 파일로 꺼내는 작업입니다.',
            'mkdir -p "backup files"\n' + f'docker run --rm --mount type=volume,src={volume},dst=/from,readonly --mount {backup} {IMAGE} cp /from/note.txt /backup/note.txt\ncat "backup files/note.txt"', '기존 볼륨과 컨테이너를 유지하고 사본만 만들었는지 확인합니다.')
        add('새 볼륨으로 사본 복원', '검증용 새 볼륨에 파일을 복원합니다. 원본 볼륨을 지우고 같은 이름을 다시 만드는 것과 다릅니다.',
            f'docker volume create {volume}-restored\ndocker run --rm --mount type=volume,src={volume}-restored,dst=/data --mount {backup},readonly {IMAGE} cp /backup/note.txt /data/note.txt\ndocker run --rm --mount type=volume,src={volume}-restored,dst=/data {IMAGE} cat /data/note.txt', '새 저장소에서도 원래 내용이 읽혀야 합니다. 보호용 볼륨은 건드리지 않습니다.')
    elif key == 'network':
        add('통신할 네트워크 만들기', '사용자 정의 bridge에서는 컨테이너 이름과 별칭을 DNS 이름으로 사용할 수 있습니다. 기본 bridge와 구별합니다.', lines[0], '이름은 이번 실습에서 정한 네트워크를 가리킵니다. 외부 인터넷 연결은 필요하지 않습니다.')
        add('상대의 별칭 지정', '--network는 참가할 네트워크, --network-alias api는 그 안에서 상대를 찾을 별칭입니다.', lines[1], '이 별칭은 다른 네트워크 전체에 자동으로 공유되지 않습니다.')
        add('같은 네트워크에서 통신', '두 컨테이너가 같은 네트워크에 있어야 합니다. ping -c 1은 한 번, -W 2는 응답 대기 2초입니다. 내부 통신에 -p는 필요하지 않습니다.', '\n'.join(lines[2:]), 'inspect의 연결 표시뿐 아니라 실제 ping 성공을 확인합니다. 기존 연결 복구의 connect/disconnect는 F3와 활용에서 다룹니다.')
        extra, worker = f'sgd{m.seed}-net-extra', f'sgd{m.seed}-worker'
        add('기존 컨테이너의 연결만 변경', 'connect/disconnect는 컨테이너를 지우지 않고 연결을 추가/제거합니다. 연습용 추가 네트워크를 붙였다가 떼며 원래 네트워크는 유지합니다.',
            f'docker network create {extra}\ndocker network connect {extra} {worker}\ndocker network inspect {extra}', '새 네트워크에 기존 컨테이너의 같은 ID가 참가했는지 확인합니다.')
        add('불필요한 연결만 정리', '먼저 연결을 끊고 사용하지 않는 네트워크를 삭제합니다. 컨테이너나 원래 통신망은 삭제하지 않습니다.',
            f'docker network disconnect {extra} {worker}\ndocker network rm {extra}\ndocker exec {worker} ping -c 1 -W 2 api', '원래 api와의 통신이 계속 성공해야 합니다. 뒤의 활용은 이 원리로 잘못된 연결을 복구합니다.')
    elif key == 'build':
        add('기반과 작업 폴더', 'Dockerfile은 제작 절차입니다. FROM은 기반 이미지, WORKDIR은 이후 작업 경로입니다. app은 이번 빌드 자료 폴더입니다.', write_lines('app/Dockerfile', f'FROM {IMAGE}\nWORKDIR /app\n') + '\ncat app/Dockerfile', '아직 빌드하지 않습니다. 한 파일에 다음 단계의 지시를 이어서 추가합니다.')
        add('파일 복사와 빌드 중 실행', 'COPY의 원본은 빌드 문맥 app 기준입니다. RUN은 이미지 제작 중 실행되어 결과를 이미지에 남깁니다.', 'printf \'%s\\n\' \'COPY message.txt message.txt\' \'RUN printf "built\\n" > /build-stamp\' >> app/Dockerfile\ncat app/Dockerfile', 'app/message.txt가 원본이며 /build-stamp는 이미지 안에 생깁니다. >>는 앞 내용을 유지하고 덧붙입니다.')
        add('실행 사용자와 기본 명령', 'USER는 기본 UID:GID, CMD는 나중에 컨테이너가 시작할 때 실행하는 명령입니다. RUN과 시점이 다릅니다.', 'printf \'%s\\n\' \'USER 1100:1100\' \'CMD ["cat", "message.txt"]\' >> app/Dockerfile\ncat app/Dockerfile', '아직 컨테이너가 실행된 것은 아닙니다. 확장 설정 ENV는 이미지의 기본 환경변수를 지정하며 F3에서 확인할 수 있습니다.')
        add('이미지의 기본 환경변수', 'ENV는 이미지로 실행할 컨테이너의 기본 환경변수입니다. 현재 셸의 export와 다릅니다. 실행 시 -e로 덮어쓸 수 있습니다.', 'printf \'%s\\n\' \'ENV APP_MODE=training\' >> app/Dockerfile\ncat app/Dockerfile', '앞의 Dockerfile 내용은 >>로 유지합니다. 뒤의 종합에서는 이 기본 설정을 고치는 문제로 연결됩니다.')
        add('문맥과 태그로 빌드', '-t 뒤는 이미지 이름:태그, 마지막 app은 빌드 문맥입니다. --network=none은 빌드 중 네트워크를 사용하지 않게 합니다.', lines[1], '빌드 오류가 있으면 COPY 원본을 현재 셸 위치가 아니라 app 안에서 찾습니다.')
        add('기본 실행을 검증', '이미지 뒤에 새 명령을 붙이지 않아야 CMD를 검증합니다. >는 실행 결과를 실습 Linux 파일로 저장합니다.', lines[2] + '\ncat build-result.txt', 'build 번호가 출력되고 정상 종료해야 합니다. 뒤의 활용에서는 수정 후 새 태그로 빌드하고 이전 버전을 보존합니다.')
    elif key == 'diagnose':
        worker = f'sgd{m.seed}-worker'
        add('종료 상태와 실패 로그 보관', 'ps -a는 종료된 컨테이너도 보여 줍니다. logs의 표준 오류까지 저장하려면 > failure.log 뒤에 2>&1을 씁니다. 순서가 중요합니다.', 'docker ps -a\n' + lines[0] + '\ncat failure.log', '오류가 난 컨테이너를 새로 만들지 않고 원래 실패 기록을 보관합니다.')
        add('종료 코드 조사', 'inspect --format은 원하는 필드만 출력합니다. State.ExitCode가 0이 아니면 실패 원인을 조사합니다. {{...}}는 템플릿 문법이며 따옴표로 묶습니다.', lines[1] + '\ncat exit-code.txt', '이번 실패의 코드와 로그를 연결해 봅니다.')
        add('원인을 고쳐 같은 컨테이너 재시작', '이번 원인은 설정 파일의 MODE입니다. 삭제 후 재생성하지 않고 입력을 고친 뒤 start합니다.', '\n'.join(lines[2:]) + f'\ndocker logs {worker}\ndocker ps', 'ID가 유지되고 service-ready 로그와 실행 상태가 보여야 합니다. 다른 활용은 누락 파일과 권한 오류를 다룹니다.')
    else:
        raise ValueError('Missing Docker learning steps: ' + key)
    if m.kind.startswith('sim_'):
        add('작업 후 컨테이너 목록 저장', 'ps -a는 종료된 컨테이너까지 포함합니다. >는 셸의 표준출력 저장이며 Docker 옵션이 아닙니다. 작업을 끝낸 다음 현재 상태를 저장합니다.', 'docker ps -a > containers.txt\ncat containers.txt', '문제의 시작 폴더에서 저장합니다. 파일이 있다는 것보다 현재 상태가 담겼는지가 중요합니다.')
        add('이미지 목록도 따로 보관', '컨테이너 목록과 이미지 목록은 다른 조사입니다. >는 덮어쓰기, >>는 이어쓰기라 보고서 갱신에는 >를 씁니다.', 'docker images > images.txt\ncat images.txt', '이미지 이름·태그·ID를 확인합니다. 이후 자원을 바꿨다면 보고서도 다시 저장합니다.')
    return tuple(steps)
