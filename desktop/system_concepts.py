"""Read-only Linux/Docker conceptual catalog; no execution or progress writes.

The source drafts and their question/concept IDs remain authoritative.
Cards contain teaching text, not worked answers to the displayed question.
``answer`` and ``feedback`` must only be presented after submission. Selecting
``practice_keys`` opens related lesson explanations; neither selection nor a
correct conceptual answer proves completion of an execution exercise.

Sources retain their actual URLs. Local scope references retain repository-
relative document paths in ``url``; they are not presented as web references.
This module uses only the standard library and never imports an execution engine.
"""

from __future__ import annotations

import json
from pathlib import Path


_DATA_DIR = Path(__file__).resolve().parent / "python_teaching"
_DRAFT_NAMES = (
    "linux_docker_concept_draft.json",
    "shell_concept_draft.json",
    "process_concept_draft.json",
    "io_concept_draft.json",
    "system_info_concept_draft.json",
)

# Context examples, deliberately not the drafts' worked answers (some reused
# the precise numbers/observations of their own question).
_EXAMPLES = {
    "linux_components": "사용 장면: 터미널 글꼴 설정, Bash 명령 문법, 배포판의 패키지 구성을 서로 다른 설정 항목으로 나누어 살펴봅니다.",
    "linux_command_kinds": "사용 장면: 안내서의 명령이 예상과 다르게 동작하면, 파일을 다시 설치하기 전에 현재 셸이 그 이름을 어떻게 해석하는지 조사합니다.",
    "linux_utf8": "사용 장면: 업로드 제한이 바이트 기준이면 문서의 글자 수뿐 아니라 저장 크기와 인코딩도 확인합니다.",
    "linux_process_threads": "사용 장면: 작업 현황 표를 읽을 때 프로세스 식별자, 부모 관계, 스레드 식별자를 각각 표시해 봅니다.",
    "linux_sudo_policy": "사용 장면: 관리 작업이 거부되면 계정의 인증 문제와 해당 작업의 허용 범위를 나누어 조사합니다.",
    "linux_setuid": "사용 장면: 실행 파일의 소유자와 권한을 조사할 때 실행 사용자의 UID와 프로그램의 유효 UID를 별도 항목으로 기록합니다.",
    "docker_structure_oci": "사용 장면: 배포 계획에 클라이언트 위치, 엔진 위치, 이미지 아키텍처를 따로 기록해 실행 환경을 설명합니다.",
    "docker_attach_exec_lifetime": "사용 장면: 컨테이너 안의 작업을 끝내기 전에, 닫으려는 것이 연결인지 별도 명령인지 주 프로세스인지 구분합니다.",
    "docker_cpu_affinity_budget": "사용 장면: 자원 계획에서 허용할 CPU 번호와 CPU 사용 시간의 상한을 서로 다른 조건으로 작성합니다.",
    "docker_io_weight": "사용 장면: 저장장치 성능을 비교할 때 설정값뿐 아니라 경쟁 작업, 캐시, 실제 측정 조건을 함께 기록합니다.",
    "docker_device_gpu_minimum": "사용 장면: GPU 실습 준비표에는 이미지 확보, 장치 접근, 실제 계산 결과를 별도 확인 항목으로 둡니다.",
    "docker_x11_authorization": "사용 장면: 원격 화면 문제를 조사할 때 화면 주소, 연결 경로, 허가를 구분하며 인증 비밀은 보고서에 적지 않습니다.",
    "shell.path_resolution": "사용 장면: 팀 전용 도구가 실행되지 않으면 파일 후보 목록과 현재 셸의 명령 해석을 나란히 확인합니다.",
    "shell.current_child_state": "사용 장면: 설정 파일을 적용할 때 현재 터미널에 남길 설정인지 별도 작업에서만 쓸 설정인지 먼저 정합니다.",
    "shell.argument_boundaries": "사용 장면: 파일을 여러 개 받는 도구를 만들 때 화면에 보이는 단어 수 대신 전달할 값의 경계를 설계합니다.",
    "shell.validation_branch": "사용 장면: 입력 요구사항을 항목별로 적고 스크립트의 각 검사 조건이 어느 요구를 확인하는지 대조합니다.",
    "shell.noclobber_safety": "사용 장면: 보고서 생성 도구는 새 결과의 저장과 기존 문서의 보존을 서로 다른 통과 조건으로 둡니다.",
    "process.real_effective_uid": "사용 장면: 계정별 작업을 조사할 때 보고서가 실제 UID와 유효 UID 중 어느 기준을 쓰는지 제목에 밝힙니다.",
    "process.thread_columns": "사용 장면: 많은 행이 나온 프로세스 표를 요약하기 전에 열 제목과 프로세스·스레드 관계부터 확인합니다.",
    "process.cpu_time": "사용 장면: 느린 작업을 조사할 때 시작 시각, 경과 시간, CPU 사용 시간을 서로 다른 항목으로 기록합니다.",
    "process.wait_stop": "사용 장면: 잠시 출력이 없는 작업을 만났을 때 즉시 종료하지 않고 현재 상태와 기다리는 조건을 살펴봅니다.",
    "process.shell_jobs": "사용 장면: 여러 백그라운드 작업이 있는 터미널에서는 대상의 작업 번호와 프로세스 번호를 혼동하지 않도록 확인합니다.",
    "process.termination_signals": "사용 장면: 서비스 종료 절차에는 종료 요청, 실제 종료 확인, 정리 결과 확인을 구분해 적습니다.",
    "io.input_eof": "활용 장면: 대화식으로 기록을 추가할 때 기존 내용을 남길지, 새 내용으로 바꿀지 먼저 정하고 입력 종료와 파일 내용을 따로 확인합니다.",
    "io.pager_navigation": "활용 장면: 긴 보고서를 읽을 때 원하는 부분을 찾고 화면을 닫는 일과, 보고서 내용을 수정하거나 저장하는 일을 구별합니다.",
    "io.tree_visibility": "활용 장면: 프로젝트의 폴더 배치를 간단히 설명할 때 숨김 폴더 포함 여부와 어느 깊이까지 볼지를 먼저 정합니다.",
    "io.executable_file": "활용 장면: 복사한 도구가 실행되지 않을 때 이름 변경부터 시도하지 않고 실제 파일 형식, 실행 경로, 권한을 나누어 조사합니다.",
    "io.script_interpreter": "활용 장면: 같은 파일이 호출 방식에 따라 다르게 동작할 때 파일 확장자보다 실제로 어느 인터프리터가 내용을 읽는지 확인합니다.",
    "system_info.identity_layers": "활용 장면: 장애 보고서에 커널 릴리스, 배포판 버전, 환경의 이름을 서로 다른 칸에 적어 어떤 정보를 조사했는지 밝힙니다.",
    "system_info.interface_evidence": "활용 장면: 접속 문제 보고서에서 인터페이스 존재, 관리 상태, 링크 상태, 주소, 목적 서비스 확인 결과를 분리합니다.",
    "system_info.epoch_and_zone": "활용 장면: 서로 다른 지역의 로그를 비교할 때 표시 시간대와 공통 시각 기준을 구분하고, 화면 표시를 바꾼 것과 시계를 맞춘 것을 혼동하지 않습니다.",
    "system_info.clock_support": "활용 장면: 격리 환경의 시간 조사에서는 시스템 시각을 읽을 수 있는지, RTC가 노출됐는지, 동기화 상태가 확인되는지를 별도 항목으로 남깁니다.",
    "system_info.snap_components": "활용 장면: 배포 준비표에서 관리 명령의 존재, 관리 서비스와의 통신, 패키지 확보, 실제 설치·실행 결과를 각각 확인합니다.",
}

_SOURCE_TITLES = {
    "scope_audit": "Linux/Docker 학습 범위 감사 — 로컬 범위 자료",
    "coverage": "강의 자료와 구현 범위 대조 — 로컬 범위 자료",
    "linux_threads": "Linux man-pages — pthreads(7)",
    "linux_execve": "Linux man-pages — execve(2)",
    "sudo_policy": "sudo 프로젝트 — sudoers 매뉴얼 원본",
    "oci": "Open Container Initiative — Overview",
    "docker_attach": "Docker Docs — docker container attach",
    "docker_exec": "Docker Docs — docker container exec",
    "docker_cpu": "Docker Docs — Resource constraints",
    "docker_io": "Docker Docs — Block I/O constraints",
    "docker_privilege": "Docker Docs — Privileged containers",
    "nvidia_prerequisites": "NVIDIA Container Toolkit — Installation prerequisites",
    "x11_authorization": "X.Org — Xsecurity(7)",
}

# Keys were checked against mode_curriculum.curriculum('real') registration and
# the corresponding course source, not inferred from extension/future goals.
_PRACTICE = {
    "linux_components": (("navigate", "sim_env"), "폴더 이동과 셸 환경변수 설명으로 이어집니다. 터미널·커널 교체나 POSIX 호환성 비교를 실행하는 과제는 아닙니다."),
    "linux_command_kinds": (("shell_path", "shell_source"), "명령 해석과 현재·자식 셸의 상태를 다룹니다. 개념 문제와 같은 자료를 그대로 재현하는 과제는 아닙니다."),
    "linux_utf8": (("edit", "linux_line_count"), "텍스트 편집과 줄 수 확인을 다룹니다. UTF-8 바이트·문자 수 비교나 인코딩 진단은 여기서 평가하지 않습니다."),
    "linux_process_threads": (("process_threads",), "실제 프로세스·스레드 표와 부모 관계를 조사합니다. 공유 데이터의 동시 접근이나 동기화 코드를 작성하는 실습은 아닙니다."),
    "linux_sudo_policy": (("auth_sudo",), "제한된 sudo 정책 아래 허용된 작업과 거부되는 작업을 확인합니다. 임의의 sudoers 정책을 작성하는 과제는 아닙니다."),
    "linux_setuid": ((), "현재 연결할 setuid 실행·nosuid 효과 비교 실습은 없습니다. 일반 권한이나 소유자 실습을 그 실행 검증의 대체로 표시하지 않습니다."),
    "docker_structure_oci": (("sim_images", "sim_run"), "실제 Docker 이미지와 컨테이너를 다룹니다. 새 VM 생성, OCI 런타임 직접 실행, 다른 아키텍처의 호환성 검증은 하지 않습니다."),
    "docker_attach_exec_lifetime": (("docker_sessions_attach", "docker_sessions_exec"), "실제 attach·detach·주 셸 종료와 별도 exec 프로세스의 수명을 비교합니다. 개념 정답을 실행 완료로 바꾸지 않습니다."),
    "docker_cpu_affinity_budget": (("docker_runtime_stats", "docker_runtime_cpu"), "사용량과 상한을 구별하고 실제 cpuset·CPU quota 적용을 확인합니다. CPU 독점·성능 비교는 평가하지 않습니다."),
    "docker_io_weight": (("docker_runtime_io_weight",), "실제 요청과 cgroup 가중치 적용을 확인합니다. 장치의 처리량·가중치 효과는 미측정이며 지원 부족을 실행 성공으로 표시하지 않습니다."),
    "docker_device_gpu_minimum": ((), "현재 연결할 실제 GPU 장치·계산 실습은 없습니다. 장비와 런타임 준비, 실제 계산 결과를 확인하기 전에는 실행 완료가 아닙니다."),
    "docker_x11_authorization": ((), "현재 연결할 X11 연결·인증 실습은 없습니다. 전용 화면에서의 실제 연결 확인이 필요하며, 창 표시만으로 GPU 계산까지 완료한 것은 아닙니다."),
    "shell.path_resolution": (("shell_path",), "PATH 검색 순서와 실제 명령 해석을 조사합니다. 이 문제의 파일 후보 자료와 실습의 준비 파일은 다릅니다."),
    "shell.current_child_state": (("shell_source",), "현재 셸과 자식 셸의 변수·작업 폴더 차이를 확인합니다. 이 문제의 설정 파일을 그대로 실행하는 과제는 아닙니다."),
    "shell.argument_boundaries": (("shell_args",), "스크립트 이름, 개수, 공백·빈 값이 있는 인자를 기록합니다. 개념 답안을 고르는 것과 실제 인자 처리 도구 작성은 다릅니다."),
    "shell.validation_branch": (("shell_if",), "인자 개수를 검사하고 잘못된 호출을 거부하는 도구를 만듭니다. 두 값이 모두 비어 있지 않은지 검사하는 추가 조건은 기존 실습의 평가 범위가 아닙니다."),
    "shell.noclobber_safety": (("shell_noclobber",), "기존 파일 보존과 새 파일 생성을 함께 확인합니다. 이 문제의 보호 실패를 판단하는 것만으로 스크립트 작성까지 완료되지는 않습니다."),
    "process.real_effective_uid": (("process_list",), "실제 UID 기준의 프로세스 목록을 조사합니다. 실습의 대상은 실제·유효 UID가 같으므로 두 UID가 다른 이 문제의 선택 비교까지 실행하지는 않습니다."),
    "process.thread_columns": (("process_threads",), "실제 스레드별 표와 부모·자식 트리를 조사합니다. 문항의 고정 번호를 외우는 과제가 아니라 그때의 관계를 확인합니다."),
    "process.cpu_time": (("process_list",), "프로세스 목록의 누적 CPU 시간 열을 확인합니다. 경과 시간과 CPU 시간을 장기간 비교 측정하는 과제는 아닙니다."),
    "process.wait_stop": (("process_stop", "process_resume"), "같은 작업을 중지·재개하며 상태를 확인합니다. S 표시 하나만으로 프로그램의 정상 동작 전체를 보증하는 검사는 아닙니다."),
    "process.shell_jobs": (("process_stop", "process_resume"), "작업 번호를 골라 전경·백그라운드에서 제어합니다. 각 작업은 한 프로세스이므로 여러 프로세스의 파이프라인 전체를 제어하는 실습과는 다릅니다."),
    "process.termination_signals": (("process_signals",), "정상 종료 요청과 강제 종료, 실제 종료·정리 결과를 확인합니다. 여기서 주어진 서비스의 동작을 모든 프로그램에 일반화하지 않습니다."),
    "io.input_eof": (("io_input",), "내용을 입력하고 기존 내용을 보존하거나 이어 쓰는 과제로 이어집니다. 실제 파일 내용과 셸 복귀를 확인하며, 개념 답변만으로 Ctrl+D 입력을 실행한 것은 아닙니다."),
    "io.pager_navigation": (("io_pager",), "긴 문서에서 필요한 값을 찾아 인계합니다. 실습 채점은 찾은 값·원본 보존·셸 복귀를 확인하며, 페이지 탐색의 특정 키 문자열을 정답으로 강제하지 않습니다."),
    "io.tree_visibility": (("io_tree",), "실제 폴더의 숨김 항목·디렉터리·깊이 범위를 구분해 트리 보고서를 만듭니다. 문제의 가정된 목록을 읽는 것과 실제 계층을 조사하는 과제는 다릅니다."),
    "io.executable_file": (("io_binary",), "실제 실행 파일을 복사하고 실행 권한·경로·원본 보존을 확인합니다. 같은 Linux 안의 준비된 실행 환경을 다루며 다른 OS나 CPU에서의 실행 호환성은 평가하지 않습니다."),
    "io.script_interpreter": (("io_shebang",), "Bash 해석기를 명시한 도구를 작성하고 다른 경로의 인자에도 직접 실행되는지 확인합니다. 이 문제의 두 해석기 비교나 shebang 없는 파일의 fallback까지 실습으로 완료한 것은 아닙니다."),
    "system_info.identity_layers": (("system_identity",), "실제 환경의 커널·배포판·호스트 이름을 구분해 기록합니다. 문제의 고정된 버전이나 이름을 재현하는 과제는 아니며, DNS 등록·서비스 통신은 여기서 평가하지 않습니다."),
    "system_info.interface_evidence": (("system_links", "system_addresses"), "실제 인터페이스의 상태와 IPv4·IPv6 주소를 설정 변경 없이 조사합니다. 목록·관리 UP·주소 확인을 인터넷이나 목적 서비스의 통신 성공으로 처리하지 않습니다."),
    "system_info.epoch_and_zone": (("system_time",), "실제로 읽은 시각을 epoch와 UTC로 표현하고 파일 수정 시각과 구별합니다. 퀴즈의 고정 숫자는 실습 정답이 아니며, 시계 변경·NTP 동기화는 수행하지 않습니다."),
    "system_info.clock_support": (("system_clock",), "시계 속성과 RTC 조회의 실제 출력·종료 상태를 보고합니다. RTC 미지원도 그대로 기록하며, 조사 완료가 RTC 읽기 성공이나 NTP 동기화 완료를 뜻하지 않습니다."),
    "system_info.snap_components": ((), "현재 연결할 실제 snap 설치·실행 실습은 없습니다. 클라이언트나 패키지 파일이 있어도 설치 완료가 아니며, 필요한 서비스·환경 지원과 실제 결과를 별도로 확인해야 합니다."),
}

_PRACTICE_OVERRIDES = {
    "linux_components_posix_scope": ((), "현재 연결할 POSIX 이식성 비교 실습은 없습니다. Linux 명령 실습의 통과를 다른 셸·배포판에서의 호환성 검증으로 표시하지 않습니다."),
    "linux_command_kinds_pwd_resolution": (("shell_path",), "내장 명령과 외부 실행 파일을 구분하고 실제 명령 해석을 조사합니다. 이 문제의 관찰값만 읽는 것과 직접 확인하는 실습은 다릅니다."),
    "linux_command_kinds_cd_parent": (("shell_source",), "현재·자식 셸에서 설정과 작업 폴더가 달라지는 것을 확인합니다. 퀴즈 응답만으로 해당 실행 결과를 만든 것은 아닙니다."),
    "io_ctrl_d_depends_on_input_context": (("io_input", "io_pager"), "입력을 끝내는 상황과 긴 문서를 탐색하는 상황의 설명으로 이어집니다. 실제 파일 결과·문서 조회·셸 복귀를 별도로 확인하며, 셸을 Ctrl+D로 종료하는 것은 이 실습들의 완료 목표가 아닙니다."),
}

_QUESTION_FOCUS = {
    # The last listed prerequisite is background knowledge, not this question's
    # main topic. Do not route noclobber to the argument-validation exercise.
    "shell_noclobber_expected_refusal": "shell.noclobber_safety",
}

_PRACTICE_PREFIX = "연결은 관련 단원의 설명 보기입니다. 자동 실행·채점·실습 완료 처리는 하지 않습니다. "
_SCENARIO_LABELS = {
    "assumptions": "가정", "command_to_reason_about": "판단할 명령",
    "initial_state": "시작 상태", "prepared_file": "준비된 파일",
    "alternatives": "비교할 명령", "invocation": "실행할 명령",
    "arguments": "전달된 인자", "requirement": "요구사항",
    "script": "스크립트 내용", "initial_file": "기존 파일",
    "rows": "관찰 자료", "elapsed": "경과 시간", "TIME": "TIME 열",
    "job_number": "현재 셸의 작업 번호", "process_group": "프로세스 그룹 번호",
    "process_ids": "프로세스 번호 목록", "state": "현재 상태",
}


def _paragraphs(value):
    if isinstance(value, list) and all(isinstance(v, str) for v in value):
        value = "\n\n".join(value)
    if not isinstance(value, str) or not value.strip():
        raise ValueError("A non-empty teaching paragraph is required")
    return value


def _code(text):
    # The native UI is plain text, not a Markdown renderer. Preserve the shell
    # text and argument boundaries without displaying formatting fence tokens.
    return text.rstrip("\n")


def _table(rows):
    if not rows or not all(isinstance(row, dict) for row in rows):
        raise ValueError("Scenario rows must be non-empty dictionaries")
    columns = list(dict.fromkeys(key for row in rows for key in row))

    def cell(value):
        return str(value).replace("\n", " / ")

    values = [list(map(cell, columns))] + [[cell(row.get(k, "")) for k in columns] for row in rows]
    widths = [max(len(row[i]) for row in values) for i in range(len(columns))]
    lines = ["  ".join(value.ljust(width) for value, width in zip(row, widths)).rstrip() for row in values]
    lines.insert(1, "  ".join("─" * width for width in widths))
    return "\n".join(lines)


def _scenario_prompt(scenario, prompt):
    if scenario is None:
        return prompt
    heading = "가정 자료 — 아래는 문제에서 주어진 상황이며 실제 실행 결과 보고가 아닙니다."
    sections = []
    if isinstance(scenario, str):
        sections.append(scenario)
    elif isinstance(scenario, dict):
        for key, value in scenario.items():
            if key not in _SCENARIO_LABELS:
                raise ValueError(f"Unformatted scenario field: {key}")
            label = _SCENARIO_LABELS[key]
            if key == "rows":
                body = _table(value)
            elif key == "prepared_file":
                if set(value) != {"name", "content"}:
                    raise ValueError("Unformatted prepared file fields")
                body = f"파일 이름: {value['name']}\n" + _code(value["content"])
            elif key in ("script", "invocation", "command_to_reason_about"):
                body = _code(value)
            elif key == "alternatives":
                body = "\n".join(f"비교 {i}: {_code(command)}" for i, command in enumerate(value, 1))
            elif key == "arguments":
                # JSON quoting makes an explicitly empty argument visible.
                body = _code("\n".join(f"인자 {i}: {json.dumps(arg, ensure_ascii=False)}"
                                       for i, arg in enumerate(value, 1)))
            elif key == "process_ids":
                body = ", ".join(str(pid) for pid in value)
            elif isinstance(value, list):
                body = "\n".join(f"- {item}" for item in value)
            else:
                body = str(value)
            sections.append(f"{label}\n{body}" if "\n" in body else f"{label}: {body}")
    else:
        raise ValueError("Unsupported scenario")
    return prompt + "\n\n" + heading + "\n" + "\n\n".join(sections)


def _read_drafts():
    return [json.loads((_DATA_DIR / name).read_text(encoding="utf-8")) for name in _DRAFT_NAMES]


def _build_catalog(drafts):
    """Normalize all drafts before filtering, detecting cross-topic collisions."""
    concepts, questions = {}, []
    question_ids = set()

    for draft in drafts:
        if draft.get("schema") != 1:
            raise ValueError("Unsupported concept draft schema")
        sources = draft["sources"]
        mixed = draft.get("kind") == "linux-docker-concept-draft"
        if not mixed and draft.get("kind") not in {"shell-concept-draft", "process-concept-draft", "io-concept-draft", "system-info-concept-draft"}:
            raise ValueError("Unsupported concept draft kind")
        rows = draft["cards"] if mixed else draft["concepts"]
        for row in rows:
            cid = row["id"]
            if cid in concepts:
                raise ValueError(f"Duplicate concept ID: {cid}")
            if cid not in _EXAMPLES or cid not in _PRACTICE:
                raise ValueError(f"Missing reviewed concept presentation: {cid}")
            concepts[cid] = {
                "id": cid, "title": _paragraphs(row["title"]),
                "explanation": _paragraphs(row["explanation"]),
                "example": _EXAMPLES[cid],
                "prerequisites": list(row.get("prerequisites", [])),
                "source_refs": [(sources, sid) for sid in row.get("source_ids", [])],
            }
        pairs = ((row, q) for row in rows for q in row["questions"]) if mixed else ((None, q) for q in draft["questions"])
        for card, question in pairs:
            qid = question["id"]
            if qid in question_ids:
                raise ValueError(f"Duplicate question ID: {qid}")
            question_ids.add(qid)
            roots = [card["id"]] if mixed else list(question["prerequisites"])
            refs = [(sources, sid) for sid in question.get("source_ids", [])]
            if not mixed:
                # These concepts cite evidence on their questions, not the cards.
                for cid in roots:
                    if cid not in concepts:
                        raise ValueError(f"Unknown prerequisite: {cid}")
                    concepts[cid]["source_refs"].extend(refs)
            questions.append((card, question, roots, refs))

    def expand(roots):
        ordered, visiting, done = [], set(), set()

        def visit(cid):
            if cid in visiting:
                raise ValueError(f"Cyclic prerequisites: {cid}")
            if cid in done:
                return
            if cid not in concepts:
                raise ValueError(f"Unknown prerequisite: {cid}")
            visiting.add(cid)
            for parent in concepts[cid]["prerequisites"]:
                visit(parent)
            visiting.remove(cid)
            done.add(cid)
            ordered.append(cid)

        for cid in roots:
            visit(cid)
        return ordered

    # Validate even an otherwise unused prerequisite so bad draft edits fail fast.
    expand(concepts)
    result = []
    for card, q, roots, question_refs in questions:
        ordered = expand(roots)
        choices, feedback = list(q["choices"]), list(q["choice_feedback"])
        answer = q["answer"]
        if (len(choices) != 4 or len(feedback) != 4 or len(set(choices)) != 4
                or type(answer) is not int or not 0 <= answer < 4
                or not all(isinstance(s, str) and s.strip() for s in choices + feedback)):
            raise ValueError(f"Invalid four-choice question: {q['id']}")
        if not ordered:
            raise ValueError(f"Missing teaching concepts: {q['id']}")
        topic = "docker" if card and card["id"].startswith("docker_") else "linux"
        focus = _QUESTION_FOCUS.get(q["id"], roots[-1])
        keys, note = _PRACTICE_OVERRIDES.get(q["id"], _PRACTICE[focus])
        resolved_sources, seen_sources = [], set()
        refs = [ref for cid in ordered for ref in concepts[cid]["source_refs"]] + question_refs
        for registry, sid in refs:
            if sid not in registry:
                raise ValueError(f"Unknown source: {sid}")
            source = registry[sid]
            title = source.get("title") or _SOURCE_TITLES.get(sid)
            url = source.get("url") or source.get("path")
            if not title or not url:
                raise ValueError(f"Unresolved source: {sid}")
            if url not in seen_sources:
                seen_sources.add(url)
                resolved_sources.append({"title": title, "url": url})
        if not resolved_sources:
            raise ValueError(f"Missing evidence: {q['id']}")
        result.append({
            "id": q["id"], "topic": topic,
            "title": card["title"] if card else q["topic"],
            "cards": [{field: concepts[cid][field] for field in ("id", "title", "explanation", "example")} for cid in ordered],
            "prerequisites": list(ordered),
            "prompt": _scenario_prompt(q.get("scenario"), _paragraphs(q["prompt"])),
            "choices": choices, "answer": answer, "feedback": feedback,
            "sources": resolved_sources, "practice_keys": list(keys),
            "practice_note": _PRACTICE_PREFIX + note,
            "completion_equivalence": False, "execution_completion": False,
        })
    return result


def load_catalog(topic="linux") -> list[dict]:
    """Return fresh dictionaries for ``linux`` or ``docker`` in draft order.

    ``prerequisites`` lists the concept IDs displayed in ``cards``: recursive
    prerequisites first, then the current question's concepts. It is not a list
    of required quiz passes. A Docker card may include basic Linux concepts.
    """
    if topic not in ("linux", "docker"):
        raise ValueError("topic must be 'linux' or 'docker'")
    return [item for item in _build_catalog(_read_drafts()) if item["topic"] == topic]
