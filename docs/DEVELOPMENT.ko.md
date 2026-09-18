# 개발 안내

일반 사용자는 [실행 묶음](https://github.com/kimwoo666/shellground/releases/tag/v4.7.4-preview)을 사용합니다. 아래 도구는 개발 환경에만 필요합니다.

## 구성

- `desktop/`: Python·Qt 기반 단일 창 UI, Linux/Docker/ROS 과제, Python·Conda·Jupyter 과정과 실제 상태 채점.
- `android/app/`: Java 네이티브 UI와 내장 CPython. 데스크톱 학습 자료를 빌드 시 가져옵니다.
- `android/runtime/`: Android용 QEMU 제작, ARM64 guest 준비, 앱 전용 통신 연결.
- `docs/screenshots/`: 실제 실행 화면. 화면 제작용 시안이 아닙니다.

## 제작과 검증

PC는 `desktop/requirements.txt`와 `python-requirements.txt`, 각 운영체제용 빌드 스크립트를 사용합니다. 실제 Linux 실습에는 별도로 제작된 runtime 팩이 필요합니다. 소스만 내려받으면 대형 실습 디스크가 자동으로 생기는 것은 아닙니다.

Android 개발 도구와 빌드 옵션은 [Android README](../android/README.md), 내부 Linux 제작 절차는 [runtime README](../android/runtime/README.md)를 따릅니다. 최신 빌드의 임시 SDK·캐시는 저장소에 넣지 않습니다. Android 업데이트용 서명 키도 공개하지 않습니다.

문제와 채점 조건은 공통 소스에서 관리합니다. Android에 별도 정답 문자열 표를 만들지 않습니다. 아키텍처별 패키지 선택과 모바일 시작 대기는 별도 포팅 경계이며 학습 목표나 채점 조건을 완화하지 않습니다.

검사는 새 기능·변경 영향 범위를 우선합니다. 이미 검증한 동일 문제를 매번 전수 실행하지 않습니다. 실제 Windows 환경이 없으므로 Windows 바이너리 제작 사실과 Windows 실행 미검증 사실을 함께 기록합니다.

## 공개 저장소 정리 원칙

실행파일은 GitHub Releases, 소스와 문서는 Git에 둡니다. VM·SDK·빌드 캐시·개인 진도·서명 키·강의 PDF는 커밋하지 않습니다. LGPL/GPL 등 배포 구성요소의 고지와 필요한 대응 소스는 쓰레기 캐시와 구분해 보존합니다.
