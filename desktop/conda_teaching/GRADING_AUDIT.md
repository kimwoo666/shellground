# 실제 Conda 54문제 채점·목표 정합성 감사

## 부모 후속 검증 — 2026-09-16

- create_preserve의 최종 활성 상태 문장은 실제 fixture/기준과 같은 ‘없음’으로 정정했다. 두 학습 환경의 활성/비활성 조사에서 base까지 답 후보로 오해하지 않도록 목표 범위도 명시했다.
- 학습 환경 보존은 설치·요청 spec·파일 등의 최종 상태를 비교하되 거래 history 바이트만 제외한다. 관리용 base는 기존 전체 비교를 유지한다. 실제 `conda_update_preserve`에서 잘못된1.1설치를 거부하고 Conda로1.0을 원상복구한 뒤 같은 세션의 재채점이 통과했다. 이력 파일을 손으로 수정하지 않았다.
- `conda export -n sg-share --from-history --format=environment-yaml --file share/environment.yml`을 설치된 Conda26.7.1에서 실제 실행했고 같은 YAML 의미 채점이 통과했다.
- 현재 수정본에서 update/export6문제·2단원(74754)과 나머지48문제·16단원(77987)이 모두 종료0이다. 새 보고서가54문제·4개 오답 복구·13개 답안 변형·18단원 소단계의 통과를 기록한다. 통합 fingerprint는 `575fce6c24c00186857ae6e48f8b4d691025ac8cbeb4edb5ba27eff2532006f2`이다.
- 검증 팩을 별도 내보낸 뒤 Qt 앱의 실제 PTY 오답→수정→재채점·YAML 파일 보기·다음 문제·완료 진도·VM/overlay 정리 검사도 통과했다(66759 종료0,26.872초). 초기 검사에서 프롬프트의 전체 경로 표시와 임의 export 파일명에 대한 형식 지정을 반영해 테스트를 바로잡았다. 실제 실행 결과를 가짜로 대체하지 않았다.
- 소단계 재개 안내를 UI에 추가하고 저장된 소단계를 초기화하지 않는 검사를 통과했다. 전체 소스 회귀342개 중283통과/59개 별도환경skip(27.920초). 이 회귀는 실제 VM 전체 채점 검증의 대체 증거가 아니다.

작성일: 2026-09-16. 감사 범위는 `course_spec.json`의 54개 목표·fixture·답칸·동등 풀이와 `guest_runtime.py`의 실제 판정 조건이다. **이 문서만 새로 작성했으며 과정, 채점기, 소단계, 검증 보고서, 실행 팩은 수정하지 않았다. 개인 Conda와 guest를 실행하거나 변경하지 않았다.**

## 결론과 증거 수준

참조 풀이가 통과하는 경로와 별개로 우선 정리할 정적 불일치가 있다. 목표에 없는 최종 활성 조건 5문제, 현재 상태 대신 시작 상태를 정답으로 삼는 읽기 2문제, 약속된 환경명/경로 정규화 미구현, 원본 보존에 이력 파일 바이트까지 요구하는 조건이다. 별도로 부모가 실제 확인한 base 활성 시 답안 채점 예외와, 대체 export 명령의 대상 누락을 기록한다.

- **실제 검증 — 기존 보고서 확인:** `desktop/.conda-build/course-validation.json`은 실제 guest Bash/Conda/Python 54문제와 대표 오답 수정 3개를 기록한다. `learning-validation.json`은 18단원 소단계 순차 실행 통과를 기록한다. 이 감사가 그 실행을 새로 수행한 것은 아니다.
- **정적 확정:** 문자열 비교식, 활성 상태 비교식, fixture와 기준의 선언 불일치는 소스에서 확인했다. 아래의 새 입력·명령 조합은 실제 guest로 실행하지 않았다.
- **실행 재현 후보:** 설치 이력 변화 및 신형 exporter의 실제 출력처럼 실제 Conda가 관여하는 차이는 재현 후보로 표시했다. 결과를 추측하여 성공/실패 로그로 기록하지 않는다.
- **누락 검사:** 54문제, 220개 기준, 19개 operation을 전부 훑었다. 기준의 환경 이름, 초기 활성 대상, 제거·변경 대상, 제공 export의 원본을 fixture와 대조하여 미해결 이름은 0개였다. 파일 관련 기준 22개와 모듈 probe 기준 35개도 대조하여 누락은 0개였다.

감사 기준본:

| 대상 | SHA-256 |
|---|---|
| `course_spec.json` | `1e45e6342350358df1bf3cbc3438a2d9355231f03a025472f08272c4f7dc921b` |
| `guest_runtime.py` | `19301d85f34371c7b81e218459160f31ad1df367f7f9caf8b02938b00a01f803` |
| `learning_steps.py` | `f7d7279eb8b2c7864577525c77c61d1cc7dd96f2cea6e586e8e8fd8d6174d02c` |
| `course_smoke.source_fingerprint()`와 같은 방식으로 읽기 전용 계산한 통합 fingerprint | `6f7bfe7e39d9f878d88550d85240a158406b4761820b27e082d3f32240d91bad` |

검사 당시 두 기존 실행 보고서의 fingerprint는 위 소스와 일치했다. 아래 줄 번호도 이 기준본에 대한 것이다. 부모의 후속 수정이 시작되면 이 문서는 **수정 전 감사 증거**이며, 새 소스가 실제 통과했다는 증명이 아니다.

## 감사 중 부모 수정 — 정적 재확인, 실제 재검증 대기

부모는 감사 결과를 받아 과정/채점기/검증기를 직접 수정했다. 이 감사자는 변경된 파일을 읽기만 했다. 다음은 **구현 반영 여부**이며 실제 guest 재검증 통과 판정이 아니다.

| 항목 | 후속 소스에서 읽은 상태 |
|---|---|
| A01 최종 활성 조건 5문제 | 설치·문장 설치·재구성 예시·복구 복습 4문제는 정확한 최종 활성 이름을 목표에 추가함. create_preserve는 최초 수정 문장이 sg-archive 활성 유지라고 되어 있어 `active(None)`와 불일치함을 즉시 부모에게 알림; 아래 보류 상태 참조 |
| A02 고정 현재 답 | 환경 목록 3문제 모두 환경/현재 선택 변경 금지 문장과 초기 상태의 `active` 기준을 추가함. 시작 상태를 유지하며 읽는 정책으로 정리 |
| A03 환경명/전체 경로 | `answer_matches`가 준비된 이름에 대해 할당된 전체 경로 표기도 비교하도록 추가됨. 동일 basename의 다른 경로는 거부하도록 구현 |
| A04 경로 정규화 | 절대경로 답에 POSIX 경로 정규화를 추가함. 실제 symlink 해석까지 지원한다고 확대 해석하지 않음 |
| A06 무관한 Python 검사 | answer_ref를 runtime/envs/shell selector별 지연 관찰로 변경하고 실제 base prefix를 base 이름으로 대응함 |
| 추가 답 표기 | Conda 대소문자, Linux guest의 명시된 한국어 동의어를 처리함. bool과 숫자 타입 구분은 유지 |
| 실제 검증 확장 | `course_smoke.answer_variants`에 새 동등 답/잘못된 경로/변경된 현재 상태/복구 등 12케이스를 추가함. `export_runtime.validate_report`에서 해당 케이스의 통과 기록을 요구하도록 함 |

부모는 전체 54문제+오답 수정과 18단원 소단계를 새 소스로 다시 실행하고 새 별도 팩을 내보낼 계획이라고 알렸다. 기존 성공 보고서가 있다는 이유만으로 위 수정이 검증됐다고 표시하지 않는다.

후속 보류: A05의 history 전체 해시 판정과 A07의 신형 export 대상 누락도 부모에게 전달했다. 실제 Conda 복구/대체 export는 이 감사에서 실행하지 않았다. create_preserve의 새 문장 불일치는 기존 기준대로 “마지막 활성 환경 없음”을 명시하는 정정을 요청했다. 이 중간 수정 상태를 최종 구현 완료로 간주하지 않는다.

## A01. 최종 활성 상태가 목표에 없는 5문제

분류: 목표에 없는 조건 / 정적 확정. 우선순위: 높음. 공통 근거는 `guest_runtime.py:249`의 `active` 판정이며, 기준은 단순히 Python 실행 성공이 아니라 **채점 순간의 셸 활성 상태**다.

| 문제 ID / 목표 위치 | 목표가 요구한 결과 | 추가로 검사하는 최종 상태 | 실제 guest 재현 후보 |
|---|---|---|---|
| `conda_create_preserve` / `course_spec.json:1283` | sg-archive를 보존하며 sg-scratch를 Python 3.12로 생성 | `active(None)` | 참조 생성 뒤 `conda activate sg-scratch`로 새 환경을 확인하고 그대로 채점 |
| `conda_install_example` / `:2452` | sg-sum에 설치하고 그 Python에서 합 7 확인 | `active('sg-sum')` | 참조 명령을 전부 수행한 뒤 `conda deactivate`하고 채점 |
| `conda_install_text` / `:2518` | sg-format에 설치하고 실제 문장 변환 확인 | `active('sg-format')` | 참조 명령을 전부 수행한 뒤 `conda deactivate`하고 채점 |
| `conda_recreate_example` / `:4349` | 원본 보존, 파일로 새 환경 생성, 새 환경의 계산 도구 실행 | `active('sg-rebuilt')` | 참조 명령을 전부 수행한 뒤 `conda deactivate`하고 채점 |
| `review_conda_03_recovery` / `:5505` | 두 기록 보존, 후계 환경 생성·실행, 원본 정리 | `active('sg-successor')` | 참조 명령을 전부 수행한 뒤 `conda deactivate`하고 채점 |

앞선 실제 풀이 검증은 참조가 이 최종 상태를 남기기 때문에 통과한다. 위 후보는 환경·파일·설치 결과를 망가뜨리는 오답이 아니라, 목표 문장만 읽었을 때 허용되는 작업 종료 상태다. 특히 다른 설치·재구성 문제 다수에는 `active` 조건이 없으므로 과정 전체에서 일관된 암묵 규칙이라고 배우기도 어렵다.

권장 조치: **학습량이나 조건을 줄이지 않고 목표에 최종 선택 상태를 적는다.** 예를 들어 create_preserve에는 “마지막 활성 환경은 없음으로 유지하세요”, 나머지 네 문제에는 각각 “확인을 마친 뒤에도 sg-…가 활성인 상태로 두세요”를 추가할 후보로 둔다. 기존 조건을 계속 유지한다면 최종 채점 라벨만으로 요구를 뒤늦게 알려 주지 않는다.

## A02. ‘현재 활성 환경’ 답이 시작 fixture에 고정됨

분류: 현재 사실과 다른 답 통과 / 현재 사실의 올바른 답 거부. 정적 확정. 우선순위: 높음.

`conda_env_list_example` (`course_spec.json:866`)과 `conda_env_list_active` (`:939`)는 현재 목록을 읽으라고 하지만 `answer` 기준으로 고정 문자열을 비교한다. 두 문제 모두 셸의 현재 활성 상태를 제한하는 `active` 기준은 없다. `unchanged`와 공통 원본 보존 게이트는 환경 설치 snapshot을 비교하므로 활성화만으로는 실패하지 않는다.

재현 후보:

1. **예시:** 새 fixture에서 `conda activate sg-notes` 후 `conda env list`를 읽는다. 경로 답을 맞게 쓰고 활성 답에 `없음`을 쓰면 코드상 통과 경로다. 실제로 관찰한 `sg-notes`를 쓰면 고정 답과 달라 거부된다.
2. **활용 1:** 새 fixture에서 `conda activate sg-publish` 후 목록을 읽는다. 실제 현재 활성은 sg-publish, 비활성 학습 환경은 sg-draft다. 그런데 `active='sg-draft', inactive='sg-publish'`라는 시작 상태 답이 통과하고, 현재 사실대로 뒤집어 쓰면 두 답이 모두 거부된다.

근거: `guest_runtime.py:241`의 고정 `answer`, `:256`의 설치 snapshot 비교, `:301` 이후의 환경 목록/보존 게이트. 실제 셸 snapshot은 `:222`에서 읽지만 이 답 두 개의 판정에는 사용되지 않는다.

권장 조치: 문제 의미를 먼저 확정한다. 현재 관찰을 평가할 것이면 신뢰된 현재 활성 prefix와 실제 존재 환경에서 답을 구한다. 시작 상태 읽기 문제로 유지할 것이면 목표를 “환경을 전환하지 않고 시작 상태의 목록을 읽으세요”로 명확히 하고 초기 활성 상태 유지도 검증한다. **고정 답만 남긴 채 ‘현재’라고 묻는 혼합 상태를 피한다.**

참고: `conda_env_list_active`의 “존재하지만 비활성인 환경 하나”는 목록에 보이는 base까지 포함할 수 있다. sg-publish를 유일한 답으로 삼으려면 “두 학습 환경 중 비활성인 쪽”으로 범위를 좁히는 것이 자연스럽다. base를 새 생성 대상으로 허용하자는 뜻이 아니다.

## A03. 전체 환경 경로 답을 허용한다는 약속이 구현되지 않음

분류: 명시된 동등 정답 거부 / 정적 확정. 우선순위: 중간.

대상은 `conda_env_list_active`. `equivalent_solutions`에는 전체 경로를 검증된 환경 이름으로 정규화하여 인정할 수 있다고 적혀 있다. 그러나 실제 `answer` (`guest_runtime.py:241`)는 타입과 앞뒤 공백을 제거한 문자열만 비교한다. `conda_app.py:112` 이후 답칸도 문자열을 받아 `:212`에서 그대로 전달한다.

재현 후보: 시작 상태를 전혀 바꾸지 않고 아래 답을 입력한다.

```text
활성 환경: /home/learner/conda-envs/sg-draft
존재하지만 비활성인 환경: /home/learner/conda-envs/sg-publish
```

두 경로는 준비된 실제 환경을 정확히 가리키지만 각각 `sg-draft`, `sg-publish`와 문자열이 달라 거부된다. A02처럼 활성 상태를 바꿀 필요도 없는 독립 사례다.

권장 조치: 이 답칸에만 allowlist에 있는 실제 환경의 이름/전체 경로 정규화를 적용한다. 문자열 끝부분만 잘라 임의 경로를 환경으로 인정하지 않는다. 또는 환경 이름 전용 선택 UI로 범위를 명료하게 만들되 기존 허용 약속도 함께 정리한다.

## A04. 경로 canonical 비교 계약과 실제 문자열 비교가 다름

분류: 명시된 동등 정답 거부 / 정적 확정. 우선순위: 중간.

`grading_operations.answer_ref`는 경로를 canonical path로 비교한다고 선언하고, `conda_identity_root` (`course_spec.json:781`)의 동등 풀이도 경로 정규화를 언급한다. 실제 `guest_runtime.py:246`은 `actual.strip() == value`만 수행한다.

최소 재현 후보: conda_identity_root의 실제 경로 답을 `/opt/shellground/miniconda/`로 쓰고 도구 답은 `Conda`로 쓴다. 끝의 슬래시는 같은 디렉터리를 나타내지만 채점 문자열은 일치하지 않는다. 이는 로컬 문자열/`posixpath.normpath` 비교로도 확인했으며 **실제 guest 판정은 아직 실행하지 않았다.**

같은 구현의 경로 답칸은 총 5개다.

| 문제 | 답칸 |
|---|---|
| `conda_identity_root` | `base_path` |
| `conda_env_list_example` | `notes_path` |
| `conda_env_list_missing` | `local_path` |
| `conda_interpreter_example` | `python_path`, `python_prefix` |

권장 조치: 선택자가 경로일 때만 guest의 실제 경로 규칙과 허용된 prefix에 따라 비교한다. 버전·플랫폼 문자열까지 경로로 정규화하지 않는다. 경로가 대상과 일치하는지 검증하며 임의 basename이나 다른 환경의 실행 파일은 계속 거부한다. `sys.executable`의 다른 유효 alias 허용 범위도 이 정책에서 명확히 한다.

## A05. 원본 보존 판정이 무해한 이력 변화/원상복구를 거부할 후보

분류: 계약보다 엄격한 동등 상태 판정. **비교 대상 차이는 정적 확정, 실제 Conda 복구 경로는 재현 필요.** 우선순위: 중간.

`grading_operations.unchanged`는 실제 패키지·설치 파일을 비교하며 무해한 이력 주석 같은 부산물은 비교하지 않는다고 선언한다 (`course_spec.json:506` 부근). 반면 snapshot은 `conda-meta/history`의 전체 SHA-256을 포함한다 (`guest_runtime.py:101`). `unchanged` (`:256`)와 공통 원본 보존 (`:303`)은 이 dictionary 전체를 비교한다. 따라서 패키지·요청 조건·실행 파일을 원래 상태로 맞추어도 history 바이트가 달라지면 통과할 수 없다.

대표 재현 후보는 `conda_update_preserve` (`course_spec.json:2997`)의 잘못된 대상을 수정하는 학습 흐름이다. **새 disposable fixture에서 부모 검증용으로만** 다음 순서를 시험할 수 있다.

```bash
conda install -n sg-stable training-math==1.1 --offline
conda install -n sg-stable training-math==1.0 --offline
conda update -n sg-experiment training-math --offline
```

이 흐름은 처음 실수한 설치를 실제 Conda로 되돌린다. 채점 전에 sg-stable의 패키지 metadata, 요청 spec, 모듈 파일 해시, Python 해시를 before와 비교하고 차이가 history에만 남는지 실제로 확인해야 한다. 코드상 history 차이가 남으면 `unchanged` 및 공통 보존 게이트가 거부한다. 또 같은 버전 `--force-reinstall` 후 설치 내용이 같아도 거래 이력이 추가되는 경우가 동등 상태 거부 후보다.

해석 주의: 목표의 “원본을 그대로 보존”을 **시도 중 절대 변경 금지**로 정의한다면 이 거부 자체는 정책 선택일 수 있다. 다만 현재 과정은 최종 결과 중심 정책과 잘못한 상태를 같은 세션에서 수정해 다시 채점하는 흐름을 설명하고 있고, unchanged 계약은 무해한 이력 차이를 제외한다고 명시한다. 이 세 부분을 일관되게 정할 필요가 있다.

권장 조치: learner 환경의 설치 상태 동등성과 실제 관리용 base/channel의 불변 정책을 분리한다. 복구를 허용하기 위해 보호 base의 변경을 용인하거나 이력 파일 수동 편집을 가르쳐서는 안 된다. 이력은 요청 spec/진단 근거로 보존하면서 최종 상태 비교에 필요한 의미만 사용할 수 있다. 이력 불변을 계속 요구한다면 F2 재준비가 필요한 이유와 조건을 목표/오답 피드백에서 명시한다.

## A06. base가 활성일 때 무관한 읽기 답까지 Python 검사 때문에 실패

분류: 숨은 실행 상태 의존 / 코드 근거 + **부모의 실제 재현 보고**. 우선순위: 높음. 이 감사자는 별도로 실행하지 않았다.

`answer_ref` (`guest_runtime.py:244`)는 selector가 runtime의 Conda 버전이라도 envs 전체와 `actual_python()`을 먼저 평가한다. base가 활성인 경우 `actual_python()`은 `/opt/shellground/miniconda`의 basename인 `miniconda`를 `prefix()`에 전달한다 (`:234`). `prefix()`는 `base` 또는 `sg-...` 이름만 허용하므로 이 단계에서 예외가 난다 (`:24`).

재현 대상: `conda_identity_example`의 fixture에서 `conda activate base` 후 실제 `conda --version`의 값을 맞게 답한다. 관리 도구 버전은 정상이며 base의 설치 내용도 바꾸지 않았지만 관련 없는 Python 경로 검사가 답 판정을 실패시킨다. 목표에는 base 비활성 조건이 없다.

영향 분석: answer_ref는 총 9개 기준/8문제에 사용된다. 모든 경우에 shell Python을 미리 관찰하는 구조지만, 실제로 shell Python이 필요한 selector는 `shell.python.executable` 하나뿐이다. `conda_interpreter_example`처럼 별도 활성 목표가 있는 문제의 의도적 거부와, runtime/version/path 읽기 문제의 무관한 예외를 구별해야 한다.

부모가 이미 실제 증상을 확인하고 수정 예정임을 전달했다. 권장 방향은 selector에 필요한 관찰만 평가하고 base의 prefix/name 대응을 안전하게 처리하는 것이다. 관리용 base 패키지 변경을 허용하자는 뜻은 아니다.

## A07. 대체 export 예시에서 실제 대상이 빠짐

분류: fixture에 맞지 않는 동등 풀이 안내. **정적 대상 누락 확정, 해당 신형 명령의 guest 실행 결과는 재현 필요.** 우선순위: 낮음~중간.

`conda_export_intent_example` (`course_spec.json:4090`)은 sg-share가 준비되어 있으나 활성 환경은 없다. 참조는 정확히 `conda env export -n sg-share ...`를 사용한다. 반면 동등 풀이에는 다음 명령이 단독으로 나온다.

```bash
conda export --from-history --format=environment-yaml --file share/environment.yml
```

이 명령에는 sg-share를 고르는 옵션도, 앞선 활성화 지시도 없다. 따라서 제공 fixture에서 이를 그대로 실행하면 sg-share를 대상으로 보장할 수 없다. 신형 exporter가 설치본에서 지원되더라도 대상 선택은 별도 필요하다. 공식 문서도 환경 대상에 `--name`/`--prefix`를 제공한다. [Conda 공식 env export 문서](https://docs.conda.io/projects/conda/en/stable/commands/env/export.html).

대체 안내 후보는 아래처럼 대상까지 완결한 명령이다. 이는 제안이며 설치된 26.7.1 guest의 실제 지원과 산출 YAML을 검증한 뒤 채택한다. 확인한 웹 문서는 26.7.2였으며 이를 26.7.1 실행 증거로 취급하지 않는다.

```bash
conda export -n sg-share --from-history --format=environment-yaml --file share/environment.yml
```

대상의 실제 YAML 내용이 틀리면 기존 manifest 판정이 거부하는 것은 옳다. 여기의 문제는 그 명령을 fixture-compatible 동등 풀이처럼 안내한 데이터이지, 잘못된 원본 export를 정답으로 인정해야 한다는 뜻이 아니다.

## 준비 상태·원본 누락 대조 결과

54개 문제의 기준 이름과 준비 자료 선언에서 실제 누락을 발견하지 못했다. 단순히 “모두 문제없음”으로 확장하지 않고 확인한 범위를 기록한다.

| 대조 항목 | 정적 결과 |
|---|---|
| 초기 `active_env`가 준비 환경에 존재 | 전부 일치 |
| 제거 대상이 초기 준비 환경에 존재 | 전부 일치 |
| 변경 대상이 초기 또는 지정 생성 환경에 속함 | 전부 일치 |
| 기준의 환경 이름이 초기/지정 생성/base 중 하나 | 전부 일치 |
| `real_export.source_env`가 초기 준비 환경에 존재 | 전부 일치 |
| manifest/재구성 기준 파일이 제공 파일 또는 준비된 출력 폴더 안에 있음 | 22개 기준 모두 일치 |
| 참조 명령 `--file` 대상이 제공 파일 또는 준비된 출력 폴더 안에 있음 | 전부 일치 |
| module 기준이 정의된 probe를 참조 | 35개 모두 일치 |

재구성 3문제는 각각 share/environment.yml, text/environment.yml, shared/environment.yml을 실제 원본 export로 준비한다. 삭제 뒤에도 export를 비교하는 두 문제는 `manifest_*_before`로 삭제 전 원본을 보관한다. 이 동작은 누락이 아니라 필요한 정상 설계다.

제공된 `real_export` 파일의 byte 보존은 공통 계약에 명시된 조건이다. 같은 YAML 의미의 주석 추가를 거부한다고 해서 자동으로 오채점이라고 판단하지 않았다. 새로 내보내는 파일의 의미상 비교와, 제공된 읽기 원본 보존을 구분한다. UI에서는 제공 원본 파일과 새 출력 파일을 계속 구별해 보여 주는 것이 좋다.

## 전체 검토 범위와 보류한 확대 해석

| 단원 | 문제 수 | 직접 연결한 감사 항목 |
|---|---:|---|
| conda_identity | 3 | A04, A06 |
| conda_env_list | 3 | A02, A03, A04, A06 |
| conda_create | 3 | A01 |
| conda_activate | 3 | 새 직접 불일치 없음 |
| conda_interpreter | 3 | A04 |
| review_conda_01 | 3 | A06의 runtime 답 관찰 경로 |
| conda_package_list | 3 | A06의 version 답 관찰 경로 |
| conda_install | 3 | A01 |
| conda_versions | 3 | 새 직접 불일치 없음 |
| conda_update | 3 | A05의 복구 재현 후보 |
| conda_remove_package | 3 | 새 직접 불일치 없음 |
| review_conda_02 | 3 | 새 직접 불일치 없음 |
| conda_isolation | 3 | 새 직접 불일치 없음 |
| conda_export_intent | 3 | A07 |
| conda_recreate | 3 | A01 |
| conda_export_snapshot | 3 | 새 직접 불일치 없음 |
| conda_remove_environment | 3 | 새 직접 불일치 없음 |
| review_conda_03 | 3 | A01 |

“새 직접 불일치 없음”은 해당 3문제의 모든 동등 풀이를 실제 실행했다는 뜻이 아니다. A05의 공통 원본 보존 비교는 여러 단원에 걸친다.

- 기존 실제 검증에서 처리한 `conda env remove --offline` 미지원, from-history의 `==1.0` → `=1.0` 정규화는 새 오류로 중복 보고하지 않았다.
- module probe가 신선한 Python으로 실제 함수·파일을 검사하는 것은 목표를 추가하는 작업 요구가 아니라 설치 정상성의 증거다. 학생이 probe의 모든 내부 입력을 별도로 실행해야 한다고 해석하지 않았다.
- 과거 명령 순서나 사용자가 실제로 읽기 명령을 입력했는지 증명하지 못하는 것은 이미 명시된 결과 중심 정책이다. 이를 해결하려고 CLI 감시기·가짜 출력·새 실행 엔진을 요구하지 않는다.
- `same_packages`는 name/version/build/subdir 외에 채널·URL 등 snapshot dictionary 전체를 비교한다. 선언보다 비교 범위는 넓지만, 동결된 단일 로컬 채널 안에서 일반적인 동등 풀이가 실제로 다른 metadata 표현을 만드는 재현을 확보하지 못했다. 따라서 확인된 오채점으로 집계하지 않는다.

## 후속 인수 검사 후보

1. A01의 최종 활성 상태 5개를 목표에 명시한 뒤, 활성 상태만 다른 오답을 거부하고 목표의 상태는 통과시키는지 확인한다.
2. A02는 두 읽기 문제에서 초기 상태/전환 후 상태를 각각 검증한다. 현재 사실과 반대인 고정 답이 통과하지 않아야 한다.
3. A03/A04는 허용된 이름·경로 표기와 유사하지만 다른 환경/파일 경로를 함께 시험한다. 정규화 추가 때문에 다른 환경이 정답으로 섞이면 안 된다.
4. A06은 비활성, 학습 환경 활성, base 활성에서 runtime 버전/경로 읽기를 검증한다. shell Python이 필수인 문제의 실제 활성 조건은 유지한다.
5. A05는 실제 오답 거래 → 실제 원상복구 후 before/after 차이를 확인하고, 정한 보존 정책대로 판정하는지 검증한다. history를 손으로 고쳐 통과시키지 않는다.
6. A07은 대상이 명시된 신형 export가 실제 설치본에서 동작할 때만 동등 풀이로 확정한다.
7. 채점기/문제 목표가 바뀐 뒤에는 **기존 54문제+3오답 수정, 18단원 소단계 전체를 새 fingerprint로 다시 실행**한다. 이 감사 문서나 옛 성공 보고서를 새 버전 성공 증거로 재사용하지 않는다. 후속 검증이 끝나야 별도 Conda 실행 팩을 다시 내보내고 이전 검증 팩과 교체한다.
