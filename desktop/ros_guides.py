"""Learning-only ROS 2 Humble explanations; never injected into test goals.

References (Humble, not Rolling): ros2/ros2_documentation tutorials,
ros2/ros2cli ros2topic/verb/pub.py, and ros2/rosbag2 player.cpp.
See ROS_TEACHING.md for source links and the scope of verification.
"""

REPORT_KEYS = frozenset(('env', 'overlay', 'nodes', 'topics', 'interface', 'echo',
                         'params', 'dump', 'load', 'baginfo'))

TERMINAL_GUIDE = (
    '실습 터미널의 역할\n'
    '각 터미널은 파일과 실행 중인 노드를 공유하지만 환경변수는 따로 갖습니다. 새 터미널에서도 source /opt/ros/humble/setup.bash를 실행하세요.\n'
    'run·launch·반복 발행·관찰·기록은 계속 실행될 수 있습니다. 프롬프트가 돌아오지 않으면 그 작업이 터미널을 사용 중인 것입니다. '
    '조회는 앱의 새 터미널에서 하고, 끝낼 작업에만 Ctrl+C를 보냅니다. 유지해야 하는 노드의 터미널을 닫지 마세요.')

FILE_GUIDE = (
    '파일로 결과 남기기\n'
    '명령 > 결과.txt는 표준출력을 화면 대신 파일에 저장하는 셸 문법입니다. ROS 옵션이 아닙니다. '
    '>는 기존 파일을 덮어쓰고 >>는 뒤에 붙입니다. 오류 메시지는 기본적으로 화면에 남으므로 빈 파일만 생겼다고 성공은 아닙니다.\n'
    '상대 파일명은 현재 폴더 기준입니다. pwd로 위치를 확인하고, 문제의 시작 폴더에서 저장하거나 그 폴더의 경로를 지정하세요. '
    'cat 결과.txt로 실제 내용을 확인합니다. 조회·변경을 마친 뒤 저장해야 그 시점의 상태가 남습니다.')

REPORT_GUIDE = (
    '활용에서 이어지는 파일 인계\n'
    'reports는 결과 사본을 모으는 일반 폴더입니다. ROS 예약 이름이 아닙니다. '
    '원본을 유지하므로 mv가 아니라 cp를 사용합니다. 결과를 수정했다면 사본도 다시 복사해야 합니다.\n'
    '문제의 시작 폴더에서 결과 파일을 모두 만든 뒤 실행하는 예:\n'
    'mkdir -p reports\n'
    'find . -maxdepth 1 -type f \\( -name "*.txt" -o -name "*.yaml" \\) -exec cp {} reports/ \\;\n'
    '-p는 폴더가 이미 있어도 사용할 수 있게 합니다. .은 현재 폴더, -maxdepth 1은 바로 아래까지만, -type f는 일반 파일만 선택합니다.\n'
    '-name은 이름 조건, -o는 둘 중 하나입니다. \\(와 \\)는 조건을 묶으며 셸이 먼저 해석하지 않게 역슬래시를 붙입니다. '
    '"*.txt"처럼 따옴표로 묶어야 셸이 아니라 find가 이름을 비교합니다.\n'
    '{}는 찾은 파일 경로, \\;는 -exec 명령의 끝입니다. cp가 파일마다 실행되므로 공백 이름도 처리합니다. '
    'reports 안으로 다시 내려가지 않습니다. 복사할 파일이 없으면 아무것도 복사하지 않으므로 ls reports와 cat으로 확인하세요. '
    '제공된 restore.yaml이 있는 문제에서는 그 파일도 보관 대상입니다.')

NODE_REPORT_GUIDE = (
    '활용에서 이어지는 노드 조사\n'
    '작업이 끝난 시점에 ros2 node list > nodes-after.txt로 노드 목록을 저장하고 cat nodes-after.txt로 확인합니다. '
    '작업 전의 목록을 남기거나 노드를 종료한 뒤 저장하면 요구한 실행 상태가 빠집니다.\n'
    '실행 터미널이 사용 중이면 별도의 조회 터미널을 엽니다. 그곳에서도 ROS 환경을 활성화하고 같은 ROS_DOMAIN_ID를 사용하세요. '
    '도메인 42 문제에서는 조회 터미널에도 export ROS_DOMAIN_ID=42가 필요합니다. 파일은 문제의 시작 폴더에 저장합니다.')

GUIDES = {
    'env': (
        '왜 필요한가\nROS는 패키지·라이브러리를 찾는 경로를 셸 환경에서 읽습니다. source는 설치가 아니라 이미 설치된 환경을 현재 셸에 적용하는 작업입니다.\n\n'
        '명령을 읽는 법\nsource /opt/ros/humble/setup.bash\n'
        '/opt/ros/humble은 이 실습 Linux의 Humble 설치 폴더, setup.bash는 Bash용 환경 설정 파일입니다. 다른 배포판/설치 방식에서는 경로가 달라집니다. '
        'bash setup.bash로 별도 셸에서 실행하면 현재 셸의 환경을 설정하는 것과 다릅니다.\n'
        'printenv ROS_DISTRO → 배포판 이름 humble, printenv ROS_VERSION → ROS 세대 2를 확인합니다. 2는 패키지의 상세 버전 번호가 아닙니다.\n\n'
        '결과 확인과 흔한 실수\nsource는 성공해도 아무것도 출력하지 않을 수 있습니다. 위 두 값과 ros2 --help로 확인하세요. '
        '환경변수 값을 echo로 파일에 직접 적는 것은 환경 활성화가 아닙니다. 새 터미널에는 다시 적용해야 합니다.'),
    'overlay': (
        '왜 필요한가\n기본 ROS 위에 내가 만든 패키지 검색 경로를 더하는 것이 오버레이입니다. 기본 설치 파일을 복사하거나 덮어쓰지 않습니다.\n\n'
        '명령을 읽는 법\n먼저 기본 setup.bash를 source하고, source ~/training_ws/install/local_setup.bash를 실행합니다. '
        '~는 실습 사용자 홈, training_ws는 이 과정에서 정한 작업공간 이름, install은 빌드 결과를 설치한 폴더입니다. '
        '소스 코드가 담긴 src와 다릅니다. 이 문제에서는 빌드를 이미 준비했습니다.\n'
        'local_setup.bash는 이 작업공간을 추가합니다. setup.bash는 빌드 때 연결된 언더레이 설정도 불러옵니다. '
        '기본 환경 → 추가 환경 순서를 익히면 어느 패키지를 선택했는지 추적하기 쉽습니다.\n\n'
        '결과 확인과 흔한 실수\nros2 pkg prefix shellground_demo는 패키지의 설치 위치를 조회합니다. 현재 폴더를 보는 pwd와 다릅니다. '
        'Package not found이면 경로·source 순서·현재 터미널을 확인하세요. cd training_ws만으로 오버레이가 활성화되지는 않습니다.'),
    'run': (
        '왜 필요한가\n노드는 ROS 통신에 참여하는 실행 단위입니다. 패키지는 관련 프로그램을 묶고, 실행파일은 시작할 프로그램을 가리킵니다.\n\n'
        '명령을 읽는 법\nros2 run turtlesim turtlesim_node\n'
        'turtlesim은 패키지, turtlesim_node는 그 안의 실행파일입니다. 기본 노드 이름은 /turtlesim이므로 세 이름을 바꿔 쓰면 안 됩니다. '
        'ros2 pkg executables turtlesim으로 실행파일 목록을 볼 수 있습니다.\n\n'
        '결과 확인과 흔한 실수\n실행 터미널을 유지하고 새 터미널에서 ros2 node list, ros2 node info /turtlesim으로 확인합니다. '
        '이 단원은 직접 노드를 시작합니다. 이후 “준비된 TurtleSim” 문제는 앱이 먼저 실행하므로 같은 노드를 중복 실행하지 않습니다. '
        '실제 Linux 화면에서 거북이를 관찰할 수 있으며 노드 유지가 목표인 동안 Ctrl+C로 끄지 않습니다.'),
    'nodes': (
        '왜 필요한가\n노드 목록은 어떤 구성 요소가 살아 있는지, info는 그 노드가 무엇과 통신하는지 조사하는 출발점입니다.\n\n'
        '명령을 읽는 법\nros2 node list → 발견한 노드 이름 목록\n'
        'ros2 node info /turtlesim → 특정 노드의 Publishers, Subscribers, Service Servers/Clients, Action Servers/Clients\n'
        'Publisher는 메시지를 내보내고 Subscriber는 받습니다. Server는 요청을 처리하고 Client는 요청합니다. '
        '/turtlesim은 ROS 이름이지 Linux 폴더가 아니므로 cd로 이동하지 않습니다.\n\n'
        '결과 확인과 흔한 실수\nlist 출력에서 실제 전체 이름을 골라 info에 전달합니다. nodes.txt에는 목록을, node-info.txt에는 연결 정보를 따로 남깁니다. '
        '조회용 임시 노드 등 추가 항목이 나타날 수 있으므로 총 개수를 외우기보다 목표 노드와 연결을 확인하세요. '
        '목록이 비면 환경과 도메인, 실행 터미널이 살아 있는지 먼저 점검합니다.'),
    'launch': (
        '왜 필요한가\n여러 프로그램의 시작과 이름 설정을 런치 파일 하나에 모으면 같은 구성을 반복 실행하기 쉽습니다.\n\n'
        '명령을 읽는 법\nros2 launch turtlesim multisim.launch.py\n'
        'turtlesim은 패키지, multisim.launch.py는 그 패키지에서 찾는 런치 파일입니다. run 뒤에는 실행파일, launch 뒤에는 런치 파일을 넣습니다. '
        '이 파일은 turtlesim1, turtlesim2 이름공간으로 두 노드를 실행합니다.\n\n'
        '결과 확인과 흔한 실수\n별도 터미널의 ros2 node list에서 /turtlesim1/turtlesim과 /turtlesim2/turtlesim을 찾습니다. '
        '이름공간은 ROS 이름 앞에 붙는 구분자이지 파일 폴더나 통신 격리 장치가 아닙니다. '
        'launch 터미널은 두 노드를 관리하므로 유지해야 합니다. 기본 /turtlesim 하나를 실행한 것은 같은 결과가 아닙니다.'),
    'topics': (
        '왜 필요한가\n토픽은 노드 사이의 메시지 흐름에 붙인 이름입니다. /turtle1/cmd_vel은 이동 명령, /turtle1/pose는 위치 관측에 사용합니다.\n\n'
        '명령을 읽는 법\nros2 topic list -t → 이름과 타입을 함께 표시(-t는 타입 표시)\n'
        'ros2 topic type /turtle1/cmd_vel → 그 토픽의 메시지 타입만 조회\n'
        'ros2 topic info /turtle1/cmd_vel → 타입과 발행자/구독자 수 조회\n'
        'info 뒤 --verbose 또는 -v를 더하면 연결 노드와 QoS(전달 방식)까지 조사할 수 있습니다.\n\n'
        '결과 확인과 흔한 실수\n노드 이름 /turtlesim과 토픽 이름 /turtle1/cmd_vel은 서로 다릅니다. '
        '구독자만 있어도 목록에 보일 수 있으므로 토픽 존재가 메시지 도착을 뜻하지 않습니다. '
        'topics.txt, type.txt, topic-info.txt는 서로 다른 조사 결과입니다. 한 출력을 세 파일에 복제하지 마세요.'),
    'interface': (
        '왜 필요한가\n타입은 메시지의 설계도입니다. 필드 이름과 자료형을 먼저 읽으면 발행할 YAML을 추측하지 않아도 됩니다.\n\n'
        '명령을 읽는 법\nros2 interface show geometry_msgs/msg/Twist\n'
        'geometry_msgs는 타입을 제공하는 패키지, msg는 메시지 정의, Twist는 타입 이름입니다. 토픽 이름이나 파일 경로가 아닙니다. '
        '출력의 linear와 angular는 각각 x/y/z 실수 성분을 갖는 Vector3입니다.\n'
        '평면 TurtleSim에서는 linear.x를 전진 속도로, angular.z를 회전 속도로 사용합니다. angular.z는 목표 각도 자체가 아닙니다. '
        'YAML의 {linear: {x: 1.0}, angular: {z: 0.5}}는 이 중첩 구조를 그대로 표현합니다.\n\n'
        '결과 확인과 흔한 실수\nshow는 정의를 읽는 명령이며 현재 위치나 속도를 측정하지 않습니다. 실제 메시지 값은 다음 단원의 echo로 봅니다. '
        '필드 이름은 대소문자를 구분하며 없는 필드는 발행 오류의 원인이 됩니다.'),
    'echo': (
        '왜 필요한가\necho는 메시지 내용, hz는 내가 수신하는 빈도를 관찰합니다. 노드나 타입의 설명만 읽는 조회와 다릅니다.\n\n'
        '명령을 읽는 법\nros2 topic echo /turtle1/pose에서 x, y, theta 등을 봅니다. 메시지 사이의 ---는 YAML 문서 구분입니다. '
        'ros2 topic hz /turtle1/pose의 average rate는 초당 수신 횟수, min/max는 관측 간격입니다. 몇 개 메시지를 받아야 통계가 나옵니다.\n\n'
        '결과 확인과 흔한 실수\n파일 저장은 echo ... > pose.txt 실행 → 몇 개 수신 → Ctrl+C → hz ... > hz.txt 실행 → 통계 수집 → Ctrl+C 순서입니다. '
        '두 명령을 그대로 연달아 붙여 넣으면 첫 작업이 계속 실행되어 두 번째가 시작되지 않습니다. 리다이렉션 중 화면이 조용한 것은 정상입니다. '
        '종료 후 cat으로 두 파일을 확인합니다. 토픽·발행자·도메인이 맞는데 수신되지 않으면 info -v로 QoS 호환성을 조사합니다.'),
    'once': (
        '왜 필요한가\n프로그램을 작성하기 전에 메시지를 직접 보내 수신 노드의 반응을 시험할 수 있습니다.\n\n'
        '명령을 읽는 법\nros2 topic pub --once /turtle1/cmd_vel geometry_msgs/msg/Twist "{linear: {x: 1.0}, angular: {z: 0.5}}"\n'
        '순서는 발행 옵션 → 토픽 이름 → 메시지 타입 → YAML 값입니다. --once(-1)는 한 번 발행 후 종료, -w 1은 일치하는 구독자 하나를 기다린다는 뜻입니다. '
        'Humble의 --once는 -w를 생략해도 기본 한 구독자를 기다립니다.\n'
        '따옴표는 공백·중괄호를 포함한 YAML 전체를 한 인자로 전달합니다. 콜론 다음 공백과 중첩 괄호를 유지하세요. '
        '생략한 Twist 성분은 기본값 0입니다.\n\n'
        '결과 확인과 흔한 실수\nWaiting for ...는 구독 연결을 기다리는 상태입니다. 무작정 재실행하지 말고 목표 노드·타입·도메인을 조사하세요. '
        '발행 출력뿐 아니라 거북이의 반응도 봅니다. 한 번의 속도 명령은 계속 움직이라는 무한 반복과 다릅니다.'),
    'rate': (
        '왜 필요한가\n속도 명령을 일정 간격으로 갱신하는 연습입니다. 같은 값을 반복해 보내는 것과 화면 글자를 반복 출력하는 것은 다릅니다.\n\n'
        '명령을 읽는 법\n--rate 2 또는 -r 2는 2 Hz, 즉 약 0.5초마다 한 번입니다. '
        '2초마다 한 번이 아닙니다. --once가 없으면 계속 발행합니다. '
        '일정 횟수만 보내는 확장 옵션은 --times 횟수이며, --once와 함께 쓰지 않습니다.\n\n'
        '결과 확인과 흔한 실수\n터미널 A에서 pub --rate 2를 유지하고 B에서 ros2 topic hz /turtle1/cmd_vel로 수신 빈도를 관찰합니다. '
        '발행을 시작하자마자 끄지 말고 목표 시간 동안 유지한 뒤 A의 Ctrl+C로 종료합니다. B의 hz도 따로 종료합니다. '
        '관찰값은 부하·연결 지연에 따라 조금 달라집니다. 거북이를 실행하는 노드까지 끄는 것은 발행 중단과 다릅니다.'),
    'params': (
        '왜 필요한가\n파라미터는 특정 노드가 가진 설정입니다. 셸의 ROS_DOMAIN_ID 같은 환경변수, 토픽에 흐르는 관측 데이터와 구별하세요.\n\n'
        '명령을 읽는 법\nros2 param list /turtlesim → 해당 노드의 설정 이름\n'
        'ros2 param describe /turtlesim background_r → 타입·설명·제약\n'
        'ros2 param get /turtlesim background_r → 현재 값과 타입\n'
        '/turtlesim은 대상 노드, background_r은 그 노드의 빨강 배경 성분입니다. 설정 이름만으로 모든 노드에 한꺼번에 적용되지 않습니다.\n\n'
        '결과 확인과 흔한 실수\nInteger value is: ...는 정수 값입니다. 목록에 이름이 있다고 항상 변경 가능한 것은 아닙니다. '
        '읽기 전용 여부와 허용 조건을 조사하고 다음 단원에서 변경합니다. 설명 결과와 실제 값은 서로 다른 파일에 저장합니다.'),
    'set': (
        '왜 필요한가\n실행 중인 노드의 설정만 바꿔 반응을 확인합니다. 설정 파일을 고치거나 노드를 새로 실행하는 작업이 아닙니다.\n\n'
        '명령을 읽는 법\nros2 param set /turtlesim background_r 150\n'
        '순서는 노드 → 파라미터 이름 → 새 값입니다. TurtleSim의 background_r/g/b는 RGB 색 성분입니다. '
        '150은 정수, 150.0은 실수이므로 타입을 확인하세요. background_b는 파랑 성분입니다.\n\n'
        '결과 확인과 흔한 실수\n성공 응답 뒤 ros2 param get /turtlesim background_r로 실제 값을 읽고 화면도 봅니다. '
        '변경 거절은 타입·제약·읽기 전용 등의 이유를 확인합니다. set은 설치 파일이나 영구 기본값을 바꾸지 않으므로 노드를 다시 시작하면 이 값이 유지된다고 가정하지 마세요.'),
    'dump': (
        '왜 필요한가\n현재 설정을 파일로 남겨 비교하거나 다시 적용하기 위한 단계입니다. 프로그램·거북이의 위치·실행 상태 전체를 저장하는 기능은 아닙니다.\n\n'
        '명령을 읽는 법\nros2 param dump /turtlesim > turtle.yaml\n'
        'dump가 출력한 YAML을 셸의 >가 저장합니다. 먼저 값을 바꾼 다음 dump해야 변경 후 상태가 남습니다. '
        'turtle.yaml은 임의로 정한 파일명이며 노드 이름과 같을 필요가 없습니다.\n\n'
        '결과 확인과 흔한 실수\ncat turtle.yaml에서 /turtlesim 아래 ros__parameters, 그 아래 background_r의 중첩과 값을 확인합니다. '
        'YAML은 들여쓰기로 구조를 표현합니다. 출력에 읽기 전용 설정이 포함되어도 이상이 아니며 다음 load에서 항목별 결과를 확인합니다.'),
    'load': (
        '왜 필요한가\n저장해 둔 설정을 이미 실행 중인 노드에 적용합니다. 파일이 존재한다는 사실만으로 노드가 설정을 읽은 것은 아닙니다.\n\n'
        '명령을 읽는 법\nros2 param load /turtlesim restore.yaml\n'
        '앞은 적용 대상 노드, 뒤는 현재 폴더 기준 입력 파일입니다. 이름을 바꾼 노드라면 파일의 노드 이름도 적용 대상과 맞는지 확인합니다. '
        '이 문제의 restore.yaml은 준비된 입력이므로 덮어쓰지 않습니다.\n\n'
        '결과 확인과 흔한 실수\nload 결과는 항목별로 성공/거절이 섞일 수 있습니다. ros2 param get으로 background_r과 background_b를 각각 다시 읽으세요. '
        '원하는 항목까지 실패했는데 읽기 전용 경고겠거니 넘기지 않습니다. '
        '노드 시작부터 파일을 적용하는 방식은 run 명령 뒤 --ros-args --params-file 파일을 붙이는 것이며, 실행 중 load와 구별합니다.'),
    'record': (
        '왜 필요한가\nbag은 시간에 따라 흐른 메시지를 남깁니다. 파라미터 파일이나 터미널 출력 로그가 아니라 재생 가능한 통신 데이터입니다.\n\n'
        '명령을 읽는 법\nros2 bag record -o capture /turtle1/cmd_vel /turtle1/pose\n'
        '-o 뒤 capture는 결과 폴더 이름이고, 뒤의 두 이름은 기록할 토픽입니다. '
        '모든 토픽을 수집하는 -a도 있지만 필요한 것만 고르면 불필요한 데이터와 용량을 줄일 수 있습니다.\n\n'
        '결과 확인과 흔한 실수\n터미널 A에서 기록 시작 → pose 구독 확인 → B에서 앞서 배운 --rate 2로 이동 메시지를 계속 발행 → A의 cmd_vel 구독 확인 후 몇 개 더 발행 → B의 발행 종료 → A의 기록 종료 순서입니다. 각각 Ctrl+C로 종료합니다. '
        'B에서도 source가 필요합니다. pose는 가만히 있어도 흐르지만 cmd_vel 발행자가 아직 없으면 기록기의 구독 로그가 먼저 나오지 않을 수 있습니다. '
        '발행 전에 두 구독 로그를 모두 기다리면 서로 기다리게 됩니다. --once의 한 메시지는 기록기가 발견하기 전에 지나갈 수 있으므로 기록할 때는 주기 발행 후 구독을 확인합니다. '
        '종료 후 ros2 bag info capture에서 두 토픽의 메시지 수를 확인하세요. '
        '기존 capture 폴더가 있으면 record가 거부할 수 있습니다. 기존 자료를 무작정 지우지 말고 내용을 먼저 조사합니다.'),
    'baginfo': (
        '왜 필요한가\n재생이나 공유 전에 무엇이 얼마나 기록됐는지 조사합니다. ls로 파일 존재만 보는 것보다 더 많은 정보를 얻습니다.\n\n'
        '명령을 읽는 법\nros2 bag info sample_bag\n'
        'sample_bag은 이번 실습에서 준비한 기록 폴더입니다. 현재 폴더 기준 경로이며 metadata.yaml만 골라 전달하지 않습니다. '
        'Files는 저장 파일, Storage id는 저장 방식, Duration은 기록 시간, Messages는 메시지 수입니다. '
        'Topic information의 Type과 Count로 각 토픽을 따로 확인합니다.\n\n'
        '결과 확인과 흔한 실수\n전체 메시지가 많아도 필요한 토픽의 Count가 0이면 목적에 맞는 기록이 아닙니다. '
        '이 실습은 SQLite .db3를 사용하지만 확장자를 바꾼다고 형식이 변하지 않습니다. '
        'info는 재생하지 않으므로 거북이가 움직이지 않아도 정상입니다. 출력만 bag-info.txt에 저장하고 원본 폴더는 유지합니다.'),
    'play': (
        '왜 필요한가\n원래 발행 프로그램 없이 기록된 입력을 다시 보내 수신 노드의 동작을 시험합니다. 수신할 노드는 별도로 실행되어 있어야 합니다.\n\n'
        '명령을 읽는 법\nros2 bag play sample_bag --delay 2 --topics /turtle1/cmd_vel\n'
        '--topics 뒤에 재생할 토픽 이름을 지정합니다. 같은 기록에 pose가 있어도 여기서는 이동 명령만 보냅니다. '
        '선택을 생략하면 다른 기록 토픽도 발행될 수 있습니다. '
        '--delay 2는 재생기를 준비한 뒤 메시지 발행 시작을 2초 늦춥니다. 짧은 기록은 DDS 상대 발견 전에 시작하면 첫 메시지를 놓칠 수 있어 연결 시간을 줍니다. '
        '재생 명령 앞에 sleep만 넣는 것과 다릅니다. 이 시간은 모든 시스템에서 전달을 보장하는 값은 아닙니다.\n\n'
        '결과 확인과 흔한 실수\n재생 터미널에서 Space는 일시정지/재개, ↑/↓는 속도 조정입니다. 원래 시간 간격을 따르므로 바로 끝나지 않을 수 있습니다. '
        '다른 발행자가 같은 이동 토픽에 명령을 보내면 동작이 섞입니다. 재생 전 불필요한 발행만 종료하고 수신 노드는 유지합니다. '
        'bag은 노드 실행이나 초기 위치를 복원하지 않으므로 같은 메시지를 재생해도 시작 상태가 다르면 같은 경로가 되지 않습니다. '
        '이 연습의 bag에는 이동 메시지가 8개 있습니다. 수신이 부족하면 수신 노드를 유지하고 대기 시간을 늘려 다시 재생할 수 있습니다.'),
    'domain': (
        '왜 필요한가\n도메인은 서로 발견하고 통신할 ROS 집단을 구분합니다. 이름공간은 같은 집단 안의 이름 구분입니다. 둘은 다른 역할입니다.\n\n'
        '명령을 읽는 법\nexport ROS_DOMAIN_ID=42는 이후 이 셸이 시작할 ROS 프로세스에 도메인 42를 전달합니다. '
        '42는 이 문제에서 고른 값이며 모든 ROS 실습의 고정값이나 서버 포트가 아닙니다.\n'
        '--ros-args는 ROS 전용 인자를 시작합니다. -r은 remap(이름 재지정), __node:=turtle1234는 노드 이름, __ns:=/team은 이름공간입니다. '
        '합쳐진 전체 이름은 /team/turtle1234입니다. :=를 =와 혼동하지 마세요.\n\n'
        '결과 확인과 흔한 실수\n실행 터미널과 조회 터미널 각각에서 source 후 export하고 ros2 node list로 조사합니다. '
        '다른 셸에서 export해도 이미 실행 중인 노드의 도메인은 바뀌지 않습니다. '
        '이전 도메인으로 실행했다면 그 작업을 정상 종료한 뒤 올바른 환경에서 다시 실행합니다. '
        '도메인 구분은 인증/보안 경계가 아닙니다.'),
    'service': (
        '왜 필요한가\n토픽은 메시지 흐름, 서비스는 한 요청에 대한 응답입니다. 새 거북이 생성처럼 처리 결과를 받아야 하는 작업에 사용합니다.\n\n'
        '명령을 읽는 법\nros2 service list → 서비스 이름 조사\n'
        'ros2 service type /spawn → 요청할 서비스의 타입 조사\n'
        'ros2 interface show turtlesim/srv/Spawn → --- 앞은 요청 필드, 뒤는 응답 필드\n'
        'call 뒤에는 서비스 이름, 서비스 타입, YAML 요청을 넣습니다. srv는 서비스 정의로 메시지의 msg와 다릅니다. '
        'x/y는 생성 위치, theta는 라디안 방향, name은 새 거북이 이름입니다.\n\n'
        '결과 확인과 흔한 실수\n응답의 name과 화면의 새 거북이, /helper/pose 토픽을 확인합니다. '
        'helper라는 별도 ROS 노드를 만드는 것이 아니라 기존 /turtlesim 노드가 거북이를 추가합니다. '
        '같은 이름을 다시 요청하면 충돌할 수 있습니다. /reset으로 전체를 지워 문제를 해결하면 기존 turtle1 보존 조건을 해칠 수 있습니다.'),
    'action': (
        '왜 필요한가\n액션은 시간이 걸리는 작업에 목표·피드백·최종 결과를 연결합니다. 단순 응답형 서비스와 달리 수행 도중 진행을 관찰하거나 취소를 요청할 수 있습니다.\n\n'
        '명령을 읽는 법\nros2 action list -t로 이름과 타입, ros2 action info /turtle1/rotate_absolute로 연결을 조사합니다. '
        'ros2 interface show turtlesim/action/RotateAbsolute는 ---로 구분된 목표·결과·피드백 구조를 보여 줍니다.\n'
        'send_goal 뒤에는 액션 이름 → 타입 → YAML 목표가 옵니다. "{theta: 1.57}"는 약 90도의 절대 방향입니다. '
        '현재 방향에서 90도를 더 돌거나 1.57의 속도를 유지하라는 뜻이 아닙니다. --feedback은 중간 피드백 표시 옵션입니다.\n\n'
        '결과 확인과 흔한 실수\nGoal accepted는 접수, SUCCEEDED는 완료 성공입니다. 최종 상태와 실제 방향을 함께 확인하세요. '
        '이동 토픽의 다른 발행이 동작을 방해할 수 있으므로 불필요한 발행만 멈춥니다. '
        'CLI를 Ctrl+C로 닫는 것을 서버 작업의 정상 완료나 취소 확인으로 대신하지 않습니다.'),
}


def expanded_explanation(key, original):
    """Keep the existing scope, then teach the arguments and extra objectives."""
    handoff = REPORT_GUIDE if key in REPORT_KEYS else NODE_REPORT_GUIDE
    return '\n\n'.join((original, GUIDES[key], TERMINAL_GUIDE, FILE_GUIDE, handoff))
