# Android 내부 Linux 실행기

## 4.7.4 포팅 현황 (2026-09-18)

학습 APK에 실제 ARM64 Ubuntu, Docker, ROS 2, Miniconda·pip, Jupyter 커널을 연결했다. `export_port_assets.py`는 데스크톱 문제/채점 payload를 유지하고 Android 조작 문구만 바꾼다. `finish_port_guest.py`와 `guest_port_setup.py`가 기존 ARM 이미지에 필요한 오프라인 패키지를 추가하며 과거 전체 수업 검사를 반복하지 않는다.

- Linux90·Docker25·ROS 2 23단원,27복습,441등록 사례.
- Conda·pip20학습/복습,60문제 및 동의 후 진행하는 별도 설치 실습.
- Jupyter6학습/복습,18문제. 실제 커널 선택, 실행, 저장, 미완료 후 같은 상태 재채점.
- Python95학습/복습,285문제. 이번 변경분은4개 pandas 단원/12문제.

새 실행기/자료의 확인 결과는 최종 배포 옆 `releases/android-build.json`에 기록한다. 실제 ARM 휴대폰과 전 과정 Android 전수 실행은 별도 미검증 사항이다. 설치와 종료는 앱 내부에서 처리하고 PC 실습 서버를 요구하지 않는다. 배포 실행기의 디버그 섹션만 제거하며 원본 ELF 구조·시스템 의존성·16KB 정렬은 확인한다.

배포 이후 임시 검증 기기, 구형 APK, 이미지 중복본, 빌드 중간물과 SDK 캐시는 제거한다. 현재 소스·빌드 스크립트·서명 키·작은 검증 보고서·배포에 필요한 라이선스/대응 소스는 캐시와 구별해 보존한다.

## 이전 개발 이력

아래 날짜가 붙은 수치·‘아직 미연결’ 문구는 당시 기록이며 현재 기능표가 아니다. 현재 연결 상태는 위 요약과 앱의 메뉴를 기준으로 한다.

이 폴더는 실제 QEMU를 Android용으로 교차 빌드하고 앱 전용 Linux를 준비·검증하는 도구다. 기존 Python 과정에 실제 Linux 학습 서비스를 추가했다. 명령 출력을 흉내 내는 엔진으로 대체하지 않는다. ARM 실휴대폰과 전체 수업 인수는 아직 미완료다.

## ARM Conda 준비 도구 (아직 학습 APK에 미연결)

`build_conda_guest.py --build`는 검증된 기존 Linux 팩을 변경하지 않고 별도 `conda-arm64/provisioning.qcow2`에 공식 Miniconda ARM64를 설치한다. 공식 설치파일 SHA, 실제 guest 아키텍처, 실제 Conda channel의 `linux-aarch64`를 확인한다. 외부 네트워크와 호스트 폴더 공유 없이2vCPU/2GiB에서 실행한다. 호스트용 `systemd-run --user --scope -p CPUQuota=100% -- nice -n15 …`로 이 작업에만 CPU 상한을 적용할 수 있다.

설치 후 `--course-test --learning-test`로 동일54문제·오답복구4개·답안변형13개·18소단계를 실제 guest에서 검사한다. 선택 검사에는 `--units`를 쓸 수 있으나 일부 통과는 전체 통과가 아니다. 보고서는 x86과 다른 `.native-runtime/conda-arm64`에 저장한다. VM이 종료된 뒤 `export_conda_guest.py`를 실행하면 **현재 소스·전체 결과·ARM 실행 증거**가 모두 있을 때에만 별도 팩을 내보낸다. 기존 팩 덮어쓰기와 사용 중인 디스크의 잠금 우회는 금지한다. 실패한 작업 디스크와 임시 산출물은 진단용으로 보존한다.

실패한 설치는 `--diagnose`로 기존 작업 이미지를 부팅해 로그·두 검사용 환경의 패키지/이력·내보낸 YAML만 읽을 수 있다. 삭제·재설치·복구 명령은 실행하지 않는다. `diagnostic.json`은 검증 성공 보고서가 아니며 내보내기 조건을 충족시키지 않는다. 이후 설치 실패에서는 VM 종료 전에 이 읽기 전용 진단을 자동으로 시도한다.

후속 진단 보완: 실제 명령 출력은 guest의 새로운 `conda-smoke-*/output.log`에 즉시 기록하며 단계 이름·소요 시간·종료 상태도 보존한다. x86 90초/ARM600초 제한은 유지한다. 시간 초과·취소 시 새로 만든 프로세스 그룹만 유한 시간 내 정리한다. 이 방식의 실제 x86 Conda 생성→활성화→설치→갱신→내보내기→재생성→삭제는24.349초에 통과했다. ARM 전체 통과의 대체 증거는 아니다.

과거 실패로 남은 두 환경을 보존하고 다시 검사하려면 개발자가 명시적으로 `--archive-smoke-fixtures --build`를 선택할 수 있다. 실패 로그와 **두 환경 모두의 원래 생성 이력**을 먼저 검사하고, 정확히 `sg-proof`·`sg-copy`만 guest의 별도 보관 폴더로 옮긴다. 링크·이력 불일치·다른 실패는 거부하며 사용자 환경을 삭제하지 않는다. 호스트 `smoke-archives.json`과 guest `archive.json`에 위치가 남는다. 보관 자료는 개발 증거이며 최종 배포 이미지 용량 정리 전에 별도 보존·검토가 필요하다. 일반 앱 시작이나 단순 `--build`는 이 복구를 자동 실행하지 않는다.

공식 ARM Miniconda 설치는 완료했지만 후속 `runtime_smoke.sh`가600초 제한을 넘겨 실패했다. CPU 제한한 개발 호스트 TCG에서의 결과이며 실제 휴대폰 성능을 뜻하지 않는다. 설치 작업 이미지는 보존했고 전체검증/내보내기 성공으로 표시하지 않는다. **데이터 변환이나 내보내기 코드만으로 Android Conda가 사용 가능하다고 표시하지 않는다.** 실제 앱 답안 입력·파일 확인·채점 연결과 ARM휴대폰 검증이 남아 있다.

### 모바일 Conda 자료 계약 v2

`desktop/conda_teaching/mobile_course.py`는15단원·3복습·54문제·54소단계를 전달한다. 빠졌던 `bootstrap`(배포판/도구, host/guest, 플랫폼별 설치 방식, 기존 Python과 Conda의 구별, 실제 준비 조건, 선택 설치 실습1개)과 공식 출처도 보존한다. 선택 설치 정의가 있다는 이유로 지원 완료로 표시하지 않도록 `runtime_integration.practice_enabled`와 `optional_install_enabled`는 현재 `false`다.

- 배우기 문장의 PC F4/F2는 Android의 ‘실습 시작’·‘터미널’·‘문제 다시 시작’으로 바꾸되 실제 명령과 원본 데스크톱 자료는 바꾸지 않는다.
- 화면용 `example_commands`는 예시18문제에만 있다. 활용36문제는 빈 배열이며 정답 풀이를 자동 노출하지 않는다.
- `provided_diagnostics`는 퀴즈 설계 감사로 확인한13종의 정확한 Python 진단식만 해당 문제에 제공한다(전체31회, 환경별 반복 보존). Conda 설치·활성화·조회 정답은 섞지 않는다. 새 표현식은 검토 없이 접두사만 보고 허용하지 않는다.
- `mission`은 기존 실제 채점기의 비공개 UI용 payload다. 앱 내부 JSON을 비밀 저장소로 취급한다는 뜻은 아니며, 문제 화면은 `mission` 전체나 답안 `expected` 값을 렌더링하지 않아야 한다. 화면용 답칸에는 key·label·입력 형식만 있다.
- 자료 보존·UI 문구·정답 분리·복합 명령 거부·변경 격리9검사 통과. 이 검사는 학습 APK의 실제 Conda 실행 증거가 아니다.

Android 연결 구현(검증 중): `export_conda_course.py`가 데스크톱의 기존 실제 guest 채점기·셸 설정·파일 읽기 코드를 그대로 APK 자산에 넣는다. `CondaGuest`는 이 코드를 실제 VM에 적용하고 `prepare`가 돌려준 실행 장소에서 PTY를 열며, 같은 세션의 답안과 상태로 채점한다. 참/거짓 답의 빈칸은 `false`로 바꾸지 않고, 채점 실패 결과를 그대로 반환한다. 일반 Linux 팩은 Conda 지원 팩으로 간주하지 않는다.

`LinuxActivity`의 내부 `course=conda` 경로에 네이티브 답칸·제공 진단식·학습 소단계·파일 보기를 연결했다. Conda 진도는 기존 Linux 진도와 다른 저장소를 사용한다. 기본 메뉴에 지원 완료 항목을 추가하지 않았으며, 현재 실제 Conda 팩 연결 및 선택 설치 실습은 준비 중이다. 새 프로토콜5개·화면4개 검사는 실제 Android 위젯/전송 계약을 검사하는 것이며 ARM Conda 실행을 대신하지 않는다. 현재 빌드와 실제 계측을 완료한 뒤 APK별 결과를 기록해야 한다.

## 2026-09-17 현재: 학습 APK 통합과 최초 자체 설치

`LinuxService`는 별도 프로세스에서 실제 guest와 최대4개의 PTY를 관리한다. `LinuxActivity`의 네이티브 문제·터미널·채점 탭, 소단계·완료 자동 저장, 랜덤복귀, 기록복사와 연결했다. 기존 pyte가 VT출력을 해석하고 Canvas가 표시하며, 셸/nano/Docker/ROS 동작은 실제 Ubuntu가 수행한다. 기존 실제 과정95단원+19복습은 `desktop/export_real_course.py`로 같은 문제·설명·채점 payload를 사용한다.

- 실제 학습 서비스 검사80.043초 PASS: 초기 미완료→nano수정/저장→동일세션실제채점,2PTY전환·기록복사,VM/reader종료. `.native-runtime/learner-service-validation.json`.
- 실제 APK 최초 이미지 설치 검사80.087초 PASS: PC에서 이미지를 따로 넣지 않고 앱이 APK자산에서 설치·SHA검증 후 같은 실습을 수행. `.native-runtime/learner-bundled-validation.json`. 당시APK해시`c93eefdbf752d05ddd315237a66f7f0933b547492f86f374e11211de84d2eadc`.
- 학습 화면의 실제 nano입력→저장→채점→완료진도검사68.1초 PASS. 최신 UI 빌드 해시·가로/작은화면 재검증은 `../UI_VERIFICATION.md` 참조.

`-PlinuxRuntime=true -PbundleLinuxPack=true` 빌드가 실제 실행기와 이미지를 포함한다. 약2.03GB 개발APK이며 최초설치에 약2GB 추가 공간, 업데이트에는 설치기의 임시공간도 필요하다. 큰 단일asset을 Javaheap에 올리다 실패한 뒤52개32MiB이하 조각으로 나눴다. `stage_app_pack.py`는 원본체크섬을 검사하고 앱은1MiB버퍼로 자체설치한다. 사용자는Termux/root/WSL/PC실습서버를 준비하지 않는다. 설치중단은 다음 시작에 재시도하며 원본이미지는변경하지않는다.

현재API35 x86_64 전용에뮬레이터에서 검증했다. 실제 ARM폰,AndroidConda,95단원전체인수,라이선스대응소스/일반배포는 남았다. 아래 '학습APK미연결' 문구와작은Alpine검사는 이전단계의이력이다.

## 현재 준비물과 경계

### 2026-09-17: 실제 Ubuntu·nano·Docker·ROS 종단 검사 통과

아래 실패 이력 이후 공식 ROS setup을 `bash -ec`로 불러오도록 검사 명령을 수정했다. 상류 setup의 선택 변수를 `-u`로 거부하던 문제였으며 실제 명령 오류를 무시하지 않는다. 개발 호스트에서 실제 ARM64 Ubuntu22.04의 PTY/nano 저장·종료, 파일 보존, Docker ARM 컨테이너, ROS 준비 검사가 통과했다. 빌더/아키텍처 단위 검사8개도 통과했다.

이어 **Android API35 x86_64 에뮬레이터의 별도 검증 앱**에서 실제 Ubuntu ARM64를 실행했다. 기존 실제 과정의 편집 문제 초기 미완료 → nano Ctrl+K/O/X → 같은 PTY 상태 채점 통과, Ctrl+C 셸 복귀, 실제 Docker 컨테이너, ROS2 발행자/구독자 메시지 송수신, VM/reader 종료를 모두 확인했다. `full-guest-validation.json` 및 `full-guest-instrumentation.log`가 증거다. 부팅43.927초, 전체 계측106.198초이며 ARM 휴대폰 성능을 의미하지 않는다. 기존 작은 부팅/프로토콜8개도 재실행해 통과했다(2.4초).

`GuestMachine`은 앱 내부 Unix 소켓, SHA256으로 검증한 이미지, 임시 snapshot overlay, 네트워크·호스트 공유 폴더 없는2vCPU/2GiB VM을 관리한다. 정상 poweroff 뒤 유한 대기·강제 정리 경로를 제공한다. `export_guest.py`는 성공한 개발 검증 팩을 독립 압축 이미지로 내보낸다. 현재 base.qcow2는1,736,215,040바이트이고 커널/initrd는 별도다. 기존 개발 원본 디스크는 보존한다.

재실행은 `python3 runtime/run_full_guest.py --serial emulator-5558`이며 개인 기기가 아닌 명시된 전용 에뮬레이터만 사용한다. 검증 APK SHA256은 `af92d87786239a2f3c5b15745e42a764597e730cf469aa41ab52ad3f466a385c`, 계측 APK는 `307aac2b9ca3b3aec6e55f172429de5d50e21b1f7cf35bcac25b67fc77a0f1bb`다.

**현재 학습 APK의 서비스·터미널 화면에는 아직 연결되지 않았다.** Android Conda, 전체95단원 인수검사, 실제 ARM 휴대폰·발열·배터리, 대응 소스/라이선스·일반 배포도 남아 있다. 아래 내용은 이전 단계의 이력이다.

### 최신 추가 검증: 앱 내부 제어 채널

`src/main/java/org/shellground/runtime/GuestChannel.java`는 기존 실제 게스트 에이전트의 JSON/virtio 프로토콜을 Android의 앱 전용 Unix 소켓으로 연결한다. UTF-8이 여러 읽기로 나뉘어도 보존하고, 터미널 이벤트와 요청 응답을 구분하며, 응답 크기·대기 시간을 제한한다. 같은 앱 UID의 연결만 허용하고 종료 시 대기 중 요청을 깨운다. Android에서 명령을 해석하거나 출력 결과를 흉내 내지 않는다. 아직 학습 앱 서비스·터미널 화면에 연결한 상태는 아니다.

최신 API35 x86_64 개발 APK 검사 **8개 PASS / 2.878초**. 기존 실제 부팅·종료4개에 실제 QEMU의 Unix 소켓 연결/정상 종료1개와 프로토콜3개를 추가했다. 실제 QEMU 소켓 검사는 INTERNET 권한이 없는 앱에서 수행했다. 프로토콜3개는 테스트 상대편과 메시지 분할·boolean 응답·타임아웃·종료를 검사하며 실제 Linux 실행 검사와 혼동하지 않는다. 새 APK SHA256은 `c632087d1cf3d59bb21367b0754a9192ddeee58721f79cd547d15730ebe4b691`, 계측 APK는 `0243ba3b1478908b12b89e2826b18e3aff09bb63127adbcce6c47fc8f2447caf`다. 검사 후 자식 프로세스가 남지 않았고 전용 에뮬레이터도 종료했다. 아래4개 검사/이전 APK 해시는 이전 이력이다.

### 전체 ARM64 수업 이미지 빌더

`guest-sources.json`은 공식 Ubuntu22.04의20260913 ARM64 이미지·동일 릴리스 커널/initrd·개발 호스트용 QEMU deb를 SHA256으로 고정한다. `build_guest.py --download`는 프로젝트의 `.native-runtime/ubuntu-arm64/downloads`에만 내려받으며 `dpkg -i`나 호스트 APT를 사용하지 않는다. `--build`는 원본의 전용16GiB QCOW2 overlay 안에 실제 Bash/nano/APT/Docker/ROS2를 설치한다. 사용자용 APK에 들어갈 Android 실행기와 개발 호스트의 QEMU 패키지는 서로 다르다.

개발 VM은2vCPU/2GiB, 낮은 우선순위, 호스트 공유 폴더/노출 포트 없이 구성한다. 준비 중에만 외부 저장소를 접근하며 `--probe` 검사는 외부 네트워크 없이 수행한다. 실제 PTY에서 공백 경로 복사, 원본 유지, GNU nano Ctrl+K/O/X 저장·종료, Ctrl+C 복귀를 검증하도록 했다. Docker 이미지 선택과 ROS 저장소는 실제 게스트 아키텍처를 사용하며 ARM 이미지가 없으면 x86으로 대체하지 않고 실패한다. 빌더/아키텍처7개 단위 검사를 통과했다.

첫 ARM64 이미지의 Ubuntu 부팅과 게스트 제어 연결·도구 설치 후, 종단 검사에서 ROS의 공식 setup.bash를 `bash -u`로 불러온 검사 명령이 미정의 변수 오류로 실패했다. 빌더는 실패로 종료했고 VM은 정상 종료했으며 작업 이미지를 보존했다. **전체 종단 검증은 미완료**다. 검사 명령을 확인한 뒤 `--probe`로 재검증해야 한다. `validation.json` 성공 기록 없이 완성 이미지로 배포하지 않는다. 이 Linux 개발 호스트의 TCG 빌드/검사도 Android 휴대폰 실행 증거가 아니다. 기존 x86 배포 이미지와 개인 진도는 변경하지 않았다.

- Linux 개발 호스트, Python3.12 이상, make/ninja/pkg-config/patch.
- 프로젝트 전용 NDK r27c: `desktop/.android-tools/sdk/ndk/27.2.12479018`.
- `native-sources.json`의 공식 소스와 고정 SHA-256. 압축 파일은 `android/.native-runtime/downloads`에 보관한다. 빌드 도구가 의존성을 자동 다운로드하지 않는다.
- QEMU/GLib 등의 압축은 `.native-runtime`에 풀어 둔다. 의존성 스크립트는 의존성 소스의 체크섬을 검증하고 없으면 안전한 tar data 필터로 추출한다.
- `.native-runtime/build-tools`는 호스트 빌드용 Python venv다. QEMU 배포본의 Meson1.10.0 wheel, setuptools84.0.0/wheel0.46.3/packaging26.3을 사용했다. 이 도구는 Android 앱의 Python 실행기가 아니다.

## 실행

상류 autotools의 공백 경로 제약 때문에 `mktemp -d /tmp/shellground-android-native.XXXXXX`로 새 작업 폴더를 만든다. 스크립트는 그 폴더의 소유 마커를 검사하고 프로젝트 NDK·소스에 대한 링크를 둔다. 개인 `/usr`, 개인 Conda, Termux 설치를 사용하지 않는다.

```sh
python3 android/runtime/build_dependencies.py --abi arm64-v8a --build-root /tmp/shellground-android-native.생성된이름
python3 android/runtime/build_qemu.py --abi arm64-v8a
```

`x86_64` ABI도 같은 명령의 별도 대상으로 준비한다. `-j2`, nice15로 제한한다. 현재 게스트 아키텍처는 실제 ARM64이고, 호스트 ABI와 혼동하지 않는다. Android API28로 빌드하며 기존 Python 앱의 API24 하한을 바꾸지 않는다.

의존성 결과는 `.native-runtime/dependencies-ABI.json`, QEMU 빌드가 성공하면 `.native-runtime/qemu-ABI.json`과 `qemu-ABI-elf.txt`에 기록한다. 이는 **빌드 증거일 뿐 Android 실행 증거가 아니다.**

검증된 QEMU 실행 파일은 `.native-runtime/candidates/<ABI>/<SHA256>/qemu-system-aarch64`에도 보존한다. 재부팅으로 임시 빌드 폴더가 사라져도 해당 체크섬 캐시를 다시 사용할 수 있다. 과거 캐시가 없는 경우에는 이 프로젝트의 두 지정된 생성물 폴더에 남은 **기존 보고서와 바이트 단위로 동일한** 파일만 복구한다. 소스·패치·SHA·ELF 검사를 모두 유지하고 영구 프로젝트 NDK의 `llvm-readelf`로 재검증한다. 다른 실행 파일을 새 빌드로 인정하거나 충돌 캐시를 덮어쓰지 않는다.

## Android 포팅 패치

`patches/0001-android-shared-memory.patch`는 Android에 없는 POSIX shm/librt 대신 NDK의 실제 `ASharedMemory_create`를 사용하고 close-on-exec 오류를 처리한다. 이 빌드에서 지원하지 않는 ivshmem 주변장치는 제외한다. libfdt는 교차 빌드한 pkg-config 경로에서 찾는다. 제삼자 의존성은 정적으로 묶되 Android 플랫폼 라이브러리는 정상 동적 연결하도록 `prefer_static`의 실행파일 전체 정적 링크를 제외한다. 패치는 문맥 생략 없이(`--fuzz=0`) 검사한다. Termux의 앱 전용 파일 경로를 복사하지 않는다. 원본 QEMU의 라이선스와 저작권은 유지하며 배포 시 전체 대응 소스·이 패치·빌드 도구·종속 라이선스를 함께 제공해야 한다.

ARM64와 x86_64 후보 모두 교차 빌드와 ELF 검사를 통과했다. `verify_candidate.py`는 host ABI, Android linker64, PIE,16KB LOAD 정렬과 offset 일치, 허용된 시스템 동적 라이브러리, RPATH/텍스트 재배치 부재를 검사한다. 이 검사는 실제 Android 실행이나 실제 Linux 부팅의 대체 증거가 아니다. 원본 QEMU 압축의 두 파일에 저장된 패치를 `--fuzz=0`으로 적용해 실제 빌드 입력과 일치하는지도 검사했다(5개 개발 검사 통과).

## 별도 Android 실행·부팅 검증

`runtime-probe`는 `-PlinuxProbe=true`를 주었을 때만 포함되는 별도 개발 모듈이다. `org.shellground.runtimeprobe`라는 다른 패키지명이며 기존 학습 앱·진도를 변경하지 않는다. APK에 포함한 실행파일을 설치기의 nativeLibraryDir에서 시작하고 쓰기 가능한 앱 폴더에서 호스트 실행파일을 실행하지 않는다. 네트워크 권한이나 루팅, Termux, 외부 PC 실습 서버가 없다.

프로젝트 SDK/JDK/Gradle 캐시를 지정한 상태에서:

```sh
gradle --offline --no-daemon -PlinuxProbe=true :runtime-probe:assembleDebug :runtime-probe:assembleDebugAndroidTest
python3 runtime/run_probe.py --serial emulator-5558
```

두 번째 명령은 명시된 전용 에뮬레이터에 검증 APK 두 개를 설치하고 실제 검사를 수행한다. `adb`가 exit0이어도 계측 검사에 실패하면 실패로 기록한다. 결과는 `.native-runtime/probe-validation.json`, 실제 콘솔 출력은 `probe-instrumentation.log`다. 설치/실행 명령이므로 개인 기기에 무심코 사용하지 않는다.

부팅 데이터는 공식 Alpine3.23.5 ARM64 ISO의 게시된 SHA256을 검증한 뒤 커널6.18.36과 initramfs 두 파일만 추출했다. 출처는 `boot-sources.json`에 고정했고 mount/root 권한을 사용하지 않는다. `stage_boot.py`는 개발 APK의 지정 출력 폴더에만 쓴다. 이 작은 initramfs는 **수업용 Ubuntu/Bash/Conda/Docker/ROS 배포판이 아니다.** 진단을 위해 `/init` 대신 실제 `/bin/sh`를 시작하고 원래 init이 수행하는 BusyBox 명령 링크 준비를 명시적으로 했다. job control과 실제 PTY/nano 조작은 별도 통합 검사가 필요하다.

API35 x86_64에서4개 검사 통과: 실제 QEMU 버전, ARM 머신 시작/정상 종료, 강제 종료, 실제 Linux의 `uname`·공백 경로 파일 생성/추가/읽기·poweroff. 첫 전체 통과에서 부팅+파일+종료는1.555초였으며 **휴대폰 성능이나 전체 수업 VM 부팅 시간으로 일반화하지 않는다.** 게스트는2vCPU/384MiB, TCG 코드 캐시16MiB이며 호스트 에뮬레이터 자원은 별도다.

동일 APK의 반복 검사도4개 통과했다(계측2.06초,부팅+파일+종료1.492초). 이후 Android 프로세스 목록에서 검증 앱과 실행기 자식이 남지 않았음을 확인했다. 첫 실패들도 기록했다: 미지원 커널 옵션이 init 인자로 전달되던 문제, 프롬프트를 잘못 예상한 검사, rdinit으로 생략된 BusyBox 링크 준비. 명령 출력 모사나 기대값 완화로 덮지 않고 실제 콘솔에 맞춰 부팅 준비/검사를 정정했다.

검증 APK SHA256 `10b2d587e3c6af04e313a4f4e1b78fb7fece231eedd93b34f9f67199fd8daa40`, 계측 APK `c3773769511db9be760563ed2786d2f54ab43d2f7fcffb43b8451450b1279654`. 대응 소스·라이선스 배포 준비가 끝난 일반 사용자용 릴리스가 아니다.

## 남은 인수 조건

1. ARM 실제기기에서 현재 후보 실행·커널 부팅·16KB 페이지 런타임 확인. x86_64 에뮬레이터 결과로 대체하지 않는다.
2. 개발 검증 APK가 아닌 학습 앱의 서비스·백그라운드/비정상 종료 처리와 실제 PTY 통합.
3. 실제 Bash/nano/APT/Docker/ROS2/Conda 수업 이미지와 채점 통합.
4. ARM 실제기기의 메모리·반복 부팅·발열·배터리·백그라운드 처리 및 기존 Android UI 회귀.
5. 용량 최적화·최초 준비 UI·대응 소스/라이선스/업데이트 정책과 배포 검증.

출처와 선택 근거는 `../LINUX_RUNTIME_RESEARCH.md` 및 각 소스 URL에 있다. 일반 사용자가 위 빌드·설정을 해야 한다는 최종 사용 방식은 아니다.
