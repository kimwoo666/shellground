# One download per OS / OS별 파일 하나로 설치

Delivery revision `v4.7.4-setup.1`, same learning binaries as 4.7.4.

- Windows: **Shellground-Windows-Setup.exe** → 설치 → 시작 메뉴/바탕화면 **Shellground**.
- Linux: **Shellground-Linux-Setup.run** → 설치 → 앱 메뉴 **Shellground**.
- Android: **Shellground-4.7.4-Android.apk** → 설치 → 앱 아이콘.

PC는 첫 설치에 인터넷이 필요한 온라인 설치 프로그램입니다. 프로그램과 실습 자료 약 8.1GB를 자동으로 받고 SHA-256을 확인합니다. 약 9GB 여유 공간을 준비하세요. 조각 고르기·합치기·압축 해제는 설치창이 처리하며 사용자 작업이 아닙니다. 중단 후 검증된 구간부터 이어 받습니다. 설치 후에는 포함된 과정의 실습 자료를 다시 받지 않습니다.

기존 학습 실행파일·Android APK·실습 디스크는 변경하지 않았습니다. 새 설치 경로만 검사했습니다: 8개 소규모 전송/복구/잠금/경로 보호 검사, Linux 설치창 표시·종료, 최종 설치파일의 HTTPS와 공개 메타데이터 체크섬, NSIS 빌드, C# 다운로드 모듈 타입 검사. 8GB 재다운로드나 학습 과정 재실행은 하지 않았습니다. **Windows PC에서 설치를 실행한 결과는 아닙니다.**

## English

Download one file for your OS. PC setup automatically downloads and verifies its application and practice data, creates a Shellground launcher and supports resuming verified segments. First setup needs Internet and about 9GB free; it is not a fully offline installer. Android retains its standalone APK.

Learning binaries are unchanged. Verification focuses on the new installer layer; it does not claim native Windows execution or repeat existing curriculum tests. [Full installation guide](GETTING_STARTED.md) · [Platform boundaries](PLATFORMS.md)
