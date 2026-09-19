# Windows 포팅 착수 — Linux 검토판 이후

2026-09-18. [Linux4.7.4 실행파일](LINUX_474_REVIEW.md)의 증분 배포 검사까지 끝난 뒤 착수했다. Windows 완성/실행 성공을 선언하는 문서가 아니다.

추가 진행: Windows GUI 내부 파이프/UTF-8·native CPU probe와 Windows 빌드용 guest 증거 연결을 보완했다. 이번 추가 계약 검사 **14개 통과**(Win32 실제 실행 아님). Windows는 반복 압축 해제를 없앤 onedir 폴더형으로 준비하며 Linux onefile은 유지한다. 준비된 입력/명령/미완료 실기동 항목은 [Windows 빌드 재개 문서](WINDOWS_BUILD_HANDOFF.md)에 정리했다. `.jupyter-build/incremental-course-manifest-windows-prep.json`은 정확한 host-only 역패치 해시 확인으로 441개 **Linux 학습** 결과를 재사용하며 Windows 실행 성공은 0건으로 명시한다. 기존 441 manifest는 변조하지 않았다.

## 현재 준비한 것

Windows x64 개발용 런타임을 `.windows-build/runtime/windows-x86_64`에 조립했다. **Shellground.exe 완제품이 아니며 Windows에서 실행한 결과도 아니다.** `runtime.json`에 `windows_validation.state=not-run`, `release_ready=false`를 명시했다. Android 포팅은 아직 이 단계 다음이다.

- QEMU 공식 다운로드 페이지가 연결하는 Windows 배포본 `qemu-w64-setup-20260811.exe`를 공식 SHA512와 대조했다. 설치 프로그램은 실행하지 않았고 필요한 x64 QEMU 두 도구·DLL·펌웨어·문서/라이선스 3,319개만 추출했다. 추출한 PE 파일 116개가 x64인지 확인하고 정적 DLL 의존성 목록도 남겼다. 동적으로 로드되는 파일과 Windows OS DLL 실제 해석은 실기동 검사 대상이다.
- Linux에서 검증된 16,169,566,208바이트 guest의 SHA256을 다시 확인한 뒤 **하드링크**로 연결했다. Windows 검증을 위해 학습 문제를 재실행하지 않았다. 현재 guest SHA256은 `92ad90b561abe6ac7851244cb2abadd0836e3b328216b8b72ac5ecc3fb81b7fc`이다. 원본 runtime.json은 별도의 `guest-runtime-linux.json`에 바이트 그대로 보존하며 Linux 증거를 Windows 성공으로 바꾸지 않는다.
- 하드링크는 현재 개발 PC의 공간 절약 방법이다. 이 runtime을 다른 PC로 배포할 때는 base 파일 실제 용량을 포함해야 한다. 모든 공유 base는 **불변**이며 교체할 때 새 파일을 만들어 원자적으로 바꿔야 한다. 직접 수정하면 기존 Linux 검토판도 손상된다.
- Windows 하이퍼바이저가 이미 켜져 있으면 WHPX를 선택한다. 없으면 설정/재부팅/WSL 설치 없이 TCG를 선택하되 시작 화면에 느린 소프트웨어 실행임을 표시한다. WHPX 시작 실패를 임의로 TCG로 재시도하지 않는다. TCG는 최대 600초의 취소 가능한 시작 대기를 갖는다. 이것은 빠른 기동 검증 완료라는 뜻이 아니다.
- Windows supervisor와 QEMU에 **한 개의 kill-on-close Job Object**를 적용하고 CPU hard cap을 함께 설정한다. WHPX 하드웨어 가속에는 **호스트 논리 코어의 절반, 최대 4코어분**을 허용한다(단일 코어 호스트는 0.6코어). 소프트웨어 실행 TCG의 예산은 **논리 코어 0.6개분 합계**로 유지한다. 코어 고정은 하지 않는다. 제한 설정이 실패하면 QEMU 실행 전에 중단한다. CPU 시간 제한이지 온도/배터리 사용량 보장은 아니며, WHPX 실제 사용량도 Windows에서 측정해야 한다.
- 앱이 Windows qemu.log를 계속 열어 두어 임시 폴더 삭제를 막던 구조를 분리했다. 감독 프로세스 오류는 별도의 자동 정리 임시 파일로 받고, QEMU 오류는 종료 전 최대 3,000바이트만 전달한다. 쉼표/공백/한글 경로, firmware 경로 검증과 UTF-8 runtime metadata 처리도 추가했다.
- `.gitattributes`는 Windows checkout이 guest 스크립트 줄바꿈과 소스 해시를 바꾸지 않게 LF를 지정한다. 기존 Linux 실행파일/바로가기/진도는 건드리지 않았다.

## 이번 증분 검사

**새/변경 코드 계약 검사 19개 통과**. Win32 API는 Linux에서 모의 호출한 검사이므로 실제 CPU cap·프로세스 종료 성공으로 보고하지 않는다.

- 자원/종료 API 계약 및 Windows 분기 7개.
- 경로 escaping·로그 분리·오류 길이 제한 3개.
- 설치파일/압축 경로/PE 구조/기존 파일 보존 5개.
- UTF-8 metadata와 firmware 경로 검증 1개.
- Windows boot argv·실패 진단/정리·즉시 취소 3개. 처음 2개는 기존 소켓의 멱등 close를 1회로만 가정한 검사 오류였고 해당 가정만 고쳐 두 사례만 재검사했다. 통과한 취소 검사는 다시 실행하지 않았다.

실제 조립은 CPUQuota 60%·nice 15로 한 번 실행했다. 최고 관측 온도는 55°C, 종료 후 38°C였고 디스크 여유는 약 4.6GiB다. 16GB를 복사하지 않았으며 다운로드/추출한 새 파일은 약 0.7GB다. 모든 작업 scope는 종료됐다.

기록: `assembly.json`(파일별 SHA256·원본 guest 증거 연결), `pe-import-inventory.json`(116개 PE의 정적 import), `.windows-build/downloads/`(정확한 배포본), `windows_runtime_pack.py`(재현 조립기). 기존 통과한 Linux 문제 채점은 반복하지 않았다.

## 남은 실제 Windows 게이트

1. Windows x64에서 native Python/PyInstaller로 Shellground.exe를 빌드하고 번들 worker/한글 UI/Shift+Enter/진도 저장을 확인한다. PyInstaller는 Linux 출력물을 Windows 실행파일로 바꾸는 크로스 빌더가 아니다.
2. 실제 WHPX 및 WHPX가 없는 환경에서 부팅, 루프백 채널, PTY, 새 플랫폼의 대표 채점/수정 후 재채점, Conda/Jupyter 연결을 확인한다. 기존 전체 과정 전수 검사는 반복하지 않는다.
3. 정상 종료·부팅 중 취소·앱 강제 종료·감독 프로세스 강제 종료에서 실제 QEMU 종료와 임시 overlay 삭제, 원본 base/사용자 진도 보존을 확인한다. CPU cap 실제 적용 여부와 기동 시간을 측정한다.
4. Windows 배포용 의존성/라이선스 자료와 무설정 사용자 설치·실행 묶음을 마무리한다. 재배포용 압축팩과 native 실행파일은 아직 없다.

현재 연결 환경은 Linux뿐이며 Wine/Windows 빌더도 없다. 사용자에게 사용 가능한 Windows PC 여부를 질문했다. Windows 실행 검증 전 완료 표시/Android 선행 전환/컴퓨터 종료를 하지 않는다.

`real_vm.py`의 Windows 부팅/로그와 공통 metadata 읽기 변경으로 기존 `incremental-course-manifest-441.json` 소스 snapshot은 현재 소스와 달라졌다. 옛 증거나 배포 바이너리를 덮어쓰지 않았다. 새 `windows-prep` manifest는 학습 소스 재사용 검토만 담으며 Windows 호스트 검증은 계속 별도로 필요하다. 과거 전체 채점 PASS를 현재 Windows PASS로 재작성해서는 안 된다.

근거: [QEMU 공식 배포 안내](https://www.qemu.org/download/), [Windows 배포 및 체크섬](https://qemu.weilnetz.de/w64/), [Microsoft CPU Job hard cap](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_cpu_rate_control_information), [Windows 하이퍼바이저 조회](https://learn.microsoft.com/en-us/virtualization/api/hypervisor-platform/funcs/whvgetcapability), [PyInstaller 플랫폼별 빌드](https://pyinstaller.org/en/stable/operating-mode.html).

초기 착수 기록(위 조립 작업 이전):

- `build-windows.ps1`은 이전에 매번 기존 Python 과정 검사들을 실행했다. 이제 기본은 새 바이너리 검사이며 명시적 `--full-validation`일 때만 기존 전체 검사도 실행한다. PowerShell 실제 실행은 아직 하지 않았다.
- 기존 build.py는 호스트가 Linux일 때만 Conda 실습용 NumPy wheel을 넣었다. Windows에서도 내부 실습 OS는 Linux이므로, Conda runtime을 포함하는 빌드는 호스트와 무관하게 해당 Linux guest wheel을 넣도록 수정했다. Linux 기존 경로는 변하지 않는다. 정책 단위검사만 통과했고 Windows 실제 설치/실행 검사는 남아 있다.
- 당시 Windows용 QEMU 실행파일과 runtime 팩이 없었으며, 현재는 위 개발 팩 조립까지 진행했다. 기존 스크립트나 플랫폼별 경로 분기가 있다는 사실은 Windows 실행 증거가 아니다.

현재 남은 작업은 위의 실제 Windows 게이트 목록을 따른다. 이전 학습 문제 전수는 다시 실행하지 않고 플랫폼 의존 경로와 새로운 문제만 검사한다. Android는 이 단계 다음이며 macOS는 이번 목표 밖이다.
