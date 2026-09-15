"""Five-unit checkpoints: one shared workspace and a combined outcome."""
from dataclasses import dataclass, replace
import shlex

from missions import UNITS, make_mission
from path_practice import natural_paths


@dataclass(frozen=True)
class Checkpoint:
    end: int
    title: str
    kind: str

    @property
    def key(self):
        return f'checkpoint-{self.end:02d}'

    @property
    def units(self):
        return UNITS[self.end - 5:self.end]

    @property
    def label(self):
        return f'{self.end - 4:02d}–{self.end:02d} 종합 복습 · {self.title}'


CHECKPOINTS = (
    Checkpoint(5, '새 작업 공간 준비', 'read'),
    Checkpoint(10, '설정 수정과 인계 정리', 'edit'),
    Checkpoint(15, '자료 보관과 목록 인계', 'mixed'),
    Checkpoint(20, '릴리스 구조·로그 조사', 'find'),
    Checkpoint(25, '도구 내려받기와 실행 준비', 'script'),
    Checkpoint(30, '환경·작업·패키지 관리', 'sim_review30'),
    Checkpoint(35, '컨테이너 생성·파일 작업·정리', 'sim_review35'),
    Checkpoint(40, '이미지 갱신·보관·실행 설정', 'sim_review40'),
)


def checkpoint_at(end):
    return next(c for c in CHECKPOINTS if c.end == end)


def make_checkpoint(end, seed=None):
    checkpoint = checkpoint_at(end)
    m = make_mission(checkpoint.kind, seed)
    if end > 25:
        return replace(m, review=dict(m.review, checkpoint=checkpoint.key, units=[u.key for u in checkpoint.units]))
    s, t, r = m.source, m.target, m.report
    q = shlex.quote
    def file(path, text): return {'type': 'file', 'path': path, 'text': text}
    def directory(path): return {'type': 'dir', 'path': path}
    def absent(path): return {'type': 'absent', 'path': path}
    def copy(path, source): return {'type': 'copy', 'path': path, 'source': source}
    def output(text, count=1): return {'type': 'output', 'text': text, 'count': count}
    def listing(path, options): return {'type': 'listing', 'path': path, 'source': s, 'options': options}
    setup, goals = [], []
    keep_base = False
    if end == 5:
        prompt = (f'{s}/docs로 이동해 숨김 항목까지 목록을 확인하고, {s}/guide.txt와 '
                  f'{s}/docs/read me.txt를 읽으세요. 두 원본은 보존하세요.\n'
                  f'{t} 안에 checkin 폴더와 그 안의 빈 ready.txt를 만든 뒤 checkin에서 위치를 확인하고 채점하세요.')
        solution = (f'pwd\ncd {s}/docs\nls -a\ncat ../guide.txt {q("read me.txt")}\n'
                    f'cd {t}\nmkdir checkin\ntouch checkin/ready.txt\ncd checkin\npwd')
        goals = [output(f'Release {m.seed} user guide'), output('A file name with spaces'),
                 {'type': 'output_contains', 'text': '.draft'}, directory(t + '/checkin'),
                 file(t + '/checkin/ready.txt', ''), {'type': 'cwd', 'path': t + '/checkin'},
                 file(s + '/guide.txt', f'Release {m.seed} user guide\n'),
                 file(s + '/docs/read me.txt', 'A file name with spaces\n')]
    elif end == 10:
        prompt = (f'{t}의 note.txt를 note.before.txt로 먼저 보존하고, 원래 note.txt의 status=draft를 '
                  'status=ready로 수정해 저장한 뒤 편집기를 종료하세요.\n'
                  '같은 폴더의 draft.txt는 final.txt로 이름을 바꾸고 obsolete.txt만 삭제하세요.\n'
                  f'{t}의 위치를 그 안의 location.txt에 기록하고 수정한 파일과 기록을 확인하세요.')
        solution = (f'cd {t}\ncp note.txt note.before.txt\nnano note.txt\nmv draft.txt final.txt\n'
                    'rm obsolete.txt\npwd > location.txt\ncat note.txt location.txt')
        goals = [file(t + '/note.before.txt', 'status=draft\n'),
                 file(t + '/note.txt', 'status=ready\n'),
                 copy(t + '/final.txt', t + '/draft.txt'), absent(t + '/draft.txt'),
                 absent(t + '/obsolete.txt'), file(t + '/location.txt', t + '\n')]
    elif end == 15:
        prompt = (f'{t}/daily notes/backup 폴더 구조를 만들고 {s}/guide.txt를 그 안에 manual.txt로 보관하세요. '
                  'daily notes 안에는 빈 done.txt도 만드세요. 원본은 보존하세요.\n'
                  f'{t}/draft.txt는 final.txt로 바꾸고 obsolete.txt는 삭제하세요.\n'
                  f'{s}의 바로 아래 항목을 숨김 항목과 .·..까지 포함해 {r}.names에 한 줄씩, '
                  f'{r}에는 권한·소유자·크기·시간을 포함한 상세 형식으로 저장하세요. {s}에서 채점하세요.')
        solution = (f'cd {t}\nmkdir -p {q("daily notes/backup")}\ntouch {q("daily notes/done.txt")}\n'
                    f'cp {s}/guide.txt {q("daily notes/backup/manual.txt")}\nmv draft.txt final.txt\n'
                    f'rm obsolete.txt\ncd {s}\nls -a > {r}.names\nls -al > {r}\npwd')
        goals = [directory(t + '/daily notes/backup'), file(t + '/daily notes/done.txt', ''),
                 copy(t + '/daily notes/backup/manual.txt', s + '/guide.txt'),
                 file(s + '/guide.txt', f'Release {m.seed} user guide\n'),
                 copy(t + '/final.txt', t + '/draft.txt'), absent(t + '/draft.txt'),
                 absent(t + '/obsolete.txt'), listing(r + '.names', '-1a'),
                 listing(r, '-al'), {'type': 'cwd', 'path': s}]
    elif end == 20:
        keep_base = True  # Existing find grader checks the complete path set.
        setup = [file(s + '/large-sample.bin', 'X' * 16384)]
        prompt = (f'바로가기를 거치지 않고 실제 폴더 {s}에 들어가 논리 경로와 물리 경로를 각각 출력하세요.\n'
                  f'이 폴더의 숨김 항목과 .·..를 포함한 상세 목록을 읽기 쉬운 크기·큰 크기순으로 {r}.sizes에, '
                  f'모든 하위 폴더의 숨김 포함 상세 목록을 {r}.tree에 기록하세요.\n'
                  f'app.log의 error 줄을 대소문자 구분 없이 {r}.errors에, 일치 줄 수는 {r}.count에 저장하세요.\n'
                  f'{s} 아래 모든 .deb 일반 파일의 절대경로를 {r}에 한 줄씩 기록하세요. .deb 이름의 폴더는 제외하세요.')
        solution = (f'cd {s}\npwd -L\npwd -P\nls -alhS > {r}.sizes\nls -alR > {r}.tree\n'
                    f'grep -i error app.log > {r}.errors\ngrep -i error app.log | wc -l > {r}.count\n'
                    f"find {s} -type f -name '*.deb' > {r}")
        goals = [output(s, 2), listing(r + '.sizes', '-alhS'), listing(r + '.tree', '-alR'),
                 file(r + '.errors', 'ERROR disk full\nerror timeout\nError network\n'),
                 {'type': 'stripped_file', 'path': r + '.count', 'text': '3'}]
    else:
        keep_base = True  # Existing script grader verifies bytes, mode and receipt.
        archive_url = m.url.rsplit('/', 1)[0] + '/bundle.tar.gz'
        prompt = (f'curl로 {m.url}을 {t}/received-setup.sh에 내려받고 내용을 확인하세요. '
                  f'소유자 실행 권한을 추가하고 {t}/receipt.txt를 결과 파일로 넘겨 실행하세요.\n'
                  f'wget으로 {archive_url}을 {t}/bundle.tar.gz에 받아 내용을 조회한 뒤 '
                  f'{t}/unpacked에 풀어 README.txt와 bin/hello.sh를 복원하세요. 내려받은 파일도 남겨 두세요.')
        solution = (f'cd {t}\ncurl -fL -o received-setup.sh {m.url}\ncat received-setup.sh\n'
                    f'chmod u+x received-setup.sh\n./received-setup.sh receipt.txt\n'
                    f'wget -O bundle.tar.gz {archive_url}\ntar -tzf bundle.tar.gz\n'
                    'mkdir -p unpacked\ntar -xzf bundle.tar.gz -C unpacked')
        goals = [copy(t + '/bundle.tar.gz', s + '/bundle.tar.gz'),
                 file(t + '/unpacked/README.txt', 'Shellground training bundle\nVersion 1.0\n'),
                 file(t + '/unpacked/bin/hello.sh', '#!/bin/sh\nprintf "Hello from Linux\\n"\n')]
    review = {'checkpoint': checkpoint.key, 'title': checkpoint.label,
              'units': [u.key for u in checkpoint.units], 'setup': setup,
              'goals': goals, 'keep_base': keep_base}
    formatted = natural_paths(replace(m, prompt=prompt, solution=solution, review=review), move_to_focus=False)
    return replace(formatted, solution='\n'.join(line for line in formatted.solution.splitlines() if line != 'cd .'))
