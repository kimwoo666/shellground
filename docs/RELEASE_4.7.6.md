# Shellground 4.7.6

## 한국어

- **NAS 진도 연동**: Linux·Windows·Android에서 같은 개인 NAS 폴더로 완료 기록과 소단계 위치를 이어갑니다. Windows는 연결된 공유/UNC 경로, Android는 앱 내 SMB 연결을 사용합니다. [설정 방법](NAS_SYNC.ko.md)
- **pandas 설명 보강**: 기존 26단원의 내용과 활용 문제를 유지하면서 설명·준비 자료·실행 예제·결과 확인을 갖춘 81개 배우기 소단계를 추가했습니다. 배우기 단계의 결과 확인은 단원 완료로 처리하지 않습니다.
- **Matplotlib 표시 수정**: 현재 그림을 먼저 보여 주고 최대 6개 그림을 선택해 확인합니다. 실행 오류와 그림 렌더링 오류를 숨기지 않습니다. Android에도 같은 실행·표시 흐름을 적용했습니다.
- Android에서 설명 소단계 이전 이동·예제 불러오기·처음부터 다시 배우기·외부 키보드 Shift+Enter 실행을 지원합니다.
- 개인 NAS 주소·공유 경로·계정·비밀번호·프로필·진도는 소스나 설치파일에 넣지 않았습니다. 각 기기에서 본인의 연결을 설정하세요.

Windows는 `Shellground-Windows-Setup.exe`, Linux는 `Shellground-Linux-Setup.run`, Android는 `Shellground-4.7.6-Android.apk` 하나를 받습니다. PC의 공통 실습 자료는 첫 설치 때 자동으로 받으며, 검증된 기존 디스크는 가능한 경우 재사용합니다. 개인 Docker·WSL·Python 환경과 완료 진도는 삭제하지 않습니다.

네트워크 연결이 끊겨도 로컬 진도는 유지됩니다. 기기를 옮기기 전 **NAS 저장 완료**를 확인하고, 다른 기기에서는 앱을 완전히 닫았다가 다시 열어 받은 진도를 적용하세요. 문제 업데이트는 앱 업데이트로, 진도 이동은 NAS 동기화로 이루어집니다.

검증은 변경된 동기화·소단계 연결·그래프와 새 실행파일의 시작/종료에 집중하며, 이미 통과한 전체 강의 실습을 반복하지 않습니다. Android의 실제 ARM 휴대폰 검증을 완료했다는 뜻은 아닙니다. [플랫폼별 확인 범위](PLATFORMS.md)

## English

- Private NAS progress sync across Linux, Windows and Android. Use an OS-mounted share/UNC path on Windows and the in-app SMB client on Android. [Setup guide](NAS_SYNC.md)
- 81 guided pandas learning steps across the existing 26 units, with explanations, initial data, executable examples and focused checks. Existing application tasks are retained; guided checks do not mark a unit complete.
- Matplotlib shows the current figure first and supports selecting up to six previews. Execution and rendering errors remain visible, including on Android.
- Android gains previous-step navigation, example loading, relearning and external-keyboard Shift+Enter execution.
- No personal NAS endpoint, account, password, profile or progress is embedded in source or downloads. Configure your own connection on each device.

Download one installer/APK for your OS. PC setup retrieves the shared practice runtime automatically and reuses a verified previous disk where possible. Updates preserve personal progress and do not remove a user's Docker, WSL or Python installation.

Offline progress stays on the device. Confirm successful NAS saving before switching devices; fully close and reopen the receiving app to apply incoming progress. Courses update with the application, not through the NAS.

Verification is scoped to changed sync, guided learning, graph behavior and new-binary startup/shutdown, not a full curriculum replay. Physical ARM Android phones remain unverified. See the [platform notes](PLATFORMS.md).
