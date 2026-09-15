# Shellground 4

Linux·Docker 명령을 연습하는 **오프라인 네이티브 데스크톱 시뮬레이터**입니다. 웹 앱이 아니며 Docker·WSL·VM 설치가 필요하지 않습니다. 명령어 정답 문자열을 맞추는 방식이 아니라 가상 파일·권한·셸·프로세스·이미지·컨테이너 상태로 채점합니다.

## 현재 버전

- 40단원, 5단원마다 종합 복습 8개, 완료 범위 올랜덤.
- 설명을 보며 자유 연습 → 예시 → 서로 다른 활용 2개 → 완료 기록 자동 저장.
- 활용·종합·랜덤 테스트 중에는 왼쪽 명령어·단원명을 숨깁니다. 배우기·예시에서는 복원합니다.
- 미완료 채점 후 같은 상태에서 계속 수정하고 F5로 재채점할 수 있습니다.
- Linux x86-64에서 빌드·검사했습니다. Windows 공용 코드/빌드 스크립트는 제공하지만 **Windows exe 산출물과 실기기 검증은 아직 없습니다**.

## 시작하기

Linux 빌드 산출물은 `desktop/dist/Shellground`, Windows에서 빌드한 산출물은 `desktop/dist/Shellground.exe`입니다. 실행할 때 Docker나 가상화 설정은 필요 없습니다.

소스에서 실행하려면 Python 3.12 환경에서 다음을 실행하세요.

```sh
cd desktop
python -m pip install -r requirements.txt
python shellground.py
```

Linux 빌드: `bash desktop/build.sh`. Windows 빌드: PowerShell에서 `desktop/build-windows.ps1`.

## 안내

[사용설명서](docs/USER_GUIDE.ko.md) · [실행 및 지원 범위](desktop/README.md) · [학습 순서](desktop/LEARNING_PATH.md) · [검증 기록](desktop/VERIFICATION.md) · [개발 구조](docs/DEVELOPMENT.ko.md)

전체 GNU/bash/Docker를 구현한 운영체제가 아닙니다. 아직 미구현인 명령·옵션은 오류로 표시합니다. 패키지/이미지·자원 수치는 학습용 가상 상태이며 실제 설치·네트워크·성능 측정이 아닙니다. 강의자료의 모든 명령·옵션을 다루는 확장은 아직 미완료입니다.

이전 Docker 백엔드와 문자열 퀴즈는 보관용이며 4.x GUI에서 사용하지 않습니다. 이전 버전의 Docker 자원을 자동으로 삭제하지 않습니다. 완료 진도와 기억노트는 유지합니다.
