"""Shellground curriculum and command matching logic.

The simulator never executes commands on the host.  Every exercise is matched
against a small allow-list so destructive commands are safe to practise.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Iterable


@dataclass(frozen=True)
class Exercise:
    prompt: str
    context: str
    answers: tuple[str, ...]
    output: tuple[str, ...] = ()
    hint: str = ""
    solution: str = ""

    def accepts(self, command: str) -> bool:
        normalized = normalize_command(command)
        return any(re.fullmatch(pattern, normalized) for pattern in self.answers)


@dataclass(frozen=True)
class Lesson:
    key: str
    command: str
    title: str
    level: int
    summary: str
    syntax: str
    options: tuple[tuple[str, str], ...]
    examples: tuple[Exercise, ...]
    practice: tuple[Exercise, ...]
    tip: str


@dataclass(frozen=True)
class ComboExercise:
    requires: tuple[str, ...]
    exercise: Exercise


def normalize_command(command: str) -> str:
    return re.sub(r"\s+", " ", command.strip())


def ex(
    prompt: str,
    context: str,
    solution: str,
    *answers: str,
    output: Iterable[str] = (),
    hint: str = "",
) -> Exercise:
    patterns = tuple(answers) or (re.escape(solution),)
    return Exercise(prompt, context, patterns, tuple(output), hint, solution)


LEVELS = {
    1: ("입문", "위치와 디렉터리"),
    2: ("기초", "파일 다루기"),
    3: ("활용", "검색과 텍스트"),
    4: ("실전", "권한과 시스템"),
}


LESSONS: tuple[Lesson, ...] = (
    Lesson(
        "pwd", "pwd", "현재 위치 확인", 1,
        "현재 작업 중인 디렉터리의 절대 경로를 출력합니다. 터미널에서 길을 잃었을 때 가장 먼저 쓰는 명령어입니다.",
        "pwd",
        (("옵션 없음", "인자 없이 그대로 실행합니다."),),
        (ex("현재 작업 위치를 확인하세요.", "명령어를 그대로 입력합니다.", "pwd", output=("/home/learner/projects",), hint="print working directory의 약자입니다."),),
        (
            ex("지금 어느 디렉터리에 있는지 출력하세요.", "추가 옵션은 필요하지 않습니다.", "pwd", output=("/home/learner/projects",), hint="세 글자 명령어입니다."),
            ex("현재 셸의 작업 경로를 확인하세요.", "절대 경로가 출력되어야 합니다.", "pwd", output=("/home/learner/projects",), hint="p로 시작합니다."),
        ),
        "명령 실행 전후에 pwd를 사용하면 예상하지 않은 위치에서 파일을 수정하는 실수를 줄일 수 있습니다.",
    ),
    Lesson(
        "ls", "ls", "목록 살펴보기", 1,
        "디렉터리 안의 파일과 하위 디렉터리를 나열합니다. 옵션을 조합하면 숨김 파일, 권한, 크기도 확인할 수 있습니다.",
        "ls [옵션] [경로]",
        (("-l", "권한·소유자·크기·시간을 자세히 표시"), ("-a", "점(.)으로 시작하는 숨김 파일까지 표시"), ("-h", "크기를 K, M, G 단위로 표시")),
        (
            ex("현재 위치의 파일 목록을 보세요.", "가장 기본적인 사용법입니다.", "ls", output=("README.md  logs  src",), hint="두 글자 명령어입니다."),
            ex("숨김 파일을 포함해 자세히 보세요.", "-l과 -a를 함께 사용합니다.", "ls -la", r"ls -(?:la|al)", r"ls -l -a", r"ls -a -l", output=("drwxr-xr-x  5 learner learner 4.0K .", "-rw-r--r--  1 learner learner  220 .env", "drwxr-xr-x  3 learner learner 4.0K src"), hint="ls -la처럼 옵션을 붙여 보세요."),
        ),
        (
            ex("/var/log 디렉터리의 목록을 확인하세요.", "경로를 명령어 뒤에 적습니다.", "ls /var/log", r"ls /var/log/?", output=("apt  auth.log  syslog",), hint="ls 다음에 /var/log를 입력하세요."),
            ex("파일 크기를 읽기 쉬운 단위로 자세히 표시하세요.", "-l과 -h를 조합합니다.", "ls -lh", r"ls -(?:lh|hl)", r"ls -l -h", r"ls -h -l", output=("-rw-r--r-- 1 learner learner 1.4M access.log",), hint="long과 human-readable 옵션입니다."),
        ),
        "실무에서는 ls -lah 조합을 가장 자주 사용합니다.",
    ),
    Lesson(
        "cd", "cd", "디렉터리 이동", 1,
        "현재 작업 디렉터리를 바꿉니다. 상대 경로와 절대 경로를 모두 사용할 수 있습니다.",
        "cd [이동할 경로]",
        (("..", "한 단계 위 디렉터리"), ("~", "사용자의 홈 디렉터리"), ("-", "바로 전에 있던 디렉터리")),
        (
            ex("src 디렉터리로 이동하세요.", "현재 위치 아래의 상대 경로입니다.", "cd src", r"cd (?:\./)?src/?", hint="cd 뒤에 목적지를 적으세요."),
            ex("한 단계 위로 이동하세요.", "상위 디렉터리는 점 두 개로 표현합니다.", "cd ..", r"cd \.\./?", hint="점 두 개를 사용하세요."),
        ),
        (
            ex("사용자의 홈 디렉터리로 이동하세요.", "물결표는 홈 경로의 축약입니다.", "cd ~", r"cd ~/?", r"cd /home/learner/?", hint="~ 기호를 사용하세요."),
            ex("직전에 있던 디렉터리로 돌아가세요.", "앞뒤 두 위치를 오갈 때 편리합니다.", "cd -", hint="빼기 기호 하나를 목적지로 씁니다.", output=("/home/learner/projects",)),
        ),
        "공백이 있는 경로는 cd \"My Files\"처럼 따옴표로 감싸세요.",
    ),
    Lesson(
        "mkdir", "mkdir", "디렉터리 만들기", 1,
        "새 디렉터리를 생성합니다. -p 옵션을 사용하면 중간 경로가 없어도 한 번에 만들 수 있습니다.",
        "mkdir [옵션] 디렉터리명",
        (("-p", "필요한 상위 디렉터리까지 함께 생성"),),
        (
            ex("logs 디렉터리를 만드세요.", "현재 위치에 빈 디렉터리를 만듭니다.", "mkdir logs", r"mkdir logs/?", hint="mkdir 뒤에 이름을 적으세요."),
            ex("data/backup 경로를 한 번에 만드세요.", "상위 data가 없다고 가정합니다.", "mkdir -p data/backup", r"mkdir -p data/backup/?", hint="parents를 뜻하는 -p가 필요합니다."),
        ),
        (
            ex("config 디렉터리를 생성하세요.", "추가 옵션은 필요 없습니다.", "mkdir config", r"mkdir config/?", hint="mkdir + 디렉터리명"),
            ex("reports/2026/sep 전체 경로를 만드세요.", "중간 디렉터리도 함께 생성해야 합니다.", "mkdir -p reports/2026/sep", r"mkdir -p reports/2026/sep/?", hint="-p 옵션을 사용하세요."),
        ),
        "mkdir 실행 뒤 ls로 실제 생성 위치와 이름을 확인하는 습관을 들이세요.",
    ),
    Lesson(
        "touch", "touch", "빈 파일 만들기", 1,
        "파일이 없으면 빈 파일을 만들고, 이미 있으면 수정 시간을 현재 시각으로 갱신합니다.",
        "touch 파일명 [파일명 ...]",
        (("여러 이름", "공백으로 구분해 여러 파일을 한 번에 생성"),),
        (
            ex("notes.txt 파일을 만드세요.", "현재 디렉터리에 빈 파일을 만듭니다.", "touch notes.txt", hint="touch 다음에 파일명을 씁니다."),
            ex("a.txt와 b.txt를 한 번에 만드세요.", "파일명을 공백으로 구분합니다.", "touch a.txt b.txt", r"touch (?:a\.txt b\.txt|b\.txt a\.txt)", hint="touch 뒤에 두 파일명을 이어 적으세요."),
        ),
        (
            ex("app.log 파일을 생성하세요.", "빈 로그 파일을 준비합니다.", "touch app.log", hint="확장자까지 입력하세요."),
            ex("index.html과 style.css를 한 번에 만드세요.", "두 파일의 순서는 바뀌어도 됩니다.", "touch index.html style.css", r"touch (?:index\.html style\.css|style\.css index\.html)", hint="두 이름을 공백으로 구분하세요."),
        ),
        "touch는 파일 내용을 쓰지 않습니다. 내용을 입력하려면 편집기나 리다이렉션을 사용합니다.",
    ),
    Lesson(
        "cat", "cat", "파일 내용 확인", 2,
        "짧은 텍스트 파일의 전체 내용을 터미널에 출력합니다. 여러 파일을 이어서 출력할 수도 있습니다.",
        "cat [옵션] 파일명",
        (("-n", "출력되는 모든 줄에 줄 번호 표시"),),
        (
            ex("README.md의 내용을 출력하세요.", "파일명 하나를 전달합니다.", "cat README.md", r"cat (?:\./)?README\.md", output=("# Shellground", "Linux command practice"), hint="cat + 파일명"),
            ex("README.md를 줄 번호와 함께 출력하세요.", "number 옵션을 사용합니다.", "cat -n README.md", r"cat -n (?:\./)?README\.md", output=("     1  # Shellground", "     2  Linux command practice"), hint="-n 옵션을 사용하세요."),
        ),
        (
            ex("config.ini의 내용을 확인하세요.", "짧은 설정 파일입니다.", "cat config.ini", output=("port=8080", "debug=false"), hint="cat 뒤에 파일명을 입력하세요."),
            ex("a.txt와 b.txt 내용을 이어서 출력하세요.", "두 파일명을 차례로 적습니다.", "cat a.txt b.txt", r"cat a\.txt b\.txt", output=("alpha", "bravo"), hint="cat 파일1 파일2"),
        ),
        "화면보다 긴 파일은 cat보다 less를 사용하면 위아래로 탐색하기 쉽습니다.",
    ),
    Lesson(
        "cp", "cp", "파일 복사", 2,
        "원본 파일을 다른 이름이나 위치로 복사합니다. 디렉터리는 -r 옵션으로 내부까지 재귀 복사합니다.",
        "cp [옵션] 원본 대상",
        (("-r", "디렉터리와 내부 내용을 재귀적으로 복사"), ("-i", "덮어쓰기 전에 확인")),
        (
            ex("notes.txt를 notes.bak으로 복사하세요.", "원본을 먼저 적습니다.", "cp notes.txt notes.bak", hint="cp 원본 대상 순서입니다."),
            ex("src 디렉터리를 backup으로 복사하세요.", "디렉터리 복사에는 -r이 필요합니다.", "cp -r src backup", r"cp -r src/? backup/?", hint="recursive의 -r 옵션을 사용하세요."),
        ),
        (
            ex("report.txt를 archive/report.txt로 복사하세요.", "파일을 다른 디렉터리에 보관합니다.", "cp report.txt archive/report.txt", hint="대상 경로까지 모두 입력하세요."),
            ex("config 디렉터리를 config.bak으로 복사하세요.", "폴더이므로 재귀 옵션이 필요합니다.", "cp -r config config.bak", r"cp -r config/? config\.bak/?", hint="cp -r 원본 대상"),
        ),
        "중요한 파일을 복사할 때는 cp -i로 의도치 않은 덮어쓰기를 막을 수 있습니다.",
    ),
    Lesson(
        "mv", "mv", "이동과 이름 변경", 2,
        "파일이나 디렉터리를 옮깁니다. 같은 위치에서 새 이름을 대상으로 지정하면 이름 변경이 됩니다.",
        "mv [옵션] 원본 대상",
        (("-i", "덮어쓰기 전에 확인"), ("-n", "기존 파일을 덮어쓰지 않음")),
        (
            ex("draft.txt 이름을 final.txt로 바꾸세요.", "같은 디렉터리 안에서 이름을 변경합니다.", "mv draft.txt final.txt", hint="mv 현재이름 새이름"),
            ex("final.txt를 archive 디렉터리로 옮기세요.", "대상에 디렉터리 이름을 씁니다.", "mv final.txt archive/", r"mv final\.txt archive/?", hint="mv 파일 목적지"),
        ),
        (
            ex("old.log의 이름을 app.log로 변경하세요.", "원본 파일은 새 이름으로 대체됩니다.", "mv old.log app.log", hint="mv 원본 새이름"),
            ex("photo.png를 images 디렉터리로 이동하세요.", "파일명은 유지합니다.", "mv photo.png images/", r"mv photo\.png images/?", hint="대상은 images 디렉터리입니다."),
        ),
        "mv는 실행 취소가 없습니다. 중요한 대상에는 -i 옵션을 사용하세요.",
    ),
    Lesson(
        "rm", "rm", "파일 삭제", 2,
        "파일을 즉시 삭제합니다. 휴지통을 거치지 않으므로 항상 pwd와 ls로 대상을 확인한 뒤 사용하세요.",
        "rm [옵션] 파일명",
        (("-i", "삭제 전에 하나씩 확인"), ("-r", "디렉터리와 내부 내용을 재귀 삭제"), ("-f", "확인 없이 강제 삭제 — 사용 주의")),
        (
            ex("temp.txt 파일을 삭제하세요.", "일반 파일 하나를 지웁니다.", "rm temp.txt", hint="rm 뒤에 삭제할 파일을 적으세요."),
            ex("old 디렉터리를 내부 파일과 함께 삭제하세요.", "디렉터리에는 재귀 옵션이 필요합니다.", "rm -r old", r"rm -r old/?", hint="-r 옵션을 사용하세요."),
        ),
        (
            ex("cache.tmp를 확인받으며 삭제하세요.", "실수 방지를 위해 interactive 옵션을 사용합니다.", "rm -i cache.tmp", hint="-i 옵션을 사용하세요."),
            ex("build 디렉터리 전체를 삭제하세요.", "강제 옵션 없이 재귀 삭제합니다.", "rm -r build", r"rm -r build/?", hint="rm -r 디렉터리명"),
        ),
        "rm -rf에 루트(/), 홈(~), 별표(*)를 함께 쓰지 마세요. 먼저 삭제 대상을 ls로 확인하세요.",
    ),
    Lesson(
        "grep", "grep", "문자열 검색", 3,
        "텍스트에서 원하는 패턴이 포함된 줄만 골라냅니다. 로그 분석과 설정 확인에 매우 자주 사용합니다.",
        "grep [옵션] '검색어' 파일명",
        (("-i", "대소문자 구분 없이 검색"), ("-n", "일치한 줄 번호 표시"), ("-r", "디렉터리 아래를 재귀 검색")),
        (
            ex("app.log에서 ERROR가 있는 줄을 찾으세요.", "검색어는 대문자입니다.", "grep ERROR app.log", r"grep ['\"]?ERROR['\"]? app\.log", output=("2026-09-10 ERROR database timeout",), hint="grep 검색어 파일명"),
            ex("config.ini에서 port를 대소문자 구분 없이 찾으세요.", "ignore-case 옵션을 사용합니다.", "grep -i port config.ini", r"grep -i ['\"]?port['\"]? config\.ini", output=("PORT=8080",), hint="-i 옵션을 사용하세요."),
        ),
        (
            ex("server.log에서 WARN 줄을 줄 번호와 함께 찾으세요.", "-n 옵션이 줄 번호를 붙입니다.", "grep -n WARN server.log", r"grep -n ['\"]?WARN['\"]? server\.log", output=("42:WARN disk usage high",), hint="grep -n 검색어 파일명"),
            ex("현재 디렉터리 아래에서 TODO를 재귀 검색하세요.", "검색 위치는 현재 디렉터리입니다.", "grep -r TODO .", r"grep -r ['\"]?TODO['\"]? \.\/?", output=("./src/app.py:TODO: add retry",), hint="recursive의 -r을 사용하세요."),
        ),
        "검색어에 공백이나 특수 문자가 있으면 작은따옴표로 감싸는 습관을 들이세요.",
    ),
    Lesson(
        "find", "find", "파일 위치 찾기", 3,
        "시작 경로 아래를 탐색하며 이름, 종류, 크기 같은 조건에 맞는 파일을 찾습니다.",
        "find 시작경로 [조건]",
        (("-name", "이름 패턴으로 검색"), ("-type f", "일반 파일만 검색"), ("-type d", "디렉터리만 검색")),
        (
            ex("현재 위치 아래의 모든 .log 파일을 찾으세요.", "별표 패턴은 따옴표로 감쌉니다.", "find . -name '*.log'", r"find \. -name ['\"]\*\.log['\"]", output=("./logs/app.log", "./logs/access.log"), hint="find . -name '*.log'"),
            ex("/etc 아래에서 hosts 파일을 찾으세요.", "검색 시작 경로를 /etc로 지정합니다.", "find /etc -name 'hosts'", r"find /etc/? -name ['\"]?hosts['\"]?", output=("/etc/hosts",), hint="find 시작경로 -name 이름"),
        ),
        (
            ex("현재 위치 아래의 config 디렉터리만 찾으세요.", "디렉터리 타입 조건을 함께 사용합니다.", "find . -type d -name 'config'", r"find \. (?:-type d -name ['\"]?config['\"]?|-name ['\"]?config['\"]? -type d)", output=("./src/config",), hint="-type d와 -name을 함께 쓰세요."),
            ex("src 아래의 모든 .py 일반 파일을 찾으세요.", "파일 타입과 이름 조건을 조합합니다.", "find src -type f -name '*.py'", r"find src/? (?:-type f -name ['\"]\*\.py['\"]|-name ['\"]\*\.py['\"] -type f)", output=("src/app.py", "src/utils.py"), hint="find src -type f -name '*.py'"),
        ),
        "*.log 같은 패턴은 셸이 먼저 해석하지 않도록 항상 따옴표로 감싸세요.",
    ),
    Lesson(
        "head", "head", "앞부분 읽기", 3,
        "파일의 처음 부분만 빠르게 확인합니다. 기본값은 10줄이며 -n으로 줄 수를 지정할 수 있습니다.",
        "head [옵션] 파일명",
        (("-n 숫자", "출력할 첫 줄 수 지정"),),
        (
            ex("access.log의 처음 10줄을 보세요.", "기본값이 10줄이므로 옵션이 필요 없습니다.", "head access.log", output=("10.0.0.8 GET / 200", "... 8 lines ...", "10.0.0.2 GET /health 200"), hint="head + 파일명"),
            ex("access.log의 처음 5줄만 보세요.", "-n 뒤에 줄 수를 지정합니다.", "head -n 5 access.log", r"head (?:-n 5|-5) access\.log", output=("line 1", "line 2", "line 3", "line 4", "line 5"), hint="head -n 5 파일명"),
        ),
        (
            ex("users.csv의 첫 3줄을 확인하세요.", "헤더와 샘플을 빠르게 확인합니다.", "head -n 3 users.csv", r"head (?:-n 3|-3) users\.csv", output=("id,name", "1,Ada", "2,Linus"), hint="-n 3을 사용하세요."),
            ex("README.md의 첫 1줄만 출력하세요.", "한 줄만 지정합니다.", "head -n 1 README.md", r"head (?:-n 1|-1) README\.md", output=("# Shellground",), hint="head -n 1 파일명"),
        ),
        "CSV나 로그 파일을 처리하기 전에 head로 형식을 확인하면 실수를 줄일 수 있습니다.",
    ),
    Lesson(
        "tail", "tail", "끝부분과 로그 추적", 3,
        "파일의 마지막 부분을 봅니다. -f 옵션은 파일에 새 줄이 추가될 때마다 계속 표시합니다.",
        "tail [옵션] 파일명",
        (("-n 숫자", "출력할 마지막 줄 수 지정"), ("-f", "파일의 새 내용을 계속 추적")),
        (
            ex("app.log의 마지막 10줄을 보세요.", "기본값이 10줄입니다.", "tail app.log", output=("... recent log lines ...", "INFO server ready"), hint="tail + 파일명"),
            ex("app.log를 실시간으로 추적하세요.", "follow 옵션을 사용합니다.", "tail -f app.log", output=("INFO request complete", "^C  (연습 환경에서 자동 종료)",), hint="-f 옵션을 사용하세요."),
        ),
        (
            ex("error.log의 마지막 20줄을 확인하세요.", "줄 수를 지정합니다.", "tail -n 20 error.log", r"tail (?:-n 20|-20) error\.log", output=("... last 20 lines ...",), hint="tail -n 20 파일명"),
            ex("access.log의 새 요청을 계속 관찰하세요.", "Ctrl+C로 종료하는 방식입니다.", "tail -f access.log", output=("10.0.0.7 GET /docs 200", "^C  (연습 환경에서 자동 종료)"), hint="tail -f 파일명"),
        ),
        "운영 로그를 볼 때 tail -f를 종료하려면 Ctrl+C를 누릅니다.",
    ),
    Lesson(
        "wc", "wc", "줄·단어 수 세기", 3,
        "파일의 줄, 단어, 바이트 수를 셉니다. 파이프와 함께 검색 결과 개수를 셀 때 특히 유용합니다.",
        "wc [옵션] 파일명",
        (("-l", "줄 수만 출력"), ("-w", "단어 수만 출력"), ("-c", "바이트 수만 출력")),
        (
            ex("users.csv의 줄 수를 세세요.", "line 옵션을 사용합니다.", "wc -l users.csv", output=("128 users.csv",), hint="wc -l 파일명"),
            ex("README.md의 단어 수를 세세요.", "word 옵션을 사용합니다.", "wc -w README.md", output=("42 README.md",), hint="wc -w 파일명"),
        ),
        (
            ex("access.log에 몇 줄이 있는지 확인하세요.", "로그 한 줄을 요청 하나로 봅니다.", "wc -l access.log", output=("1842 access.log",), hint="줄 수는 -l입니다."),
            ex("article.txt의 단어 개수를 출력하세요.", "단어 수 옵션을 선택합니다.", "wc -w article.txt", output=("356 article.txt",), hint="word의 -w를 사용하세요."),
        ),
        "grep 결과를 파이프로 wc -l에 보내면 조건에 맞는 줄의 개수를 셀 수 있습니다.",
    ),
    Lesson(
        "chmod", "chmod", "파일 권한 변경", 4,
        "파일 소유자와 그룹, 다른 사용자의 읽기(r)·쓰기(w)·실행(x) 권한을 변경합니다.",
        "chmod 권한 파일명",
        (("u+x", "소유자에게 실행 권한 추가"), ("644", "소유자 rw, 나머지 r"), ("755", "소유자 rwx, 나머지 rx")),
        (
            ex("deploy.sh에 소유자 실행 권한을 추가하세요.", "기호 방식을 사용합니다.", "chmod u+x deploy.sh", hint="user + execute를 조합하세요."),
            ex("config.ini 권한을 644로 설정하세요.", "소유자는 읽기·쓰기, 나머지는 읽기입니다.", "chmod 644 config.ini", hint="chmod 644 파일명"),
        ),
        (
            ex("run.sh 권한을 755로 설정하세요.", "모두 실행할 수 있고 소유자만 쓸 수 있습니다.", "chmod 755 run.sh", hint="chmod 755 파일명"),
            ex("backup.sh에서 다른 사용자의 쓰기 권한을 제거하세요.", "others에서 write를 뺍니다.", "chmod o-w backup.sh", hint="o-w 기호를 사용하세요."),
        ),
        "무조건 777을 주기보다 필요한 최소 권한만 부여하세요.",
    ),
    Lesson(
        "ps", "ps", "프로세스 확인", 4,
        "현재 실행 중인 프로세스의 PID, CPU·메모리 사용량, 명령어를 확인합니다.",
        "ps [옵션]",
        (("aux", "모든 사용자의 프로세스를 자세히 표시"), ("-ef", "전체 프로세스를 표준 형식으로 표시")),
        (
            ex("현재 셸의 프로세스를 확인하세요.", "옵션 없이 실행합니다.", "ps", output=("PID TTY          TIME CMD", "804 pts/0    00:00:00 bash"), hint="두 글자 명령어입니다."),
            ex("모든 사용자의 프로세스를 자세히 보세요.", "BSD 스타일의 aux 조합입니다.", "ps aux", output=("USER PID %CPU %MEM COMMAND", "root 1 0.0 0.1 /sbin/init", "learner 1842 0.2 1.4 node server.js"), hint="ps와 aux 사이에 공백을 둡니다."),
        ),
        (
            ex("전체 프로세스를 -ef 형식으로 표시하세요.", "System V 스타일 옵션입니다.", "ps -ef", output=("UID PID PPID C STIME TTY TIME CMD", "root 1 0 0 09:10 ? 00:00:02 /sbin/init"), hint="ps -ef"),
            ex("모든 프로세스의 CPU와 메모리 비율을 확인하세요.", "aux 출력에 두 비율이 포함됩니다.", "ps aux", output=("USER PID %CPU %MEM COMMAND", "learner 1842 0.2 1.4 node server.js"), hint="ps aux"),
        ),
        "프로세스를 종료하기 전 ps로 PID와 실행 명령을 반드시 다시 확인하세요.",
    ),
    Lesson(
        "kill", "kill", "프로세스 종료", 4,
        "PID를 지정해 프로세스에 신호를 보냅니다. 기본 SIGTERM(15)은 프로그램이 정리 후 종료할 시간을 줍니다.",
        "kill [신호] PID",
        (("-15", "정상 종료 요청(SIGTERM), 기본값"), ("-9", "즉시 강제 종료(SIGKILL), 마지막 수단")),
        (
            ex("PID 1842에 정상 종료 신호를 보내세요.", "신호를 생략하면 SIGTERM입니다.", "kill 1842", r"kill (?:-15 )?1842", hint="kill + PID"),
            ex("응답 없는 PID 3901을 강제 종료하세요.", "이번 예시에서만 SIGKILL을 연습합니다.", "kill -9 3901", hint="강제 종료 신호 번호는 9입니다."),
        ),
        (
            ex("PID 2050에 SIGTERM을 명시해 종료 요청하세요.", "신호 15를 직접 적습니다.", "kill -15 2050", hint="kill -15 PID"),
            ex("PID 7711을 기본 신호로 안전하게 종료하세요.", "-9를 사용하지 않습니다.", "kill 7711", r"kill (?:-15 )?7711", hint="kill PID만 입력해도 됩니다."),
        ),
        "먼저 SIGTERM을 보내고 기다린 뒤, 정말 종료되지 않을 때만 SIGKILL을 고려하세요.",
    ),
    Lesson(
        "df", "df", "디스크 여유 확인", 4,
        "마운트된 파일시스템별 전체·사용·여유 공간을 표시합니다.",
        "df [옵션] [경로]",
        (("-h", "K, M, G처럼 사람이 읽기 쉬운 단위 사용"),),
        (
            ex("디스크 여유를 읽기 쉬운 단위로 보세요.", "human-readable 옵션입니다.", "df -h", output=("Filesystem Size Used Avail Use% Mounted on", "/dev/vda1 80G 31G 45G 41% /"), hint="df -h"),
            ex("/var가 속한 파일시스템의 용량을 확인하세요.", "경로를 마지막에 지정합니다.", "df -h /var", r"df -h /var/?", output=("/dev/vda1 80G 31G 45G 41% /",), hint="df -h 경로"),
        ),
        (
            ex("현재 디렉터리가 속한 디스크의 여유 공간을 확인하세요.", "현재 위치는 점으로 표현합니다.", "df -h .", output=("/dev/vda1 80G 31G 45G 41% /",), hint="df -h ."),
            ex("/home 파일시스템 용량을 읽기 쉬운 단위로 보세요.", "경로와 -h를 함께 사용합니다.", "df -h /home", r"df -h /home/?", output=("/dev/vda1 80G 31G 45G 41% /",), hint="df -h /home"),
        ),
        "df는 파일시스템 전체를, du는 특정 디렉터리의 사용량을 확인할 때 사용합니다.",
    ),
    Lesson(
        "tar", "tar", "묶고 압축하기", 4,
        "여러 파일과 디렉터리를 하나의 아카이브로 묶습니다. z 옵션을 더하면 gzip으로 압축합니다.",
        "tar [옵션] 아카이브파일 대상",
        (("-c", "새 아카이브 생성"), ("-x", "아카이브 풀기"), ("-z", "gzip 압축 사용"), ("-f", "뒤의 값을 아카이브 파일명으로 사용")),
        (
            ex("logs 디렉터리를 logs.tar.gz로 압축하세요.", "create, gzip, file 옵션을 조합합니다.", "tar -czf logs.tar.gz logs", r"tar -?(?:czf|zcf) logs\.tar\.gz logs/?", hint="tar -czf 결과파일 대상"),
            ex("backup.tar.gz를 현재 위치에 푸세요.", "extract, gzip, file 옵션입니다.", "tar -xzf backup.tar.gz", r"tar -?(?:xzf|zxf) backup\.tar\.gz", hint="tar -xzf 파일명"),
        ),
        (
            ex("src 디렉터리를 source.tar.gz로 압축하세요.", "아카이브 이름이 먼저, 대상이 다음입니다.", "tar -czf source.tar.gz src", r"tar -?(?:czf|zcf) source\.tar\.gz src/?", hint="tar -czf source.tar.gz src"),
            ex("release.tar.gz 압축을 푸세요.", "풀기에는 x 옵션을 사용합니다.", "tar -xzf release.tar.gz", r"tar -?(?:xzf|zxf) release\.tar\.gz", hint="tar -xzf 파일명"),
        ),
        "f 옵션 바로 뒤에는 반드시 아카이브 파일명이 와야 합니다.",
    ),
)


COMBO_EXERCISES: tuple[ComboExercise, ...] = (
    ComboExercise(("cat", "grep"), ex("app.log에서 ERROR 줄만 찾아 출력하세요.", "파일 출력과 검색을 파이프로 연결합니다.", "cat app.log | grep ERROR", r"cat app\.log \| grep ['\"]?ERROR['\"]?", output=("ERROR database timeout",), hint="cat app.log | grep ERROR")),
    ComboExercise(("grep", "wc"), ex("app.log의 ERROR 줄 개수를 세세요.", "grep 결과를 wc -l로 전달합니다.", "grep ERROR app.log | wc -l", r"grep ['\"]?ERROR['\"]? app\.log \| wc -l", output=("7",), hint="grep ... | wc -l")),
    ComboExercise(("find", "wc"), ex("현재 위치 아래의 .log 파일 개수를 세세요.", "find 결과의 줄 수를 셉니다.", "find . -name '*.log' | wc -l", r"find \. -name ['\"]\*\.log['\"] \| wc -l", output=("4",), hint="find 명령 뒤에 | wc -l을 연결하세요.")),
    ComboExercise(("ps", "grep"), ex("실행 중인 프로세스에서 nginx만 찾으세요.", "프로세스 목록을 문자열 검색으로 좁힙니다.", "ps aux | grep nginx", r"ps aux \| grep ['\"]?nginx['\"]?", output=("www-data 2110 0.1 0.8 nginx: worker process",), hint="ps aux | grep nginx")),
    ComboExercise(("ls", "grep"), ex("현재 목록에서 .log가 포함된 항목만 찾으세요.", "ls 출력을 grep으로 전달합니다.", "ls | grep '.log'", r"ls \| grep ['\"]?\.log['\"]?", output=("access.log", "app.log"), hint="ls | grep '.log'")),
)


def review_pool(learned_keys: Iterable[str]) -> list[Exercise]:
    learned = set(learned_keys)
    pool: list[Exercise] = []
    for lesson in LESSONS:
        if lesson.key in learned:
            pool.extend(lesson.practice)
    for combo in COMBO_EXERCISES:
        if set(combo.requires).issubset(learned):
            pool.append(combo.exercise)
    return pool


def validate_curriculum() -> list[str]:
    errors: list[str] = []
    keys: set[str] = set()
    for lesson in LESSONS:
        if lesson.key in keys:
            errors.append(f"duplicate lesson key: {lesson.key}")
        keys.add(lesson.key)
        if not lesson.examples or not lesson.practice:
            errors.append(f"missing exercises: {lesson.key}")
        for exercise in (*lesson.examples, *lesson.practice):
            if not exercise.solution or not exercise.accepts(exercise.solution):
                errors.append(f"solution rejected: {lesson.key} / {exercise.solution}")
    for combo in COMBO_EXERCISES:
        if not combo.exercise.accepts(combo.exercise.solution):
            errors.append(f"combo solution rejected: {combo.exercise.solution}")
        for requirement in combo.requires:
            if requirement not in keys:
                errors.append(f"unknown combo requirement: {requirement}")
    return errors
