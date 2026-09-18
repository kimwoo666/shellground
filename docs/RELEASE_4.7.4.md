# Shellground 4.7.4 preview

> 이 문서는 최초 배포 당시의 기록입니다. 지금은 [OS별 설치파일 하나](https://github.com/kimwoo666/shellground/releases/tag/v4.7.4-setup.1)를 받으세요. 아래 수동 조각 합치기는 일반 사용자가 하지 않습니다. The current [setup guide](GETTING_STARTED.md) replaces the manual assembly instructions below.

**Linux · Windows · Android**용 네이티브 학습 프로그램입니다. Linux 명령, Docker, ROS 2, Python·과학 라이브러리, Conda·pip, 실제 Jupyter 커널을 한 프로그램에서 연습합니다.

[한국어 소개](https://github.com/kimwoo666/shellground/blob/main/README.ko.md) · [English introduction](https://github.com/kimwoo666/shellground/blob/main/README.md) · [사용 방법](https://github.com/kimwoo666/shellground/blob/main/docs/GETTING_STARTED.ko.md)

![실제 Linux 학습 화면](https://raw.githubusercontent.com/kimwoo666/shellground/main/docs/screenshots/linux-learning.png)

## 무엇을 받나요?

| 대상 | 필요한 파일 |
| --- | --- |
| Linux x86-64 | `Linux-App.tar` + **PC-Guest 조각 01–05 전부** + `Join-Linux.sh` |
| Windows x64 | `Windows-App.zip` + **PC-Guest 조각 01–05 전부** + `Join-Windows.cmd` |
| Android | `Android.apk` 하나 |
| 개발·라이선스 자료 | 저장소 소스 + `Native-Sources.tar` |

파일명 앞에는 `Shellground-4.7.4-`가 붙습니다. PC 파일들은 빈 폴더에 받고 Join 파일을 한 번 실행합니다. 파일 확인·압축 해제·디스크 조합이 끝나면 생성된 폴더 안의 실행파일을 사용하세요. Linux에서는 `sh Join-Linux.sh`를 사용합니다. Python·Conda·Docker·WSL·Termux를 별도로 설치하지 않습니다.

PC 두 버전의 실습 디스크는 같은 내용이라 **7.8GB 공통 파일을 한 번만 배포**합니다. 완성된 앱 폴더는 약8GB이며, 다운로드 조각과 조립 결과를 동시에 보관하려면 약17GB 여유가 필요합니다. 조립 후 다운로드 조각은 지워도 됩니다. Android APK는 약2.10GB이며 설치 전 최소10GB 여유 공간을 권장합니다.

## 이번 배포

- 배우기 소단계 → 예시 → 활용 → 항목별 채점 → 복습·올랜덤으로 이어집니다.
- 완료 학습과 소단계 진도는 자동 저장합니다. 미완료 채점 후 같은 실습에서 계속 수정합니다.
- Python 실행과 그래프, 실제 Linux 기반 명령, Conda 환경, Jupyter 커널은 각 실행 환경의 결과를 사용합니다.
- 한·영 소개문, 실제 화면, 플랫폼별 사용법을 제공합니다. 기존 검사 전체를 반복하지 않고 변경된 부분과 포팅 연결부를 확인했습니다.

**검증 경계:** Windows는 Wine에서 실행파일을 제작했으며 Windows PC 실기동은 미검증입니다. Android 검사는 에뮬레이터 기준으로 ARM 실휴대폰의 성능·발열 검증은 아닙니다. 이 때문에 정식 안정판이 아닌 preview로 공개합니다. [상세 범위](https://github.com/kimwoo666/shellground/blob/main/docs/PLATFORMS.md)

입력 코드와 실습 파일은 임시 자료입니다. Python 실행 프로세스는 외부 악성 코드를 안전하게 실행하는 보안 격리 환경이 아닙니다. 학습 코드만 실행하세요. 실행파일은 자체 제작 서명/개발 서명이며 스토어 심사를 받은 배포판은 아닙니다.

---

## English

Shellground is a native learning application for Linux, Windows and Android. It combines Linux, Docker, ROS 2, Python/data libraries, Conda/pip and actual Jupyter kernels. Teaching content and the application UI are currently Korean; introductions and setup instructions are bilingual.

For desktop, download your platform's **App archive**, **all five shared PC-Guest parts**, and its **Join script** into an empty folder. Run the Join script once, then launch the executable in the resulting application folder. Android needs only the APK and runs without a connected PC. [English setup guide](https://github.com/kimwoo666/shellground/blob/main/docs/GETTING_STARTED.md)

The identical7.8GB desktop guest is distributed once rather than duplicated across platforms. Allow about17GB for desktop download plus assembly, or at least10GB free for Android installation. Download chunks can be removed after desktop assembly; keep the assembled runtime.

**Preview limitations:** Windows binaries were built using Wine and have not been run on a native Windows PC. Android emulator results do not establish physical ARM-phone performance or thermal behavior. Current lesson counts are not a claim of exhaustive support for every lecture option. Existing unchanged evidence was reused; new integration boundaries were checked separately.

`Native-Sources.tar` contains corresponding source and required licensing material for bundled native components. It is not needed to launch the app. Checksums and small build/verification reports accompany the release.
