# Platform status / 운영체제별 상태

Version 4.7.4 / Windows update 4.7.4-windows.1 · 2026-09-18

[이번 배포의 구체적인 검증 기록 / Verification record](VERIFICATION_4.7.4.md)

| Platform | Produced | What the evidence means |
| --- | --- | --- |
| Linux x86-64 | Native executable + bundled guest | Packaged Python, actual Conda/Jupyter and new ROS controls were checked on the development laptop. Existing unchanged course evidence was reused, not replayed. |
| Windows x64 | Windows executable + bundled Windows QEMU | Native Windows build; current evidence and tested OS/hardware boundary are in the [Windows verification record](WINDOWS_4.7.4.1_VERIFICATION.md). |
| Android | Native APK + embedded ARM64 guest | Emulator checks cover new port boundaries. This is not a physical ARM-phone or full-curriculum acceptance claim. |
| macOS | Not packaged | Outside this release. |

실행파일 제작과 실기기 검증을 구분합니다. 초기 Wine 빌드 이후 Windows 호환성 수정판을 별도로 제작하고 실제 Windows에서 검증했습니다. Android 에뮬레이터 결과를 실제 휴대폰의 발열·속도·배터리 검증으로 바꾸어 표시하지 않습니다.

Android 검사는 CPU 사용량을 제한한 x86-64 에뮬레이터 안에서 ARM64 Linux를 실행했습니다. 이 조건에서는 VM 시작과 실습 준비에 수분이 걸렸습니다. 앱 화면이 열리는 시간과 실습 OS·커널의 준비 시간은 다릅니다. 실제 휴대폰의 빠른 기동을 보장하는 결과가 아닙니다.

## Runtime choices

Desktop uses native Qt widgets. Android uses native Java views, not WebView. Python data exercises use embedded CPython; Linux-based exercises run actual tools in an app-owned Linux guest. Android embeds the guest locally and does not require a desktop server.

The guest has restricted networking and preloaded teaching fixtures. Registry/download exercises can refer to lab-local resources; they are not promises of unrestricted Internet access, GPU support, robotics hardware access or a full driving simulator.

The retained desktop simulator is a separate, limited mode. It is not used as proof that a real Linux/Docker/ROS command ran.

## Curriculum vs. exhaustive support

The currently registered material is published with shared task definitions and graders. Counts do **not** establish coverage of every option in the lecture PDFs. Some hardware-dependent topics are taught through explanation, settings or observation; actual GPU computation, external devices, X11 display, snap/RTC/NTP success are not claimed universally.

현재 수록 문제의 채점 확인과 강의의 모든 세부 옵션 대조는 별개입니다. [상세 범위](../desktop/CURRENT_COVERAGE.md)를 참고하세요. 과거 보고서는 당시 버전의 증거이며 최신 APK 전체 실행 증거로 둔갑시키지 않습니다.

## Validation policy

Only newly added or directly affected paths are rerun. A portable package records its SHA-256 and build/verification boundary. Source tests, build success, emulator execution and physical-device testing remain distinct.

Large generated caches and obsolete review binaries are not repository content. Keep current source, small evidence summaries, the latest deliverables and the signing key; the key is private and never uploaded.
