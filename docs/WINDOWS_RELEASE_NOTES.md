Windows · Linux 실습 시작 속도 개선판입니다.

- 앱을 열면 모드 선택·설명 화면 뒤에서 실제 Linux와 Docker를 미리 준비합니다.
- 준비된 VM을 첫 실습에서 그대로 사용합니다. 설명이나 다음 단원으로 이동해도 VM을 다시 부팅하지 않습니다.
- 이전 문제의 터미널·프로세스·파일은 정리합니다. ROS 노드는 선택한 실습에 맞춰 시작합니다.
- 앱 종료·모드 선택 취소·Python/시뮬레이션 선택 시 불필요한 미리 부팅 작업을 정리합니다.
- 저장된 완료 기록·학습 진도·기억노트는 기존 경로와 형식을 사용합니다.
- Windows 측정에서 준비 완료 후 첫 실습 0.44초, 다음 실습 0.33초를 관찰했습니다. 백그라운드 준비 자체는 약 9초이며 PC에 따라 달라집니다.
- 이전 Windows 설치 DLL, QEMU·한글 경로, WHPX CPU 예산 수정도 포함합니다.

Windows는 `Shellground-Windows-Setup.exe`, Linux는 `Shellground-Linux-Setup.run`을 실행합니다. 별도 Python, Docker, ROS 2, Conda 또는 WSL 설치는 필요하지 않습니다. 첫 설치에는 인터넷 연결과 약 9GB의 여유 공간이 필요합니다.

기존 Linux 4.7.4 설치의 검증된 실습 디스크는 재사용합니다. Android는 기존 배포본을 사용합니다. 플랫폼별 확인 범위와 실제 측정 조건은 저장소의 `docs/DESKTOP_4.7.5_VERIFICATION.md`를 참고하세요.
