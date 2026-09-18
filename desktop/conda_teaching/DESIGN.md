# 실제 Conda 입문 과정 설계

`course_spec.json`은 UI와 실행 엔진에 독립적인 한국어 문제 초안이다. 실제 Conda의 결과를 채점하는 과정이며, 명령 출력 시뮬레이터가 아니다. 정규 15단원과 5단원마다 넣는 복습 3개, 단원당 예시·활용 1·활용 2의 3문제로 총 54문제를 제공한다. 설치는 별도 0단계 준비 게이트와 선택 실습 1개로 분리한다.

이 작업은 과정 데이터와 설계 문서만 작성한다. 개인 host의 Conda를 조회하거나 변경하지 않았으며, installer·guest·UI·기존 Python 과정의 코드는 수정하지 않았다. 실제 runtime 구현과 전체 54문제의 실행 검증은 통합 담당자의 후속 작업이다.

## 1. 학습 범위와 출처

기존 `python_teaching/quiz_blueprint.md`에서 확인된 PDF 물리 페이지를 배경으로 사용한다.

| 자료 | 실제 페이지 | 이 과정과의 관계 |
|---|---:|---|
| Week 1_1.pdf | 13·14 | 로컬 환경 선택, Conda 사용 권장, 실행·저장 장소 구별 |
| week_1_2_handout.pdf | 34 | 패키지 설치와 pip/Conda 소개 |

강의의 설치 소개를 상세한 Conda 실습으로 확장한 것이므로 **모든 새 단원은 `source="supplement"`, `pages=[]`**다. PDF에 세부 명령과 전체 과정이 실렸다고 주장하지 않는다. 강의의 Conda/Anaconda 혼동은 관리 도구와 배포판을 구별하여 보정한다. 강의 문장·그림은 복제하지 않았다.

공식 문서는 2026-09-16에 확인했다. 확인한 stable 문서는 Conda 26.7.2를 표시했으며 런타임 후보는 26.7.1이다. 특정 문서 버전의 새 옵션이 무조건 설치본에도 있다고 가정하지 않고 `runtime_contract.feature_tests`를 실제 실행한다.

| 근거 | 적용한 사실 |
|---|---|
| [Conda 시작 안내](https://docs.conda.io/projects/conda/en/stable/user-guide/getting-started.html) | Conda 관리 도구와 최소 설치 배포판, 생성·목록·활성화의 기본 구분 |
| [Miniconda 시스템 요구사항](https://www.anaconda.com/docs/getting-started/miniconda/system-requirements) | OS·CPU·glibc 요구를 확인해야 하며 Android 네이티브 공식 지원으로 표시하지 않음 |
| [공식 일괄 설치 안내](https://www.anaconda.com/docs/getting-started/advanced-install/silent-mode) | Linux 설치 파일의 `-b`, `-p`; 셸 설정 변경과 설치를 분리 |
| [환경 관리](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html) | 환경 생성·활성화·해제·내보내기·재구성·제거 및 플랫폼 제약 |
| [create](https://docs.conda.io/projects/conda/en/stable/commands/create.html), [info](https://docs.conda.io/projects/conda/en/stable/commands/info.html) | 실제 생성과 계획 출력의 차이, JSON은 관찰자용 |
| [list](https://docs.conda.io/projects/conda/en/stable/commands/list.html), [install](https://docs.conda.io/projects/conda/en/stable/commands/install.html) | 설치된 패키지 조사, 대상 이름과 버전 조건 |
| [update](https://docs.conda.io/projects/conda/en/stable/commands/update.html), [패키지 관리](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-pkgs.html) | 호환되는 최신 버전 탐색, 의존 패키지의 동반 변경, 지정 패키지 제거 |
| [env export](https://docs.conda.io/projects/conda/en/stable/commands/env/export.html) | 직접 요청 기록과 전체 설치 기록의 차이, 기존 파일 덮어쓰기 위험 |
| [env create](https://docs.conda.io/projects/conda/en/stable/commands/env/create.html) | 파일 기반 생성과 CLI의 새 환경 이름 지정 |

## 2. 확정된 실행 계약

모든 host OS에서 **앱 전용 실제 Linux guest**를 사용한다. Windows/macOS/Linux host의 개인 Conda를 실행하는 과정도, Android 네이티브 Conda 설치라고 표시하는 과정도 아니다. Linux guest가 실제로 준비되지 않은 플랫폼은 실습 준비 미완료로 표시한다.

| 항목 | 계약 |
|---|---|
| 관리용 Conda base | `/opt/shellground/miniconda`, 학습 문제에서 수정·업데이트·삭제 금지 |
| 학습 환경들 | `/home/learner/conda-envs` 아래의 문제별 `sg-*` 이름 |
| 실제 채널 | `file:///opt/shellground/conda-channel`, 동결된 로컬 repodata와 패키지 파일 |
| Python | 3.12 계열. 학생에게 정확한 patch 문자열 암기 요구 없음 |
| 설치 후보 | 공식 `Miniconda3-py312_26.7.1-1`; 최종 실행 버전은 관찰된 manifest 값 |
| 플랫폼 | 우선 실제 `linux-64`; `linux-aarch64`는 별도 빌드·검증 후 활성화 |
| 셸 | 초기화된 지속 Bash. 각 명령마다 새 셸로 바꾸지 않음 |
| 설정·캐시 | guest 전용 CONDARC, envs_dirs, pkgs_dirs. 개인 설정을 읽지 않음 |
| 학습 패키지 | 실제 noarch:python `training-math` 1.0/1.1, `training-text` 1.0 |

`CONDARC` 환경변수를 넣었다는 사실만으로 격리가 증명되지는 않는다. **learner 프로세스에서** 실제 효과가 있는 설정, 디렉터리 소유권, 쓰기 권한, Conda root, 채널을 확인해야 한다. 읽기 전용 base/채널, 허용된 환경 prefix와 workspace, host 개인 폴더 비노출은 실행 엔진의 경계다. 게스트라는 이름이나 설정 파일 하나를 보안 경계라고 과장하지 않는다.

화면에는 guest ID, host OS, 실제 실행 OS, 실제 guest 루트의 저장 위치, 문제 workspace, Conda root, envroot, 로컬 채널 위치를 표시한다. 이 경로는 앱의 실제 관찰값으로 채우고 학생에게 외우게 하지 않는다. 표시용 마커 파일만 만들어 guest 실행 성공을 주장해서도 안 된다.

앱의 기존 Python 실습 실행기와 새 Conda 환경의 Python은 별개다. 기존 NumPy 실습이 실행되었다는 사실은 Conda 설치·생성·활성화의 증거가 아니다.

### 오프라인 패키지의 의미

작은 교육 패키지만 준비해서는 Python 환경을 만들 수 없다. guest-native Python 3.12와 전체 의존 패키지, noarch 의존성을 함께 제공해야 한다. builder는 실제 배포 archive, 설치 metadata와 필요한 repodata 보정, 해시, 라이선스/재배포 조건을 검증한다. 이 설계는 외부 채널의 이용 약관에 대신 동의하거나 재배포 권한을 추정하지 않는다.

학생 명령은 이미 설정된 로컬 채널을 사용한다. `--offline`의 의미를 생성 단원에서 가르치며, 긴 절대 채널 경로나 가르치지 않은 `--override-channels` 옵션을 매 문제 외우게 하지 않는다. 네트워크 차단과 올바른 채널 선택은 앱의 실제 설정으로 보장한다. 해결 실패 시 온라인 다운로드나 개인 base 설치를 자동 대안으로 사용하지 않는다.

교육 패키지의 실제 API 계약은 다음과 같다.

| 패키지 | 실제 import와 기능 |
|---|---|
| training-math 1.0 | `training_math.__version__ == "1.0"`, `total(values) == sum(values)` |
| training-math 1.1 | 위 기능과 `mean(values)` 추가. 평균 검증에는 비어 있지 않은 입력만 사용 |
| training-text 1.0 | `training_text.__version__ == "1.0"`, `normalize(text) == text.strip().upper()` |

두 패키지는 서로 의존하지 않아 하나를 제거해 다른 도구까지 사라지는 숨은 함정을 만들지 않는다. 새 API는 설명에서 먼저 소개하고 제공된 짧은 Python 진단식으로 확인한다. Python 함수 정의 문법을 Conda 문제의 새 선수 조건으로 넣지 않는다.

## 3. 설치 0단계

준비 게이트는 실제 guest, 검증된 바이너리, 올바른 root_prefix/platform, learner의 환경 생성 권한, 오프라인 의존성, 지속 셸의 활성화/해제를 확인한다. 실패는 ‘실행 준비 오류’이며 학생의 개념 오답이나 성공으로 바꾸지 않는다.

선택 실습은 **한 번의 실제 새 설치**다. 앱이 읽기 전용 공식 installer 경로 `{{installer_path}}`와 아직 존재하지 않는 새 설치 경로 `{{student_install_prefix}}`를 채워 보여 준다. `-b`/`-p`의 의미를 먼저 설명한다. 필요한 실제 라이선스 안내와 동의 절차는 설치 실행 전에 처리한다.

```bash
bash "{{installer_path}}" -b -p "{{student_install_prefix}}"
"{{student_install_prefix}}/bin/conda" --version
"{{student_install_prefix}}/bin/conda" info --json
```

이는 토큰이 해소되기 전 그대로 실행할 명령이 아니다. 새 경로가 기존 base나 기존 자료와 겹치면 차단한다. installer의 실제 종료 결과와 **새 경로 바이너리**의 실행·root_prefix·platform을 함께 확인한다. 정답 같은 문구, 빈 폴더, 기존 base의 버전은 새 설치 성공 증거가 아니다. JSON 진단은 제공된 검증 명령이며 학생이 JSON 보고서를 작성하는 과제가 아니다.

설치 실습은 별도 셸을 사용하고 본 과정은 보호된 관리용 base의 셸로 돌아온다. host의 `conda init`, 프로필 수정, 시스템 PATH 변경, 관리자 권한, 재귀 삭제는 요구하지 않는다. 선택 설치 결과를 정리하려면 검증된 정확한 prefix와 명시적 정리 동의를 받는 별도 UI를 사용한다.

## 4. 점진적 수업과 복습

각 단원은 `explanation → 짧은 microsteps 3개 → 예시 → 서로 다른 활용 1·2` 순서다. 예시 해설에만 참조 명령을 기본 노출하고 활용 문제는 목표·초기 상태를 먼저 보여 준다. 활용 문제에 정답 코드를 미리 붙이지 않는다. 힌트는 학생이 요청하거나 피드백이 필요할 때 공개한다.

| 순서 | key | 새로운 핵심 | 세 문제의 다른 목적 |
|---:|---|---|---|
| 1 | conda_identity | 관리 도구와 실행 장소 | 버전 읽기 / guest 플랫폼 / base와 앱 실행기 구별 |
| 2 | conda_env_list | 환경 존재와 활성 상태 | 경로 찾기 / 활성·비활성 구별 / 없는 환경 조사 |
| 3 | conda_create | Python 계열을 지정한 생성 | 하나 생성 / 두 프로젝트 분리 / 기존 환경 보존 |
| 4 | conda_activate | 현재 셸의 전환·해제 | 활성화 / 다른 환경으로 전환 / 삭제 없이 해제 |
| 5 | conda_interpreter | 실제 Python 소속 확인 | 경로 진단 / 같은 버전의 다른 환경 / 생성부터 실행까지 연결 |
| 복습 1 | review_conda_01 | 앞의 5개만 조합 | 원본 보존·새 실험 / 발표 환경 인계 / 두 환경 준비 후 비활성 |
| 6 | conda_package_list | 설치 패키지 조사 | 설치 버전 / 비활성 대상의 부재 / 두 환경 버전 비교 |
| 7 | conda_install | 설치와 import 연결 | 계산 도구 / 문장 도구 / 기존 도구 보존하며 추가 |
| 8 | conda_versions | 버전 조건과 실제 결과 | 옛 버전 / 두 과제의 다른 버전 / 하위 버전으로 맞추기 |
| 9 | conda_update | 호환 최신 버전 | 새 기능 / 안정 환경 보존 / 기존 다른 기능 보존 |
| 10 | conda_remove_package | 패키지 제거 | 하나만 제거 / 비활성 대상만 제거 / Python 의존성 보존 |
| 복습 2 | review_conda_02 | 앞의 5개만 조합 | 갱신+불필요 도구 제거 / 역할별 다른 상태 / 원본 보존+조사 |
| 11 | conda_isolation | 환경별 독립 상태 | 버전·모듈 소속 분리 / 역할 분리 / 한쪽 제거 영향 비교 |
| 12 | conda_export_intent | 직접 요청 사항 YAML | 요청 저장 / 비활성 원본 선택 / 두 요구사항 분리 |
| 13 | conda_recreate | 파일의 요구로 새 환경 | 원본 보존 재구성 / 다른 역할의 파일 / 한 파일로 독립 복사본 둘 |
| 14 | conda_export_snapshot | 전체 설치 기록과 의도 비교 | 두 기록 생성 / 같은 guest의 구체적 상태 재현 / 이식성 판단 |
| 15 | conda_remove_environment | 환경 전체 정리 | 활성 해제 후 정리 / 요청 기록 보관 / 임시 복사본만 정리 |
| 복습 3 | review_conda_03 | 앞의 5개만 조합 | 공유 후 복사본 확장 / 전체 기록 재현 / 기록·후속 환경·원본 정리 |

`prerequisites`는 이 JSON 안의 **단원 key**다. 기존 개념 퀴즈의 topic이나 질문 ID가 아니다. 복습의 prerequisites와 review_of는 바로 앞 다섯 원단원 key와 정확히 일치한다. 복습은 새 Conda 명령·옵션·Python 진단 API를 도입하지 않는다.

활성화 해제는 ‘모두 비활성화’가 아니라 **가장 최근 활성화 직전 상태로 복귀**하는 작업이다. 비활성 → A 활성화 → B 활성화 → 해제는 A로 돌아간다. `--stack`을 쓰지 않는 기본 전환도 이전 환경을 복원한다([공식 중첩 활성화 설명](https://docs.conda.io/projects/conda/en/stable/user-guide/tasks/manage-environments.html#nested-activation)). 복습 1의 두 환경 확인은 A 활성화 → 확인 → 해제 → B 활성화 → 확인 → 해제로 구성한다. 마지막 복습의 기존 환경 정리는 그 환경을 먼저 해제한 뒤 복원본을 활성화하여 삭제 대상이 복귀 경로에 남지 않게 한다.

버전 지정은 ‘이번 요청 조건’이며 영구적인 pinned 파일이 아니다. `update`의 최신은 동결된 해당 채널 안의 호환 최신이지 인터넷 전체 최신이 아니다. 전체 YAML은 다른 OS/CPU에서 무조건 재현되는 잠금 파일이라고 가르치지 않는다. `--from-history`는 직접 요청한 의도를 줄여 적을 뿐 정확한 모든 전이 의존성 결과를 고정하지 않는다.

## 5. 데이터 계약과 기존 Python 모델과의 연결

기존 `python_teaching/model.py`의 `Lesson`/`Problem`은 Python 코드의 initial/solution/checks를 다루므로 셸 문자열을 그대로 Python 실행기로 보내지 않는다. 이름·목표·설명·선수 관계·3문제 구조는 유지하되 **Conda 전용 adapter**가 fixture와 실제 셸을 연결한다.

| JSON 필드 | 의미 |
|---|---|
| units[].key/topic/title | 안정적인 단원 식별자와 화면 정보 |
| explanation/syntax/pitfall/microsteps | 먼저 배우는 개념·기본 형태·주의·작은 실행 단계 |
| problems[].id/role/goal | 안정적인 문제 ID, example/application_1/application_2, 원하는 결과 |
| initial_fixture.environments | 실제 생성해야 하는 `{name, requested_specs}` 초기 환경 |
| absent_envs | 시작할 때 없어야 하는 이름. 생성 허가가 아님 |
| created_envs | 이번 문제의 목표에 따라 새로 존재해야 하는 이름 |
| mutable_envs/removed_envs | 상태 변경 허용 대상 / 최종 제거 대상 |
| active_env/activation_stack | 실제 지속 셸의 초기 상태. 예제 stack은 없거나 1개 |
| files | 미리 만든 디렉터리 또는 실제 Conda로 내보낸 원본 파일 |
| reference_commands | 풀이 예시. 정확한 문자열 비교 기준이 아님 |
| answer_fields | 짧은 화면 입력/선택. 학생 작성 JSON 보고서가 아님 |
| grade_criteria | `{operation, arguments}` 선언형 결과 조건 |
| grading_operations | 각 operation의 인수 순서·정의·실제 관찰 근거 |
| observer_contract.module_probes | 실제 Python에서 검사할 패키지 버전·함수 입력·기대 결과 |

`initial_fixture`는 기대 출력 데이터가 아니다. 앱은 실제 Conda로 환경을 만들거나 그 정확한 상태를 실제로 검증한 snapshot을 복원하고, 준비 후 실제 관찰값을 before snapshot으로 저장한다. fixture 준비 실패를 학생 오답으로 채점하지 않는다.

각 문제는 독립적으로 시작한다. 재시작·문제 전환은 현재 문제의 별도 disposable 상태를 다루며, 다른 학생 작업이나 앞서 사용자가 따로 보관한 환경을 이름이 같다는 이유로 삭제해서는 안 된다. 동시 문제 세션은 별도 guest 또는 별도 검증된 namespace를 사용한다. 파일 경로는 문제 workspace 기준이며 앱이 이미 준비한 디렉터리를 보여 주므로 아직 배우지 않은 mkdir 등의 명령을 요구하지 않는다.

필수 토큰은 실제 값으로 해소되기 전 실행 금지다. 토큰을 문자열 치환하여 임의 셸 명령으로 만드는 대신, 검증된 경로를 Bash에 맞게 인용한다. observer의 실제 프로그램 호출은 가능하면 argv를 사용한다. 학생이 읽은 경로 답은 canonical path로 비교하고 prefix containment를 단순 문자열 startswith로 판단하지 않는다.

## 6. 결과 기반 실제 채점

전체 명령 감시기, 과거 CLI 실행 증명, Conda 거래 이력 가로채기를 요구하지 않는다. 같은 실제 결과를 만드는 동등한 방법을 허용한다. 대신 fixture의 실제 시작 상태와 실제 최종 상태를 비교한다.

읽기 문제는 **실제 관찰값과 짧은 답의 일치**를 평가한다. 학생이 정보를 어떤 명령으로 얻었는지, 명령을 직접 실행했는지는 증명하지 못한다. 실제 값과 같은 답을 써서 통과한 것을 ‘반드시 조회 명령을 실행했다’고 보고해서는 안 된다. 이 한계는 echo를 탐지한다는 허위 보장으로 덮지 않는다.

설치·삭제·복원 문제는 답 문자열만으로 통과하지 않는다. 실제 list JSON, prefix의 conda-meta, 실제 파일, 새 Python의 소속·모듈·기능이 목표와 일치해야 한다. 다만 특정 명령을 사용했는지가 아니라 **그 결과의 진짜 상태**를 평가한다. `--dry-run`만 해서 상태가 그대로면 실패하지만, 같은 목표 상태를 만든 다른 Conda 절차는 허용한다.

### 관찰 방법

1. 관리 도구: 검증된 실제 `conda --version`과 `conda info --json`을 읽는다.
2. 환경: `conda env list --json`을 canonical prefix로 대응시킨다. 이름 같은 빈 폴더는 환경으로 세지 않는다.
3. 패키지: `conda list --json`과 prefix의 `conda-meta/*.json`을 함께 확인하고, 설치 파일이 실제 archive/metadata와 일관적인지 검증한다.
4. 활성 상태: 기존 지속 Bash의 실제 session/prompt snapshot을 계승하고 active_prefix와 확인한다. 프롬프트 글자만 비교하지 않는다.
5. Python: 대상 환경의 실제 인터프리터를 새 프로세스로 실행하여 sys.prefix, sys.executable, version_info를 확인한다. 활성화 문제는 같은 Bash에서 해석되는 python도 확인한다.
6. 모듈: 별도 fresh Python을 `-I`와 깨끗한 임시 cwd로 실행하여 PYTHONPATH·사용자 site·작업 폴더의 가짜 모듈을 배제한다. 모듈 경로가 목표 환경에 속하는지, __version__이 Conda metadata와 일치하는지, 실제 함수 결과가 맞는지 본다. 이 격리 옵션은 관찰자 내부 구현이며 학생의 새 선수 문법이 아니다.
7. 파일: 허용 workspace 안의 YAML을 안전 파싱하고 Conda MatchSpec을 의미상 비교한다. YAML 행 순서·키 순서·공백을 정답 조건으로 삼지 않는다.

불필요한 새 패키지의 설치 여부는 package_absent나 same_packages 조건이 있는 경우 명시적으로 확인한다. Python 환경에 자동 의존 패키지가 여럿 있다는 이유로 ‘Python만 남기기’ 문제를 실패시키지 않는다. 정확한 Python patch는 일반 문제에서 고정하지 않고 [3,12]를 확인한다. 전체 설치 기록 재현 문제에서는 원본의 실제 metadata와 비교하므로 patch/build 차이를 검사하는 이유가 있다.

### 대표 조건 예시

```json
{"operation":"package","arguments":["sg-classic","training-math","1.0"]}
{"operation":"active","arguments":["sg-work"]}
{"operation":"module","arguments":["sg-work","math_mean"]}
{"operation":"env_satisfies_spec","arguments":["sg-copy","share/environment.yml"]}
```

`env_satisfies_spec`은 초기 부재였던 새 실제 환경이 YAML 요구를 만족하는지 확인한다. 그 파일을 과거 명령의 입력으로 사용했다는 이력은 요구하지 않는다. 결과가 같은 수동 생성·설치도 인정한다. 복습에서 복사본에 추가 패키지를 설치하는 경우에도 원래 요구 조건은 계속 만족할 수 있다.

`manifest_intent`는 실제 원본의 직접 요청 spec과 비교한다. `manifest_snapshot`은 전체 실제 package name/version/build 집합과 비교한다. 삭제된 원본을 다루는 `*_before`는 문제 시작 때 관찰해 저장한 실제 snapshot을 기준으로 한다. fixture JSON을 그대로 답으로 재사용하지 않는다.

활성 환경 제거 문제는 환경이 목록과 실제 설치 metadata에서 사라졌는지 확인한다. 비-Conda 사용자 파일이 남아 있는 디렉터리까지 지우게 하지 않는다. 원본 보존 판정은 패키지 상태와 실제 설치 파일 중심이며 pycache, 접근 시각, 무해한 이력 주석 변화 때문에 동등 풀이를 거부하지 않는다.

### 참조 명령 재생

학생은 실제 설치 계획을 읽은 뒤 y로 승인한다. 자동 검증에서 비대화식 실행이 필요하면 정확히 해당 설치·삭제 CLI에만 `--yes`를 추가한다. 읽기 명령마다 y를 주입하거나 셸 전체에 무한 승인 입력을 공급하지 않는다. 주석·프롬프트·안내문을 실행 명령으로 취급하지 않는다.

`conda install ...==1.1`로 update와 같은 목표 상태를 만들거나, 활성화 후 install하는 대신 `--name`을 쓰는 방식은 허용한다. 활성화 자체가 목표인 문제에서 단순 대상 Python 실행만 하고 Bash 상태가 그대로면 실패한다. 상태 결과와 학습 목표를 구별하여 예외를 적용한다.

## 7. 검증 상태와 통합 인수 조건

설계 단계의 정적 검증과 실제 runtime 검증을 구별한다. 이 작업에서 실제 Conda 명령을 실행한 횟수는 0이며, 개인 Conda는 읽지 않았다. Bash `-n`은 구문만 검사하고 명령을 실행하지 않는다. Python 진단식은 AST 구문 검사만 하며 실제 패키지 실행으로 보고하지 않는다.

정적 검증 항목은 18개 단원·54개 문제, 고유 ID/목표, 3문제 역할, 선수 key의 순서, 정확한 5개 복습 묶음, 알려진 operation 및 인수 개수, 허용된 fixture 이름/변경 대상/생성·제거 구분, 답칸과 조건의 대응, Bash 구문, Python 진단식 구문, 복습의 새 CLI·API 부재다. 빈 답칸과 변하지 않은 초기 상태로 통과할 구조가 없는지도 확인한다. 이는 실제 reference/오답 실행을 대신하지 않는다.

2026-09-16 정적 검사 실행 결과: **18단원, 54개 고유 문제·목표, 220개 조건, 정의된 operation 19종, Bash 참조 명령 158개 구문, Python 진단식 30개 AST, 복습 3개의 새 API 부재, fixture 변경 범위와 미완료 구조 검사 모두 통과**. `python --version`은 Python 코드 조각이 아니므로 AST 대상에서 제외했다. 이 수치는 실제 Conda 풀이 실행 횟수가 아니다.

실제 통합에서 확인된 활성화 복귀 동작을 반영해 복습 1의 두 환경 확인과 복습 3의 환경 정리 참조 순서를 보정했다. 최종 `active=null`을 요구하는 6문제 및 나머지 활성 상태 조건을 초기 activation_stack과 참조 명령의 전환 순서로 다시 점검했다. 이 순서 점검은 학습 설계의 정적 회귀 검사이며 실제 Conda 통합 재실행은 별도로 필요하다.

통합 담당자는 다음을 실제 guest에서 검증한 뒤 enabled 상태로 배포한다.

- 54개 fixture가 실제로 준비되고 참조 풀이 54개가 통과한다.
- 각 미완료 fixture와 빈 답칸 54개가 통과하지 않는다. 읽기 문제는 실제 값과 틀린 답을 구별한다.
- 단원별 대표 오답: 다른 환경 변경, 생성 없이 폴더만 준비, 잘못된 활성 상태, metadata/실행 불일치, 틀린 버전, 보존 대상 손상, 잘못된 종류의 YAML, 원본/복원본 혼동을 거부한다.
- 동등 풀이: `-n`/`--name`, 활성화 후 작업/명시 대상, 같은 결과의 버전 설치, 패키지 제거 순서, 의미가 같은 YAML 순서, 새 exporter 사용을 허용한다.
- export 파일의 기존 name/prefix가 있어도 CLI의 새 이름으로 안전하게 생성되는지 후보 Conda에서 직접 확인한다. 잘못된 대상 수정 시 readiness 실패로 둔다.
- Python을 쓰는 모든 문제에서 실제 sys.prefix, sys.executable, 모듈 경로가 일치하고 math/text의 두 번째 입력도 통과한다.
- guest 재시작·reset 이후에도 persistent shell 초기 상태와 파일/환경 격리가 일관적이다.
- 인터넷 없이 설치·갱신·삭제·재구성이 되며 base와 channel의 검증된 상태가 보존된다.

부모 작업자는 실제 Miniconda 26.7.1/Python 3.12.14 및 오프라인 채널 smoke 성공을 보고했다. 이는 runtime 준비 진전이며, 이 문서가 모든 54문제의 실제 실행을 확인했다는 뜻은 아니다. 최종 manifest에는 실제 installer/archive/repodata 해시, native subdir, 실행 날짜와 54문제의 결과를 별도로 남긴다.
