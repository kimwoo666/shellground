# Android 단독 실제 Linux — 조사와 구현 검증 기록

## 2026-09-17 후속: 학습 앱 화면·서비스 연결

실제 학습 APK에 native LinuxService/문제·터미널·채점 화면을 연결했고, APK 안 이미지 자체설치→실제 nano편집→같은세션채점→VM정리를 검증했다. 서비스검사80.043초,최초자체설치80.087초,실제UI검사68.1초. 기존95단원19복습의 공유자료를 내보낸다. APK약2.03GB/추가이미지공간약2GB이며최초준비와부팅대기는남는다. 실제ARM휴대폰/전체단원인수/AndroidConda/라이선스배포완료가아니다. 상세 `runtime/README.md`, 최신UI회귀·해시는 `UI_VERIFICATION.md`. 아래미연결기록은이력이다.

## 최신 실행 증거 — 2026-09-17

별도 개발 검증 앱에서 전체 ARM64 Ubuntu22.04의 실제 PTY/nano 편집→채점, Docker 컨테이너, ROS2 메시지 발행·구독과 종료까지 통과했다. API35 x86_64 에뮬레이터에서 부팅43.927초/전체계측106.198초이며 실제 ARM 휴대폰 측정은 아니다. 무결성을 확인하는 GuestMachine과 독립 압축 이미지(기본 디스크 약1.74GB)를 준비했다. 상세 증거·APK 해시는 `runtime/README.md`의2026-09-17 절을 따른다. 학습 APK 화면 통합, Android Conda, 전체과정/실기기 검증, 배포 용량·라이선스는 미완료다. 아래 기록은 앞선 단계의 이력으로 보존한다.

## 최신 실행 증거 — 2026-09-16

후속 구현에서 앱 내부 Unix 소켓/JSON 제어 연결부를 추가했다. API35 x86_64의 최신 별도 검증 APK는8개 검사 통과(실제 QEMU 소켓1개, 프로토콜3개 추가)이며 전체 로그·해시는 `runtime/README.md`가 기준이다. 실제 Ubuntu ARM64 수업 이미지 빌더도 구현해 부팅/제어 연결을 확인했고 도구 설치와 종단 검증을 진행 중이다. 이 시점에 학습 APK 통합이나 휴대폰 지원 완료로 표시하지 않는다.

조사 뒤 실제 구현을 진행했다. 두 Android ABI의 QEMU를 빌드하고 검증 APK에 묶었으며 API35 x86_64 에뮬레이터의 일반 앱 권한에서 실제 ARM64 Linux6.18.36 부팅·셸 입출력·공백 파일명 저장/추가/읽기·poweroff가 통과했다. 버전·머신 정상 종료·강제 종료를 포함한4검사 통과(2.138초), 부팅/파일/전원 종료 구간1.555초다. 후속 반복 결과와 APK 해시는 `runtime/README.md` 및 `.native-runtime/probe-validation.json`에 기록한다.

이는 별도 **개발 검증 앱 + 작은 Alpine initramfs**의 결과다. 사용자용 학습 APK, 실제 ARM 휴대폰, Bash/nano의 완전한 PTY, Docker/ROS/Conda 수업 VM의 완료나 성능 검증으로 확대하지 않는다. 아래의 ‘미검증’은 조사/빌드 당시 이력이며 현재 남은 조건은 `runtime/README.md`가 기준이다.

## 2026-09-16 네이티브 빌드 착수

공식 QEMU11.0.3/GLib2.88.3/libffi3.5.2/PCRE2 10.47/libfdt1.8.1 및 GLib 지정 proxy-libintl0.5 소스를 다운로드하고 고정 SHA-256을 확인했다. 소스 URL·해시는 `runtime/native-sources.json`에 기록했다. 원본 소스/라이선스는 `.native-runtime` 개발 폴더에 보존하며 배포 대응 소스 패키지는 아직 만들지 않았다.

`runtime/build_dependencies.py`로 NDK r27c의 ARM64/Android API28 대상 필수 라이브러리를 실제 교차 빌드했다. 개인 SDK/Termux 경로에 의존하지 않는 별도 prefix이며2작업/nice15로 제한한다. 상류 autotools의 공백 경로 문제를 피하려고 소유 마커가 있는 `/tmp/shellground-android-native.*` 작업 폴더를 사용하고, 원본은 프로젝트에 둔다. 첫 GLib 구성에서 발견한 libintl 의존성은 GLib의 고정 wrap 소스로 해결했다. 프로젝트 밖 시스템 설치는 하지 않았다.

`runtime/build_qemu.py`로 실제 ARM `virt` 머신을 지원하는 ARM64 호스트용 headless QEMU 후보 빌드에 성공했다. ELF의 네 LOAD 구간은16KB 정렬이며 Android의 linker64와 libc/libm/libandroid만 동적 의존한다. `runtime/verify_candidate.py`가 잘못된 ABI/호스트 라이브러리/RPATH/정렬을 거부한다. **Android 프로세스 실행·Linux 커널 부팅·수업 VM·APK 통합의 성공 증거는 아직 없다.** API28은 이 후보의 빌드 하한이고 기존 Python 앱의 API24 하한을 바꾸지 않았다. x86_64 호스트용 빌드는 별도 진행 중이다.

2026-09-16. 사용자 선택은 PC 연결 없는 독립 실행이다. 이 문서는 지원 완료나 성능 검증 결과가 아니다. 현재 APK는 실제 Python 실습만 제공한다.

## 실행 경로

일반 앱의 기기별 가상화 권한을 가정하지 않고, 앱에 포함한 전체 시스템 QEMU가 실제 Linux 커널을 실행하는 경로를 검토한다. proot 환경을 Docker 가능한 VM이라고 부르거나 명령어 출력 모사로 바꾸지 않는다. 호스트는 Android ARM64/x86_64, 게스트 CPU는 별도로 선택해야 한다.

상류 구현 근거:

- [QEMU ARM virt](https://www.qemu.org/docs/master/system/arm/virt): ARM 게스트 머신과 CPU/가속 구성을 확인할 기준.
- [Termux의 QEMU headless 빌드 레시피](https://github.com/termux/termux-packages/blob/master/packages/qemu-system-x86-64-headless/build.sh): 현재11.0.3에 Android/Bionic 관련 빌드·ARM64 setjmp 보정·공유메모리 의존성이 있다. 파일명과 달리 aarch64-softmmu 등 여러 게스트를 빌드한다. **Termux 앱을 사용자 준비물로 요구하는 계획은 아니다.** 상류 이식 작업을 참고하고 Shellground의 경로·패키징으로 다시 빌드해야 한다.
- [Limbo 개발 문서](https://github.com/limboemu/limbo/blob/master/README.developers): NDK로 빌드한 `libqemu-system-*.so`를 APK에 넣는 기존 접근과 수정 소스 배포 요건을 확인했다. 문서의5.1/2.9 버전을 현재 지원 버전이라고 그대로 채택하지 않는다.

후보 공식 QEMU11.0.3 소스 SHA256은 `da5fcffc32762820568b828ed430a728864d34d50b6d2f30358597760cbb0523`이며 실제 다운로드 해시를 확인했다. 독립 서명 검증을 수행했다고 주장하지 않는다. QEMU/의존 라이브러리와 Android 이식 패치의 라이선스·대응 소스도 배포에 포함해야 한다.

Android10+의 [앱 쓰기 가능 홈 디렉터리 실행 제한](https://developer.android.com/about/versions/10/behavior-changes-10#execute-permission)에 따라 실행기를 다운로드 폴더에서 chmod하여 실행하지 않는다. APK에 포함해 설치 시 추출한 nativeLibraryDir에서 실행하는 개발 검사부터 한다. 공유메모리도 같은 공식 문서가 요구하는 NDK `ASharedMemory` API를 사용한다.

## 실제로 확인해야 할 순서

1. 프로젝트에 이미 있는 NDK r27c로 앱 전용 headless 실행파일과 최소 의존성을 빌드한다. 다른 앱의 개인 디렉터리나 Termux 경로에 의존하지 않는지 ELF를 검사한다. ARM64 16KB 페이지 정렬도 별도 검사한다.
2. 네이티브 라이브러리 디렉터리에서 실행 가능한 패키징과 Android의 실행 제한을 검증한다. 앱 writable 폴더에 내려받은 실행파일을 chmod해 실행하는 방식은 전제하지 않는다.
3. 작은 실제 ARM64 커널/루트 파일시스템으로 부팅, 양방향 터미널, 정상 종료·강제 종료·고아 프로세스 정리를 먼저 검증한다. 이는 Linux/Docker/ROS 전체 지원 증거가 아니다.
4. 그 후 수업용 실제 Bash/nano/APT/Docker/ROS2/Conda와 채점 에이전트를 갖춘 별도 ARM64 게스트를 구성한다. 현재 x86_64 이미지가 ARM64 네이티브 이미지인 것처럼 취급하지 않는다.
5. 학습 초기 상태/참조 풀이/오답 수정과 프로세스 종료를 실제 Android에서 검증한다. 기기 RAM, 설치·확장 용량, 냉간/반복 부팅, CPU·온도·배터리·종료 지연을 측정한다. 에뮬레이터 결과를 실제 휴대폰 성능이라고 보고하지 않는다.

기본 자원 정책은 작은 가상 CPU 수, 표시되지 않을 때 작업 정지/종료, 제한된 출력 큐, 이벤트 기반 I/O이다. TCG의 여러 스레드 지원이 저발열 보장은 아니다. 지금 상태에서는 ‘켜면 바로 준비되는 전체 Linux 실습’을 달성했다고 표시할 수 없다.
