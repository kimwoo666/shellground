# Conda 설명·소단계 실습 사용성 감사

## 부모 통합 후 검증 — 2026-09-16

아래는 수정 전 정적 감사 이력이다. 이후 실제 UI에 `STEPS`를 연결했고18단원/54소단계의 순차 실행이 실제 Conda에서 통과했다. 현재 `learning-validation.json`의 source hash는 `f7d7279eb8b2c7864577525c77c61d1cc7dd96f2cea6e586e8e8fd8d6174d02c`이다. 원문 풀이54문제의 실제 검증도 별도로 완료했다.

아래 제안 중 **재개 시 첫 소단계로 돌아가기**는 채택하지 않았다. 사용자가 저장한 학습 위치는 유지하고 `이전 소단계 준비 보기`로 필요한 준비 설명을 제공한다. 입력/실습 파일 저장과 학습 위치 저장을 구별하며 명령 자동 실행·완료 임의 부여를 하지 않는다. 이 동작은 UI 회귀 검사로 확인했다. 실제 앱의 오답 수정·파일 탭·진도 저장·종료 검증도 통과했다.

감사일: 2026-09-16. 대상은 `course_spec.json`의 18단원과 각 단원의 **첫 번째 example fixture**, 현재 PC의 `conda_app.py` 학습 화면이다. 기존 원문·참조 풀이·채점·runtime·UI는 수정하지 않았다. 새 제안 데이터는 `learning_steps.py`의 `STEPS`에만 작성했다.

감사 전후 확인한 `course_spec.json` SHA-256:

```text
1e45e6342350358df1bf3cbc3438a2d9355231f03a025472f08272c4f7dc921b
```

## 결론

18단원 중 10단원의 `syntax`가 해당 예시에서 준비되거나 생성 허용된 이름이 아닌 `sg-project`, `sg-one`, `sg-two`를 포함한다. 설명 속 추상적인 기본 형태를 현재 터미널에서 바로 실행하도록 제시하면 실패하거나 다른 환경을 만들 수 있다. **학습 단계의 실행 명령은 해당 예시 fixture와 결합되어야 한다.**

이름 치환만으로 해결되지 않는 문제도 있다. Python 진단 이전의 활성화가 빠진 단원, 해제를 끝까지 따라 하면 예시의 최종 활성 목표와 달라지는 단원, 예시 범위를 벗어난 새 환경 생성을 요구하는 단계가 있다. 제안은 범위를 줄이지 않고 실행 순서와 학습 장소를 명확히 한다.

이 감사에서 실제 Conda 명령은 실행하지 않았다. 아래 데이터는 **정적 감사와 구문 검사를 통과한 제안**이지 실제 guest의 연속 실행 성공 보고가 아니다. 부모 작업자의 별도 실제 실행 검증이 끝난 뒤 배포 상태를 정해야 한다.

## 현재 UI의 상태 경계 — 이전 발견 정정

현재 코드를 다시 읽어 확인한 사실은 다음과 같다.

- `conda_app.py:58,62,161`의 F4/버튼은 `try_lab`에 연결된다. 터미널이 연결되어 있으면 focus만 이동하고, 연결되지 않았을 때만 실습을 준비한다. **F4를 반복해도 정상 연결 중인 상태는 초기화되지 않는다.** 초기에 읽었던 이전 구현을 근거로 한 “F4 재진입 초기화” 지적은 철회한다.
- F2와 다시 시작 버튼은 `start`에 연결된 의도적인 초기화다. 이것을 다음 소단계로 가는 동작과 구별해 안내한다.
- `previous_step`과 아직 다음 소단계가 남은 `advance`는 `render`만 하므로 **단원 안의 소단계들은 같은 지속 Bash 상태를 이어 쓴다.**
- 마지막 learn 소단계에서 example 단계로 넘어갈 때는 현재 `advance`가 phase를 바꾼 뒤 `start`를 호출한다. 따라서 **설명 연습 → 채점 가능한 예시는 새 example fixture로 시작**한다. 이 경계를 알려 이미 생성한 환경이 왜 다시 없어졌는지 혼란스럽지 않게 한다.
- learn에서는 답칸과 채점이 숨겨진다. 읽기 단계는 실제 값을 관찰하는 연습이고, example의 답칸 제출이나 완료 판정과는 다르다.
- 준비된 파일과 내보낸 YAML은 이미 구현된 **읽기 전용 파일 탭**에서 본다. 초보자에게 아직 배우지 않은 파일 읽기 명령이나 JSON 보고서 작성을 요구하지 않는다.

## 단원별 감사표

`P3.12`는 Python 3.12 계열, `M1.0/M1.1`은 training-math, `T1.0`은 training-text다. 실제 경로와 버전 patch는 화면·명령 결과에서 읽는다. 아래 모든 생성·변경 대상은 example에 선언된 범위 안이다.

| 단원 key | 예시 준비 상태 | 원문에서의 문제 또는 확인 사항 | 제안의 3단계 / 최종 상태 |
|---|---|---|---|
| conda_identity | 학습 환경 없음, 비활성 | 명령은 호환됨. 도구 버전·Python·host/guest 구별이 중요 | info에서 장소 → Conda 버전 → base·platform 재확인. 설치 변경 없음 |
| conda_env_list | sg-notes(P3.12), 비활성 | 명령은 호환됨. 목록에 base가 있어도 활성으로 오해하면 안 됨 | 환경 찾기 → 별표 확인 → 경로와 비활성 기록. 설치 변경 없음 |
| conda_create | sg-analysis 부재, 생성 허용 | `sg-project`를 만들면 실패 대신 **잘못된 새 환경**이 생길 수 있음 | 부재 확인 → sg-analysis 생성 → 목록 확인. 비활성 유지 |
| conda_activate | sg-work(P3.12), 비활성 | `sg-project` 없음. 이름만 고쳐도 마지막 deactivate는 예시의 활성 목표와 어긋남 | sg-work 활성 → 해제 관찰 → sg-work 다시 활성. 환경 보존 |
| conda_interpreter | sg-code(P3.12), 비활성 | syntax의 Python 명령 앞에 실제 대상 활성화가 없음 | sg-code 활성 → Python 버전 → 실행 파일·prefix 확인. sg-code 활성 유지 |
| review_conda_01 | sg-notebook(P3.12) 활성, sg-lab 생성 허용 | “조합합니다”만 있어 설명 보며 실행할 단계별 명령이 없음 | 기존/새 이름 구별 → sg-lab 생성 → 활성·Python 확인. sg-notebook 보존 |
| conda_package_list | sg-calc(P3.12,M1.0) 활성 | `conda list`는 맞지만 `--name sg-project`는 없음 | 대상 환경 확인 → 현재 패키지 목록 → sg-calc 명시 목록. 설치 변경 없음 |
| conda_install | sg-sum(P3.12), 비활성 | 설치·활성화 대상 `sg-project`가 없음 | 미설치 확인 → sg-sum에 설치 → 활성화하고 total 실행. sg-sum 활성 |
| conda_versions | sg-classic(P3.12), 비활성 | `sg-project` 없음. 이름만 고쳐도 Python 진단 전 활성화가 빠짐 | 1.0 요청 → 설치 목록 → sg-classic 활성·모듈 버전 확인 |
| conda_update | sg-average(P3.12,M1.0) 활성 | 존재하지 않는 `sg-project`에 update | 기존 버전 → sg-average 갱신 → 새 버전·mean 실행. 활성 대상 유지 |
| conda_remove_package | sg-clean(P3.12,M1.1,T1.0) 활성 | 존재하지 않는 `sg-project`에 remove/list | 남길/뺄 도구 → text만 제거 → 목록·Python·math 실행. 환경 보존 |
| review_conda_02 | sg-analysis(P3.12,M1.0,T1.0) 활성 | 조합 지시만으로 갱신과 제거의 각 목적을 읽기 어려움 | 차이 조사 → math 갱신·text 제거 → mean 실행. Python·환경 보존 |
| conda_isolation | sg-reference와 sg-research 모두 P3.12,M1.0, 비활성 | `sg-one/sg-two` 없음. 두 곳 모두 미활성인데 Python 진단만 제시됨 | 두 실제 목록 → research만 갱신 → 각각 활성·모듈 소속 확인. reference 보존 |
| conda_export_intent | sg-share(P3.12,M1.0), 비활성; share/ | `sg-project` 없음. 내보내기 성공 시 stdout이 비어 실패로 오해할 수 있음 | 원본·폴더 확인 → share/environment.yml 저장 → 파일 탭 읽기 |
| conda_recreate | sg-source(P3.12,M1.0), 비활성; 실제 share/environment.yml; sg-rebuilt 생성 허용 | 이름·파일은 호환됨. syntax만으로는 실제 Python·모듈 검증이 빠짐 | 제공 파일/부재 읽기 → 새 이름 생성 → 활성·prefix·모듈 확인. 원본·파일 보존 |
| conda_export_snapshot | sg-capture(P3.12,M1.1), 비활성; intent/, full/ | `sg-project` 없음. 3번째 microstep의 **새 환경 재구성은 created_envs/mutable_envs가 빈 예시 범위를 벗어남** | 요청 파일 → 전체 파일 → 두 내용 비교. 재구성은 활용 1에서 이어 수행 |
| conda_remove_environment | sg-finished(P3.12,M1.0) 활성, sg-keep(P3.12,T1.0) | 현재 수정된 이름/명령은 호환됨. env remove에 --offline을 재추가하면 안 됨 | 대상 확인 → 해제/목록 → finished 제거/목록. keep 보존, 비활성 |
| review_conda_03 | sg-source(P3.12,M1.0), sg-obsolete(P3.12), 비활성; share/; sg-copy 생성 허용 | 복합 작업을 원본 보존·복사본 확장·정리로 나눌 필요 | 원본 export → 복사본 생성·text 추가·실행 → 상태 비교·obsolete 제거. 원본/복사본/파일 보존 |

## 새 실행 단계 데이터

`learning_steps.py`는 다음 계약을 가진다.

```python
STEPS: dict[str, tuple[dict, ...]]
# 각 단원에는 정확히 세 단계가 있으며 각 단계의 필드는 다음 네 개다.
# {"title": str, "explanation": str, "commands": tuple[str, ...], "observe": str}
```

전체 18단원의 fixture-compatible Python dict 데이터는 해당 파일에 작성했다. 원문과 감사 문서에 서로 다른 전체 사본을 중복 저장하지 않는다. 다음 코드블록은 부모 UI에서 그대로 읽을 수 있는 데이터 연결 예시다. UI·엔진을 여기서 변경하거나 명령을 자동 실행하지 않는다.

```python
from conda_teaching.learning_steps import STEPS

unit_steps = STEPS[unit["key"]]
step_data = unit_steps[step_index]
commands_text = "\n".join(step_data["commands"])
if not commands_text:
    commands_text = "이번 단계는 추가 명령 없이 읽기 전용 파일 탭에서 확인합니다."
step_text = "\n\n".join((
    step_data["title"],
    step_data["explanation"],
    commands_text,
    "관찰할 것\n" + step_data["observe"],
))
```

기존 전체 설명의 `syntax`는 추상적인 형태 설명으로 따로 남길 수 있지만, **실행하도록 제시하는 현재 단계 명령을 다시 generic 이름의 syntax로 덮어쓰면 안 된다.** 현재 소단계 명령과 관찰 목표를 인접하게 보여 준다. 활용 평가 화면에 설명과 실행 예시를 누설하지 않는 기존 구분도 유지한다.

`commands=()`인 단계는 `conda_export_intent`와 `conda_export_snapshot`의 마지막 단계다. 아무 작업도 하지 않는 빈 단계가 아니라 실제 YAML을 읽는 관찰 과제다. 파일 탭 새로고침/선택 안내를 보여 주고 빈 문자열을 명령으로 전송하지 않는다.

## 순차 실행과 주의

1. 각 단원은 **해당 단원의 example fixture**를 실제로 준비하고 시작한다. 직전 단원의 터미널 상태를 임의로 가져오지 않는다.
2. 세 소단계는 같은 Bash에서 순서대로 실행한다. 이전/다음 화면 이동은 셸 상태를 되감지 않는다. 특히 생성·제거를 이미 한 뒤 이전 단계로 돌아가면 그 명령을 무조건 다시 실행하지 않는다. 필요한 경우 F2가 이 예시를 다시 준비한다는 안내를 쓴다.
3. 명령은 한 줄씩 완료를 기다린다. 실제 거래 계획에서 대상과 패키지를 읽은 뒤 승인 질문에 y로 응답한다. **`y`는 commands 항목에 넣지 않았고**, 실패한 명령 다음으로 무조건 진행하지 않는다.
4. `conda deactivate`는 직전 활성 상태로 복귀한다. `conda_activate` 단계는 해제를 관찰한 뒤 sg-work를 다시 활성화해 예시의 최종 목표를 맞춘다. 분리 단원은 reference → research 전환 뒤 research가 현재 상태이며 한 번 해제하면 reference로 돌아간다는 사실을 명시한다.
5. 생성·변경 명령은 문제에 배정된 실제 이름만 쓴다. generic 이름을 사용할 추가 환경을 미리 만들어 우회하지 않는다. 그렇게 하면 학습자가 목표와 임의 환경을 혼동하고 원래 채점 범위를 늘리게 된다.
6. 파일은 이미 준비된 share/, intent/, full/ 또는 제공된 share/environment.yml만 사용한다. 제공된 재구성 파일은 읽기 전용 원본으로 보존하고 학생에게 절대경로·mkdir·YAML 수동 편집을 새 과제로 떠넘기지 않는다.
7. 내보내기는 성공해도 stdout이 비어 있을 수 있다. 터미널에 눈에 띄는 문구가 없다는 이유로 실패라 판단하지 말고 실제 파일을 읽는다. 파일 저장과 실제 환경 생성은 다른 단계다.
8. 읽기 단계의 명령 결과만으로 답칸 작성이나 과정 완료를 자동 처리하지 않는다. 현재 learn은 관찰 연습, example은 실제 상태와 답을 평가하는 단계라는 구분을 유지한다.

### 새 fixture와 저장된 소단계의 경계

활성 세션에서 F4를 다시 누르는 동작은 focus만 하므로 현재 상태를 유지한다. 이것과 **새 fixture를 여는 동작**을 구분해야 한다. 중간 단계에서 F2로 초기화하거나, 중간 소단계가 저장된 채 앱을 재시작한 다음 F4로 새 세션을 준비하면 앞 단계의 실제 작업은 아직 실행되지 않은 상태다. 이때 화면만 중간 단계에 머물면 존재하지 않는 환경을 활성화하거나 아직 없는 파일을 관찰하게 될 수 있다.

통합 시 확인할 계약은 다음과 같다. learn에서 새 fixture를 준비하면 첫 소단계로 돌아가고 그 사실을 안내한다. 실제 셸 상태를 검증하여 복구하는 기능이 따로 없다면 저장된 단계 번호만으로 실행 상태까지 복구되었다고 가정하지 않는다. 반대로 이미 연결된 세션의 F4 및 단순 이전/다음 이동은 초기화하지 않는다. 이 항목은 변경 중인 부모 UI의 최종 동작을 단정하는 버그 보고가 아니라 인수 검사 조건이다.

## 확인된 버전 차이와 검증 한계

- 부모 작업자가 실제 설치본 **Conda 26.7.1**에서 `conda env remove`가 `--offline`을 받지 않음을 확인하고 원문 참조 풀이를 고쳤다. 새 단계 데이터도 env remove에는 이 옵션을 사용하지 않는다. 환경 전체 제거와 `conda remove PACKAGE --offline`은 서로 다른 CLI 형태다. 뒤의 패키지 제거는 기존 참조와 같은 형태를 사용한다.
- 실제 from-history export가 `training-math==1.0` 요청을 `training-math=1.0`으로 내보내는 정상 정규화가 확인되었다. 학생에게 ==의 문자 개수를 맞추도록 파일을 고치게 하지 않는다. 다만 모든 버전 문자열을 무차별로 같다고 보는 의미는 아니며 실제 export·요구 조건과 설치 결과를 확인한다.
- Python은 3.12 **계열**을 읽는다. 이 설명의 숫자를 실제 patch 결과로 대신하지 않는다. Conda 버전과 플랫폼도 실제 출력에서 읽는다.
- 이 감사에서는 지원 여부를 모르는 새 옵션, 외부 채널, 네트워크 설치, host Conda, 시스템 설정 변경을 도입하지 않았다. 그래도 명령 형태가 기존 참조와 유사하다는 사실만으로 **실제 연속 실행 성공을 보장하지 않는다.**

## 정적 검증 결과

`learning_steps.py`를 독립 import하고 실제 source fixture에 대조했다.

- 단원 key 18개가 원문과 정확히 일치하고 모두 3단계: 총 54단계.
- 네 필드의 형식과 비어 있지 않은 설명/관찰 문자열 확인.
- 실행 명령 77개의 Bash 구문 검사와 Python `-c` 진단식 11개의 AST 검사 통과. 이것은 실제 Conda 실행이 아니다.
- 모든 명령의 환경 이름이 준비된 환경 또는 명시된 생성 대상에 속함. generic 이름과 `y` 단독 명령 없음.
- 파일 대상이 해당 예시의 준비된 폴더/파일 안에 있음. 새 절대경로·상위 경로 이동 없음.
- 초기 activation_stack에서 명령 순서를 따라 점검했을 때 명시된 최종 active 조건 모두 일치. 제거 대상은 현재/복귀 스택에 남지 않음.
- `env remove --offline` 없음. 파일 관찰만 하는 빈 command tuple은 정확히 2개.
- 위 SHA-256은 감사 시작과 정적 검사 종료 때 동일함. fingerprint 대상 원문은 수정하지 않음.

## 실제 guest 인수 검사 — 부모 통합 후 필요

18단원을 각각 새 example fixture에서 시작하여 3단계를 연속 실행한다. 생성/설치/제거는 실제 승인을 처리하고, 파일 단계에서는 읽기 전용 탭의 새로고침·내용을 확인한다. 마지막 상태를 기존 example의 모든 상태 조건으로 평가하며 읽기 문제의 답은 실제 관찰값을 답칸에 입력한다.

특히 활성화 단원의 활성 → 해제 → 재활성, 해제된 상태에서 다시 실행하는 Python 진단, 다른 환경만 갱신하는 분리 단원, 표준 출력이 없는 export, 전체 기록 단원의 **새 환경 생성 없음**, 파일 기반 재구성의 새 이름 우선, env remove의 옵션 차이를 실제로 확인한다. F4 재진입·소단계 이동 시 상태 유지, F2·앱 재시작 후 새 세션의 첫 소단계 복귀, 마지막 learn → example 전환 시 새 준비도 UI에서 확인한다.

실제 검증 전 이 데이터의 상태는 **후속 실행 검증 필요**다. 실패를 모의 출력·가짜 설치 완료·원문 기대값으로 덮어서는 안 된다.
