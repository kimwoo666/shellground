"""Per-lesson explanation of state changes, option positions and mistakes.

This is teaching content, not a shell implementation or an answer matcher.
The canonical examples remain the executable, seeded mission solutions.
"""

GUIDES = {
    'images': (
        '명령을 읽는 법\ndocker pull 이미지이름:태그 → 저장소에서 로컬 Docker로 이미지를 가져옵니다. 아직 실행하지 않습니다.\n'
        'ubuntu는 이미지 이름, 24.04는 태그입니다. 태그는 버전처럼 쓰는 이름표이며, 같은 태그가 나중에 다른 내용을 가리킬 수도 있습니다.\n'
        'docker images의 REPOSITORY는 이미지 이름, TAG는 태그, IMAGE ID는 내용의 식별자입니다. 컨테이너 ID와는 다릅니다.\n\n'
        '결과 확인과 흔한 실수\n이미지를 받았는지는 docker images, 실행한 컨테이너가 있는지는 docker ps -a로 확인합니다. pull 성공은 컨테이너 실행 성공이 아닙니다.\n'
        '명령에서 [옵션] 같은 대괄호는 설명용 표기이지 직접 입력하는 글자가 아닙니다. 아래 예시의 이미지 이름·태그는 한 덩어리로 입력하세요.'),
    'run': (
        '명령을 읽는 법\ndocker run [Docker 옵션] 이미지 [컨테이너 안에서 실행할 명령과 인자]\n'
        '--name box는 컨테이너 이름을 box로 정합니다. -d는 터미널을 점유하지 않는 분리 실행이고, 뒤의 sleep 300은 컨테이너 안에서 300초 동안 기다리는 명령입니다.\n'
        '옵션은 이미지 앞에 둡니다. 이미지 뒤의 -d는 Docker 옵션이 아니라 실행할 프로그램 쪽 인자로 해석될 수 있습니다.\n\n'
        '결과 확인과 흔한 실수\ndocker ps의 STATUS가 Up이면 실행 중이고, docker ps -a에서 Exited이면 주 프로세스가 끝난 상태입니다.\n'
        '컨테이너는 켜 둔 컴퓨터처럼 영원히 대기하지 않습니다. 주 명령이 끝나면 종료되며 -d도 이를 막지 않습니다. 이름 충돌은 같은 이름의 컨테이너가 이미 있다는 뜻입니다.'),
    'lifecycle': (
        '명령을 읽는 법\ndocker stop box → 종료 요청 후 필요하면 제한시간 뒤 강제 종료합니다. 삭제 명령은 아닙니다.\n'
        'docker start box → 기존 설정과 기존 쓰기 영역을 가진 같은 컨테이너를 다시 시작합니다.\n'
        'docker restart box → 기존 컨테이너를 중지한 뒤 다시 시작합니다. 새 이미지로 교체하는 기능은 아닙니다.\n\n'
        '결과 확인과 흔한 실수\n시작 전후 docker ps -a의 CONTAINER ID가 같은지, STATUS만 바뀌는지 확인하세요. 새 명령·환경변수·마운트로 교체할 때는 단순 start로 바뀌지 않습니다.\n'
        'run을 다시 하면 새 컨테이너를 만들려는 것입니다. 같은 이름 오류를 피하려고 원래 컨테이너를 삭제하면, “같은 ID 유지” 목표를 어길 수 있습니다.'),
    'exec': (
        '명령을 읽는 법\ndocker exec box 명령 → 실행 중인 box 안에서 추가 프로세스를 시작합니다.\n'
        '-i는 입력을 열어 두고, -t는 터미널을 할당합니다. -it는 둘을 함께 쓴 것으로 대화형 셸에 사용합니다. 이미지에 bash가 없으면 sh를 사용합니다.\n'
        "docker exec box bash -c 'printf \"ready\\n\" > /tmp/note.txt'에서 작은따옴표 안은 컨테이너 셸이 해석합니다.\n\n"
        '결과 확인과 흔한 실수\n>를 따옴표 밖에 쓰면 바깥 실습 셸이 처리해 실습 호스트에 파일을 만듭니다. 컨테이너 안 파일은 docker exec box cat /tmp/note.txt로 확인하세요.\n'
        'exec 셸에서 exit하면 그 추가 셸만 끝납니다. 컨테이너의 원래 주 프로세스를 종료하는 것과 다릅니다. 중지된 컨테이너에는 exec할 수 없습니다.'),
    'cleanup': (
        '명령을 읽는 법\ndocker rm 컨테이너이름 → 컨테이너와 그 고유 쓰기 영역을 삭제합니다.\n'
        'docker rmi 이미지:태그 → 이미지 이름표를 제거하고, 다른 참조가 없으면 이미지 삭제까지 수행합니다. 이름/ID를 서로 혼동하지 마세요.\n'
        '일반적인 정리 순서는 대상 확인 → stop → rm → 필요 없는 이미지의 rmi입니다.\n\n'
        '결과 확인과 흔한 실수\ndocker ps -a와 docker images로 없앨 대상과 남길 대상을 각각 확인하세요. 실행 중인 컨테이너나 남은 참조 때문에 삭제가 거절되면 오류 이유부터 읽습니다.\n'
        'rm -f는 강제 종료·삭제입니다. 전체 prune이나 모든 ID를 넘기는 명령은 보호할 자원도 지울 수 있으므로 이 문제의 해법으로 사용하지 마세요.'),
    'update': (
        '무엇이 바뀌는가\n태그 → 이미지 ID → 그 이미지로 만든 컨테이너를 구분합니다. pull은 태그가 가리키는 로컬 이미지를 갱신하지만 이미 만든 컨테이너의 기반 이미지는 그대로입니다.\n'
        '교체 순서: 새 이미지 받기 → 기존 컨테이너 중지 → 필요한 데이터 보존 확인 → 기존 컨테이너 삭제 → 새 이미지로 생성.\n\n'
        '결과 확인과 흔한 실수\ndocker image inspect 이미지:태그의 Id와 docker inspect 컨테이너의 Image를 비교합니다. 새 컨테이너는 새 이미지 ID를 사용해야 합니다.\n'
        'docker restart만으로는 새 버전이 적용되지 않습니다. 이미지 태그 이름이 같다는 것만으로 내용도 같다고 판단하지 마세요.\n'
        '컨테이너 고유 파일은 삭제하면 잃을 수 있습니다. 이 과정 뒤의 볼륨 단원에서 컨테이너와 데이터의 수명을 분리합니다.'),
    'tag': (
        '명령을 읽는 법\ndocker tag 원본이미지:태그 새이름:새태그\n'
        '앞은 이미 존재하는 이미지 참조, 뒤는 추가할 이름표입니다. 컨테이너 이름을 붙이는 --name과 다른 작업입니다.\n'
        '같은 이미지에 training:v1을 붙여도 실행 중인 컨테이너나 이미지 내용은 변경되지 않습니다.\n\n'
        '결과 확인과 흔한 실수\ndocker images에서 두 행의 이름/태그가 달라도 IMAGE ID가 같으면 같은 이미지입니다. 행의 SIZE를 단순 합산하면 공유된 내용을 중복 계산할 수 있습니다.\n'
        '원래 태그 보존이 목표라면 새 태그를 붙인 뒤 원래 태그를 rmi하지 않습니다. “새 내용 만들기”는 tag가 아니라 뒤에서 다룰 commit 또는 build입니다.'),
    'commit': (
        '명령을 읽는 법\ndocker commit 원본컨테이너 새이미지:태그\n'
        '컨테이너의 쓰기 영역 변경을 새 이미지로 남깁니다. 원래 기반 이미지를 직접 수정하는 명령이 아닙니다.\n'
        '예시 흐름은 exec로 파일 작성 → commit → 새 이미지로 다른 컨테이너 생성 → 그 안에서 cat으로 파일 확인입니다.\n\n'
        '결과 확인과 흔한 실수\n원본 컨테이너에서만 파일을 확인하면 새 이미지에 들어갔는지 알 수 없습니다. 새 컨테이너에서 확인해야 합니다.\n'
        'RAM·실행 중 위치를 저장하지 않으며 마운트된 볼륨 데이터도 이미지에 포함하지 않습니다. 기본적으로 일관성 확보를 위해 commit 중 컨테이너를 잠시 멈춥니다. 재현 가능한 제작 과정은 뒤의 Dockerfile로 배웁니다.'),
    'save': (
        '명령을 읽는 법\ndocker save -o images.tar 이미지:태그\n-o 뒤는 보관할 파일 경로, 마지막은 이미지 참조입니다. 파일 이름의 .tar와 이미지 태그는 별개의 이름입니다.\n'
        'docker load -i images.tar 또는 docker load < images.tar로 복원합니다. -i는 입력 파일 지정이고 <는 셸의 입력 연결입니다.\n\n'
        '결과 확인과 흔한 실수\n파일을 만들었다는 사실과 복원 가능성은 다릅니다. 실습은 로컬 이미지를 제거한 뒤 아카이브에서 되살려 확인합니다.\n'
        'save/load는 이미지 보관·복원이며, 실행 중 컨테이너나 볼륨 데이터의 전체 백업이 아닙니다. export/import와 목적 및 보존 정보가 다릅니다. 복원 시험 중 다시 pull하면 파일로 복원했는지 확인할 수 없습니다.'),
    'limits': (
        '옵션을 한 개씩 읽기\n-e APP_MODE=training: 컨테이너의 환경변수입니다. 바깥 셸의 환경변수를 바꾸지 않습니다.\n'
        '-p 8080:80: 실습 호스트의 8080을 컨테이너의 80으로 연결합니다. 방향은 호스트:컨테이너입니다.\n'
        '--memory 128m: 메모리 한도를 설정합니다. --cpus 1: CPU 한 개 분량의 시간 한도이며 특정 코어 하나에 고정한다는 뜻은 아닙니다.\n\n'
        '결과 확인과 흔한 실수\ninspect에서 Config.Env, HostConfig.PortBindings/Memory/NanoCpus를 확인합니다. 설정값과 현재 사용량은 다릅니다.\n'
        '포트를 지정해도 서버가 저절로 생기지 않습니다. 이 단원의 sleep은 웹서버가 아니며 여기서는 포트 설정을 평가합니다. 실제 모드에서 “호스트”는 사용자 PC가 아니라 앱 전용 Linux입니다.'),
    'bind': (
        '옵션을 한 개씩 읽기\n--mount type=bind,src=원본절대경로,dst=/input,readonly\n'
        'src는 실습 Linux 쪽의 기존 경로, dst는 컨테이너 안에서 보일 위치입니다. 파일을 복사하는 대신 같은 자료를 연결합니다. readonly는 컨테이너 쪽 쓰기를 막습니다.\n'
        '-v "원본절대경로:/input:ro"도 같은 목적입니다. 공백을 포함한 경로와 연결 구분자를 하나의 인자로 묶으세요.\n\n'
        '결과 확인과 흔한 실수\n입력은 ro, 결과 폴더는 rw로 분리합니다. inspect의 Mounts에서 경로와 RW=false/true를 함께 확인하세요.\n'
        'rw여도 Linux 소유권/권한이 쓰기를 막을 수 있습니다. -u의 숫자 UID/GID와 대상 폴더 소유자를 함께 확인합니다. 문제 해결을 위해 원본까지 전부 쓰기 가능하게 바꾸지 마세요.'),
    'volume': (
        '명령을 읽는 법\ndocker volume create notes → notes라는 저장소를 준비합니다.\n'
        '--mount type=volume,src=notes,dst=/data → 그 저장소를 컨테이너의 /data에 연결합니다. src는 경로가 아니라 볼륨 이름입니다.\n'
        '컨테이너 교체 뒤에도 같은 볼륨을 다시 연결해야 예전 데이터가 보입니다. 이름을 조금 다르게 쓰면 다른 빈 저장소를 만들 수 있습니다.\n\n'
        '결과 확인과 흔한 실수\nvolume ls/inspect로 이름을 확인하고, 데이터를 읽는 컨테이너에서 실제 파일을 확인합니다. 컨테이너 존재만으로 자료 보존을 판단하지 마세요.\n'
        '백업할 때 원본은 읽기 전용, 백업 경로는 쓰기 가능으로 연결합니다. 복원은 새 볼륨에서 확인한 뒤 원본 보존을 점검합니다. --rm은 이름 있는 볼륨을 자동으로 없애지 않습니다.'),
    'network': (
        '명령을 읽는 법\ndocker network create teamnet → 통신할 사용자 정의 bridge를 만듭니다.\n'
        '--network teamnet은 시작할 때 참가할 네트워크이고, --network-alias api는 그 네트워크에서 사용할 추가 DNS 이름입니다.\n'
        'docker network connect teamnet box는 기존 box를 추가 연결하며, disconnect는 특정 연결만 제거합니다. 컨테이너를 다시 만들 필요가 없습니다.\n\n'
        '결과 확인과 흔한 실수\nnetwork inspect에서 두 컨테이너가 같은 네트워크에 있는지 보고, 한쪽에서 상대 별칭으로 ping해 실제 통신을 확인합니다. ping -c 1은 한 번, -W 2는 응답 대기시간 2초입니다.\n'
        '연결 설정이 있다는 사실과 통신 성공은 별도입니다. 서로 다른 네트워크의 별칭이나 기본 bridge의 이름 검색을 같은 동작으로 가정하지 마세요. -p는 이 내부 통신에 필요한 옵션이 아닙니다.'),
    'build': (
        '명령을 읽는 법\ndocker build --network=none -t training/report:v1 app\n'
        '-t 뒤는 만들 이미지 이름:태그, 마지막 app은 빌드할 자료 폴더입니다. 기본 Dockerfile도 그 안에서 찾으며 COPY의 원본은 그 폴더 기준입니다.\n'
        'FROM → 기반 이미지, COPY → 파일 넣기, RUN → 빌드 중 실행, WORKDIR → 이후 기본 경로, USER → 기본 UID/GID, ENV → 환경변수, CMD → 시작할 때 기본 명령입니다.\n\n'
        '결과 확인과 흔한 실수\nCOPY 뒤 파일명은 현재 터미널 위치가 아니라 빌드 문맥 기준입니다. CMD ["cat", "message.txt"]는 이미지 제작 중이 아니라 나중에 컨테이너를 실행할 때 동작합니다.\n'
        '소스 파일을 바꾼 뒤에는 다시 build해야 이미지에 반영됩니다. 기본 실행 검증은 이미지 뒤에 다른 명령을 붙이지 않은 run으로 합니다. 이전 v1을 보존하려면 새 결과를 v2로 구분하세요.'),
    'diagnose': (
        '조사 순서\n1. ps -a로 종료 상태 확인 → 2. logs로 실패 원인 확인 → 3. inspect로 종료 코드·마운트·사용자 확인 → 4. 필요한 파일만 복구 → 5. 같은 컨테이너 start.\n'
        "docker inspect --format '{{.State.ExitCode}}' 이름은 JSON 전체 대신 종료 코드 필드만 출력합니다. 작은따옴표와 중괄호도 형식의 일부입니다.\n\n"
        '기록과 결과 확인\n> failure.log 2>&1에서 먼저 표준 출력을 파일로 연결하고, 표준 오류(2)도 같은 출력(1)에 연결합니다. >만 쓰면 오류 기록이 터미널에 남을 수 있습니다.\n'
        '종료 코드는 시작하기 전에 기록하세요. 재시작 후에는 상태 정보가 바뀝니다. 이 문제의 42/44/13은 준비된 프로그램이 반환한 값이지 모든 Docker 오류의 공통 번호가 아닙니다.\n'
        '복구 후 정상 로그와 실행 상태를 함께 확인합니다. 원인 파일 대신 service.sh를 우회 수정하거나 컨테이너를 삭제·재생성하면 목표를 만족하지 않습니다.'),
}


REPORT_GUIDE = (
    '활용 2의 추가 조사: 작업 결과를 파일로 남기기\n'
    '먼저 컨테이너 생성·시작·중지·삭제나 이미지 작업을 모두 끝낸 뒤 목록을 저장합니다.\n'
    'docker ps -a > containers.txt\n'
    'docker images > images.txt\n'
    'ps는 실행 중만, ps -a는 종료된 것까지 포함한 전체 컨테이너 목록입니다. -a는 all의 뜻이며 images 목록과는 다른 대상입니다.\n'
    '>는 Docker 옵션이 아니라 바깥 셸의 출력 저장 기호입니다. 왼쪽 명령의 표준 출력을 화면 대신 오른쪽 파일에 쓰고, 기존 파일이 있으면 덮어씁니다. >>는 덧붙이기라 최신 목록 한 벌을 만드는 이번 목적과 다릅니다.\n'
    '파일은 컨테이너 안이 아니라 현재 실습 셸 위치에 생성됩니다. 문제의 두 보고서는 시작 폴더에 두세요. 다른 폴더로 이동했다면 시작 폴더로 돌아가거나 그 전체 경로를 지정합니다.\n'
    'cat containers.txt\ncat images.txt\n'
    'cat으로 실제 내용이 저장됐는지 확인합니다. 파일 이름만 만들거나 빈 파일을 두는 것은 목록 저장이 아닙니다.\n'
    '이 파일은 자동 갱신되는 화면이 아니라 저장한 순간의 기록입니다. 저장 후 컨테이너 상태나 이미지가 바뀌었다면 두 목록을 다시 저장해야 “작업 후의 상태”가 됩니다.'
)


def expanded_explanation(key, original):
    short = key.removeprefix('sim_').removeprefix('docker_')
    guide = GUIDES.get(short)
    if not guide: return original
    text = original + '\n\n' + guide
    if short in {'images', 'run', 'lifecycle', 'exec', 'cleanup', 'update', 'tag', 'commit', 'save', 'limits'}:
        text += '\n\n' + REPORT_GUIDE
    return text


REGISTRY_GUIDE = (
    '이 앱의 실제 모드에서 이미지 주소 읽기\n'
    'localhost:5000/training/ubuntu:24.04\n'
    'localhost:5000 = 앱 전용 Linux 안의 교육용 저장소 주소와 포트\n'
    'training/ubuntu = 교육용 이름 공간 training 아래의 이미지 이름 ubuntu\n'
    '마지막 :24.04 = 이미지의 태그\n'
    '따라서 첫 번째 :5000과 마지막 :24.04는 역할이 다릅니다. 긴 주소 전체가 하나의 이미지 참조입니다. '
    'Ubuntu 설치용 ISO를 받거나 사용자 PC에 운영체제를 설치하는 작업이 아닙니다.\n\n'
    '왜 localhost:5000/training/을 쓰나요?\n'
    '이 앱은 외부 인터넷 없이도 내려받기·갱신·복원을 연습하도록, 공식 Ubuntu/Alpine을 기반으로 한 교육용 이미지를 전용 Linux 안의 레지스트리(이미지 저장 서버)에 준비합니다. 실제 Docker가 그 서버에서 이미지를 받습니다.\n'
    'localhost는 그 실습 Linux 자신입니다. 사용자 PC의 브라우저 주소나 Docker Hub 주소가 아닙니다. 5000은 이 앱이 저장 서버에 정한 접속 포트이며 모든 Docker 명령에 반드시 붙이는 숫자가 아닙니다.\n'
    'training은 교육용 이미지를 구분하려고 정한 이름 공간입니다. Linux 파일 경로가 아니므로 cd /training을 하지 않습니다. 다른 저장소에서는 다른 이름을 쓸 수 있습니다.\n'
    'ubuntu:24.04처럼 저장소 주소를 생략하면 기본적으로 Docker Hub의 library/ubuntu:24.04를 뜻합니다. '
    '이 앱의 교육용 이미지와는 참조가 다르므로 여기서는 문제에 적힌 localhost:5000/training/ubuntu:24.04 전체를 입력합니다. '
    '일반적인 인터넷 연결 Docker 환경에서 항상 이 접두사를 쓰라는 뜻은 아닙니다.'
)
