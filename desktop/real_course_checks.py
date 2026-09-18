"""Reviews follow the real course's teaching blocks, not old storage indexes."""
from dataclasses import dataclass, replace
from copy import deepcopy
import shlex


@dataclass(frozen=True)
class CourseCheckpoint:
    end: int
    title: str
    kind: str
    key: str
    units: tuple
    legacy_end: int = 0

    @property
    def label(self): return self.title


LINUX_TITLES = (
    '경로와 목록·문서 확인', '목록과 작업 위치 인계', '전체 구조와 작업 폴더 준비',
    '공백 경로의 원본 보존과 정리', '로그의 필요한 부분 인계', '검색·필터와 도구 준비',
    '다운로드 자료 조사와 실행', '셸 환경·작업·패키지 조합', '사용자 조사와 파일 권한',
    '파일·폴더 권한과 소유권 인계', '그룹 준비와 새 계정 설정', '계정 인계와 그룹 보존',
    '패키지 조사·의존성 복구와 설정 인계',
    '암호 설정·로그인 환경과 최소 권한 인계',
    '현재 셸 설정과 안전한 문서 생성',
    '프로세스 조사와 안전한 서비스 종료',
    '문서 조사·입력 종료와 실행 도구 인계',
    '시스템·네트워크·시계 조사 인계',
)


def checkpoints(linux, docker, ros):
    result = [CourseCheckpoint(end, LINUX_TITLES[end // 5 - 1], 'linux_review',
                               f'real-linux-v2-{end:02d}', linux[end - 5:end])
              for end in range(5, len(linux) + 1, 5)]
    for offset, title, kind, key, legacy in (
        (5, '컨테이너 생성·파일 작업·정리', 'sim_review35', 'checkpoint-35', 35),
        (10, '이미지 갱신·보관·실행 설정', 'sim_review40', 'checkpoint-40', 40),
        (15, '데이터 보존과 서비스 배포 복구', 'docker_review', 'docker-checkpoint-deployment', 0),
        (20, '주 셸 유지·이미지 인계와 선별 정리', 'docker_sessions_review', 'docker-checkpoint-sessions', 0),
        (25, 'HTTP 응답·자원 설정·최소 권한 인계', 'docker_runtime_review', 'docker-checkpoint-runtime', 0)):
        result.append(CourseCheckpoint(len(linux) + offset, title, kind, key, docker[offset - 5:offset], legacy))
    for offset, title in ((5, '환경과 다중 노드 실행'), (10, '메시지 조사와 주기적 발행'),
                          (15, '설정 보관과 메시지 기록'), (20, '기록 재생과 서비스·액션')):
        old_end = 40 + offset
        result.append(CourseCheckpoint(len(linux) + len(docker) + offset, title, f'ros_review{old_end}',
                                       f'checkpoint-{old_end:02d}', ros[offset - 5:offset]))
    return tuple(result)


def make_review(checkpoint, seed=None):
    from missions import make_mission
    if checkpoint.kind != 'linux_review':
        m = make_mission(checkpoint.kind, seed)
    else:
        m = linux_review(checkpoint.end, seed)
    return replace(m, review=dict(m.review, checkpoint=checkpoint.key,
                                  units=[u.key for u in checkpoint.units], title=checkpoint.title))


def linux_review(end, seed):
    from missions import make_mission
    from checkpoints import make_legacy_checkpoint
    if end == 90:
        return make_mission('system_review', seed)
    if end == 20:
        return make_legacy_checkpoint(15, seed)  # All cp/mv/rm/mkdir prerequisites now precede this block.
    if end == 40:
        return make_mission('sim_review30', seed)
    if end == 60:
        return make_mission('admin_review', seed)
    if end == 65:
        return make_mission('apt_review', seed)
    if end == 70:
        return make_mission('auth_review', seed)
    if end == 75:
        return make_mission('shell_review', seed)
    if end == 80:
        return make_mission('process_review', seed)
    if end == 85:
        return make_mission('io_review', seed)
    if end in (45, 50, 55):
        return admin_review(end, seed)
    m = make_mission('pwdpaths' if end == 5 else 'edit' if end == 15 else 'script' if end == 35 else 'long', seed)
    s, t, r, q = m.source, m.target, m.report, shlex.quote
    def file(path, text): return {'type': 'file', 'path': path, 'text': text}
    def copy(path, source): return {'type': 'copy', 'path': path, 'source': source}
    def listing(path, options): return {'type': 'listing', 'path': path, 'source': s, 'options': options}
    def directory(path): return {'type': 'dir', 'path': path}
    setup, goals = [], []
    if end == 5:
        prompt = (f'{m.start}/shortcut 바로가기로 들어가 논리 경로와 실제 경로를 각각 화면에 표시하세요. '
                  f'{s}의 숨김 항목과 .·..를 포함한 상세 목록을 화면에 표시하고, '
                  f'{s}/guide.txt와 {s}/docs/read me.txt 두 원본의 내용을 읽으세요. 마지막 위치는 {s}/docs입니다.')
        solution = f'cd {q(m.start + "/shortcut")}\npwd -L\npwd -P\nls -al {q(s)}\ncat ../guide.txt "read me.txt"'
        goals = [{'type': 'output', 'text': m.start + '/shortcut'}, {'type': 'output', 'text': s + '/docs'},
                 {'type': 'output_listing', 'source': s, 'options': '-al'},
                 {'type': 'output', 'text': f'Release {m.seed} user guide'}, {'type': 'output', 'text': 'A file name with spaces'},
                 file(s + '/guide.txt', f'Release {m.seed} user guide\n'), file(s + '/docs/read me.txt', 'A file name with spaces\n'),
                 {'type': 'cwd', 'path': s + '/docs'}]
    elif end == 10:
        setup = [file(s + '/large-sample.bin', 'X' * 16384), file(r, 'outdated inventory\n')]
        prompt = (f'{s}로 이동하세요. 현재 디렉터리의 절대경로는 {r}.where에 저장하세요. '
                  f'기존 {r}은 숨김 항목과 .·..를 포함한 상세 목록으로 덮어쓰되 크기는 K/M 단위로 표시하세요. '
                  f'숨김 항목을 제외한 이름 목록은 큰 크기순으로 {r}.largest에 한 줄씩 저장하세요. 마지막에도 그 폴더에 머무세요.')
        solution = f'cd {q(s)}\npwd > {q(r + ".where")}\nls -alh > {q(r)}\nls -1S > {q(r + ".largest")}'
        goals = [file(r + '.where', s + '\n'), listing(r, '-alh'), listing(r + '.largest', '-1S'), {'type': 'cwd', 'path': s}]
    elif end == 15:
        prompt = (f'{s}의 숨김 포함 전체 하위 구조를 상세 형식으로 {r}에 저장하세요. '
                  f'{t} 안에 handover 폴더와 그 안의 빈 done.txt를 만드세요. '
                  f'{t}/note.txt의 status=draft를 status=ready로 수정해 저장한 뒤 편집기를 종료하세요.')
        solution = f'ls -alR {q(s)} > {q(r)}\ncd {q(t)}\nmkdir handover\ntouch handover/done.txt\nnano note.txt'
        goals = [listing(r, '-alR'), directory(t + '/handover'), file(t + '/handover/done.txt', ''), file(t + '/note.txt', 'status=ready\n')]
    elif end == 25:
        log = s + '/app.log'
        prompt = (f'{s}로 이동해 숨김 포함 상세 목록을 {r}에 저장하세요. app.log의 첫 2줄은 {r}.head에, '
                  f'마지막 2줄은 {r}.tail에, 대문자 ERROR가 있는 줄은 {r}.errors에 저장하세요. '
                  f'원본 로그 전체의 줄 수만 {r}.count에 기록하세요. 원본은 유지하세요.')
        solution = f'cd {q(s)}\nls -al > {q(r)}\nhead -n 2 app.log > {q(r + ".head")}\ntail -n 2 app.log > {q(r + ".tail")}\ngrep ERROR app.log > {q(r + ".errors")}\nwc -l < app.log > {q(r + ".count")}'
        goals = [listing(r, '-al'), file(r + '.head', 'INFO start\nERROR disk full\n'), file(r + '.tail', 'INFO ready\nError network\n'),
                 file(r + '.errors', 'ERROR disk full\n'), {'type': 'stripped_file', 'path': r + '.count', 'text': '6'},
                 file(log, 'INFO start\nERROR disk full\nwarning warm\nerror timeout\nINFO ready\nError network\n')]
    elif end == 30:
        m = make_mission('curl', m.seed)
        downloaded = t + '/received-' + m.artifact
        prompt = (f'{s}/app.log에서 대소문자와 관계없이 error가 포함된 줄의 개수만 {r}.count에 저장하세요. '
                  f'{s} 아래의 .deb 일반 파일 경로를 {r}에 저장하세요. '
                  f'{m.url}을 {downloaded}에 내려받으세요. 다른 원본은 변경하지 마세요.')
        solution = f'grep -i error {q(s + "/app.log")} | wc -l > {q(r + ".count")}\nfind {q(s)} -type f -name "*.deb" > {q(r)}\ncurl -fL -o {q(downloaded)} {m.url}'
        # Reference find paths are deterministic from the same prepared tree.
        from lab.lab import tree_paths
        hidden, nested = tree_paths(m.payload())
        expected = '\n'.join([s + '/toolkit.deb', s + '/' + hidden + '/extra.deb', s + '/' + nested + '/agent.deb'])
        goals = [{'type': 'stripped_file', 'path': r + '.count', 'text': '3'}, copy(downloaded, s + '/' + m.artifact),
                 {'type': 'line_set', 'path': r, 'text': expected}]
    elif end == 35:
        archive = m.url.rsplit('/', 1)[0] + '/bundle.tar.gz'
        prompt = (f'{archive}를 {t}/bundle.tar.gz로 받아 내부 목록을 {r}.archive에 저장한 뒤 {t}/unpacked에 푸세요. '
                  f'{m.url}도 {t}/received-setup.sh로 받아 읽고, 소유자 실행 권한을 추가한 뒤 {t}/receipt.txt를 결과 경로로 넘겨 실행하세요. '
                  f'{s}/toolkit.deb의 패키지 정보는 {r}.package에 저장하세요.')
        solution = f'cd {q(t)}\nwget -O bundle.tar.gz {archive}\ntar -tzf bundle.tar.gz > {q(r + ".archive")}\nmkdir unpacked\ntar -xzf bundle.tar.gz -C unpacked\ncurl -fL -o received-setup.sh {m.url}\ncat received-setup.sh\nchmod u+x received-setup.sh\n./received-setup.sh receipt.txt\ndpkg-deb --info {q(s + "/toolkit.deb")} > {q(r + ".package")}'
        goals = [file(r + '.archive', 'README.txt\nbin/\nbin/hello.sh\n'), file(t + '/unpacked/README.txt', 'Shellground training bundle\nVersion 1.0\n'),
                 file(t + '/unpacked/bin/hello.sh', '#!/bin/sh\nprintf "Hello from Linux\\n"\n'),
                 file(t + '/receipt.txt', 'Linux script completed\n'), {'type': 'executable', 'path': t + '/received-setup.sh', 'value': True},
                 {'type': 'file_contains', 'path': r + '.package', 'text': 'Package: shellground-toolkit'}]
    else:
        raise ValueError(end)
    return replace(m, prompt=prompt, solution=solution, review={'setup': setup, 'goals': goals, 'keep_base': False})


def admin_review(end, seed):
    from missions import make_mission
    if end == 45:
        m = make_mission('admin_identity', seed, 2)
        p = deepcopy(m.review)
        p['files']['notes.txt'] = {'type': 'file', 'text': 'private notes\n', 'mode': 0o666, 'uid': 1100, 'gid': 1100}
        p['expected_files']['notes.txt'] = dict(p['files']['notes.txt'], mode=0o640)
        return replace(m, prompt=m.prompt + '\nnotes.txt는 소유자 읽기·쓰기, 그룹 읽기만 허용하고 나머지는 접근 불가로 설정하세요. 내용을 유지하세요.',
                       solution=m.solution + '\nchmod u=rw,g=r,o= notes.txt', review=p)
    if end == 50:
        m = make_mission('admin_owners', seed, 0)
        p = deepcopy(m.review)
        p['files']['private'] = {'type': 'dir', 'text': '', 'mode': 0o600, 'uid': 1100, 'gid': 1100}
        p['expected_files']['private'] = dict(p['files']['private'], mode=0o700)
        return replace(m, prompt=m.prompt + '\nprivate 폴더는 소유자만 읽기·쓰기·탐색할 수 있도록 권한을 복구하세요.',
                       solution=m.solution + '\nchmod 700 private', review=p)
    m = make_mission('admin_user_primary', seed, 0)
    p = deepcopy(m.review)
    dev = 'sgdev' + str(m.seed)
    gid = p['groups'].pop(dev)
    return replace(m, prompt=f'GID={gid}인 {dev} 그룹을 먼저 만드세요.\n' + m.prompt.replace('준비된 ' + dev, dev),
                   solution=f'sudo groupadd -g {gid} {dev}\n' + m.solution, review=p)
