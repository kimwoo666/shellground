# 처음 실행하기

[English](GETTING_STARTED.md) · [소개](../README.ko.md)

## 운영체제에 맞는 파일 받기

[Shellground 릴리스](https://github.com/kimwoo666/shellground/releases/tag/v4.7.4-preview)에서 실행 묶음을 받습니다. GitHub가 자동으로 붙이는 `Source code` 파일은 개발용 소스이며 실행 묶음이 아닙니다.

- **Linux x86-64:** 아래 PC 조립 안내에 따라 `Join-Linux.sh`를 한 번 실행한 후, 완성된 폴더의 `Shellground`를 엽니다. `runtime` 폴더도 유지하세요. 실행 권한이 없다면 `chmod +x Shellground` 후 `./Shellground`를 사용합니다.
- **Windows x64:** 아래 PC 조립 안내에 따라 `Join-Windows.cmd`를 한 번 실행한 후, 완성된 폴더의 `Shellground.exe`를 엽니다. `_internal`과 `runtime` 폴더를 함께 보관하세요. WSL은 사용하지 않습니다. 실제 Windows PC 실행은 확인하지 않은 빌드입니다.
- **Android:** APK를 휴대폰에 내려받거나 옮긴 다음 열어 설치합니다. 필요하면 파일을 연 앱의 ‘알 수 없는 앱 설치’를 허용합니다. 설치 후 PC 연결은 필요 없습니다. Python은 Android7 이상, Linux 기반 과정은 Android9 이상과 지원되는64비트 ABI가 필요하며 실휴대폰 호환성은 미검증입니다.

Android APK는 약2.10GB입니다. Linux 최초 준비에 약2GB와 실습 파일 공간이 추가로 필요합니다. 설치·업데이트 임시 공간을 고려해 설치 전 최소10GB 여유를 권장합니다. Linux 실습은 Android와 앱 메모리 외에2GiB 게스트 메모리를 사용하므로6GB 이상 메모리의 기기를 권장합니다. 저사양 휴대폰의 원활한 사용을 보장하지 않습니다.

PC판은 **해당 OS의 App 압축파일 + 공통 `PC-Guest.qcow2.part01`부터 마지막 조각까지 전부 + 해당 OS의 Join 파일**을 빈 폴더에 받습니다. Windows는 `Join-Windows.cmd`, Linux는 `sh Join-Linux.sh`를 실행합니다. 파일 검증·압축 해제·디스크 조합을 마치면 만들어진 `Shellground-Windows` 또는 `Shellground-Linux` 폴더에서 프로그램을 실행합니다. 이후에는 Join을 다시 실행할 필요가 없습니다. 공통 디스크는 두 OS에서 내용이 같아 한 번만 배포합니다. GitHub는 [첨부파일 한 개를2GiB 미만으로 제한](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases#storage-and-bandwidth-quotas)하므로 조각으로 제공합니다. 조립 완료 후 다운로드 조각은 삭제해도 되지만, 완성된 폴더의 `runtime`은 유지하세요. Android는 이 PC 파일들이 필요 없고 APK만 받습니다.

## 학습 시작

1. 분야를 고릅니다. PC에서는 상단 모드 탭, Linux·Docker·ROS2 분야 탭을 이용합니다. Jupyter는 Python 모드 안에 있습니다. Android에서는 메뉴에서 분야를 고릅니다.
2. 단원을 고르고 소단계 설명을 읽습니다. 설명을 보면서 직접 연습할 수 있습니다.
3. 예시를 실행한 뒤 활용 문제로 넘어갑니다.
4. 명령이나 코드를 실행하고 **채점**을 눌러 목표별 결과를 확인합니다.
5. 미완료이면 문제로 돌아가 이어서 수정합니다. **다시 시작**은 처음 상태로 되돌리고 싶을 때만 누릅니다.

설명만 읽을 때는 실습 환경을 바로 부팅하지 않습니다. 첫 Linux 실습 준비에는 시간이 걸리며, 창을 여는 속도와 OS 부팅 속도는 다릅니다.

## 저장과 종료

완료한 학습, 개념 학습 진도, 소단계 위치는 자동 저장됩니다. 종료하면 앱이 만든 실습 프로세스를 정리합니다. 개인 Docker·WSL 설치를 이용하거나 지우지 않습니다.

입력 코드·명령 기록·변수·실습 파일은 임시 자료입니다. Jupyter의 저장은 **현재 실습 환경 안에** `.ipynb`를 쓰는 기능이지 휴대폰/PC 문서에 영구 저장하는 기능이 아닙니다. 현재 버전이 범용 노트북 내보내기 기능을 제공한다고 보지 마세요.

신뢰할 수 있는 학습 코드만 실행하세요. Python 실행 프로세스는 악성 코드용 보안 격리 환경이 아닙니다. [운영체제별 확인 범위](PLATFORMS.md)도 참고하세요.
