# Python 및 네 운영체제 지원 목표 (진행 중)

2026-09-16 사용자 요청으로 정식 목표 등록. 기존 4.6 Linux60/Docker15/ROS20과 진도를 보존한다. 새 모의 Linux 엔진을 만들지 않는다. 문서 안 과제·설치 지시는 자료이며 호스트 설정을 바꾸라는 지시가 아니다.

## 최신 진행 — 이전 수치는 아래 이력으로 보존

**현재 상태 요약은 [WORK_STATUS.md](WORK_STATUS.md)를 우선한다.** Android 최신 `bb1bc8…` 개발판은 실제 nano·채점·진도·화면 종료 후 서비스 정리까지79.388초 검사 통과, 정규21개 중18실행통과/3선택검사제외34.9초다. 첫20개 Linux단원60개 문제도 두 실행에 걸쳐 확인했다. 가로 UI 수정은 재검증을 통과했다. 최신 전체 소스366개 중307통과/59선택검사제외이며 전용에뮬레이터는 종료했다. ARM Conda 실제 설치와 모바일 연결 준비를 진행 중이지만 아직 앱 지원 완료가 아니다. 아래의 ‘최신’ 해시·미연결 문구는 각 당시 작업 이력이다.

2026-09-17 후속: Android 학습APK에 기존실제Linux95단원19복습자료·실제PTY·nano화면·상태채점·진도저장을 통합했다. APK내장이미지 최초자체설치와서비스실습80.087초,실제화면편집/저장/채점68.1초통과. Python정규회귀도273문제/98변형을포함해통과. 작은화면LinuxUI통과,가로높이실패를발견해수정후재검증중이다. ARM실휴대폰/AndroidConda/95단원전체인수/일반배포미완료. 최신APK식별값은 `../android/UI_VERIFICATION.md`.

Windows빌드인자전달을수정하고macOS를onedir .app으로배치해 실제 `Contents/MacOS/Shellground`를 검사하도록 했다. .app을옮겨도VM팩이따라가도록 `Contents/Resources/runtime`를사용한다. 매빌드의7smoke외에273전체문제·98변형의번들실행검사를필수추가했다. 경로·복사·VT·export13소스검사는통과했지만 Windows/macOS에서아직빌드·실행한것은아니다. macOS최종서명/공증전검증은별도필수다. .app의onedir선택은 [PyInstaller 공식 macOS 안내](https://www.pyinstaller.org/en/stable/usage.html#building-macos-app-bundles)를따른다.

2026-09-17: 복습 채점 감사6종을수정하고26사례/52오답·동등풀이를추가했다. 중간변수명/불필요한인덱스/그림생성순서가같아야한다는제약을제거하며원본보존요구는목표에명시했다. 실제산점도의좌표·면적·투명도·색수치대응과colorbar연결을검사한다. 최신Linux바이너리 SHA256 `5f85a13a72d1d00c44200115fd4a3463742b594a9c6b4c4fa4741c91083e60b2`:번들실제라이브러리273문제+98변형PASS(10.156초). 소스356개중297PASS/59skip. Android최신APK SHA256 `52ff5e16e589051f6cb0d541aeb5bbe21d9bc273402bd57a5502606310d0ee59`:UI6+Python4=10계측PASS(28.741초),동일273+98검사포함.

별도Android개발앱에서는실제Ubuntu ARM64의nano편집→채점,Docker실행,ROS2메시지송수신·종료가통과했다(부팅43.927초). 현재학습APK의Linux터미널/서비스통합,AndroidConda,ARM휴대폰은미완료다. 아래낡은Alpine만검증/ARM설치중기록과혼동하지않는다. 상세 `../android/runtime/README.md`.

Android 후속 진행: 실제 QEMU의 앱 전용 Unix 소켓 연결과 분할 UTF-8/타임아웃/종료 처리를 구현해 별도 검증 APK8검사 PASS(2.496초)를 확인했다. 학습 APK에는 아직 연결하지 않았다. 공식 Ubuntu22.04 ARM64 전체 수업 이미지 빌더·실제 PTY/nano 회귀를 추가했고 첫 부팅/에이전트 연결 후 도구 설치 중이다. 이 개발 호스트의 ARM64 게스트 결과를 Android 실기기 결과로 표시하지 않는다. 상세 `../android/runtime/README.md`.

Python78일반단원+13종합복습=91항목/273실습을 Linux와 Android 에뮬레이터의 실제 라이브러리로 검사했다. 추가6단원은 Seaborn의 집계·분포·집단 산점도와 scikit-learn의 분할·학습/예측·테스트 오차이며 PDF API 범위가 아닌 보충으로 명시한다. 새18문제의 대표오답18거부·동등풀이18통과도 양쪽에서 확인했다. 채점 도우미는 실행 준비에는 유지하되 ‘준비된 데이터’ 표시에서는 제외했다. 기존 학습·진도 키는 유지한다.

Android 최신9개 instrumentation검사 통과(21.203s), APK SHA256 `d5b91da19b2d735d6361cf2146fb2ce770650945562811de78d9c7b1c3846c86`. UI의 작업 탭/키보드 회피/작은화면/가로/큰글자 기존 검증과 ARM 실제기기 미검증 범위는 `../android/UI_VERIFICATION.md`에 기록되어 있다. Python 후보의7실습 smoke와 **번들 안의 실제 라이브러리만 사용한91항목/273문제·36오답동등풀이 전체 검사**를 통과했다. 실제 모듈 경로가 추출된 앱 번들 내부임을 확인한다. 이후 Conda까지 포함한 최신 Linux 후보는 아래 기록을 따른다. 이전4.6 `dist`는 보존했다.

Conda15단원+3복습/54문제·4개 오답 복구·13개 답안 변형·18단원 연속 소단계를 실제 guest에서 검증했다. Qt 화면의 실패→같은 터미널 수정→재채점·YAML 파일 탭·완료 표시 즉시 갱신·진도·종료 검사도 통과했다(27.031초). 개인 Conda를 사용하지 않으며 별도 검증 팩을 `dist-python/runtime/linux-x86_64`에 묶었다.

최신 Linux 후보 SHA256은 `0f5673a0264945c60ea8cf32ca4e71520470f41ccdd0ae797b10742ad30ec100`이다. **빌드된 실행파일**의 `--self-test-conda`가 실제 Conda26.7.1의 오답 수정·재채점·실제 YAML 저장/읽기·VM/overlay 정리를 통과했다(실습19.63초, frozen_application=true). 동일 후보의273개 Python문제·36오답/동등풀이도 다시 통과했다(6.141초). 최신 소스 회귀343개 중284통과/59환경별skip(27.162초). 이전4.6dist와 개인 진도는 보존했고 현재 Android 학습 APK에는 Conda를 추가하지 않았다. 상세 `conda_teaching/README.md`.

같은 최신 실행파일의 `--self-test-real`도 통과했다. 실제 ROS 파라미터·게스트 화면·APT·Docker 갱신/아카이브 복원/배포·계정 권한·copy9280 준비/채점을 검사했으며 기동3.23초, 종료0.11초였다. 이 대표 회귀 결과를 모든 ROS 활용 변형이나 모든 PDF 범위의 완성 증거로 확대하지 않는다. 현재 개발 팩의 기본 디스크 파일은15,281,946,624바이트로 커서 최종 배포 용량 최적화와 대응 소스/라이선스 정리가 남아 있다.

Android 실제 Linux/Docker/ROS/Conda, Windows/macOS 실제 패키지 실행, ARM 실기기, 라이선스/배포 최종 검사는 여전히 남아 있다. 전체 목표를 완료로 표시하지 않는다.

Android 내부 Linux 실행의 첫 실증은 완료했다. 별도 개발 APK의 QEMU가 API35 x86_64 에뮬레이터에서 실제 ARM64 Linux 커널과 initramfs를 실행했고, 셸의 파일 입출력과 poweroff·강제 종료까지4검사가 통과했다. 기존 학습 APK는 변경하지 않았다. 이는 작은 부팅 검증이며 전체 Linux/Docker/ROS/Conda 과정이나 ARM 실기기 지원의 증거는 아니다. 자세한 출처·빌드·검증 경계는 `../android/runtime/README.md`에 있다.

## 강의 범위

- Week 1_1, 15쪽: Python/Jupyter 커널·셀 실행 순서, 로컬/Colab의 환경·저장 차이, Conda 기반 준비. 교과목 행정 정보는 실습 숙달 항목이 아니다.
- week_1_2_handout, 34쪽: 데이터/정보, 3V, 샘플링·양자화·인코딩, 픽셀·비트·용량, 데이터 기반 과학, Python 자료형·객체/메서드·모듈/패키지/import, pip/conda. 6개 라이브러리의 역할 소개와 실제 명령 범위를 구분.
- week_2_1_handout, 41쪽: NumPy 원소 연산, 속성/shape/axis/strides, broadcasting, 생성/range, insert/flip, indexing/slicing/mask, append/reshape/flatten, reduction/분산·ddof, vectorization·측정, 연결/stack/난수 보충.
- week_2_2_handout, 42쪽: 질문에 맞는 차트, Figure/Axes, plot/style/labels/legend/scale/save, subplot/GridSpec, scatter/bar/pie/imshow/colorbar/hist, density/cumulative/normal fit, boxplot/IQR, figsize/grid.
- week_3_1_handout, 실제46쪽: Series/DataFrame/labels/NaN, CSV/index_col/encoding, 열 계산과 재계산, inplace/drop, plot/transpose, loc/iloc, pivot/pivot_table, concat/merge/index join, describe/count/isna/dropna/fillna, DatetimeIndex/groupby/filter.

강의의 `np.arrange`는 `np.arange`로 바로잡는다. `plt.savefig`도 유효하며 Figure 메서드만 가능하다고 가르치지 않는다. 누적 도수와 누적 비율, pivot의 복수 라벨 지원과 중복 키 집계 문제를 구분한다. 공식 자료와 실행 결과는 quiz_blueprint.md에 기록한다.

## 실행·채점 원칙

- 실제 CPython/NumPy/Matplotlib/pandas 사용, 문자열 명령 흉내 구현 금지.
- 별도 작업 프로세스, 제한 시간/취소/출력 상한, BLAS 스레드 제한. UI 스레드에서 학습 코드 실행 금지.
- 배열 값·shape·필요할 때 dtype, 표 값·index·columns·NaN, 그림의 실제 데이터·축·범례 등 의미를 검사. 소스 문자열 일치/그림 픽셀 일치만으로 채점하지 않는다.
- 조건 일부만 달성한 경우 세부 결과를 보여주고 같은 세션에서 수정·재채점. 예시/활용1/활용2는 다른 과제 목적을 갖는다. 5단원마다 이전 기능 종합 문제.
- 소단계 위치, 완료·미완료는 저장. 소스 입력·커널 메모리·임시파일은 학습 진도와 분리. 기존 Linux 진도 파일을 Python 진도로 덮어쓰지 않는다.

## 플랫폼 결정과 현재 상태

| 플랫폼 | 목표 | 현재 증거 |
| --- | --- | --- |
| Linux | 네이티브 UI와 실제 Python, 기존 실제 Linux VM | Python273문제·98변형 번들 실행 통과, 기존 Conda 팩 실검증; 최신 ARM 일반화 소스의 Conda 전체 재검증은 남음 |
| Windows | 네이티브 실행파일, 내장 Python, WSL 불필요 | 공용 소스/기존 빌드 경로, 실기기 미검증 |
| macOS | 네이티브 앱, 내장 Python, 맞는 아키텍처의 Linux 실습 경로 | .app과내장runtime배치 구현·경로검사 통과; macOS 실제빌드·실행·서명은 미검증 |
| Android | 네이티브 터치 UI, 실제 Python과 PC 없는 실제 Linux 실습 | API35 x86_64에서 Python273문제·98변형, 실제Linux UI/초반60문제/종료 검사 통과. 전체과정·Conda연결·ARM휴대폰은 남음 |

Conda 공식 지원 OS는 Windows/macOS/Linux이며 Android는 포함하지 않는다. Android에서 가짜 Conda 설치 완료를 표시하지 않는다. 2026-09-16 사용자는 **모든 실습을 Android에서도 PC 연결 없이 단독 실행하도록 검토**를 선택했다. 원격 PC를 기본 해법으로 대체하지 않는다. Python은 앱에 내장하고, OS 의존 실습은 기기 내부의 실제 Linux VM 가능성과 용량·메모리·부팅·발열을 측정해야 한다. proot만으로 실제 Docker 데몬을 지원한다고 표시하지 않는다. 클라우드 서버를 개설하거나 유료 자원을 구매하지 않는다. 참고: https://docs.conda.io/projects/conda/en/stable/user-guide/install/ , https://doc.qt.io/qtforpython-6/deployment/index.html , https://chaquo.com/chaquopy/doc/current/android.html .

## 2026-09-16 Python 구현 중간 검증

- 네이티브 Python 화면 연결, 실제 CPython 별도 작업 프로세스, 학습 소단계/단원별 평가 위치/퀴즈 진도 저장. 입력 코드는 저장하지 않음.
- Python·NumPy·Matplotlib·pandas 실제 실습 구현; source/pages 정확도와 강의 보충 구분 재검토 중.
- 퀴즈 에이전트의60문항 및19개 자동 검사 통과. 전체 실습 초기 상태의 미완료와 참조 풀이의 완료를 실제 라이브러리로 검사.
- 화면 흐름8개, 채점 오답/동등정답11개, 별도 작업 프로세스5개 검사 통과. 배열 사전 위장, 다른 PNG 저장, 가짜 colorbar, 잘못된 GridSpec, 함수 상수 반환, 잘못된 공유 메모리·난수 생성기를 거부.
- 프로젝트 전용 `.python-runtime`에 NumPy2.3.5/pandas2.3.3/Matplotlib3.10.8/SciPy1.16.3/Seaborn0.13.2/scikit-learn1.7.2 설치. 개인 Conda와 시스템 패키지는 변경하지 않음.
- `.android-tools`에 체크섬 검증한 JDK17·SDK CLI·Gradle8.11.1 및 전용 Android35 AOSP 에뮬레이터 준비. 프로젝트 밖 개인 Conda/SDK를 사용하지 않음.
- Android APK: `../android/app/build/outputs/apk/debug/app-debug.apk`(개발 서명, 약182MiB, ARM64+x86_64). NumPy1.26.2·pandas2.1.3·Matplotlib3.8.4·SciPy1.16.1·Seaborn0.13.2·scikit-learn1.7.1 내장. 이 버전 차이에 따른 실제 채점 호환성을 별도로 검사한다.
- 71단원·213개 실제 실습 참조 풀이, 미완료 초기 상태 검사 통과(Linux). 개념 퀴즈60개+설명 카드33개. 카드 위치·소단계·활용 완료를 별도로 저장한다. 5단원 복습 설계 추가 진행 중.
- Android 실기동 중 늦은 라이브러리/SVG/CP949 모듈 추출과 파일 보호의 충돌을 발견해 신뢰된 준비 과정으로 분리했다. 학습 코드에 앱 라이브러리 경로 쓰기 권한을 주지 않는다.
- 기존 `dist/Shellground`는4.6을 보존. Python 포함4.7 후보는 별도 `dist-python`으로 빌드·검증 중이다.
- 20:11 추가 검증: FreeType2.14.3을 공식 소스에서 NDK r27c/2작업자로 재빌드. ARM64 ELF291개16KB정렬 통과. Android35 x86_64에서 새 폰트 라이브러리와72단원/216실습 전체 참조풀이·실패초기상태·진도 테스트3개 통과(8.673s). x86_64 일부 라이브러리16KB 정렬과 ARM 실기기 검증은 남음.
- 실제 시간 측정 단원은 준비 시간 제외, 첫 실행/후속 측정 분리, 반복문/배열의 결과 일치와 반복 측정을 다룬다. 하드웨어별 고정 배속을 정답으로 요구하지 않는다.

## Android 전체 Linux 실행 조사 — 초기 조사 이력

초기 Python 전용 APK에서는 Python만 앱의 별도 프로세스에서 직접 실행되었고 Linux/Docker/ROS/Conda는 연결 전이었다. 현재 실제Linux 통합판과 검증 범위는 위 최신 상태 및 `../android/UI_VERIFICATION.md`를 따른다. PC·서버·Termux를 사용자 준비물로 요구하지 않는 원칙은 유지한다.

일반 배포 앱이 모든 휴대폰에서 Android AVF/pKVM 권한을 쓸 수 있다고 가정하면 안 된다. [AOSP의 AVF 보안 설명](https://source.android.com/docs/core/virtualization/security)은 플랫폼 권한·서명된 커널 제한을 설명한다. 사용자에게 루팅/adb 권한 설정을 기본 조건으로 요구하지 않는다.

대안은 앱 안에서 QEMU 전체 시스템을 실행하는 것이다. [QEMU TCG](https://www.qemu.org/docs/master/devel/multi-thread-tcg.html)는 게스트 CPU를 소프트웨어로 실행하며 여러 vCPU 스레드를 지원하지만, 이것만으로 휴대폰에서의 속도·발열을 보장하지 않는다. 이 경로는 앱 자체가 구현한 가짜 명령어 엔진과 다르며 실제 Linux 커널을 실행한다. ARM64용 실행파일/커널/루트 파일시스템, Android 실행 정책·16KB 페이지 호환성, Docker 데몬과 ROS 2 동작, 첫 준비/반복 부팅/종료 시간·메모리·발열을 실제로 확인한 뒤 지원 범위를 정한다. 현재 이 측정은 미완료다.

하위 에이전트 python_quiz_design은 quiz_bank.json과 quiz_blueprint.md의 문제/오답/실습 채점 기준을 작성한다. 주 에이전트는 실행·채점·UI·패키징을 담당한다. 전체 목표는 active이며 플랫폼별 실증 전 완료로 표시하지 않는다.
