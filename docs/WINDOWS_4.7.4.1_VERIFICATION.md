# Windows 4.7.4-windows.2 검증

2026-09-18 · Windows 11 Pro x64, OS 10.0.26200, WHPX 사용.

초기 Windows 배포의 설치 실패를 재현하고 Windows에서 실행 파일과 NSIS 설치기를 다시 빌드했다. Python 3.12.14, PyInstaller 6.22.2, PySide6 6.8.3 및 고정된 의존성을 사용한다. 공유 Linux 게스트 디스크의 SHA-256은 `cd7f3361dc0b2b1c66e88bfc3ab2ed037e21ee276f2ae3f20bd12efd8530e2e6`이다.

## 수정한 문제

- NSIS 임시 폴더의 네이티브 `System.dll`이 C# 컴파일러의 .NET 참조를 가리는 문제: 설치기가 로드된 관리 어셈블리의 절대 경로를 전달한다.
- QEMU 11에서 제거된 `reconnect=1`: Windows에서 `reconnect-ms=1000`을 사용한다.
- 한글 설치·임시 경로의 QEMU 파일 조회 실패: 세션에 작은 펌웨어 파일만 복사하고, Windows 작업 폴더를 해당 세션으로 지정한다. 펌웨어·overlay·로그를 ASCII 상대 경로로 열며 종료 시 함께 정리한다.
- 제한된 CPU에서 첫 ROS 실행 준비 시간 초과: 실제 DDS pose 관찰과 turtlesim 파라미터 응답을 확인한다. 제한 시간과 실패 시 종료 동작은 유지한다.
- Windows 자체 검사에서 LF가 CRLF로 바뀌는 문제, GUI 실행 파일의 표준 핸들 상속, Python 전체 검사 목록 결합을 수정했다.

## 실행 검사

| 검사 | 확인 범위 |
| --- | --- |
| Windows/ROS 회귀 검사 | 27건 통과: Job 제한, 종료 수명, 입출력, QEMU 명령·경로, 취소, ROS 준비 |
| 새 바이너리 무결성 | 리소스 22개, 실습 단원 138개 목록, 번들 과학 라이브러리 실행·그림 저장, 작업자 정리 |
| Python 전체 | 번들 작업자에서 95개 단원·285개 문제와 오답/동등 풀이 124건 통과 |
| Windows 네이티브 화면 | Qt windows 플랫폼에서 화면 전환, Shift+Enter, F6, 퀴즈→실습 이동, 숨은 프로세스 정리 |
| 실제 Linux·ROS·Docker | ROS 파라미터 채점 및 게스트 화면, 파일 복사, apt 설치, 계정·권한, Docker 갱신·아카이브 복원·배포 |
| 실제 Conda | 환경 활성화, 동일 터미널 재채점, 환경 내보내기와 파일 읽기, VM/overlay 정리 |
| 실제 Jupyter | basic/data 커널 등록, data 커널 선택·실행·채점·노트북 저장, VM/overlay 정리 |

마지막 경로 변경은 동일한 번들/실습 자료에 적용되며, 위 Python·Conda·Jupyter 과정 코드는 바뀌지 않았다. 한글·공백 설치 폴더와 한글 임시 폴더를 동시에 사용해 실제 WHPX 부팅과 게스트 채점기 전송을 확인했다.

## 확인 범위의 경계

이 기록은 실제 Windows 11 WHPX 실행 결과다. 모든 Linux/Docker/ROS/Jupyter 문제를 모든 PC에서 전수 실행했다는 의미가 아니다. Windows 10, ARM Windows, WHPX가 없는 TCG 실행 성능, 외부 로봇·GPU 장치는 이번 실제 장치 검사 범위에 포함되지 않는다. 설치 파일은 서명되지 않았다.

CPU Job에는 0.6 논리 코어에 해당하는 hard cap과 kill-on-close를 설정하고 실제 값을 조회했다. 짧은 CPU 시간 측정은 프로세서 주기 기반 제한과 동일한 값이 아니므로 10초의 보조 관찰로 무제한 실행 여부를 확인한다. [Windows Job CPU rate 설명](https://learn.microsoft.com/en-us/windows/win32/api/winnt/ns-winnt-jobobject_cpu_rate_control_information).

GitHub Windows 워크플로는 네이티브 빌드·회귀·번들·UI 검사를 수행한다. 실제 VM 검사는 WHPX가 있는 별도 Windows에서 수행했다. 배포 ZIP과 설치기의 최종 SHA-256은 해당 릴리스의 `SHA256SUMS.txt` 및 `windows-build.json`에 제공한다.
