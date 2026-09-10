# 외부 구성요소 안내

이 저장소에서 사용하는 주요 외부 구성요소입니다. 애플리케이션 자체에 새로운 라이선스를 임의로 부여하지 않았으며, 아래 고지는 각 외부 구성요소의 라이선스를 대체하지 않습니다.

| 구성요소 | 사용 방식 | 확인 위치 |
| --- | --- | --- |
| Noto Sans CJK | 한글 표시용 글꼴 파일 포함 | [동봉된 저작권/OFL 고지](desktop/assets/Noto-COPYRIGHT.txt) |
| Qt for Python / PySide6 | Python 의존성으로 설치 | [Qt for Python](https://doc.qt.io/qtforpython-6/), 설치 패키지의 라이선스 문서 |
| pyte, wcwidth | 터미널 상태와 문자 너비 처리 | 설치 패키지의 라이선스 문서 |
| PyInstaller | 운영체제별 실행 파일 패키징 | [PyInstaller](https://pyinstaller.org/), 설치 패키지의 라이선스 문서 |
| libxcb-cursor | 일부 Linux 빌드에서 커서 라이브러리로 사용 | [저작권 고지](desktop/assets/libxcb-cursor-COPYRIGHT.txt); 라이브러리 바이너리는 이 소스 저장소에 포함하지 않음 |
| Ubuntu 및 GNU/Linux 도구 | Dockerfile을 통해 설치 | 각 배포 패키지의 저작권/라이선스 문서 |

글꼴은 수정하지 않은 파일을 고지와 함께 포함합니다. Python 의존성 자체, 시스템 패키지, Docker 이미지, 빌드된 실행 파일은 Git 소스 이력에 포함하지 않습니다.
