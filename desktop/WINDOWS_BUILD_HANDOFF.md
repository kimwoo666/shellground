# Windows 빌드·실기동 검토 재개 지점

이 문서는 **개발자용**이다. 2026-09-18에 Windows x64 `Shellground.exe` 생성을 완료했다. Linux의 프로젝트 전용 Wine에서 Windows Python 3.12.10·Qt 6.8.3·PyInstaller 6.22.2로 제작했다. 실제 Windows PC 실행 검증은 하지 않았다. 최종 사용자는 Python·Conda·WSL을 설정하지 않는다.

Windows 배포 폴더는 `windows_delivery.py`로 논리 디스크 내용이 같은지 비교하며 압축하고, `../releases/Shellground-4.7.4-Windows-x64.zip`으로 묶는다. 압축 단계는 새 수업 검사나 Windows 실행 증거가 아니다. 아래의 빌드 입력 경로는 개발 단계 경로이며 최종 캐시 정리 후에는 실행파일에 포함되지 않는다.

원본 Conda 검증 실행파일을 계속 보관할 필요는 없다. `archive_conda_baseline.py`가 원본 두 소스·메타데이터만 9,675바이트로 추출했고, `.jupyter-build/conda-shared-shell-carry-compact.json`이 원본 강의 지문과 해당 파일의 해시를 검증한다. 과거 보고서를 수정하거나 전체 수업을 다시 실행하지 않았다.

## 준비된 배포 구조

Windows는 `dist-windows-4.7.4-review/Shellground/Shellground.exe`와 같은 폴더의 `_internal`, `runtime/windows-x86_64`를 함께 배포하는 형태로 변경했다. 실습 디스크 때문에 어차피 외부 폴더가 필요하다. 과학 라이브러리/Qt를 worker·VM 시작 때마다 임시 압축 해제하지 않고, 부모가 감독 프로세스를 직접 관리하도록 onedir를 선택했다. Linux 기존 onefile 실행파일은 변경하지 않았다.

Windows frozen interpreter에는 `X utf8`을 넣는다. `build-windows.ps1`도 빌드 동안만 UTF-8 환경을 사용하고 원래 값을 복구한다. `stdio_transport.py`는 GUI 실행파일에서 상속받은 Win32 핸들을 복제하고 CRT descriptor 0/1/2에 연결한다. 단순히 sys.stdin만 복원하고 실제 fd 0은 비워 두던 문제가 남지 않도록 했다. 일반 UI 실행에는 이 내부 모드 복구를 강제로 적용하지 않는다.

## Windows 빌더에 필요한 입력

- 현재 `desktop` 소스와 `assets`, `guest`, `lab`, `python_teaching`, `conda_teaching`, `notebook_teaching` 자료. LF 줄바꿈을 보존한다.
- `.windows-build/runtime/windows-x86_64` 전체. base는 16GB이며 다른 PC로 옮길 때는 실제 파일을 운반해야 한다. 원본 Linux runtime은 수정하지 않는다.
- `.jupyter-build/incremental-course-manifest-windows-prep.json`, 거기서 참조하는 원본 evidence 파일/리뷰 문서. original 441 manifest도 보존한다.
- `.jupyter-build/conda-shared-shell-carry-compact.json`과 참조하는 delta/rationale, `.jupyter-build/conda-baseline`의 작은 원본 소스·메타데이터. 구형 검증 실행파일은 더 이상 필요하지 않다.
- `.jupyter-build/course-final.json`, `ui-final.json`, `wheels-linux-x86_64`(Jupyter guest 설치 자료), `.conda-build/numpy-2.3.5-cp312-cp312-manylinux_2_27_x86_64.manylinux_2_28_x86_64.whl`.
- Windows 빌더의 Python 3.12 x64와 requirements 두 파일의 의존성. 이것은 제작 환경이며 최종 배포 사용자 요구 사항이 아니다.

GitHub 업로드는 이 포팅 작업에서 수행하지 않았다. Windows 호스트 제공 없이 로컬에서 패키징했으며 빌드 상태의 `native_platform_accepted`는 false로 유지한다.

## 재개할 빌드 명령

아래는 준비된 명령이며 **Windows에서 실행한 기록이 아니다**. Windows 빌더가 정해지면 먼저 CPU·온도·디스크 여유와 빌드 자원 제한을 설정하고 한 작업씩 실행한다. `--link-runtime`은 같은 파일시스템에서만 쓰며 base를 제자리 수정하지 않는다.

```powershell
.\build-windows.ps1 `
  --dist-dir .\dist-windows-4.7.4-review `
  --with-conda-runtime --with-notebook-runtime `
  --runtime-source .\.windows-build\runtime\windows-x86_64 `
  --link-runtime `
  --course-manifest .\.jupyter-build\incremental-course-manifest-windows-prep.json `
  --conda-carry-review .\.jupyter-build\conda-shared-shell-carry-compact.json
```

Windows guest carry gate는 원본 Linux Conda gate를 먼저 검증하고 복사된 원본 metadata/guest disk/Windows assets를 대조한다. old PASS의 해시나 플랫폼을 바꾸지 않는다. 학습 manifest는 441 reviewed-carry / 0 current이며 Windows 실행 증거를 담지 않는다. 문제나 채점기가 바뀌면 해당 사례를 새로 검증해야 한다.

향후 실제 Windows 기기가 있을 때 선택적으로 확인할 경계는 다음과 같다. 사용자가 Windows 테스트 환경을 제공하지 않는다는 조건에 따라 이번 배포는 실제 Windows 실행 미검증 상태를 명시하며 제작한다. 이 목록 때문에 다른 OS 포팅을 보류하거나 사용자에게 기기를 요구하지 않는다.

1. `--self-test-windows-pipes`: 실제 frozen Windows에서만 실행 가능. 한글 stdin/stdout/stderr, raw fd 0의 EOF, UTF-8 모드, 실제 Windows Job 설정 조회 및 3초 CPU 시간 관찰을 기록한다. Linux/소스 실행을 Windows PASS로 쓰지 못한다. 이 검사도 **VM CPU 사용량이나 VM 강제 종료를 검증한 것은 아니다**.
2. 기존 new-binary resource/worker 검사와 단일 창·Shift+Enter·탭 전환·숨겨진 worker 정리 검사. 구 과정을 전수 실행하지 않는다.
3. 실제 Conda 한 경로의 prepare→미완료 채점→같은 터미널 해결→재채점→파일 조회와 VM/overlay 정리.
4. 실제 선택한 Jupyter 커널 연결/코드 실행/저장/정리의 packaged 확인.

WHPX/TCG별 기동 시간, OS별 창 동작과 비정상 종료는 실제 Windows에서 확인하지 않았다. 패키지 제작 완료와 실제 Windows 실행 검증 완료는 구별한다. 컴퓨터 종료 지시는 철회되었으며 이번 작업 종료 후에도 호스트를 종료하지 않는다.

참고: [PyInstaller Windows GUI 표준 입출력](https://pyinstaller.org/en/stable/common-issues-and-pitfalls.html#sys-stdin-sys-stdout-and-sys-stderr-in-noconsole-windowed-applications-windows-only), [interpreter UTF-8 옵션](https://pyinstaller.org/en/stable/spec-files.html#specifying-python-interpreter-options), [Win32 핸들 복제](https://learn.microsoft.com/en-us/windows/win32/api/handleapi/nf-handleapi-duplicatehandle).
