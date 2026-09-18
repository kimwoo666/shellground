> Windows 후속 수정 및 실제 실행 검증: [4.7.4-windows.1](WINDOWS_4.7.4.1_VERIFICATION.md). 아래는 초기 배포 당시 기록입니다.

# 4.7.4 verification / 검증 기록

2026-09-18 · Preview release. Build success, actual execution and physical-device acceptance are different claims.

| 대상 | 확인한 내용 | 경계 |
| --- | --- | --- |
| Linux 묶음 | 패키징된 Python worker, 실제 Jupyter 커널 선택, 새 ROS 조작, 종료 정리 | 변경 없는 기존 과정의 증거를 재사용 |
| Windows 묶음 | Wine 기반 Windows 실행파일 제작, 포함 파일·공유 실습 디스크 확인 | 실제 Windows PC 기동은 미검증 |
| Android Python | 새 pandas 4항목·12참조 문제의 준비 → 실행 → 채점 | 전체 285문제 재실행 아님 |
| Android Jupyter | 실제 `sg-data` 커널 선택, 셀 실행, 오답 후 재채점, `.ipynb` 저장, VM 종료 | Android 15 x86-64 에뮬레이터 안의 ARM64 guest |
| Android Conda | 실제 환경 준비, 파일 목록, 미완료 채점, `conda --version`, 정답 재채점, VM 종료 | 최종 연결 검사 `OK (1 test)`, 372.813초 |
| Android 입력·자료 | Shift+Enter가 줄바꿈 없이 실행, 현재 과정 포함, 6개 소스·내보내기 경계 검사 | 실제 명령 실행 증거와 구분 |
| 공유 PC 디스크 | 압축 전후 논리 내용 비교 통과, Linux·Windows 동일 SHA-256 | 같은 디스크를 OS별로 중복 배포하지 않음 |

마지막 Android 수정은 Conda 연결 파일을 guest에 갱신하는 목록의 누락을 고친 것이다. 이전 파일은 115초 제한을 계속 사용했다. 수정 후 실제 준비·명령·채점·종료를 다시 확인했다. Jupyter 코드와 자산은 바뀌지 않아 이미 통과한 실행 증거를 재사용했다.

노트북 자원을 제한하며 검사했다. Jupyter 검사는 CPU 합산 0.55코어 상한, 마지막 Conda 검사는 1.0–1.2코어 상한이었다. 에뮬레이터 안에서 다른 아키텍처의 guest를 실행한 시간은 실제 휴대폰의 성능 측정이 아니다. Android 실휴대폰의 발열·배터리·호환성과 Windows 실기동은 확인되지 않았다.

릴리스의 `pc-build.json`, `android-build.json`, `SHA256SUMS.txt`는 배포 파일의 식별 정보와 확인 범위를 기록한다. 체크섬은 파일 손상 확인용이며 공인 코드 서명이나 보안 인증을 대신하지 않는다. 이 기록은 강의 PDF의 모든 명령 옵션을 구현했다는 선언이 아니다.

## English summary

Linux packaging checks passed using real workers/kernels and focused new ROS controls. Windows was built with Wine and has **not** been executed on a native Windows PC. Android's new Python and input/catalog checks passed; actual Jupyter kernel selection, execution, retry, saving and cleanup passed. The final actual Conda preparation, command, failed-grade retry and cleanup test passed in 372.813 seconds.

The Conda fix synchronizes the guest adapter before its first import. Unchanged, already-passing Jupyter evidence was reused rather than replayed. Android results came from an Android 15 x86-64 emulator running the embedded ARM64 guest under CPU limits, not a physical ARM phone. No full-curriculum rerun or exhaustive lecture-option completion is claimed. See the small release receipts and checksums for artifact identities.
